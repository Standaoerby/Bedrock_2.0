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
import platform
import time
import json
import re

# Configure environment variables for Raspberry Pi
# These will be modified for Windows in the build method
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_GRAPHICS'] = 'gles'
os.environ['KIVY_BCM_DISPMANX_ID'] = '0'
os.environ['KIVY_WINDOW'] = 'egl_rpi'
os.environ['KIVY_DPI'] = '96'
os.environ['KIVY_METRICS_DENSITY'] = '1'

LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.weather import WeatherScreen
from pages.schedule import ScheduleScreen
from pages.pigs import PigsScreen
from pages.settings import SettingsScreen

def load_theme_config(theme="minecraft", mode="light"):
    path = f"themes/{theme}/{mode}/theme.json"
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config
    
from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'show_cursor', '0')

class BedrockApp(MDApp):
    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)
    
    # Параметры масштабирования для различных платформ
    is_raspberry_pi = BooleanProperty(platform.system() != 'Windows')
    ui_scale = NumericProperty(1.0)
    font_scale = NumericProperty(1.0)
    padding_scale = NumericProperty(1.0)
    
    # Основные параметры размещения
    menu_height = NumericProperty(70)
    menu_padding = NumericProperty(10)
    content_padding = NumericProperty(15)
    
    # Общие значения для всех экранов
    ui_metrics = DictProperty({
        'menu_height': 70,
        'menu_padding': 10,
        'content_padding': 15,
        'widget_spacing': 10,
        'widget_height': 48,
        'small_widget_height': 36,
    })

    def build(self):
        # Применяем различные настройки для разных платформ
        if platform.system() == 'Windows':
            for key in ['KIVY_GL_BACKEND', 'KIVY_WINDOW', 'KIVY_GRAPHICS', 'KIVY_BCM_DISPMANX_ID']:
                if key in os.environ:
                    del os.environ[key]
            print("Running on Windows - adjusted environment settings")
            
            self.ui_scale = 1.0
            self.font_scale = 1.0
            self.padding_scale = 1.0
        else:
            print(f"Running on {platform.system()} - using Raspberry Pi settings")
            
            self.ui_scale = 0.9
            self.font_scale = 0.85
            self.padding_scale = 0.8
            
            Config.set('graphics', 'fullscreen', '1')

        self._update_ui_metrics()

        self.theme_name = "minecraft"
        self.theme_mode = "light"
        self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
        
        if self.is_raspberry_pi:
            if "font_sizes" not in self.theme_config:
                self.theme_config["font_sizes"] = {}
                
            self.theme_config["font_sizes"]["small"] = "14sp"
            self.theme_config["font_sizes"]["medium"] = "16sp"
            self.theme_config["font_sizes"]["large"] = "20sp"
            self.theme_config["font_sizes"]["title"] = "24sp"
            
            if "padding" not in self.theme_config:
                self.theme_config["padding"] = {}
                
            self.theme_config["padding"]["small"] = 4
            self.theme_config["padding"]["medium"] = 8
            self.theme_config["padding"]["large"] = 12
        
        # Initialize sound system
        self.sounds = {}
        self.last_sound_time = 0
        self.last_sound_name = ""
        self.ensure_directories()
        self.load_sounds()
        
        # Initialize services
        self.alarm_service = AlarmService()
        self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)
        self.schedule_service = ScheduleService()
        self.pigs_service = PigsService()
        self.notification_service = NotificationService()
        self.sensor_service = SensorService() 
        self.sensor_service.start()
        
        return Builder.load_file('main.kv')

    def _update_ui_metrics(self):
        """Обновляет метрики UI с учетом масштабирования"""
        self.ui_metrics = {
            'menu_height': int(70 * self.ui_scale),
            'menu_padding': int(10 * self.padding_scale),
            'content_padding': int(15 * self.padding_scale),
            'widget_spacing': int(10 * self.padding_scale),
            'widget_height': int(48 * self.ui_scale),
            'small_widget_height': int(36 * self.ui_scale),
        }
        
        self.menu_height = self.ui_metrics['menu_height']
        self.menu_padding = self.ui_metrics['menu_padding']
        self.content_padding = self.ui_metrics['content_padding']

    def scale_font(self, size):
        """Масштабирует размер шрифта в зависимости от платформы"""
        if isinstance(size, str):
            # Если размер шрифта задан строкой (например, "20sp")
            match = re.match(r'(\d+)(\w+)', size)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return f"{int(value * self.font_scale)}{unit}"
        # Если это число
        try:
            return f"{int(float(size) * self.font_scale)}sp"
        except (ValueError, TypeError):
            print(f"Warning: Could not scale font size: {size}, returning default")
            return "14sp"

    def scale_size(self, size):
        """Масштабирует размеры виджетов в зависимости от платформы"""
        if isinstance(size, (list, tuple)):
            return [self.scale_size(item) for item in size]
        
        if isinstance(size, str):
            # Если размер задан строкой (например, "48dp")
            match = re.match(r'(\d+)(\w+)', size)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return f"{int(value * self.ui_scale)}{unit}"
        
        # Если это число или что-то другое
        try:
            return int(float(size) * self.ui_scale)
        except (TypeError, ValueError):
            print(f"Warning: Could not scale size: {size}, returning as is")
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
            print(f"Ensured directory exists: {dir_path}")
    
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
                    print(f"Loaded sound: {name} from {path}")
                    break
            if name not in self.sounds:
                print(f"Warning: Sound '{name}' not found. Tried: {paths}")
    
    def play_sound(self, sound_name="click"):
        """Play a sound by name with simple debounce"""
        current_time = time.time()
        
        if (current_time - self.last_sound_time) < 0.05:
            return
            
        self.last_sound_time = current_time
        self.last_sound_name = sound_name
        
        sound = self.sounds.get(sound_name)
        if sound:
            sound_copy = SoundLoader.load(sound.source)
            if sound_copy:
                sound_copy.play()
                from kivy.clock import Clock
                Clock.schedule_once(
                    lambda dt: setattr(sound_copy, 'on_stop', lambda: None), 
                    sound.length + 0.1
                )

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        self.root.ids.screen_manager.bind(current=self._update_current_screen)
        
    def on_stop(self):
        """Clean up when the application exits"""
        if hasattr(self, 'sensor_service'):
            self.sensor_service.stop()

    def _update_current_screen(self, instance, value):
        self.current_screen = value
        
        if not self.menu_navigation:
            self.play_sound("success")
            
        self.menu_navigation = False

if __name__ == "__main__":
    BedrockApp().run()