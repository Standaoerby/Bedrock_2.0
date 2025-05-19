"""
Сервис для работы с датчиками ENS160+AHT21
Поддерживает реальные датчики на Raspberry Pi и заглушки на Windows
"""
import time
import platform
from threading import Thread
import sys
import os

# Встроенные заглушки, которые будут использованы если ничего другого не доступно
class DummyBoard:
    SCL = "SCL"
    SDA = "SDA"

class DummyI2C:
    def __init__(self, scl, sda):
        print(f"Dummy I2C initialized (SCL: {scl}, SDA: {sda})")

class DummyENS160:
    """Встроенная заглушка для ENS160 датчика"""
    def __init__(self, i2c, address=0x68):
        self._eco2 = 800
        self._tvoc = 250
        self._aqi = 2
        print(f"Dummy ENS160 initialized at address 0x{address:02x}")
    
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

class DummyAHTx0:
    """Встроенная заглушка для AHT21 датчика"""
    def __init__(self, i2c, address=0x38):
        self._temperature = 22.5
        self._humidity = 45.0
        print(f"Dummy AHT21 initialized at address 0x{address:02x}")
        
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
        
# Функции-адаптеры для встроенных заглушек
def dummy_ENS160(i2c, address=0x68):
    return DummyENS160(i2c, address)

def dummy_AHTx0(i2c, address=0x38):
    return DummyAHTx0(i2c, address)

# Определяем, какие библиотеки загружать в зависимости от платформы
use_real_sensors = False
if platform.system() == 'Windows':
    # На Windows используем заглушки
    print("Running on Windows - using built-in mock sensors")
    board = DummyBoard()
    busio = DummyI2C
    adafruit_ens160 = dummy_ENS160
    adafruit_ahtx0 = dummy_AHTx0
else:
    # На Raspberry Pi пробуем использовать реальные библиотеки
    print("Running on Raspberry Pi - trying to use real sensors")
    try:
        import board
        import busio
        import adafruit_ens160
        import adafruit_ahtx0
        use_real_sensors = True
        print("Successfully loaded real sensor libraries")
    except Exception as e:
        print(f"Error importing sensor libraries: {e}")
        print("Please install required libraries:")
        print("sudo apt-get install -y python3-lgpio")
        print("sudo pip3 install adafruit-blinka adafruit-circuitpython-ens160 adafruit-circuitpython-ahtx0")
        print("Using built-in mock sensors instead")
        
        # Используем встроенные заглушки
        board = DummyBoard()
        busio = DummyI2C
        adafruit_ens160 = dummy_ENS160
        adafruit_ahtx0 = dummy_AHTx0

class SensorService:
    """Сервис для работы с датчиками окружающей среды"""
    
    def __init__(self):
        """Инициализация сервиса датчиков"""
        # Инициализация переменных
        self.sensor_available = False
        self.ens = None
        self.aht = None
        self.running = False
        self.thread = None
        self._readings = {
            'temperature': 0,
            'humidity': 0,
            'co2': 0,
            'tvoc': 0,
            'air_quality': 'Unknown'
        }
    
    def start(self):
        """Инициализирует датчики и запускает поток обновления"""
        try:
            # Инициализация I2C
            if use_real_sensors:
                self.i2c = busio.I2C(board.SCL, board.SDA)
            else:
                self.i2c = busio(board.SCL, board.SDA)
            
            # Инициализация датчиков
            if use_real_sensors:
                self.ens = adafruit_ens160.ENS160(self.i2c, address=0x68)
                self.aht = adafruit_ahtx0.AHTx0(self.i2c, address=0x38)
            else:
                self.ens = adafruit_ens160(self.i2c, address=0x68)
                self.aht = adafruit_ahtx0(self.i2c, address=0x38)
                
            self.sensor_available = True
            
            # Первичное чтение данных
            self.update_readings()
            
            # Запуск фонового потока для регулярного обновления
            self.running = True
            self.thread = Thread(target=self._background_update, daemon=True)
            self.thread.start()
            
            print("Sensor service started successfully")
        except Exception as e:
            print(f"Error initializing sensors: {e}")
            self.sensor_available = False
    
    def stop(self):
        """Останавливает поток обновления и освобождает ресурсы"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("Sensor service stopped")
    
    def _background_update(self):
        """Фоновый процесс для обновления данных датчиков"""
        while self.running:
            try:
                self.update_readings()
            except Exception as e:
                print(f"Error in background sensor update: {e}")
            # Пауза между обновлениями данных
            time.sleep(30)  # Обновление каждые 30 секунд
    
    def update_readings(self):
        """Обновляет данные с датчиков"""
        if not self.sensor_available:
            return
            
        try:
            # Чтение ENS160
            self._readings['co2'] = self.ens.eCO2
            self._readings['tvoc'] = self.ens.TVOC
            
            # Конвертация AQI в текстовое значение
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
            
            # Чтение AHT21
            self._readings['temperature'] = self.aht.temperature
            self._readings['humidity'] = self.aht.relative_humidity
            
            # Отладочный вывод текущих значений
            print(f"Sensor readings: Temp={self._readings['temperature']:.1f}°C, "
                  f"Humidity={self._readings['humidity']:.1f}%, "
                  f"CO2={self._readings['co2']} ppm, "
                  f"TVOC={self._readings['tvoc']} ppb, "
                  f"Air Quality={self._readings['air_quality']}")
                  
        except Exception as e:
            print(f"Error reading sensors: {e}")
    
    def get_readings(self):
        """Возвращает последние показания датчиков"""
        return self._readings.copy()  # Возвращаем копию, чтобы избежать проблем с многопоточностью