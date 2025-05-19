from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.audio import SoundLoader
from kivy.animation import Animation
from kivy.clock import Clock
import os

class AlarmPopup(ModalView):
    """Popup that shows when alarm goes off"""
    
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
        self.ringtone = ringtone
        self.fadein = fadein
        self.volume = 0.0 if fadein else 1.0
        self.max_volume = 1.0
        self.fade_time = 30.0  # Seconds to fade from 0 to max volume
        
    def start_alarm(self):
        """Start playing the alarm sound"""
        folder = "media/ringtones"
        path = os.path.join(folder, self.ringtone)
        
        if os.path.exists(path):
            self.sound = SoundLoader.load(path)
            if self.sound:
                # Set initial volume
                self.sound.volume = self.volume
                self.sound.loop = True  # Loop the sound until turned off
                self.sound.play()
                
                # Start fade-in if enabled
                if self.fadein:
                    self.start_fade_in()
    
    def start_fade_in(self):
        """Gradually increase volume"""
        self.fade_step = 0.01  # Small increment
        self.fade_interval = self.fade_time * self.fade_step  # Time between volume increases
        
        # Schedule incremental volume increase
        self._fade_event = Clock.schedule_interval(self._increase_volume, self.fade_interval)
    
    def _increase_volume(self, dt):
        """Callback for incrementing volume"""
        if self.sound and self.sound.volume < self.max_volume:
            self.sound.volume += self.fade_step
            return True  # Continue the interval
        else:
            return False  # Stop the interval
    
    def stop_alarm(self, *args):
        """Stop the alarm and close the popup"""
        # Cancel any scheduled fade events
        if hasattr(self, '_fade_event'):
            self._fade_event.cancel()
        
        # Stop the sound
        if self.sound:
            self.sound.stop()
            self.sound = None
        
        # Dismiss the popup
        self.dismiss()