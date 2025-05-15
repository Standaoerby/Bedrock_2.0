from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty

class HomeScreen(MDScreen):

    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")  # "↑" or "↓" or ""
    notification_text = StringProperty("")

    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self.post_init(), 0)
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        Clock.schedule_interval(lambda dt: self.update_alarm(), 60)
        Clock.schedule_interval(lambda dt: self.update_weather(), 180)
        Clock.schedule_interval(lambda dt: self.update_notification(), 10)
    def update_alarm(self):
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.current_alarm_time = alarm.get("time", "--:--")
            self.alarm_active = alarm.get("enabled", False)
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False

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
            # Trend
            try:
                temp_now = float(now.get("temperature", 0))
                temp_5h = float(f5.get("temperature", 0))
                if temp_5h > temp_now:
                    self.weather_trend_arrow = "↑"
                elif temp_5h < temp_now:
                    self.weather_trend_arrow = "↓"
                else:
                    self.weather_trend_arrow = ""
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
        print("IDS HomeScreen (post):", self.ids)  # теперь всегда НЕ пустой
        self.update_clock()
        self._clock_ev = Clock.schedule_interval(lambda dt: self.update_clock(), 1)


    def on_leave(self):
        # Останавливаем таймер при уходе со страницы
        if hasattr(self, '_clock_ev'):
            self._clock_ev.cancel()

    def update_clock(self):
        now = datetime.now().strftime("%H:%M")
        self.ids.clock_label.text = now
