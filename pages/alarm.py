from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
import os
import re
import logging
import traceback

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
        # Убедимся, что нет активного звука с предыдущего использования экрана
        self.stop_ringtone()
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    def load_ringtones(self):
        folder = "media/ringtones"
        if os.path.exists(folder):
            try:
                # Поддерживаем форматы, которые поддерживает pygame
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
            # If folder doesn't exist, create it and use test values
            try:
                os.makedirs(folder, exist_ok=True)
                logger.info(f"Created ringtones folder: {folder}")
            except Exception as e:
                logger.error(f"Failed to create ringtones folder: {e}")
            
            self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]

    def load_alarm_config(self):
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            try:
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
            except Exception as e:
                logger.error(f"Error processing alarm config: {e}")

    def save_alarm(self):
        app = self.get_app()
        try:
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
        except Exception as e:
            logger.error(f"Error saving alarm: {e}")
            app.play_sound("error")

    def update_ui(self):
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
        
        # Update fadein button (replacing checkbox)
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
        # Play sound for feedback
        app = self.get_app()
        # The click sound is already played by the button's on_press event
        # Only play success sound when turning ON
        if active and not self.alarm_active:
            app.play_sound("success")
        
        self.alarm_active = active
        self.update_ui()

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
        """Play the selected ringtone using pygame directly"""
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
                
            # Use pygame with better error handling
            try:
                import pygame
                # Check if mixer is initialized
                if not pygame.mixer.get_init():
                    logger.info("Pygame mixer not initialized, initializing...")
                    
                    # Try different configurations for initialization
                    init_configs = [
                        # Try default config first
                        {"frequency": 44100, "size": -16, "channels": 2, "buffer": 512},
                        # Fallback configs with more compatible settings
                        {"frequency": 44100, "size": 16, "channels": 2, "buffer": 1024},
                        {"frequency": 48000, "size": -16, "channels": 1, "buffer": 1024},
                        {"frequency": 22050, "size": -16, "channels": 1, "buffer": 512},
                        # Minimal configuration as last resort
                        {"frequency": 22050, "size": 8, "channels": 1, "buffer": 512},
                        # Try with no parameters as final fallback
                        {}
                    ]
                    
                    # Try each configuration until one works
                    for config in init_configs:
                        try:
                            logger.info(f"Trying pygame.mixer.init with config: {config}")
                            pygame.mixer.init(**config)
                            logger.info(f"Successfully initialized pygame mixer with config: {config}")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to initialize pygame mixer with config {config}: {e}")
                            # Try to quit mixer before trying another config
                            try:
                                pygame.mixer.quit()
                            except:
                                pass
                
                # Check if mixer was successfully initialized
                if pygame.mixer.get_init():
                    # Create and play sound
                    self.current_sound = pygame.mixer.Sound(path)
                    self.current_sound.play()
                    logger.info(f"Playing ringtone preview with pygame: {path}")
                else:
                    logger.error("Failed to initialize pygame mixer after multiple attempts")
                    # Fall back to app sound
                    app = self.get_app()
                    app.play_sound("success")
            except Exception as pygame_error:
                logger.error(f"Pygame error: {pygame_error}")
                # If error with pygame, use app method
                app = self.get_app()
                app.play_sound("success")  # Play standard sound

        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            logger.error(traceback.format_exc())
            # Reset button state on error
            if hasattr(self.ids, 'play_button'):
                self.ids.play_button.state = 'normal'
                self.ids.play_button.text = 'Play'

    def stop_ringtone(self):
        """Stop the currently playing ringtone"""
        try:
            if self.current_sound:
                try:
                    # Стандартный способ остановки звука pygame
                    if hasattr(self.current_sound, 'stop'):
                        self.current_sound.stop()
                except Exception as e:
                    logger.warning(f"Error with standard stop: {e}")
                    # Запасной вариант - остановить все каналы
                    try:
                        import pygame
                        if pygame.mixer.get_init():
                            pygame.mixer.stop()
                    except Exception as e2:
                        logger.error(f"Failed to stop mixer: {e2}")
                
                # Очищаем ссылку на звук
                self.current_sound = None
                logger.info("Stopped ringtone preview")
        except Exception as e:
            logger.error(f"Error stopping ringtone: {e}")
            self.current_sound = None

    def on_fadein_toggled(self, active):
        # Now handles the ON/OFF button toggle instead of checkbox
        app = self.get_app()
        
        # Play success sound when turning ON
        if active and not self.alarm_fadein:
            app.play_sound("success")
        
        self.alarm_fadein = active
        self.update_ui()

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
        
    def on_leave(self):
        """Clean up when leaving the screen"""
        # Остановить любой воспроизводимый звук при уходе с экрана
        self.stop_ringtone()
        # Сбросить состояние кнопки воспроизведения
        if hasattr(self.ids, 'play_button'):
            self.ids.play_button.state = 'normal'
            self.ids.play_button.text = 'Play'
        logger.info("Leaving alarm screen, resources cleaned up")
            
    def test_alarm(self):
        """Test the alarm by triggering it immediately (for debugging)"""
        app = self.get_app()
        app.play_sound("click")  # Play UI sound
        
        if hasattr(app, 'alarm_clock'):
            try:
                # Get current alarm settings
                alarm = app.alarm_service.get_alarm()
                ringtone = alarm.get("ringtone", "morning.mp3")
                fadein = alarm.get("fadein", False)
                
                # Trigger the alarm with current settings
                app.alarm_clock.trigger_alarm(ringtone, fadein)
                logger.info(f"Testing alarm with ringtone: {ringtone}, fadein: {fadein}")
                return True
            except Exception as e:
                logger.error(f"Error testing alarm: {e}")
        
        return False