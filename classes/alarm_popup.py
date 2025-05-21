from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
import os
import traceback
import logging

logger = logging.getLogger("AlarmPopup")

class AlarmPopup(ModalView):
    """Popup that shows when alarm goes off"""
    
    # Add property to track current volume
    current_volume = NumericProperty(0.0)
    
    def __init__(self, ringtone="morning.mp3", fadein=False, **kwargs):
        super(AlarmPopup, self).__init__(**kwargs)
        self.size_hint = (0.7, 0.5)  # 70% of screen width, 50% of height
        self.auto_dismiss = False  # Prevent dismissing by clicking outside
        self.background_color = [0, 0, 0, 0.9]  # Semi-transparent black background
        
        # Create layout
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Get app instance for theme configuration
        from kivy.app import App
        app = App.get_running_app()
        theme = app.theme_config
        font_name = theme.get("font_name", "Minecraftia")
        
        # Wake up label
        wake_up_label = Label(
            text="WAKE UP!",
            font_name=font_name,
            font_size=theme.get("font_sizes", {}).get("large", "28sp"),
            size_hint_y=0.7
        )
        
        # Turn off button
        turn_off_button = Button(
            text="Turn Off",
            font_name=font_name,
            font_size=theme.get("font_sizes", {}).get("large", "28sp"),
            size_hint=(0.5, 0.3),
            pos_hint={'center_x': 0.5}
        )
        turn_off_button.bind(on_release=self.stop_alarm)
        
        # Add widgets to layout
        layout.add_widget(wake_up_label)
        layout.add_widget(turn_off_button)
        
        # Add layout to popup
        self.add_widget(layout)
        
        # Audio properties
        self.sound = None
        self.sound_path = None
        self.ringtone = ringtone
        self.fadein = fadein
        self.current_volume = 0.0 if fadein else 1.0
        self.max_volume = 1.0
        self.fade_time = 30.0  # Seconds to fade from 0 to max volume
        self._fade_event = None
        
    def start_alarm(self):
        """Start playing the alarm sound"""
        folder = "media/ringtones"
        path = os.path.join(folder, self.ringtone)
        self.sound_path = path
        
        try:
            if not os.path.exists(path):
                logger.warning(f"Ringtone file not found: {path}")
                return
                
            self.sound = SoundLoader.load(path)
            if not self.sound:
                logger.warning(f"Failed to load ringtone: {path}")
                return
            
            # Set initial volume
            self.sound.volume = self.current_volume
            self.sound.loop = True  # Loop the sound until turned off
            
            # Start playing
            if self.sound.state != 'playing':
                self.sound.play()
                logger.info(f"Started alarm sound: {path}")
            
            # Start fade-in if enabled
            if self.fadein:
                self.start_fade_in()
                
        except Exception as e:
            logger.error(f"Error starting alarm: {e}")
            logger.error(traceback.format_exc())
    
    def start_fade_in(self):
        """Gradually increase volume"""
        # Cancel any existing fade event
        if self._fade_event:
            self._fade_event.cancel()
            self._fade_event = None
        
        # Configuration for smooth fading
        self.fade_step = 0.01  # Small increment
        interval = self.fade_time * self.fade_step  # Time between volume increases
        
        # Schedule incremental volume increase
        self._fade_event = Clock.schedule_interval(self._increase_volume, interval)
        logger.info(f"Started fade-in effect over {self.fade_time} seconds")
    
    def _increase_volume(self, dt):
        """Callback for incrementing volume"""
        if not self.sound:
            return False
            
        try:
            if self.current_volume < self.max_volume:
                # Increase volume by step
                self.current_volume += self.fade_step
                # Apply new volume to sound
                self.sound.volume = self.current_volume
                return True  # Continue the interval
            else:
                logger.info("Fade-in complete")
                return False  # Stop the interval
        except Exception as e:
            logger.error(f"Error in fade-in: {e}")
            return False  # Stop on error
    
    def stop_alarm(self, *args):
        """Stop the alarm and close the popup"""
        try:
            # Cancel any scheduled fade events
            if self._fade_event:
                self._fade_event.cancel()
                self._fade_event = None
            
            # Stop the sound
            if self.sound:
                if self.sound.state != 'stop':
                    self.sound.stop()
                self.sound = None
            
            logger.info("Alarm stopped")
        except Exception as e:
            logger.error(f"Error stopping alarm: {e}")
        finally:
            # Always dismiss the popup
            self.dismiss()
            
    def on_dismiss(self):
        """Ensure proper cleanup when popup is dismissed"""
        self.stop_alarm()
        return super(AlarmPopup, self).on_dismiss()