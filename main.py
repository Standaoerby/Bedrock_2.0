from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.clock import Clock, mainthread
from kivy.core.image import Image as CoreImage
from kivy.cache import Cache
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
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

class ThemedPanel(BoxLayout):
    """ИСПРАВЛЕННАЯ панель с автообновлением фона при смене темы"""
    
    def __init__(self, **kwargs):
        super(ThemedPanel, self).__init__(**kwargs)
        self.bg_color = None
        self.bg_rect = None
        
        # Привязываемся к изменениям размера/позиции
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Инициализируем фон с задержкой (когда app будет доступен)
        Clock.schedule_once(self.update_background, 0.1)
    
    def update_background(self, *args):
        """Обновление фона панели"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            if not app or not hasattr(app, 'theme_config'):
                # Повторить попытку через некоторое время
                Clock.schedule_once(self.update_background, 0.5)
                return
            
            # Очищаем старый фон
            self.canvas.before.clear()
            
            # Рисуем новый фон
            with self.canvas.before:
                panel_bg = app.theme_config.get("panel_bg", [0, 0, 0, 0.08])
                panel_radius = app.theme_config.get("panel_radius", 16)
                
                self.bg_color = Color(*panel_bg)
                self.bg_rect = RoundedRectangle(
                    pos=self.pos, 
                    size=self.size,
                    radius=[panel_radius]
                )
                
        except Exception as e:
            logger.error(f"Error updating ThemedPanel background: {e}")
    
    def update_rect(self, *args):
        """Обновление размера/позиции фона"""
        if self.bg_rect:
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size

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
        
        # Theme switching state
        self._switching = False
        self._auto_theme_event = None
        
        # Call parent init
        super(BedrockApp, self).__init__(**kwargs)
        
        # Ensure dark theme exists and load current theme
        self.create_default_dark_theme()
        self._load_current_theme()

    def create_default_dark_theme(self):
        """Create default dark theme if it doesn't exist"""
        try:
            dark_theme_dir = "themes/minecraft/dark"
            os.makedirs(dark_theme_dir, exist_ok=True)
            
            theme_file = os.path.join(dark_theme_dir, "theme.json")
            
            if not os.path.exists(theme_file):
                dark_theme_config = {
                    "background_image": "themes/minecraft/dark/background.png",
                    "overlay_images": {
                        "home": "themes/minecraft/dark/overlay_home.png",
                        "alarm": "themes/minecraft/dark/overlay_alarm.png",
                        "schedule": "themes/minecraft/dark/overlay_schedule.png",
                        "weather": "themes/minecraft/dark/overlay_weather.png",
                        "pigs": "themes/minecraft/dark/overlay_pigs.png",
                        "settings": "themes/minecraft/dark/overlay_settings.png"
                    },
                    "menu_button_normal": "themes/minecraft/dark/menu_button.png",
                    "menu_button_active": "themes/minecraft/dark/menu_button_active.png",
                    "button_normal": "themes/minecraft/dark/button.png", 
                    "button_active": "themes/minecraft/dark/button_active.png",
                    "panel_bg": [0.1, 0.1, 0.1, 0.7],
                    "panel_radius": 16,
                    "font_name": "Minecraftia",
                    "font_color": [0.9, 0.9, 0.9, 1],
                    "font_sizes": {
                        "tiny": "12sp", "small": "14sp", "default": "18sp",
                        "medium": "20sp", "large": "26sp", "xlarge": "34sp", "huge": "240sp"
                    },
                    "colors": {
                        "primary": [0.2, 0.4, 0.8, 1],
                        "secondary": [0.6, 0.3, 0.8, 1],
                        "accent": [1, 0.6, 0, 1],
                        "active": [0.2, 0.8, 0.2, 1],
                        "inactive": [0.4, 0.4, 0.4, 1],
                        "semi_active": [0.5, 0.7, 0.5, 1],
                        "warning": [0.9, 0.7, 0.1, 1],
                        "error": [0.9, 0.2, 0.2, 1],
                        "success": [0.2, 0.8, 0.2, 1],
                        "font_highlight": [0.8, 0.8, 0.9, 1],
                        "shadow": [0.9, 0.9, 0.9, 0.3],
                        "trend_up": [1, 0.5, 0.5, 1],
                        "trend_down": [0.4, 0.7, 1, 1]
                    },
                    "menu_selected_color": [0.9, 0.9, 0.9, 1],
                    "menu_unselected_color": [0.5, 0.5, 0.5, 1],
                    "menu_button_size": [180, 60],
                    "grid_unit": "32dp", "grid_unit_half": "16dp", "grid_unit_quarter": "8dp",
                    "grid_unit_1.5x": "48dp", "grid_unit_2x": "64dp",
                    "padding": "15dp", "widget_font_size": "20sp"
                }
                
                with open(theme_file, "w", encoding="utf-8") as f:
                    json.dump(dark_theme_config, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Created default dark theme")
                return True
        except Exception as e:
            logger.error(f"Error creating default dark theme: {e}")
            return False
        
        return False

    def load_theme_config(self, theme="minecraft", mode="light"):
        """Load theme configuration from file"""
        path = f"themes/{theme}/{mode}/theme.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Error loading theme config from {path}: {e}")
            
            # If dark theme fails, create it
            if mode == "dark":
                if self.create_default_dark_theme():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                        return config
                    except Exception:
                        pass
            
            # Return fallback config
            return {
                "background_image": "", "menu_button_normal": "", "font_name": "Minecraftia", 
                "font_color": [1, 1, 1, 1], "menu_selected_color": [1, 1, 1, 1], 
                "menu_unselected_color": [0.7, 0.7, 0.7, 1], "overlay_images": {},
                "colors": {"shadow": [0.1, 0.1, 0.1, 0.5], "trend_up": [1, 0.3, 0.3, 1], "trend_down": [0.2, 0.6, 1, 1]}
            }

    def _load_current_theme(self):
        """Load current theme configuration"""
        try:
            self.theme_config = self.load_theme_config(self.theme_name, self.theme_mode)
            logger.info(f"Loaded theme: {self.theme_name}/{self.theme_mode}")
        except Exception as e:
            logger.error(f"Error loading theme: {e}")
            self.theme_config = {"font_name": "Minecraftia", "font_color": [1, 1, 1, 1]}

    @mainthread
    def switch_theme_mode(self, mode):
        """ИСПРАВЛЕННОЕ переключение режима темы - интегрировано в BedrockApp"""
        try:
            # Проверка блокировки
            if self._switching:
                logger.warning("Theme switch already in progress")
                return False
                
            if mode not in ["light", "dark"] or mode == self.theme_mode:
                return True
            
            # Блокировка переключения
            self._switching = True
            
            # Проверяем доступность тёмной темы
            if mode == "dark":
                dark_theme_path = f"themes/{self.theme_name}/dark/theme.json"
                if not os.path.exists(dark_theme_path):
                    if not self.create_default_dark_theme():
                        self._switching = False
                        return False
            
            logger.info(f"Switching theme: {self.theme_mode} → {mode}")
            
            # Загружаем новую конфигурацию темы
            new_theme_config = self.load_theme_config(self.theme_name, mode)
            if not new_theme_config:
                self._switching = False
                return False
            
            # ИСПРАВЛЕНО: Атомарное обновление theme_config
            old_mode = self.theme_mode
            self.theme_mode = mode
            
            # Заменяем конфигурацию целиком, а не по частям
            self.theme_config = new_theme_config.copy()
            
            # Сохраняем пользовательскую конфигурацию
            self.user_config["theme_mode"] = mode
            self._save_user_config()
            
            # ИСПРАВЛЕНО: Комплексное обновление UI
            self._clear_cache_and_refresh()
            
            logger.info(f"Theme successfully switched to {mode}")
            
            # Разблокировка через 1 секунду
            Clock.schedule_once(lambda dt: setattr(self, '_switching', False), 1.0)
            return True
            
        except Exception as e:
            logger.error(f"Error switching theme: {e}")
            self._switching = False
            return False

    def _clear_cache_and_refresh(self):
        """ИСПРАВЛЕННАЯ очистка кэша и обновление"""
        try:
            # Очистка кэша изображений
            cache_categories = ['kv.image', 'kv.texture', 'kv.atlas']
            for category in cache_categories:
                try:
                    Cache.remove(category)
                except:
                    pass
            
            # ИСПРАВЛЕНО: Комплексное обновление UI
            Clock.schedule_once(self._comprehensive_refresh, 0.1)
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def _comprehensive_refresh(self, dt):
        """ИСПРАВЛЕННОЕ комплексное обновление UI"""
        try:
            if not hasattr(self, 'root') or not self.root:
                return
            
            # 1. Обновить фоновое изображение
            self._update_background_image()
            
            # 2. Обновить все экраны и их overlay
            self._update_all_screens()
            
            # 3. Принудительно обновить все панели
            self._update_all_panels()
            
            # 4. Принудительно обновить все canvas
            self._force_canvas_update()
            
            logger.info("Comprehensive theme refresh completed")
            
        except Exception as e:
            logger.error(f"Error in comprehensive refresh: {e}")

    def _update_background_image(self):
        """Обновление фонового изображения"""
        try:
            if hasattr(self.root, 'ids'):
                bg_widget = getattr(self.root.ids, 'background_image', None)
                if bg_widget and hasattr(bg_widget, 'source'):
                    new_source = self.theme_config.get("background_image", "")
                    if new_source != bg_widget.source:
                        bg_widget.source = new_source
                        logger.debug(f"Background updated: {new_source}")
        except Exception as e:
            logger.error(f"Error updating background: {e}")

    def _update_all_screens(self):
        """Обновление всех экранов"""
        try:
            screen_manager = getattr(self.root.ids, 'screen_manager', None)
            if not screen_manager:
                return
                
            for screen in screen_manager.screens:
                self._update_screen_overlays(screen)
                
        except Exception as e:
            logger.error(f"Error updating screens: {e}")

    def _update_screen_overlays(self, screen):
        """Обновление overlay изображений для экрана"""
        try:
            screen_name = getattr(screen, 'name', '')
            if not screen_name:
                return
                
            # Получить новый источник overlay
            new_overlay_source = self.get_overlay_image(screen_name)
            
            # Найти и обновить overlay виджеты
            for widget in screen.walk():
                if self._is_overlay_widget(widget, screen_name):
                    if hasattr(widget, 'source') and widget.source != new_overlay_source:
                        widget.source = new_overlay_source
                        logger.debug(f"Overlay updated for {screen_name}: {new_overlay_source}")
                        
        except Exception as e:
            logger.error(f"Error updating overlays for {getattr(screen, 'name', 'unknown')}: {e}")

    def _is_overlay_widget(self, widget, screen_name):
        """Проверить, является ли виджет overlay изображением"""
        if not (hasattr(widget, 'source') and hasattr(widget, 'id')):
            return False
            
        widget_id = getattr(widget, 'id', '')
        if not widget_id:
            return False
            
        # Проверяем разные паттерны ID для overlay
        overlay_patterns = [
            f"{screen_name}_overlay",
            "overlay" in str(widget_id).lower()
        ]
        
        return any(pattern and (pattern == str(widget_id) or pattern in str(widget_id)) for pattern in overlay_patterns if pattern)

    def _update_all_panels(self):
        """Обновление всех ThemedPanel виджетов"""
        try:
            if not hasattr(self, 'root') or not self.root:
                return
                
            # Найти все ThemedPanel виджеты и обновить их фон
            screen_manager = getattr(self.root.ids, 'screen_manager', None)
            if screen_manager:
                for screen in screen_manager.screens:
                    for widget in screen.walk():
                        if isinstance(widget, ThemedPanel):
                            widget.update_background()
                            
        except Exception as e:
            logger.error(f"Error updating panels: {e}")

    def _force_canvas_update(self):
        """Принудительное обновление всех canvas"""
        try:
            if not hasattr(self, 'root') or not self.root:
                return
                
            # Обновить корневой canvas
            self.root.canvas.ask_update()
            
            # Обновить canvas всех виджетов
            screen_manager = getattr(self.root.ids, 'screen_manager', None)
            if screen_manager:
                for screen in screen_manager.screens:
                    screen.canvas.ask_update()
                    for widget in screen.walk():
                        if hasattr(widget, 'canvas'):
                            widget.canvas.ask_update()
                            
        except Exception as e:
            logger.error(f"Error forcing canvas update: {e}")

    def _save_user_config(self):
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
            
            # Initialize correct theme based on current light level
            Clock.schedule_once(self._initialize_theme_on_startup, 2)
            
            # Start auto theme monitoring
            Clock.schedule_once(self._start_auto_theme, 4)
                
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
    
    def _initialize_theme_on_startup(self, dt):
        """Set correct theme based on current light level at startup"""
        try:
            if not self.auto_theme_enabled or not self.sensor_service:
                return
                
            # Get current light level
            current_light = self.sensor_service.get_light_level()
            target_mode = "light" if current_light else "dark"
            
            logger.info(f"Startup light level: {'Light' if current_light else 'Dark'}")
            
            # Switch theme if needed
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
        """УПРОЩЕННАЯ проверка автопереключения темы"""
        if not self.auto_theme_enabled or not self.sensor_service:
            return
            
        try:
            # Check for light level changes
            if self.sensor_service.is_light_changed():
                current_light = self.sensor_service.get_light_level()
                target_mode = "light" if current_light else "dark"
                
                if target_mode != self.theme_mode:
                    logger.info(f"Auto theme switch triggered: {self.theme_mode} → {target_mode}")
                    # ИСПРАВЛЕНО: Прямое переключение без задержек
                    if self.switch_theme_mode(target_mode):
                        self.notification_service.add(f"Theme switched to {target_mode}", "system")
                        self.play_sound("success")
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")
    
    def set_auto_theme_enabled(self, enabled):
        """Enable/disable auto theme switching"""
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        self._save_user_config()
        
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