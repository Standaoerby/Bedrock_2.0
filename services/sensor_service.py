"""
SensorService — polls AHT21 (temperature/humidity, I2C 0x38) and ENS160
(eCO2/TVOC/AQI, I2C 0x53) every UPDATE_INTERVAL seconds in a daemon
thread. Latest readings are cached under a Lock and exposed via
`get_readings()` for the UI.

On Windows / dev boxes the adafruit-blinka stack isn't available, so we
fall back to the slow-random-walk mocks in services/mock_sensors.py. The
fallback also kicks in on Pi when the libraries fail to import (typically
because `python3-lgpio` / circuitpython packages weren't installed) — the
UI keeps working, just with placeholder values.

Calibration: temp_offset / humidity_offset live in config/user.json. The
AHT21 chip on the Pi 5 case sees ~7-8 C above ambient because the Pi
itself heats it. Apply a negative offset to correct. Reloaded on demand
via reload_calibration() — admin web UI calls this through a follow-up
endpoint, or just restart bedrock.service.
"""
import json
import logging
import os
import platform
import time
from threading import Lock, Thread

from services import mock_sensors

logger = logging.getLogger(__name__)

USER_CONFIG_PATH = "config/user.json"
SENSORS_CACHE_PATH = "cache/sensors.json"

# Real ENS160 lives at 0x53 (or 0x52 if ADDR is tied low). 0x68 is for RTC
# chips like DS3231 / IMU MPU6050 — using that address here was the bug
# that made the sensor service silently fall back to mock on Pi.
ENS160_ADDRESS = 0x53
AHTX0_ADDRESS = 0x38

# LDR (light dependent resistor) on BCM GPIO 12, digital read with pull-up:
# 0 = light, 1 = dark (LDR drops resistance under light, pulls input low).
# Smoothing buffer kept inside SensorService — read_light_level() returns
# the majority of the last LDR_BUFFER_SIZE samples, so brief flickers
# (cloud passing, hand wave) don't churn the auto-theme.
LDR_GPIO_PIN = 12
LDR_BUFFER_SIZE = 4

# Per-update polling cadence. The UI polls get_readings() far more often
# than this; the readings are just served from cache between updates.
UPDATE_INTERVAL_SEC = 30
MAX_CONSECUTIVE_FAILURES = 5

# LDR backend — gpiozero shares its LGPIOFactory with VolumeService's
# Buttons, so GPIO chip 0 is opened exactly once per process. Going raw
# `lgpio.gpiochip_open(0)` here would double-claim against gpiozero —
# that's the failure mode that bit the 1.0.x branch (see RECOVERY.md).
try:
    from gpiozero import DigitalInputDevice as _LdrInput  # type: ignore
    _GPIOZERO_AVAILABLE = True
except ImportError:
    _LdrInput = None  # type: ignore
    _GPIOZERO_AVAILABLE = False


# ── Backend resolution ────────────────────────────────────────────────
# Bind `board`, `busio`, `_ens160_factory`, `_ahtx0_factory` once at
# import time so SensorService.start() doesn't have to branch on
# Windows / Pi / fallback. `_use_real_sensors` is informational — the
# factories themselves are interchangeable.
_use_real_sensors = False

if platform.system() == "Windows":
    logger.info("Windows — using mock sensors")
    board = mock_sensors.MockBoard()
    busio = mock_sensors.MockI2C
    _ens160_factory = mock_sensors.ENS160
    _ahtx0_factory = mock_sensors.AHTx0
else:
    try:
        import board                 # type: ignore
        import busio                 # type: ignore
        import adafruit_ens160       # type: ignore
        import adafruit_ahtx0        # type: ignore

        _ens160_factory = adafruit_ens160.ENS160
        _ahtx0_factory = adafruit_ahtx0.AHTx0
        _use_real_sensors = True
        logger.info("Real sensor libraries loaded")
    except ImportError as e:
        logger.warning(f"sensor libraries missing ({e}); using mocks")
        logger.warning("Install: sudo apt-get install -y python3-lgpio")
        logger.warning(
            "         pip install adafruit-blinka "
            "adafruit-circuitpython-ens160 adafruit-circuitpython-ahtx0"
        )
        board = mock_sensors.MockBoard()
        busio = mock_sensors.MockI2C
        _ens160_factory = mock_sensors.ENS160
        _ahtx0_factory = mock_sensors.AHTx0


_AQI_LABEL = {
    1: "Excellent",
    2: "Good",
    3: "Moderate",
    4: "Poor",
    5: "Unhealthy",
}


class SensorService:
    def __init__(self):
        self.sensor_available = False
        self.i2c = None
        self.ens = None
        self.aht = None
        self.running = False
        self.thread: Thread | None = None
        self._lock = Lock()
        self._consecutive_failures = 0
        self._readings = {
            "temperature": 0,
            "humidity": 0,
            "co2": 0,
            "tvoc": 0,
            "air_quality": "Unknown",
        }
        # Calibration offsets — added to raw sensor reading. Negative
        # offset compensates for case heat (~ -7.5 on Pi5).
        self._temp_offset = 0.0
        self._humidity_offset = 0.0
        self._cal_mtime = 0.0
        self.reload_calibration()

        # LDR state — initialised in _init_ldr(), called from start().
        self._ldr_backend: str = "none"        # "gpiozero" / "mock" / "none"
        self._ldr_device = None                 # gpiozero DigitalInputDevice
        self._ldr_mock = None                   # MockLDR for Windows / no GPIO
        self._ldr_buffer: list[bool] = []
        self._ldr_lock = Lock()

    def reload_calibration(self) -> None:
        """Re-read calibration offsets from config/user.json. Cheap to
        call from a polling thread — only re-parses when mtime changed."""
        try:
            mtime = os.path.getmtime(USER_CONFIG_PATH)
        except OSError:
            return
        if mtime == self._cal_mtime:
            return
        try:
            with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        self._temp_offset = float(cfg.get("temp_offset", 0.0))
        self._humidity_offset = float(cfg.get("humidity_offset", 0.0))
        self._cal_mtime = mtime
        logger.info(
            f"calibration reloaded: temp_offset={self._temp_offset:+.2f} "
            f"humidity_offset={self._humidity_offset:+.2f}"
        )

    # ── Lifecycle ─────────────────────────────────────────────────────
    def start(self) -> None:
        """Initialise hardware and spawn the polling thread. Idempotent
        for callers that retry — but cheap enough that we don't bother
        reusing a previous instance."""
        self._init_ldr()
        try:
            if _use_real_sensors:
                self.i2c = busio.I2C(board.SCL, board.SDA)
            else:
                self.i2c = busio(board.SCL, board.SDA)
            self.ens = _ens160_factory(self.i2c, address=ENS160_ADDRESS)
            self.aht = _ahtx0_factory(self.i2c, address=AHTX0_ADDRESS)

            self.sensor_available = True
            self.update_readings()

            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            logger.info("sensor service started")
        except Exception:
            # Hardware init covers a lot of failure modes (I2C bus busy,
            # device not present, permission errors). Log and continue
            # in disabled state so the UI shows zeros instead of crashing.
            logger.exception("sensor init failed — service disabled")
            self.sensor_available = False

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self._release_ldr()
        logger.info("sensor service stopped")

    # ── LDR (light sensor on GPIO 12) ─────────────────────────────────
    def _init_ldr(self) -> None:
        """Claim BCM 12 via gpiozero (which uses the process-shared
        LGPIOFactory on Pi 5). On Windows / no gpiozero, fall back to
        MockLDR — auto-theme stays usable in dev."""
        if _GPIOZERO_AVAILABLE:
            try:
                # pull_up=True matches the LDR voltage divider: light
                # pulls the pin LOW (value=0), dark leaves it HIGH (value=1).
                self._ldr_device = _LdrInput(LDR_GPIO_PIN, pull_up=True)
                _ = self._ldr_device.value  # smoke read
                self._ldr_backend = "gpiozero"
                logger.info(f"LDR ready on BCM {LDR_GPIO_PIN} via gpiozero")
                return
            except Exception as e:
                logger.warning(f"gpiozero LDR init failed: {e}")
                if self._ldr_device is not None:
                    try:
                        self._ldr_device.close()
                    except Exception:
                        pass
                self._ldr_device = None

        # Fallback: mock (Windows / no GPIO available)
        self._ldr_mock = mock_sensors.MockLDR()
        self._ldr_backend = "mock"
        logger.info("LDR using mock (day/night by hour)")

    def _release_ldr(self) -> None:
        if self._ldr_device is not None:
            try:
                self._ldr_device.close()
            except Exception:
                pass
            self._ldr_device = None

    def _read_ldr_raw(self) -> int | None:
        """Return 0 (light) / 1 (dark), or None if backend isn't ready."""
        try:
            if self._ldr_backend == "gpiozero":
                return int(self._ldr_device.value)
            if self._ldr_backend == "mock":
                return self._ldr_mock.read_digital()
        except Exception as e:
            logger.warning(f"LDR raw read failed ({self._ldr_backend}): {e}")
        return None

    def read_light_level(self) -> bool | None:
        """Smoothed light reading: True = light, False = dark, None if
        the backend isn't usable. Each call samples the GPIO once and
        returns the majority of the last LDR_BUFFER_SIZE samples."""
        raw = self._read_ldr_raw()
        if raw is None:
            return None
        is_light = raw == 0
        with self._ldr_lock:
            self._ldr_buffer.append(is_light)
            if len(self._ldr_buffer) > LDR_BUFFER_SIZE:
                self._ldr_buffer.pop(0)
            light_votes = sum(self._ldr_buffer)
            total = len(self._ldr_buffer)
        # Strict majority — at boundary (50/50) keep current vote
        return light_votes * 2 > total or (light_votes * 2 == total and is_light)

    def get_light_status(self) -> dict:
        """For the settings UI — backend type + last buffer state."""
        with self._ldr_lock:
            buf = list(self._ldr_buffer)
        return {
            "backend": self._ldr_backend,
            "available": self._ldr_backend != "none",
            "mock": self._ldr_backend == "mock",
            "buffer": buf,
            "current_light": (sum(buf) * 2 > len(buf)) if buf else None,
        }

    # ── Polling thread ────────────────────────────────────────────────
    def _background_update(self) -> None:
        while self.running:
            try:
                self.update_readings()
                self._consecutive_failures = 0
            except Exception as e:
                self._consecutive_failures += 1
                logger.warning(
                    f"sensor read error "
                    f"({self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}"
                )
                if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("too many sensor failures, stopping background updates")
                    self.sensor_available = False
                    self.running = False
                    return
            time.sleep(UPDATE_INTERVAL_SEC)

    def update_readings(self) -> None:
        if not self.sensor_available:
            return
        # Pick up live calibration edits from the admin UI without
        # restarting the panel.
        self.reload_calibration()
        # Read everything before taking the lock so I2C wait never blocks
        # get_readings() callers.
        co2 = self.ens.eCO2
        tvoc = self.ens.TVOC
        aqi = self.ens.AQI
        temperature_raw = self.aht.temperature
        humidity_raw = self.aht.relative_humidity
        # Calibration applied here so debug log shows the corrected
        # value the user actually sees on the panel.
        temperature = temperature_raw + self._temp_offset
        humidity = max(0.0, min(100.0, humidity_raw + self._humidity_offset))
        air_quality = _AQI_LABEL.get(aqi, f"Unknown ({aqi})")

        with self._lock:
            self._readings["co2"] = co2
            self._readings["tvoc"] = tvoc
            self._readings["air_quality"] = air_quality
            self._readings["temperature"] = temperature
            self._readings["humidity"] = humidity
            self._readings["temperature_raw"] = temperature_raw
            self._readings["humidity_raw"] = humidity_raw

        logger.debug(
            f"t={temperature:.1f}C (raw {temperature_raw:.1f}, off {self._temp_offset:+.1f}) "
            f"h={humidity:.1f}% "
            f"CO2={co2}ppm TVOC={tvoc}ppb AQI={air_quality}"
        )

        # Write a snapshot for the admin UI. Best-effort — failures here
        # never block the sensor loop.
        try:
            os.makedirs(os.path.dirname(SENSORS_CACHE_PATH), exist_ok=True)
            with open(SENSORS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "temperature": round(temperature, 2),
                    "humidity": round(humidity, 2),
                    "temperature_raw": round(temperature_raw, 2),
                    "humidity_raw": round(humidity_raw, 2),
                    "temp_offset": self._temp_offset,
                    "humidity_offset": self._humidity_offset,
                    "co2": co2,
                    "tvoc": tvoc,
                    "air_quality": air_quality,
                    "updated": time.time(),
                }, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def get_readings(self) -> dict:
        """Atomic snapshot of the latest readings."""
        with self._lock:
            return self._readings.copy()
