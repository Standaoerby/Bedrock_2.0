"""
Service for working with sensors (ENS160+AHT21+LDR)
FIXED: Inverted light sensor logic for proper theme switching
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
    """FIXED: Mock LDR with proper light/dark simulation"""
    def __init__(self):
        self._is_light = True
        self._last_change = time.time()
        self._change_counter = 0
    
    def read_digital(self):
        """FIXED: Simulate LDR with pull-up resistor behavior
        Real LDR: 0 (LOW) = bright light, 1 (HIGH) = dark/covered
        """
        current_hour = datetime.now().hour
        
        # Simulate day/night cycle: dark from 20:00 to 07:00
        if 7 <= current_hour < 20:
            base_is_light = True  # It's daytime
        else:
            base_is_light = False  # It's nighttime
        
        # Add random changes for testing
        if time.time() - self._last_change > random.randint(45, 120):  # Every 45-120 seconds
            if random.random() < 0.4:  # 40% chance to change for testing
                self._is_light = not base_is_light
                self._last_change = time.time()
                self._change_counter += 1
                
                # FIXED: Return inverted value (LDR with pull-up)
                # When light -> return 0 (LOW)
                # When dark -> return 1 (HIGH)
                gpio_value = 0 if self._is_light else 1
                
                logger.info(f"🔆 Mock LDR changed: {'Light' if self._is_light else 'Dark'} "
                           f"-> GPIO: {gpio_value} (change #{self._change_counter})")
                return gpio_value
        
        # FIXED: Return inverted value for normal operation
        gpio_value = 0 if base_is_light else 1
        return gpio_value

class SensorService:
    """Service for environmental sensors with FIXED light logic"""
    
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
        
        # FAST light switching configuration
        self._last_light_state = None
        self._light_change_threshold = 3  # seconds
        self._light_change_start = None
        self._light_readings_buffer = []
        self._buffer_size = 8
        self._stability_threshold = 0.7
        
        # GPIO setup with proper handle management
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        self._gpio_handles = []
        
        # Default to mock sensors until we verify real hardware
        self.using_mock_sensors = True
        
        # Debug counters
        self._debug_counter = 0
        self._last_debug_light = None
        self._change_detection_debug = 0
        
        # Fast switching parameters
        self._consecutive_same_readings = 0
        self._min_consecutive_for_change = 3
        self._change_confirmation_count = 0
        self._min_confirmations = 2
        
        # State tracking for debugging
        self._light_state_history = []
        self._max_history = 30
        
        # Fast switch settings
        self._fast_switch_enabled = True
        self._fast_switch_confidence = 0.85
        
        logger.info("🚀 SensorService initialized with FIXED light logic")
    
    @ErrorHandler.handle_exception
    def start(self):
        """Start the sensor service"""
        logger.info("Starting sensor service...")
        
        # Try to initialize real sensors first
        self._init_i2c_sensors()
        self._init_gpio_sensors()
        
        if not self.sensor_available and not self.gpio_available:
            logger.warning("No real sensors available, using mock sensors")
            self._init_mock_sensors()
        
        # Start sensor reading thread
        self.running = True
        self.thread = Thread(target=self._sensor_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Sensor service started - Real: {not self.using_mock_sensors}, Mock: {self.using_mock_sensors}")
        return True
    
    def _init_i2c_sensors(self):
        """Initialize I2C sensors (ENS160 + AHT21)"""
        try:
            # Try to import I2C libraries
            try:
                import board
                import busio
                import adafruit_ens160
                import adafruit_ahtx0
                
                # Initialize I2C
                i2c = busio.I2C(board.SCL, board.SDA)
                
                # Try to initialize sensors
                self.ens = adafruit_ens160.ENS160(i2c, address=ENS160_ADDRESS)
                self.aht = adafruit_ahtx0.AHTx0(i2c, address=AHT21_ADDRESS)
                
                # Test read to verify sensors work
                _ = self.ens.eCO2
                _ = self.aht.temperature
                
                self.sensor_available = True
                self.using_mock_sensors = False
                logger.info("✅ Real I2C sensors initialized successfully")
                
            except ImportError as e:
                logger.warning(f"I2C libraries not available: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize I2C sensors: {e}")
                
        except Exception as e:
            logger.error(f"Error in I2C sensor initialization: {e}")
    
    def _init_gpio_sensors(self):
        """Initialize GPIO sensors (LDR light sensor)"""
        try:
            # Try lgpio first (for Raspberry Pi 5)
            if LGPIO_AVAILABLE:
                try:
                    self.gpio_handle = lgpio.gpiochip_open(0)
                    lgpio.gpio_claim_input(self.gpio_handle, LDR_GPIO_PIN, lgpio.SET_PULL_UP)
                    
                    # Test read
                    _ = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info(f"✅ GPIO sensors initialized with lgpio (pin {LDR_GPIO_PIN})")
                    return
                    
                except Exception as e:
                    logger.warning(f"lgpio initialization failed: {e}")
                    if self.gpio_handle is not None:
                        try:
                            lgpio.gpiochip_close(self.gpio_handle)
                        except:
                            pass
                        self.gpio_handle = None
            
            # Fallback to RPi.GPIO
            if RPI_GPIO_AVAILABLE:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(LDR_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    
                    # Test read
                    _ = GPIO.input(LDR_GPIO_PIN)
                    
                    self.gpio_lib = "RPi.GPIO"
                    self.gpio_available = True
                    logger.info(f"✅ GPIO sensors initialized with RPi.GPIO (pin {LDR_GPIO_PIN})")
                    return
                    
                except Exception as e:
                    logger.warning(f"RPi.GPIO initialization failed: {e}")
                    try:
                        GPIO.cleanup()
                    except:
                        pass
            
            logger.warning("No GPIO library available for light sensor")
            
        except Exception as e:
            logger.error(f"Error in GPIO sensor initialization: {e}")
    
    def _init_mock_sensors(self):
        """Initialize mock sensors for development"""
        try:
            self.ens = DummyENS160(None)
            self.aht = DummyAHTx0(None)
            self.ldr = DummyLDR()
            
            self.sensor_available = True
            self.using_mock_sensors = True
            logger.info("✅ Mock sensors initialized with FIXED light logic")
            
        except Exception as e:
            logger.error(f"Error initializing mock sensors: {e}")
    
    def _sensor_loop(self):
        """Main sensor reading loop"""
        logger.info("Sensor reading loop started")
        
        while self.running:
            try:
                self._update_readings()
                time.sleep(1)  # Read every second
                
            except Exception as e:
                logger.error(f"Error in sensor loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _update_readings(self):
        """Update all sensor readings"""
        try:
            # Update I2C sensor readings
            if self.ens:
                try:
                    self._readings['co2'] = self.ens.eCO2
                    self._readings['tvoc'] = self.ens.TVOC
                    aqi_num = self.ens.AQI
                    self._readings['air_quality'] = AIR_QUALITY_LEVELS.get(aqi_num, "Unknown")
                except Exception as e:
                    logger.debug(f"Error reading ENS160: {e}")
            
            if self.aht:
                try:
                    self._readings['temperature'] = self.aht.temperature
                    self._readings['humidity'] = self.aht.relative_humidity
                except Exception as e:
                    logger.debug(f"Error reading AHT21: {e}")
            
            # Update light sensor readings
            self._update_light_readings()
            
            # Debug logging every 30 seconds
            self._debug_counter += 1
            if self._debug_counter % 30 == 0:
                logger.debug(f"Sensor readings: temp={self._readings['temperature']:.1f}°C, "
                           f"humidity={self._readings['humidity']:.1f}%, "
                           f"light={'Light' if self._readings['light_level'] else 'Dark'} "
                           f"(raw={self._readings['light_raw']})")
                
        except Exception as e:
            logger.error(f"Error updating readings: {e}")
    
    def _update_light_readings(self):
        """FIXED: Update light sensor readings with correct logic"""
        try:
            # Read raw light value from GPIO
            raw_value = self._read_light_sensor()
            self._readings['light_raw'] = raw_value
            
            # FIXED: Convert GPIO value to light level
            # LDR with pull-up: 0 = bright (light), 1 = dark/covered
            light_level = (raw_value == 0) if raw_value is not None else True
            
            # Add to buffer for stability checking
            self._light_readings_buffer.append(light_level)
            if len(self._light_readings_buffer) > self._buffer_size:
                self._light_readings_buffer.pop(0)
            
            # Calculate stable light level
            if len(self._light_readings_buffer) >= 3:
                light_count = sum(self._light_readings_buffer)
                total_count = len(self._light_readings_buffer)
                light_ratio = light_count / total_count
                
                # Use threshold to determine stable state
                if light_ratio >= self._stability_threshold:
                    stable_light = True  # Light
                elif light_ratio <= (1 - self._stability_threshold):
                    stable_light = False  # Dark
                else:
                    # Keep previous state if readings are too mixed
                    stable_light = self._readings['light_level']
                
                self._readings['light_level'] = stable_light
                
                # Debug logging for light changes
                if self._debug_counter % 15 == 0:  # Every 15 seconds
                    logger.debug(f"Light sensor: raw={raw_value}, "
                               f"level={'Light' if stable_light else 'Dark'}, "
                               f"ratio={light_ratio:.2f}, buffer={len(self._light_readings_buffer)}")
            else:
                self._readings['light_level'] = light_level
                
        except Exception as e:
            logger.error(f"Error updating light readings: {e}")
    
    def _read_light_sensor(self):
        """Read raw value from light sensor"""
        try:
            if self.ldr and self.using_mock_sensors:
                # Mock sensor
                return self.ldr.read_digital()
            elif self.gpio_available and not self.using_mock_sensors:
                # Real GPIO sensor
                if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                    return lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                elif self.gpio_lib == "RPi.GPIO":
                    return GPIO.input(LDR_GPIO_PIN)
            
            # Fallback - assume bright light
            return 0
            
        except Exception as e:
            logger.error(f"Error reading light sensor: {e}")
            return 0  # Default to bright
    
    # PUBLIC API METHODS
    
    def get_readings(self):
        """Get all current sensor readings"""
        return self._readings.copy()
    
    def get_light_level(self):
        """Get current light level as boolean (True=light, False=dark)"""
        return self._readings.get('light_level', True)
    
    def get_light_sensor_status(self):
        """Get detailed light sensor status"""
        return {
            'current_level': self._readings.get('light_level', True),
            'raw_value': self._readings.get('light_raw', 0),
            'gpio_available': self.gpio_available,
            'using_mock': self.using_mock_sensors,
            'change_pending': self._light_change_start is not None,
            'consecutive_readings': self._consecutive_same_readings,
            'buffer_size': len(self._light_readings_buffer),
            'stability_threshold': self._stability_threshold
        }
    
    def is_light_changed(self):
        """Check if light level has changed and is stable"""
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
            
            # Light level is different - check for fast switching
            self._consecutive_same_readings += 1
            
            # Fast switching check
            if self._fast_switch_enabled and len(self._light_readings_buffer) >= 5:
                valid_readings = [x for x in self._light_readings_buffer[-5:] if x is not None]
                if valid_readings:
                    target_count = sum(1 for x in valid_readings if x == current_light)
                    confidence = target_count / len(valid_readings)
                    
                    if confidence >= self._fast_switch_confidence:
                        # High confidence - switch quickly!
                        old_state = "Light" if self._last_light_state else "Dark"
                        new_state = "Light" if current_light else "Dark"
                        
                        self._last_light_state = current_light
                        self._light_change_start = None
                        self._consecutive_same_readings = 0
                        
                        logger.info(f"⚡ FAST LIGHT SWITCH: {old_state} → {new_state} (confidence: {confidence:.1%})")
                        return True
            
            # Need minimum consecutive different readings before starting timer
            if self._consecutive_same_readings < self._min_consecutive_for_change:
                if self._change_detection_debug % 5 == 0:
                    logger.debug(f"Light change detected but not stable yet "
                               f"({self._consecutive_same_readings}/{self._min_consecutive_for_change})")
                return False
            
            # Start change timer if not already started
            if self._light_change_start is None:
                self._light_change_start = time.time()
                old_state = "Light" if self._last_light_state else "Dark"
                new_state = "Light" if current_light else "Dark"
                logger.info(f"🔄 LIGHT CHANGE DETECTED: {old_state} → {new_state}")
                logger.info(f"Waiting {self._light_change_threshold}s for confirmation...")
                
                self._change_confirmation_count = 0
            
            # Check if change has been stable long enough
            elif time.time() - self._light_change_start >= self._light_change_threshold:
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
                    return True
                else:
                    logger.debug(f"Change confirmation {self._change_confirmation_count}/{self._min_confirmations}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error in is_light_changed: {e}")
            return False
    
    def calibrate_light_sensor(self, threshold_seconds=3):
        """Calibrate light sensor switching threshold"""
        try:
            old_threshold = self._light_change_threshold
            self._light_change_threshold = max(1, min(threshold_seconds, 8))
            logger.info(f"🔧 Light sensor threshold: {old_threshold}s → {self._light_change_threshold}s")
            
            # Adjust buffer size based on threshold
            if threshold_seconds <= 3:
                self._buffer_size = 6
                self._stability_threshold = 0.65
                logger.info(f"🚀 Fast mode enabled: buffer={self._buffer_size}, threshold={self._stability_threshold}")
            elif threshold_seconds <= 5:
                self._buffer_size = 8
                self._stability_threshold = 0.70
            else:
                self._buffer_size = 10
                self._stability_threshold = 0.75
                
        except Exception as e:
            logger.error(f"Error in calibrate_light_sensor: {e}")
    
    def set_fast_switching(self, enabled=True, confidence=0.85):
        """Enable/disable fast theme switching"""
        self._fast_switch_enabled = enabled
        self._fast_switch_confidence = confidence
        logger.info(f"Fast switching {'enabled' if enabled else 'disabled'} "
                   f"(confidence: {confidence:.1%})")
    
    def test_light_sensor(self, duration=15):
        """Test light sensor for specified duration"""
        if not self.sensor_available and not self.gpio_available:
            logger.error("No sensors available for testing")
            return
            
        logger.info(f"=== LIGHT SENSOR TEST ({duration}s) ===")
        logger.info("Cover and uncover the light sensor to test detection...")
        
        start_time = time.time()
        last_level = None
        
        while time.time() - start_time < duration:
            try:
                current_level = self.get_light_level()
                raw_value = self._readings.get('light_raw', 0)
                
                if current_level != last_level:
                    status = 'Light' if current_level else 'Dark'
                    sensor_type = 'Mock' if self.using_mock_sensors else 'Real'
                    logger.info(f"🔆 Light level: {status} (raw GPIO: {raw_value}, type: {sensor_type})")
                    last_level = current_level
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in light sensor test: {e}")
        
        logger.info("Light sensor test completed")
    
    def update_readings(self):
        """Force update of all sensor readings"""
        self._update_readings()
    
    def stop(self):
        """Stop the sensor service"""
        logger.info("Stopping sensor service...")
        
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # Cleanup GPIO
        try:
            if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None
            elif self.gpio_lib == "RPi.GPIO":
                GPIO.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")
        
        logger.info("Sensor service stopped")