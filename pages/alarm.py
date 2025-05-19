from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
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
    current_sound = ObjectProperty(None, allownone=True)  # Store the sound object

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
            # If folder doesn't exist, use test values
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
        # Play success sound when saving
        app.play_sound("success")
        
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
        # Update hours and minutes
        hours, minutes = self.alarm_time.split(':')
        self.ids.hour_label.text = hours
        self.ids.minute_label.text = minutes
        
        # Update other UI elements
        self.ids.active_checkbox.active = self.alarm_active
        
        for day in DAYS_EN:
            btn_id = f"repeat_{day.lower()}"
            if btn_id in self.ids:
                self.ids[btn_id].state = "down" if day in self.alarm_repeat else "normal"
        
        if hasattr(self.ids, 'ringtone_spinner'):
            self.ids.ringtone_spinner.text = self.selected_ringtone
        
        if hasattr(self.ids, 'fadein_checkbox'):
            self.ids.fadein_checkbox.active = self.alarm_fadein
        
        # Reset play button state
        if hasattr(self.ids, 'play_button'):
            self.ids.play_button.state = 'normal'
            self.ids.play_button.text = 'Play'

    def increment_hour(self):
        # Play sound (already added in kv file)
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) + 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        self.ids.hour_label.text = f"{new_hour:02d}"

    def decrement_hour(self):
        # Play sound (already added in kv file)
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) - 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        self.ids.hour_label.text = f"{new_hour:02d}"

    def increment_minute(self):
        # Play sound (already added in kv file)
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) + 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        self.ids.minute_label.text = f"{new_minute:02d}"

    def decrement_minute(self):
        # Play sound (already added in kv file)
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) - 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        self.ids.minute_label.text = f"{new_minute:02d}"

    def on_active_toggled(self, active):
        # Play sound (already added in kv file)
        self.alarm_active = active

    def toggle_repeat(self, day, state):
        # Play sound (already added in kv file)
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)

    def select_ringtone(self, name):
        # Play sound (already added in kv file)
        self.selected_ringtone = name
        # Stop any playing sound when ringtone is changed
        self.stop_ringtone()
        # Reset play button
        if hasattr(self.ids, 'play_button'):
            self.ids.play_button.state = 'normal'
            self.ids.play_button.text = 'Play'

    def toggle_play_ringtone(self, state):
        """Toggle between play and stop based on button state"""
        app = self.get_app()
        app.play_sound("click")  # Play UI sound
        
        if state == 'down':
            self.play_ringtone()
            self.ids.play_button.text = 'Stop'
        else:
            self.stop_ringtone()
            self.ids.play_button.text = 'Play'

    def play_ringtone(self):
        """Play the selected ringtone"""
        from kivy.core.audio import SoundLoader
        
        # Stop any currently playing sound
        self.stop_ringtone()
        
        folder = "media/ringtones"
        path = os.path.join(folder, self.selected_ringtone)
        if os.path.exists(path):
            self.current_sound = SoundLoader.load(path)
            if self.current_sound:
                self.current_sound.play()

    def stop_ringtone(self):
        """Stop the currently playing ringtone"""
        if self.current_sound:
            self.current_sound.stop()
            self.current_sound = None

    def on_fadein_toggled(self, active):
        # Play sound (already added in kv file)
        self.alarm_fadein = active

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
        
    def on_leave(self):
        """Clean up when leaving the screen"""
        self.stop_ringtone()
        if hasattr(self.ids, 'play_button'):
            self.ids.play_button.state = 'normal'
            self.ids.play_button.text = 'Play'
            
    def test_alarm(self):
        """Test the alarm by triggering it immediately (for debugging)"""
        app = self.get_app()
        app.play_sound("click")  # Play UI sound
        
        if hasattr(app, 'alarm_clock'):
            # Get current alarm settings
            alarm = app.alarm_service.get_alarm()
            ringtone = alarm.get("ringtone", "morning.mp3")
            fadein = alarm.get("fadein", False)
            
            # Trigger the alarm with current settings
            app.alarm_clock.trigger_alarm(ringtone, fadein)
            return True
        return False