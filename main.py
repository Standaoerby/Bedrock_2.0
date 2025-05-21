from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from services.alarm_service import AlarmService
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from services.sensor_service import SensorService
from classes.marquee import MarqueeLabel
import os
import time
import json
import re
import threading
import traceback

# Import utility modules
from utils.logging_config import configure_logging
from utils.error_handler import ErrorHandler

# Initialize logging and error handling first
configure_logging()
ErrorHandler.init()

# Настройка и включение отладки
import logging
logger = logging.getLogger("BedrockApp")
logger.setLevel(logging.DEBUG)

# Вывод версии Python для отладки
import sys
logger.info(f"Python version: {sys.version}")
logger.info(f"Running on platform: {sys.platform}")

def is_raspbian():
    """Check if we're running on Raspberry Pi with Raspbian"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            if 'raspberry pi' in f.read().lower():
                return True
    except:
        pass
    
    try:
        # Check for specific ARM processor used by Raspberry Pi
        with open('/proc/cpuinfo', 'r') as f:
            if any(line.startswith('Hardware') and 'BCM' in line for line in f):
                return True
    except:
        pass
        
    return False

# Add specific configuration for Raspberry Pi
if is_raspbian():
    logger.info("Running on Raspberry Pi, applying specific optimizations")
    os.environ['GST_GL_API'] = 'gles2'  # Use GLES2 on Raspberry Pi
    os.environ['GST_GL_PLATFORM'] = 'egl'  # Use EGL on Raspberry Pi

# Initialize GStreamer for sound
try:
    # Инициализация GStreamer для звука
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst  # type: ignore
    Gst.init(None)
    logger.info("GStreamer initialized successfully")
except ImportError:
    logger.warning("GStreamer Python bindings not found. Sound may not work correctly.")
except Exception as e:
    logger.warning(f"Failed to initialize GStreamer: {e}")

# Отладочная информация о модулях
logger.info("Importing modules...")

# Создаем файл для логов критических ошибок
with open('bedrock_startup_log.txt', 'w') as log_file:
    log_file.write(f"Starting app at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"Python version: {sys.version}\n")
    log_file.write(f"Platform: {sys.platform}\n")

# Force more synchronous widget building on Pi
from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')
Config.set('kivy', 'log_level', 'debug')  # More detailed logging
Config.set('kivy', 'window_icon', '')  # Prevent icon issues
Config.set('kivy', 'build_force_sync', '1')  # Force sync widget building

# Configure environment variables - these work with the launch script
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Raspberry Pi specific settings - updated for better compatibility
if sys.platform.startswith('linux'):
    os.environ['KIVY_WINDOW'] = 'sdl2'  # Use SDL2 window provider
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'  # Try SDL2 GL backend instead of gl
    os.environ['KIVY_LOG_LEVEL'] = 'debug'
    # Give window manager more time to initialize
    os.environ['KIVY_WAIT_FOR_WINDOW'] = '1'
    # Set GL pipeline to reduce memory usage
    os.environ['KIVY_GL_PIPELINE'] = 'sdl2'
    # Use GStreamer for audio
    os.environ['KIVY_AUDIO'] = 'gstplayer'

# Import Config BEFORE anything creates a Window 
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '0')
Config.set('graphics', 'borderless', '0')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'window_state', 'visible')
Config.set('graphics', 'resizable', '0')    
Config.set('graphics', 'show_cursor', '0')

# Fix for 'No section: audio' error
try:
    # Make sure the audio section exists before setting values
    Config.adddefaultsection('audio')
    Config.set('audio', 'enable_mpg123', '0')  # Disable non-GStreamer backends
    Config.set('audio', 'enable_ffpyplayer', '0')  # Disable non-GStreamer backends
    Config.set('audio', 'gstplayer_rpi_fix', '1')  # Enable Raspberry Pi fix for GStreamer
except Exception as e:
    logger.warning(f"Could not configure audio settings: {e}")

# Register font
logger.info("Registering fonts...")
try:
    LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
    logger.info("Font registered successfully")
except Exception as e:
    logger.error(f"Error registering font: {e}")
    with open('bedrock_startup_log.txt', 'a') as log_file:
        log_file.write(f"Font registration error: {e}\n")
        log_file.write(traceback.format_exc())

# Import screens after font registration
logger.info("Importing screens...")
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
        log_file.write(traceback.format_exc())

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

# Отловим возможную ошибку импорта kivymd перед классом BedrockApp
try:
    from kivymd.app import MDApp
    logger.info("MDApp imported successfully")
except Exception as e:
    logger.error(f"Error importing MDApp: {e}")
    with open('bedrock_startup_log.txt', 'a') as log_file:
        log_file.write(f"KivyMD import error: {e}\n")
        log_file.write(traceback.format_exc())

class BedrockApp(MDApp):
    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)
    
    # Fixed scaling parameters - no platform detection
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

    def __init__(self, **kwargs):
        # Initialize services to None to avoid attribute errors
        self.alarm_service = None
        self.weather_service = None  
        self.schedule_service = None
        self.pigs_service = None
        self.notification_service = None
        self.sensor_service = None
        self._init_sensor_thread = None
        
        # Initialize theme_config BEFORE parent init to ensure it's available for KV loading
        self.theme_name = "minecraft"
        self.theme_mode = "light"
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
        
        # Initialize empty sounds dict and sound state
        self.sounds = {}
        self.last_sound_time = 0
        self.last_sound_name = ""
        
        # Call parent init after our initializations
        super(BedrockApp, self).__init__(**kwargs)

    def build(self):
        logger.info("Building app...")
        
        # Ensure directories exist
        self.ensure_directories()
        logger.info("Directories checked")
        
        # Check GStreamer availability
        self.check_gstreamer()
        
        # Theme is already loaded in __init__
        logger.info("Theme already loaded")
        
        # Initialize sound system
        try:
            self.load_sounds()
            logger.info("Sounds loaded successfully")
        except Exception as e:
            logger.error(f"Error loading sounds: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"Sound loading error: {e}\n")
                log_file.write(traceback.format_exc())
        
        # Initialize services in отдельных потоках чтобы не блокировать UI
        logger.info("Initializing services...")
        try:
            self.alarm_service = AlarmService()
            self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)  # Camden, London coordinates
            self.schedule_service = ScheduleService()
            self.pigs_service = PigsService()
            self.notification_service = NotificationService()
            
            # Инициализируем датчики в отдельном потоке
            self.sensor_service = SensorService()
            self._init_sensor_thread = threading.Thread(target=self._init_sensors_async, daemon=True)
            self._init_sensor_thread.start()
            logger.info("Services initialized")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"Service initialization error: {e}\n")
                log_file.write(traceback.format_exc())
        
        # Load the UI
        try:
            from kivy.core.window import Window
            logger.info("Setting window properties")
            Window.size = (1024, 600)
            Window.left = 0
            Window.top = 0
            logger.info(f"Window size set to: {Window.size}, position: ({Window.left}, {Window.top})")
            
            # Use the safe KV loader
            logger.info("Loading UI from KV file...")
            ui = safe_kv_load()
            
            # Add diagnostics to verify KV loading
            try:
                def _check_kv_loaded(dt):
                    print("===== KV DIAGNOSTICS =====")
                    try:
                        if hasattr(self.root, 'ids') and hasattr(self.root.ids, 'screen_manager'):
                            print(f"Main screen manager: {self.root.ids.screen_manager}")
                            for screen_name in ["home", "alarm", "schedule", "weather", "pigs", "settings"]:
                                try:
                                    screen = self.root.ids.screen_manager.get_screen(screen_name)
                                    print(f"{screen_name} screen: {screen}, ids: {list(screen.ids.keys()) if hasattr(screen, 'ids') else 'None'}")
                                except Exception as e:
                                    print(f"{screen_name} screen error: {e}")
                        else:
                            print(f"Root: {self.root}")
                            if hasattr(self.root, 'ids'):
                                print(f"Root IDs: {self.root.ids}")
                        print("========================")
                    except Exception as e:
                        print(f"Diagnostics error: {e}")
                        
                # Run diagnostics after a delay
                Clock.schedule_once(_check_kv_loaded, 1.0)
            except Exception as e:
                print(f"Failed to schedule diagnostics: {e}")
                
            return ui
        except Exception as e:
            logger.error(f"Error loading UI: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"UI loading error: {e}\n")
                log_file.write(traceback.format_exc())
            # Return a basic error UI
            from kivy.uix.label import Label
            return Label(text=f"Error loading UI:\n{str(e)}", font_size='24sp')

    def _init_sensors_async(self):
        """Initialize sensors in a background thread to avoid blocking UI"""
        try:
            logger.info("Starting sensor service in background thread...")
            if hasattr(self, 'sensor_service') and self.sensor_service:
                self.sensor_service.start()
                logger.info("Sensor service started successfully")
            else:
                logger.warning("Cannot start sensor service - not initialized")
        except Exception as e:
            logger.error(f"Error starting sensor service: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"Sensor service error: {e}\n")
                log_file.write(traceback.format_exc())

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
            "media/ringtones",
            "cache",
            "config",
            "pages",
            "utils",  # Added for utility modules
            "logs"    # Added for logs
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def check_gstreamer(self):
        """Check if GStreamer is available and working"""
        try:
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst  # type: ignore
            
            if not hasattr(gi.repository, 'Gst') or not Gst.is_initialized():
                logger.warning("GStreamer is not initialized, sound may not work correctly")
                return False
                    
            # Try to create a simple pipeline to verify GStreamer works
            pipeline_str = 'audiotestsrc num-buffers=1 ! audioconvert ! autoaudiosink'
            pipeline = Gst.parse_launch(pipeline_str)
            if not pipeline:
                logger.warning("Could not create GStreamer test pipeline")
                return False
                    
            logger.info("GStreamer is available and working")
            return True
        except Exception as e:
            logger.warning(f"GStreamer check failed: {e}")
            return False
    
    def load_sounds(self):
        """Load sound effects using GStreamer"""
        sound_files = {
            "click": ["assets/sounds/click.ogg"],
            "success": ["assets/sounds/success.ogg"],
            "error": ["assets/sounds/error.ogg"]
        }
        
        try:
            # Try to load each sound
            for sound_name, paths in sound_files.items():
                # Try each path until one works
                for path in paths:
                    if os.path.exists(path):
                        try:
                            sound = SoundLoader.load(path)
                            if sound:
                                self.sounds[sound_name] = sound
                                logger.info(f"Loaded sound: {sound_name} from {path}")
                                break
                        except Exception as e:
                            logger.warning(f"Failed to load sound {sound_name} from {path}: {e}")
                
                if sound_name not in self.sounds:
                    logger.warning(f"Could not load sound: {sound_name}, no valid paths found")
            
            logger.info(f"Loaded {len(self.sounds)} sounds")
        except Exception as e:
            logger.error(f"Error in load_sounds: {e}")
            logger.error(traceback.format_exc())
    
    def play_sound(self, sound_name="click"):
        """Play a sound by name with simple debounce and recovery on errors"""
        current_time = time.time()
        
        # Debounce - avoid playing sounds too rapidly
        if sound_name == self.last_sound_name and (current_time - self.last_sound_time) < 0.05:
            return
            
        self.last_sound_time = current_time
        self.last_sound_name = sound_name
        
        # Play the sound if it's loaded
        if sound_name in self.sounds:
            try:
                # Create a new instance for each play to support concurrent sounds
                sound = self.sounds[sound_name]
                source = sound.source
                
                # For small UI sounds, try to just play the original if available
                if sound.state == 'stop':
                    sound.play()
                else:
                    # If original is playing, try to load and play a new instance
                    new_sound = SoundLoader.load(source)
                    if new_sound:
                        new_sound.play()
            except Exception as e:
                logger.warning(f"Error playing sound {sound_name}: {e}")
                
                # Try to reload the sound if error occurred
                try:
                    # Reload sound
                    if os.path.exists(self.sounds[sound_name].source):
                        self.sounds[sound_name] = SoundLoader.load(self.sounds[sound_name].source)
                        logger.info(f"Reloaded sound: {sound_name}")
                except:
                    pass
        else:
            logger.debug(f"Sound not found: {sound_name}")

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        logger.info("App starting...")
        try:
            if hasattr(self, 'root') and hasattr(self.root, 'ids') and hasattr(self.root.ids, 'screen_manager'):
                self.root.ids.screen_manager.bind(current=self._update_current_screen)
                logger.info("Screen manager bound successfully")
            else:
                logger.warning("Could not bind screen manager - not found")
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"on_start error: {e}\n")
                log_file.write(traceback.format_exc())
        
    def on_stop(self):
        """Clean up when the application exits"""
        logger.info("App stopping...")
        if hasattr(self, 'sensor_service') and self.sensor_service:
            try:
                self.sensor_service.stop()
                logger.info("Sensor service stopped")
            except Exception as e:
                logger.error(f"Error stopping sensor service: {e}")
                
        # Cleanup sounds
        try:
            for sound_name, sound in self.sounds.items():
                try:
                    if sound and sound.state != 'stop':
                        sound.stop()
                except:
                    pass
            self.sounds.clear()
        except Exception as e:
            logger.error(f"Error cleaning up sounds: {e}")

    def _update_current_screen(self, instance, value):
        self.current_screen = value
        logger.info(f"Screen changed to {value}")
        
        if not self.menu_navigation:
            self.play_sound("success")
            
        self.menu_navigation = False

if __name__ == "__main__":
    logger.info("Starting Bedrock App...")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Error running app: {e}")
        with open('bedrock_startup_log.txt', 'a') as log_file:
            log_file.write(f"Fatal error running app: {e}\n")
            log_file.write(traceback.format_exc())