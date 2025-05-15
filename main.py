from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen  # <-- Важно!

class HomeScreen(MDScreen): pass
class AlarmScreen(MDScreen): pass
class ScheduleScreen(MDScreen): pass
class WeatherScreen(MDScreen): pass
class PigsScreen(MDScreen): pass
class SettingsScreen(MDScreen): pass

class BedrockApp(MDApp):
    def build(self):
        return Builder.load_file('main.kv')

if __name__ == "__main__":
    BedrockApp().run()
