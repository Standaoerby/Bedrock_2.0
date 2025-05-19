"""
Заглушки для библиотек Adafruit для разработки на Windows
Эмулирует датчики ENS160 и AHT21
"""

class MockENS160:
    """Заглушка для ENS160 датчика (CO2, TVOC, AQI)"""
    def __init__(self, i2c, address=0x68):
        self._eco2 = 800  # ppm, нормальный уровень
        self._tvoc = 250  # ppb, нормальный уровень
        self._aqi = 2     # Good
        print(f"Mock ENS160 initialized at address 0x{address:02x}")
    
    @property
    def eCO2(self):
        """Эквивалентный CO2 (eCO2) в ppm"""
        import random
        # Небольшая случайная вариация значений для имитации живых данных
        self._eco2 += random.randint(-25, 25)
        # Ограничение значений реалистичным диапазоном
        self._eco2 = max(400, min(self._eco2, 1500))
        return self._eco2
    
    @property
    def TVOC(self):
        """Total Volatile Organic Compounds в ppb"""
        import random
        self._tvoc += random.randint(-15, 15)
        self._tvoc = max(50, min(self._tvoc, 500))
        return self._tvoc
    
    @property
    def AQI(self):
        """Air Quality Index (1-5: Excellent, Good, Moderate, Poor, Unhealthy)"""
        import random
        # Иногда изменяем AQI для имитации изменений качества воздуха
        if random.random() < 0.05:  # 5% вероятность изменения
            self._aqi = random.randint(1, 5)
        return self._aqi

class MockAHTx0:
    """Заглушка для AHT21 датчика (температура и влажность)"""
    def __init__(self, i2c, address=0x38):
        self._temperature = 22.5  # °C
        self._humidity = 45.0     # %
        print(f"Mock AHT21 initialized at address 0x{address:02x}")
        
    @property
    def temperature(self):
        """Температура в градусах Цельсия"""
        import random
        # Небольшие случайные изменения температуры
        self._temperature += random.uniform(-0.3, 0.3)
        # Ограничение температуры реалистичным домашним диапазоном
        self._temperature = max(18.0, min(self._temperature, 28.0))
        return self._temperature
        
    @property
    def relative_humidity(self):
        """Относительная влажность в %"""
        import random
        self._humidity += random.uniform(-1.0, 1.0)
        self._humidity = max(30.0, min(self._humidity, 70.0))
        return self._humidity

# Заглушки для board и busio модулей Adafruit Blinka
class MockI2C:
    """Заглушка для I2C интерфейса"""
    def __init__(self, scl, sda):
        print(f"Mock I2C initialized (SCL: {scl}, SDA: {sda})")

class MockBoard:
    """Заглушка для board модуля с GPIO пинами"""
    SCL = "GPIO3"
    SDA = "GPIO2"

# Функции-адаптеры для интерфейса Adafruit
def ENS160(i2c, address=0x68):
    """Создаёт экземпляр заглушки ENS160"""
    return MockENS160(i2c, address)

def AHTx0(i2c, address=0x38):
    """Создаёт экземпляр заглушки AHT21"""
    return MockAHTx0(i2c, address)