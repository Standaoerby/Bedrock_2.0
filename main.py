from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty
from services.alarm_service import AlarmService
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from classes.marquee import MarqueeLabel
import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_GRAPHICS'] = 'gles'
os.environ['KIVY_BCM_DISPMANX_ID'] = '0'  # Использовать основной дисплей
# Отключить многосенсорность для лучшей производительности (если это простой сенсорный экран)
os.environ['KIVY_WINDOW'] = 'egl_rpi'

import json

LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.weather import WeatherScreen
from pages.schedule import ScheduleScreen
from pages.pigs import PigsScreen

def load_theme_config(theme="minecraft", mode="light"):
    path = f"themes/{theme}/{mode}/theme.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
from kivy.config import Config # Добавьте перед BedrockApp класса
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
# Отключение полноэкранного режима для разработки (включить для продакшн)
Config.set('graphics', 'fullscreen', '0')  # Измените на '1' для продакшн
# Скрыть курсор мыши на сенсорном экране
Config.set('graphics', 'show_cursor', '0')
class BedrockApp(MDApp):
    current_screen = StringProperty("home")

    def build(self):
        self.theme_name = "minecraft"
        self.theme_mode = "light"
        self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
        self.alarm_service = AlarmService()
        self.weather_service = WeatherService(lat=55.75, lon=37.62)
        self.schedule_service = ScheduleService()
        self.pigs_service = PigsService()
        self.notification_service = NotificationService()
        
        # Ensure the pages directory exists
        os.makedirs("pages", exist_ok=True)
        
        # Load main.kv which includes all the other KV files
        return Builder.load_file('main.kv')

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

    def on_start(self):
        self.root.ids.screen_manager.bind(current=self._update_current_screen)

    def _update_current_screen(self, instance, value):
        self.current_screen = value

if __name__ == "__main__":
    BedrockApp().run()