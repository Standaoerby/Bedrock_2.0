from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window

# фиксированное разрешение (для Windows-теста)
Window.size = (1024, 600)

class HomeScreen(Screen):
    pass

class BedrockApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        Builder.load_file("main.kv")
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        return sm

if __name__ == '__main__':
    BedrockApp().run()
