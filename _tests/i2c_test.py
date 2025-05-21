#!/usr/bin/env python3
"""
Простой скрипт для проверки I2C датчиков ENS160 и AHT21
Исправлен адрес ENS160 (0x53 вместо 0x68)
"""
import os
import sys
import time
import traceback

print("========================================")
print("    ТЕСТ ДАТЧИКОВ ENS160 И AHT21")
print("========================================")

# Адреса датчиков
ENS160_ADDRESS = 0x53  # Исправлено на 0x53 вместо 0x68
AHT21_ADDRESS = 0x38

# Проверка модулей
print("\n1. Проверка наличия необходимых модулей:")
try:
    import board
    import busio
    print("✓ Базовые модули (board, busio) найдены")
except ImportError:
    print("✗ Базовые модули не найдены. Установите adafruit-blinka:")
    print("  pip3 install adafruit-blinka")
    sys.exit(1)

try:
    import adafruit_ens160
    print("✓ Модуль adafruit_ens160 найден")
except ImportError:
    print("✗ Модуль для ENS160 не найден. Установите:")
    print("  pip3 install adafruit-circuitpython-ens160")
    sys.exit(1)

try:
    import adafruit_ahtx0
    print("✓ Модуль adafruit_ahtx0 найден")
except ImportError:
    print("✗ Модуль для AHT21 не найден. Установите:")
    print("  pip3 install adafruit-circuitpython-ahtx0")
    sys.exit(1)

# Проверка I2C устройств в системе
print("\n2. Проверка I2C устройств в системе:")
if os.path.exists("/dev/i2c-1"):
    print("✓ Устройство /dev/i2c-1 найдено")
    i2c_dev = "/dev/i2c-1"
elif os.path.exists("/dev/i2c-0"):
    print("✓ Устройство /dev/i2c-0 найдено")
    i2c_dev = "/dev/i2c-0"
else:
    print("✗ Устройства I2C не найдены в системе")
    print("  Выполните: sudo raspi-config")
    print("  и включите I2C в Interfacing Options")
    sys.exit(1)

# Проверка прав доступа
try:
    with open(i2c_dev, "rb"):
        print("✓ Права доступа к I2C в порядке")
except PermissionError:
    print("✗ Ошибка прав доступа к устройству I2C:")
    print(f"  sudo chmod 666 {i2c_dev}")
    sys.exit(1)

# Инициализация I2C - несколько методов
print("\n3. Инициализация I2C:")
i2c = None
try:
    print("   Попытка 1 (SCL/SDA)...")
    i2c = busio.I2C(board.SCL, board.SDA)
    print("✓ I2C успешно инициализирован через SCL/SDA")
except Exception as e:
    print(f"✗ Ошибка: {e}")
    try:
        print("   Попытка 2 (GPIO 3/2)...")
        i2c = busio.I2C(3, 2)  # GPIO3=SCL, GPIO2=SDA для Pi 5
        print("✓ I2C успешно инициализирован через GPIO 3/2")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        try:
            # Пробуем метод от Adafruit Blinka для прямого доступа
            print("   Попытка 3 (прямой доступ)...")
            from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
            i2c = I2C(1 if i2c_dev == "/dev/i2c-1" else 0)
            print("✓ I2C успешно инициализирован через прямой доступ")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            print("  Не удалось инициализировать I2C!")
            sys.exit(1)

# Сканирование шины
print("\n4. Сканирование шины I2C:")
devices = []
try:
    for address in range(0x00, 0x80):
        try:
            i2c.writeto(address, b'')
            devices.append(address)
        except:
            pass
            
    if devices:
        print(f"✓ Найдено {len(devices)} устройств:")
        for address in devices:
            print(f"   0x{address:02X}", end="")
            if address == ENS160_ADDRESS:
                print(" (ENS160)", end="")
            elif address == AHT21_ADDRESS:
                print(" (AHT21)", end="")
            print()
            
        if ENS160_ADDRESS not in devices:
            print(f"✗ ENS160 не найден по адресу 0x{ENS160_ADDRESS:02X}")
            
        if AHT21_ADDRESS not in devices:
            print(f"✗ AHT21 не найден по адресу 0x{AHT21_ADDRESS:02X}")
    else:
        print("✗ Устройства не найдены на шине I2C!")
except Exception as e:
    print(f"✗ Ошибка при сканировании шины: {e}")

# Тест датчика ENS160
print("\n5. Проверка датчика ENS160:")
if ENS160_ADDRESS in devices:
    try:
        ens = adafruit_ens160.ENS160(i2c, address=ENS160_ADDRESS)
        
        print("   Выполняется 3 замера (с паузами 1с)...")
        for i in range(3):
            if i > 0:
                time.sleep(1)  # Пауза между замерами
                
            eco2 = ens.eCO2
            tvoc = ens.TVOC
            aqi = ens.AQI
            
            print(f"   Замер {i+1}: eCO2={eco2} ppm, TVOC={tvoc} ppb, AQI={aqi}")
            
            # Проверка на значения-заглушки
            if 790 <= eco2 <= 810 and 245 <= tvoc <= 255 and 1 <= aqi <= 3:
                print("   ⚠ Возможно значения-заглушки!")
                
        print("✓ ENS160 успешно протестирован")
    except Exception as e:
        print(f"✗ Ошибка при чтении ENS160: {e}")
        print(traceback.format_exc())
else:
    print("✗ ENS160 не найден на шине")

# Тест датчика AHT21
print("\n6. Проверка датчика AHT21:")
if AHT21_ADDRESS in devices:
    try:
        aht = adafruit_ahtx0.AHTx0(i2c, address=AHT21_ADDRESS)
        
        print("   Выполняется 3 замера (с паузами 1с)...")
        for i in range(3):
            if i > 0:
                time.sleep(1)  # Пауза между замерами
                
            temp = aht.temperature
            humid = aht.relative_humidity
            
            print(f"   Замер {i+1}: Темп.={temp:.2f}°C, Влажность={humid:.2f}%")
            
            # Проверка на значения-заглушки
            if 22.0 <= temp <= 23.0 and 44.0 <= humid <= 46.0:
                print("   ⚠ Возможно значения-заглушки!")
                
        print("✓ AHT21 успешно протестирован")
    except Exception as e:
        print(f"✗ Ошибка при чтении AHT21: {e}")
        print(traceback.format_exc())
else:
    print("✗ AHT21 не найден на шине")

# Проверка настройки USE_MOCK_SENSORS
print("\n7. Проверка настроек приложения:")
use_mock = os.environ.get("USE_MOCK_SENSORS")
if use_mock == "1":
    print("✗ Включен режим заглушек (USE_MOCK_SENSORS=1)")
    print("  Измените на USE_MOCK_SENSORS=0 в start.sh")
else:
    print(f"✓ Режим заглушек выключен (USE_MOCK_SENSORS={use_mock or 'не задан'})")

# Рекомендации
print("\n8. Рекомендации:")
if ENS160_ADDRESS not in devices or AHT21_ADDRESS not in devices:
    print("• Проверьте подключение датчиков к шине I2C")
    print("• Убедитесь, что провода SDA и SCL подключены правильно")
    print("• Проверьте питание датчиков (3.3В или 5В согласно спецификации)")
    
    print("\nДля настройки системы выполните:")
    print("• sudo raspi-config > Interfacing Options > I2C > Enable")
    print("• sudo usermod -a -G i2c $USER  # и перезагрузка")
    print("• sudo chmod 666 /dev/i2c*")

print("\nДля использования в приложении:")
print("• Проверьте настройку USE_MOCK_SENSORS=0 в start.sh")
print("• Убедитесь, что методы инициализации в services/sensor_service.py")
print("  соответствуют вашей модели Raspberry Pi")

print("\n========================================")
print("            ТЕСТ ЗАВЕРШЕН")
print("========================================")