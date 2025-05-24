#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новых датчиков:
- LDR модуль (датчик освещённости) 
- Кнопки громкости (Volume UP/DOWN)

Запуск на Raspberry Pi:
cd /home/standa/bedrock-app
python test_new_sensors.py
"""

import time
import sys
import os

# Цвета для консоли
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def log(msg): print(f"{GREEN}[INFO] {msg}{NC}")
def warn(msg): print(f"{YELLOW}[WARN] {msg}{NC}")
def error(msg): print(f"{RED}[ERROR] {msg}{NC}")
def info(msg): print(f"{BLUE}[INFO] {msg}{NC}")

class NewSensorsTest:
    def __init__(self):
        self.gpio_handle = None
        self.gpio_lib = None
        self.LDR_PIN = 18
        self.VOL_UP_PIN = 23
        self.VOL_DOWN_PIN = 24
        
        # Состояния для обнаружения изменений
        self.last_light = None
        self.last_vol_up = None
        self.last_vol_down = None
        
    def init_gpio(self):
        """Инициализация GPIO библиотеки"""
        log("Инициализация GPIO...")
        
        # Пробуем lgpio (для Pi 5)
        try:
            import lgpio
            self.gpio_lib = "lgpio"
            self.gpio_handle = lgpio.gpiochip_open(0)
            
            # Настройка пинов
            lgpio.gpio_claim_input(self.gpio_handle, self.LDR_PIN)
            lgpio.gpio_claim_input(self.gpio_handle, self.VOL_UP_PIN, lgpio.SET_PULL_UP)
            lgpio.gpio_claim_input(self.gpio_handle, self.VOL_DOWN_PIN, lgpio.SET_PULL_UP)
            
            log(f"✅ Используем lgpio для Pi 5")
            return True
            
        except ImportError:
            warn("lgpio недоступно, пробуем RPi.GPIO...")
            
        # Пробуем RPi.GPIO (старая версия)
        try:
            import RPi.GPIO as GPIO
            self.gpio_lib = "RPi.GPIO"
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.LDR_PIN, GPIO.IN)
            GPIO.setup(self.VOL_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.VOL_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            log(f"✅ Используем RPi.GPIO")
            return True
            
        except ImportError:
            error("❌ Ни одна GPIO библиотека не доступна!")
            return False
    
    def read_sensors(self):
        """Чтение всех датчиков"""
        try:
            if self.gpio_lib == "lgpio":
                import lgpio
                light = lgpio.gpio_read(self.gpio_handle, self.LDR_PIN)
                vol_up = lgpio.gpio_read(self.gpio_handle, self.VOL_UP_PIN)
                vol_down = lgpio.gpio_read(self.gpio_handle, self.VOL_DOWN_PIN)
                
            elif self.gpio_lib == "RPi.GPIO":
                import RPi.GPIO as GPIO
                light = GPIO.input(self.LDR_PIN)
                vol_up = GPIO.input(self.VOL_UP_PIN)
                vol_down = GPIO.input(self.VOL_DOWN_PIN)
                
            else:
                return None, None, None
                
            return light, vol_up, vol_down
            
        except Exception as e:
            error(f"Ошибка чтения датчиков: {e}")
            return None, None, None
    
    def test_light_sensor(self, light_value):
        """Тест датчика освещённости"""
        if light_value != self.last_light:
            if light_value == 1:
                info("☀️  СВЕТЛО - Обнаружен яркий свет!")
                info("   → Рекомендация: переключить на LIGHT тему")
            else:
                info("🌙 ТЕМНО - Низкое освещение")
                info("   → Рекомендация: переключить на DARK тему")
            self.last_light = light_value
    
    def test_volume_buttons(self, vol_up, vol_down):
        """Тест кнопок громкости"""
        # Volume UP (нажатие = 0, отпускание = 1)
        if vol_up != self.last_vol_up:
            if vol_up == 0:
                info("🔊 VOLUME UP нажата!")
                info("   → Команда: увеличить громкость")
            self.last_vol_up = vol_up
        
        # Volume DOWN (нажатие = 0, отпускание = 1)  
        if vol_down != self.last_vol_down:
            if vol_down == 0:
                info("🔉 VOLUME DOWN нажата!")
                info("   → Команда: уменьшить громкость")
            self.last_vol_down = vol_down
    
    def show_status(self, light, vol_up, vol_down):
        """Показать текущий статус всех датчиков"""
        # Очистка строки для обновления
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        
        # Статус датчика освещённости
        light_status = "☀️ СВЕТЛО" if light == 1 else "🌙 ТЕМНО"
        
        # Статус кнопок (инвертированная логика - 0 = нажата)
        vol_up_status = "🔊⬇️" if vol_up == 0 else "🔊  "
        vol_down_status = "🔉⬇️" if vol_down == 0 else "🔉  "
        
        # Вывод статуса в одной строке
        status = f"Свет: {light_status} | {vol_up_status} | {vol_down_status}"
        sys.stdout.write(status)
        sys.stdout.flush()
    
    def run_test(self, duration=60):
        """Запуск тестирования"""
        if not self.init_gpio():
            return False
            
        log(f"🧪 Начинаю тест новых датчиков на {duration} секунд...")
        log("💡 Попробуйте закрыть/открыть датчик освещённости")
        log("🔘 Попробуйте нажать кнопки громкости")
        log("🛑 Нажмите Ctrl+C для остановки")
        print()
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Читаем все датчики
                light, vol_up, vol_down = self.read_sensors()
                
                if light is None:
                    error("Ошибка чтения датчиков")
                    break
                
                # Проверяем изменения и выводим уведомления
                self.test_light_sensor(light)
                self.test_volume_buttons(vol_up, vol_down)
                
                # Показываем текущий статус
                self.show_status(light, vol_up, vol_down)
                
                time.sleep(0.1)  # Обновление 10 раз в секунду
                
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Тест остановлен пользователем{NC}")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                import lggio
                lgpio.gpiochip_close(self.gpio_handle)
                log("✅ lgpio очищено")
                
            elif self.gpio_lib == "RPi.GPIO":
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                log("✅ RPi.GPIO очищено")
                
        except Exception as e:
            warn(f"Предупреждение при очистке: {e}")

def system_info():
    """Информация о системе"""
    log("🖥️  Информация о системе:")
    try:
        # Версия Pi
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
        info(f"   Модель: {model}")
        
        # Проверка GPIO утилит
        if os.system('which gpio > /dev/null 2>&1') == 0:
            info("   ✅ GPIO утилиты установлены")
        else:
            warn("   ❌ GPIO утилиты не найдены (установите: sudo apt install wiringpi)")
            
        # Проверка I2C
        if os.system('which i2cdetect > /dev/null 2>&1') == 0:
            info("   ✅ I2C утилиты доступны")
        else:
            warn("   ❌ I2C утилиты не найдены")
            
    except Exception as e:
        warn(f"Не удалось получить информацию о системе: {e}")

def check_current_sensors():
    """Проверка текущих I2C датчиков"""
    log("🔍 Проверка существующих I2C датчиков...")
    
    try:
        # Проверяем I2C устройства
        result = os.popen('i2cdetect -y 1').read()
        
        if '38' in result and '53' in result:
            info("   ✅ ENS160 (0x53) и AHT21 (0x38) найдены")
        elif '38' in result:
            info("   ✅ AHT21 (0x38) найден")
            warn("   ❌ ENS160 (0x53) не найден")
        elif '53' in result:
            info("   ✅ ENS160 (0x53) найден") 
            warn("   ❌ AHT21 (0x38) не найден")
        else:
            warn("   ❌ I2C датчики не обнаружены")
            
    except Exception as e:
        warn(f"Ошибка проверки I2C: {e}")

def main():
    """Главная функция"""
    print(f"{BLUE}=" * 60)
    print(f"🧪 ТЕСТИРОВАНИЕ НОВЫХ ДАТЧИКОВ BEDROCK v2.0")
    print(f"=" * 60 + f"{NC}")
    
    system_info()
    print()
    check_current_sensors() 
    print()
    
    # Запуск теста
    tester = NewSensorsTest()
    tester.run_test(duration=120)  # 2 минуты тестирования
    
    print(f"\n{GREEN}✅ Тестирование завершено!{NC}")
    log("📋 Результаты:")
    log("   - Если датчик освещённости работает → готов к интеграции") 
    log("   - Если кнопки реагируют → готовы к программированию")
    log("   - Если есть проблемы → проверьте подключение по схеме")

if __name__ == "__main__":
    main()