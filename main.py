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
    os.environ['KIVY_LOG_LEVEL'] = 'debug'

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
            
            logger.info(f"Created default dark theme at {theme_file}")
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
                "menu_unselected_color": [0.7, 0.7, 0.7, 1], "overlay_images": {},
                "colors": {"shadow": [0.1, 0.1, 0.1, 0.5], "trend_up": [1, 0.3, 0.3, 1], "trend_down": [0.2, 0.6, 1, 1]}}

def load_user_config():
    """Load user configuration from file"""
    try:
        with open("config/user.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading user config: {e}")
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

def safe_kv_load():
    """Load KV file with error handling"""
    try:
        with open('main.kv', 'r') as f:
            kv_content = f.read()
        
        kv_content = re.sub(
            r'app\.theme_config\["([^"]+)"\]', 
            r'app.theme_config.get("\1", "")', 
            kv_content
        )
        
        return Builder.load_string(kv_content)
    except Exception as e:
        logger.error(f"Error in safe_kv_load: {e}")
        return Builder.load_file('main.kv')

# Register font
try:
    LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
    logger.info("Font registered successfully")
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
    logger.info("Screen imports successful")
except Exception as e:
    logger.error(f"Error importing screens: {e}")

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
    
    # Theme configuration as Kivy property
    theme_config = DictProperty({})
    
    # Auto theme properties
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
        
        # Theme switching state
        self._theme_switch_pending = False
        self._theme_switch_timer = None
        self._last_theme_switch = 0
        self._theme_monitoring_active = False
        self._auto_theme_event = None
        
        # Call parent init
        super(BedrockApp, self).__init__(**kwargs)
        
        # Load theme config
        try:
            loaded_theme_config = load_theme_config(self.theme_name, self.theme_mode)
            self.theme_config = loaded_theme_config
            logger.info(f"Theme initialized: {self.theme_name}/{self.theme_mode}")
        except Exception as e:
            logger.error(f"Error initializing theme in __init__: {e}")
            self.theme_config = {
                "background_image": "",
                "menu_button_normal": "",
                "font_name": "Minecraftia",
                "font_color": [1, 1, 1, 1],
                "menu_selected_color": [1, 1, 1, 1],
                "menu_unselected_color": [0.7, 0.7, 0.7, 1],
                "overlay_images": {},
                "colors": {"shadow": [0.1, 0.1, 0.1, 0.5], "trend_up": [1, 0.3, 0.3, 1], "trend_down": [0.2, 0.6, 1, 1]}
            }

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

    def _init_sensors_async(self):
        """Initialize sensors in background thread"""
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
        logger.info("Directories checked and created if needed")
    
    def play_sound(self, sound_name="click"):
        """Play sound via sound service"""
        self.sound_service.play_sound(sound_name)

    def get_overlay_image(self, page):
        """Get overlay image for page"""
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        logger.info("App starting...")
        try:
            self.root.ids.screen_manager.bind(current=self._update_current_screen)
            
            # Start auto theme checking with delay
            Clock.schedule_once(self._delayed_auto_theme_start, 3)
                
            logger.info("Screen manager bound successfully")
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
    
    def _delayed_auto_theme_start(self, dt):
        """Start auto theme monitoring with fast switching"""
        if self.auto_theme_enabled:
            logger.info("Starting FAST auto theme monitoring...")
            
            # Configure fast switching
            if self.sensor_service:
                self.sensor_service.set_fast_switching(enabled=True, confidence=0.8)
                switch_delay = self.user_config.get("theme_switch_delay", 3)
                self.sensor_service.calibrate_light_sensor(switch_delay)
            
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
        """Update current screen property"""
        self.current_screen = value
        logger.info(f"Screen changed to {value}")
        
        if not self.menu_navigation:
            self.play_sound("success")
            
        self.menu_navigation = False
    
    # AUTO THEME SWITCHING METHODS
    
    def _start_auto_theme_monitoring(self):
        """Start monitoring light sensor for theme switching"""
        if not self.auto_theme_enabled:
            logger.info("Auto theme monitoring disabled in user config")
            return
            
        # Check if dark theme is available
        if not self._check_dark_theme_available():
            logger.warning("Dark theme not available - auto theme switching disabled")
            if create_default_dark_theme():
                logger.info("Created default dark theme, retrying...")
            else:
                logger.error("Failed to create dark theme")
                return
        
        # Check sensor availability
        if not self.sensor_service:
            logger.warning("Sensor service not available for auto theme monitoring")
            return
            
        if not self.sensor_service.sensor_available:
            logger.warning("Sensor service not available - using mock sensor for auto theme testing")
        
        if self._theme_monitoring_active:
            logger.info("Auto theme monitoring already active")
            return
            
        logger.info("=== STARTING FAST AUTO THEME MONITORING ===")
        logger.info(f"Current theme: {self.theme_name}/{self.theme_mode}")
        logger.info(f"Auto theme enabled: {self.auto_theme_enabled}")
        logger.info(f"Sensor available: {self.sensor_service.sensor_available}")
        
        # Get initial light state
        initial_light = self.sensor_service.get_light_level()
        logger.info(f"Initial light level: {'Light' if initial_light else 'Dark'}")
        
        # Initialize sensor state if needed
        if not hasattr(self.sensor_service, '_last_light_state') or self.sensor_service._last_light_state is None:
            self.sensor_service._last_light_state = initial_light
            logger.info(f"Initialized sensor last light state: {'Light' if initial_light else 'Dark'}")
        
        # Fast checking every 1.5 seconds
        self._auto_theme_event = Clock.schedule_interval(self._check_auto_theme_switch, 1.5)
        self._theme_monitoring_active = True
        
        # Initial check after 1 second
        Clock.schedule_once(lambda dt: self._check_auto_theme_switch(dt), 1)
        
        logger.info("✅ Fast auto theme monitoring started successfully")
    
    def _stop_auto_theme_monitoring(self):
        """Stop auto theme monitoring"""
        if self._auto_theme_event:
            self._auto_theme_event.cancel()
            self._auto_theme_event = None
        if self._theme_switch_timer:
            self._theme_switch_timer.cancel()
            self._theme_switch_timer = None
        self._theme_monitoring_active = False
        logger.info("Auto theme monitoring stopped")
    
    def _check_dark_theme_available(self):
        """Check if dark theme is available"""
        dark_theme_path = f"themes/{self.theme_name}/dark/theme.json"
        available = os.path.exists(dark_theme_path)
        logger.debug(f"Dark theme check: {dark_theme_path} {'exists' if available else 'missing'}")
        return available
    
    def _check_auto_theme_switch(self, dt):
        """Check if theme should be switched based on light sensor"""
        if not self.auto_theme_enabled:
            return
            
        try:
            if not self.sensor_service:
                logger.debug("Sensor service not available for auto theme switching")
                return
            
            # Prevent rapid switching
            current_time = time.time()
            if current_time - self._last_theme_switch < 15:
                return
                
            # Get current light level
            current_light = self.sensor_service.get_light_level()
            
            # Debug logging every 10 checks
            if not hasattr(self, '_debug_check_counter'):
                self._debug_check_counter = 0
            self._debug_check_counter += 1
            
            if self._debug_check_counter % 10 == 0:
                logger.info(f"=== AUTO THEME CHECK #{self._debug_check_counter} ===")
                logger.info(f"Current light level: {'Light' if current_light else 'Dark'}")
                logger.info(f"Current theme mode: {self.theme_mode}")
                logger.info(f"Switch pending: {self._theme_switch_pending}")
            
            # Check for light level changes
            light_changed = self.sensor_service.is_light_changed()
            
            if light_changed:
                target_mode = "light" if current_light else "dark"
                current_mode = self.theme_mode
                
                logger.info(f"🌟 LIGHT LEVEL CHANGED DETECTED! 🌟")
                logger.info(f"Current light: {'Light' if current_light else 'Dark'}")
                logger.info(f"Target mode: {target_mode}")
                logger.info(f"Current mode: {current_mode}")
                
                # Check if theme switch is needed
                if target_mode != current_mode:
                    logger.info(f"🔄 SCHEDULING THEME SWITCH: {current_mode} → {target_mode}")
                    self._schedule_theme_switch(target_mode)
                else:
                    logger.info(f"Theme mode already matches light level: {target_mode}")
            else:
                if self._debug_check_counter % 20 == 0:
                    logger.debug(f"No light level change detected (check #{self._debug_check_counter})")
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _schedule_theme_switch(self, target_mode):
        """Schedule theme switch with delay"""
        if self._theme_switch_pending:
            logger.info("Theme switch already pending, cancelling previous and scheduling new")
            if self._theme_switch_timer:
                self._theme_switch_timer.cancel()
            self._theme_switch_pending = False
            
        if not self._check_dark_theme_available():
            logger.error(f"Cannot switch to {target_mode} mode - dark theme not available")
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
        """Execute the theme switch"""
        try:
            logger.info(f"🚀 EXECUTING THEME SWITCH to {target_mode}")
            
            if target_mode != self.theme_mode:
                logger.info(f"Switching theme: {self.theme_mode} → {target_mode}")
                
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
        """Switch theme mode with UI refresh"""
        try:
            logger.info(f"🎨 === SWITCHING THEME MODE: {self.theme_mode} → {mode} ===")
            
            if mode not in ["light", "dark"]:
                logger.error(f"Invalid theme mode: {mode}")
                return False
            
            # Check if dark theme exists
            if mode == "dark" and not self._check_dark_theme_available():
                logger.error(f"Dark theme not available for {self.theme_name}")
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
            self.theme_mode = mode
            self.theme_config = new_theme_config
            
            logger.info(f"✅ Updated theme properties: {old_mode} → {self.theme_mode}")
            
            # Update user config
            self.user_config["theme_mode"] = mode
            if save_user_config(self.user_config):
                logger.info("✅ User config saved successfully")
            else:
                logger.error("❌ Failed to save user config")
            
            # FIXED: Force UI update with special handling for conditional colors
            logger.info("🔄 Starting enhanced UI refresh...")
            self._force_enhanced_ui_update()
            
            logger.info(f"✅ Theme mode switched: {old_mode} → {mode}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error switching theme mode: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _force_enhanced_ui_update(self):
        """FIXED: Enhanced UI update that handles conditional colors"""
        try:
            logger.info("🚀 ENHANCED UI UPDATE")
            
            # 1. Multiple property dispatches for reliability
            for i in range(3):
                try:
                    self.property('theme_config').dispatch(self)
                    logger.info(f"✅ Property dispatch #{i+1} completed")
                except Exception as e:
                    logger.error(f"Property dispatch #{i+1} failed: {e}")
            
            # 2. Force screen updates
            if hasattr(self.root, 'ids') and 'screen_manager' in self.root.ids:
                screen_manager = self.root.ids.screen_manager
                current_screen_name = screen_manager.current
                
                # Update all screens
                for screen in screen_manager.screens:
                    try:
                        self._update_screen_theme(screen)
                    except Exception as e:
                        logger.error(f"Error updating screen {screen.name}: {e}")
                
                # FIXED: Special handling for Home screen conditional colors
                try:
                    home_screen = screen_manager.get_screen("home")
                    Clock.schedule_once(lambda dt: self._fix_home_screen_colors(home_screen), 0.1)
                    Clock.schedule_once(lambda dt: self._fix_home_screen_colors(home_screen), 0.5)  # Second pass
                except Exception as e:
                    logger.error(f"Error in home screen color fix: {e}")
                
                # Additional update for current screen
                try:
                    current_screen = screen_manager.get_screen(current_screen_name)
                    Clock.schedule_once(lambda dt: self._final_screen_update(current_screen), 0.2)
                except Exception as e:
                    logger.error(f"Error in current screen update: {e}")
            
            # 3. Update main background
            self._update_main_background()
            
            logger.info("🎯 Enhanced UI update completed")
            
        except Exception as e:
            logger.error(f"Error in enhanced UI update: {e}")
    
    def _fix_home_screen_colors(self, home_screen):
        """FIXED: Special method to fix conditional colors on home screen"""
        try:
            logger.info("🎨 Fixing home screen conditional colors...")
            
            def find_and_fix_conditional_colors(widget):
                """Find and fix widgets with conditional colors"""
                try:
                    # Check if this is the clock shadow
                    if hasattr(widget, 'id') and widget.id == 'clock_shadow_label':
                        # Set shadow color based on theme mode
                        if self.theme_mode == "light":
                            shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.1, 0.1, 0.1, 0.5])
                        else:
                            shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.9, 0.9, 0.9, 0.3])
                        
                        widget.color = shadow_color
                        logger.info(f"🔧 Fixed clock shadow color: {shadow_color}")
                    
                    # Check if this is the weather trend arrow
                    elif hasattr(widget, 'id') and widget.id == 'weather_trend_label':
                        # Get the arrow text to determine color
                        arrow_text = getattr(widget, 'text', '')
                        
                        if arrow_text == "↓":  # Down arrow (cooler)
                            trend_color = self.theme_config.get("colors", {}).get("trend_down", [0.2, 0.6, 1, 1])
                        elif arrow_text == "↑":  # Up arrow (warmer)
                            trend_color = self.theme_config.get("colors", {}).get("trend_up", [1, 0.3, 0.3, 1])
                        else:  # No change or equals
                            trend_color = self.theme_config.get("font_color", [1, 1, 1, 1])
                        
                        widget.color = trend_color
                        logger.info(f"🔧 Fixed weather trend color: {arrow_text} -> {trend_color}")
                    
                    # Recursively check children
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            find_and_fix_conditional_colors(child)
                            
                except Exception as e:
                    logger.debug(f"Error fixing widget colors: {e}")
            
            # Start the recursive fix
            find_and_fix_conditional_colors(home_screen)
            
            logger.info("✅ Home screen color fixes applied")
            
        except Exception as e:
            logger.error(f"Error fixing home screen colors: {e}")
    
    def _update_screen_theme(self, screen):
        """Update theme for a specific screen"""
        try:
            def update_widget_theme(widget):
                try:
                    widget_class = widget.__class__.__name__
                    
                    # Update colors based on widget type
                    if hasattr(widget, 'color'):
                        if 'Label' in widget_class or 'ThemedLabel' in widget_class:
                            # Don't override widgets with special IDs that need conditional colors
                            widget_id = getattr(widget, 'id', '')
                            if widget_id not in ['clock_shadow_label', 'weather_trend_label']:
                                widget.color = self.theme_config.get("font_color", [1, 1, 1, 1])
                    
                    # Update fonts
                    if hasattr(widget, 'font_name'):
                        widget.font_name = self.theme_config.get("font_name", "Minecraftia")
                    
                    # Update canvas
                    if hasattr(widget, 'canvas'):
                        widget.canvas.ask_update()
                    
                    # Update panels
                    if 'Panel' in widget_class or 'ThemedPanel' in widget_class:
                        if hasattr(widget, 'canvas') and hasattr(widget.canvas, 'before'):
                            widget.canvas.before.clear()
                            with widget.canvas.before:
                                from kivy.graphics import Color, RoundedRectangle
                                Color(*self.theme_config.get("panel_bg", [0, 0, 0, 0.2]))
                                RoundedRectangle(
                                    pos=widget.pos, 
                                    size=widget.size,
                                    radius=[self.theme_config.get("panel_radius", 16)]
                                )
                    
                    # Recursively update children
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            update_widget_theme(child)
                            
                except Exception as e:
                    logger.debug(f"Error updating widget {widget}: {e}")
            
            update_widget_theme(screen)
            
        except Exception as e:
            logger.error(f"Error updating screen theme: {e}")
    
    def _final_screen_update(self, screen):
        """Final update for screen"""
        try:
            self.property('theme_config').dispatch(self)
            self._update_screen_theme(screen)
            self._update_screen_overlays(screen)
            
            # Special handling for home screen
            if screen.name == "home":
                self._fix_home_screen_colors(screen)
                
        except Exception as e:
            logger.error(f"Error in final screen update: {e}")

    def _update_screen_overlays(self, screen):
        """Update overlay images for screen"""
        try:
            def find_and_update_overlays(widget):
                try:
                    if hasattr(widget, 'source') and isinstance(widget.source, str):
                        if 'overlay_' in widget.source or '/overlay_' in widget.source:
                            screen_name = screen.name
                            new_overlay = self.get_overlay_image(screen_name)
                            if new_overlay and new_overlay != widget.source:
                                logger.info(f"🖼️  Updating overlay: {widget.source} → {new_overlay}")
                                widget.source = new_overlay
                                widget.reload()
                    
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            find_and_update_overlays(child)
                            
                except Exception as e:
                    logger.debug(f"Error updating overlay: {e}")
            
            find_and_update_overlays(screen)
            
        except Exception as e:
            logger.error(f"Error updating screen overlays: {e}")

    def _update_main_background(self):
        """Update main background image"""
        try:
            if hasattr(self.root, 'ids') and 'background_image' in self.root.ids:
                bg_image = self.root.ids.background_image
                new_bg = self.theme_config.get("background_image", "")
                if new_bg and new_bg != bg_image.source:
                    logger.info(f"🖼️  Updating main background: {bg_image.source} → {new_bg}")
                    bg_image.source = new_bg
                    bg_image.reload()
        except Exception as e:
            logger.error(f"Error updating main background: {e}")
    
    def set_auto_theme_enabled(self, enabled):
        """Enable/disable auto theme switching"""
        old_state = self.auto_theme_enabled
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        save_user_config(self.user_config)
        
        logger.info(f"=== AUTO THEME SETTING CHANGED ===")
        logger.info(f"Old state: {old_state}")
        logger.info(f"New state: {enabled}")
        
        if enabled and not old_state:
            logger.info("🟢 Starting auto theme monitoring...")
            self._start_auto_theme_monitoring()
        elif not enabled and old_state:
            logger.info("🔴 Stopping auto theme monitoring...")
            self._stop_auto_theme_monitoring()
        else:
            logger.info(f"Auto theme state unchanged: {enabled}")
            
        logger.info(f"Auto theme switching {'enabled' if enabled else 'disabled'}")
    
    # VOLUME CONTROL METHODS
    
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
    
    # SENSOR STATUS METHODS
    
    def get_light_sensor_status(self):
        """Get light sensor status for UI"""
        if hasattr(self, 'sensor_service') and self.sensor_service:
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
        
        if hasattr(self, 'sensor_service') and self.sensor_service:
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
        import traceback
        logger.critical(traceback.format_exc())