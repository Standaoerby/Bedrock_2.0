"""
Service for working with sensors (ENS160+AHT21+LDR)
Supports real sensors on Raspberry Pi and mock sensors for development
FIXED: None type errors in GPIO operations
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
    """Built-in mock for LDR light sensor"""
    def __init__(self):
        self._is_light = True
        self._last_change = time.time()
    
    def read_digital(self):
        """Simulate light level changes based on time of day"""
        current_hour = datetime.now().hour
        
        # Simulate day/night cycle: dark from 20:00 to 07:00
        if 7 <= current_hour < 20:
            base_is_light = True
        else:
            base_is_light = False
            
        # Add some random variation for testing
        if time.time() - self._last_change > 60:  # Change every 60 seconds for testing
            if random.random() < 0.15:  # 15% chance to flip
                self._is_light = not base_is_light
                self._last_change = time.time()
                logger.info(f"Mock LDR changed to: {'Light' if self._is_light else 'Dark'}")
                return self._is_light
        
        return base_is_light

# Вставьте этот код в services/sensor_service.py вместо класса SensorService

class SensorService:
    """Service for environmental sensors with БЫСТРОЕ переключение тем"""
    
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
        
        # ИСПРАВЛЕНО: БЫСТРОЕ переключение - уменьшены все задержки
        self._last_light_state = None
        self._light_change_threshold = 3  # УМЕНЬШЕНО с 5 до 3 секунд
        self._light_change_start = None
        self._light_readings_buffer = []
        self._buffer_size = 8  # УМЕНЬШЕНО с 15 до 8 для быстрого отклика
        self._stability_threshold = 0.7  # УМЕНЬШЕНО с 0.8 до 0.7 (70% вместо 80%)
        
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
        
        # ИСПРАВЛЕНО: Более быстрое подтверждение изменений
        self._consecutive_same_readings = 0
        self._min_consecutive_for_change = 3  # УМЕНЬШЕНО с 5 до 3
        self._change_confirmation_count = 0
        self._min_confirmations = 2  # УМЕНЬШЕНО с 3 до 2
        
        # State tracking for debugging
        self._light_state_history = []
        self._max_history = 30  # Уменьшено с 50
        
        # НОВОЕ: Быстрая проверка для немедленного переключения
        self._fast_switch_enabled = True
        self._fast_switch_confidence = 0.85  # 85% уверенности для быстрого переключения
        
        logger.info("🚀 SensorService initialized with FAST theme switching")
    
    # ... (остальные методы остаются прежними до is_light_changed)
    
    def is_light_changed(self):
        """ИСПРАВЛЕНО: Быстрая проверка изменения освещённости"""
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
            
            # Light level is different - БЫСТРАЯ проверка
            self._consecutive_same_readings += 1
            
            # НОВОЕ: Проверяем можем ли мы переключиться быстро
            if self._fast_switch_enabled and len(self._light_readings_buffer) >= 5:
                valid_readings = [x for x in self._light_readings_buffer[-5:] if x is not None]
                if valid_readings:
                    target_count = sum(1 for x in valid_readings if x == current_light)
                    confidence = target_count / len(valid_readings)
                    
                    if confidence >= self._fast_switch_confidence:
                        # Высокая уверенность - переключаемся быстро!
                        old_state = "Light" if self._last_light_state else "Dark"
                        new_state = "Light" if current_light else "Dark"
                        
                        self._last_light_state = current_light
                        self._light_change_start = None
                        self._consecutive_same_readings = 0
                        
                        logger.info(f"⚡ FAST LIGHT SWITCH: {old_state} → {new_state} (confidence: {confidence:.1%})")
                        return True
            
            # Need minimum consecutive different readings before starting timer
            if self._consecutive_same_readings < self._min_consecutive_for_change:
                if self._change_detection_debug % 5 == 0:  # Логируем чаще
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
                    
                    return True
                else:
                    logger.debug(f"Change confirmation {self._change_confirmation_count}/{self._min_confirmations}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error in is_light_changed: {e}")
            return False
    
    def calibrate_light_sensor(self, threshold_seconds=3):
        """ИСПРАВЛЕНО: Быстрая калибровка - по умолчанию 3 секунды"""
        try:
            old_threshold = self._light_change_threshold
            # Ограничиваем между 1-8 секундами (вместо 2-15)
            self._light_change_threshold = max(1, min(threshold_seconds, 8))
            logger.info(f"🔧 Light sensor threshold: {old_threshold}s → {self._light_change_threshold}s")
            
            # Также обновляем размер буфера для быстрого отклика
            if threshold_seconds <= 3:
                self._buffer_size = 6
                self._stability_threshold = 0.65  # Ещё более быстрое переключение
                logger.info(f"🚀 Fast mode enabled: buffer={self._buffer_size}, threshold={self._stability_threshold}")
            elif threshold_seconds <= 5:
                self._buffer_size = 8
                self._stability_threshold = 0.70
            else:
                self._buffer_size = 10
                self._stability_threshold = 0.75
                
        except Exception as e:
            logger.error(f"Error in calibrate_light_sensor: {e}")

    # НОВЫЙ: Метод для включения/отключения быстрого переключения
    def set_fast_switching(self, enabled=True, confidence=0.85):
        """Включить/отключить быстрое переключение тем"""
        self._fast_switch_enabled = enabled
        self._fast_switch_confidence = confidence
        logger.info(f"Fast switching {'enabled' if enabled else 'disabled'} "
                   f"(confidence: {confidence:.1%})")

    # Остальные методы остаются без изменений...