"""
Общие утилиты для проекта Bedrock
"""
import os
import json
import logging
from datetime import datetime
from kivy.app import App
from kivymd.uix.screen import MDScreen

logger = logging.getLogger("CommonUtils")

class Constants:
    """Константы проекта"""
    
    # Файлы конфигурации
    USER_CONFIG_PATH = "config/user.json"
    ALARM_CONFIG_PATH = "config/alarm.json"
    SCHEDULE_CONFIG_PATH = "config/schedule.json"
    PIGS_CONFIG_PATH = "config/pigs.json"
    NOTIFICATIONS_CONFIG_PATH = "config/notifications.json"
    
    # Пути к ресурсам
    THEMES_DIR = "themes"
    ASSETS_DIR = "assets"
    MEDIA_DIR = "media"
    CACHE_DIR = "cache"
    LOGS_DIR = "logs"
    
    # Настройки по умолчанию
    DEFAULT_THEME = "minecraft"
    DEFAULT_MODE = "light"
    DEFAULT_FONT = "Minecraftia"
    
    # Размеры UI
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600
    MENU_HEIGHT = 70
    
    # Интервалы обновления (секунды)
    CLOCK_UPDATE_INTERVAL = 1
    WEATHER_UPDATE_INTERVAL = 900  # 15 минут
    SENSOR_UPDATE_INTERVAL = 30
    NOTIFICATION_UPDATE_INTERVAL = 30

def safe_json_load(file_path, default=None):
    """Безопасная загрузка JSON файла"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON {file_path}: {e}")
    
    return default or {}

def safe_json_save(file_path, data):
    """Безопасное сохранение JSON файла"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON {file_path}: {e}")
        return False

def get_current_time_str():
    """Получить текущее время как строку ISO"""
    return datetime.now().isoformat()

def parse_time_str(time_str):
    """Безопасный парсинг времени из строки"""
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Error parsing time {time_str}: {e}")
        return datetime.now()

class BasePage(MDScreen):
    """Базовый класс для всех страниц"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._timers = []
    
    def safe_get_widget(self, widget_id):
        """Безопасное получение виджета по ID"""
        if hasattr(self, 'ids') and hasattr(self.ids, widget_id):
            return getattr(self.ids, widget_id)
        return None
    
    def safe_set_widget_text(self, widget_id, text):
        """Безопасная установка текста виджета"""
        widget = self.safe_get_widget(widget_id)
        if widget and hasattr(widget, 'text'):
            widget.text = str(text)
            return True
        return False
    
    def get_app(self):
        """Получить экземпляр приложения"""
        return App.get_running_app()
    
    def schedule_timer(self, callback, interval):
        """Запланировать таймер с автоочисткой"""
        from kivy.clock import Clock
        timer = Clock.schedule_interval(callback, interval)
        self._timers.append(timer)
        return timer
    
    def schedule_once(self, callback, timeout):
        """Запланировать однократное выполнение с автоочисткой"""
        from kivy.clock import Clock
        timer = Clock.schedule_once(callback, timeout)
        self._timers.append(timer)
        return timer
    
    def cleanup_timers(self):
        """Очистить все таймеры"""
        for timer in self._timers:
            try:
                timer.cancel()
            except Exception as e:
                logger.error(f"Error canceling timer: {e}")
        self._timers.clear()
    
    def on_leave(self):
        """Автоматическая очистка при выходе с экрана"""
        self.cleanup_timers()
        super().on_leave()

class ConfigManager:
    """Централизованное управление конфигурацией"""
    
    def __init__(self):
        self._configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Загрузить все конфигурации"""
        config_files = {
            'user': Constants.USER_CONFIG_PATH,
            'alarm': Constants.ALARM_CONFIG_PATH,
            'schedule': Constants.SCHEDULE_CONFIG_PATH,
            'pigs': Constants.PIGS_CONFIG_PATH,
            'notifications': Constants.NOTIFICATIONS_CONFIG_PATH
        }
        
        for name, path in config_files.items():
            try:
                self._configs[name] = self._load_config_with_defaults(name, path)
            except Exception as e:
                logger.error(f"Error loading config {name}: {e}")
                self._configs[name] = self._get_default_config(name)
    
    def _load_config_with_defaults(self, name, path):
        """Загрузить конфиг с fallback значениями"""
        defaults = self._get_default_config(name)
        config = safe_json_load(path, defaults)
        
        # ИСПРАВЛЕНИЕ: Проверяем что defaults это словарь перед вызовом .items()
        if isinstance(defaults, dict) and isinstance(config, dict):
            # Merge with defaults to ensure all keys exist
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
        elif isinstance(defaults, list):
            # Для списков (например notifications) просто используем загруженные данные или defaults
            if not isinstance(config, list):
                config = defaults
        
        return config
    
    def _get_default_config(self, name):
        """Получить конфигурацию по умолчанию"""
        defaults = {
            'user': {
                "theme": Constants.DEFAULT_THEME,
                "theme_mode": Constants.DEFAULT_MODE,
                "username": "User",
                "birthdate": "2000-01-01",
                "auto_theme_enabled": True,
                "theme_switch_delay": 2,
                "volume_settings": {
                    "enabled": True,
                    "step": 5,
                    "min_volume": 0,
                    "max_volume": 100,
                    "feedback_sounds": True
                },
                "sensor_settings": {
                    "light_sensor_enabled": True,
                    "calibration_time": 2,
                    "mock_mode": False
                }
            },
            'alarm': {
                "alarm": {
                    "time": "07:30",
                    "enabled": False,
                    "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                    "ringtone": "morning.mp3",
                    "fadein": False
                }
            },
            'schedule': {str(d): [] for d in range(1, 8)},
            'pigs': {
                "pigs": [{"name": "Korovka"}, {"name": "Karamelka"}],
                "bars": {
                    "water": {"label": "Water", "max_hours": 8, "last_reset": get_current_time_str()},
                    "food": {"label": "Food", "max_hours": 6, "last_reset": get_current_time_str()},
                    "clean": {"label": "Cleaning", "max_hours": 12, "last_reset": get_current_time_str()}
                }
            },
            # ИСПРАВЛЕНИЕ: notifications должно быть списком по умолчанию
            'notifications': []
        }
        return defaults.get(name, {})
    
    def get_config(self, name):
        """Получить конфигурацию"""
        return self._configs.get(name, self._get_default_config(name))
    
    def update_config(self, name, data):
        """Обновить конфигурацию"""
        if name in self._configs:
            if isinstance(self._configs[name], dict) and isinstance(data, dict):
                self._configs[name].update(data)
            else:
                self._configs[name] = data
    
    def save_config(self, name):
        """Сохранить конфигурацию"""
        if name in self._configs:
            config_paths = {
                'user': Constants.USER_CONFIG_PATH,
                'alarm': Constants.ALARM_CONFIG_PATH,
                'schedule': Constants.SCHEDULE_CONFIG_PATH,
                'pigs': Constants.PIGS_CONFIG_PATH,
                'notifications': Constants.NOTIFICATIONS_CONFIG_PATH
            }
            path = config_paths.get(name)
            if path:
                return safe_json_save(path, self._configs[name])
        return False
    
    def save_all_configs(self):
        """Сохранить все конфигурации"""
        success = True
        for name in self._configs.keys():
            try:
                if not self.save_config(name):
                    success = False
                    logger.error(f"Failed to save config: {name}")
            except Exception as e:
                logger.error(f"Error saving config {name}: {e}")
                success = False
        return success

# Глобальный экземпляр с защитой от ошибок
try:
    config_manager = ConfigManager()
except Exception as e:
    logger.error(f"Failed to initialize ConfigManager: {e}")
    # Создаем заглушку чтобы приложение не упало
    class DummyConfigManager:
        def get_config(self, name):
            return {}
        def update_config(self, name, data):
            pass
        def save_config(self, name):
            return False
        def save_all_configs(self):
            return False
    
    config_manager = DummyConfigManager()