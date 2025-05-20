"""
Service for working with sensors (ENS160+AHT21)
Supports real sensors on Raspberry Pi and mock sensors for development
"""
import time
from threading import Thread

# Built-in mock sensor classes
class DummyBoard:
    SCL = "SCL"
    SDA = "SDA"

class DummyI2C:
    def __init__(self, scl, sda):
        print(f"Dummy I2C initialized (SCL: {scl}, SDA: {sda})")

class DummySensor:
    """Base class for dummy sensors"""
    def __init__(self, address):
        self.address = address
        print(f"Dummy sensor initialized at address 0x{address:02x}")

class DummyENS160(DummySensor):
    """Built-in mock for ENS160 sensor"""
    def __init__(self, i2c, address=0x68):
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
    def __init__(self, i2c, address=0x38):
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

# Try to import real libraries, use mocks if not available
try:
    import board
    import busio
    import adafruit_ens160
    import adafruit_ahtx0
    use_real_sensors = True
    print("Successfully loaded real sensor libraries")
except Exception as e:
    print(f"Error importing sensor libraries: {e}")
    print("Using mock sensors instead")
    
    # Use built-in mocks
    board = DummyBoard()
    busio = DummyI2C
    adafruit_ens160 = DummyENS160
    adafruit_ahtx0 = DummyAHTx0
    use_real_sensors = False

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
    
    def start(self):
        """Initialize sensors and start update thread"""
        try:
            # Initialize I2C
            if use_real_sensors:
                self.i2c = busio.I2C(board.SCL, board.SDA)
            else:
                self.i2c = busio(board.SCL, board.SDA)
            
            # Initialize sensors
            if use_real_sensors:
                self.ens = adafruit_ens160.ENS160(self.i2c, address=0x68)
                self.aht = adafruit_ahtx0.AHTx0(self.i2c, address=0x38)
            else:
                self.ens = adafruit_ens160(self.i2c, address=0x68)
                self.aht = adafruit_ahtx0(self.i2c, address=0x38)
                
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