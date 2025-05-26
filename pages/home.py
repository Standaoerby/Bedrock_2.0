from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
import logging

# Добавляем логирование
logger = logging.getLogger("HomeScreen")

class HomeScreen(MDScreen):
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")  # "↑", "↓", or "="
    notification_text = StringProperty("")
    current_date = StringProperty("")
    current_day = StringProperty("")
    # Add property to track clock initialization
    _clock_initialized = BooleanProperty(False)
    _retry_count = NumericProperty(0)

    def on_pre_enter(self):
        logger.info("Entering HomeScreen - initializing")
        self._clock_initialized = False  # Сбрасываем флаг инициализации часов
        
        # Обновляем дату и данные немедленно
        self.update_date()
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        
        # ИСПРАВЛЕНО: Инициализируем часы сразу без задержки
        self.initialize_clock(None)
        
        # Schedule regular updates с увеличенными интервалами
        self._alarm_update_ev = Clock.schedule_interval(lambda dt: self.update_alarm(), 300)  # 5 min
        self._weather_update_ev = Clock.schedule_interval(lambda dt: self.update_weather(), 900)  # 15 min
        self._notification_update_ev = Clock.schedule_interval(lambda dt: self.update_notification(), 30)  # 30 sec
        self._date_update_ev = Clock.schedule_interval(lambda dt: self.update_date(), 300)  # 5 min
    
    def initialize_clock(self, dt):
        """ИСПРАВЛЕННАЯ инициализация часов"""
        logger.info("Initializing clock")
        
        # ИСПРАВЛЕНО: Проверяем доступность виджетов
        if not self._check_clock_widgets():
            if self._retry_count < 5:
                self._retry_count += 1
                logger.warning(f"Clock widgets not ready, retry {self._retry_count}/5")
                Clock.schedule_once(self.initialize_clock, 0.5)
                return
            else:
                logger.error("Clock widgets failed to initialize after 5 retries")
                return
        
        # Обновляем часы сразу
        self.update_clock(None)
        
        # ИСПРАВЛЕНО: Запускаем таймер только если виджеты готовы
        if not hasattr(self, '_clock_ev') or not self._clock_ev:
            self._clock_ev = Clock.schedule_interval(self.update_clock, 1)
            self._clock_initialized = True
            logger.info("Clock initialization complete")
    
    def _check_clock_widgets(self):
        """Проверка доступности виджетов часов"""
        try:
            return (hasattr(self, 'ids') and 
                    self.ids and 
                    'clock_label' in self.ids and 
                    self.ids.clock_label is not None)
        except Exception as e:
            logger.error(f"Error checking clock widgets: {e}")
            return False
    
    def update_date(self):
        """Update the current date and day of week"""
        now = datetime.now()
        self.current_date = now.strftime("%d %B, %A")  # "15 May, Thursday"
    
    def update_alarm(self):
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.current_alarm_time = alarm.get("time", "--:--")
            self.alarm_active = alarm.get("enabled", False)
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False
    
    def toggle_alarm(self):
        """Toggle the alarm active state on button press"""
        app = self.get_app()
        # The click sound is already played by the button's on_press event
        # Don't play it again here
        
        alarm = app.alarm_service.get_alarm()
        if alarm:
            alarm["enabled"] = not alarm.get("enabled", False)
            app.alarm_service.set_alarm(alarm)
            self.update_alarm()
            
            # Play success sound only when alarm is enabled
            if alarm["enabled"]:
                app.play_sound("success")

    def update_weather(self):
        app = self.get_app()
        w = app.weather_service.get_weather()
        now = w.get("current", {})
        f5 = w.get("forecast_5h", {})
        if now:
            self.weather_now_str = f'{now.get("temperature", "--")}°C {now.get("condition", "")}'
        else:
            self.weather_now_str = ""
        if f5:
            self.weather_5h_str = f'{f5.get("temperature", "--")}°C in 5h'
            # Trend - modified to use equals sign when temperatures are the same
            try:
                temp_now = float(now.get("temperature", 0))
                temp_5h = float(f5.get("temperature", 0))
                if temp_5h > temp_now:
                    self.weather_trend_arrow = "↑"  # Red arrow up
                elif temp_5h < temp_now:
                    self.weather_trend_arrow = "↓"  # Blue arrow down
                else:
                    self.weather_trend_arrow = "~"  # White equals sign for no change
            except Exception:
                self.weather_trend_arrow = ""
        else:
            self.weather_5h_str = ""
            self.weather_trend_arrow = ""

    def update_notification(self):
        app = self.get_app()
        notifications = app.notification_service.notifications
        if notifications:
            last = sorted(notifications, key=lambda n: n.get("time", ""))[-1]
            self.notification_text = last.get("text", "")
        else:
            self.notification_text = ""

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
    
    def on_leave(self):
        """ИСПРАВЛЕННАЯ очистка при выходе с экрана"""
        logger.info("Leaving HomeScreen - cleaning up")
        
        # Останавливаем все таймеры
        timers_to_stop = [
            '_clock_ev', '_alarm_update_ev', '_weather_update_ev', 
            '_notification_update_ev', '_date_update_ev'
        ]
        
        for timer_name in timers_to_stop:
            if hasattr(self, timer_name):
                try:
                    timer = getattr(self, timer_name)
                    if timer:
                        timer.cancel()
                        logger.debug(f"{timer_name} canceled")
                except Exception as e:
                    logger.error(f"Error canceling {timer_name}: {e}")
                finally:
                    setattr(self, timer_name, None)
        
        # Сбрасываем флаги
        self._clock_initialized = False
        self._retry_count = 0

    def update_clock(self, dt):
        """ИСПРАВЛЕННОЕ обновление часов с проверкой доступности виджетов"""
        now = datetime.now().strftime("%H:%M")
        
        try:
            # ИСПРАВЛЕНО: Более тщательная проверка виджетов
            if not self._check_clock_widgets():
                logger.warning("Clock widgets not available during update")
                return
            
            # Обновляем текст часов
            self.ids.clock_label.text = now
            
            # Обновляем тень часов, если она есть
            if 'clock_shadow_label' in self.ids and self.ids.clock_shadow_label:
                self.ids.clock_shadow_label.text = now
                
            # Журналируем обновление раз в минуту (чтобы не засорять логи)
            if now.endswith(':00'):
                logger.debug(f"Clock updated: {now}")
                
        except Exception as e:
            logger.error(f"Error updating clock: {e}")
            # ИСПРАВЛЕНО: При ошибке перезапускаем инициализацию часов
            if self._retry_count < 3:
                self._retry_count += 1
                logger.info(f"Reinitializing clock, attempt {self._retry_count}")
                Clock.schedule_once(self.initialize_clock, 1.0)