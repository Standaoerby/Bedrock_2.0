import json
import os

from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp

# Регистрируем кастомный шрифт
LabelBase.register(
    name="Minecraftia",
    fn_regular="assets/fonts/Minecraftia-Regular.ttf"
)

# Импорт экранов
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
            "font_name": "Minecraftia"
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class BedrockApp(MDApp):
    def build(self):
        self.theme_name = "minecraft"
        self.theme_mode = "light"
        self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
        return Builder.load_file('main.kv')

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

if __name__ == "__main__":
    BedrockApp().run()
