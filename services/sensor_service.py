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
"""
import logging
import platform
import time
from threading import Lock, Thread

from services import mock_sensors

logger = logging.getLogger(__name__)

# Real ENS160 lives at 0x53 (or 0x52 if ADDR is tied low). 0x68 is for RTC
# chips like DS3231 / IMU MPU6050 — using that address here was the bug
# that made the sensor service silently fall back to mock on Pi.
ENS160_ADDRESS = 0x53
AHTX0_ADDRESS = 0x38

# Per-update polling cadence. The UI polls get_readings() far more often
# than this; the readings are just served from cache between updates.
UPDATE_INTERVAL_SEC = 30
MAX_CONSECUTIVE_FAILURES = 5


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

    # ── Lifecycle ─────────────────────────────────────────────────────
    def start(self) -> None:
        """Initialise hardware and spawn the polling thread. Idempotent
        for callers that retry — but cheap enough that we don't bother
        reusing a previous instance."""
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
        logger.info("sensor service stopped")

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
        # Read everything before taking the lock so I2C wait never blocks
        # get_readings() callers.
        co2 = self.ens.eCO2
        tvoc = self.ens.TVOC
        aqi = self.ens.AQI
        temperature = self.aht.temperature
        humidity = self.aht.relative_humidity
        air_quality = _AQI_LABEL.get(aqi, f"Unknown ({aqi})")

        with self._lock:
            self._readings["co2"] = co2
            self._readings["tvoc"] = tvoc
            self._readings["air_quality"] = air_quality
            self._readings["temperature"] = temperature
            self._readings["humidity"] = humidity

        logger.debug(
            f"t={temperature:.1f}C h={humidity:.1f}% "
            f"CO2={co2}ppm TVOC={tvoc}ppb AQI={air_quality}"
        )

    def get_readings(self) -> dict:
        """Atomic snapshot of the latest readings."""
        with self._lock:
            return self._readings.copy()
