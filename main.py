from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.clock import Clock, mainthread
from kivy.core.image import Image as CoreImage
from kivy.cache import Cache
from kivy.core.window import Window
from services.alarm_service import AlarmService
from classes.alarm_clock import AlarmClock
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from services.sensor_service import SensorService
from services.sound_service import SoundService
from services.volume_service import VolumeControlService
from classes.marquee import MarqueeLabel
import os
import sys
import time
import json
import re
import threading
import logging
from utils.error_handler import ErrorHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BedrockApp")

# Import Config BEFORE any window creation
from kivy.config import Config

# Configure resolution and display
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '0')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'window_state', 'visible')
Config.set('graphics', 'resizable', '0')    
Config.set('graphics', 'show_cursor', '0')

# Configure environment variables
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Raspberry Pi specific settings
if sys.platform.startswith('linux'):
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'

def load_user_config():
    """Load user configuration from file"""
    try:
        with open("config/user.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {
            "theme": "minecraft",
            "theme_mode": "light",
            "auto_theme_enabled": True,
            "theme_switch_delay": 2,
            "username": "User",
            "birthdate": "2000-01-01"
        }

# Register font
try:
    LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
except Exception as e:
    logger.error(f"Error registering font: {e}")

# Import screens
try:
    from pages.home import HomeScreen
    from pages.alarm import AlarmScreen
    from pages.weather import WeatherScreen
    from pages.schedule import ScheduleScreen
    from pages.pigs import PigsScreen
    from pages.settings import SettingsScreen
except Exception as e:
    logger.error(f"Error importing screens: {e}")

class BedrockApp(MDApp):
    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)
    
    # Fixed scaling parameters
    ui_scale = NumericProperty(1.0)
    font_scale = NumericProperty(1.0)
    
    # Common UI metrics
    ui_metrics = DictProperty({
        'menu_height': 70,
        'menu_padding': 10,
        'content_padding': 15,
        'widget_spacing': 10,
        'widget_height': 48,
        'small_widget_height': 36,
    })
    
    # Theme configuration as properties
    theme_name = StringProperty("minecraft")
    theme_mode = StringProperty("light")
    theme_config = DictProperty({})
    
    # Auto theme properties
    auto_theme_enabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        # Load user configuration
        self.user_config = load_user_config()
        
        # Initialize theme properties
        self.theme_name = self.user_config.get("theme", "minecraft")
        self.theme_mode = self.user_config.get("theme_mode", "light")
        self.auto_theme_enabled = self.user_config.get("auto_theme_enabled", True)
        
        # Initialize sound service
        self.sound_service = SoundService()
        
        # Auto theme event
        self._auto_theme_event = None
        
        # Call parent init
        super(BedrockApp, self).__init__(**kwargs)
        
        # Load theme config
        self.load_theme_config()

    def load_theme_config(self):
        """УПРОЩЁННАЯ загрузка конфигурации темы"""
        try:
            theme_path = f"themes/{self.theme_name}/{self.theme_mode}/theme.json"
            
            if not os.path.exists(theme_path) and self.theme_mode == "dark":
                # Create default dark theme
                self.create_default_dark_theme()
            
            if os.path.exists(theme_path):
                with open(theme_path, "r", encoding="utf-8") as f:
                    self.theme_config = json.load(f)
                logger.info(f"Loaded theme: {self.theme_name}/{self.theme_mode}")
            else:
                # Fallback config
                self.theme_config = {
                    "background_image": "", 
                    "menu_button_normal": "", 
                    "font_name": "Minecraftia", 
                    "font_color": [1, 1, 1, 1], 
                    "menu_selected_color": [1, 1, 1, 1], 
                    "menu_unselected_color": [0.7, 0.7, 0.7, 1], 
                    "overlay_images": {},
                    "colors": {
                        "shadow": [0.1, 0.1, 0.1, 0.5], 
                        "trend_up": [1, 0.3, 0.3, 1], 
                        "trend_down": [0.2, 0.6, 1, 1]
                    }
                }
                logger.warning(f"Using fallback theme config")
                
        except Exception as e:
            logger.error(f"Error loading theme config: {e}")
            self.theme_config = {"font_name": "Minecraftia", "font_color": [1, 1, 1, 1]}

    def create_default_dark_theme(self):
        """Создание дефолтной тёмной темы если её нет"""
        try:
            dark_theme_dir = "themes/minecraft/dark"
            os.makedirs(dark_theme_dir, exist_ok=True)
            
            theme_file = os.path.join(dark_theme_dir, "theme.json")
            
            if not os.path.exists(theme_file):
                # Load light theme as base
                light_path = "themes/minecraft/light/theme.json"
                if os.path.exists(light_path):
                    with open(light_path, "r", encoding="utf-8") as f:
                        light_config = json.load(f)
                    
                    # Modify for dark theme
                    dark_config = light_config.copy()
                    
                    # Update paths to dark theme
                    for key, value in dark_config.items():
                        if isinstance(value, str) and "light/" in value:
                            dark_config[key] = value.replace("light/", "dark/")
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if isinstance(subvalue, str) and "light/" in subvalue:
                                    dark_config[key][subkey] = subvalue.replace("light/", "dark/")
                    
                    # Update dark theme specific colors
                    dark_config.update({
                        "theme_mode": "dark",
                        "panel_bg": [0.1, 0.1, 0.1, 0.7],
                        "font_color": [0.9, 0.9, 0.9, 1],
                        "menu_selected_color": [0.9, 0.9, 0.9, 1],
                        "menu_unselected_color": [0.5, 0.5, 0.5, 1]
                    })
                    
                    with open(theme_file, "w", encoding="utf-8") as f:
                        json.dump(dark_config, f, ensure_ascii=False, indent=2)
                    
                    logger.info("Created default dark theme")
                    return True
                    
        except Exception as e:
            logger.error(f"Error creating default dark theme: {e}")
            
        return False

    @mainthread
    def switch_theme_mode(self, mode):
        """МАКСИМАЛЬНО УПРОЩЁННОЕ переключение темы"""
        if mode not in ["light", "dark"] or mode == self.theme_mode:
            return True
            
        logger.info(f"Switching theme: {self.theme_mode} → {mode}")
        
        try:
            # Update mode
            old_mode = self.theme_mode
            self.theme_mode = mode
            
            # Load new theme config
            self.load_theme_config()
            
            # Save to user config
            self.user_config["theme_mode"] = mode
            self.save_user_config()
            
            # Simple UI refresh
            self.refresh_ui()
            
            logger.info(f"Theme switched successfully to {mode}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching theme: {e}")
            self.theme_mode = old_mode  # Revert
            return False

    def refresh_ui(self):
        """ИСПРАВЛЕННОЕ обновление UI с принудительной перезагрузкой изображений"""
        try:
            # Агрессивная очистка всех кэшей
            self._clear_all_caches()
            
            # Принудительное обновление property
            Clock.schedule_once(self._force_property_update, 0.1)
            
            # Обновление UI
            Clock.schedule_once(self._update_ui, 0.2)
            
        except Exception as e:
            logger.error(f"Error refreshing UI: {e}")

    def _clear_all_caches(self):
        """Агрессивная очистка всех кэшей"""
        try:
            # Kivy image caches
            cache_categories = ['kv.image', 'kv.texture', 'kv.atlas', 'kv.loader']
            for category in cache_categories:
                try:
                    Cache.remove(category)
                except:
                    pass
            
            # Core image cache
            try:
                if hasattr(CoreImage, '_texture_cache'):
                    CoreImage._texture_cache.clear()
                if hasattr(CoreImage, '_cache'):
                    CoreImage._cache.clear()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")

    def _force_property_update(self, dt):
        """Принудительное обновление theme_config property"""
        try:
            # Триггерим обновление property через временную замену
            old_config = self.theme_config.copy()
            self.theme_config = {}
            
            # Возвращаем через короткую задержку
            Clock.schedule_once(
                lambda dt: setattr(self, 'theme_config', old_config), 
                0.05
            )
            
        except Exception as e:
            logger.error(f"Error forcing property update: {e}")

    def _update_ui(self, dt):
        """Принудительное обновление UI с перезагрузкой изображений"""
        try:
            if not self.root:
                return
                
            # Update root canvas
            self.root.canvas.ask_update()
            
            # Обновляем фоновое изображение
            self._update_background_image()
            
            # Update all screens
            screen_manager = getattr(self.root.ids, 'screen_manager', None)
            if screen_manager:
                for screen in screen_manager.screens:
                    self._update_screen_images(screen)
            
            logger.info("UI refresh completed")
            
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

    def _update_background_image(self):
        """Обновление фонового изображения"""
        try:
            if hasattr(self.root, 'ids') and hasattr(self.root.ids, 'background_image'):
                bg_widget = self.root.ids.background_image
                new_source = self.theme_config.get("background_image", "")
                
                if new_source:
                    # Принудительная перезагрузка
                    bg_widget.source = ''
                    Clock.schedule_once(
                        lambda dt: setattr(bg_widget, 'source', new_source),
                        0.1
                    )
                    
        except Exception as e:
            logger.error(f"Error updating background image: {e}")

    def _update_screen_images(self, screen):
        """Обновление всех изображений на экране"""
        try:
            screen.canvas.ask_update()
            
            # Найти и обновить все Image виджеты
            for widget in screen.walk():
                if hasattr(widget, 'source') and hasattr(widget, 'id'):
                    widget_id = getattr(widget, 'id', '')
                    
                    if widget_id:
                        # Определяем новый source на основе id виджета
                        new_source = self._get_new_source_for_widget(widget_id, screen.name)
                        
                        if new_source and new_source != widget.source:
                            # Принудительная перезагрузка
                            widget.source = ''
                            Clock.schedule_once(
                                lambda dt, w=widget, src=new_source: setattr(w, 'source', src),
                                0.1
                            )
                            
        except Exception as e:
            logger.error(f"Error updating screen {screen.name} images: {e}")

    def _get_new_source_for_widget(self, widget_id, screen_name):
        """Получить новый source для виджета на основе его ID"""
        try:
            # Фоновое изображение
            if widget_id == 'background_image':
                return self.theme_config.get('background_image', '')
            
            # Overlay изображения
            elif 'overlay' in widget_id or widget_id.endswith('_overlay'):
                return self.get_overlay_image(screen_name)
            
            # Другие изображения возвращаем как есть для принудительной перезагрузки
            return None
            
        except Exception as e:
            logger.error(f"Error getting new source for widget {widget_id}: {e}")
            return None

    def save_user_config(self):
        """Сохранение пользовательской конфигурации"""
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/user.json", "w", encoding="utf-8") as f:
                json.dump(self.user_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving user config: {e}")

    def build(self):
        logger.info("Building app...")
        
        # Ensure directories exist
        self.ensure_directories()
        
        # Initialize services
        try:
            self._init_services()
            return Builder.load_file('main.kv')
        except Exception as e:
            logger.error(f"Error building app: {e}")

    def _init_services(self):
        """Initialize all application services"""
        try:
            self.alarm_service = AlarmService()
            self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)
            self.schedule_service = ScheduleService()
            self.pigs_service = PigsService()
            self.notification_service = NotificationService()
            self.alarm_clock = AlarmClock(self)
            self.volume_service = VolumeControlService(self)
            
            # Initialize sensors in background
            self.sensor_service = SensorService()
            threading.Thread(target=self._init_sensors_async, daemon=True).start()
            
            logger.info("Services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise

    def _init_sensors_async(self):
        """Initialize sensors in background thread"""
        try:
            self.sensor_service.start()
            
            # Configure sensor
            switch_delay = self.user_config.get("theme_switch_delay", 2)
            self.sensor_service.calibrate_light_sensor(switch_delay)
            
            # Start volume control
            if self.volume_service.start():
                self.volume_service.set_volume_change_callback(self._on_volume_changed)
                
        except Exception as e:
            logger.error(f"Error starting services: {e}")

    def scale_font(self, size):
        """Scale font size"""
        if isinstance(size, str):
            match = re.match(r'(\d+)(\w+)', size)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return f"{int(value * self.font_scale)}{unit}"
        try:    
            return f"{int(float(size) * self.font_scale)}sp"
        except (ValueError, TypeError):
            return "14sp"

    def scale_size(self, size):
        """Scale widget size"""
        if isinstance(size, (list, tuple)):
            return [self.scale_size(item) for item in size]
        
        if isinstance(size, str):
            match = re.match(r'(\d+)(\w+)', size)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return f"{int(value * self.ui_scale)}{unit}"
        
        try:
            return int(float(size) * self.ui_scale)
        except (TypeError, ValueError):
            return size

    def ensure_directories(self):
        """Ensure all required directories exist"""
        dirs = [
            "assets/fonts", "assets/sounds", "assets/images",
            "themes/minecraft/light", "themes/minecraft/dark",
            "media/ringtones", "cache", "config", "pages", "logs"
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def play_sound(self, sound_name="click"):
        """Play sound via sound service"""
        self.sound_service.play_sound(sound_name)

    def get_overlay_image(self, page):
        """Get overlay image for page"""
        return self.theme_config.get("overlay_images", {}).get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        logger.info("App starting...")
        try:
            self.root.ids.screen_manager.bind(current=self._update_current_screen)
            
            # Initialize theme based on current light level
            Clock.schedule_once(self._initialize_startup_theme, 2)
            
            # Start auto theme monitoring
            Clock.schedule_once(self._start_auto_theme, 4)
                
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
    
    def _initialize_startup_theme(self, dt):
        """Set correct theme based on current light level at startup"""
        try:
            if not self.auto_theme_enabled or not self.sensor_service:
                return
                
            current_light = self.sensor_service.get_light_level()
            target_mode = "light" if current_light else "dark"
            
            if target_mode != self.theme_mode:
                logger.info(f"Setting startup theme: {self.theme_mode} → {target_mode}")
                self.switch_theme_mode(target_mode)
                
        except Exception as e:
            logger.error(f"Error initializing startup theme: {e}")
    
    def _start_auto_theme(self, dt):
        """Start auto theme monitoring"""
        if self.auto_theme_enabled and self.sensor_service:
            logger.info("Starting auto theme monitoring...")
            
            # Configure sensor
            switch_delay = self.user_config.get("theme_switch_delay", 2)
            self.sensor_service.calibrate_light_sensor(switch_delay)
            
            # Check every 5 seconds
            self._auto_theme_event = Clock.schedule_interval(self._check_auto_theme, 5)
    
    def on_stop(self):
        """Clean up when the application exits"""
        logger.info("App stopping...")
        
        # Stop auto theme monitoring
        if self._auto_theme_event:
            self._auto_theme_event.cancel()
        
        # Stop services
        services_to_stop = [
            ('sensor_service', 'stop'),
            ('volume_service', 'stop'), 
            ('sound_service', 'cleanup'),
            ('alarm_clock', 'stop'),
            ('alarm_service', 'stop')
        ]
        
        for service_name, method_name in services_to_stop:
            if hasattr(self, service_name):
                try:
                    service = getattr(self, service_name)
                    if hasattr(service, method_name):
                        getattr(service, method_name)()
                        logger.info(f"{service_name} stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")

    def _update_current_screen(self, instance, value):
        """Update current screen property"""
        self.current_screen = value
        if not self.menu_navigation:
            self.play_sound("success")
        self.menu_navigation = False
    
    def _check_auto_theme(self, dt):
        """УПРОЩЁННАЯ проверка автопереключения темы"""
        if not self.auto_theme_enabled or not self.sensor_service:
            return
            
        try:
            if self.sensor_service.is_light_changed():
                current_light = self.sensor_service.get_light_level()
                target_mode = "light" if current_light else "dark"
                
                if target_mode != self.theme_mode:
                    logger.info(f"Auto theme switch: {self.theme_mode} → {target_mode}")
                    if self.switch_theme_mode(target_mode):
                        self.notification_service.add(f"Theme switched to {target_mode}", "system")
                        self.play_sound("success")
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")
    
    def set_auto_theme_enabled(self, enabled):
        """Enable/disable auto theme switching"""
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        self.save_user_config()
        
        if enabled and not self._auto_theme_event:
            Clock.schedule_once(self._start_auto_theme, 1)
        elif not enabled and self._auto_theme_event:
            self._auto_theme_event.cancel()
            self._auto_theme_event = None
            
        logger.info(f"Auto theme switching {'enabled' if enabled else 'disabled'}")
    
    def _on_volume_changed(self, volume, action):
        """Callback for volume changes"""
        pass  # Volume updates handled by service

if __name__ == "__main__":
    logger.info("Starting Bedrock App")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")