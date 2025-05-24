"""
Service for working with sensors (ENS160+AHT21+LDR)
Supports real sensors on Raspberry Pi and mock sensors for development
ИСПРАВЛЕНО: Улучшена детекция изменений освещённости для автоматического переключения тем
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

# Configure logging
logger = logging.getLogger("SensorService")

# Define constants for I2C addresses
ENS160_ADDRESS = 0x53
AHT21_ADDRESS = 0x38

# GPIO pins for sensors
LDR_GPIO_PIN = 12  # Light sensor on GPIO 12

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
    """Enhanced mock for LDR light sensor with realistic day/night cycle"""
    def __init__(self):
        self._is_light = True
        self._last_change = time.time()
        self._change_probability = 0.02  # 2% chance per reading to change
        self._init_time = time.time()
    
    def read_digital(self):
        """Simulate light level changes with more realistic patterns"""
        current_hour = datetime.now().hour
        current_time = time.time()
        
        # Base light level on time of day
        # Light hours: 6 AM to 8 PM (14 hours)
        # Dark hours: 8 PM to 6 AM (10 hours)
        if 6 <= current_hour < 20:
            base_is_light = True
        else:
            base_is_light = False
        
        # Add random variation every 30-120 seconds for testing
        time_since_last_change = current_time - self._last_change
        min_change_interval = 30  # Minimum 30 seconds between changes
        max_change_interval = 120  # Maximum 120 seconds between changes
        
        # For testing, make changes more frequent
        if time_since_last_change > min_change_interval:
            # Probability increases over time
            time_factor = min(time_since_last_change / max_change_interval, 1.0)
            change_probability = self._change_probability * time_factor
            
            if random.random() < change_probability:
                # Sometimes override base light level for testing
                if random.random() < 0.3:  # 30% chance to override natural cycle
                    self._is_light = not base_is_light
                else:
                    self._is_light = base_is_light
                    
                self._last_change = current_time
                
                # Log significant changes
                state_name = 'Light' if self._is_light else 'Dark'
                logger.info(f"🌟 Mock LDR changed to: {state_name} (hour: {current_hour})")
                return self._is_light
        
        # Return current state or base state
        return self._is_light if hasattr(self, '_is_light') else base_is_light

class SensorService:
    """Service for environmental sensors with improved light change detection"""
    
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
        
        # Light sensor state tracking - УЛУЧШЕННАЯ СТАБИЛЬНОСТЬ
        self._last_light_state = None
        self._light_change_threshold = 5  # seconds to confirm change
        self._light_change_start = None
        self._light_readings_buffer = []  # Buffer for stable readings
        self._buffer_size = 15  # Increased buffer size for better stability
        self._stability_threshold = 0.8  # 80% of readings must agree (повышена стабильность)
        
        # GPIO setup with proper handle management
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        self._gpio_handles = []  # Track all handles for cleanup
        
        # Default to mock sensors until we verify real hardware
        self.using_mock_sensors = True
        
        # Debug counters
        self._debug_counter = 0
        self._last_debug_light = None
        self._change_detection_debug = 0
        
        # Enhanced stability measures
        self._consecutive_same_readings = 0
        self._min_consecutive_for_change = 5  # Need 5 consecutive different readings (увеличено)
        self._change_confirmation_count = 0  # Count confirmations
        self._min_confirmations = 3  # Need 3 confirmations
        
        # State tracking for debugging
        self._light_state_history = []
        self._max_history = 50
    
    @ErrorHandler.handle_exception
    def start(self):
        """Initialize sensors and start update thread"""
        try:
            logger.info(f"=== STARTING SENSOR SERVICE ===")
            logger.info(f"LDR sensor configured on GPIO pin {LDR_GPIO_PIN}")
            
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
                logger.info(f"Real LDR sensor available via GPIO pin {LDR_GPIO_PIN}")
                
                # Test initial reading and populate buffer
                self._initialize_light_buffer()
            else:
                self.ldr = DummyLDR()
                logger.info("Using enhanced mock LDR sensor with realistic patterns")
                # Initialize buffer with mock data
                for _ in range(self._buffer_size):
                    self._light_readings_buffer.append(self.ldr.read_digital())
            
            self.sensor_available = True
            
            # Initial reading
            self.update_readings()
            
            # Initialize light state properly
            initial_light = self.get_light_level()
            self._last_light_state = initial_light
            logger.info(f"Initial light state set: {'Light' if initial_light else 'Dark'}")
            
            # Start background thread
            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            
            logger.info(f"✅ Sensor service started successfully")
            logger.info(f"Mock mode: {self.using_mock_sensors}")
            logger.info(f"GPIO available: {self.gpio_available}")
            logger.info(f"Sensor available: {self.sensor_available}")
            
        except Exception as e:
            logger.error(f"Error initializing sensors: {e}")
            self.sensor_available = False
    
    def _initialize_light_buffer(self):
        """Initialize light sensor buffer with safe readings"""
        try:
            self._light_readings_buffer.clear()
            
            for i in range(self._buffer_size):
                reading = self._read_ldr_gpio_safe()
                if reading is not None:
                    self._light_readings_buffer.append(reading)
                else:
                    # Fallback to default if reading fails
                    self._light_readings_buffer.append(True)
                time.sleep(0.03)  # Small delay between readings
            
            if self._light_readings_buffer:
                stable_reading = self._get_stable_light_reading()
                light_count = sum(1 for x in self._light_readings_buffer if x)
                logger.info(f"Initial LDR buffer: {'Light' if stable_reading else 'Dark'} "
                           f"(confidence: {light_count}/{len(self._light_readings_buffer)})")
            else:
                logger.warning("Failed to initialize light sensor buffer")
        except Exception as e:
            logger.error(f"Error initializing light buffer: {e}")
            # Fill with default values
            self._light_readings_buffer = [True] * self._buffer_size
    
    def _init_gpio(self):
        """Initialize GPIO for LDR sensor with pull-up resistor"""
        try:
            logger.info(f"Initializing GPIO for LDR sensor on pin {LDR_GPIO_PIN} with pull-up resistor...")
            
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
                    if self.gpio_handle < 0:
                        raise Exception(f"Failed to open GPIO chip, handle: {self.gpio_handle}")
                    
                    self._gpio_handles.append(self.gpio_handle)  # Track handle
                    
                    # Claim the pin WITH pull-up resistor
                    result = lgpio.gpio_claim_input(self.gpio_handle, LDR_GPIO_PIN, lgpio.SET_PULL_UP)
                    if result < 0:
                        raise Exception(f"Failed to claim GPIO pin {LDR_GPIO_PIN}, result: {result}")
                    
                    # Test read to make sure it works
                    test_val = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                    if test_val < 0:
                        raise Exception(f"Failed to read GPIO pin {LDR_GPIO_PIN}, result: {test_val}")
                    
                    logger.info(f"GPIO test read successful: raw={test_val} (with pull-up)")
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info(f"✅ GPIO initialized with lgpio (pin {LDR_GPIO_PIN}, handle {self.gpio_handle})")
                    return
                    
                except Exception as e:
                    logger.error(f"lgpio initialization failed: {e}")
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
                    # Setup with pull-up resistor
                    GPIO.setup(LDR_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    
                    # Test read
                    test_val = GPIO.input(LDR_GPIO_PIN)
                    if test_val is None:
                        raise Exception("GPIO.input returned None")
                    
                    logger.info(f"GPIO test read successful: raw={test_val} (with pull-up)")
                    
                    self.gpio_lib = "RPi.GPIO"
                    self.gpio_available = True
                    logger.info(f"✅ GPIO initialized with RPi.GPIO (pin {LDR_GPIO_PIN})")
                    return
                    
                except Exception as e:
                    logger.error(f"RPi.GPIO initialization failed: {e}")
                    try:
                        GPIO.cleanup()
                    except:
                        pass
            else:
                logger.warning("RPi.GPIO not available")
            
            # No GPIO available
            logger.warning("No GPIO library available for LDR sensor - using enhanced mock")
            self.gpio_available = False
            
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            self.gpio_available = False
            self._cleanup_gpio_handles()
    
    def _read_ldr_gpio_safe(self):
        """Safe version of GPIO reading with proper error handling"""
        try:
            if not self.gpio_available:
                return None
                
            raw_value = None
            
            if self.gpio_lib == "lgpio" and LGPIO_AVAILABLE and self.gpio_handle is not None:
                raw_value = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                if raw_value < 0:  # lgpio returns negative on error
                    logger.error(f"lgpio.gpio_read returned error: {raw_value}")
                    return None
            elif self.gpio_lib == "RPi.GPIO" and RPI_GPIO_AVAILABLE:
                raw_value = GPIO.input(LDR_GPIO_PIN)
                if raw_value is None:
                    logger.error("GPIO.input returned None")
                    return None
            else:
                return None
            
            # Validate raw_value is a valid integer
            if not isinstance(raw_value, (int, bool)):
                logger.error(f"GPIO read returned invalid type: {type(raw_value)}, value: {raw_value}")
                return None
            
            # Convert to boolean and invert (LDR logic with pull-up)
            interpreted_value = not bool(raw_value)
            
            return interpreted_value
                
        except Exception as e:
            logger.error(f"Error in safe GPIO read: {e}")
            return None
    
    def _read_ldr_gpio(self):
        """Read LDR sensor value from GPIO and interpret correctly"""
        try:
            reading = self._read_ldr_gpio_safe()
            
            if reading is not None:
                # Debug output less frequently
                self._debug_counter += 1
                if self._debug_counter % 30 == 0 or reading != self._last_debug_light:
                    raw_val = 0 if reading else 1  # Show what the raw GPIO value would be
                    logger.debug(f"LDR GPIO{LDR_GPIO_PIN}: raw={raw_val} → {'Light' if reading else 'Dark'}")
                    self._last_debug_light = reading
            
            return reading
                
        except Exception as e:
            logger.error(f"Error reading LDR GPIO: {e}")
            return None
    
    def _get_stable_light_reading(self):
        """Get stable light reading using majority vote from buffer"""
        try:
            if not self._light_readings_buffer:
                return True  # Default to light
            
            # Filter out None values and count valid readings
            valid_readings = [x for x in self._light_readings_buffer if x is not None]
            
            if not valid_readings:
                return True  # Default to light if no valid readings
            
            # Count light vs dark readings
            light_count = sum(1 for x in valid_readings if x)
            total_count = len(valid_readings)
            
            # Use stability threshold (80% must agree)
            light_ratio = light_count / total_count
            
            if light_ratio >= self._stability_threshold:
                return True  # Light
            elif light_ratio <= (1 - self._stability_threshold):
                return False  # Dark
            else:
                # In uncertain zone, keep current state
                return self._readings.get('light_level', True)
        except Exception as e:
            logger.error(f"Error in _get_stable_light_reading: {e}")
            return True  # Default to light on error
    
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
                        if handle is not None and handle >= 0:
                            lgpio.gpiochip_close(handle)
                            logger.debug(f"Closed GPIO handle {handle}")
                    except Exception as e:
                        logger.debug(f"Error closing handle {handle}: {e}")
                self._gpio_handles.clear()
                self.gpio_handle = None
            elif self.gpio_lib == "RPi.GPIO" and RPI_GPIO_AVAILABLE:
                try:
                    GPIO.cleanup()
                    logger.debug("RPi.GPIO cleaned up")
                except Exception as e:
                    logger.debug(f"Error in GPIO cleanup: {e}")
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
            # Faster updates for better light change detection
            time.sleep(0.5)  # Update every 0.5 seconds
    
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
            
            # Read LDR sensor with improved stability
            if self.gpio_available:
                light_reading = self._read_ldr_gpio_safe()
                if light_reading is not None:
                    # Add to buffer for stability
                    self._light_readings_buffer.append(light_reading)
                    if len(self._light_readings_buffer) > self._buffer_size:
                        self._light_readings_buffer.pop(0)
                    
                    # Get stable reading using majority vote
                    stable_light = self._get_stable_light_reading()
                    
                    self._readings['light_raw'] = 1 if light_reading else 0
                    self._readings['light_level'] = stable_light
                    
                    # Track state history for debugging
                    self._light_state_history.append({
                        'time': time.time(),
                        'raw': light_reading,
                        'stable': stable_light
                    })
                    if len(self._light_state_history) > self._max_history:
                        self._light_state_history.pop(0)
                        
                else:
                    logger.debug(f"Failed to read LDR from GPIO pin {LDR_GPIO_PIN}")
            else:
                # Use mock LDR
                if self.ldr:
                    light_value = self.ldr.read_digital()
                    self._readings['light_raw'] = 1 if light_value else 0
                    self._readings['light_level'] = light_value
                    
                    # Track mock state too
                    self._light_state_history.append({
                        'time': time.time(),
                        'raw': light_value,
                        'stable': light_value
                    })
                    if len(self._light_state_history) > self._max_history:
                        self._light_state_history.pop(0)
            
            # Log comprehensive readings less frequently
            if self._debug_counter % 60 == 0:  # Every 30 seconds at 0.5s intervals
                buffer_info = "N/A"
                if self._light_readings_buffer:
                    valid_readings = [x for x in self._light_readings_buffer if x is not None]
                    light_count = sum(1 for x in valid_readings if x)
                    buffer_info = f"{light_count}/{len(valid_readings)}"
                
                logger.info(f"Sensor readings: Temp={self._readings['temperature']:.1f}°C, "
                           f"Humidity={self._readings['humidity']:.1f}%, "
                           f"CO2={self._readings['co2']} ppm, "
                           f"TVOC={self._readings['tvoc']} ppb, "
                           f"Air Quality={self._readings['air_quality']}, "
                           f"Light={'Light' if self._readings['light_level'] else 'Dark'} "
                           f"(GPIO{LDR_GPIO_PIN}, buffer={buffer_info})")
                  
        except Exception as e:
            logger.error(f"Error reading sensors: {e}")
    
    def get_readings(self):
        """Return the latest sensor readings"""
        return self._readings.copy()  # Return a copy to avoid threading issues
    
    def get_light_level(self):
        """Get current light level (True = light, False = dark)"""
        return self._readings.get('light_level', True)
    
    def is_light_changed(self):
        """Check if light level has changed and is stable - УЛУЧШЕННАЯ ЛОГИКА"""
        try:
            current_light = self.get_light_level()
            
            # Debug counter for change detection
            self._change_detection_debug += 1
            
            # If this is the first reading
            if self._last_light_state is None:
                self._last_light_state = current_light
                logger.info(f"🔆 Initial light state set: {'Light' if current_light else 'Dark'}")
                return False
            
            # If light level is the same as before
            if current_light == self._last_light_state:
                # Reset change tracking if it was running
                if self._light_change_start is not None:
                    self._light_change_start = None
                    logger.debug("Light change cancelled - returned to previous state")
                self._consecutive_same_readings = 0
                self._change_confirmation_count = 0
                return False
            
            # Light level is different - start stability checking
            self._consecutive_same_readings += 1
            
            # Need minimum consecutive different readings before starting timer
            if self._consecutive_same_readings < self._min_consecutive_for_change:
                if self._change_detection_debug % 10 == 0:  # Log every 10th check
                    logger.debug(f"Light change detected but not stable yet "
                               f"({self._consecutive_same_readings}/{self._min_consecutive_for_change})")
                return False
            
            # Start change timer if not already started
            if self._light_change_start is None:
                self._light_change_start = time.time()
                old_state = "Light" if self._last_light_state else "Dark"
                new_state = "Light" if current_light else "Dark"
                logger.info(f"🔄 STABLE LIGHT CHANGE DETECTED: {old_state} → {new_state}")
                logger.info(f"Waiting {self._light_change_threshold}s for final confirmation...")
                
                # Reset confirmation counter
                self._change_confirmation_count = 0
            
            # Check if change has been stable long enough
            elif time.time() - self._light_change_start >= self._light_change_threshold:
                # Need additional confirmations to be sure
                self._change_confirmation_count += 1
                
                if self._change_confirmation_count >= self._min_confirmations:
                    # Change is fully confirmed
                    old_state = "Light" if self._last_light_state else "Dark"
                    new_state = "Light" if current_light else "Dark"
                    
                    # Update state
                    self._last_light_state = current_light
                    self._light_change_start = None
                    self._consecutive_same_readings = 0
                    self._change_confirmation_count = 0
                    
                    logger.info(f"✅ LIGHT LEVEL CHANGE CONFIRMED: {old_state} → {new_state}")
                    logger.info(f"State history: {self._get_recent_state_summary()}")
                    
                    return True
                else:
                    logger.debug(f"Change confirmation {self._change_confirmation_count}/{self._min_confirmations}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error in is_light_changed: {e}")
            return False
    
    def _get_recent_state_summary(self):
        """Get summary of recent light state changes for debugging"""
        try:
            if not self._light_state_history:
                return "No history"
            
            # Get last 10 states
            recent = self._light_state_history[-10:]
            states = [('Light' if s['stable'] else 'Dark') for s in recent]
            
            # Count consecutive same states at the end
            if states:
                current_state = states[-1]
                consecutive = 1
                for i in range(len(states) - 2, -1, -1):
                    if states[i] == current_state:
                        consecutive += 1
                    else:
                        break
                
                return f"Last {len(states)} states: {' '.join(states)} (current: {consecutive} consecutive)"
            
            return "No states"
        except Exception as e:
            logger.error(f"Error getting state summary: {e}")
            return "Error"
    
    def calibrate_light_sensor(self, threshold_seconds=5):
        """Set the threshold for light change confirmation"""
        try:
            old_threshold = self._light_change_threshold
            self._light_change_threshold = max(2, min(threshold_seconds, 15))  # Clamp between 2-15 seconds
            logger.info(f"🔧 Light sensor threshold: {old_threshold}s → {self._light_change_threshold}s")
        except Exception as e:
            logger.error(f"Error in calibrate_light_sensor: {e}")
    
    def get_light_sensor_status(self):
        """Get detailed light sensor status for debugging"""
        try:
            valid_buffer = [x for x in self._light_readings_buffer if x is not None]
            light_count = sum(1 for x in valid_buffer if x) if valid_buffer else 0
            
            return {
                'current_level': self.get_light_level(),
                'raw_value': self._readings.get('light_raw', 0),
                'gpio_available': self.gpio_available,
                'gpio_lib': self.gpio_lib,
                'gpio_pin': LDR_GPIO_PIN,
                'using_mock': not self.gpio_available,
                'change_threshold': self._light_change_threshold,
                'buffer_size': len(self._light_readings_buffer),
                'buffer_light_count': light_count,
                'buffer_valid_count': len(valid_buffer),
                'stability_threshold': self._stability_threshold,
                'change_pending': self._light_change_start is not None,
                'consecutive_readings': self._consecutive_same_readings,
                'confirmation_count': self._change_confirmation_count,
                'last_light_state': self._last_light_state,
                'state_history_length': len(self._light_state_history)
            }
        except Exception as e:
            logger.error(f"Error in get_light_sensor_status: {e}")
            return {
                'current_level': True,
                'raw_value': 1,
                'gpio_available': False,
                'using_mock': True,
                'error': str(e)
            }
    
    def test_light_sensor(self, duration=15):
        """Test light sensor readings for debugging - УЛУЧШЕННЫЙ ТЕСТ"""
        try:
            if not self.gpio_available and not self.ldr:
                logger.error(f"No light sensor available for testing")
                return
                
            logger.info(f"🔬 TESTING LIGHT SENSOR FOR {duration} SECONDS")
            logger.info("Cover and uncover the sensor to see changes...")
            
            if self.gpio_available:
                logger.info(f"Using real LDR on GPIO pin {LDR_GPIO_PIN}")
            else:
                logger.info("Using mock LDR sensor")
            
            start_time = time.time()
            last_value = None
            change_count = 0
            
            while time.time() - start_time < duration:
                try:
                    # Use the appropriate reading method
                    if self.gpio_available:
                        interpreted = self._read_ldr_gpio_safe()
                        stable = self._get_stable_light_reading()
                    else:
                        interpreted = self.ldr.read_digital() if self.ldr else None
                        stable = interpreted
                    
                    if interpreted is not None:
                        if interpreted != last_value:
                            change_count += 1
                            status = 'Light' if interpreted else 'Dark'
                            stable_status = 'Light' if stable else 'Dark'
                            
                            # Buffer info
                            try:
                                valid_readings = [x for x in self._light_readings_buffer if x is not None]
                                light_count = sum(1 for x in valid_readings if x)
                                buffer_info = f"{light_count}/{len(valid_readings)}"
                            except:
                                buffer_info = "N/A"
                            
                            elapsed = time.time() - start_time
                            logger.info(f"[{elapsed:.1f}s] Change #{change_count}: "
                                       f"Raw={status}, Stable={stable_status}, Buffer={buffer_info}")
                            
                            # Check if this would trigger an auto theme change
                            if hasattr(self, 'is_light_changed'):
                                would_change = self.is_light_changed()
                                if would_change:
                                    logger.info("🎯 This change WOULD trigger auto theme switch!")
                            
                            last_value = interpreted
                    else:
                        if last_value is not None:  # Only log once
                            logger.warning(f"Failed to read sensor")
                            last_value = None
                    
                    time.sleep(0.3)  # Faster sampling for test
                    
                except KeyboardInterrupt:
                    logger.info("Test interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in light sensor test loop: {e}")
                    break
            
            logger.info(f"🏁 Light sensor test completed!")
            logger.info(f"Total changes detected: {change_count}")
            
            # Show final status
            try:
                status = self.get_light_sensor_status()
                logger.info(f"Final sensor status:")
                for key, value in status.items():
                    logger.info(f"  {key}: {value}")
            except Exception as e:
                logger.error(f"Error getting final status: {e}")
                
        except Exception as e:
            logger.error(f"Error in test_light_sensor: {e}")
            import traceback
            traceback.print_exc()