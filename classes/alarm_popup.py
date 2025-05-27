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
        # ИСПРАВЛЕНО: Начинаем с хорошо слышимой громкости при fade-in
        self.current_volume = 0.35 if fadein else 0.85  # Start at 35% if fade-in, 85% if not
        self.max_volume = 0.85  # Maximum volume
        self.fade_time = 6.0  # Быстрый fade-in: 6 секунд
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
        """Create beautiful UI elements with theme colors"""
        # Main container with custom background
        main_layout = BoxLayout(orientation='vertical', padding=[30, 40], spacing=30)
        
        # ИСПРАВЛЕНО: Используем цвета темы вместо хардкода
        # Получаем цвета из темы
        primary_color = self.theme.get("colors", {}).get("primary", [0.2, 0.4, 0.8, 1])
        accent_color = self.theme.get("colors", {}).get("accent", [1, 0.6, 0, 1])
        warning_color = self.theme.get("colors", {}).get("warning", [0.9, 0.7, 0.1, 1])
        panel_bg = self.theme.get("panel_bg", [0.1, 0.1, 0.15, 0.9])
        
        # Custom background drawing with theme colors
        with main_layout.canvas.before:
            # Main background from theme
            bg_color = list(panel_bg)
            bg_color[3] = 0.95  # Увеличиваем непрозрачность для будильника
            Color(*bg_color)
            self.bg_rect1 = RoundedRectangle(pos=main_layout.pos, size=main_layout.size, radius=[25])
            
            # ИСПРАВЛЕНО: Используем warning/accent цвет вместо красного
            overlay_color = list(warning_color)
            overlay_color[3] = 0.6  # Полупрозрачное наложение для внимания
            Color(*overlay_color)
            self.bg_rect2 = RoundedRectangle(pos=main_layout.pos, size=main_layout.size, radius=[25])
        
        # Bind background updates
        main_layout.bind(pos=self._update_bg, size=self._update_bg)
        
        # Current time display
        current_time = datetime.now().strftime("%H:%M")
        font_color = self.theme.get("font_color", [1, 1, 1, 1])
        
        time_label = Label(
            text=current_time,
            font_name=self.font_name,
            font_size="48sp",
            color=font_color,
            size_hint_y=0.2,
            bold=True
        )
        
        # Main wake up message with username
        wake_message = f"WAKE UP,\n{self.username.upper()}!"
        font_highlight = self.theme.get("colors", {}).get("font_highlight", [1, 1, 0.8, 1])
        
        wake_up_label = Label(
            text=wake_message,
            font_name=self.font_name,
            font_size="36sp",
            color=font_highlight,
            size_hint_y=0.4,
            halign="center",
            valign="middle",
            bold=True
        )
        wake_up_label.bind(size=wake_up_label.setter('text_size'))
        
        # Volume indicator (if fade-in is enabled)
        font_secondary = self.theme.get("colors", {}).get("font_secondary", [0.8, 0.8, 1, 1])
        
        self.volume_label = Label(
            text="🔊 Volume: 35%" if self.fadein else "",
            font_name=self.font_name,
            font_size="20sp",
            color=font_secondary,
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
        
        # ИСПРАВЛЕНО: Используем цвета темы для кнопок
        inactive_color = self.theme.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
        error_color = self.theme.get("colors", {}).get("error", [0.9, 0.2, 0.2, 1])
        
        # Snooze button (5 minutes) - используем warning цвет
        snooze_button = Button(
            text="SNOOZE\n5 min",
            font_name=self.font_name,
            font_size="24sp",
            size_hint_x=0.4,
            background_color=warning_color,  # Цвет темы
            color=font_color
        )
        snooze_button.bind(on_release=self._on_snooze_button)
        
        # Turn off button - используем error цвет
        turn_off_button = Button(
            text="TURN OFF",
            font_name=self.font_name,
            font_size="28sp",
            size_hint_x=0.6,
            background_color=error_color,  # Цвет темы
            color=font_color,
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
            # Make overlay slightly smaller for layered effect
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
            
            # ИСПРАВЛЕНО: Устанавливаем начальную громкость и проверяем применение
            self.sound.volume = self.current_volume
            self.sound.loop = True  # Loop the sound until turned off
            
            logger.info(f"🎵 Starting alarm sound: {path} with volume {self.current_volume:.2f} ({int(self.current_volume*100)}%)")
            
            # Start playing
            if hasattr(self.sound, 'state') and self.sound.state != 'playing':
                self.sound.play()
                logger.info(f"🎵 Alarm sound started playing")
                
                # ДОБАВЛЕНО: Принудительно переустанавливаем громкость после начала воспроизведения
                import time
                time.sleep(0.1)  # Короткая пауза для инициализации
                self.sound.volume = self.current_volume
                logger.info(f"🔊 Volume re-applied after play start: {self.current_volume:.2f}")
            
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
        
        logger.info(f"🔊 Starting fade-in from {int(self.current_volume*100)}% to {int(self.max_volume*100)}% over {self.fade_time} seconds")
        
        # ИСПРАВЛЕНО: Более агрессивный fade-in с проверкой применения громкости
        total_steps = int(self.fade_time * 8)  # 8 шагов в секунду для очень плавности
        volume_increase = (self.max_volume - self.current_volume) / total_steps
        fade_interval = self.fade_time / total_steps
        
        logger.info(f"🔊 Fade parameters: {total_steps} steps, increase per step: {volume_increase:.4f}, interval: {fade_interval:.3f}s")
        
        # ДОБАВЛЕНО: Принудительно проверяем текущую громкость звука
        if self.sound:
            actual_volume = getattr(self.sound, 'volume', 0)
            logger.info(f"🎵 Current sound volume check: set={self.current_volume:.2f}, actual={actual_volume:.2f}")
            
            # Если громкости не совпадают, принудительно устанавливаем
            if abs(actual_volume - self.current_volume) > 0.05:
                self.sound.volume = self.current_volume
                logger.warning(f"🔧 Fixed volume mismatch: {actual_volume:.2f} → {self.current_volume:.2f}")
        
        # Schedule incremental volume increase
        self._fade_event = Clock.schedule_interval(
            lambda dt: self._increase_volume(volume_increase), 
            fade_interval
        )
        
        # Update display immediately
        self._update_volume_display()
    
    def _increase_volume(self, volume_step):
        """Improved volume increment with better error handling and verification"""
        if not self.sound or self._sound_stopped:
            logger.info("🔇 Fade-in stopped (sound stopped)")
            return False
            
        try:
            if self.current_volume < self.max_volume:
                # Increase volume by calculated step
                old_volume = self.current_volume
                self.current_volume = min(self.current_volume + volume_step, self.max_volume)
                
                # Apply new volume to sound with verification
                self.sound.volume = self.current_volume
                
                # ДОБАВЛЕНО: Проверяем, что громкость действительно применилась
                applied_volume = getattr(self.sound, 'volume', 0)
                
                if abs(applied_volume - self.current_volume) > 0.05:
                    # Повторная попытка установки громкости
                    logger.warning(f"🔧 Volume not applied correctly, retrying: target={self.current_volume:.2f}, actual={applied_volume:.2f}")
                    self.sound.volume = self.current_volume
                    applied_volume = getattr(self.sound, 'volume', 0)
                
                logger.debug(f"🔊 Volume: {old_volume:.2f} → {self.current_volume:.2f} ({int(self.current_volume*100)}%) [applied: {applied_volume:.2f}]")
                
                # Update UI display
                self._update_volume_display()
                
                return True  # Continue the interval
            else:
                logger.info(f"🔊 Fade-in complete at {int(self.current_volume*100)}%")
                
                # ДОБАВЛЕНО: Финальная проверка громкости
                final_volume = getattr(self.sound, 'volume', 0)
                logger.info(f"🎵 Final volume check: target={self.current_volume:.2f}, actual={final_volume:.2f}")
                
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
                    logger.info("🔇 Sound stopped")
                self.sound = None
            
            # Update volume display
            if self.volume_label:
                self.volume_label.text = "🔇 Alarm stopped"
            
            logger.info("🔇 Alarm sound stopped completely")
            
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