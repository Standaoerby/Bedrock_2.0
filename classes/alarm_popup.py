import os

from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock

from classes.audio_player import AudioPlayer

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
        
        # AudioPlayer abstracts away the Pi-vs-Windows backend split.
        # Fade-in: pw-play on Pi can't change the volume of a running
        # stream, so we kill+restart with a higher --volume each step.
        # That introduces a tiny audible gap at each step, but spread
        # over fade_time seconds it's barely noticeable, and skipping
        # fade-in altogether would be a regression on the Windows side
        # where Kivy SoundLoader supports live volume updates.
        self._player = AudioPlayer()
        self.ringtone = ringtone
        self.fadein = fadein
        self._volume = 0.0 if fadein else 1.0
        self._max_volume = 1.0
        self._fade_time = 30.0      # seconds to ramp 0 → max
        self._fade_step = 0.05      # +5% per tick
        self._fade_event = None

    def start_alarm(self):
        """Start playing the alarm sound (looping)."""
        path = os.path.join("media/ringtones", self.ringtone)
        if not self._player.play(path, loop=True, volume=self._volume):
            return
        if self.fadein:
            self._start_fade_in()

    def _start_fade_in(self):
        # Tick interval = total fade time / number of steps. With
        # _fade_step = 0.05 and _fade_time = 30, that's 1.5s per step.
        steps = self._max_volume / self._fade_step
        interval = self._fade_time / max(1, steps)
        self._fade_event = Clock.schedule_interval(self._tick_volume, interval)

    def _tick_volume(self, _dt):
        if self._volume >= self._max_volume:
            return False  # cancel the interval
        self._volume = min(self._max_volume, self._volume + self._fade_step)
        # Re-arm pw-play (Pi) / live-set volume (Kivy) by replaying.
        # AudioPlayer.play() stops the previous instance first.
        path = os.path.join("media/ringtones", self.ringtone)
        self._player.play(path, loop=True, volume=self._volume)
        return True

    def stop_alarm(self, *_):
        """Stop the alarm and dismiss the popup."""
        if self._fade_event is not None:
            self._fade_event.cancel()
            self._fade_event = None
        self._player.stop()
        self.dismiss()