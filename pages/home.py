from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty
import logging

logger = logging.getLogger("HomeScreen")

class HomeScreen(MDScreen):
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")  # "↑", "↓", or "="
    notification_text = StringProperty("")
    current_date = StringProperty("")

    def on_pre_enter(self):
        logger.info("Entering HomeScreen")
        
        # Update all data immediately
        self.update_date()
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        
        # Start clock - УПРОЩЁННО
        Clock.schedule_once(self.start_clock, 0.5)
        
        # Schedule regular updates
        self._alarm_update_ev = Clock.schedule_interval(lambda dt: self.update_alarm(), 300)  # 5 min
        self._weather_update_ev = Clock.schedule_interval(lambda dt: self.update_weather(), 900)  # 15 min
        self._notification_update_ev = Clock.schedule_interval(lambda dt: self.update_notification(), 30)  # 30 sec
        self._date_update_ev = Clock.schedule_interval(lambda dt: self.update_date(), 300)  # 5 min
    
    def start_clock(self, dt):
        """УПРОЩЁННЫЙ запуск часов"""
        try:
            # Update clock immediately
            self.update_clock(None)
            
            # Start clock timer
            self._clock_ev = Clock.schedule_interval(self.update_clock, 1)
            logger.info("Clock started")
            
        except Exception as e:
            logger.error(f"Error starting clock: {e}")
    
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

    def update_clock(self, dt):
        """УПРОЩЁННОЕ обновление часов"""
        try:
            now = datetime.now().strftime("%H:%M")
            
            # Update clock widgets if they exist
            if hasattr(self, 'ids') and self.ids:
                if hasattr(self.ids, 'clock_label') and self.ids.clock_label:
                    self.ids.clock_label.text = now
                
                if hasattr(self.ids, 'clock_shadow_label') and self.ids.clock_shadow_label:
                    self.ids.clock_shadow_label.text = now
                    
        except Exception as e:
            logger.error(f"Error updating clock: {e}")

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
    
    def on_leave(self):
        """УПРОЩЁННАЯ очистка при выходе с экрана"""
        logger.info("Leaving HomeScreen")
        
        # Stop all timers
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
                except Exception as e:
                    logger.error(f"Error canceling {timer_name}: {e}")
                finally:
                    setattr(self, timer_name, None)