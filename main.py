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

    is_raspberry_pi = BooleanProperty(_IS_PI)

    # ui_metrics kept as a DictProperty for backwards compat with screens
    # that haven't been rewritten yet (P5 migrates them off). Values come
    # from theme.json["layout"] now, no Pi-specific scaling.
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

        # Read persisted theme prefs so saved dark mode survives restart
        user_prefs = load_user_config()
        self.theme_name = user_prefs.get("theme", "minecraft")
        self.theme_mode = user_prefs.get("theme_mode", "light")
        self.theme_config = self.load_theme_config(self.theme_name, self.theme_mode)

        # Pull layout metrics from theme.json — no platform-specific
        # scaling, no in-place mutation of theme_config.
        layout = self.theme_config.get("layout", {})
        if layout:
            self.ui_metrics = {
                'menu_height':         layout.get("menu_height", 70),
                'menu_padding':        layout.get("menu_padding", 10),
                'content_padding':     layout.get("content_padding", 15),
                'widget_spacing':      layout.get("widget_spacing", 10),
                'widget_height':       layout.get("widget_height", 48),
                'small_widget_height': layout.get("small_widget_height", 36),
            }

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

    # scale_size / scale_font are kept as no-op identity functions for
    # backward compat with screens that still call them in KV — we drop
    # the scaling assumption entirely (designed natively for 1024x600,
    # use sp/dp consistently). P5 will remove these calls per-screen.
    def scale_size(self, size):
        return size

    def scale_font(self, size):
        if isinstance(size, str):
            return size
        try:
            return f"{int(size)}sp"
        except (TypeError, ValueError):
            return "14sp"

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