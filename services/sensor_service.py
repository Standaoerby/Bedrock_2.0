"""
Service for working with sensors (ENS160+AHT21)
Supports real sensors on Raspberry Pi and mock sensors for development
"""
import time
import os
import sys
from threading import Thread
import logging
import random
from utils.error_handler import ErrorHandler

# Configure logging
logger = logging.getLogger("SensorService")

# Define constants for I2C addresses
ENS160_ADDRESS = 0x53
AHT21_ADDRESS = 0x38

# Air quality levels mapping
AIR_QUALITY_LEVELS = {
    1: "Excellent",
    2: "Good", 
    3: "Moderate",
    4: "Poor",
    5: "Unhealthy"
}

# Mock classes for development/testing
class DummySensor:
    """Base class for dummy sensors"""
    def __init__(self, address):
        self.address = address
        logger.info(f"Dummy sensor initialized at address 0x{address:02x}")

class DummyENS160(DummySensor):
    """Built-in mock for ENS160 sensor"""
    def __init__(self, i2c, address=ENS160_ADDRESS):
        super().__init__(address)
        self._eco2 = 800
        self._tvoc = 250
        self._aqi = 2
    
    @property
    def eCO2(self):
        self._eco2 += random.randint(-25, 25)
        self._eco2 = max(400, min(self._eco2, 1500))
        return self._eco2
    
    @property
    def TVOC(self):
        self._tvoc += random.randint(-15, 15)
        self._tvoc = max(50, min(self._tvoc, 500))
        return self._tvoc
    
    @property
    def AQI(self):
        if random.random() < 0.05:
            self._aqi = random.randint(1, 5)
        return self._aqi

class DummyAHTx0(DummySensor):
    """Built-in mock for AHT21 sensor"""
    def __init__(self, i2c, address=AHT21_ADDRESS):
        super().__init__(address)
        self._temperature = 22.5
        self._humidity = 45.0
        
    @property
    def temperature(self):
        self._temperature += random.uniform(-0.3, 0.3)
        self._temperature = max(18.0, min(self._temperature, 28.0))
        return self._temperature
        
    @property
    def relative_humidity(self):
        self._humidity += random.uniform(-1.0, 1.0)
        self._humidity = max(30.0, min(self._humidity, 70.0))
        return self._humidity

class SensorService:
    """Service for environmental sensors"""
    
    def __init__(self):
        """Initialize the sensor service"""
        # Initialize variables
        self.sensor_available = False
        self.ens = None
        self.aht = None
        self.i2c = None
        self.running = False
        self.thread = None
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good'
        }
        # Default to mock sensors until we verify real hardware
        self.using_mock_sensors = True
    
    @ErrorHandler.handle_exception
    def start(self):
        """Initialize sensors and start update thread"""
        try:
            # Try to import and initialize real hardware
            try:
                # Try to initialize real sensors
                import board
                import busio
                import adafruit_ens160
                import adafruit_ahtx0
                
                # Try to initialize I2C
                try:
                    logger.info("Trying I2C with board.SCL/board.SDA")
                    self.i2c = busio.I2C(board.SCL, board.SDA)
                    self.using_mock_sensors = False
                except Exception as e1:
                    logger.warning(f"Standard I2C failed: {e1}")
                    try:
                        logger.info("Trying I2C with direct GPIO pins")
                        self.i2c = busio.I2C(3, 2)  # GPIO3=SCL, GPIO2=SDA
                        self.using_mock_sensors = False
                    except Exception as e2:
                        logger.warning(f"GPIO I2C failed: {e2}")
                        self.using_mock_sensors = True
                
                # Initialize sensors based on availability
                if not self.using_mock_sensors:
                    # Detect real I2C devices
                    self._scan_i2c()
                    
                    # Initialize real sensors
                    self.ens = adafruit_ens160.ENS160(self.i2c, address=ENS160_ADDRESS)
                    self.aht = adafruit_ahtx0.AHTx0(self.i2c, address=AHT21_ADDRESS)
                    logger.info("Real sensors initialized successfully")
                else:
                    raise ImportError("Failed to initialize real hardware")
            except ImportError as e:
                logger.info(f"Using mock sensors: {e}")
                self.using_mock_sensors = True
            
            # If we need to use mock sensors, initialize them
            if self.using_mock_sensors:
                logger.info("Initializing mock sensors")
                self.ens = DummyENS160(None)
                self.aht = DummyAHTx0(None)
            
            self.sensor_available = True
            
            # Initial reading
            self.update_readings()
            
            # Start background thread
            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            
            logger.info(f"Sensor service started successfully (mock mode: {self.using_mock_sensors})")
        except Exception as e:
            logger.error(f"Error initializing sensors: {e}")
            self.sensor_available = False
    
    def _scan_i2c(self):
        """Scan I2C bus and print detected devices"""
        if self.using_mock_sensors or not self.i2c:
            return
            
        try:
            logger.info("Scanning I2C bus for devices...")
            addresses = []
            
            for address in range(0x00, 0x80):
                try:
                    self.i2c.writeto(address, b'')
                    addresses.append(address)
                except Exception:
                    pass
            
            if addresses:
                logger.info(f"Found {len(addresses)} I2C devices at addresses:")
                for address in addresses:
                    logger.info(f"0x{address:02X}")
                    
                # Check for our sensors
                if ENS160_ADDRESS in addresses:
                    logger.info(f"ENS160 found at address 0x{ENS160_ADDRESS:02X}")
                else:
                    logger.warning(f"WARNING: ENS160 not found at address 0x{ENS160_ADDRESS:02X}")
                    
                if AHT21_ADDRESS in addresses:
                    logger.info(f"AHT21 found at address 0x{AHT21_ADDRESS:02X}")
                else:
                    logger.warning(f"WARNING: AHT21 not found at address 0x{AHT21_ADDRESS:02X}")
            else:
                logger.warning("No I2C devices found! Check your wiring")
        except Exception as e:
            logger.error(f"Error scanning I2C: {e}")
    
    def stop(self):
        """Stop the update thread and free resources"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("Sensor service stopped")
    
    def _background_update(self):
        """Background process for sensor data updates"""
        while self.running:
            try:
                self.update_readings()
            except Exception as e:
                logger.error(f"Error in background sensor update: {e}")
            # Pause between updates
            time.sleep(30)  # Update every 30 seconds
    
    @ErrorHandler.handle_exception
    def update_readings(self):
        """Update data from sensors"""
        if not self.sensor_available or not self.ens or not self.aht:
            return
            
        try:
            # Read ENS160
            self._readings['co2'] = self.ens.eCO2
            self._readings['tvoc'] = self.ens.TVOC
            
            # Convert AQI to text value
            aqi = self.ens.AQI
            self._readings['air_quality'] = AIR_QUALITY_LEVELS.get(aqi, f"Unknown ({aqi})")
            
            # Read AHT21
            self._readings['temperature'] = self.aht.temperature
            self._readings['humidity'] = self.aht.relative_humidity
            
            # Log readings periodically (at debug level to avoid log spam)
            logger.debug(f"Sensor readings: Temp={self._readings['temperature']:.1f}°C, "
                       f"Humidity={self._readings['humidity']:.1f}%, "
                       f"CO2={self._readings['co2']} ppm, "
                       f"TVOC={self._readings['tvoc']} ppb, "
                       f"Air Quality={self._readings['air_quality']}")
                  
        except Exception as e:
            logger.error(f"Error reading sensors: {e}")
    
    def get_readings(self):
        """Return the latest sensor readings"""
        return self._readings.copy()  # Return a copy to avoid threading issues