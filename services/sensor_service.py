"""
Service for working with environmental sensors (ENS160+AHT21)
Supports real sensors on Raspberry Pi and mock sensors for development
"""
import time
import os
import sys
import importlib.util
from threading import Thread
import logging

# Set up logging
logger = logging.getLogger("SensorService")

# Define constants for I2C addresses
ENS160_ADDRESS = 0x68
AHT21_ADDRESS = 0x38

# Air quality levels mapping
AIR_QUALITY_LEVELS = {
    1: "Excellent",
    2: "Good", 
    3: "Moderate",
    4: "Poor",
    5: "Unhealthy"
}

class HardwareDetector:
    """Utilities to detect and initialize hardware sensors"""
    
    @staticmethod
    def is_raspberry_pi():
        """Check if we're running on a Raspberry Pi"""
        try:
            # Check for Raspberry Pi-specific file
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read()
                return 'raspberry pi' in model.lower()
        except:
            # Check for ARM architecture as fallback
            return os.uname().machine.startswith('arm')
    
    @staticmethod
    def has_real_sensors():
        """Check if the real sensor libraries are available"""
        # Check if we should force mock mode via environment variable
        if os.environ.get('USE_MOCK_SENSORS') == '1':
            logger.info("Using mock sensors (forced by environment variable)")
            return False
            
        # Check if we're on a Pi first
        if not HardwareDetector.is_raspberry_pi():
            logger.info("Not running on Raspberry Pi, using mock sensors")
            return False
            
        # Check for required libraries
        required_libs = ['adafruit_ens160', 'adafruit_ahtx0', 'board', 'busio']
        for lib in required_libs:
            if importlib.util.find_spec(lib) is None:
                logger.warning(f"Required library {lib} not found, using mock sensors")
                return False
                
        # Check for I2C device
        if not os.path.exists('/dev/i2c-1'):
            logger.warning("I2C device not found, using mock sensors")
            return False
            
        logger.info("Real sensor hardware and libraries detected")
        return True
    
    @staticmethod
    def initialize_i2c():
        """Initialize I2C interface with proper error handling
        
        Returns:
            tuple: (i2c_interface, success_flag)
        """
        logger.info("Initializing I2C interface")
        
        # Try multiple initialization methods for different hardware configs
        try:
            import board
            import busio
            
            methods = [
                # Method 1: Traditional board with SCL/SDA pins
                lambda: (busio.I2C(board.SCL, board.SDA), "board.SCL/board.SDA"),
                
                # Method 2: Direct GPIO pin numbers (Raspberry Pi)
                lambda: (busio.I2C(board.D3, board.D2), "GPIO pins 3 and 2"),
                
                # Method 3: Use generic I2C device 
                lambda: (HardwareDetector._get_generic_i2c(), "generic I2C device")
            ]
            
            # Try each method
            for i, (method, desc) in enumerate(methods, 1):
                try:
                    logger.info(f"Trying I2C Method {i}: {desc}")
                    i2c = method()
                    if i2c:
                        logger.info(f"I2C initialized successfully using {desc}")
                        return i2c, True
                except Exception as e:
                    logger.warning(f"Method {i} failed: {e}")
            
            logger.error("All I2C initialization methods failed")
            return None, False
            
        except ImportError as e:
            logger.error(f"Required libraries not available: {e}")
            return None, False
    
    @staticmethod
    def _get_generic_i2c():
        """Try to get a generic I2C interface (method 3)"""
        try:
            from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
            return I2C(1)  # /dev/i2c-1
        except:
            return None
    
    @staticmethod
    def scan_i2c(i2c):
        """Scan I2C bus for devices and log found addresses"""
        if not i2c:
            logger.warning("Cannot scan I2C: no interface provided")
            return []
            
        logger.info("Scanning I2C bus for devices...")
        devices = []
        
        try:
            for address in range(0x00, 0x80):
                try:
                    i2c.writeto(address, b'')
                    devices.append(address)
                except Exception:
                    pass
            
            if devices:
                logger.info(f"Found {len(devices)} I2C devices at addresses: " + 
                            ", ".join([f"0x{addr:02X}" for addr in devices]))
                
                # Check for our sensors
                if ENS160_ADDRESS in devices:
                    logger.info(f"ENS160 found at address 0x{ENS160_ADDRESS:02X}")
                else:
                    logger.warning(f"ENS160 not found at address 0x{ENS160_ADDRESS:02X}")
                    
                if AHT21_ADDRESS in devices:
                    logger.info(f"AHT21 found at address 0x{AHT21_ADDRESS:02X}")
                else:
                    logger.warning(f"AHT21 not found at address 0x{AHT21_ADDRESS:02X}")
            else:
                logger.warning("No I2C devices found! Check your wiring")
                
        except Exception as e:
            logger.error(f"Error scanning I2C: {e}")
            
        return devices

class MockSensors:
    """Mock sensor implementations for development and testing"""
    
    class I2C:
        """Mock I2C interface"""
        def __init__(self, scl, sda):
            logger.info(f"Mock I2C initialized (SCL: {scl}, SDA: {sda})")
            
        def writeto(self, address, data):
            """Mock write to I2C device"""
            pass
    
    class ENS160:
        """Mock ENS160 sensor (CO2, TVOC, AQI)"""
        def __init__(self, i2c, address=ENS160_ADDRESS):
            self._eco2 = 800  # ppm, normal level
            self._tvoc = 250  # ppb, normal level
            self._aqi = 2     # Good (1-5)
            logger.info(f"Mock ENS160 initialized at address 0x{address:02X}")
        
        @property
        def eCO2(self):
            """Equivalent CO2 in ppm"""
            import random
            # Add random variation to simulate live data
            self._eco2 += random.randint(-25, 25)
            # Keep within realistic range
            self._eco2 = max(400, min(self._eco2, 1500))
            return self._eco2
        
        @property
        def TVOC(self):
            """Total Volatile Organic Compounds in ppb"""
            import random
            self._tvoc += random.randint(-15, 15)
            self._tvoc = max(50, min(self._tvoc, 500))
            return self._tvoc
        
        @property
        def AQI(self):
            """Air Quality Index (1-5)"""
            import random
            # Occasionally change AQI to simulate air quality changes
            if random.random() < 0.05:  # 5% chance
                self._aqi = random.randint(1, 5)
            return self._aqi
    
    class AHTx0:
        """Mock AHT21 sensor (temperature and humidity)"""
        def __init__(self, i2c, address=AHT21_ADDRESS):
            self._temperature = 22.5  # °C
            self._humidity = 45.0     # %
            logger.info(f"Mock AHT21 initialized at address 0x{address:02X}")
            
        @property
        def temperature(self):
            """Temperature in Celsius"""
            import random
            # Small random changes in temperature
            self._temperature += random.uniform(-0.3, 0.3)
            # Keep within realistic home range
            self._temperature = max(18.0, min(self._temperature, 28.0))
            return self._temperature
            
        @property
        def relative_humidity(self):
            """Relative humidity in percentage"""
            import random
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
        
        # Default readings
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good'
        }
        
        # Detect hardware
        self.use_real_sensors = HardwareDetector.has_real_sensors()
        
        # Public flag for UI to check
        self.using_mock_sensors = not self.use_real_sensors
        
        # Log hardware detection result
        if self.use_real_sensors:
            logger.info("Using real sensor hardware")
        else:
            logger.info("Using mock sensors")
    
    def start(self):
        """Initialize sensors and start update thread"""
        try:
            # Initialize sensors
            if self.use_real_sensors:
                self._initialize_real_sensors()
            else:
                self._initialize_mock_sensors()
                
            # Initial readings
            self.update_readings()
            
            # Start background thread
            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            
            logger.info("Sensor service started successfully")
            
        except Exception as e:
            logger.error(f"Error initializing sensors: {e}", exc_info=True)
            self.sensor_available = False
            self.using_mock_sensors = True
    
    def _initialize_real_sensors(self):
        """Initialize real hardware sensors"""
        try:
            # Get I2C interface
            self.i2c, success = HardwareDetector.initialize_i2c()
            if not success or not self.i2c:
                logger.error("Failed to initialize I2C, falling back to mock sensors")
                self._initialize_mock_sensors()
                return
                
            # Scan for devices
            devices = HardwareDetector.scan_i2c(self.i2c)
            
            # Import sensor libraries
            import adafruit_ens160
            import adafruit_ahtx0
            
            # Initialize sensors
            self.ens = adafruit_ens160.ENS160(self.i2c, address=ENS160_ADDRESS)
            self.aht = adafruit_ahtx0.AHTx0(self.i2c, address=AHT21_ADDRESS)
            
            # Set flag based on presence of expected devices
            self.sensor_available = (ENS160_ADDRESS in devices and AHT21_ADDRESS in devices)
            
            if not self.sensor_available:
                logger.warning("Not all sensors were found on I2C bus")
                
        except Exception as e:
            logger.error(f"Error initializing real sensors: {e}", exc_info=True)
            # Fall back to mock sensors
            self._initialize_mock_sensors()
    
    def _initialize_mock_sensors(self):
        """Initialize mock sensors for development"""
        try:
            # Create mock interface and sensors
            self.i2c = MockSensors.I2C("SCL", "SDA")
            self.ens = MockSensors.ENS160(self.i2c, address=ENS160_ADDRESS)
            self.aht = MockSensors.AHTx0(self.i2c, address=AHT21_ADDRESS)
            
            # Even with mocks, sensors are available
            self.sensor_available = True
            self.using_mock_sensors = True
            
            logger.info("Mock sensors initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing mock sensors: {e}", exc_info=True)
            self.sensor_available = False
    
    def stop(self):
        """Stop the update thread and free resources"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # Clean up resources
        self.ens = None
        self.aht = None
        self.i2c = None
        
        logger.info("Sensor service stopped")
    
    def _background_update(self):
        """Background process for sensor data updates"""
        while self.running:
            try:
                self.update_readings()
            except Exception as e:
                logger.error(f"Error in background sensor update: {e}")
            
            # Wait between updates
            time.sleep(30)  # Update every 30 seconds
    
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


# Simple self-test if file is run directly
if __name__ == "__main__":
    # Configure logging for standalone test
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Sensor Service - Self Test")
    service = SensorService()
    service.start()
    
    try:
        # Display readings for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            readings = service.get_readings()
            print(f"\rTemp: {readings['temperature']:.1f}°C, "
                  f"Humidity: {readings['humidity']:.1f}%, "
                  f"CO2: {readings['co2']} ppm, "
                  f"TVOC: {readings['tvoc']} ppb, "
                  f"Quality: {readings['air_quality']}", end="")
            time.sleep(1)
        print("\nTest complete")
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        service.stop()