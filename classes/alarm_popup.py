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
import subprocess
import re
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
        
        # ИСПРАВЛЕНО: Улучшенные параметры громкости
        self.sound = None
        self.sound_path = None
        self.ringtone = ringtone
        self.fadein = fadein
        
        # ИСПРАВЛЕНО: Новые параметры громкости для максимального звука
        self.start_volume = 0.15  # Начинаем с 15% для плавности
        self.current_volume = self.start_volume
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Устанавливаем системную громкость на максимум
        self._ensure_max_system_volume()
        
        # ИСПРАВЛЕНО: Максимальная громкость теперь может быть выше 100%
        self.max_volume = self._get_optimal_max_volume()  # Может быть > 1.0
        self.fade_time = 12.0  # ИСПРАВЛЕНО: Сократили время fade-in до 12 секунд
        self._fade_event = None
        self._loop_event = None  # Для зацикливания звука
        
        # Create the beautiful UI
        self._create_ui()
        
        logger.info(f"🚨 AlarmPopup created: user={self.username}, ringtone={ringtone}, fadein={fadein}")
        logger.info(f"🔊 Volume settings: start={int(self.start_volume*100)}%, max={int(self.max_volume*100)}%, fade_time={self.fade_time}s")
    
    def _ensure_max_system_volume(self):
        """НОВОЕ: Принудительно устанавливаем системную громкость на максимум"""
        try:
            logger.info("🔊 Setting system volume to maximum for alarm...")
            
            # Получаем текущую системную громкость
            current_vol = self._get_current_system_volume()
            logger.info(f"🔊 Current system volume: {current_vol}%")
            
            # Если громкость меньше 95%, устанавливаем на максимум
            if current_vol < 95:
                result = subprocess.run(['amixer', 'set', 'Master', '100%'], 
                                      capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info("✅ System volume set to 100%")
                    
                    # Также попробуем установить PCM если есть
                    try:
                        subprocess.run(['amixer', 'set', 'PCM', '100%'], 
                                     capture_output=True, text=True, timeout=3)
                        logger.debug("✅ PCM volume also set to 100%")
                    except:
                        pass  # Не критично если PCM недоступен
                        
                else:
                    logger.warning(f"⚠️ Failed to set system volume: {result.stderr}")
            else:
                logger.info("✅ System volume already at maximum")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not set system volume: {e}")
    
    def _get_current_system_volume(self):
        """ИСПРАВЛЕНО: Правильно получаем текущую системную громкость"""
        try:
            result = subprocess.run(['amixer', 'get', 'Master'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Ищем строки с процентами громкости
                # Пример: "  Mono: Playback 31 [100%] [0.00dB] [on]"
                lines = result.stdout.split('\n')
                for line in lines:
                    if '[' in line and '%' in line and ('Playback' in line or 'Front Left:' in line):
                        # Используем regex для извлечения процента
                        match = re.search(r'\[(\d+)%\]', line)
                        if match:
                            volume = int(match.group(1))
                            logger.debug(f"Found system volume: {volume}% in line: {line.strip()}")
                            return volume
                
                logger.warning("Could not parse volume from amixer output")
                logger.debug(f"Amixer output: {result.stdout}")
                
            return 50  # Fallback
            
        except Exception as e:
            logger.warning(f"Error getting current system volume: {e}")
            return 50
    
    def _get_optimal_max_volume(self):
        """ИСПРАВЛЕНО: Определяем оптимальную максимальную громкость"""
        try:
            # Проверяем актуальную системную громкость
            system_vol = self._get_current_system_volume()
            
            if system_vol >= 95:
                # Система на максимуме - можем попробовать превышение
                optimal_volume = 1.3  # 130% - пробуем усиление
                logger.info(f"🔊 System at {system_vol}%, trying enhanced volume: {int(optimal_volume*100)}%")
            elif system_vol >= 80:
                # Хорошая системная громкость
                optimal_volume = 1.1  # 110%
                logger.info(f"🔊 System at {system_vol}%, using boosted volume: {int(optimal_volume*100)}%")
            else:
                # Системная громкость низкая
                optimal_volume = 1.0  # 100%
                logger.warning(f"🔊 System volume low ({system_vol}%), using standard max: {int(optimal_volume*100)}%")
            
            return optimal_volume
            
        except Exception as e:
            logger.error(f"Error determining optimal volume: {e}")
            return 1.0  # Safe fallback
    
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
            text=f"🔊 Volume: {int(self.start_volume*100)}%" if self.fadein else "",
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
            text="SNOOZE",
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
        """Start playing the alarm sound with MAXIMUM volume fade-in"""
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
                
            logger.info(f"🎵 Loading alarm sound with MAXIMUM volume: {path}")
            
            # ИСПРАВЛЕНО: Улучшенная загрузка звука
            try:
                import pygame
                if not pygame.mixer.get_init():
                    logger.error("❌ Pygame mixer not initialized")
                    return
                    
                # Создаем звук напрямую через pygame
                pygame_sound = pygame.mixer.Sound(path)
                
                # Оборачиваем в наш класс для совместимости
                from services.sound_service import PyGameSound
                self.sound = PyGameSound(path)
                self.sound._sound = pygame_sound
                
                logger.info(f"✅ Sound loaded directly via pygame")
                
            except Exception as load_error:
                logger.error(f"❌ Direct pygame load failed: {load_error}")
                
                # Fallback к sound service
                from kivy.app import App
                app = App.get_running_app()
                self.sound = app.sound_service.load_sound_file(path)
                
                if not self.sound:
                    logger.warning(f"❌ Failed to load ringtone via sound service: {path}")
                    return
                    
                logger.info(f"✅ Sound loaded via sound service fallback")
            
            # ИСПРАВЛЕНО: Устанавливаем правильные параметры звука
            if not self.sound or not self.sound._sound:
                logger.error("❌ Sound object invalid")
                return
            
            # НЕ зацикливаем автоматически - будем управлять вручную
            self.sound.loop = False
            
            # ИСПРАВЛЕНО: Устанавливаем начальную громкость
            self.current_volume = self.start_volume
            self.sound.volume = self.current_volume
            
            logger.info(f"🎵 Starting MAXIMUM VOLUME alarm: {int(self.current_volume*100)}% → {int(self.max_volume*100)}%")
            logger.info(f"🔊 Fade parameters: {self.fade_time}s to reach {int(self.max_volume*100)}% volume")
            
            # Запускаем воспроизведение
            self.sound.play()
            
            # ДОБАВЛЕНО: Планируем зацикливание звука
            self._schedule_sound_loop()
            
            # Start fade-in if enabled
            if self.fadein:
                self.start_fade_in()
            else:
                # Если fade-in отключен, сразу устанавливаем максимальную громкость
                self.current_volume = self.max_volume
                self.sound.volume = self.current_volume
                
                # НОВОЕ: Дополнительная проверка что громкость применилась
                applied_vol = getattr(self.sound, 'volume', 0)
                logger.info(f"🔊 Immediate max volume: target={int(self.current_volume*100)}%, applied={int(applied_vol*100)}%")
                
                self._update_volume_display()
                
        except Exception as e:
            logger.error(f"❌ Error starting alarm: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _schedule_sound_loop(self):
        """Планируем зацикливание звука"""
        if self._sound_stopped:
            return
            
        # Планируем проверку состояния звука каждые 2 секунды
        self._loop_event = Clock.schedule_interval(self._check_sound_loop, 2.0)
    
    def _check_sound_loop(self, dt):
        """Проверяем нужно ли перезапустить звук для зацикливания"""
        if self._sound_stopped or not self.sound:
            return False  # Останавливаем событие
            
        try:
            # Проверяем состояние звука
            if self.sound.state == 'stop':
                logger.debug("🔄 Restarting alarm sound for loop")
                self.sound.play()
                
                # НОВОЕ: Убеждаемся что громкость сохраняется при перезапуске
                if hasattr(self.sound, 'volume'):
                    current_vol = self.current_volume
                    self.sound.volume = current_vol
                    logger.debug(f"🔊 Volume maintained on restart: {int(current_vol*100)}%")
                
                return True  # Продолжаем событие
            else:
                return True  # Продолжаем следить
                
        except Exception as e:
            logger.error(f"❌ Error in sound loop check: {e}")
            return False  # Останавливаем событие при ошибке
    
    def start_fade_in(self):
        """ИСПРАВЛЕНО: МАКСИМАЛЬНЫЙ fade-in до усиленной громкости"""
        if self._sound_stopped:
            return
            
        # Cancel any existing fade event
        if self._fade_event:
            self._fade_event.cancel()
            self._fade_event = None
        
        logger.info(f"🔊 Starting MAXIMUM fade-in: {int(self.current_volume*100)}% → {int(self.max_volume*100)}% over {self.fade_time}s")
        
        # ИСПРАВЛЕНО: Ускоренный fade-in для достижения максимальной громкости
        total_steps = int(self.fade_time * 5)  # 5 шагов в секунду для более быстрого нарастания
        volume_increase = (self.max_volume - self.current_volume) / total_steps
        fade_interval = self.fade_time / total_steps
        
        logger.info(f"🔊 Enhanced fade parameters: {total_steps} steps, increase: +{volume_increase:.4f} per step, interval: {fade_interval:.3f}s")
        
        # Проверяем текущую громкость звука
        if self.sound:
            actual_volume = getattr(self.sound, 'volume', 0)
            logger.info(f"🎵 Volume verification: set={self.current_volume:.2f}, actual={actual_volume:.2f}")
            
            # Если громкости не совпадают, принудительно устанавливаем
            if abs(actual_volume - self.current_volume) > 0.05:
                self.sound.volume = self.current_volume
                logger.warning(f"🔧 Fixed volume mismatch: {actual_volume:.2f} → {self.current_volume:.2f}")
        
        # НОВОЕ: Дополнительная попытка установить системную громкость на максимум
        try:
            subprocess.run(['amixer', 'set', 'Master', '100%'], 
                         capture_output=True, text=True, timeout=2)
            logger.debug("🔊 Re-confirmed system volume at 100%")
        except:
            pass
        
        # Schedule incremental volume increase with enhanced parameters
        self._fade_event = Clock.schedule_interval(
            lambda dt: self._increase_volume_enhanced(volume_increase), 
            fade_interval
        )
        
        # Update display immediately
        self._update_volume_display()
    
    def _increase_volume_enhanced(self, volume_step):
        """ИСПРАВЛЕНО: Усиленное увеличение громкости с проверками"""
        if not self.sound or self._sound_stopped:
            logger.debug("🔇 Fade-in stopped (sound stopped)")
            return False
            
        try:
            if self.current_volume < self.max_volume:
                # Increase volume by calculated step
                old_volume = self.current_volume
                self.current_volume = min(self.current_volume + volume_step, self.max_volume)
                
                # НОВОЕ: Пробуем установить громкость с усилением
                target_volume = self.current_volume
                
                # Первая попытка - обычная установка
                self.sound.volume = target_volume
                
                # Проверяем что громкость применилась
                applied_volume = getattr(self.sound, 'volume', 0)
                
                # НОВОЕ: Если pygame ограничивает до 1.0, пробуем системное усиление
                if target_volume > 1.0 and applied_volume <= 1.0:
                    logger.debug(f"🔊 Pygame capped at {applied_volume:.2f}, trying system boost...")
                    
                    # Пробуем увеличить системную громкость выше 100%
                    try:
                        boost_percent = int(target_volume * 100)  # Может быть > 100%
                        subprocess.run(['amixer', 'set', 'Master', f'{boost_percent}%'], 
                                     capture_output=True, text=True, timeout=2)
                        logger.debug(f"🔊 System volume boosted to {boost_percent}%")
                    except Exception as boost_error:
                        logger.debug(f"System boost failed: {boost_error}")
                
                # Повторная проверка после системного усиления
                applied_volume = getattr(self.sound, 'volume', 0)
                
                # Логируем значительные изменения громкости
                old_percent = int(old_volume * 100)
                new_percent = int(self.current_volume * 100) 
                applied_percent = int(applied_volume * 100)
                
                if new_percent != old_percent:
                    logger.info(f"🔊 MAXIMUM Volume: {old_percent}% → {new_percent}% [actual: {applied_percent}%]")
                
                # Update UI display
                self._update_volume_display()
                
                return True  # Continue the interval
            else:
                logger.info(f"🔊 MAXIMUM fade-in complete at {int(self.current_volume*100)}%")
                
                # НОВОЕ: Финальная проверка максимальной громкости
                final_volume = getattr(self.sound, 'volume', 0)
                final_system = self._get_current_system_volume()
                
                logger.info(f"🎵 FINAL MAXIMUM check: pygame={int(final_volume*100)}%, system={final_system}%")
                
                self._update_volume_display()
                return False  # Stop the interval
                
        except Exception as e:
            logger.error(f"❌ Error in enhanced fade-in: {e}")
            return False  # Stop on error
    
    def _update_volume_display(self):
        """Update volume display in UI with enhanced info"""
        if self.volume_label and self.fadein:
            volume_percent = int(self.current_volume * 100)
            
            # НОВОЕ: Показываем усиленную громкость
            if volume_percent > 100:
                volume_bars = "🔊🔊"  # Двойной значок для усиления
                status = f"BOOSTED {volume_percent}%"
            elif volume_percent > 80:
                volume_bars = "🔊"
                status = f"{volume_percent}%"
            elif volume_percent > 40:
                volume_bars = "🔉"
                status = f"{volume_percent}%"
            else:
                volume_bars = "🔈"
                status = f"{volume_percent}%"
            
            self.volume_label.text = f"{volume_bars} Volume: {status}"
    
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
            # Cancel any scheduled events
            if self._fade_event:
                self._fade_event.cancel()
                self._fade_event = None
            
            if self._loop_event:
                self._loop_event.cancel()
                self._loop_event = None
            
            # Stop the sound
            if self.sound:
                if hasattr(self.sound, 'state') and self.sound.state != 'stop':
                    self.sound.stop()
                    logger.info("🔇 MAXIMUM volume sound stopped")
                self.sound = None
            
            # Update volume display
            if self.volume_label:
                self.volume_label.text = "🔇 Alarm stopped"
            
            logger.info("🔇 MAXIMUM volume alarm sound stopped completely")
            
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