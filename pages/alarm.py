from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
import os
import re

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class AlarmScreen(MDScreen):
    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("morning.mp3")
    ringtone_list = ListProperty([])
    alarm_fadein = BooleanProperty(False)
    is_playing = BooleanProperty(False)  # Добавить в класс AlarmScreen

    def toggle_play_ringtone(self):
        if self.is_playing:
            # Остановить воспроизведение...
            self.is_playing = False
        else:
            # Воспроизвести рингтон...
            self.is_playing = True

    def on_pre_enter(self):
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    def load_ringtones(self):
        folder = "media/ringtones"
        if os.path.exists(folder):
            self.ringtone_list = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]
            if self.selected_ringtone not in self.ringtone_list and self.ringtone_list:
                self.selected_ringtone = self.ringtone_list[0]
        else:
            # Если папка не существует, используем тестовые значения
            self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]

    def load_alarm_config(self):
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.alarm_time = alarm.get("time", "07:30")
            self.alarm_active = alarm.get("enabled", True)
            repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
            if repeat and all(isinstance(x, int) for x in repeat):
                days_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                self.alarm_repeat = [days_map[i-1] for i in repeat if 1 <= i <= 7]
            else:
                self.alarm_repeat = repeat
            self.selected_ringtone = alarm.get("ringtone", self.selected_ringtone)
            self.alarm_fadein = alarm.get("fadein", False)

    def save_alarm(self):
        app = self.get_app()
        alarm = {
            "time": self.alarm_time,
            "enabled": self.alarm_active,
            "repeat": self.alarm_repeat,
            "ringtone": self.selected_ringtone,
            "fadein": self.alarm_fadein,
        }
        app.alarm_service.set_alarm(alarm)
        self.update_ui()

    def update_ui(self):
        # Обновляем часы и минуты
        hours, minutes = self.alarm_time.split(':')
        self.ids.hour_label.text = hours
        self.ids.minute_label.text = minutes
        
        # Обновляем остальные элементы интерфейса
        self.ids.active_checkbox.active = self.alarm_active
        
        for day in DAYS_EN:
            btn = self.ids.get(f"repeat_{day.lower()}")
            if btn:
                btn.state = "down" if day in self.alarm_repeat else "normal"
        
        if hasattr(self.ids, 'ringtone_spinner'):
            self.ids.ringtone_spinner.text = self.selected_ringtone
        
        if hasattr(self.ids, 'fadein_checkbox'):
            self.ids.fadein_checkbox.active = self.alarm_fadein

    def increment_hour(self):
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) + 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        self.ids.hour_label.text = f"{new_hour:02d}"

    def decrement_hour(self):
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) - 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        self.ids.hour_label.text = f"{new_hour:02d}"

    def increment_minute(self):
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) + 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        self.ids.minute_label.text = f"{new_minute:02d}"

    def decrement_minute(self):
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) - 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        self.ids.minute_label.text = f"{new_minute:02d}"

    def on_active_toggled(self, active):
        self.alarm_active = active

    def toggle_repeat(self, day, state):
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)

    def select_ringtone(self, name):
        self.selected_ringtone = name

    def play_ringtone(self):
        from kivy.core.audio import SoundLoader
        folder = "media/ringtones"
        path = os.path.join(folder, self.selected_ringtone)
        if os.path.exists(path):
            sound = SoundLoader.load(path)
            if sound:
                sound.play()

    def on_fadein_toggled(self, active):
        self.alarm_fadein = active

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()