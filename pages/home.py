from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty

from classes.base_screen import BaseScreen


class HomeScreen(BaseScreen):
    page_key = StringProperty("home")

    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")  # "↑" / "↓" / "="
    notification_text = StringProperty("")
    current_date = StringProperty("")

    def do_on_pre_enter(self):
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        self.update_date()
        # First clock update + 1s tick — 250ms delay so root.ids is populated
        self.schedule_once(self.update_clock, 0.25)
        self.add_interval(self.update_clock, 1)
        # Periodic updates — auto-cancelled in BaseScreen.on_leave
        self.add_interval(self.update_alarm, 300)
        self.add_interval(self.update_weather, 900)
        self.add_interval(self.update_notification, 30)
        self.add_interval(self.update_date, 300)

    def update_clock(self):
        now = datetime.now().strftime("%H:%M")
        if "clock_label" in self.ids:
            self.ids.clock_label.text = now

    def update_date(self):
        self.current_date = datetime.now().strftime("%d %B, %A")

    def update_alarm(self):
        alarm = self.get_app().alarm_service.get_alarm()
        if alarm:
            self.current_alarm_time = alarm.get("time", "--:--")
            self.alarm_active = alarm.get("enabled", False)
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False

    def toggle_alarm(self):
        app = self.get_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            alarm["enabled"] = not alarm.get("enabled", False)
            app.alarm_service.set_alarm(alarm)
            self.update_alarm()
            if alarm["enabled"]:
                app.play_sound("success")

    def update_weather(self):
        w = self.get_app().weather_service.get_weather()
        now = w.get("current", {})
        f5 = w.get("forecast_5h", {})
        if now:
            self.weather_now_str = f'{now.get("temperature", "--")}°C {now.get("condition", "")}'
        else:
            self.weather_now_str = ""
        if f5:
            self.weather_5h_str = f'{f5.get("temperature", "--")}°C in 5h'
            try:
                t_now = float(now.get("temperature", 0))
                t_5h = float(f5.get("temperature", 0))
                if t_5h > t_now:
                    self.weather_trend_arrow = "↑"
                elif t_5h < t_now:
                    self.weather_trend_arrow = "↓"
                else:
                    self.weather_trend_arrow = "="
            except (TypeError, ValueError):
                self.weather_trend_arrow = ""
        else:
            self.weather_5h_str = ""
            self.weather_trend_arrow = ""

    def update_notification(self):
        notifications = self.get_app().notification_service.notifications
        if notifications:
            last = sorted(notifications, key=lambda n: n.get("time", ""))[-1]
            self.notification_text = last.get("text", "")
        else:
            self.notification_text = ""
