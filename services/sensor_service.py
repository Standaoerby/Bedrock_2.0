"""
Service for working with sensors (ENS160+AHT21+LDR)
Supports real sensors on Raspberry Pi and mock sensors for development
"""
import time
import os
import sys
from threading import Thread
import logging
import random
from datetime import datetime
from utils.error_handler import ErrorHandler

# Global GPIO imports with error handling
try:
    import lgpio
    LGPIO_AVAILABLE = True
except ImportError:
    LGPIO_AVAILABLE = False
    lgpio = None

try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True  
except ImportError:
    RPI_GPIO_AVAILABLE = False
    GPIO = None

# Global GPIO imports with error handling
try:
    import lgpio
    LGPIO_AVAILABLE = True
except ImportError:
    LGPIO_AVAILABLE = False
    lgpio = None

try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True  
except ImportError:
    RPI_GPIO_AVAILABLE = False
    GPIO = None

# Global GPIO imports with error handling
try:
    import lgpio
    LGPIO_AVAILABLE = True
except ImportError:
    LGPIO_AVAILABLE = False
    lgpio = None

try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True  
except ImportError:
    RPI_GPIO_AVAILABLE = False
    GPIO = None

# Configure logging
logger = logging.getLogger("SensorService")

# Define constants for I2C addresses
ENS160_ADDRESS = 0x53
AHT21_ADDRESS = 0x38

# GPIO pins for new sensors
LDR_GPIO_PIN = 18

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

class DummyLDR:
    """Built-in mock for LDR light sensor"""
    def __init__(self):
        """Initialize the sensor service"""
        # Initialize variables
        self.sensor_available = False
        self.ens = None
        self.aht = None
        self.ldr = None
        self.i2c = None
        self.running = False
        self.thread = None
        
        # Sensor readings
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good',
            'light_level': True,  # True = light, False = dark
            'light_raw': 1        # Raw digital value from sensor
        }
        
        # Light sensor state tracking
        self._last_light_state = None
        self._light_change_threshold = 2  # seconds to confirm change
        self._light_change_start = None
        
        # GPIO setup with proper handle management
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        self._gpio_handles = []  # Track all handles for cleanup
        
        # Default to mock sensors until we verify real hardware
        self.using_mock_sensors = True
    def read_digital(self):
        """Simulate light level changes based on time of day"""
        current_hour = datetime.now().hour
        
        # Simulate day/night cycle: dark from 20:00 to 07:00
        if 7 <= current_hour < 20:
            base_is_light = True
        else:
            base_is_light = False
            
        # Add some random variation
        if time.time() - self._last_change > 30:  # Change every 30 seconds for testing
            if random.random() < 0.1:  # 10% chance to flip
                self._is_light = not self._is_light
                self._last_change = time.time()
                logger.debug(f"Mock LDR changed to: {'Light' if self._is_light else 'Dark'}")
        
        return base_is_light if random.random() > 0.05 else self._is_light

class SensorService:
    """Service for environmental sensors"""
    
    def __init__(self):
        """Initialize the sensor service"""
        # Initialize variables
        self.sensor_available = False
        self.ens = None
        self.aht = None
        self.ldr = None
        self.i2c = None
        self.running = False
        self.thread = None
        
        # Sensor readings
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good',
            'light_level': True,  # True = light, False = dark
            'light_raw': 1        # Raw digital value from sensor
        }
        
        # Light sensor state tracking
        self._last_light_state = None
        self._light_change_threshold = 2  # seconds to confirm change
        self._light_change_start = None
        
        # GPIO setup with proper handle management
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        self._gpio_handles = []  # Track all handles for cleanup
        
        # Default to mock sensors until we verify real hardware
        self.using_mock_sensors = True
    @ErrorHandler.handle_exception
    def start(self):
        """Initialize sensors and start update thread"""
        try:
            # Initialize GPIO first
            self._init_gpio()
            
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
                    logger.info("Real I2C sensors initialized successfully")
                else:
                    raise ImportError("Failed to initialize real I2C hardware")
                    
            except ImportError as e:
                logger.info(f"Using mock I2C sensors: {e}")
                self.using_mock_sensors = True
            
            # If we need to use mock sensors, initialize them
            if self.using_mock_sensors:
                logger.info("Initializing mock I2C sensors")
                self.ens = DummyENS160(None)
                self.aht = DummyAHTx0(None)
            
            # Initialize LDR sensor (GPIO-based)
            if self.gpio_available:
                self.ldr = None  # Real LDR uses GPIO directly
                logger.info("Real LDR sensor available via GPIO")
            else:
                self.ldr = DummyLDR()
                logger.info("Using mock LDR sensor")
            
            self.sensor_available = True
            
            # Initial reading
            self.update_readings()
            
            # Start background thread
            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            
            logger.info(f"Sensor service started successfully (mock mode: {self.using_mock_sensors}, GPIO: {self.gpio_available})")
        except Exception as e:
            logger.error(f"Error initializing sensors: {e}")
            self.sensor_available = False
    
    def _init_gpio(self):
        """Initialize GPIO for LDR sensor with proper handle management"""
        try:
            logger.info("Initializing GPIO for LDR sensor...")
            
            # Clean up any existing handles first
            self._cleanup_gpio_handles()
            
            # Kill any existing GPIO processes that might be holding pins
            import subprocess
            try:
                subprocess.run(['sudo', 'pkill', '-f', 'gpio'], capture_output=True, timeout=5)
                time.sleep(0.5)
            except:
                pass
            
            # Try lgpio first (preferred for Pi 5)
            if LGPIO_AVAILABLE:
                try:
                    logger.info("Trying lgpio initialization...")
                    
                    # Open GPIO chip
                    self.gpio_handle = lgpio.gpiochip_open(0)
                    self._gpio_handles.append(self.gpio_handle)  # Track handle
                    
                    # Claim the pin
                    lgpio.gpio_claim_input(self.gpio_handle, LDR_GPIO_PIN)
                    
                    # Test read to make sure it works
                    test_val = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                    logger.info(f"GPIO test read successful: {test_val}")
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info(f"✓ GPIO initialized with lgpio (pin {LDR_GPIO_PIN}, handle {self.gpio_handle})")
                    return
                    
                except Exception as e:
                    logger.warning(f"lgpio initialization failed: {e}")
                    self._cleanup_gpio_handles()
            else:
                logger.info("lgpio not available, trying RPi.GPIO")
            
            # Fallback to RPi.GPIO
            if RPI_GPIO_AVAILABLE:
                try:
                    logger.info("Trying RPi.GPIO initialization...")
                    
                    # Clean up any existing setup
                    GPIO.cleanup()
                    time.sleep(0.2)
                    
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(LDR_GPIO_PIN, GPIO.IN)
                    
                    # Test read
                    test_val = GPIO.input(LDR_GPIO_PIN)
                    logger.info(f"GPIO test read successful: {test_val}")
                    
                    self.gpio_lib = "RPi.GPIO"
                    self.gpio_available = True
                    logger.info(f"✓ GPIO initialized with RPi.GPIO (pin {LDR_GPIO_PIN})")
                    return
                    
                except Exception as e:
                    logger.warning(f"RPi.GPIO initialization failed: {e}")
                    try:
                        GPIO.cleanup()
                    except:
                        pass
            else:
                logger.warning("RPi.GPIO not available")
            
            # No GPIO available
            logger.warning("No GPIO library available for LDR sensor - using mock")
            self.gpio_available = False
            
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            self.gpio_available = False
            self._cleanup_gpio_handles()
    def _read_ldr_gpio(self):
        """Read LDR sensor value from GPIO"""
        try:
            if not self.gpio_available:
                return None
                
            if self.gpio_lib == "lgpio" and LGPIO_AVAILABLE:
                value = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                return bool(value)
            elif self.gpio_lib == "RPi.GPIO" and RPI_GPIO_AVAILABLE:
                value = GPIO.input(LDR_GPIO_PIN)
                return bool(value)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error reading LDR GPIO: {e}")
            return None
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
    
    def _cleanup_gpio_handles(self):
        """Clean up all GPIO handles properly"""
        try:
            if self.gpio_lib == "lgpio" and LGPIO_AVAILABLE:
                # Close all tracked handles
                for handle in self._gpio_handles:
                    try:
                        lgpio.gpiochip_close(handle)
                        logger.debug(f"Closed GPIO handle {handle}")
                    except:
                        pass
                self._gpio_handles.clear()
                self.gpio_handle = None
            elif self.gpio_lib == "RPi.GPIO" and RPI_GPIO_AVAILABLE:
                try:
                    GPIO.cleanup()
                    logger.debug("RPi.GPIO cleaned up")
                except:
                    pass
        except Exception as e:
            logger.error(f"Error cleaning up GPIO handles: {e}")
    def _cleanup_gpio_handles(self):
        """Clean up all GPIO handles properly"""
        try:
            if self.gpio_lib == "lgpio" and LGPIO_AVAILABLE:
                # Close all tracked handles
                for handle in self._gpio_handles:
                    try:
                        lgpio.gpiochip_close(handle)
                        logger.debug(f"Closed GPIO handle {handle}")
                    except:
                        pass
                self._gpio_handles.clear()
                self.gpio_handle = None
            elif self.gpio_lib == "RPi.GPIO" and RPI_GPIO_AVAILABLE:
                try:
                    GPIO.cleanup()
                    logger.debug("RPi.GPIO cleaned up")
                except:
                    pass
        except Exception as e:
            logger.error(f"Error cleaning up GPIO handles: {e}")
    def stop(self):
        """Stop the update thread and free resources"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        # Cleanup GPIO with improved method
        self._cleanup_gpio_handles()
            
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
            
            # Read LDR sensor
            if self.gpio_available:
                light_raw = self._read_ldr_gpio()
                if light_raw is not None:
                    self._readings['light_raw'] = int(light_raw)
                    self._readings['light_level'] = light_raw
            else:
                # Use mock LDR
                if self.ldr:
                    light_value = self.ldr.read_digital()
                    self._readings['light_raw'] = int(light_value)
                    self._readings['light_level'] = light_value
            
            # Log readings periodically (at debug level to avoid log spam)
            logger.debug(f"Sensor readings: Temp={self._readings['temperature']:.1f}°C, "
                       f"Humidity={self._readings['humidity']:.1f}%, "
                       f"CO2={self._readings['co2']} ppm, "
                       f"TVOC={self._readings['tvoc']} ppb, "
                       f"Air Quality={self._readings['air_quality']}, "
                       f"Light={'Light' if self._readings['light_level'] else 'Dark'}")
                  
        except Exception as e:
            logger.error(f"Error reading sensors: {e}")
    
    def get_readings(self):
        """Return the latest sensor readings"""
        return self._readings.copy()  # Return a copy to avoid threading issues
    
    def get_light_level(self):
        """Get current light level (True = light, False = dark)"""
        return self._readings.get('light_level', True)
    
    def is_light_changed(self):
        """Check if light level has changed and is stable"""
        current_light = self.get_light_level()
        
        # If this is the first reading
        if self._last_light_state is None:
            self._last_light_state = current_light
            return False
        
        # If light level is different
        if current_light != self._last_light_state:
            # Start change timer if not already started
            if self._light_change_start is None:
                self._light_change_start = time.time()
                logger.debug(f"Light change detected: {self._last_light_state} -> {current_light}")
            
            # Check if change has been stable long enough
            elif time.time() - self._light_change_start >= self._light_change_threshold:
                # Change is confirmed
                self._last_light_state = current_light
                self._light_change_start = None
                logger.info(f"Light level changed to: {'Light' if current_light else 'Dark'}")
                return True
        else:
            # Light level returned to previous state, cancel change
            if self._light_change_start is not None:
                self._light_change_start = None
                logger.debug("Light change cancelled - returned to previous state")
        
        return False
    
    def calibrate_light_sensor(self, threshold_seconds=2):
        """Set the threshold for light change confirmation"""
        self._light_change_threshold = threshold_seconds
        logger.info(f"Light sensor threshold set to {threshold_seconds} seconds")
    
    def get_light_sensor_status(self):
        """Get detailed light sensor status for debugging"""
        return {
            'current_level': self.get_light_level(),
            'raw_value': self._readings.get('light_raw', 0),
            'gpio_available': self.gpio_available,
            'gpio_lib': self.gpio_lib,
            'using_mock': not self.gpio_available,
            'change_threshold': self._light_change_threshold
        }