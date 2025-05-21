from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from services.alarm_service import AlarmService
from classes.alarm_clock import AlarmClock
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from services.sensor_service import SensorService
from services.sound_service import SoundService
from classes.marquee import MarqueeLabel
import os
import time
import json
import re
import threading
import traceback


# Настройка и включение отладки
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BedrockApp")
logger.setLevel(logging.DEBUG)

# Initialize pygame for sound support
try:
    import pygame
    
    # Try multiple initialization configurations
    pygame_available = False
    init_configs = [
        # Try default config first
        {"frequency": 44100, "size": -16, "channels": 2, "buffer": 4096},
        # Fallback configs with more compatible settings
        {"frequency": 44100, "size": 16, "channels": 2, "buffer": 1024},
        {"frequency": 48000, "size": -16, "channels": 1, "buffer": 1024},
        {"frequency": 22050, "size": -16, "channels": 1, "buffer": 512},
        # Minimal configuration as last resort
        {"frequency": 22050, "size": 8, "channels": 1, "buffer": 512},
        # Try with no parameters as final fallback
        {}
    ]
    
    # Try each configuration until one works
    init_error = None
    for config in init_configs:
        try:
            logger.info(f"Trying pygame.mixer.init with config: {config}")
            pygame.mixer.init(**config)
            pygame_available = True
            logger.info(f"Successfully initialized pygame mixer with config: {config}")
            break
        except Exception as e:
            init_error = e
            logger.warning(f"Failed to initialize pygame mixer with config {config}: {e}")
            # Try to quit mixer before trying another config
            try:
                pygame.mixer.quit()
            except:
                pass
    
    if not pygame_available:
        logger.error(f"All pygame mixer initialization attempts failed: {init_error}")
        print(f"WARNING: Could not initialize pygame mixer: {init_error}")
except ImportError:
    pygame_available = False
    print("WARNING: Pygame not available, sound will be disabled")
except Exception as e:
    pygame_available = False
    print(f"WARNING: Could not initialize pygame: {e}")

# Вывод версии Python для отладки
import sys
logger.info(f"Python version: {sys.version}")
logger.info(f"Running on platform: {sys.platform}")
logger.info(f"Pygame available: {pygame_available}")

# Отладочная информация о модулях
logger.info("Importing modules...")

# Создаем файл для логов критических ошибок
with open('bedrock_startup_log.txt', 'w') as log_file:
    log_file.write(f"Starting app at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"Python version: {sys.version}\n")
    log_file.write(f"Platform: {sys.platform}\n")
    log_file.write(f"Pygame available: {pygame_available}\n")

# Configure environment variables - these work with the launch script
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Raspberry Pi specific settings - use SDL2 rather than EGL for better compatibility
if sys.platform.startswith('linux'):
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['KIVY_LOG_LEVEL'] = 'debug'

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
    
# Импорт Config ПЕРЕД всем, что создает окно
from kivy.config import Config

# Настройка разрешения и отображения
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '0')
Config.set('graphics', 'borderless', '1')  # Включаем безрамочный режим
Config.set('graphics', 'fullscreen', '1')  # Включаем полноэкранный режим
Config.set('graphics', 'window_state', 'visible')
Config.set('graphics', 'resizable', '0')    
Config.set('graphics', 'show_cursor', '0')

# Отловим возможную ошибку импорта kivymd перед классом BedrockApp
try:
    from kivymd.app import MDApp
    logger.info("MDApp imported successfully")
except Exception as e:
    logger.error(f"Error importing MDApp: {e}")
    with open('bedrock_startup_log.txt', 'a') as log_file:
        log_file.write(f"KivyMD import error: {e}\n")
        log_file.write(traceback.format_exc())

# Define a PyGameSound class to wrap pygame.mixer.Sound
class PyGameSound:
    """A wrapper class for pygame.mixer.Sound to match SoundLoader API"""
    def __init__(self, source):
        self.source = source
        self._sound = None
        self._channel = None
        self._volume = 1.0
        self._loop = 0  # 0 = no loop, -1 = infinite loop
        self._state = 'stop'
        self.length = 1.0  # Default length in seconds
        
        # Try to load the sound
        if pygame_available:
            try:
                self._sound = pygame.mixer.Sound(source)
            except Exception as e:
                logger.error(f"Error loading sound {source}: {e}")
    
    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value):
        self._volume = max(0.0, min(1.0, value))
        if pygame_available and self._sound:
            try:
                self._sound.set_volume(self._volume)
            except Exception as e:
                logger.error(f"Error setting volume: {e}")
    
    @property
    def state(self):
        # Update state if playing on a channel
        if pygame_available and self._channel and hasattr(self._channel, 'get_busy'):
            try:
                if self._channel.get_busy():
                    self._state = 'playing'
                else:
                    self._state = 'stop'
            except Exception as e:
                logger.error(f"Error checking channel state: {e}")
                self._state = 'stop'
        else:
            self._state = 'stop'
        return self._state
    
    @property
    def loop(self):
        return self._loop
    
    @loop.setter
    def loop(self, value):
        self._loop = -1 if value else 0
    
    def play(self):
        if pygame_available and self._sound:
            try:
                # Play on a new channel - pygame gives us back the Channel object
                self._channel = self._sound.play(loops=self._loop)
                if self._channel and hasattr(self._channel, 'set_volume'):
                    self._channel.set_volume(self._volume)
                self._state = 'playing'
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
                self._state = 'stop'
    
    def stop(self):
        if pygame_available and self._channel and hasattr(self._channel, 'stop'):
            try:
                self._channel.stop()
                self._state = 'stop'
            except Exception as e:
                logger.error(f"Error stopping sound: {e}")

# A replacement for Kivy's SoundLoader that uses pygame
class PygameSoundLoader:
    """A replacement for Kivy's SoundLoader that uses pygame"""
    @staticmethod
    def load(filename):
        try:
            if not pygame_available:
                logger.warning("Pygame not available, cannot load sound")
                return None
                
            return PyGameSound(filename)
        except Exception as e:
            logger.error(f"Error loading sound {filename}: {e}")
            return None

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
        
        # Initialize sound service
        self.sound_service = SoundService()
        
        # Call parent init after our initializations
        super(BedrockApp, self).__init__(**kwargs)

    def build(self):
        logger.info("Building app...")
        
        # Ensure directories exist
        self.ensure_directories()
        logger.info("Directories checked")
        
        # Theme is already loaded in __init__
        logger.info("Theme already loaded")
        
        # Sound system already initialized in __init__
        logger.info("Sound system already initialized")
        
        # Initialize services in отдельных потоках чтобы не блокировать UI
        logger.info("Initializing services...")
        try:
            self.alarm_service = AlarmService()
            self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)  # Camden, London coordinates
            self.schedule_service = ScheduleService()
            self.pigs_service = PigsService()
            self.notification_service = NotificationService()
            
            # Инициализация AlarmClock
            self.alarm_clock = AlarmClock(self)
            
            # Инициализируем датчики в отдельном потоке
            self.sensor_service = SensorService()
            self._init_sensor_thread = threading.Thread(target=self._init_sensors_async, daemon=True)
            self._init_sensor_thread.start()
            logger.info("Services initialized")
            return safe_kv_load()
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"Service initialization error: {e}\n")
                log_file.write(traceback.format_exc())

    def _init_sensors_async(self):
        """Initialize sensors in a background thread to avoid blocking UI"""
        try:
            logger.info("Starting sensor service in background thread...")
            self.sensor_service.start()
            logger.info("Sensor service started successfully")
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
            "logs"  # Added for logging
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def load_sounds(self):
        """Load sound effects using pygame with enhanced error handling"""
        sound_files = {
            "click": ["assets/sounds/click.ogg", "assets/sounds/click.wav", "assets/sounds/click.mp3"],
            "success": ["assets/sounds/success.ogg", "assets/sounds/success.wav", "assets/sounds/success.mp3"],
            "error": ["assets/sounds/error.ogg", "assets/sounds/error.wav", "assets/sounds/error.mp3"]
        }
        
        # Ensure sound directories exist
        os.makedirs("assets/sounds", exist_ok=True)
        
        # Log sound directory status
        sound_dir = "assets/sounds"
        if not os.path.exists(sound_dir):
            logger.error(f"Sound directory {sound_dir} does not exist!")
        else:
            # List files in sound directory for debugging
            try:
                files = os.listdir(sound_dir)
                logger.info(f"Files in {sound_dir}: {files}")
            except Exception as e:
                logger.error(f"Error listing sound directory: {e}")
        
        if not pygame_available:
            logger.warning("Pygame not available, cannot load sounds")
            return
        
        try:
            # Try to load each sound
            for sound_name, paths in sound_files.items():
                # Try each path until one works
                loaded = False
                for path in paths:
                    abs_path = os.path.abspath(path)
                    if os.path.exists(path):
                        try:
                            logger.info(f"Attempting to load sound {sound_name} from {path}")
                            sound = PygameSoundLoader.load(path)
                            if sound and sound._sound:
                                self.sounds[sound_name] = sound
                                logger.info(f"Successfully loaded sound: {sound_name} from {path}")
                                loaded = True
                                break
                            else:
                                logger.warning(f"Sound loaded but not initialized correctly: {sound_name} from {path}")
                        except Exception as e:
                            logger.warning(f"Failed to load sound {sound_name} from {path}: {e}")
                    else:
                        logger.warning(f"Sound file not found: {path} (absolute: {abs_path})")
                
                if not loaded:
                    logger.warning(f"Could not load sound: {sound_name}, no valid paths found")
            
            logger.info(f"Loaded {len(self.sounds)} sounds")
            
            # Generate test sounds if no sound files were found
            if not self.sounds and pygame_available:
                logger.warning("No sounds were loaded. Generating test sounds.")
                self._generate_test_sounds()
                
        except Exception as e:
            logger.error(f"Error in load_sounds: {e}")
            logger.error(traceback.format_exc())
    
   
    def play_sound(self, sound_name="click"):
        """Переадресация к sound_service"""
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
            logger.info("Screen manager bound successfully")
        except Exception as e:
            logger.error(f"Error in on_start: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"on_start error: {e}\n")
                log_file.write(traceback.format_exc())
        
    def on_stop(self):
        """Clean up when the application exits"""
        logger.info("App stopping...")
        if hasattr(self, 'sensor_service'):
            try:
                self.sensor_service.stop()
                logger.info("Sensor service stopped")
            except Exception as e:
                logger.error(f"Error stopping sensor service: {e}")
                
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

if __name__ == "__main__":
    logger.info("Starting Bedrock App...")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Error running app: {e}")
        with open('bedrock_startup_log.txt', 'a') as log_file:
            log_file.write(f"Fatal error running app: {e}\n")
            log_file.write(traceback.format_exc())