"""
Service for working with sensors (ENS160+AHT21)
Supports real sensors on Raspberry Pi and mock sensors for development
"""
import time
import os
import sys
from threading import Thread

# Define constants for I2C addresses
ENS160_ADDRESS = 0x68
AHT21_ADDRESS = 0x38

# Built-in mock sensor classes
class DummyBoard:
    SCL = "SCL"
    SDA = "SDA"

class DummyI2C:
    def __init__(self, scl, sda):
        print(f"Dummy I2C initialized (SCL: {scl}, SDA: {sda})")

    def writeto(self, address, data):
        pass

class DummySensor:
    """Base class for dummy sensors"""
    def __init__(self, address):
        self.address = address
        print(f"Dummy sensor initialized at address 0x{address:02x}")

class DummyENS160(DummySensor):
    """Built-in mock for ENS160 sensor"""
    def __init__(self, i2c, address=ENS160_ADDRESS):
        super().__init__(address)
        self._eco2 = 800
        self._tvoc = 250
        self._aqi = 2
    
    @property
    def eCO2(self):
        import random
        self._eco2 += random.randint(-25, 25)
        self._eco2 = max(400, min(self._eco2, 1500))
        return self._eco2
    
    @property
    def TVOC(self):
        import random
        self._tvoc += random.randint(-15, 15)
        self._tvoc = max(50, min(self._tvoc, 500))
        return self._tvoc
    
    @property
    def AQI(self):
        import random
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
        import random
        self._temperature += random.uniform(-0.3, 0.3)
        self._temperature = max(18.0, min(self._temperature, 28.0))
        return self._temperature
        
    @property
    def relative_humidity(self):
        import random
        self._humidity += random.uniform(-1.0, 1.0)
        self._humidity = max(30.0, min(self._humidity, 70.0))
        return self._humidity

# Set up real libraries based on available hardware
def setup_i2c():
    """Set up I2C interface for the current platform
    Returns a tuple of (i2c_interface, is_real_hardware)
    """
    # Check if we should force mock mode (for testing)
    if os.environ.get('USE_MOCK_SENSORS') == '1':
        print("Using mock sensors (forced by environment variable)")
        return None, False
        
    # Try multiple methods to initialize I2C
    try:
        # Method 1: Traditional board with SCL/SDA pins
        import board
        import busio
        try:
            print("Trying I2C Method 1: board.SCL/board.SDA")
            i2c = busio.I2C(board.SCL, board.SDA)
            print("I2C initialized using board.SCL/board.SDA")
            return i2c, True
        except (AttributeError, ValueError) as e:
            print(f"Method 1 failed: {e}")
            
            # Method 2: Direct GPIO pin numbers (for Raspberry Pi 5)
            try:
                print("Trying I2C Method 2: Direct GPIO pins (3=SCL, 2=SDA)")
                i2c = busio.I2C(3, 2)  # GPIO3=SCL, GPIO2=SDA
                print("I2C initialized using direct GPIO pins 3 and 2")
                return i2c, True
            except Exception as e:
                print(f"Method 2 failed: {e}")
                
                # Method 3: Use adafruit_blinka to access /dev/i2c-1 directly
                if os.path.exists('/dev/i2c-1'):
                    try:
                        print("Trying I2C Method 3: Direct I2C device access")
                        from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
                        i2c = I2C(1)  # /dev/i2c-1
                        print("I2C initialized using generic Linux I2C device")
                        return i2c, True
                    except Exception as e:
                        print(f"Method 3 failed: {e}")
                
                # Method 4: For specific hardware try Raspberry Pi-specific approach
                # Method 4: For specific hardware try a more generic approach
                try:
                    print("Trying I2C Method 4: Generic Pin approach")
                    # Use more generic approach
                    from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
                    i2c = I2C(1)  # /dev/i2c-1
                    print("I2C initialized using generic Linux I2C device - Method 4")
                    return i2c, True
                except Exception as e:
                    print(f"Method 4 failed: {e}")
                        
    except ImportError as e:
        # If board or busio not available
        print(f"Error importing required libraries: {e}")
    
    # If all methods fail, use mock mode
    print("Falling back to mock sensors mode")
    return None, False

# Initialize global variables
try:
    i2c_interface, use_real_sensors = setup_i2c()
    
    if use_real_sensors:
        import adafruit_ens160
        import adafruit_ahtx0
        print("Successfully loaded real sensor libraries")
    else:
        # Set up mock objects
        board = DummyBoard()
        busio = DummyI2C
        adafruit_ens160 = DummyENS160
        adafruit_ahtx0 = DummyAHTx0
        print("Using mock sensors (hardware unavailable)")
        
except Exception as e:
    print(f"Error during sensor initialization: {e}")
    # Fall back to mocks
    board = DummyBoard()
    busio = DummyI2C
    adafruit_ens160 = DummyENS160
    adafruit_ahtx0 = DummyAHTx0
    use_real_sensors = False
    print("Using mock sensors due to initialization error")

class SensorService:
    """Service for environmental sensors"""
    
    def __init__(self):
        """Initialize the sensor service"""
        # Initialize variables
        self.sensor_available = False
        self.ens = None
        self.aht = None
        self.running = False
        self.thread = None
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good'
        }
        # Store the mock status for UI to check
        self.using_mock_sensors = not use_real_sensors
    
    def start(self):
        """Initialize sensors and start update thread"""
        try:
            if use_real_sensors:
                # Real hardware mode - use the already initialized I2C interface
                self.i2c = i2c_interface
                
                # Detect I2C devices
                self._scan_i2c()
                
                # Initialize sensors
                self.ens = adafruit_ens160.ENS160(self.i2c, address=ENS160_ADDRESS)
                self.aht = adafruit_ahtx0.AHTx0(self.i2c, address=AHT21_ADDRESS)
            else:
                # Mock mode
                self.i2c = busio(board.SCL, board.SDA)
                self.ens = adafruit_ens160(self.i2c, address=ENS160_ADDRESS)
                self.aht = adafruit_ahtx0(self.i2c, address=AHT21_ADDRESS)
                
            self.sensor_available = True
            
            # Initial reading
            self.update_readings()
            
            # Start background thread
            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            
            print("Sensor service started successfully")
        except Exception as e:
            print(f"Error initializing sensors: {e}")
            self.sensor_available = False
            self.using_mock_sensors = True
    
    def _scan_i2c(self):
        """Scan I2C bus and print detected devices"""
        if not use_real_sensors:
            return
            
        try:
            print("Scanning I2C bus for devices...")
            addresses = []
            
            for address in range(0x00, 0x80):
                try:
                    self.i2c.writeto(address, b'')
                    addresses.append(address)
                except Exception:
                    pass
            
            if addresses:
                print(f"Found {len(addresses)} I2C devices at addresses:")
                for address in addresses:
                    print(f"0x{address:02X}")
                    
                # Check for our sensors
                if ENS160_ADDRESS in addresses:
                    print(f"ENS160 found at address 0x{ENS160_ADDRESS:02X}")
                else:
                    print(f"WARNING: ENS160 not found at address 0x{ENS160_ADDRESS:02X}")
                    
                if AHT21_ADDRESS in addresses:
                    print(f"AHT21 found at address 0x{AHT21_ADDRESS:02X}")
                else:
                    print(f"WARNING: AHT21 not found at address 0x{AHT21_ADDRESS:02X}")
            else:
                print("No I2C devices found! Check your wiring")
        except Exception as e:
            print(f"Error scanning I2C: {e}")
    
    def stop(self):
        """Stop the update thread and free resources"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("Sensor service stopped")
    
    def _background_update(self):
        """Background process for sensor data updates"""
        while self.running:
            try:
                self.update_readings()
            except Exception as e:
                print(f"Error in background sensor update: {e}")
            # Pause between updates
            time.sleep(30)  # Update every 30 seconds
    
    def update_readings(self):
        """Update data from sensors"""
        if not self.sensor_available:
            return
            
        try:
            # Read ENS160
            self._readings['co2'] = self.ens.eCO2
            self._readings['tvoc'] = self.ens.TVOC
            
            # Convert AQI to text value
            aqi = self.ens.AQI
            if aqi == 1:
                self._readings['air_quality'] = "Excellent"
            elif aqi == 2:
                self._readings['air_quality'] = "Good"
            elif aqi == 3:
                self._readings['air_quality'] = "Moderate"
            elif aqi == 4:
                self._readings['air_quality'] = "Poor"
            elif aqi == 5:
                self._readings['air_quality'] = "Unhealthy"
            else:
                self._readings['air_quality'] = f"Unknown ({aqi})"
            
            # Read AHT21
            self._readings['temperature'] = self.aht.temperature
            self._readings['humidity'] = self.aht.relative_humidity
            
            # Debug output
            print(f"Sensor readings: Temp={self._readings['temperature']:.1f}°C, "
                  f"Humidity={self._readings['humidity']:.1f}%, "
                  f"CO2={self._readings['co2']} ppm, "
                  f"TVOC={self._readings['tvoc']} ppb, "
                  f"Air Quality={self._readings['air_quality']}")
                  
        except Exception as e:
            print(f"Error reading sensors: {e}")
    
    def get_readings(self):
        """Return the latest sensor readings"""
        return self._readings.copy()  # Return a copy to avoid threading issues

# Simple self-test if file is run directly
if __name__ == "__main__":
    print("Sensor Service - Self Test")
    service = SensorService()
    service.start()
    
    if service.sensor_available:
        print("Service started successfully, press Ctrl+C to exit")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            service.stop()
            print("Service stopped")
    else:
        print("Failed to start sensor service")