from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from services.alarm_service import AlarmService
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from services.sensor_service import SensorService
from classes.marquee import MarqueeLabel
from kivy.core.audio import SoundLoader
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

# Вывод версии Python для отладки
import sys
logger.info(f"Python version: {sys.version}")
logger.info(f"Running on platform: {sys.platform}")

# Отладочная информация о модулях
logger.info("Importing modules...")

# Создаем файл для логов критических ошибок
with open('bedrock_startup_log.txt', 'w') as log_file:
    log_file.write(f"Starting app at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"Python version: {sys.version}\n")
    log_file.write(f"Platform: {sys.platform}\n")

# Configure environment variables - these work with the launch script
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Пробуем другие настройки для Pi
if sys.platform.startswith('linux'):
    # На Raspberry Pi используем более совместимые настройки
    os.environ['KIVY_WINDOW'] = 'egl_rpi'
    os.environ['KIVY_GL_BACKEND'] = 'gl'
    # Можем попробовать включить вывод отладки Kivy
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
    
# Import Config BEFORE anything creates a Window 
from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')

# Отключим borderless на Pi для отладки
if sys.platform.startswith('linux'):
    Config.set('graphics', 'borderless', '0')
    Config.set('graphics', 'fullscreen', '0')  # Отключим полноэкранный режим для отладки
else:
    Config.set('graphics', 'borderless', '1')
    
Config.set('graphics', 'show_cursor', '0')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '0')

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

    def build(self):
        logger.info("Building app...")
        
        # Ensure directories exist
        self.ensure_directories()
        logger.info("Directories checked")
        
        # Load theme
        self.theme_name = "minecraft"
        self.theme_mode = "light"
        try:
            self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
            logger.info("Theme loaded")
        except Exception as e:
            logger.error(f"Error loading theme: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"Theme loading error: {e}\n")
                log_file.write(traceback.format_exc())
        
        # Initialize sound system
        try:
            self.sounds = {}
            self.last_sound_time = 0
            self.last_sound_name = ""
            self.load_sounds()
            logger.info("Sounds loaded")
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
            logger.info("Loading UI from KV file...")
            return Builder.load_file('main.kv')
        except Exception as e:
            logger.error(f"Error loading UI: {e}")
            with open('bedrock_startup_log.txt', 'a') as log_file:
                log_file.write(f"UI loading error: {e}\n")
                log_file.write(traceback.format_exc())
            return None

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
            "pages"
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def load_sounds(self):
        """Load sound effects"""
        sound_files = {
            "click": ["assets/sounds/click.ogg"],
            "success": ["assets/sounds/success.ogg"],
            "error": ["assets/sounds/error.ogg"]
        }
        
        for name, paths in sound_files.items():
            for path in paths:
                if os.path.exists(path):
                    self.sounds[name] = SoundLoader.load(path)
                    logger.info(f"Loaded sound: {name} from {path}")
                    break
            if name not in self.sounds:
                logger.warning(f"Sound '{name}' not found. Tried: {paths}")
    
    def play_sound(self, sound_name="click"):
        """Play a sound by name with simple debounce"""
        current_time = time.time()
        
        if (current_time - self.last_sound_time) < 0.05:
            return
            
        self.last_sound_time = current_time
        self.last_sound_name = sound_name
        
        sound = self.sounds.get(sound_name)
        if sound:
            try:
                sound_copy = SoundLoader.load(sound.source)
                if sound_copy:
                    sound_copy.play()
                    from kivy.clock import Clock
                    Clock.schedule_once(
                        lambda dt: setattr(sound_copy, 'on_stop', lambda: None), 
                        sound.length + 0.1
                    )
            except Exception as e:
                logger.error(f"Error playing sound: {e}")

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