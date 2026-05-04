"""
Mock implementations of the AHT21 + ENS160 + adafruit-blinka surface so
SensorService can run on Windows / dev boxes (and as a fallback on Pi if
the native libraries fail to import).

The real ENS160 lives at I2C 0x53 (or 0x52 if ADDR is tied low). The old
mock had it at 0x68, which is the address for RTC chips like DS3231 and
the MPU6050 IMU — picking that address up by accident on the bus would
silently mask a real ENS160 init failure. Keep these constants in sync
with sensor_service.ENS160_ADDRESS / AHTX0_ADDRESS.
"""
import logging
import random

logger = logging.getLogger(__name__)

ENS160_ADDRESS = 0x53
AHTX0_ADDRESS = 0x38


class MockBoard:
    SCL = "SCL"
    SDA = "SDA"


class MockI2C:
    def __init__(self, scl, sda):
        logger.debug(f"mock I2C (SCL={scl}, SDA={sda})")


class MockENS160:
    """Slow random walk so the UI shows movement during dev."""

    def __init__(self, i2c, address: int = ENS160_ADDRESS):
        self._eco2 = 800     # ppm — typical room baseline
        self._tvoc = 250     # ppb — typical "good" range
        self._aqi = 2        # 1=Excellent .. 5=Unhealthy
        logger.debug(f"mock ENS160 at 0x{address:02x}")

    @property
    def eCO2(self) -> int:
        self._eco2 = max(400, min(self._eco2 + random.randint(-25, 25), 1500))
        return self._eco2

    @property
    def TVOC(self) -> int:
        self._tvoc = max(50, min(self._tvoc + random.randint(-15, 15), 500))
        return self._tvoc

    @property
    def AQI(self) -> int:
        # Flip the AQI category occasionally so the dev UI shows colour
        # transitions; 5% per read is rare enough to look natural.
        if random.random() < 0.05:
            self._aqi = random.randint(1, 5)
        return self._aqi


class MockAHTx0:
    def __init__(self, i2c, address: int = AHTX0_ADDRESS):
        self._temperature = 22.5     # °C
        self._humidity = 45.0        # %
        logger.debug(f"mock AHT21 at 0x{address:02x}")

    @property
    def temperature(self) -> float:
        self._temperature = max(18.0, min(self._temperature + random.uniform(-0.3, 0.3), 28.0))
        return self._temperature

    @property
    def relative_humidity(self) -> float:
        self._humidity = max(30.0, min(self._humidity + random.uniform(-1.0, 1.0), 70.0))
        return self._humidity


# Adafruit module-level factory functions — match the surface that
# adafruit_ens160.ENS160 / adafruit_ahtx0.AHTx0 expose, so SensorService
# can call them interchangeably.
def ENS160(i2c, address: int = ENS160_ADDRESS) -> MockENS160:
    return MockENS160(i2c, address)


def AHTx0(i2c, address: int = AHTX0_ADDRESS) -> MockAHTx0:
    return MockAHTx0(i2c, address)
