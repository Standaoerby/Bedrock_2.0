#!/usr/bin/env python3

"""
Bedrock 2.0 Health Check
Проверка консистентности конфигурации и системы
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

class HealthChecker:
    """Класс для проверки здоровья системы Bedrock"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.fixes_applied = []
        
    def log_issue(self, message, level="ERROR"):
        """Логирование проблемы"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {level}: {message}"
        
        if level == "ERROR":
            self.issues.append(message)
            print(f"❌ {formatted}")
        elif level == "WARNING":
            self.warnings.append(message)
            print(f"⚠️  {formatted}")
        elif level == "INFO":
            print(f"ℹ️  {formatted}")
        elif level == "SUCCESS":
            print(f"✅ {formatted}")
    
    def check_config_files(self):
        """Проверка конфигурационных файлов"""
        print("\n🔍 Checking configuration files...")
        
        config_files = {
            "config/alarm.json": self._check_alarm_config,
            "config/user.json": self._check_user_config,
            "config/schedule.json": self._check_schedule_config,
            "config/pigs.json": self._check_pigs_config,
            "config/notifications.json": self._check_notifications_config
        }
        
        for file_path, checker in config_files.items():
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    checker(data, file_path)
                    self.log_issue(f"Config {file_path} is valid", "SUCCESS")
                except json.JSONDecodeError as e:
                    self.log_issue(f"Invalid JSON in {file_path}: {e}")
                except Exception as e:
                    self.log_issue(f"Error reading {file_path}: {e}")
            else:
                self.log_issue(f"Missing config file: {file_path}")
    
    def _check_alarm_config(self, data, file_path):
        """Проверка конфигурации будильника"""
        # Проверка на старую структуру (дублирование)
        if "time" in data and "alarm" in data:
            self.log_issue(f"Alarm config has duplicate structure in {file_path}")
            return False
        
        # Проверка корректной структуры
        if "alarm" not in data:
            self.log_issue(f"Missing 'alarm' key in {file_path}")
            return False
            
        alarm = data["alarm"]
        required_fields = ["time", "enabled", "repeat", "ringtone", "fadein"]
        
        for field in required_fields:
            if field not in alarm:
                self.log_issue(f"Missing field '{field}' in alarm config")
        
        # Проверка формата времени
        time_str = alarm.get("time", "")
        if not self._is_valid_time_format(time_str):
            self.log_issue(f"Invalid time format in alarm: {time_str}")
        
        return True
    
    def _check_user_config(self, data, file_path):
        """Проверка пользовательской конфигурации"""
        required_fields = ["theme", "theme_mode", "username", "auto_theme_enabled"]
        
        for field in required_fields:
            if field not in data:
                self.log_issue(f"Missing field '{field}' in user config")
        
        # Проверка значений
        if data.get("theme_mode") not in ["light", "dark"]:
            self.log_issue(f"Invalid theme_mode: {data.get('theme_mode')}")
            
        return True
    
    def _check_schedule_config(self, data, file_path):
        """Проверка конфигурации расписания"""
        # Проверка что есть дни 1-7
        for day in range(1, 8):
            if str(day) not in data:
                self.log_issue(f"Missing day {day} in schedule config", "WARNING")
        
        return True
    
    def _check_pigs_config(self, data, file_path):
        """Проверка конфигурации питомцев"""
        if "bars" not in data:
            self.log_issue("Missing 'bars' in pigs config")
            return False
        
        required_bars = ["water", "food", "clean"]
        for bar in required_bars:
            if bar not in data["bars"]:
                self.log_issue(f"Missing bar '{bar}' in pigs config")
        
        return True
    
    def _check_notifications_config(self, data, file_path):
        """Проверка конфигурации уведомлений"""
        if not isinstance(data, list):
            self.log_issue("Notifications config should be a list")
            return False
        
        return True
    
    def check_theme_files(self):
        """Проверка файлов тем"""
        print("\n🎨 Checking theme files...")
        
        theme_dir = "themes/minecraft"
        modes = ["light", "dark"]
        
        for mode in modes:
            theme_path = f"{theme_dir}/{mode}/theme.json"
            
            if os.path.exists(theme_path):
                try:
                    with open(theme_path, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                    
                    self._check_theme_structure(theme_data, mode)
                    self.log_issue(f"Theme {mode} is valid", "SUCCESS")
                    
                except Exception as e:
                    self.log_issue(f"Error in {mode} theme: {e}")
            else:
                self.log_issue(f"Missing {mode} theme file: {theme_path}")
    
    def _check_theme_structure(self, theme_data, mode):
        """Проверка структуры темы"""
        required_fields = [
            "theme_name", "theme_mode", "background_image", 
            "font_name", "font_color", "colors"
        ]
        
        for field in required_fields:
            if field not in theme_data:
                self.log_issue(f"Missing field '{field}' in {mode} theme", "WARNING")
        
        # Проверка overlay изображений
        overlay_images = theme_data.get("overlay_images", {})
        expected_pages = ["home", "alarm", "schedule", "weather", "pigs", "settings"]
        
        for page in expected_pages:
            if page not in overlay_images:
                self.log_issue(f"Missing overlay for {page} in {mode} theme", "WARNING")
    
    def check_directory_structure(self):
        """Проверка структуры директорий"""
        print("\n📁 Checking directory structure...")
        
        required_dirs = [
            "assets/fonts", "assets/sounds", "assets/images",
            "themes/minecraft/light", "themes/minecraft/dark",
            "media/ringtones", "cache", "config", "logs",
            "services", "classes", "pages", "utils"
        ]
        
        for directory in required_dirs:
            if os.path.exists(directory):
                self.log_issue(f"Directory {directory} exists", "SUCCESS")
            else:
                self.log_issue(f"Missing directory: {directory}", "WARNING")
    
    def check_critical_files(self):
        """Проверка критических файлов"""
        print("\n📄 Checking critical files...")
        
        critical_files = [
            "main.py", "main.kv", "requirements.txt",
            "bedrock_launcher.py",
            "utils/common.py", "utils/theme_manager.py"
        ]
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                self.log_issue(f"File {file_path} exists", "SUCCESS")
            else:
                self.log_issue(f"Missing critical file: {file_path}")
    
    def check_autostart_conflicts(self):
        """Проверка конфликтов autostart"""
        print("\n🔄 Checking autostart conflicts...")
        
        autostart_dir = os.path.expanduser("~/.config/autostart")
        if not os.path.exists(autostart_dir):
            self.log_issue("Autostart directory doesn't exist", "INFO")
            return
        
        bedrock_files = []
        for file in os.listdir(autostart_dir):
            if file.startswith("bedrock") and file.endswith(".desktop"):
                bedrock_files.append(file)
        
        if len(bedrock_files) == 0:
            self.log_issue("No Bedrock autostart files found", "WARNING")
        elif len(bedrock_files) == 1:
            self.log_issue(f"Single autostart file: {bedrock_files[0]}", "SUCCESS")
        else:
            self.log_issue(f"Multiple autostart files found: {bedrock_files}")
    
    def fix_common_issues(self):
        """Автоисправление частых проблем"""
        print("\n🔧 Applying automatic fixes...")
        
        # Создание недостающих директорий
        required_dirs = [
            "assets/fonts", "assets/sounds", "assets/images",
            "cache", "logs"
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    self.fixes_applied.append(f"Created directory: {directory}")
                    self.log_issue(f"Created missing directory: {directory}", "SUCCESS")
                except Exception as e:
                    self.log_issue(f"Failed to create directory {directory}: {e}")
        
        # Исправление alarm.json если есть дублирование
        self._fix_alarm_config()
    
    def _fix_alarm_config(self):
        """Исправление конфигурации будильника"""
        alarm_path = "config/alarm.json"
        
        if not os.path.exists(alarm_path):
            return
        
        try:
            with open(alarm_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверка на дублирование
            if "time" in data and "alarm" in data:
                # Удаляем дублированные поля в корне
                alarm_data = data["alarm"]
                fixed_data = {"alarm": alarm_data}
                
                # Создаем backup
                backup_path = f"{alarm_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # Сохраняем исправленную версию
                with open(alarm_path, 'w', encoding='utf-8') as f:
                    json.dump(fixed_data, f, ensure_ascii=False, indent=2)
                
                self.fixes_applied.append("Fixed alarm.json duplicate structure")
                self.log_issue("Fixed alarm.json duplicate structure", "SUCCESS")
                
        except Exception as e:
            self.log_issue(f"Failed to fix alarm config: {e}")
    
    def _is_valid_time_format(self, time_str):
        """Проверка формата времени HH:MM"""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except:
            return False
    
    def generate_report(self):
        """Генерация отчета о проверке"""
        print("\n" + "=" * 60)
        print("📊 HEALTH CHECK REPORT")
        print("=" * 60)
        
        print(f"\n✅ Fixes Applied: {len(self.fixes_applied)}")
        for fix in self.fixes_applied:
            print(f"   • {fix}")
        
        print(f"\n⚠️  Warnings: {len(self.warnings)}")
        for warning in self.warnings:
            print(f"   • {warning}")
        
        print(f"\n❌ Errors: {len(self.issues)}")
        for issue in self.issues:
            print(f"   • {issue}")
        
        # Общий статус
        if len(self.issues) == 0:
            if len(self.warnings) == 0:
                print("\n🎉 SYSTEM STATUS: EXCELLENT - No issues found!")
            else:
                print("\n✅ SYSTEM STATUS: GOOD - Only warnings found")
        else:
            print("\n⚠️  SYSTEM STATUS: NEEDS ATTENTION - Errors found")
        
        print("\n💡 RECOMMENDATIONS:")
        if len(self.issues) > 0:
            print("   • Fix all errors before deployment")
        if len(self.warnings) > 0:
            print("   • Consider addressing warnings for optimal performance")
        
        return len(self.issues) == 0

def main():
    """Главная функция health check"""
    print("🏥 BEDROCK 2.0 HEALTH CHECK")
    print("=" * 40)
    
    # Проверяем что мы в правильной директории
    if not os.path.exists("main.py"):
        print("❌ Error: Run this script from the Bedrock project root directory")
        sys.exit(1)
    
    checker = HealthChecker()
    
    try:
        # Автоисправления
        if "--fix" in sys.argv:
            checker.fix_common_issues()
        
        # Основные проверки
        checker.check_config_files()
        checker.check_theme_files()
        checker.check_directory_structure()
        checker.check_critical_files()
        checker.check_autostart_conflicts()
        
        # Генерация отчета
        success = checker.generate_report()
        
        # Выход с соответствующим кодом
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Health check interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()