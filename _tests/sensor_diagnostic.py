#!/usr/bin/env python3
"""
Скрипт диагностики датчиков I2C для Bedrock App
Проверяет подключение и работу датчиков ENS160 и AHT21
"""
import os
import sys
import time
import logging
import subprocess
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sensor_diagnostic.log')
    ]
)
logger = logging.getLogger("SensorDiagnostic")

# Константы для адресов I2C
ENS160_ADDRESS = 0x68  # Адрес датчика качества воздуха
AHT21_ADDRESS = 0x38   # Адрес датчика температуры и влажности

def print_header(text):
    """Вывод заголовка секции с выделением"""
    border = "=" * (len(text) + 4)
    print(f"\n{border}")
    print(f"= {text} =")
    print(f"{border}\n")

def run_command(cmd):
    """Запуск команды и возврат вывода"""
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return f"Ошибка выполнения команды: {e}", "", 1

def check_system_info():
    """Проверка информации о системе"""
    print_header("ИНФОРМАЦИЯ О СИСТЕМЕ")
    
    # Проверка версии ОС
    stdout, stderr, code = run_command("cat /etc/os-release | grep PRETTY_NAME")
    if code == 0:
        print(f"Операционная система: {stdout.strip()}")
    
    # Проверка модели Raspberry Pi
    stdout, stderr, code = run_command("cat /proc/device-tree/model | tr -d '\\0'")
    if code == 0:
        print(f"Модель устройства: {stdout.strip()}")
    
    # Проверка ядра
    stdout, stderr, code = run_command("uname -a")
    if code == 0:
        print(f"Ядро: {stdout.strip()}")
    
    # Проверка загруженных модулей I2C
    print("\nЗагруженные модули I2C:")
    stdout, stderr, code = run_command("lsmod | grep i2c")
    if stdout:
        print(stdout)
    else:
        print("Модули I2C не загружены!")
    
    # Проверка статуса I2C в конфигурации
    print("\nСтатус I2C в raspi-config:")
    stdout, stderr, code = run_command("raspi-config nonint get_i2c")
    if code == 0:
        status = "Включен" if stdout.strip() == "0" else "Отключен"
        print(f"I2C статус: {status}")
    else:
        print("Не удалось проверить статус I2C через raspi-config")
    
    # Проверка конфигурации загрузки
    print("\nПроверка конфигурации в /boot/config.txt:")
    stdout, stderr, code = run_command("grep -E 'i2c|dtparam' /boot/config.txt")
    if stdout:
        print(stdout)
    else:
        print("Настройки I2C не найдены в /boot/config.txt!")

def check_i2c_devices():
    """Проверка наличия устройств на шине I2C"""
    print_header("ПРОВЕРКА УСТРОЙСТВ I2C")
    
    # Проверка наличия устройств I2C
    print("Устройства I2C в системе:")
    stdout, stderr, code = run_command("ls -l /dev/i2c*")
    if stdout:
        print(stdout)
    else:
        print("Устройства I2C не найдены в /dev!")
        print("\nРекомендации:")
        print("1. Проверьте, включен ли I2C в raspi-config")
        print("2. Перезагрузите устройство после включения")
        print("3. Проверьте наличие модулей ядра с помощью 'lsmod | grep i2c'")
        return False
    
    # Сканирование шины I2C
    print("\nСканирование шины I2C:")
    stdout, stderr, code = run_command("i2cdetect -y 1")
    if code != 0:
        # Попробуем шину 0, если 1 не доступна
        stdout, stderr, code = run_command("i2cdetect -y 0")
    
    if stdout:
        print(stdout)
        
        # Проверка наличия адресов наших датчиков
        ens160_found = f"68" in stdout
        aht21_found = f"38" in stdout
        
        print("\nРезультаты сканирования:")
        print(f"ENS160 (0x68): {'НАЙДЕН' if ens160_found else 'НЕ НАЙДЕН'}")
        print(f"AHT21 (0x38): {'НАЙДЕН' if aht21_found else 'НЕ НАЙДЕН'}")
        
        if not ens160_found or not aht21_found:
            print("\nРекомендации:")
            print("1. Проверьте правильность подключения датчиков")
            print("2. Проверьте питание датчиков")
            print("3. Убедитесь, что GPIO пины правильно назначены (SDA и SCL)")
            return False
        return True
    else:
        print("Не удалось просканировать шину I2C")
        return False

def test_i2c_permissions():
    """Проверка прав доступа к I2C"""
    print_header("ПРОВЕРКА ПРАВ ДОСТУПА К I2C")
    
    # Проверка наличия текущего пользователя в группе i2c
    user = os.environ.get('USER', 'pi')
    stdout, stderr, code = run_command(f"groups {user} | grep i2c")
    if stdout:
        print(f"Пользователь {user} входит в группу i2c")
    else:
        print(f"Пользователь {user} НЕ входит в группу i2c!")
        print("\nРекомендации:")
        print(f"Добавьте пользователя в группу i2c командой:")
        print(f"  sudo usermod -a -G i2c {user}")
        print("После этого перезагрузите устройство или выполните 'newgrp i2c'")
    
    # Проверка прав на устройство
    print("\nПрава доступа к устройству I2C:")
    stdout, stderr, code = run_command("ls -l /dev/i2c*")
    if stdout:
        print(stdout)
        if "crw-rw----" not in stdout:
            print("Неправильные права доступа к устройству I2C")
            print("Рекомендации:")
            print("Выполните команду: sudo chmod 660 /dev/i2c-1")
    
    # Пробуем чтение из шины I2C
    print("\nПроверка возможности чтения с шины I2C:")
    try:
        # Проверяем возможность открытия файла устройства
        i2c_device = "/dev/i2c-1" if os.path.exists("/dev/i2c-1") else "/dev/i2c-0"
        with open(i2c_device, "rb") as f:
            print(f"Успешно открыт файл устройства {i2c_device}")
    except PermissionError:
        print(f"Ошибка прав доступа при открытии {i2c_device}")
        print("\nРекомендации:")
        print("1. Выполните: sudo chmod 666 /dev/i2c*")
        print("2. Добавьте правило udev для постоянных прав:")
        print("   echo 'KERNEL==\"i2c-[0-9]*\", GROUP=\"i2c\", MODE=\"0666\"' | sudo tee /etc/udev/rules.d/99-i2c-permissions.rules")
        print("   sudo udevadm control --reload-rules && sudo udevadm trigger")
    except Exception as e:
        print(f"Ошибка при проверке доступа: {e}")

def install_dependencies():
    """Установка необходимых зависимостей"""
    print_header("ПРОВЕРКА И УСТАНОВКА ЗАВИСИМОСТЕЙ")
    
    # Проверка наличия необходимых инструментов
    print("Проверка установленных инструментов I2C:")
    stdout, stderr, code = run_command("dpkg -l | grep -E 'i2c-tools|python3-smbus'")
    if stdout:
        print(stdout)
    else:
        print("Инструменты I2C не установлены")
        
        # Предложим установить инструменты
        print("\nУстановка необходимых инструментов:")
        if input("Установить i2c-tools и python3-smbus? (y/n): ").lower() == 'y':
            stdout, stderr, code = run_command("sudo apt update && sudo apt install -y i2c-tools python3-smbus")
            if code == 0:
                print("Инструменты успешно установлены")
            else:
                print(f"Ошибка установки: {stderr}")
    
    # Проверка наличия необходимых Python библиотек
    print("\nПроверка Python библиотек:")
    packages = [
        "adafruit-blinka", 
        "adafruit-circuitpython-ahtx0", 
        "adafruit-circuitpython-ens160"
    ]
    
    missing_packages = []
    for package in packages:
        stdout, stderr, code = run_command(f"pip3 list | grep {package}")
        if not stdout:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Отсутствуют библиотеки: {', '.join(missing_packages)}")
        
        # Предложим установить библиотеки
        if input("Установить отсутствующие библиотеки? (y/n): ").lower() == 'y':
            for package in missing_packages:
                print(f"Установка {package}...")
                stdout, stderr, code = run_command(f"pip3 install {package}")
                if code == 0:
                    print(f"{package} успешно установлен")
                else:
                    print(f"Ошибка установки {package}: {stderr}")
    else:
        print("Все необходимые Python библиотеки установлены")

def test_sensor_readings():
    """Тест чтения данных с датчиков через Adafruit библиотеки"""
    print_header("ТЕСТ ЧТЕНИЯ ДАННЫХ С ДАТЧИКОВ")
    
    try:
        print("Инициализация библиотек и I2C...")
        import board
        import busio
        import adafruit_ens160
        import adafruit_ahtx0
        
        # Вывод информации о библиотеках
        print(f"Python версия: {sys.version}")
        print(f"Adafruit ENS160 версия: {adafruit_ens160.__version__}")
        print(f"Adafruit AHTx0 версия: {adafruit_ahtx0.__version__}")
        
        # Попробуем различные способы инициализации I2C
        print("\nПопытка инициализации I2C...")
        i2c = None
        i2c_methods = [
            lambda: busio.I2C(board.SCL, board.SDA),
            lambda: busio.I2C(3, 2),  # GPIO3=SCL, GPIO2=SDA для Pi 5
            lambda: busio.I2C(board.D3, board.D2)  # Альтернативное именование
        ]
        
        for i, method in enumerate(i2c_methods):
            try:
                print(f"Метод {i+1}...")
                i2c = method()
                print(f"Метод {i+1} успешно")
                break
            except Exception as e:
                print(f"Ошибка метода {i+1}: {e}")
        
        if i2c is None:
            print("\nНе удалось инициализировать I2C. Проверьте подключение и права доступа.")
            return
        
        # Сканирование устройств на шине
        print("\nСканирование I2C устройств через Python:")
        devices = []
        for address in range(0x00, 0x80):
            try:
                i2c.writeto(address, b'')
                devices.append(address)
            except Exception:
                pass
        
        if not devices:
            print("Устройства не найдены!")
            return
        
        print(f"Найдено {len(devices)} устройств:")
        for address in devices:
            print(f"0x{address:02X}", end=" ")
            if address == ENS160_ADDRESS:
                print("(ENS160)", end="")
            elif address == AHT21_ADDRESS:
                print("(AHT21)", end="")
            print()
        
        # Проверка ENS160
        ens160_working = False
        if ENS160_ADDRESS in devices:
            try:
                print("\nПроверка датчика ENS160...")
                ens = adafruit_ens160.ENS160(i2c, address=ENS160_ADDRESS)
                print(f"eCO2: {ens.eCO2} ppm")
                print(f"TVOC: {ens.TVOC} ppb")
                print(f"AQI: {ens.AQI}")
                ens160_working = True
            except Exception as e:
                print(f"Ошибка чтения ENS160: {e}")
                traceback.print_exc()
        else:
            print("\nДатчик ENS160 не найден на шине I2C")
        
        # Проверка AHT21
        aht21_working = False
        if AHT21_ADDRESS in devices:
            try:
                print("\nПроверка датчика AHT21...")
                aht = adafruit_ahtx0.AHTx0(i2c, address=AHT21_ADDRESS)
                print(f"Температура: {aht.temperature:.2f}°C")
                print(f"Влажность: {aht.relative_humidity:.2f}%")
                aht21_working = True
            except Exception as e:
                print(f"Ошибка чтения AHT21: {e}")
                traceback.print_exc()
        else:
            print("\nДатчик AHT21 не найден на шине I2C")
        
        # Итоги теста
        if ens160_working and aht21_working:
            print("\nВсе датчики работают корректно!")
        else:
            print("\nНе все датчики работают корректно:")
            print(f"ENS160: {'OK' if ens160_working else 'ОШИБКА'}")
            print(f"AHT21: {'OK' if aht21_working else 'ОШИБКА'}")
            
    except ImportError as e:
        print(f"Ошибка импорта библиотек: {e}")
        print("Убедитесь, что библиотеки установлены:")
        print("sudo pip3 install adafruit-blinka adafruit-circuitpython-ahtx0 adafruit-circuitpython-ens160")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        traceback.print_exc()

def check_app_configuration():
    """Проверка настроек приложения Bedrock"""
    print_header("ПРОВЕРКА НАСТРОЕК ПРИЛОЖЕНИЯ BEDROCK")
    
    # Проверка переменных окружения
    print("Проверка переменных окружения:")
    use_mock = os.environ.get("USE_MOCK_SENSORS", "")
    print(f"USE_MOCK_SENSORS: {use_mock or 'не задано'}")
    
    if use_mock == "1":
        print("Внимание: USE_MOCK_SENSORS=1 заставляет приложение использовать заглушки!")
        print("Измените эту настройку в файле start.sh")
    
    # Проверка прав на директории
    print("\nПроверка прав доступа к директориям:")
    app_dir = os.path.abspath(".")
    print(f"Текущая директория: {app_dir}")
    
    # Проверка файла sensor_service.py
    print("\nПроверка файла sensor_service.py:")
    service_path = os.path.join(app_dir, "services", "sensor_service.py")
    if os.path.exists(service_path):
        print(f"Файл существует: {service_path}")
        
        # Проверка содержимого файла
        with open(service_path, "r") as f:
            content = f.read()
            if "DummyBoard" in content:
                print("Найдена реализация заглушек (DummyBoard)")
            if "USE_MOCK_SENSORS" in content:
                print("Найдена проверка USE_MOCK_SENSORS")
            # Проверка адресов датчиков
            if f"ENS160_ADDRESS = 0x{ENS160_ADDRESS:X}" in content:
                print(f"Корректный адрес ENS160: 0x{ENS160_ADDRESS:X}")
            else:
                print(f"Возможно некорректный адрес ENS160 в файле")
            
            if f"AHT21_ADDRESS = 0x{AHT21_ADDRESS:X}" in content:
                print(f"Корректный адрес AHT21: 0x{AHT21_ADDRESS:X}")
            else:
                print(f"Возможно некорректный адрес AHT21 в файле")
    else:
        print(f"Файл не найден: {service_path}")
        print("Убедитесь, что файл существует и находится в нужной директории")

def fix_common_issues():
    """Исправление распространенных проблем"""
    print_header("ИСПРАВЛЕНИЕ РАСПРОСТРАНЕННЫХ ПРОБЛЕМ")
    
    fixes = [
        {
            "name": "Включить I2C в системе",
            "cmd": "sudo raspi-config nonint do_i2c 0",
            "desc": "Включает I2C интерфейс через raspi-config"
        },
        {
            "name": "Добавить пользователя в группу I2C",
            "cmd": f"sudo usermod -a -G i2c {os.environ.get('USER', 'pi')}",
            "desc": "Добавляет текущего пользователя в группу i2c"
        },
        {
            "name": "Установить права на устройства I2C",
            "cmd": "sudo chmod 666 /dev/i2c-*",
            "desc": "Устанавливает права доступа на устройства I2C"
        },
        {
            "name": "Создать постоянное правило доступа для I2C",
            "cmd": "echo 'KERNEL==\"i2c-[0-9]*\", GROUP=\"i2c\", MODE=\"0666\"' | sudo tee /etc/udev/rules.d/99-i2c-permissions.rules && sudo udevadm control --reload-rules && sudo udevadm trigger",
            "desc": "Создает правило udev для постоянных прав доступа к I2C"
        },
        {
            "name": "Обновить конфигурацию загрузки",
            "cmd": "grep -q 'dtparam=i2c_arm=on' /boot/config.txt || echo 'dtparam=i2c_arm=on' | sudo tee -a /boot/config.txt",
            "desc": "Проверяет и добавляет параметр i2c_arm в /boot/config.txt"
        },
        {
            "name": "Установить необходимые системные пакеты",
            "cmd": "sudo apt update && sudo apt install -y i2c-tools python3-smbus python3-pip",
            "desc": "Устанавливает необходимые пакеты для работы с I2C"
        },
        {
            "name": "Установить Python библиотеки",
            "cmd": "pip3 install adafruit-blinka adafruit-circuitpython-ahtx0 adafruit-circuitpython-ens160",
            "desc": "Устанавливает Python библиотеки для работы с датчиками"
        },
        {
            "name": "Отключить режим заглушек",
            "cmd": "sed -i 's/export USE_MOCK_SENSORS=1/export USE_MOCK_SENSORS=0/' start.sh",
            "desc": "Отключает режим заглушек в файле start.sh"
        }
    ]
    
    print("Выберите действия для исправления проблем:")
    for i, fix in enumerate(fixes):
        print(f"{i+1}. {fix['name']} - {fix['desc']}")
    
    print("\nВведите номера через запятую или 'all' для выполнения всех действий (0 для отмены):")
    choice = input("> ").strip().lower()
    
    if choice == '0':
        return
    
    if choice == 'all':
        selected = range(len(fixes))
    else:
        try:
            selected = [int(x.strip()) - 1 for x in choice.split(',') if x.strip()]
        except ValueError:
            print("Неверный ввод. Операция отменена.")
            return
    
    for i in selected:
        if 0 <= i < len(fixes):
            fix = fixes[i]
            print(f"\nВыполнение: {fix['name']}...")
            stdout, stderr, code = run_command(fix['cmd'])
            if code == 0:
                print(f"Успешно: {fix['name']}")
                if stdout:
                    print(stdout)
            else:
                print(f"Ошибка при выполнении: {stderr}")
        else:
            print(f"Пропуск неверного номера: {i+1}")
    
    print("\nЗавершено. Вам может потребоваться перезагрузка системы.")
    if input("Перезагрузить систему сейчас? (y/n): ").lower() == 'y':
        run_command("sudo reboot")

def main():
    """Основная функция диагностики"""
    print_header("ДИАГНОСТИКА ДАТЧИКОВ ENS160 И AHT21")
    print("Этот скрипт проверит подключение и работу датчиков для приложения Bedrock")
    print("Автор: Claude AI, 2025")
    
    # Проверяем, запущен ли скрипт с root правами
    if os.geteuid() == 0:
        print("\nВНИМАНИЕ: Скрипт запущен с правами root.")
        print("Некоторые тесты могут работать некорректно.")
        print("Рекомендуется запускать от обычного пользователя.")
        if input("Продолжить? (y/n): ").lower() != 'y':
            sys.exit(0)
    
    # Выполняем все проверки
    check_system_info()
    i2c_available = check_i2c_devices()
    test_i2c_permissions()
    install_dependencies()
    
    # Если I2C устройства доступны, пробуем читать данные
    if i2c_available:
        test_sensor_readings()
    
    # Проверка настроек приложения
    if os.path.exists("services"):
        check_app_configuration()
    
    # Предлагаем исправить проблемы
    if input("\nХотите выполнить исправления распространенных проблем? (y/n): ").lower() == 'y':
        fix_common_issues()
    
    print_header("ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("Результаты сохранены в файл sensor_diagnostic.log")
    print("Для дополнительной помощи обратитесь к документации или форумам Raspberry Pi")

if __name__ == "__main__":
    main()