from kivy.core.text import LabelBase
from kivy.app import App
from kivy.uix.label import Label

LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")

class TestApp(App):
    def build(self):
        return Label(
            text="ABC123 кириллица тест",
            font_name="Minecraftia",
            font_size=64
        )

if __name__ == '__main__':
    TestApp().run()
