from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty

class HomeScreen(MDScreen):
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")  # "↑", "↓", or "="
    notification_text = StringProperty("")
    current_date = StringProperty("")
    current_day = StringProperty("")

    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self.post_init(), 0)
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        self.update_date()

        # Schedule regular updates — track them so on_leave can cancel
        self._intervals = [
            Clock.schedule_interval(lambda dt: self.update_alarm(), 300),
            Clock.schedule_interval(lambda dt: self.update_weather(), 900),
            Clock.schedule_interval(lambda dt: self.update_notification(), 30),
            Clock.schedule_interval(lambda dt: self.update_date(), 300),
        ]
    
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
        
    def post_init(self):
        print("IDS HomeScreen (post):", self.ids)
        self.update_clock()
        self._clock_ev = Clock.schedule_interval(lambda dt: self.update_clock(), 1)

    def on_leave(self):
        # Cancel the clock and any periodic updaters scheduled in on_pre_enter
        if hasattr(self, '_clock_ev'):
            self._clock_ev.cancel()
        for ev in getattr(self, '_intervals', []):
            try:
                ev.cancel()
            except Exception:
                pass
        self._intervals = []

    def update_clock(self):
        now = datetime.now().strftime("%H:%M")
        self.ids.clock_label.text = now