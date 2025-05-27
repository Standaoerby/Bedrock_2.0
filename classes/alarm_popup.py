from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, PushMatrix, PopMatrix, Rotate
from kivy.animation import Animation
from datetime import datetime
import os
import logging
from services.sound_service import PyGameSound
from utils.common import config_manager

logger = logging.getLogger("AlarmPopup")

class AlarmPopup(ModalView):
    """Beautiful popup that shows when alarm goes off"""
    
    # Add property to track current volume
    current_volume = NumericProperty(0.0)
    
    def __init__(self, ringtone="morning.mp3", fadein=False, **kwargs):
        super(AlarmPopup, self).__init__(**kwargs)
        
        # Size and position
        self.size_hint = (0.9, 0.7)  # Larger and more prominent
        self.auto_dismiss = False  # Prevent dismissing by clicking outside
        self.background_color = [0, 0, 0, 0]  # Transparent background for custom drawing
        
        # CRITICAL: Add dismissing flag to prevent recursion
        self._is_dismissing = False
        self._sound_stopped = False
        
        # Get user name from config
        self.username = self._get_username()
        
        # Get app instance for theme configuration
        from kivy.app import App
        app = App.get_running_app()
        self.theme = app.theme_config if app else {}
        self.font_name = self.theme.get("font_name", "Minecraftia")
        
        # Audio properties
        self.sound = None
        self.sound_path = None
        self.ringtone = ringtone
        self.fadein = fadein
        self.current_volume = 0.0 if fadein else 0.8  # Start at 80% if no fade-in
        self.max_volume = 0.8  # Maximum volume (not too loud)
        self.fade_time = 10.0  # Faster fade-in: 10 seconds instead of 30
        self._fade_event = None
        
        # Create the beautiful UI
        self._create_ui()
        
        logger.info(f"🚨 Beautiful AlarmPopup created for {self.username}, ringtone: {ringtone}, fadein: {fadein}")
    
    def _get_username(self):
        """Get username from user config"""
        try:
            user_config = config_manager.get_config('user')
            username = user_config.get('username', '').strip()
            
            if username:
                return username
            else:
                return "Sleepyhead"  # Friendly fallback
                
        except Exception as e:
            logger.warning(f"Could not get username: {e}")
            return "Sleepyhead"
    
    def _create_ui(self):
        """Create beautiful UI elements"""
        # Main container with custom background
        main_layout = BoxLayout(orientation='vertical', padding=[30, 40], spacing=30)
        
        # Custom background drawing
        with main_layout.canvas.before:
            # Gradient-like background effect
            Color(0.1, 0.1, 0.15, 0.95)  # Dark blue-gray
            self.bg_rect1 = RoundedRectangle(pos=main_layout.pos, size=main_layout.size, radius=[25])
            
            Color(0.8, 0.2, 0.2, 0.8)  # Red overlay for urgency
            self.bg_rect2 = RoundedRectangle(pos=main_layout.pos, size=main_layout.size, radius=[25])
        
        # Bind background updates
        main_layout.bind(pos=self._update_bg, size=self._update_bg)
        
        # Current time display
        current_time = datetime.now().strftime("%H:%M")
        time_label = Label(
            text=current_time,
            font_name=self.font_name,
            font_size="48sp",
            color=[1, 1, 1, 1],
            size_hint_y=0.2,
            bold=True
        )
        
        # Main wake up message with username
        wake_message = f"WAKE UP,\n{self.username.upper()}!"
        wake_up_label = Label(
            text=wake_message,
            font_name=self.font_name,
            font_size="36sp",
            color=[1, 1, 0.8, 1],  # Warm yellow-white
            size_hint_y=0.4,
            halign="center",
            valign="middle",
            bold=True
        )
        wake_up_label.bind(size=wake_up_label.setter('text_size'))
        
        # Volume indicator (if fade-in is enabled)
        self.volume_label = Label(
            text="🔊 Volume: 0%" if self.fadein else "",
            font_name=self.font_name,
            font_size="20sp",
            color=[0.8, 0.8, 1, 1],
            size_hint_y=0.1,
            opacity=1 if self.fadein else 0
        )
        
        # Button container
        button_container = BoxLayout(
            orientation='horizontal',
            size_hint_y=0.3,
            spacing=20,
            padding=[50, 0]
        )
        
        # Snooze button (5 minutes)
        snooze_button = Button(
            text="SNOOZE\n5 min",
            font_name=self.font_name,
            font_size="24sp",
            size_hint_x=0.4,
            background_color=[0.8, 0.6, 0.2, 1],  # Orange
            color=[1, 1, 1, 1]
        )
        snooze_button.bind(on_release=self._on_snooze_button)
        
        # Turn off button
        turn_off_button = Button(
            text="TURN OFF",
            font_name=self.font_name,
            font_size="28sp",
            size_hint_x=0.6,
            background_color=[0.8, 0.2, 0.2, 1],  # Red
            color=[1, 1, 1, 1],
            bold=True
        )
        turn_off_button.bind(on_release=self._on_turn_off_button)
        
        # Add buttons to container
        button_container.add_widget(snooze_button)
        button_container.add_widget(turn_off_button)
        
        # Add all elements to main layout
        main_layout.add_widget(time_label)
        main_layout.add_widget(wake_up_label)
        main_layout.add_widget(self.volume_label)
        main_layout.add_widget(button_container)
        
        # Add main layout to popup
        self.add_widget(main_layout)
        
        # Start pulsing animation for urgency
        self._start_pulse_animation()
    
    def _update_bg(self, instance, value):
        """Update background rectangles"""
        if hasattr(self, 'bg_rect1'):
            self.bg_rect1.pos = instance.pos
            self.bg_rect1.size = instance.size
        if hasattr(self, 'bg_rect2'):
            # Make red overlay slightly smaller for layered effect
            padding = 5
            self.bg_rect2.pos = (instance.x + padding, instance.y + padding)
            self.bg_rect2.size = (instance.width - 2*padding, instance.height - 2*padding)
    
    def _start_pulse_animation(self):
        """Start pulsing animation to get attention"""
        def pulse_cycle():
            # Animate opacity for attention-getting effect
            anim_in = Animation(opacity=0.9, duration=0.8)
            anim_out = Animation(opacity=0.95, duration=0.8)
            
            anim_in.bind(on_complete=lambda *args: anim_out.start(self))
            anim_out.bind(on_complete=lambda *args: pulse_cycle())
            
            anim_in.start(self)
        
        # Start pulsing after a brief delay
        Clock.schedule_once(lambda dt: pulse_cycle(), 0.5)
    
    def start_alarm(self):
        """Start playing the alarm sound with improved fade-in"""
        if self._sound_stopped:
            logger.warning("⚠️ Sound already stopped, not starting")
            return
            
        folder = "media/ringtones"
        path = os.path.join(folder, self.ringtone)
        self.sound_path = path
        
        try:
            if not os.path.exists(path):
                logger.warning(f"❌ Ringtone file not found: {path}")
                return
                
            # Get app instance
            from kivy.app import App
            app = App.get_running_app()
            
            # Use sound service to load the ringtone
            self.sound = app.sound_service.load_sound_file(path)
                
            if not self.sound:
                logger.warning(f"❌ Failed to load ringtone: {path}")
                return
            
            # Set initial volume
            self.sound.volume = self.current_volume
            self.sound.loop = True  # Loop the sound until turned off
            
            # Start playing
            if hasattr(self.sound, 'state') and self.sound.state != 'playing':
                self.sound.play()
                logger.info(f"🎵 Started alarm sound: {path}")
            
            # Start fade-in if enabled
            if self.fadein:
                self.start_fade_in()
            else:
                # Update volume display even without fade-in
                self._update_volume_display()
                
        except Exception as e:
            logger.error(f"❌ Error starting alarm: {e}")
    
    def start_fade_in(self):
        """Gradually increase volume with improved algorithm"""
        if self._sound_stopped:
            return
            
        # Cancel any existing fade event
        if self._fade_event:
            self._fade_event.cancel()
            self._fade_event = None
        
        logger.info(f"🔊 Starting fade-in over {self.fade_time} seconds (0% → {int(self.max_volume*100)}%)")
        
        # Better fade-in calculation
        total_steps = int(self.fade_time * 10)  # 10 steps per second for smooth fade
        self.fade_step = self.max_volume / total_steps
        fade_interval = self.fade_time / total_steps
        
        # Reset volume to 0 for fade-in
        self.current_volume = 0.0
        if self.sound:
            self.sound.volume = 0.0
        
        # Schedule incremental volume increase
        self._fade_event = Clock.schedule_interval(self._increase_volume, fade_interval)
        
        # Update display immediately
        self._update_volume_display()
    
    def _increase_volume(self, dt):
        """Improved volume increment with better error handling"""
        if not self.sound or self._sound_stopped:
            logger.info("🔇 Fade-in stopped (sound stopped)")
            return False
            
        try:
            if self.current_volume < self.max_volume:
                # Increase volume by calculated step
                self.current_volume = min(self.current_volume + self.fade_step, self.max_volume)
                
                # Apply new volume to sound
                self.sound.volume = self.current_volume
                
                # Update UI display
                self._update_volume_display()
                
                return True  # Continue the interval
            else:
                logger.info(f"🔊 Fade-in complete at {int(self.current_volume*100)}%")
                self._update_volume_display()
                return False  # Stop the interval
                
        except Exception as e:
            logger.error(f"❌ Error in fade-in: {e}")
            return False  # Stop on error
    
    def _update_volume_display(self):
        """Update volume display in UI"""
        if self.volume_label and self.fadein:
            volume_percent = int(self.current_volume * 100)
            volume_bars = "🔊" if volume_percent > 60 else "🔉" if volume_percent > 20 else "🔈"
            self.volume_label.text = f"{volume_bars} Volume: {volume_percent}%"
    
    def _on_snooze_button(self, button_instance):
        """Handle snooze button press - 5 minute delay"""
        logger.info("😴 Snooze button pressed - 5 minutes")
        
        # Stop current alarm
        self._stop_sound_only()
        
        # Schedule new alarm in 5 minutes
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'alarm_clock'):
                # Create snooze alarm
                Clock.schedule_once(
                    lambda dt: app.alarm_clock.trigger_alarm(self.ringtone, self.fadein), 
                    300  # 5 minutes = 300 seconds
                )
                
                # Add notification
                if hasattr(app, 'notification_service'):
                    app.notification_service.add("Alarm snoozed for 5 minutes", "system")
                
                logger.info("⏰ Snooze scheduled for 5 minutes")
            
        except Exception as e:
            logger.error(f"❌ Error setting snooze: {e}")
        
        # Dismiss popup
        self._dismiss_safely()
    
    def _on_turn_off_button(self, button_instance):
        """Handle turn off button press"""
        logger.info("🔴 Turn off button pressed")
        
        # Stop sound first
        self._stop_sound_only()
        
        # Then dismiss popup
        self._dismiss_safely()
    
    def _stop_sound_only(self):
        """Stop only the sound without dismissing popup"""
        if self._sound_stopped:
            return
            
        self._sound_stopped = True
        
        try:
            # Cancel any scheduled fade events
            if self._fade_event:
                self._fade_event.cancel()
                self._fade_event = None
            
            # Stop the sound
            if self.sound:
                if hasattr(self.sound, 'state') and self.sound.state != 'stop':
                    self.sound.stop()
                self.sound = None
            
            # Update volume display
            if self.volume_label:
                self.volume_label.text = "🔇 Alarm stopped"
            
            logger.info("🔇 Alarm sound stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping sound: {e}")
    
    def _dismiss_safely(self):
        """Safely dismiss popup without causing recursion"""
        if self._is_dismissing:
            logger.warning("⚠️ Popup already dismissing, ignoring")
            return
            
        self._is_dismissing = True
        
        try:
            # Schedule dismiss on next frame to avoid recursion
            Clock.schedule_once(lambda dt: self.dismiss(), 0)
            logger.info("📤 Popup dismiss scheduled")
            
        except Exception as e:
            logger.error(f"❌ Error dismissing popup: {e}")
    
    def stop_alarm(self, *args):
        """Stop the alarm - PUBLIC method called from AlarmClock"""
        logger.info("🛑 stop_alarm() called")
        self._stop_sound_only()
    
    def on_dismiss(self):
        """Cleanup when popup is dismissed - NO recursion"""
        logger.info(f"📤 AlarmPopup.on_dismiss() called for {self.username}")
        
        # Only stop sound if not already stopped
        if not self._sound_stopped:
            self._stop_sound_only()
        
        # Call parent without recursion
        try:
            return super(AlarmPopup, self).on_dismiss()
        except Exception as e:
            logger.error(f"❌ Error in parent on_dismiss: {e}")
            return True  # Allow dismissal anyway