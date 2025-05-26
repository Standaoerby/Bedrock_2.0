from utils.common import BasePage, Constants
from kivy.properties import StringProperty, BooleanProperty
from datetime import datetime
import logging

logger = logging.getLogger("HomeScreen")

class HomeScreen(BasePage):
    """Главный экран приложения"""
    
    # Properties
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")
    notification_text = StringProperty("")
    current_date = StringProperty("")

    def on_pre_enter(self):
        """Вход на экран"""
        logger.info("Entering HomeScreen")
        
        # Update all data immediately
        self.update_date()
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        
        # Start clock
        self.schedule_once(self.start_clock, 0.5)
        
        # Schedule regular updates
        self.schedule_timer(lambda dt: self.update_alarm(), 300)  # 5 min
        self.schedule_timer(lambda dt: self.update_weather(), Constants.WEATHER_UPDATE_INTERVAL)
        self.schedule_timer(lambda dt: self.update_notification(), Constants.NOTIFICATION_UPDATE_INTERVAL)
        self.schedule_timer(lambda dt: self.update_date(), 300)  # 5 min
    
    def start_clock(self, dt):
        """Запуск часов"""
        try:
            self.update_clock(None)
            self.schedule_timer(self.update_clock, Constants.CLOCK_UPDATE_INTERVAL)
            logger.info("Clock started")
        except Exception as e:
            logger.error(f"Error starting clock: {e}")
    
    def update_date(self):
        """Обновить дату и день недели"""
        now = datetime.now()
        self.current_date = now.strftime("%d %B, %A")
    
    def update_alarm(self):
        """Обновить информацию о будильнике"""
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.current_alarm_time = alarm.get("time", "--:--")
            self.alarm_active = alarm.get("enabled", False)
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False
    
    def toggle_alarm(self):
        """Переключить состояние будильника"""
        app = self.get_app()
        
        alarm = app.alarm_service.get_alarm()
        if alarm:
            alarm["enabled"] = not alarm.get("enabled", False)
            app.alarm_service.set_alarm(alarm)
            self.update_alarm()
            
            if alarm["enabled"]:
                app.play_sound("success")

    def update_weather(self):
        """Обновить информацию о погоде"""
        app = self.get_app()
        weather = app.weather_service.get_weather()
        now = weather.get("current", {})
        forecast_5h = weather.get("forecast_5h", {})
        
        # Current weather
        if now:
            temp = now.get("temperature", "--")
            condition = now.get("condition", "")
            self.weather_now_str = f'{temp}°C {condition}'
        else:
            self.weather_now_str = ""
            
        # 5-hour forecast
        if forecast_5h:
            temp_5h = forecast_5h.get("temperature", "--")
            self.weather_5h_str = f'{temp_5h}°C in 5h'
            
            # Calculate trend
            try:
                temp_now = float(now.get("temperature", 0))
                temp_5h_val = float(forecast_5h.get("temperature", 0))
                if temp_5h_val > temp_now:
                    self.weather_trend_arrow = "↑"
                elif temp_5h_val < temp_now:
                    self.weather_trend_arrow = "↓"
                else:
                    self.weather_trend_arrow = "~"
            except (ValueError, TypeError):
                self.weather_trend_arrow = ""
        else:
            self.weather_5h_str = ""
            self.weather_trend_arrow = ""

    def update_notification(self):
        """Обновить уведомления"""
        app = self.get_app()
        notifications = app.notification_service.notifications
        if notifications:
            last = sorted(notifications, key=lambda n: n.get("time", ""))[-1]
            self.notification_text = last.get("text", "")
        else:
            self.notification_text = ""

    def update_clock(self, dt):
        """Обновить часы"""
        try:
            now = datetime.now().strftime("%H:%M")
            
            # Update clock widgets
            self.safe_set_widget_text('clock_label', now)
            self.safe_set_widget_text('clock_shadow_label', now)
                    
        except Exception as e:
            logger.error(f"Error updating clock: {e}")