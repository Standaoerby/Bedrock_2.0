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

# Configure environment variables
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Raspberry Pi specific settings
if sys.platform.startswith('linux'):
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'

def create_default_dark_theme():
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
                    "font_highlight": [0.8, 0.8, 0.6, 1],
                    "shadow": [0.9, 0.9, 0.9, 0.3],
                    "trend_up": [1, 0.5, 0.5, 1],
                    "trend_down": [0.4, 0.7, 1, 1]
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
            
            logger.info(f"Created default dark theme")
            return True
    except Exception as e:
        logger.error(f"Error creating default dark theme: {e}")
        return False
    
    return False

def load_theme_config(theme="minecraft", mode="light"):
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
            if create_default_dark_theme():
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
    
    # Theme configuration as Kivy property
    theme_config = DictProperty({})
    
    # Auto theme properties
    auto_theme_enabled = BooleanProperty(True)
    current_volume = NumericProperty(50)

    def __init__(self, **kwargs):
        # Load user configuration
        self.user_config = load_user_config()
        
        # Initialize theme properties
        self.theme_name = self.user_config.get("theme", "minecraft")
        self.theme_mode = self.user_config.get("theme_mode", "light")
        self.auto_theme_enabled = self.user_config.get("auto_theme_enabled", True)
        
        # Ensure dark theme exists
        create_default_dark_theme()
        
        # Initialize sound service
        self.sound_service = SoundService()
        
        # Theme switching state
        self._theme_switch_timer = None
        self._auto_theme_event = None
        
        # Call parent init
        super(BedrockApp, self).__init__(**kwargs)
        
        # Load theme config
        try:
            self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
        except Exception as e:
            logger.error(f"Error loading theme: {e}")
            self.theme_config = {"font_name": "Minecraftia", "font_color": [1, 1, 1, 1]}

    def build(self):
        logger.info("Building app...")
        
        # Ensure directories exist
        self.ensure_directories()
        
        # Initialize services
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
            
            return Builder.load_file('main.kv')
        except Exception as e:
            logger.error(f"Error initializing services: {e}")

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
                self.current_volume = self.volume_service.get_volume()
                
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
            
            # Start auto theme after delay
            Clock.schedule_once(self._start_auto_theme, 3)
                
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
    
    def _start_auto_theme(self, dt):
        """Start auto theme monitoring"""
        if self.auto_theme_enabled and self.sensor_service:
            logger.info("Starting auto theme monitoring...")
            
            # Configure fast switching
            self.sensor_service.set_fast_switching(enabled=True, confidence=0.8)
            switch_delay = max(1, self.user_config.get("theme_switch_delay", 2))
            self.sensor_service.calibrate_light_sensor(switch_delay)
            
            # Check every 2 seconds
            self._auto_theme_event = Clock.schedule_interval(self._check_auto_theme, 2)
    
    def on_stop(self):
        """Clean up when the application exits"""
        logger.info("App stopping...")
        
        # Stop auto theme monitoring
        if self._auto_theme_event:
            self._auto_theme_event.cancel()
        if self._theme_switch_timer:
            self._theme_switch_timer.cancel()
        
        # Stop services
        for service_name in ['sensor_service', 'volume_service', 'sound_service']:
            if hasattr(self, service_name):
                try:
                    getattr(self, service_name).stop()
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")

    def _update_current_screen(self, instance, value):
        """Update current screen property"""
        self.current_screen = value
        if not self.menu_navigation:
            self.play_sound("success")
        self.menu_navigation = False
    
    def _check_auto_theme(self, dt):
        """Check if theme should be switched based on light sensor"""
        if not self.auto_theme_enabled or not self.sensor_service:
            return
            
        try:
            # Check for light level changes
            light_changed = self.sensor_service.is_light_changed()
            
            if light_changed:
                current_light = self.sensor_service.get_light_level()
                target_mode = "light" if current_light else "dark"
                
                if target_mode != self.theme_mode:
                    logger.info(f"Light changed: switching to {target_mode} mode")
                    self._schedule_theme_switch(target_mode)
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")
    
    def _schedule_theme_switch(self, target_mode):
        """Schedule theme switch with delay"""
        if self._theme_switch_timer:
            self._theme_switch_timer.cancel()
            
        if not os.path.exists(f"themes/{self.theme_name}/dark/theme.json") and target_mode == "dark":
            if not create_default_dark_theme():
                return
    
        delay = max(1, self.user_config.get("theme_switch_delay", 2))
        logger.info(f"Scheduling theme switch to {target_mode} in {delay}s")
        
        self._theme_switch_timer = Clock.schedule_once(
            lambda dt: self._execute_theme_switch(target_mode), 
            delay
        )
    
    def _execute_theme_switch(self, target_mode):
        """Execute the theme switch"""
        try:
            if target_mode != self.theme_mode:
                logger.info(f"Switching theme: {self.theme_mode} → {target_mode}")
                
                if self.switch_theme_mode(target_mode):
                    # Show notification
                    if hasattr(self, 'notification_service'):
                        self.notification_service.add(f"Theme switched to {target_mode}", "system")
                    
                    self.play_sound("success")
                    logger.info(f"Theme switched successfully to {target_mode}")
                    
        except Exception as e:
            logger.error(f"Error executing theme switch: {e}")
        finally:
            self._theme_switch_timer = None
    
    def switch_theme_mode(self, mode):
        """Switch theme mode with UI refresh"""
        try:
            if mode not in ["light", "dark"]:
                return False
            
            # Load new theme config
            new_theme_config = load_theme_config(self.theme_name, mode)
            if not new_theme_config:
                return False
            
            # Update properties
            self.theme_mode = mode
            self.theme_config = new_theme_config
            
            # Update user config
            self.user_config["theme_mode"] = mode
            save_user_config(self.user_config)
            
            # Force UI update
            self.property('theme_config').dispatch(self)
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching theme mode: {e}")
            return False
    
    def set_auto_theme_enabled(self, enabled):
        """Enable/disable auto theme switching"""
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        save_user_config(self.user_config)
        
        if enabled and not self._auto_theme_event:
            Clock.schedule_once(self._start_auto_theme, 1)
        elif not enabled and self._auto_theme_event:
            self._auto_theme_event.cancel()
            self._auto_theme_event = None
            
        logger.info(f"Auto theme switching {'enabled' if enabled else 'disabled'}")
    
    def _on_volume_changed(self, volume, action):
        """Callback for volume changes"""
        self.current_volume = volume

if __name__ == "__main__":
    logger.info("Starting Bedrock App")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")