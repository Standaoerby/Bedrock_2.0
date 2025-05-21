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
        
        # Инициализируем часы сразу
        Clock.schedule_once(self.initialize_clock, 0.1)
        
        # Schedule regular updates
        Clock.schedule_interval(lambda dt: self.update_alarm(), 300)
        Clock.schedule_interval(lambda dt: self.update_weather(), 900)
        Clock.schedule_interval(lambda dt: self.update_notification(), 30)
        Clock.schedule_interval(lambda dt: self.update_date(), 300)
    
    def initialize_clock(self, dt):
        """Улучшенная инициализация часов"""
        logger.info("Initializing clock")
        
        # Обновляем часы сразу
        self.update_clock(None)
        
        # Запускаем таймер для обновления часов каждую секунду
        self._clock_ev = Clock.schedule_interval(self.update_clock, 1)
        self._clock_initialized = True
        logger.info("Clock initialization complete")
    
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
                    self.weather_trend_arrow = "="  # White equals sign for no change
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
        # Останавливаем таймер часов при выходе с экрана
        logger.info("Leaving HomeScreen - cleaning up")
        if hasattr(self, '_clock_ev'):
            self._clock_ev.cancel()
            logger.info("Clock timer canceled")
            
        # Сбрасываем флаг инициализации часов
        self._clock_initialized = False

    def update_clock(self, dt):
        """Обновление часов с проверкой наличия виджетов"""
        now = datetime.now().strftime("%H:%M")
        
        try:
            # Проверяем наличие элементов UI
            if hasattr(self, 'ids') and self.ids and 'clock_label' in self.ids:
                # Обновляем текст часов
                self.ids.clock_label.text = now
                
                # Обновляем тень часов, если она есть
                if 'clock_shadow_label' in self.ids:
                    self.ids.clock_shadow_label.text = now
                    
                # Журналируем обновление раз в минуту (чтобы не засорять логи)
                if now.endswith(':00'):
                    logger.debug(f"Clock updated: {now}")
            else:
                # Если виджеты не найдены, выводим предупреждение
                logger.warning("Clock widgets not found in ids")
                available_ids = list(self.ids.keys()) if hasattr(self, 'ids') and self.ids else []
                logger.warning(f"Available ids: {available_ids}")
        except Exception as e:
            logger.error(f"Error updating clock: {e}")