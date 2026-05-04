import os
import platform
import time
import json
import re

# ──────────────────────────────────────────────────────────────────
# Kivy graphics config MUST be set before kivy.core.window is imported.
# On Pi we want true fullscreen at the panel's native 1024x600;
# on Windows dev box leave it windowed so the IDE can be seen.
# ──────────────────────────────────────────────────────────────────
_IS_PI = platform.system() != 'Windows'

if _IS_PI:
    # Strip env that confuses SDL2 on Pi 5 with KMS/X11
    for _k in ['KIVY_BCM_DISPMANX_ID']:
        os.environ.pop(_k, None)

from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'fullscreen', '1' if _IS_PI else '0')
Config.set('graphics', 'borderless', '1' if _IS_PI else '0')
Config.set('graphics', 'show_cursor', '0' if _IS_PI else '1')
Config.set('graphics', 'resizable', '0')

from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from services.alarm_service import AlarmService
from services.alarm_clock import AlarmClock
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from services.sensor_service import SensorService
from classes.marquee import MarqueeLabel
from classes.themed import ThemedLabel, ThemedButton, ThemedPanel  # noqa: F401 — registers Factory classes
from kivy.core.audio import SoundLoader

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


def load_user_config(path="config/user.json"):
    """Best-effort read of persisted user prefs for startup."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

class BedrockApp(App):
    use_kivy_settings = False  # F1 must not open Kivy's built-in settings panel

    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)

    # Theme — DictProperty so KV bindings re-evaluate on switch
    theme_name = StringProperty("minecraft")
    theme_mode = StringProperty("light")
    theme_config = DictProperty({})

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
        self.title = "Bedrock 2.0"
        if _IS_PI:
            print("Running on Pi — using touchscreen scale (0.9)")
            self.ui_scale = 0.9
            self.font_scale = 0.85
            self.padding_scale = 0.8
        else:
            print("Running on Windows — using 1.0 scale for development")
            self.ui_scale = 1.0
            self.font_scale = 1.0
            self.padding_scale = 1.0

        self._update_ui_metrics()

        # Read persisted theme prefs so saved dark mode survives restart
        user_prefs = load_user_config()
        self.theme_name = user_prefs.get("theme", "minecraft")
        self.theme_mode = user_prefs.get("theme_mode", "light")
        self.theme_config = self.load_theme_config(self.theme_name, self.theme_mode)
        
        if self.is_raspberry_pi:
            # Обработка размеров шрифтов
            if "font_sizes" not in self.theme_config:
                self.theme_config["font_sizes"] = {}
                
            self.theme_config["font_sizes"]["small"] = "14sp"
            self.theme_config["font_sizes"]["medium"] = "16sp"
            self.theme_config["font_sizes"]["large"] = "20sp"
            self.theme_config["font_sizes"]["title"] = "24sp"
            
            # Обработка отступов - с проверкой типа
            if "padding" not in self.theme_config:
                self.theme_config["padding"] = {}
            elif isinstance(self.theme_config["padding"], str):
                # Если padding это строка, создаем новый словарь
                old_padding = self.theme_config["padding"]
                self.theme_config["padding"] = {
                    "default": old_padding,
                    "small": "4dp", 
                    "medium": "8dp", 
                    "large": "12dp"
                }
            else:
                # Если padding это словарь, добавляем в него значения
                self.theme_config["padding"]["small"] = "4dp"
                self.theme_config["padding"]["medium"] = "8dp"
                self.theme_config["padding"]["large"] = "12dp"
        
        # Initialize sound system
        self.sounds = {}
        self.last_sound_time = 0
        self.ensure_directories()
        self.load_sounds()
        
        # Initialize services. Location for weather comes from user prefs
        # (defaults to Camden, London) so the user can change it without
        # editing the source.
        self.alarm_service = AlarmService()
        wx_lat = float(user_prefs.get("lat", 51.5390))
        wx_lon = float(user_prefs.get("lon", -0.1426))
        self.weather_service = WeatherService(lat=wx_lat, lon=wx_lon)
        self.schedule_service = ScheduleService()
        self.pigs_service = PigsService()
        self.notification_service = NotificationService()
        self.sensor_service = SensorService()
        self.sensor_service.start()

        # Alarm clock — checks alarm.json every 30s and shows popup at fire time
        self.alarm_clock = AlarmClock(self)
        self.alarm_clock.start()

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
        """Ensure all required directories exist (silent)."""
        for d in ("assets/fonts", "assets/sounds", "assets/images",
                  "themes/minecraft/light", "media/ringtones",
                  "cache", "config", "pages"):
            os.makedirs(d, exist_ok=True)

    def load_sounds(self):
        """Load sound effects. Prefer .wav (universal Kivy support); fall back
        to .ogg if no .wav present."""
        sound_files = {
            "click":   ["assets/sounds/click.wav",   "assets/sounds/click.ogg"],
            "success": ["assets/sounds/success.wav", "assets/sounds/success.ogg"],
            "error":   ["assets/sounds/error.wav",   "assets/sounds/error.ogg"],
        }
        for name, paths in sound_files.items():
            for path in paths:
                if os.path.exists(path):
                    snd = SoundLoader.load(path)
                    if snd is not None:
                        self.sounds[name] = snd
                        break
            if name not in self.sounds:
                print(f"[bedrock] sound '{name}' not loaded; tried {paths}")
    
    def play_sound(self, sound_name="click"):
        """Play a cached sound with 50ms debounce. Reuses the same Sound
        instance — stops any in-flight playback first so rapid clicks
        retrigger correctly."""
        now = time.time()
        if (now - self.last_sound_time) < 0.05:
            return
        self.last_sound_time = now

        sound = self.sounds.get(sound_name)
        if sound is None:
            return
        try:
            if sound.state == "play":
                sound.stop()
            sound.play()
        except Exception as e:
            print(f"[bedrock] play_sound({sound_name}) failed: {e}")

    def load_theme_config(self, theme=None, mode=None):
        """Load a theme config; mirrors module-level loader so settings can call app.load_theme_config()."""
        return load_theme_config(theme or self.theme_name, mode or self.theme_mode)

    def apply_theme(self, theme=None, mode=None, persist=True):
        """Switch the live theme and trigger KV re-binding by reassigning the DictProperty."""
        new_theme = theme or self.theme_name
        new_mode = mode or self.theme_mode
        try:
            new_config = self.load_theme_config(new_theme, new_mode)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"apply_theme: failed to load {new_theme}/{new_mode}: {e}")
            return False

        self.theme_name = new_theme
        self.theme_mode = new_mode
        # DictProperty fires on identity change — reassign to a fresh dict
        self.theme_config = dict(new_config)

        if persist:
            self._persist_theme_choice()
        return True

    def _persist_theme_choice(self):
        """Write current theme_name/theme_mode back into config/user.json without clobbering other keys."""
        path = "config/user.json"
        prefs = load_user_config(path)
        prefs["theme"] = self.theme_name
        prefs["theme_mode"] = self.theme_mode
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"_persist_theme_choice: write failed: {e}")

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        self.root.ids.screen_manager.bind(current=self._update_current_screen)
        # F1..F6 cycle screens — handy for headless screenshot/debug via xdotool
        Window.bind(on_keyboard=self._dev_keyboard_shortcut)

    def _dev_keyboard_shortcut(self, _window, key, _scancode, _codepoint, _modifiers):
        keymap = {282: 'home', 283: 'alarm', 284: 'schedule',
                  285: 'weather', 286: 'pigs', 287: 'settings'}
        if key in keymap and self.root and 'screen_manager' in self.root.ids:
            self.root.ids.screen_manager.current = keymap[key]
            return True
        return False
        
    def on_stop(self):
        """Clean up when the application exits"""
        if hasattr(self, 'alarm_clock'):
            self.alarm_clock.stop()
        if hasattr(self, 'sensor_service'):
            self.sensor_service.stop()

    def _update_current_screen(self, instance, value):
        self.current_screen = value
        
        if not self.menu_navigation:
            self.play_sound("success")
            
        self.menu_navigation = False

if __name__ == "__main__":
    BedrockApp().run()