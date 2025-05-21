from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
import os
import logging
from utils.error_handler import ErrorHandler

logger = logging.getLogger("AlarmScreen")

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
        # Ensure no active sound from previous screen usage
        self.stop_ringtone()
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    @ErrorHandler.handle_exception
    def load_ringtones(self):
        """Load available ringtones from media directory"""
        folder = "media/ringtones"
        if os.path.exists(folder):
            try:
                # Support formats that pygame supports
                self.ringtone_list = [f for f in os.listdir(folder) 
                    if f.lower().endswith((".mp3", ".ogg", ".wav"))]
                if self.selected_ringtone not in self.ringtone_list and self.ringtone_list:
                    self.selected_ringtone = self.ringtone_list[0]
                logger.info(f"Loaded {len(self.ringtone_list)} ringtones from {folder}")
            except Exception as e:
                logger.error(f"Error loading ringtones: {e}")
                # Fallback to defaults
                self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]
        else:
            # If folder doesn't exist, create it and use defaults
            try:
                os.makedirs(folder, exist_ok=True)
                logger.info(f"Created ringtones folder: {folder}")
            except Exception as e:
                logger.error(f"Failed to create ringtones folder: {e}")
            
            self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]

    @ErrorHandler.handle_exception
    def load_alarm_config(self):
        """Load alarm configuration from service"""
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.alarm_time = alarm.get("time", "07:30")
            self.alarm_active = alarm.get("enabled", True)
            repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
            
            # Handle numeric day format (compatibility with older configs)
            if repeat and all(isinstance(x, int) for x in repeat):
                days_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                self.alarm_repeat = [days_map[i-1] for i in repeat if 1 <= i <= 7]
            else:
                self.alarm_repeat = repeat
                
            self.selected_ringtone = alarm.get("ringtone", self.selected_ringtone)
            self.alarm_fadein = alarm.get("fadein", False)
            logger.info(f"Loaded alarm config: {alarm}")

    @ErrorHandler.handle_exception
    def save_alarm(self):
        """Save alarm settings to service"""
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
        logger.info(f"Saved alarm config: {alarm}")
        self.update_ui()

    def update_ui(self):
        """Update UI elements to match current settings"""
        # Update hours and minutes
        hours, minutes = self.alarm_time.split(':')
        self.ids.hour_label.text = hours
        self.ids.minute_label.text = minutes
        
        # Update the active button
        if hasattr(self.ids, 'active_button'):
            self.ids.active_button.text = "ON" if self.alarm_active else "OFF"
            # Update color based on state
            app = self.get_app()
            if self.alarm_active:
                self.ids.active_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
            else:
                self.ids.active_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
        
        # Update fadein button
        if hasattr(self.ids, 'fadein_button'):
            self.ids.fadein_button.text = "ON" if self.alarm_fadein else "OFF"
            # Update color based on state
            app = self.get_app()
            if self.alarm_fadein:
                self.ids.fadein_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
            else:
                self.ids.fadein_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
        
        # Update day buttons
        for day in DAYS_EN:
            btn_id = f"repeat_{day.lower()}"
            if btn_id in self.ids:
                self.ids[btn_id].state = "down" if day in self.alarm_repeat else "normal"
        
        if hasattr(self.ids, 'ringtone_spinner'):
            self.ids.ringtone_spinner.text = self.selected_ringtone
        
        # Reset play button state
        if hasattr(self.ids, 'play_button'):
            self.ids.play_button.state = 'normal'
            self.ids.play_button.text = 'Play'

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
        """Handle active button toggle"""
        app = self.get_app()
        # Only play success sound when turning ON
        if active and not self.alarm_active:
            app.play_sound("success")
        
        self.alarm_active = active
        self.update_ui()

    def toggle_repeat(self, day, state):
        """Toggle day in repeat list based on button state"""
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)

    def select_ringtone(self, name):
        """Select ringtone by name"""
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

    @ErrorHandler.handle_exception
    def play_ringtone(self):
        """Play the selected ringtone"""
        # Stop any currently playing sound
        self.stop_ringtone()
        
        try:
            folder = "media/ringtones"
            path = os.path.join(folder, self.selected_ringtone)
            
            if not os.path.exists(path):
                logger.warning(f"Ringtone file not found: {path}")
                # If file not found, play standard sound
                app = self.get_app()
                app.play_sound("click")
                return
                
            # Use app's sound service
            app = self.get_app()
            self.current_sound = app.sound_service.load_sound_file(path)
            
            if self.current_sound:
                self.current_sound.play()
                logger.info(f"Playing ringtone preview: {path}")

        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            if hasattr(self.ids, 'play_button'):
                self.ids.play_button.state = 'normal'
                self.ids.play_button.text = 'Play'

    @ErrorHandler.handle_exception
    def stop_ringtone(self):
        """Stop the currently playing ringtone"""
        try:
            if self.current_sound:
                if hasattr(self.current_sound, 'stop'):
                    self.current_sound.stop()
                self.current_sound = None
                logger.info("Stopped ringtone preview")
        except Exception as e:
            logger.error(f"Error stopping ringtone: {e}")
            self.current_sound = None

    def on_fadein_toggled(self, active):
        """Handle fade-in toggle button"""
        app = self.get_app()
        
        # Play success sound when turning ON
        if active and not self.alarm_fadein:
            app.play_sound("success")
        
        self.alarm_fadein = active
        self.update_ui()

    def get_app(self):
        """Get the running app instance"""
        from kivy.app import App
        return App.get_running_app()
        
    def on_leave(self):
        """Clean up when leaving the screen"""
        # Stop any playing sound
        self.stop_ringtone()
        # Reset play button state
        if hasattr(self.ids, 'play_button'):
            self.ids.play_button.state = 'normal'
            self.ids.play_button.text = 'Play'
        logger.info("Leaving alarm screen, resources cleaned up")