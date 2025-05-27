#!/usr/bin/env python3

"""
Скрипт диагностики будильника Bedrock 2.0
Запускать из корневой директории проекта
"""

import os
import sys
import json
from datetime import datetime, timedelta

def check_alarm_config():
    """Проверить конфигурацию будильника"""
    print("🔍 Проверка конфигурации будильника...")
    
    config_path = "config/alarm.json"
    
    if not os.path.exists(config_path):
        print(f"❌ Файл конфигурации не найден: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ Конфиг загружен: {config_path}")
        
        if "alarm" not in config:
            print("❌ Отсутствует секция 'alarm' в конфигурации")
            return False
        
        alarm = config["alarm"]
        
        print(f"⏰ Время: {alarm.get('time', 'НЕ ЗАДАНО')}")
        print(f"🔴 Включен: {alarm.get('enabled', False)}")
        print(f"📅 Дни: {alarm.get('repeat', [])}")
        print(f"🎵 Мелодия: {alarm.get('ringtone', 'НЕ ЗАДАНО')}")
        print(f"🔊 Fade-in: {alarm.get('fadein', False)}")
        
        # Проверить формат времени
        alarm_time = alarm.get('time', '')
        if not alarm_time:
            print("❌ Время будильника не задано")
            return False
        
        try:
            datetime.strptime(alarm_time, "%H:%M")
            print(f"✅ Формат времени корректный: {alarm_time}")
        except ValueError:
            print(f"❌ Неверный формат времени: {alarm_time}")
            return False
        
        # Проверить дни недели
        valid_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        repeat_days = alarm.get('repeat', [])
        
        if not repeat_days:
            print("❌ Не заданы дни повторения")
            return False
        
        for day in repeat_days:
            if day not in valid_days:
                print(f"❌ Неверный день недели: {day}")
                return False
        
        print(f"✅ Дни недели корректные: {repeat_days}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации: {e}")
        return False

def check_ringtones():
    """Проверить наличие файлов мелодий"""
    print("\n🎵 Проверка файлов мелодий...")
    
    ringtones_dir = "media/ringtones"
    
    if not os.path.exists(ringtones_dir):
        print(f"❌ Директория мелодий не найдена: {ringtones_dir}")
        return False
    
    # Загружаем конфигурацию для получения текущей мелодии
    config_path = "config/alarm.json"
    current_ringtone = "robot.mp3"  # по умолчанию
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            current_ringtone = config.get("alarm", {}).get("ringtone", "robot.mp3")
        except:
            pass
    
    print(f"🎵 Текущая мелодия: {current_ringtone}")
    
    # Проверяем наличие файлов
    files = []
    try:
        files = [f for f in os.listdir(ringtones_dir) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        print(f"📁 Найдено мелодий: {len(files)}")
        
        for file in files:
            file_path = os.path.join(ringtones_dir, file)
            file_size = os.path.getsize(file_path)
            status = "✅" if file == current_ringtone else "  "
            print(f"{status} {file} ({file_size} bytes)")
        
        # Проверяем текущую мелодию
        current_path = os.path.join(ringtones_dir, current_ringtone)
        if os.path.exists(current_path):
            print(f"✅ Текущая мелодия найдена: {current_path}")
            return True
        else:
            print(f"❌ Текущая мелодия не найдена: {current_path}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка чтения директории мелодий: {e}")
        return False

def check_current_time():
    """Проверить текущее время и сравнить с будильником"""
    print("\n🕐 Анализ времени...")
    
    now = datetime.now()
    current_day = now.strftime("%a")
    current_time = now.strftime("%H:%M")
    
    print(f"🕐 Текущее время: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 День недели: {current_day}")
    print(f"⏰ Время (HH:MM): {current_time}")
    
    # Загружаем конфигурацию будильника
    config_path = "config/alarm.json"
    if not os.path.exists(config_path):
        print("❌ Нет конфигурации для сравнения")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        alarm = config.get("alarm", {})
        alarm_time = alarm.get("time", "")
        alarm_enabled = alarm.get("enabled", False)
        alarm_days = alarm.get("repeat", [])
        
        print(f"\n⏰ Будильник: {alarm_time}")
        print(f"🔴 Включен: {alarm_enabled}")
        print(f"📅 Дни: {alarm_days}")
        
        # Проверяем условия срабатывания
        time_matches = current_time == alarm_time
        day_matches = current_day in alarm_days
        
        print(f"\n🔍 Анализ условий:")
        print(f"  ⏰ Время совпадает: {time_matches} (нужно {alarm_time}, сейчас {current_time})")
        print(f"  📅 День совпадает: {day_matches} (нужно {alarm_days}, сейчас {current_day})")
        print(f"  🔴 Включен: {alarm_enabled}")
        
        should_trigger = alarm_enabled and time_matches and day_matches
        print(f"\n🚨 Должен сработать: {should_trigger}")
        
        if should_trigger:
            print("✅ ВСЕ УСЛОВИЯ ВЫПОЛНЕНЫ - БУДИЛЬНИК ДОЛЖЕН СРАБОТАТЬ!")
        else:
            print("⏸️ Условия не выполнены - будильник не должен сработать")
        
        # Показываем следующее время срабатывания
        if alarm_enabled and alarm_time and alarm_days:
            show_next_alarm_time(alarm_time, alarm_days)
        
    except Exception as e:
        print(f"❌ Ошибка анализа времени: {e}")

def show_next_alarm_time(alarm_time, alarm_days):
    """Показать следующее время срабатывания будильника"""
    print(f"\n📅 Следующие срабатывания:")
    
    try:
        # Парсим время будильника
        alarm_hour, alarm_minute = map(int, alarm_time.split(':'))
        
        # Мапинг дней недели
        day_mapping = {
            "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, 
            "Fri": 4, "Sat": 5, "Sun": 6
        }
        
        # Получаем номера дней
        alarm_weekdays = [day_mapping[day] for day in alarm_days if day in day_mapping]
        
        now = datetime.now()
        
        # Ищем следующие 3 срабатывания
        found = 0
        check_date = now.replace(hour=alarm_hour, minute=alarm_minute, second=0, microsecond=0)
        
        for i in range(14):  # Проверяем 2 недели вперед
            check_weekday = check_date.weekday()
            
            if check_weekday in alarm_weekdays and check_date > now:
                day_name = check_date.strftime("%a")
                time_str = check_date.strftime("%Y-%m-%d %H:%M")
                delta = check_date - now
                
                if delta.days == 0:
                    when = f"сегодня через {delta.seconds // 3600}ч {(delta.seconds % 3600) // 60}м"
                elif delta.days == 1:
                    when = "завтра"
                else:
                    when = f"через {delta.days} дней"
                
                print(f"  🔔 {time_str} ({day_name}) - {when}")
                
                found += 1
                if found >= 3:
                    break
            
            check_date += timedelta(days=1)
        
        if found == 0:
            print("  ❌ Следующие срабатывания не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка расчета следующего времени: {e}")

def test_alarm_trigger():
    """Тест срабатывания будильника"""
    print("\n🧪 Тест срабатывания будильника...")
    
    try:
        # Импортируем модули приложения
        sys.path.insert(0, '.')
        from services.alarm_service import AlarmService
        from services.sound_service import SoundService
        
        print("✅ Модули загружены")
        
        # Создаем сервисы
        alarm_service = AlarmService()
        sound_service = SoundService()
        
        print("✅ Сервисы созданы")
        
        # Получаем конфигурацию
        alarm_config = alarm_service.get_alarm()
        if not alarm_config:
            print("❌ Не удалось получить конфигурацию будильника")
            return
        
        print(f"✅ Конфигурация получена: {alarm_config}")
        
        # Проверяем мелодию
        ringtone = alarm_config.get("ringtone", "robot.mp3")
        ringtone_path = os.path.join("media/ringtones", ringtone)
        
        if not os.path.exists(ringtone_path):
            print(f"❌ Файл мелодии не найден: {ringtone_path}")
            return
        
        print(f"✅ Файл мелодии найден: {ringtone_path}")
        
        # Тестируем загрузку звука
        sound = sound_service.load_sound_file(ringtone_path)
        if sound:
            print("✅ Звук загружен успешно")
            print("🎵 Тест воспроизведения (3 секунды)...")
            
            sound.play()
            import time
            time.sleep(3)
            sound.stop()
            
            print("✅ Тест воспроизведения завершен")
        else:
            print("❌ Не удалось загрузить звук")
        
        # Cleanup
        sound_service.cleanup()
        
    except ImportError as e:
        print(f"❌ Ошибка импорта модулей: {e}")
        print("💡 Убедитесь, что запускаете скрипт из корневой директории проекта")
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")

def create_test_alarm():
    """Создать тестовый будильник на ближайшую минуту"""
    print("\n🧪 Создание тестового будильника...")
    
    # Время через 2 минуты
    test_time = datetime.now() + timedelta(minutes=2)
    test_time_str = test_time.strftime("%H:%M")
    test_day = test_time.strftime("%a")
    
    print(f"⏰ Тестовый будильник: {test_time_str} ({test_day})")
    
    config_path = "config/alarm.json"
    backup_path = config_path + ".backup"
    
    try:
        # Создаем backup
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                original_config = f.read()
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_config)
            
            print(f"✅ Backup создан: {backup_path}")
        
        # Создаем тестовую конфигурацию
        test_config = {
            "alarm": {
                "time": test_time_str,
                "enabled": True,
                "repeat": [test_day],
                "ringtone": "robot.mp3",
                "fadein": False
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, indent=2)
        
        print(f"✅ Тестовый будильник создан: {test_time_str}")
        print(f"📅 День: {test_day}")
        print("🔔 Будильник сработает через ~2 минуты")
        print(f"⚠️ Для восстановления: mv {backup_path} {config_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания тестового будильника: {e}")
        return False

def restore_backup():
    """Восстановить backup конфигурации"""
    config_path = "config/alarm.json"
    backup_path = config_path + ".backup"
    
    if os.path.exists(backup_path):
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            
            os.remove(backup_path)
            print("✅ Конфигурация восстановлена из backup")
            return True
        except Exception as e:
            print(f"❌ Ошибка восстановления: {e}")
            return False
    else:
        print("❌ Backup не найден")
        return False

def main():
    """Главная функция диагностики"""
    print("🚨 ДИАГНОСТИКА БУДИЛЬНИКА BEDROCK 2.0")
    print("=" * 50)
    
    if not os.path.exists("main.py"):
        print("❌ Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Базовые проверки
    config_ok = check_alarm_config()
    ringtones_ok = check_ringtones()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
    print(f"  🔧 Конфигурация: {'✅ OK' if config_ok else '❌ ОШИБКА'}")
    print(f"  🎵 Мелодии: {'✅ OK' if ringtones_ok else '❌ ОШИБКА'}")
    
    if config_ok:
        check_current_time()
    
    print("\n" + "=" * 50)
    print("🛠️ ДОСТУПНЫЕ ДЕЙСТВИЯ:")
    print("  1. Тест воспроизведения мелодии")
    print("  2. Создать тестовый будильник (через 2 мин)")
    print("  3. Восстановить backup конфигурации")
    print("  4. Выход")
    
    while True:
        try:
            choice = input("\nВыберите действие (1-4): ").strip()
            
            if choice == "1":
                test_alarm_trigger()
            elif choice == "2":
                create_test_alarm()
            elif choice == "3":
                restore_backup()
            elif choice == "4":
                print("👋 Выход")
                break
            else:
                print("❌ Неверный выбор")
                
        except KeyboardInterrupt:
            print("\n👋 Выход")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()