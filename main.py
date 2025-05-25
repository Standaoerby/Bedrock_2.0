from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.cache import Cache
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
                    "tiny": "12sp",
                    "small": "14sp",
                    "default": "18sp",
                    "medium": "20sp",
                    "large": "26sp",
                    "xlarge": "34sp",
                    "huge": "240sp"
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
        self._load_current_theme()

    def _load_current_theme(self):
        """Load current theme configuration"""
        try:
            self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
            logger.info(f"Loaded theme: {self.theme_name}/{self.theme_mode}")
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
        
        # Stop services with proper error handling
        services_to_stop = [
            ('sensor_service', 'stop'),
            ('volume_service', 'stop'), 
            ('sound_service', 'cleanup'),  # Используем cleanup вместо stop
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

    def _clear_image_cache(self):
        """Clear Kivy image cache to force reload of theme images"""
        try:
            # Clear all image caches
            Cache.remove('kv.image')
            Cache.remove('kv.texture')
            Cache.remove('kv.loader')
            
            # Clear specific theme images
            theme_images = []
            
            # Background images
            theme_images.extend([
                f"themes/{self.theme_name}/light/background.png",
                f"themes/{self.theme_name}/dark/background.png"
            ])
            
            # Overlay images for each screen
            for screen in ['home', 'alarm', 'schedule', 'weather', 'pigs', 'settings']:
                theme_images.extend([
                    f"themes/{self.theme_name}/light/overlay_{screen}.png",
                    f"themes/{self.theme_name}/dark/overlay_{screen}.png"
                ])
            
            # Button images
            theme_images.extend([
                f"themes/{self.theme_name}/light/menu_button.png",
                f"themes/{self.theme_name}/dark/menu_button.png",
                f"themes/{self.theme_name}/light/button.png",
                f"themes/{self.theme_name}/dark/button.png"
            ])
            
            # Remove specific images from cache using different key formats
            for img_path in theme_images:
                if os.path.exists(img_path):
                    # Try different cache key formats that Kivy uses
                    cache_keys = [
                        img_path,
                        f"{img_path}|False|0",  # Format: path|keep_data|mipmap
                        f"{img_path}|True|0",
                        os.path.abspath(img_path),
                        os.path.abspath(img_path) + "|False|0"
                    ]
                    
                    for key in cache_keys:
                        try:
                            Cache.remove('kv.image', key)
                            Cache.remove('kv.texture', key)
                        except:
                            pass
            
            # Clear CoreImage cache
            if hasattr(CoreImage, '_cache'):
                CoreImage._cache.clear()
            
            logger.info("Image cache cleared for theme switching")
            
        except Exception as e:
            logger.error(f"Error clearing image cache: {e}")

    def _reload_all_images(self, dt):
        """Force reload all Image widgets in the app"""
        try:
            def reload_images_in_widget(widget):
                """Recursively reload images in widget tree"""
                if hasattr(widget, 'source') and widget.source:
                    # This is an Image widget
                    if hasattr(widget, 'reload'):
                        try:
                            widget.reload()
                            logger.debug(f"Reloaded image: {widget.source}")
                        except:
                            # Fallback: clear and reset source
                            old_source = widget.source
                            widget.source = ""
                            Clock.schedule_once(lambda dt: setattr(widget, 'source', old_source), 0.1)
                
                # Recurse through children
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        reload_images_in_widget(child)
            
            # Start from root widget
            if self.root:
                reload_images_in_widget(self.root)
                
            logger.info("All images reloaded")
            
        except Exception as e:
            logger.error(f"Error reloading images: {e}")

    def _update_background_images(self):
        """Update only background images"""
        try:
            new_bg = self.theme_config.get("background_image", "")
            
            # Find and update background image
            def find_and_update_bg(widget):
                if hasattr(widget, 'source') and widget.source:
                    if 'background' in widget.source or (hasattr(widget, 'id') and widget.id == 'background_image'):
                        logger.info(f"Updating background: {widget.source} → {new_bg}")
                        widget.source = ""
                        Clock.schedule_once(lambda dt: setattr(widget, 'source', new_bg), 0.1)
                        return True
                
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        if find_and_update_bg(child):
                            return True
                return False
            
            if self.root:
                find_and_update_bg(self.root)
                
        except Exception as e:
            logger.error(f"Error updating background images: {e}")

    def _update_overlay_images(self):
        """Update overlay images for current screen"""
        try:
            current_screen_name = self.root.ids.screen_manager.current
            current_screen = self.root.ids.screen_manager.get_screen(current_screen_name)
            new_overlay = self.get_overlay_image(current_screen_name)
            
            def find_and_update_overlay(widget):
                if hasattr(widget, 'source') and widget.source:
                    if 'overlay_' in widget.source or current_screen_name in widget.source:
                        logger.info(f"Updating overlay: {widget.source} → {new_overlay}")
                        widget.source = ""
                        Clock.schedule_once(lambda dt: setattr(widget, 'source', new_overlay), 0.1)
                        return True
                
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        if find_and_update_overlay(child):
                            return True
                return False
            
            find_and_update_overlay(current_screen)
            
        except Exception as e:
            logger.error(f"Error updating overlay images: {e}")

    def _force_complete_ui_refresh(self):
        """Force complete UI refresh by rebuilding key elements"""
        try:
            # Получить текущий экран
            current_screen_name = self.root.ids.screen_manager.current
            current_screen = self.root.ids.screen_manager.get_screen(current_screen_name)
            
            # Обновить фоновое изображение
            self._update_background_images()
            
            # Обновить overlay изображения на текущем экране
            self._update_overlay_images()
            
            # Переключиться на другой экран и обратно для полного обновления
            temp_screens = ["home", "settings", "alarm"]
            temp_screen = next((s for s in temp_screens if s != current_screen_name), "home")
            
            Clock.schedule_once(lambda dt: self._switch_and_back(current_screen_name, temp_screen), 0.2)
            
            logger.info(f"Complete UI refresh initiated for theme: {self.theme_mode}")
            
        except Exception as e:
            logger.error(f"Error in complete UI refresh: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _switch_and_back(self, target_screen, temp_screen):
        """Switch to temp screen and back to force refresh"""
        try:
            # Переключиться на временный экран
            self.root.ids.screen_manager.current = temp_screen
            
            # Вернуться на целевой экран
            Clock.schedule_once(
                lambda dt: setattr(self.root.ids.screen_manager, 'current', target_screen), 
                0.3
            )
            
            logger.info(f"Screen refresh: {target_screen} → {temp_screen} → {target_screen}")
            
        except Exception as e:
            logger.error(f"Error in screen switching: {e}")

    def switch_theme_mode(self, mode):
        """Enhanced theme switching with complete UI refresh"""
        try:
            if mode not in ["light", "dark"]:
                return False
            
            # Check if switching to the same mode
            if mode == self.theme_mode:
                logger.info(f"Already in {mode} mode")
                return True
            
            # Check if dark theme files exist before switching
            if mode == "dark":
                dark_theme_path = f"themes/{self.theme_name}/dark/theme.json"
                if not os.path.exists(dark_theme_path):
                    logger.warning(f"Dark theme file not found: {dark_theme_path}")
                    if not create_default_dark_theme():
                        logger.error("Failed to create default dark theme")
                        return False
            
            # Load new theme config
            new_theme_config = load_theme_config(self.theme_name, mode)
            if not new_theme_config:
                logger.error(f"Failed to load theme config for {mode}")
                return False
            
            logger.info(f"Switching theme from {self.theme_mode} to {mode}")
            
            # STEP 1: Clear image cache BEFORE any changes
            self._clear_image_cache()
            
            # STEP 2: Update theme properties
            old_mode = self.theme_mode
            self.theme_mode = mode
            
            # STEP 3: Completely replace theme_config
            self.theme_config.clear()
            self.theme_config.update(new_theme_config)
            
            # STEP 4: Save user config
            self.user_config["theme_mode"] = mode
            save_user_config(self.user_config)
            
            # STEP 5: Force complete UI refresh with all theme properties
            Clock.schedule_once(lambda dt: self._force_complete_theme_refresh(), 0.1)
            
            logger.info(f"Theme switched: {old_mode} → {mode}")
            logger.info(f"New background: {new_theme_config.get('background_image', 'none')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching theme mode: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    def _force_complete_theme_refresh(self):
        """Force complete theme refresh including colors, shadows, and backgrounds"""
        try:
            logger.info("Starting complete theme refresh...")
            
            # Step 1: Update background images
            self._update_background_images()
            
            # Step 2: Update overlay images
            self._update_overlay_images()
            
            # Step 3: Force refresh all theme-dependent properties
            self._refresh_theme_properties()
            
            # Step 4: Update canvas elements (shadows, backgrounds)
            self._update_canvas_elements()
            
            # Step 5: Force screen refresh
            current_screen = self.root.ids.screen_manager.current
            Clock.schedule_once(lambda dt: self._final_screen_refresh(current_screen), 0.2)
            
            logger.info("Complete theme refresh completed")
            
        except Exception as e:
            logger.error(f"Error in complete theme refresh: {e}")
#d
    def _refresh_theme_properties(self):
        """Force refresh of all theme-dependent Kivy properties"""
        try:
            # Trigger property updates on main app
            self.property('theme_config').dispatch(self)
            self.property('theme_mode').dispatch(self)
            
            # Update all screens
            for screen_name in ['home', 'alarm', 'schedule', 'weather', 'pigs', 'settings']:
                try:
                    screen = self.root.ids.screen_manager.get_screen(screen_name)
                    self._refresh_screen_properties(screen)
                except Exception as e:
                    logger.debug(f"Could not refresh screen {screen_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error refreshing theme properties: {e}")

    def _refresh_screen_properties(self, screen):
        """Refresh properties for a specific screen"""
        try:
            # Force update of all widgets in screen
            def update_widget_properties(widget):
                # Update theme-dependent properties if they exist
                theme_props = ['color', 'background_color', 'canvas']
                
                for prop_name in theme_props:
                    if hasattr(widget, prop_name):
                        try:
                            prop = getattr(widget, prop_name)
                            if hasattr(prop, 'dispatch'):
                                prop.dispatch(widget)
                        except:
                            pass
                
                # Special handling for labels with theme colors
                if hasattr(widget, 'color') and hasattr(widget, 'text'):
                    # Check if this should use theme colors
                    if 'shadow' in str(getattr(widget, 'id', '')):
                        # This is a shadow label - update color
                        shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.2, 0.2, 0.2, 0.4])
                        widget.color = shadow_color
                
                # Recurse through children
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        update_widget_properties(child)
            
            update_widget_properties(screen)
            
        except Exception as e:
            logger.error(f"Error refreshing screen properties: {e}")

    def _update_canvas_elements(self):
        """Update canvas elements like backgrounds and shadows"""
        try:
            def update_canvas_in_widget(widget):
                # Update canvas if it has theme-dependent colors
                if hasattr(widget, 'canvas'):
                    try:
                        # Force canvas update
                        widget.canvas.ask_update()
                        
                        # Special handling for ThemedPanel widgets
                        if 'ThemedPanel' in str(type(widget)):
                            # These should get new panel background colors
                            panel_bg = self.theme_config.get("panel_bg", [0, 0, 0, 0.2])
                            # Canvas will be updated by the widget's drawing code
                    except Exception as e:
                        logger.debug(f"Error updating canvas for widget: {e}")
                
                # Recurse through children
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        update_canvas_in_widget(child)
            
            if self.root:
                update_canvas_in_widget(self.root)
            
        except Exception as e:
            logger.error(f"Error updating canvas elements: {e}")

    def _final_screen_refresh(self, target_screen):
        """Final screen refresh to ensure all changes are applied"""
        try:
            # Quick screen switch to force complete refresh
            temp_screens = ["settings", "home", "alarm"]
            temp_screen = next((s for s in temp_screens if s != target_screen), "home")
            
            # Switch away and back
            self.root.ids.screen_manager.current = temp_screen
            
            # Force immediate update
            Clock.schedule_once(lambda dt: self._return_to_screen(target_screen), 0.1)
            
        except Exception as e:
            logger.error(f"Error in final screen refresh: {e}")

    def _return_to_screen(self, target_screen):
        """Return to the target screen after refresh"""
        try:
            self.root.ids.screen_manager.current = target_screen
            
            # Final canvas update for all widgets
            Clock.schedule_once(lambda dt: self._final_canvas_update(), 0.1)
            
            logger.info(f"Theme refresh completed for screen: {target_screen}")
            
        except Exception as e:
            logger.error(f"Error returning to screen: {e}")

    def _final_canvas_update(self):
        """Final update of all canvas elements"""
        try:
            def force_canvas_update(widget):
                if hasattr(widget, 'canvas'):
                    widget.canvas.ask_update()
                
                # Special handling for shadow labels
                if hasattr(widget, 'id') and 'shadow' in str(widget.id):
                    shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.2, 0.2, 0.2, 0.4])
                    if self.theme_mode == "light":
                        shadow_color = [0.2, 0.2, 0.2, 0.4]  # Dark shadow for light theme
                    else:
                        shadow_color = [0.8, 0.8, 0.8, 0.3]  # Light shadow for dark theme
                    
                    if hasattr(widget, 'color'):
                        widget.color = shadow_color
                
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        force_canvas_update(child)
            
            if self.root:
                force_canvas_update(self.root)
                
        except Exception as e:
            logger.error(f"Error in final canvas update: {e}")
#d

    def debug_theme_state(self):
        """Debug method to check theme state"""
        logger.info("=== THEME DEBUG INFO ===")
        logger.info(f"Current theme_name: {self.theme_name}")
        logger.info(f"Current theme_mode: {self.theme_mode}")
        
        if hasattr(self, 'theme_config'):
            bg_img = self.theme_config.get("background_image", "none")
            logger.info(f"Background image: {bg_img}")
            logger.info(f"Background exists: {os.path.exists(bg_img) if bg_img else False}")
            
            overlays = self.theme_config.get("overlay_images", {})
            logger.info(f"Overlay images: {len(overlays)} defined")
            for page, path in overlays.items():
                logger.info(f"  {page}: {path} (exists: {os.path.exists(path) if path else False})")
        
        logger.info("========================")

    def force_refresh_all_theme_images(self):
        """Force refresh of all theme-related images"""
        try:
            logger.info("Force refreshing all theme images...")
            
            # Clear cache completely
            self._clear_image_cache()
            
            # Update all properties that depend on theme
            if hasattr(self, 'property'):
                self.property('theme_config').dispatch(self)
            
            # Trigger updates for all screens
            for screen_name in ['home', 'alarm', 'schedule', 'weather', 'pigs', 'settings']:
                try:
                    screen = self.root.ids.screen_manager.get_screen(screen_name)
                    # Force property updates on screen
                    if hasattr(screen, 'property'):
                        for prop_name in ['theme_config', 'theme_mode']:
                            if hasattr(screen, prop_name):
                                prop = getattr(screen, prop_name)
                                if hasattr(prop, 'dispatch'):
                                    prop.dispatch(screen)
                except:
                    pass
            
            logger.info("Theme images refresh completed")
            
        except Exception as e:
            logger.error(f"Error in force refresh: {e}")
    
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
        pass  # Volume updates handled by service

if __name__ == "__main__":
    logger.info("Starting Bedrock App")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")