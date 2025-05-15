from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.properties import StringProperty
from services.alarm_service import AlarmService
import json
import os

LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
from pages.home import HomeScreen
from pages.alarm import AlarmScreen

def load_theme_config(theme="minecraft", mode="light"):
    path = f"themes/{theme}/{mode}/theme.json"
    if not os.path.exists(path):
        return {
            "background_image": "",
            "overlay_images": {
                "home": "",
                "alarm": ""
            },
            "font_name": "Minecraftia",
            "menu_selected_color": [0, 0.7, 0, 1],
            "menu_unselected_color": [0, 0, 0, 1]
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class BedrockApp(MDApp):
    current_screen = StringProperty("home")

    def build(self):
        self.theme_name = "minecraft"
        self.theme_mode = "light"
        self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
        self.alarm_service = AlarmService()
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
