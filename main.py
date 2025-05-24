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

def load_theme_config(theme="minecraft", mode="light"):
    path = f"themes/{theme}/{mode}/theme.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"Loaded theme config from {path}")
        return config
    except Exception as e:
        logger.error(f"Error loading theme config: {e}")
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
    
    # Auto theme properties
    auto_theme_enabled = BooleanProperty(True)
    current_volume = NumericProperty(50)

    def __init__(self, **kwargs):
        # Load user configuration
        self.user_config = load_user_config()
        
        # Initialize theme_config BEFORE parent init to ensure it's available for KV loading
        self.theme_name = self.user_config.get("theme", "minecraft")
        self.theme_mode = self.user_config.get("theme_mode", "light")
        self.auto_theme_enabled = self.user_config.get("auto_theme_enabled", True)
        
        try:
            self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
            logger.info("Theme initialized in __init__")
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
        
        # Initialize sound service
        self.sound_service = SoundService()
        
        # Theme switching state - УЛУЧШЕНО
        self._theme_switch_pending = False
        self._theme_switch_timer = None
        self._last_theme_switch = 0  # Prevent rapid switching
        
        # Call parent init after our initializations
        super(BedrockApp, self).__init__(**kwargs)

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
            "themes/minecraft/dark",  # ДОБАВЛЕНО: убеждаемся что папка темной темы существует
            "media/ringtones",
            "cache",
            "config",
            "pages",
            "logs"
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
        logger.info("Directories checked")
    
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
            
            # Start auto theme checking
            if self.auto_theme_enabled:
                self._start_auto_theme_monitoring()
                
            logger.info("Screen manager bound successfully")
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"on_start error: {e}\n")
                import traceback
                log_file.write(traceback.format_exc())
        
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
    
    # ИСПРАВЛЕННЫЕ методы автоматического переключения тем
    def _start_auto_theme_monitoring(self):
        """Start monitoring light sensor for auto theme switching"""
        if not self.auto_theme_enabled:
            logger.info("Auto theme monitoring disabled in config")
            return
            
        # Проверяем наличие темной темы
        if not self._check_dark_theme_available():
            logger.warning("Dark theme not available - auto theme switching disabled")
            return
            
        logger.info("Starting auto theme monitoring")
        # Check every 5 seconds (увеличена частота)
        self._auto_theme_event = Clock.schedule_interval(self._check_auto_theme_switch, 5)
        
        # Initial check
        Clock.schedule_once(lambda dt: self._check_auto_theme_switch(dt), 2)
    
    def _stop_auto_theme_monitoring(self):
        """Stop auto theme monitoring"""
        if hasattr(self, '_auto_theme_event'):
            self._auto_theme_event.cancel()
        if self._theme_switch_timer:
            self._theme_switch_timer.cancel()
            self._theme_switch_timer = None
        logger.info("Auto theme monitoring stopped")
    
    def _check_dark_theme_available(self):
        """Check if dark theme is available for current theme"""
        dark_theme_path = f"themes/{self.theme_name}/dark/theme.json"
        available = os.path.exists(dark_theme_path)
        logger.info(f"Dark theme check: {dark_theme_path} {'exists' if available else 'missing'}")
        return available
    
    def _check_auto_theme_switch(self, dt):
        """Check if theme should be switched based on light sensor - ИСПРАВЛЕНО"""
        if not self.auto_theme_enabled:
            return
            
        try:
            if not hasattr(self, 'sensor_service') or not self.sensor_service.sensor_available:
                logger.debug("Sensor service not available for auto theme switching")
                return
            
            # Prevent rapid switching
            current_time = time.time()
            if current_time - self._last_theme_switch < 10:  # Minimum 10 seconds between switches
                return
                
            # Check if light level changed
            if self.sensor_service.is_light_changed():
                current_light = self.sensor_service.get_light_level()
                target_mode = "light" if current_light else "dark"
                
                # Check if we need to switch
                if target_mode != self.theme_mode:
                    logger.info(f"Light level changed: {self.theme_mode} → {target_mode} (sensor: {'Light' if current_light else 'Dark'})")
                    self._schedule_theme_switch(target_mode)
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")
    
    def _schedule_theme_switch(self, target_mode):
        """Schedule theme switch with delay to avoid rapid switching - ИСПРАВЛЕНО"""
        if self._theme_switch_pending:
            logger.debug("Theme switch already pending, skipping")
            return  # Switch already pending
            
        if not self._check_dark_theme_available():
            logger.warning(f"Cannot switch to {target_mode} mode - dark theme not available")
            return
            
        delay = self.user_config.get("theme_switch_delay", 3)
        self._theme_switch_pending = True
        
        logger.info(f"Scheduling theme switch to {target_mode} in {delay} seconds")
        self._theme_switch_timer = Clock.schedule_once(
            lambda dt: self._execute_theme_switch(target_mode), 
            delay
        )
    
    def _execute_theme_switch(self, target_mode):
        """Execute the theme switch - ИСПРАВЛЕНО"""
        try:
            if target_mode != self.theme_mode:
                logger.info(f"Executing theme switch: {self.theme_mode} → {target_mode}")
                
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
                    
                    logger.info(f"✓ Theme successfully switched to {target_mode}")
                else:
                    logger.error(f"Failed to switch theme to {target_mode}")
                    
        except Exception as e:
            logger.error(f"Error executing theme switch: {e}")
        finally:
            self._theme_switch_pending = False
            self._theme_switch_timer = None
    
    def switch_theme_mode(self, mode):
        """Switch theme mode (light/dark) - ИСПРАВЛЕНО"""
        try:
            if mode not in ["light", "dark"]:
                logger.error(f"Invalid theme mode: {mode}")
                return False
            
            # Check if dark theme exists
            if mode == "dark" and not self._check_dark_theme_available():
                logger.error(f"Dark theme not available for {self.theme_name}")
                return False
                
            # Load new theme config
            new_theme_config = load_theme_config(self.theme_name, mode)
            if not new_theme_config:
                logger.error(f"Failed to load theme config for {self.theme_name}/{mode}")
                return False
            
            # Update properties
            old_mode = self.theme_mode
            self.theme_mode = mode
            self.theme_config = new_theme_config
            
            # Update user config
            self.user_config["theme_mode"] = mode
            save_user_config(self.user_config)
            
            # КРИТИЧЕСКИ ВАЖНО: Обновить UI
            self._apply_theme_to_ui()
            
            logger.info(f"Theme mode switched: {old_mode} → {mode}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching theme mode: {e}")
            return False
    
    def _apply_theme_to_ui(self):
        """Apply current theme to all UI elements - НОВЫЙ МЕТОД"""
        try:
            logger.info("Applying theme to UI...")
            
            # Trigger property updates to refresh all UI elements
            # This forces all widgets to re-read theme_config
            self.property('theme_config').dispatch(self)
            
            # Force refresh of current screen
            if hasattr(self.root, 'ids') and 'screen_manager' in self.root.ids:
                current_screen_name = self.root.ids.screen_manager.current
                current_screen = self.root.ids.screen_manager.get_screen(current_screen_name)
                
                # Trigger screen refresh by temporarily switching away and back
                Clock.schedule_once(lambda dt: self._refresh_current_screen(current_screen_name), 0.1)
            
            logger.info("Theme applied to UI successfully")
            
        except Exception as e:
            logger.error(f"Error applying theme to UI: {e}")
    
    def _refresh_current_screen(self, target_screen):
        """Refresh current screen to apply new theme"""
        try:
            screen_manager = self.root.ids.screen_manager
            
            # Briefly switch to a different screen and back to force refresh
            temp_screen = "home" if target_screen != "home" else "alarm"
            
            screen_manager.current = temp_screen
            Clock.schedule_once(lambda dt: setattr(screen_manager, 'current', target_screen), 0.05)
            
        except Exception as e:
            logger.error(f"Error refreshing screen: {e}")
    
    def set_auto_theme_enabled(self, enabled):
        """Enable/disable auto theme switching - ИСПРАВЛЕНО"""
        old_state = self.auto_theme_enabled
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        save_user_config(self.user_config)
        
        if enabled and not old_state:
            # Starting auto theme
            logger.info("Auto theme switching enabled")
            self._start_auto_theme_monitoring()
        elif not enabled and old_state:
            # Stopping auto theme
            logger.info("Auto theme switching disabled")
            self._stop_auto_theme_monitoring()
            
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
                'using_mock': self.sensor_service.using_mock_sensors,
                'gpio_available': self.sensor_service.gpio_available
            }
            
        if hasattr(self, 'volume_service'):
            status['volume'] = self.volume_service.get_status()
            
        status['auto_theme'] = {
            'enabled': self.auto_theme_enabled,
            'current_mode': self.theme_mode,
            'switch_pending': self._theme_switch_pending,
            'dark_theme_available': self._check_dark_theme_available()
        }
        
        return status

if __name__ == "__main__":
    logger.info("Starting Bedrock App...")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Error running app: {e}")
        with open('bedrock_startup_log.txt', 'a') as log_file:
            log_file.write(f"Fatal error running app: {e}\n")
            import traceback
            log_file.write(traceback.format_exc())