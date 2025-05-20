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

# Configure environment variables for Raspberry Pi
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'

# Register font
LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")

# Import screens after font registration
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
Config.set('graphics', 'fullscreen', '0')  # Set to '1' for Pi deployment
Config.set('graphics', 'show_cursor', '1')  # Set to '0' for Pi deployment

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
        # Ensure directories exist
        self.ensure_directories()
        
        # Load theme
        self.theme_name = "minecraft"
        self.theme_mode = "light"
        self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
        
        # Initialize sound system
        self.sounds = {}
        self.last_sound_time = 0
        self.last_sound_name = ""
        self.load_sounds()
        
        # Initialize services
        self.alarm_service = AlarmService()
        self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)  # Camden, London coordinates
        self.schedule_service = ScheduleService()
        self.pigs_service = PigsService()
        self.notification_service = NotificationService()
        self.sensor_service = SensorService() 
        self.sensor_service.start()
        
        return Builder.load_file('main.kv')

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
            print(f"Warning: Could not scale font size: {size}, returning default")
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