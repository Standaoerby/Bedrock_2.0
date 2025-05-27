from utils.common import BasePage
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
import os
import time
import logging

logger = logging.getLogger("AlarmScreen")

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class AlarmScreen(BasePage):
    """Экран настройки будильника"""
    
    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("morning.mp3")
    ringtone_list = ListProperty([])
    alarm_fadein = BooleanProperty(False)
    current_sound = ObjectProperty(None, allownone=True)
    
    # ДОБАВЛЕНО: Защита от множественных нажатий
    _last_button_press = 0
    _button_debounce_time = 0.5  # 500ms защита от повторных нажатий
    _sound_playing = False
    _button_processing = False

    def on_pre_enter(self):
        """Вход на экран"""
        logger.info("Entering AlarmScreen")
        self.stop_ringtone()  # Останавливаем любые играющие звуки
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    def load_ringtones(self):
        """Загрузить доступные мелодии"""
        folder = "media/ringtones"
        if os.path.exists(folder):
            try:
                self.ringtone_list = [f for f in os.listdir(folder) 
                    if f.lower().endswith((".mp3", ".ogg", ".wav"))]
                if self.selected_ringtone not in self.ringtone_list and self.ringtone_list:
                    self.selected_ringtone = self.ringtone_list[0]
                logger.info(f"Loaded {len(self.ringtone_list)} ringtones")
            except Exception as e:
                logger.error(f"Error loading ringtones: {e}")
                self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]
        else:
            try:
                os.makedirs(folder, exist_ok=True)
                logger.info(f"Created ringtones folder: {folder}")
            except Exception as e:
                logger.error(f"Failed to create ringtones folder: {e}")
            
            self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]

    def load_alarm_config(self):
        """Загрузить конфигурацию будильника"""
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.alarm_time = alarm.get("time", "07:30")
            self.alarm_active = alarm.get("enabled", True)
            repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
            
            # Handle numeric day format (compatibility)
            if repeat and all(isinstance(x, int) for x in repeat):
                days_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                self.alarm_repeat = [days_map[i-1] for i in repeat if 1 <= i <= 7]
            else:
                self.alarm_repeat = repeat
                
            self.selected_ringtone = alarm.get("ringtone", self.selected_ringtone)
            self.alarm_fadein = alarm.get("fadein", False)
            logger.info(f"Loaded alarm config: {alarm}")

    def save_alarm(self):
        """Сохранить настройки будильника"""
        app = self.get_app()
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
        """Обновить UI элементы"""
        # Update hours and minutes
        hours, minutes = self.alarm_time.split(':')
        self.safe_set_widget_text('hour_label', hours)
        self.safe_set_widget_text('minute_label', minutes)
        
        # Update the active button
        active_button = self.safe_get_widget('active_button')
        if active_button:
            active_button.text = "ON" if self.alarm_active else "OFF"
            app = self.get_app()
            if self.alarm_active:
                active_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
            else:
                active_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
        
        # Update fadein button
        fadein_button = self.safe_get_widget('fadein_button')
        if fadein_button:
            fadein_button.text = "ON" if self.alarm_fadein else "OFF"
            app = self.get_app()
            if self.alarm_fadein:
                fadein_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
            else:
                fadein_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
        
        # Update day buttons
        for day in DAYS_EN:
            btn_id = f"repeat_{day.lower()}"
            button = self.safe_get_widget(btn_id)
            if button:
                button.state = "down" if day in self.alarm_repeat else "normal"
        
        # Update ringtone spinner
        spinner = self.safe_get_widget('ringtone_spinner')
        if spinner:
            spinner.text = self.selected_ringtone
        
        # ИСПРАВЛЕНО: Правильно сбрасываем состояние кнопки воспроизведения
        self._reset_play_button()

    def _reset_play_button(self):
        """Сбросить состояние кнопки воспроизведения"""
        play_button = self.safe_get_widget('play_button')
        if play_button:
            play_button.state = 'normal'
            play_button.text = 'Play'
            # ДОБАВЛЕНО: Сбрасываем флаги состояния
            self._sound_playing = False
            self._button_processing = False

    def increment_hour(self):
        """Увеличить час"""
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) + 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        self.safe_set_widget_text('hour_label', f"{new_hour:02d}")

    def decrement_hour(self):
        """Уменьшить час"""
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) - 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        self.safe_set_widget_text('hour_label', f"{new_hour:02d}")

    def increment_minute(self):
        """Увеличить минуты"""
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) + 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        self.safe_set_widget_text('minute_label', f"{new_minute:02d}")

    def decrement_minute(self):
        """Уменьшить минуты"""
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) - 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        self.safe_set_widget_text('minute_label', f"{new_minute:02d}")

    def on_active_toggled(self, active):
        """Переключить активность будильника"""
        app = self.get_app()
        if active and not self.alarm_active:
            app.play_sound("success")
        
        self.alarm_active = active
        self.update_ui()

    def toggle_repeat(self, day, state):
        """Переключить день повтора"""
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)

    def select_ringtone(self, name):
        """Выбрать мелодию"""
        self.selected_ringtone = name
        self.stop_ringtone()  # Останавливаем предыдущий звук
        self._reset_play_button()  # Сбрасываем кнопку

    def toggle_play_ringtone(self, state):
        """ИСПРАВЛЕНО: Переключить воспроизведение мелодии с защитой от множественных нажатий"""
        current_time = time.time()
        
        # ДОБАВЛЕНО: Защита от быстрых повторных нажатий
        if current_time - self._last_button_press < self._button_debounce_time:
            logger.debug(f"Button press ignored due to debounce ({current_time - self._last_button_press:.2f}s)")
            return
        
        # ДОБАВЛЕНО: Защита от обработки во время уже идущей операции
        if self._button_processing:
            logger.debug("Button press ignored - already processing")
            return
            
        self._last_button_press = current_time
        self._button_processing = True
        
        try:
            app = self.get_app()
            app.play_sound("click")
            
            logger.info(f"Play button toggled: state={state}, currently_playing={self._sound_playing}")
            
            if state == 'down' and not self._sound_playing:
                # Начинаем воспроизведение
                logger.info("Starting ringtone playback")
                self.safe_set_widget_text('play_button', 'Stop')
                self.play_ringtone()
                
            elif state == 'normal' and self._sound_playing:
                # Останавливаем воспроизведение
                logger.info("Stopping ringtone playback")
                self.safe_set_widget_text('play_button', 'Play')
                self.stop_ringtone()
                
            else:
                # Несоответствие состояний - синхронизируем
                logger.warning(f"State mismatch: button_state={state}, sound_playing={self._sound_playing}")
                self._sync_button_state()
                
        except Exception as e:
            logger.error(f"Error in toggle_play_ringtone: {e}")
            # При ошибке сбрасываем состояние
            self._reset_play_button()
        finally:
            # ДОБАВЛЕНО: Разблокируем обработку с небольшой задержкой
            Clock.schedule_once(lambda dt: setattr(self, '_button_processing', False), 0.1)

    def _sync_button_state(self):
        """Синхронизировать состояние кнопки с реальным состоянием звука"""
        play_button = self.safe_get_widget('play_button')
        if not play_button:
            return
            
        # Проверяем реальное состояние звука
        actual_playing = self.current_sound and hasattr(self.current_sound, 'state') and self.current_sound.state != 'stop'
        
        if actual_playing != self._sound_playing:
            logger.info(f"Syncing sound state: flag={self._sound_playing}, actual={actual_playing}")
            self._sound_playing = actual_playing
            
        # Синхронизируем кнопку
        if self._sound_playing:
            play_button.state = 'down'
            play_button.text = 'Stop'
        else:
            play_button.state = 'normal'  
            play_button.text = 'Play'

    def play_ringtone(self):
        """ИСПРАВЛЕНО: Воспроизвести мелодию с улучшенной обработкой ошибок"""
        self.stop_ringtone()  # Сначала останавливаем любой играющий звук
        
        try:
            folder = "media/ringtones"
            path = os.path.join(folder, self.selected_ringtone)
            
            if not os.path.exists(path):
                logger.warning(f"Ringtone file not found: {path}")
                app = self.get_app()
                app.play_sound("error")
                self._reset_play_button()
                return
                
            app = self.get_app()
            self.current_sound = app.sound_service.load_sound_file(path)
            
            if self.current_sound and hasattr(self.current_sound, '_sound') and self.current_sound._sound:
                logger.info(f"Playing ringtone preview: {path}")
                
                # ДОБАВЛЕНО: Устанавливаем громкость для предварительного прослушивания
                self.current_sound.volume = 0.7  # 70% громкости для теста
                
                self.current_sound.play()
                self._sound_playing = True
                
                # ДОБАВЛЕНО: Планируем проверку завершения воспроизведения
                self._schedule_sound_check()
                
            else:
                logger.error("Failed to create valid sound object")
                app.play_sound("error")
                self._reset_play_button()

        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            app = self.get_app()
            app.play_sound("error")
            self._reset_play_button()

    def _schedule_sound_check(self):
        """Планируем проверку состояния звука"""
        Clock.schedule_interval(self._check_sound_status, 0.5)

    def _check_sound_status(self, dt):
        """Проверяем состояние воспроизведения звука"""
        try:
            if not self.current_sound:
                self._on_sound_finished()
                return False  # Останавливаем событие
                
            # Проверяем состояние звука
            if hasattr(self.current_sound, 'state'):
                if self.current_sound.state == 'stop':
                    self._on_sound_finished()
                    return False  # Останавливаем событие
                    
            return True  # Продолжаем проверку
            
        except Exception as e:
            logger.error(f"Error checking sound status: {e}")
            self._on_sound_finished()
            return False

    def _on_sound_finished(self):
        """Обработчик завершения воспроизведения"""
        logger.info("Sound playback finished")
        self._sound_playing = False
        self._reset_play_button()

    def stop_ringtone(self):
        """ИСПРАВЛЕНО: Остановить воспроизведение мелодии"""
        try:
            if self.current_sound:
                if hasattr(self.current_sound, 'stop') and hasattr(self.current_sound, 'state'):
                    if self.current_sound.state != 'stop':
                        self.current_sound.stop()
                        logger.info("Stopped ringtone preview")
                        
                self.current_sound = None
                
            self._sound_playing = False
            logger.info("Ringtone stopped and cleaned up")
            
        except Exception as e:
            logger.error(f"Error stopping ringtone: {e}")
            # Принудительно очищаем состояние
            self.current_sound = None
            self._sound_playing = False

    def on_fadein_toggled(self, active):
        """Переключить fade-in"""
        app = self.get_app()
        
        if active and not self.alarm_fadein:
            app.play_sound("success")
        
        self.alarm_fadein = active
        self.update_ui()

    def on_leave(self):
        """Очистка при выходе с экрана"""
        logger.info("Leaving alarm screen")
        
        # Останавливаем любые играющие звуки
        self.stop_ringtone()
        
        # Сбрасываем состояние кнопки
        self._reset_play_button()
        
        # Очищаем таймеры
        self.cleanup_timers()
        
        super().on_leave()
        logger.info("Alarm screen cleanup completed")