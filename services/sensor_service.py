"""
Сервис для работы с датчиками ENS160 (CO2/TVOC, I2C 0x53)
и AHT21 (температура/влажность, I2C 0x38).
На Windows используются встроенные mock-классы.
"""
import logging
import platform
import time
from threading import Thread, Lock

logger = logging.getLogger("SensorService")

# Real ENS160 lives at 0x53 (or 0x52 if ADDR pin is tied low). 0x68 is for
# RTC chips like DS3231 / IMU MPU6050 — using it here was the bug that made
# the sensor service silently fall back to mock on Pi.
ENS160_ADDRESS = 0x53
AHTX0_ADDRESS = 0x38


# ── Mock classes for Windows / dev ──────────────────────────────────────
class DummyBoard:
    SCL = "SCL"
    SDA = "SDA"


class DummyI2C:
    def __init__(self, scl, sda):
        logger.debug(f"Dummy I2C initialized (SCL: {scl}, SDA: {sda})")


class DummyENS160:
    def __init__(self, i2c, address=ENS160_ADDRESS):
        self._eco2 = 800
        self._tvoc = 250
        self._aqi = 2
        logger.debug(f"Dummy ENS160 at 0x{address:02x}")

    @property
    def eCO2(self):
        import random
        self._eco2 = max(400, min(self._eco2 + random.randint(-25, 25), 1500))
        return self._eco2

    @property
    def TVOC(self):
        import random
        self._tvoc = max(50, min(self._tvoc + random.randint(-15, 15), 500))
        return self._tvoc

    @property
    def AQI(self):
        import random
        if random.random() < 0.05:
            self._aqi = random.randint(1, 5)
        return self._aqi


class DummyAHTx0:
    def __init__(self, i2c, address=AHTX0_ADDRESS):
        self._temperature = 22.5
        self._humidity = 45.0
        logger.debug(f"Dummy AHT21 at 0x{address:02x}")

    @property
    def temperature(self):
        import random
        self._temperature = max(18.0, min(self._temperature + random.uniform(-0.3, 0.3), 28.0))
        return self._temperature

    @property
    def relative_humidity(self):
        import random
        self._humidity = max(30.0, min(self._humidity + random.uniform(-1.0, 1.0), 70.0))
        return self._humidity


def dummy_ENS160(i2c, address=ENS160_ADDRESS):
    return DummyENS160(i2c, address)


def dummy_AHTx0(i2c, address=AHTX0_ADDRESS):
    return DummyAHTx0(i2c, address)


# ── Platform detection ──────────────────────────────────────────────────
use_real_sensors = False
if platform.system() == 'Windows':
    logger.info("Windows — using mock sensors")
    board = DummyBoard()
    busio = DummyI2C
    adafruit_ens160 = dummy_ENS160
    adafruit_ahtx0 = dummy_AHTx0
else:
    try:
        import board
        import busio
        import adafruit_ens160
        import adafruit_ahtx0
        use_real_sensors = True
        logger.info("Real sensor libraries loaded")
    except Exception as e:
        logger.warning(f"Could not load sensor libraries ({e}); using mocks")
        logger.warning("Install: sudo apt-get install -y python3-lgpio")
        logger.warning("         pip install adafruit-blinka adafruit-circuitpython-ens160 adafruit-circuitpython-ahtx0")
        board = DummyBoard()
        busio = DummyI2C
        adafruit_ens160 = dummy_ENS160
        adafruit_ahtx0 = dummy_AHTx0


class SensorService:
    """Опрос ENS160 + AHT21, кэш в _readings под lock."""

    UPDATE_INTERVAL = 30
    MAX_CONSECUTIVE_FAILURES = 5

    def __init__(self):
        self.sensor_available = False
        self.ens = None
        self.aht = None
        self.running = False
        self.thread = None
        self._lock = Lock()
        self._consecutive_failures = 0
        self._readings = {
            'temperature': 0,
            'humidity': 0,
            'co2': 0,
            'tvoc': 0,
            'air_quality': 'Unknown'
        }

    def start(self):
        """Initialise hardware and spin the polling thread."""
        try:
            if use_real_sensors:
                self.i2c = busio.I2C(board.SCL, board.SDA)
                self.ens = adafruit_ens160.ENS160(self.i2c, address=ENS160_ADDRESS)
                self.aht = adafruit_ahtx0.AHTx0(self.i2c, address=AHTX0_ADDRESS)
            else:
                self.i2c = busio(board.SCL, board.SDA)
                self.ens = adafruit_ens160(self.i2c, address=ENS160_ADDRESS)
                self.aht = adafruit_ahtx0(self.i2c, address=AHTX0_ADDRESS)

            self.sensor_available = True
            self.update_readings()

            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            logger.info("Sensor service started")
        except Exception as e:
            logger.error(f"Sensor init failed: {e}")
            self.sensor_available = False

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("Sensor service stopped")

    def _background_update(self):
        while self.running:
            try:
                self.update_readings()
                self._consecutive_failures = 0
            except Exception as e:
                self._consecutive_failures += 1
                logger.warning(f"Sensor read error ({self._consecutive_failures}/{self.MAX_CONSECUTIVE_FAILURES}): {e}")
                if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    logger.error("Too many consecutive sensor failures, stopping background updates")
                    self.sensor_available = False
                    self.running = False
                    return
            time.sleep(self.UPDATE_INTERVAL)

    def update_readings(self):
        if not self.sensor_available:
            return
        try:
            co2 = self.ens.eCO2
            tvoc = self.ens.TVOC
            aqi = self.ens.AQI
            air_quality = {
                1: "Excellent", 2: "Good", 3: "Moderate",
                4: "Poor", 5: "Unhealthy",
            }.get(aqi, f"Unknown ({aqi})")
            temperature = self.aht.temperature
            humidity = self.aht.relative_humidity

            with self._lock:
                self._readings['co2'] = co2
                self._readings['tvoc'] = tvoc
                self._readings['air_quality'] = air_quality
                self._readings['temperature'] = temperature
                self._readings['humidity'] = humidity

            logger.debug(
                f"Sensors: t={temperature:.1f}C h={humidity:.1f}% "
                f"CO2={co2}ppm TVOC={tvoc}ppb AQI={air_quality}"
            )
        except Exception:
            # Re-raise so _background_update's failure counter sees it.
            raise

    def get_readings(self):
        """Atomic snapshot of latest readings."""
        with self._lock:
            return self._readings.copy()
