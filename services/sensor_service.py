"""
Упрощенный сервис для работы с датчиками
"""
import time
import os
import random
from threading import Thread
import logging
from datetime import datetime

# GPIO imports with error handling
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

logger = logging.getLogger("SensorService")

# Constants
ENS160_ADDRESS = 0x53
AHT21_ADDRESS = 0x38
LDR_GPIO_PIN = 12

AIR_QUALITY_LEVELS = {
    1: "Excellent", 2: "Good", 3: "Moderate", 4: "Poor", 5: "Unhealthy"
}

class DummyENS160:
    """Simple mock for ENS160 sensor"""
    def __init__(self, i2c, address=ENS160_ADDRESS):
        self._eco2 = 800
        self._tvoc = 250
        self._aqi = 2
    
    @property
    def eCO2(self):
        self._eco2 += random.randint(-20, 20)
        return max(400, min(self._eco2, 1200))
    
    @property
    def TVOC(self):
        self._tvoc += random.randint(-10, 10)
        return max(50, min(self._tvoc, 400))
    
    @property
    def AQI(self):
        if random.random() < 0.1:
            self._aqi = random.randint(1, 3)
        return self._aqi

class DummyAHTx0:
    """Simple mock for AHT21 sensor"""
    def __init__(self, i2c, address=AHT21_ADDRESS):
        self._temperature = 22.5
        self._humidity = 45.0
        
    @property
    def temperature(self):
        self._temperature += random.uniform(-0.2, 0.2)
        return max(18.0, min(self._temperature, 28.0))
        
    @property
    def relative_humidity(self):
        self._humidity += random.uniform(-0.5, 0.5)
        return max(30.0, min(self._humidity, 70.0))

class DummyLDR:
    """Simple mock LDR with day/night simulation"""
    def __init__(self):
        self._manual_override = None
        self._last_change = time.time()
    
    def read_digital(self):
        """Read digital value: 0 = light, 1 = dark"""
        # Manual override for testing
        if self._manual_override is not None:
            return 0 if self._manual_override else 1
        
        # Day/night simulation: light 6:00-22:00
        current_hour = datetime.now().hour
        if 6 <= current_hour < 22:
            base_is_light = True
        else:
            base_is_light = False
        
        # Occasional random changes for testing
        if time.time() - self._last_change > random.randint(120, 300):
            if random.random() < 0.3:
                self._last_change = time.time()
                return 0 if not base_is_light else 1  # Flip for testing
        
        return 0 if base_is_light else 1
    
    def force_state(self, is_light):
        """Force sensor state for testing"""
        self._manual_override = is_light
        logger.info(f"LDR forced to: {'Light' if is_light else 'Dark'}")

class SensorService:
    """Simplified sensor service for environmental monitoring"""
    
    def __init__(self):
        self.sensor_available = False
        self.gpio_available = False
        self.using_mock_sensors = True
        
        # Sensors
        self.ens = None
        self.aht = None
        self.ldr = None
        self.i2c = None
        
        # GPIO
        self.gpio_lib = None
        self.gpio_handle = None
        
        # Threading
        self.running = False
        self.thread = None
        
        # Readings
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good',
            'light_level': True,  # True = light, False = dark
            'light_raw': 1
        }
        
        # Light sensor state
        self._last_light_state = None
        self._light_readings = []
        self._switch_threshold = 3  # seconds
        self._confidence_level = 0.8
        
        logger.info("SensorService initialized")
    
    def start(self):
        """Start the sensor service"""
        logger.info("Starting sensor service...")
        
        # Try to initialize real sensors
        self._init_i2c_sensors()
        self._init_gpio_sensors()
        
        # Fall back to mock sensors
        if not self.sensor_available and not self.gpio_available:
            self._init_mock_sensors()
        
        # Start reading thread
        self.running = True
        self.thread = Thread(target=self._sensor_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Sensor service started - Mock: {self.using_mock_sensors}")
        return True
    
    def _init_i2c_sensors(self):
        """Initialize I2C sensors"""
        try:
            import board
            import busio
            import adafruit_ens160
            import adafruit_ahtx0
            
            i2c = busio.I2C(board.SCL, board.SDA)
            self.ens = adafruit_ens160.ENS160(i2c, address=ENS160_ADDRESS)
            self.aht = adafruit_ahtx0.AHTx0(i2c, address=AHT21_ADDRESS)
            
            # Test read
            _ = self.ens.eCO2
            _ = self.aht.temperature
            
            self.sensor_available = True
            self.using_mock_sensors = False
            logger.info("Real I2C sensors initialized")
            
        except Exception as e:
            logger.warning(f"I2C sensors not available: {e}")
    
    def _init_gpio_sensors(self):
        """Initialize GPIO sensors"""
        try:
            # Try lgpio first
            if LGPIO_AVAILABLE:
                try:
                    self.gpio_handle = lgpio.gpiochip_open(0)
                    lgpio.gpio_claim_input(self.gpio_handle, LDR_GPIO_PIN, lgpio.SET_PULL_UP)
                    _ = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info(f"GPIO sensors initialized with lgpio")
                    return
                except Exception as e:
                    logger.warning(f"lgpio failed: {e}")
                    if self.gpio_handle:
                        try:
                            lgpio.gpiochip_close(self.gpio_handle)
                        except:
                            pass
                        self.gpio_handle = None
            
            # Try RPi.GPIO
            if RPI_GPIO_AVAILABLE:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(LDR_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    _ = GPIO.input(LDR_GPIO_PIN)
                    
                    self.gpio_lib = "RPi.GPIO"
                    self.gpio_available = True
                    logger.info(f"GPIO sensors initialized with RPi.GPIO")
                    return
                except Exception as e:
                    logger.warning(f"RPi.GPIO failed: {e}")
                    try:
                        GPIO.cleanup()
                    except:
                        pass
            
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
    
    def _init_mock_sensors(self):
        """Initialize mock sensors"""
        try:
            self.ens = DummyENS160(None)
            self.aht = DummyAHTx0(None)
            self.ldr = DummyLDR()
            
            self.sensor_available = True
            self.using_mock_sensors = True
            logger.info("Mock sensors initialized")
            
        except Exception as e:
            logger.error(f"Error initializing mock sensors: {e}")
    
    def _sensor_loop(self):
        """Main sensor reading loop"""
        while self.running:
            try:
                self._update_readings()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in sensor loop: {e}")
                time.sleep(5)
    
    def _update_readings(self):
        """Update all sensor readings"""
        try:
            # Update I2C sensors
            if self.ens:
                try:
                    self._readings['co2'] = self.ens.eCO2
                    self._readings['tvoc'] = self.ens.TVOC
                    aqi_num = self.ens.AQI
                    self._readings['air_quality'] = AIR_QUALITY_LEVELS.get(aqi_num, "Unknown")
                except Exception:
                    pass
            
            if self.aht:
                try:
                    self._readings['temperature'] = self.aht.temperature
                    self._readings['humidity'] = self.aht.relative_humidity
                except Exception:
                    pass
            
            # Update light sensor
            raw_value = self._read_light_sensor()
            self._readings['light_raw'] = raw_value
            
            # Convert GPIO to light level (0 = light, 1 = dark)
            light_level = (raw_value == 0) if raw_value is not None else True
            
            # Simple smoothing
            self._light_readings.append(light_level)
            if len(self._light_readings) > 5:
                self._light_readings.pop(0)
            
            # Calculate stable light level
            if len(self._light_readings) >= 3:
                light_count = sum(self._light_readings)
                light_ratio = light_count / len(self._light_readings)
                
                if light_ratio >= 0.7:
                    self._readings['light_level'] = True  # Light
                elif light_ratio <= 0.3:
                    self._readings['light_level'] = False  # Dark
                # Else keep previous state
            
        except Exception as e:
            logger.error(f"Error updating readings: {e}")
    
    def _read_light_sensor(self):
        """Read light sensor value"""
        try:
            if self.ldr and self.using_mock_sensors:
                return self.ldr.read_digital()
            elif self.gpio_available:
                if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                    return lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                elif self.gpio_lib == "RPi.GPIO":
                    return GPIO.input(LDR_GPIO_PIN)
            
            return 0  # Default to light
        except Exception:
            return 0
    
    def get_readings(self):
        """Get all current sensor readings"""
        return self._readings.copy()
    
    def get_light_level(self):
        """Get current light level"""
        return self._readings.get('light_level', True)
    
    def get_light_sensor_status(self):
        """Get light sensor status"""
        return {
            'current_level': self._readings.get('light_level', True),
            'raw_value': self._readings.get('light_raw', 0),
            'gpio_available': self.gpio_available,
            'using_mock': self.using_mock_sensors
        }
    
    def is_light_changed(self):
        """Check if light level has changed significantly"""
        try:
            current_light = self.get_light_level()
            
            # First reading
            if self._last_light_state is None:
                self._last_light_state = current_light
                return False
            
            # No change
            if current_light == self._last_light_state:
                return False
            
            # Light level changed - use confidence-based switching
            if len(self._light_readings) >= 4:
                target_count = sum(1 for x in self._light_readings if x == current_light)
                confidence = target_count / len(self._light_readings)
                
                if confidence >= self._confidence_level:
                    old_state = "Light" if self._last_light_state else "Dark"
                    new_state = "Light" if current_light else "Dark"
                    
                    self._last_light_state = current_light
                    logger.info(f"Light changed: {old_state} → {new_state}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking light change: {e}")
            return False
    
    def calibrate_light_sensor(self, threshold_seconds=3):
        """Set light sensor switching threshold"""
        self._switch_threshold = max(1, min(threshold_seconds, 8))
        
        # Adjust confidence based on threshold
        if threshold_seconds <= 2:
            self._confidence_level = 0.75  # Fast switching
        else:
            self._confidence_level = 0.8   # Normal switching
            
        logger.info(f"Light sensor calibrated: {self._switch_threshold}s, confidence: {self._confidence_level}")
    
    def set_fast_switching(self, enabled=True, confidence=0.8):
        """Enable fast switching mode"""
        if enabled:
            self._confidence_level = confidence
        logger.info(f"Fast switching: {enabled}, confidence: {confidence}")
    
    def force_light_state(self, is_light):
        """Force light state for testing"""
        try:
            if self.ldr and self.using_mock_sensors:
                self.ldr.force_state(is_light)
                
                # Clear state for change detection
                self._last_light_state = None
                self._light_readings = [is_light] * 3
                
                logger.info(f"Forced light state: {'Light' if is_light else 'Dark'}")
                return True
            else:
                logger.warning("Force state only available for mock sensors")
                return False
        except Exception as e:
            logger.error(f"Error forcing light state: {e}")
            return False
    
    def update_readings(self):
        """Force update readings"""
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