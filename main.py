from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.clock import Clock
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

# Configure environment variables - these work with the launch script
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Raspberry Pi specific settings
if sys.platform.startswith('linux'):
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['KIVY_LOG_LEVEL'] = 'debug'

def create_default_dark_theme():
    """Create default dark theme if it doesn't exist"""
    try:
        dark_theme_dir = "themes/minecraft/dark"
        os.makedirs(dark_theme_dir, exist_ok=True)
        
        theme_file = os.path.join(dark_theme_dir, "theme.json")
        
        if not os.path.exists(theme_file):
            # Create default dark theme config based on light theme
            light_theme_file = "themes/minecraft/light/theme.json"
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
                    "small": "14sp",
                    "default": "18sp",
                    "medium": "20sp",
                    "large": "26sp",
                    "xlarge": "34sp",
                    "huge": "240sp"
                },
                "colors": {
                    "accent": [0.3, 0.5, 0.8, 1],
                    "active": [0.2, 0.8, 0.2, 1],
                    "inactive": [0.4, 0.4, 0.4, 1],
                    "semi_active": [0.6, 0.8, 0.6, 1],
                    "font_highlight": [0.8, 0.8, 0.6, 1]
                },
                "menu_selected_color": [0.9, 0.9, 0.9, 1],
                "menu_unselected_color": [0.5, 0.5, 0.5, 1],
                "grid_unit": "32dp",
                "grid_unit_half": "16dp",
                "grid_unit_quarter": "8dp",
                "grid_unit_1.5x": "48dp",
                "grid_unit_2x": "64dp",
                "padding": "15dp",
                "widget_font_size": "20sp"
            }
            
            with open(theme_file, "w", encoding="utf-8") as f:
                json.dump(dark_theme_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created default dark theme at {theme_file}")
            return True
    except Exception as e:
        logger.error(f"Error creating default dark theme: {e}")
        return False
    
    return False

def load_theme_config(theme="minecraft", mode="light"):
    path = f"themes/{theme}/{mode}/theme.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"Loaded theme config from {path}")
        return config
    except Exception as e:
        logger.error(f"Error loading theme config from {path}: {e}")
        
        # If dark theme fails and we're trying to load dark, create it
        if mode == "dark":
            logger.info("Attempting to create default dark theme...")
            if create_default_dark_theme():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    logger.info(f"Successfully loaded created dark theme from {path}")
                    return config
                except Exception as e2:
                    logger.error(f"Failed to load created dark theme: {e2}")
        
        # Return fallback config
        return {"background_image": "", "menu_button_normal": "", "font_name": "Minecraftia", 
                "font_color": [1, 1, 1, 1], "menu_selected_color": [1, 1, 1, 1], 
                "menu_unselected_color": [0.7, 0.7, 0.7, 1], "overlay_images": {}}

def load_user_config():
    """Load user configuration from file"""
    try:
        with open("config/user.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading user config: {e}")
        # Return default config
        return {
            "theme": "minecraft",
            "theme_mode": "light",
            "auto_theme_enabled": True,
            "light_sensor_threshold": 50,
            "theme_switch_delay": 5,
            "username": "User",
            "birthdate": "2000-01-01"
        }

def save_user_config(config):
    """Save user configuration to file"""
    try:
        os.makedirs("config", exist_ok=True)
        with open("config/user.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving user config: {e}")
        return False

# Add a safe KV file loader that works with potentially missing theme properties
def safe_kv_load():
    """Load KV file with patched app references for error-proof loading"""
    try:
        # Read the KV file
        with open('main.kv', 'r') as f:
            kv_content = f.read()
        
        # Replace direct dictionary access with .get() method with defaults
        # This pattern matches app.theme_config["something"] and replaces with app.theme_config.get("something", "")
        kv_content = re.sub(
            r'app\.theme_config\["([^"]+)"\]', 
            r'app.theme_config.get("\1", "")', 
            kv_content
        )
        
        # Now load the patched KV content
        return Builder.load_string(kv_content)
    except Exception as e:
        logger.error(f"Error in safe_kv_load: {e}")
        # Try direct loading as fallback
        return Builder.load_file('main.kv')

# Try to register font
try:
    LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
    logger.info("Font registered successfully")
except Exception as e:
    logger.error(f"Error registering font: {e}")
    with open('bedrock_startup_log.txt', 'a') as log_file:
        log_file.write(f"Font registration error: {e}\n")

# Import screens after font registration
try:
    from pages.home import HomeScreen
    from pages.alarm import AlarmScreen
    from pages.weather import WeatherScreen
    from pages.schedule import ScheduleScreen
    from pages.pigs import PigsScreen
    from pages.settings import SettingsScreen
    logger.info("Screen imports successful")
except Exception as e:
    logger.error(f"Error importing screens: {e}")
    with open('bedrock_startup_log.txt', 'a') as log_file:
        log_file.write(f"Screen import error: {e}\n")

class BedrockApp(MDApp):
    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)
    
    # Fixed scaling parameters
    ui_scale = NumericProperty(1.0)
    font_scale = NumericProperty(1.0)
    padding_scale = NumericProperty(1.0)
    
    # Common UI metrics
    ui_metrics = DictProperty({
        'menu_height': 70,
        'menu_padding': 10,
        'content_padding': 15,
        'widget_spacing': 10,
        'widget_height': 48,
        'small_widget_height': 36,
    })
    
    # Theme configuration as Kivy property - ИСПРАВЛЕНО
    theme_config = DictProperty({})
    
    # Auto theme properties - ИСПРАВЛЕНО
    auto_theme_enabled = BooleanProperty(True)
    current_volume = NumericProperty(50)

    def __init__(self, **kwargs):
        # Load user configuration
        self.user_config = load_user_config()
        
        # Initialize theme properties BEFORE parent init 
        self.theme_name = self.user_config.get("theme", "minecraft")
        self.theme_mode = self.user_config.get("theme_mode", "light")
        self.auto_theme_enabled = self.user_config.get("auto_theme_enabled", True)
        
        # Ensure dark theme exists
        create_default_dark_theme()
        
        # Initialize sound service
        self.sound_service = SoundService()
        
        # Theme switching state - УЛУЧШЕНО с подробным логированием
        self._theme_switch_pending = False
        self._theme_switch_timer = None
        self._last_theme_switch = 0  # Prevent rapid switching
        self._theme_monitoring_active = False
        self._auto_theme_event = None
        
        # Call parent init BEFORE setting theme_config
        super(BedrockApp, self).__init__(**kwargs)
        
        # Load theme config AFTER parent init as DictProperty
        try:
            loaded_theme_config = load_theme_config(self.theme_name, self.theme_mode)
            self.theme_config = loaded_theme_config
            logger.info(f"Theme initialized: {self.theme_name}/{self.theme_mode}")
        except Exception as e:
            logger.error(f"Error initializing theme in __init__: {e}")
            # Set default fallback theme
            self.theme_config = {
                "background_image": "",
                "menu_button_normal": "",
                "font_name": "Minecraftia",
                "font_color": [1, 1, 1, 1],
                "menu_selected_color": [1, 1, 1, 1],
                "menu_unselected_color": [0.7, 0.7, 0.7, 1],
                "overlay_images": {}
            }

    def build(self):
        logger.info("Building app...")
        
        # Ensure directories exist
        self.ensure_directories()
        
        # Initialize services
        try:
            self.alarm_service = AlarmService()
            self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)  # Camden, London coordinates
            self.schedule_service = ScheduleService()
            self.pigs_service = PigsService()
            self.notification_service = NotificationService()
            
            # Initialize AlarmClock
            self.alarm_clock = AlarmClock(self)
            
            # Initialize Volume Control Service
            self.volume_service = VolumeControlService(self)
            
            # Initialize sensors in separate thread
            self.sensor_service = SensorService()
            self._init_sensor_thread = threading.Thread(target=self._init_sensors_async, daemon=True)
            self._init_sensor_thread.start()
            
            logger.info("Services initialized")
            return safe_kv_load()
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"Service initialization error: {e}\n")
                import traceback
                log_file.write(traceback.format_exc())

    def _init_sensors_async(self):
        """Initialize sensors in a background thread to avoid blocking UI"""
        try:
            logger.info("Starting sensor service in background thread...")
            self.sensor_service.start()
            
            # Configure sensor with user settings
            switch_delay = self.user_config.get("theme_switch_delay", 5)
            self.sensor_service.calibrate_light_sensor(switch_delay)
            
            logger.info("Sensor service started successfully")
            
            # Start volume control service
            logger.info("Starting volume control service...")
            if self.volume_service.start():
                # Set up volume change callback
                self.volume_service.set_volume_change_callback(self._on_volume_changed)
                self.current_volume = self.volume_service.get_volume()
                logger.info("Volume control service started successfully")
            else:
                logger.warning("Volume control service failed to start")
                
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
            logger.warning(f"Could not scale font size: {size}, returning default")
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
            logger.warning(f"Could not scale size: {size}, returning as is")
            return size

    def ensure_directories(self):
        """Ensure all required directories exist"""
        dirs = [
            "assets/fonts",
            "assets/sounds",
            "assets/images",
            "themes/minecraft/light",
            "themes/minecraft/dark",  # ВАЖНО: убеждаемся что папка темной темы существует
            "media/ringtones",
            "cache",
            "config",
            "pages",
            "logs"
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
        logger.info("Directories checked and created if needed")
    
    def play_sound(self, sound_name="click"):
        """Redirect to sound_service"""
        self.sound_service.play_sound(sound_name)

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        logger.info("App starting...")
        try:
            self.root.ids.screen_manager.bind(current=self._update_current_screen)
            
            # Start auto theme checking with delay to let sensors initialize
            Clock.schedule_once(self._delayed_auto_theme_start, 3)
                
            logger.info("Screen manager bound successfully")
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"on_start error: {e}\n")
                import traceback
                log_file.write(traceback.format_exc())
    
    def _delayed_auto_theme_start(self, dt):
        """Start auto theme monitoring after sensors have had time to initialize"""
        if self.auto_theme_enabled:
            logger.info("Starting delayed auto theme monitoring...")
            self._start_auto_theme_monitoring()
        
    def on_stop(self):
        """Clean up when the application exits"""
        logger.info("App stopping...")
        
        # Stop auto theme monitoring
        self._stop_auto_theme_monitoring()
        
        # Stop services
        if hasattr(self, 'sensor_service'):
            try:
                self.sensor_service.stop()
                logger.info("Sensor service stopped")
            except Exception as e:
                logger.error(f"Error stopping sensor service: {e}")
                
        if hasattr(self, 'volume_service'):
            try:
                self.volume_service.stop()
                logger.info("Volume service stopped")
            except Exception as e:
                logger.error(f"Error stopping volume service: {e}")
                
        # Cleanup sound service
        if hasattr(self, 'sound_service'):
            try:
                self.sound_service.cleanup()
                logger.info("Sound service cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up sound service: {e}")

    def _update_current_screen(self, instance, value):
        self.current_screen = value
        logger.info(f"Screen changed to {value}")
        
        if not self.menu_navigation:
            self.play_sound("success")
            
        self.menu_navigation = False
    
    # ИСПРАВЛЕННЫЕ методы автоматического переключения тем с подробным логированием
    def _start_auto_theme_monitoring(self):
        """Start monitoring light sensor for auto theme switching - ИСПРАВЛЕНО"""
        if not self.auto_theme_enabled:
            logger.info("Auto theme monitoring disabled in user config")
            return
            
        # Проверяем наличие темной темы
        if not self._check_dark_theme_available():
            logger.warning("Dark theme not available - auto theme switching disabled")
            # Попытаемся создать тему
            if create_default_dark_theme():
                logger.info("Created default dark theme, retrying...")
            else:
                logger.error("Failed to create dark theme")
                return
        
        # Проверяем доступность сенсора
        if not hasattr(self, 'sensor_service') or not self.sensor_service:
            logger.warning("Sensor service not available for auto theme monitoring")
            return
            
        if not self.sensor_service.sensor_available:
            logger.warning("Sensor service not available - using mock sensor for auto theme testing")
            # Продолжаем работу с mock сенсором для тестирования
        
        if self._theme_monitoring_active:
            logger.info("Auto theme monitoring already active")
            return
            
        logger.info("=== STARTING AUTO THEME MONITORING ===")
        logger.info(f"Current theme: {self.theme_name}/{self.theme_mode}")
        logger.info(f"Auto theme enabled: {self.auto_theme_enabled}")
        logger.info(f"Sensor available: {getattr(self.sensor_service, 'sensor_available', False)}")
        logger.info(f"GPIO available: {getattr(self.sensor_service, 'gpio_available', False)}")
        logger.info(f"Using mock sensors: {getattr(self.sensor_service, 'using_mock_sensors', True)}")
        
        # Получаем текущее состояние датчика для инициализации
        if hasattr(self.sensor_service, 'get_light_level'):
            initial_light = self.sensor_service.get_light_level()
            logger.info(f"Initial light level: {'Light' if initial_light else 'Dark'}")
            
            # Инициализируем состояние в сенсоре если не инициализировано
            if not hasattr(self.sensor_service, '_last_light_state') or self.sensor_service._last_light_state is None:
                self.sensor_service._last_light_state = initial_light
                logger.info(f"Initialized sensor last light state: {'Light' if initial_light else 'Dark'}")
        
        # Запускаем мониторинг каждые 3 секунды (чаще для лучшей отзывчивости)
        self._auto_theme_event = Clock.schedule_interval(self._check_auto_theme_switch, 3)
        self._theme_monitoring_active = True
        
        # Выполняем первоначальную проверку через 2 секунды
        Clock.schedule_once(lambda dt: self._check_auto_theme_switch(dt), 2)
        
        logger.info("Auto theme monitoring started successfully")
    
    def _stop_auto_theme_monitoring(self):
        """Stop auto theme monitoring"""
        if hasattr(self, '_auto_theme_event') and self._auto_theme_event:
            self._auto_theme_event.cancel()
            self._auto_theme_event = None
        if self._theme_switch_timer:
            self._theme_switch_timer.cancel()
            self._theme_switch_timer = None
        self._theme_monitoring_active = False
        logger.info("Auto theme monitoring stopped")
    
    def _check_dark_theme_available(self):
        """Check if dark theme is available for current theme"""
        dark_theme_path = f"themes/{self.theme_name}/dark/theme.json"
        available = os.path.exists(dark_theme_path)
        logger.debug(f"Dark theme check: {dark_theme_path} {'exists' if available else 'missing'}")
        return available
    
    def _check_auto_theme_switch(self, dt):
        """Check if theme should be switched based on light sensor - ИСПРАВЛЕНО с подробным логированием"""
        if not self.auto_theme_enabled:
            return
            
        try:
            if not hasattr(self, 'sensor_service') or not self.sensor_service:
                logger.debug("Sensor service not available for auto theme switching")
                return
            
            # Prevent rapid switching
            current_time = time.time()
            if current_time - self._last_theme_switch < 15:  # Minimum 15 seconds between switches
                return
                
            # Получаем текущий уровень освещённости
            current_light = self.sensor_service.get_light_level()
            
            # Подробное логирование каждые 10 проверок
            if not hasattr(self, '_debug_check_counter'):
                self._debug_check_counter = 0
            self._debug_check_counter += 1
            
            if self._debug_check_counter % 10 == 0:
                logger.info(f"=== AUTO THEME CHECK #{self._debug_check_counter} ===")
                logger.info(f"Current light level: {'Light' if current_light else 'Dark'}")
                logger.info(f"Current theme mode: {self.theme_mode}")
                logger.info(f"Last light state: {getattr(self.sensor_service, '_last_light_state', 'None')}")
                logger.info(f"Switch pending: {self._theme_switch_pending}")
                
                # Получаем статус сенсора
                if hasattr(self.sensor_service, 'get_light_sensor_status'):
                    sensor_status = self.sensor_service.get_light_sensor_status()
                    logger.info(f"Sensor status: {sensor_status}")
            
            # Проверяем изменение уровня освещённости
            light_changed = False
            if hasattr(self.sensor_service, 'is_light_changed'):
                light_changed = self.sensor_service.is_light_changed()
            
            if light_changed:
                target_mode = "light" if current_light else "dark"
                current_mode = self.theme_mode
                
                logger.info(f"🌟 LIGHT LEVEL CHANGED DETECTED! 🌟")
                logger.info(f"Current light: {'Light' if current_light else 'Dark'}")
                logger.info(f"Target mode: {target_mode}")
                logger.info(f"Current mode: {current_mode}")
                
                # Проверяем нужно ли переключать тему
                if target_mode != current_mode:
                    logger.info(f"🔄 SCHEDULING THEME SWITCH: {current_mode} → {target_mode}")
                    self._schedule_theme_switch(target_mode)
                else:
                    logger.info(f"Theme mode already matches light level: {target_mode}")
            else:
                # Логируем только каждые 20 проверок когда нет изменений
                if self._debug_check_counter % 20 == 0:
                    logger.debug(f"No light level change detected (check #{self._debug_check_counter})")
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _schedule_theme_switch(self, target_mode):
        """Schedule theme switch with delay to avoid rapid switching - ИСПРАВЛЕНО"""
        if self._theme_switch_pending:
            logger.info("Theme switch already pending, cancelling previous and scheduling new")
            if self._theme_switch_timer:
                self._theme_switch_timer.cancel()
            self._theme_switch_pending = False
            
        if not self._check_dark_theme_available():
            logger.error(f"Cannot switch to {target_mode} mode - dark theme not available")
            # Попытаемся создать тему
            if target_mode == "dark" and create_default_dark_theme():
                logger.info("Created dark theme, continuing with switch")
            else:
                return
            
        delay = self.user_config.get("theme_switch_delay", 5)
        self._theme_switch_pending = True
        
        logger.info(f"📅 SCHEDULING THEME SWITCH to {target_mode} in {delay} seconds")
        self._theme_switch_timer = Clock.schedule_once(
            lambda dt: self._execute_theme_switch(target_mode), 
            delay
        )
    
    def _execute_theme_switch(self, target_mode):
        """Execute the theme switch - ИСПРАВЛЕНО с подробным логированием"""
        try:
            logger.info(f"🚀 EXECUTING THEME SWITCH to {target_mode}")
            
            if target_mode != self.theme_mode:
                logger.info(f"Switching theme: {self.theme_mode} → {target_mode}")
                
                # Switch theme
                if self.switch_theme_mode(target_mode):
                    self._last_theme_switch = time.time()
                    
                    # Show notification
                    if hasattr(self, 'notification_service'):
                        self.notification_service.add(
                            f"Theme switched to {target_mode} mode",
                            "system"
                        )
                        
                    # Play sound feedback
                    self.play_sound("success")
                    
                    logger.info(f"✅ Theme successfully switched to {target_mode}")
                else:
                    logger.error(f"❌ Failed to switch theme to {target_mode}")
            else:
                logger.info(f"Theme already in {target_mode} mode, no switch needed")
                    
        except Exception as e:
            logger.error(f"Error executing theme switch: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self._theme_switch_pending = False
            self._theme_switch_timer = None
    
    def switch_theme_mode(self, mode):
        """Switch theme mode (light/dark) - РАДИКАЛЬНОЕ ОБНОВЛЕНИЕ UI"""
        try:
            logger.info(f"🎨 === SWITCHING THEME MODE: {self.theme_mode} → {mode} ===")
            
            if mode not in ["light", "dark"]:
                logger.error(f"Invalid theme mode: {mode}")
                return False
            
            # Check if dark theme exists
            if mode == "dark" and not self._check_dark_theme_available():
                logger.error(f"Dark theme not available for {self.theme_name}")
                # Try to create it
                if create_default_dark_theme():
                    logger.info("Created default dark theme")
                else:
                    return False
                
            # Load new theme config
            new_theme_config = load_theme_config(self.theme_name, mode)
            if not new_theme_config:
                logger.error(f"Failed to load theme config for {self.theme_name}/{mode}")
                return False
            
            # Update properties
            old_mode = self.theme_mode
            old_theme_config = self.theme_config.copy()
            
            self.theme_mode = mode
            self.theme_config = new_theme_config
            
            logger.info(f"✅ Updated theme properties:")
            logger.info(f"   Mode: {old_mode} → {self.theme_mode}")
            logger.info(f"   Font color: {old_theme_config.get('font_color', 'N/A')} → {self.theme_config.get('font_color', 'N/A')}")
            logger.info(f"   Panel bg: {old_theme_config.get('panel_bg', 'N/A')} → {self.theme_config.get('panel_bg', 'N/A')}")
            
            # Update user config
            self.user_config["theme_mode"] = mode
            if save_user_config(self.user_config):
                logger.info("✅ User config saved successfully")
            else:
                logger.error("❌ Failed to save user config")
            
            # КРИТИЧЕСКИ ВАЖНО: Принудительное обновление UI
            logger.info("🔄 Starting RADICAL UI update...")
            self._apply_theme_to_ui()
            
            # Additional force refresh after delay
            Clock.schedule_once(lambda dt: self._secondary_ui_refresh(), 0.5)
            
            logger.info(f"✅ Theme mode switched: {old_mode} → {mode}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error switching theme mode: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _secondary_ui_refresh(self):
        """Secondary UI refresh to ensure theme is applied"""
        try:
            logger.info("🔄 Secondary UI refresh...")
            
            # Force property update again
            self.property('theme_config').dispatch(self)
            
            # Force all screens to update
            if hasattr(self.root, 'ids') and 'screen_manager' in self.root.ids:
                screen_manager = self.root.ids.screen_manager
                current_screen = screen_manager.current
                
                # Get current screen object and force recreation of themed widgets
                try:
                    screen_obj = screen_manager.get_screen(current_screen)
                    
                    # Force update themed properties
                    self._recursive_theme_update(screen_obj)
                    
                    logger.info(f"✅ Secondary refresh completed for {current_screen}")
                    
                except Exception as e:
                    logger.error(f"Error in secondary refresh: {e}")
            
        except Exception as e:
            logger.error(f"Error in secondary UI refresh: {e}")
    
    def _recursive_theme_update(self, widget):
        """Recursively update theme-related properties on all widgets"""
        try:
            # Update common themed properties
            if hasattr(widget, 'color'):
                # Try to update color based on theme
                widget_class = widget.__class__.__name__
                if 'Label' in widget_class:
                    widget.color = self.theme_config.get("font_color", [1, 1, 1, 1])
            
            # Force canvas update
            if hasattr(widget, 'canvas'):
                widget.canvas.ask_update()
            
            # Update children recursively
            if hasattr(widget, 'children'):
                for child in widget.children:
                    self._recursive_theme_update(child)
                    
        except Exception as e:
            logger.debug(f"Error updating widget theme: {e}")
    
    def _apply_theme_to_ui(self):
        """Apply current theme to all UI elements - ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ"""
        try:
            logger.info("🎨 Applying theme to UI with force refresh...")
            
            # 1. Trigger property change event
            try:
                self.property('theme_config').dispatch(self)
                logger.info("✅ Property dispatch completed")
            except Exception as e:
                logger.error(f"Property dispatch failed: {e}")
            
            # 2. Force update all screens by cycling through them
            if hasattr(self.root, 'ids') and 'screen_manager' in self.root.ids:
                screen_manager = self.root.ids.screen_manager
                current_screen = screen_manager.current
                
                logger.info(f"Current screen: {current_screen}")
                
                # Get all screen names
                screen_names = [screen.name for screen in screen_manager.screens]
                logger.info(f"Available screens: {screen_names}")
                
                # Method 1: Rapid screen cycling to force refresh
                Clock.schedule_once(lambda dt: self._force_ui_refresh_cycle(screen_names, current_screen), 0.1)
            
            # 3. Force canvas updates
            Clock.schedule_once(lambda dt: self._force_canvas_updates(), 0.2)
            
            logger.info("🎨 Theme UI refresh scheduled")
            
        except Exception as e:
            logger.error(f"Error applying theme to UI: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _force_ui_refresh_cycle(self, screen_names, target_screen):
        """Force UI refresh by cycling through screens"""
        try:
            screen_manager = self.root.ids.screen_manager
            
            logger.info(f"🔄 Starting UI refresh cycle, target: {target_screen}")
            
            # Find a different screen to cycle to
            temp_screen = None
            for screen_name in screen_names:
                if screen_name != target_screen:
                    temp_screen = screen_name
                    break
            
            if temp_screen:
                logger.info(f"Cycling: {target_screen} → {temp_screen} → {target_screen}")
                
                # Quick cycle: current -> temp -> current
                screen_manager.current = temp_screen
                Clock.schedule_once(
                    lambda dt: setattr(screen_manager, 'current', target_screen), 
                    0.1
                )
                Clock.schedule_once(
                    lambda dt: self._force_screen_widget_updates(target_screen), 
                    0.2
                )
            else:
                logger.warning("No alternative screen found for cycling")
                # Fallback: just update current screen
                Clock.schedule_once(
                    lambda dt: self._force_screen_widget_updates(target_screen), 
                    0.1
                )
                
        except Exception as e:
            logger.error(f"Error in UI refresh cycle: {e}")
    
    def _force_screen_widget_updates(self, screen_name):
        """Force update all widgets on a specific screen"""
        try:
            screen_manager = self.root.ids.screen_manager
            screen = screen_manager.get_screen(screen_name)
            
            logger.info(f"🔧 Force updating widgets on screen: {screen_name}")
            
            # Method 1: Trigger size events to force redraws
            def trigger_widget_updates(widget):
                try:
                    # Force size change event
                    if hasattr(widget, 'size'):
                        original_size = widget.size[:]
                        widget.size = (original_size[0] + 1, original_size[1] + 1)
                        Clock.schedule_once(
                            lambda dt: setattr(widget, 'size', original_size), 
                            0.05
                        )
                    
                    # Force pos change event  
                    if hasattr(widget, 'pos'):
                        original_pos = widget.pos[:]
                        widget.pos = (original_pos[0] + 1, original_pos[1] + 1)
                        Clock.schedule_once(
                            lambda dt: setattr(widget, 'pos', original_pos), 
                            0.05
                        )
                    
                    # Recursively update children
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            trigger_widget_updates(child)
                            
                except Exception as e:
                    logger.debug(f"Error updating widget {widget}: {e}")
            
            # Start recursive update
            trigger_widget_updates(screen)
            
            logger.info(f"✅ Widget updates triggered for screen: {screen_name}")
            
        except Exception as e:
            logger.error(f"Error forcing widget updates: {e}")
    
    def _force_canvas_updates(self):
        """Force canvas redraws"""
        try:
            logger.info("🎯 Forcing canvas updates...")
            
            def force_canvas_redraw(widget):
                try:
                    if hasattr(widget, 'canvas'):
                        widget.canvas.ask_update()
                    
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            force_canvas_redraw(child)
                except:
                    pass
            
            if self.root:
                force_canvas_redraw(self.root)
                
            logger.info("✅ Canvas updates completed")
            
        except Exception as e:
            logger.error(f"Error forcing canvas updates: {e}")
    
    def set_auto_theme_enabled(self, enabled):
        """Enable/disable auto theme switching - ИСПРАВЛЕНО"""
        old_state = self.auto_theme_enabled
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        save_user_config(self.user_config)
        
        logger.info(f"=== AUTO THEME SETTING CHANGED ===")
        logger.info(f"Old state: {old_state}")
        logger.info(f"New state: {enabled}")
        
        if enabled and not old_state:
            # Starting auto theme
            logger.info("🟢 Starting auto theme monitoring...")
            self._start_auto_theme_monitoring()
        elif not enabled and old_state:
            # Stopping auto theme
            logger.info("🔴 Stopping auto theme monitoring...")
            self._stop_auto_theme_monitoring()
        else:
            logger.info(f"Auto theme state unchanged: {enabled}")
            
        logger.info(f"Auto theme switching {'enabled' if enabled else 'disabled'}")
    
    # Volume control methods
    def _on_volume_changed(self, volume, action):
        """Callback for volume changes"""
        self.current_volume = volume
        logger.debug(f"Volume changed to {volume}% via {action}")
    
    def get_volume(self):
        """Get current volume level"""
        if hasattr(self, 'volume_service'):
            return self.volume_service.get_volume()
        return 50
    
    def set_volume(self, volume):
        """Set volume level"""
        if hasattr(self, 'volume_service'):
            return self.volume_service.set_volume(volume)
        return False
    
    # Sensor status methods
    def get_light_sensor_status(self):
        """Get light sensor status for UI"""
        if hasattr(self, 'sensor_service'):
            return self.sensor_service.get_light_sensor_status()
        return {
            'current_level': True,
            'raw_value': 1,
            'gpio_available': False,
            'using_mock': True
        }
    
    def get_service_status(self):
        """Get status of all services for debugging"""
        status = {}
        
        if hasattr(self, 'sensor_service'):
            status['sensors'] = {
                'available': self.sensor_service.sensor_available,
                'using_mock': getattr(self.sensor_service, 'using_mock_sensors', True),
                'gpio_available': getattr(self.sensor_service, 'gpio_available', False)
            }
            
        if hasattr(self, 'volume_service'):
            status['volume'] = self.volume_service.get_status()
            
        status['auto_theme'] = {
            'enabled': self.auto_theme_enabled,
            'current_mode': self.theme_mode,
            'switch_pending': self._theme_switch_pending,
            'monitoring_active': self._theme_monitoring_active,
            'dark_theme_available': self._check_dark_theme_available()
        }
        
        return status

if __name__ == "__main__":
    logger.info("=== STARTING BEDROCK APP ===")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python version: {sys.version}")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Fatal error running app: {e}")
        with open('bedrock_startup_log.txt', 'a') as log_file:
            log_file.write(f"Fatal error running app: {e}\n")
            import traceback
            log_file.write(traceback.format_exc())