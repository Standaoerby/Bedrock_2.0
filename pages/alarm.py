import os
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.core.audio import SoundLoader

from classes.base_screen import BaseScreen


DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class AlarmScreen(BaseScreen):
    page_key = StringProperty("alarm")

    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("morning.mp3")
    ringtone_list = ListProperty([])
    alarm_fadein = BooleanProperty(False)
    current_sound = ObjectProperty(None, allownone=True)

    # ── Lifecycle ─────────────────────────────────────────────────────
    def do_on_pre_enter(self):
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    def do_on_leave(self):
        self.stop_ringtone()
        if "play_button" in self.ids:
            self.ids.play_button.state = "normal"
            self.ids.play_button.text = "Play"

    # ── State load/save ───────────────────────────────────────────────
    def load_ringtones(self):
        folder = "media/ringtones"
        if os.path.isdir(folder):
            self.ringtone_list = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith((".mp3", ".wav", ".ogg"))
            )
            if self.selected_ringtone not in self.ringtone_list and self.ringtone_list:
                self.selected_ringtone = self.ringtone_list[0]
        else:
            self.ringtone_list = ["morning.mp3", "robot.mp3"]

    def load_alarm_config(self):
        alarm = self.get_app().alarm_service.get_alarm()
        if not alarm:
            return
        self.alarm_time = alarm.get("time", "07:30")
        self.alarm_active = alarm.get("enabled", True)
        repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
        # Tolerate legacy int format
        if repeat and all(isinstance(x, int) for x in repeat):
            self.alarm_repeat = [DAYS_EN[i - 1] for i in repeat if 1 <= i <= 7]
        else:
            self.alarm_repeat = list(repeat)
        self.selected_ringtone = alarm.get("ringtone", self.selected_ringtone)
        self.alarm_fadein = alarm.get("fadein", False)

    def save_alarm(self):
        app = self.get_app()
        app.play_sound("success")
        app.alarm_service.set_alarm({
            "time": self.alarm_time,
            "enabled": self.alarm_active,
            "repeat": list(self.alarm_repeat),
            "ringtone": self.selected_ringtone,
            "fadein": self.alarm_fadein,
        })
        self.update_ui()

    def update_ui(self):
        h, m = self.alarm_time.split(":")
        if "hour_label" in self.ids:
            self.ids.hour_label.text = h
        if "minute_label" in self.ids:
            self.ids.minute_label.text = m
        if "active_checkbox" in self.ids:
            self.ids.active_checkbox.active = self.alarm_active
        for day in DAYS_EN:
            btn_id = f"repeat_{day.lower()}"
            if btn_id in self.ids:
                self.ids[btn_id].state = "down" if day in self.alarm_repeat else "normal"
        if "ringtone_spinner" in self.ids:
            self.ids.ringtone_spinner.text = self.selected_ringtone
        if "fadein_checkbox" in self.ids:
            self.ids.fadein_checkbox.active = self.alarm_fadein
        if "play_button" in self.ids:
            self.ids.play_button.state = "normal"
            self.ids.play_button.text = "Play"

    # ── Time +/- ──────────────────────────────────────────────────────
    def increment_hour(self):
        h, m = self.alarm_time.split(":")
        h = (int(h) + 1) % 24
        self.alarm_time = f"{h:02d}:{m}"
        self.update_ui()

    def decrement_hour(self):
        h, m = self.alarm_time.split(":")
        h = (int(h) - 1) % 24
        self.alarm_time = f"{h:02d}:{m}"
        self.update_ui()

    def increment_minute(self):
        h, m = self.alarm_time.split(":")
        m = (int(m) + 1) % 60
        self.alarm_time = f"{h}:{m:02d}"
        self.update_ui()

    def decrement_minute(self):
        h, m = self.alarm_time.split(":")
        m = (int(m) - 1) % 60
        self.alarm_time = f"{h}:{m:02d}"
        self.update_ui()

    # ── Toggles ───────────────────────────────────────────────────────
    def on_active_toggled(self, active):
        self.alarm_active = active

    def on_fadein_toggled(self, active):
        self.alarm_fadein = active

    def toggle_repeat(self, day, state):
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)

    # ── Ringtone preview ──────────────────────────────────────────────
    def select_ringtone(self, name):
        self.selected_ringtone = name
        self.stop_ringtone()
        if "play_button" in self.ids:
            self.ids.play_button.state = "normal"
            self.ids.play_button.text = "Play"

    def toggle_play_ringtone(self, state):
        if state == "down":
            self.play_ringtone()
            if "play_button" in self.ids:
                self.ids.play_button.text = "Stop"
        else:
            self.stop_ringtone()
            if "play_button" in self.ids:
                self.ids.play_button.text = "Play"

    def play_ringtone(self):
        self.stop_ringtone()
        path = os.path.join("media/ringtones", self.selected_ringtone)
        if os.path.exists(path):
            self.current_sound = SoundLoader.load(path)
            if self.current_sound:
                self.current_sound.play()

    def stop_ringtone(self):
        if self.current_sound:
            try:
                self.current_sound.stop()
            except Exception:
                pass
            self.current_sound = None

    # ── Test (debug) ──────────────────────────────────────────────────
    def test_alarm(self):
        app = self.get_app()
        if hasattr(app, "alarm_clock"):
            alarm = app.alarm_service.get_alarm() or {}
            app.alarm_clock.trigger_alarm(
                alarm.get("ringtone", "morning.mp3"),
                alarm.get("fadein", False),
            )
            return True
        return False
