from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty, NumericProperty

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
        # Use longer delay for post_init on Pi
        Clock.schedule_once(lambda dt: self.post_init(), 1.0)  # Give more time
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        self.update_date()
        
        # Schedule regular updates
        Clock.schedule_interval(lambda dt: self.update_alarm(), 300)
        Clock.schedule_interval(lambda dt: self.update_weather(), 900)
        Clock.schedule_interval(lambda dt: self.update_notification(), 30)
        Clock.schedule_interval(lambda dt: self.update_date(), 300)
    
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
        print("HomeScreen post_init called")
        self._retry_count = 0
        available_ids = list(self.ids.keys()) if hasattr(self, 'ids') and self.ids else []
        print(f"IDS HomeScreen (post): {available_ids}")
        
        # Give more attempts to initialize the clock
        self._try_init_clock()
        
    def _try_init_clock(self):
        if self._clock_initialized:
            return
            
        available_ids = list(self.ids.keys()) if hasattr(self, 'ids') and self.ids else []
        has_widgets = hasattr(self, 'ids') and self.ids and 'clock_label' in self.ids
        
        if has_widgets:
            print("Clock widgets found, initializing clock")
            # Update the clock immediately
            self.update_clock()
            # Start the regular updates
            self._clock_ev = Clock.schedule_interval(lambda dt: self.update_clock(), 1)
            self._clock_initialized = True
        else:
            self._retry_count += 1
            if self._retry_count <= 10:  # Try 10 times (over 5 seconds)
                print(f"Clock widgets not found (attempt {self._retry_count}/10), retrying... Available: {available_ids}")
                # Schedule another attempt
                Clock.schedule_once(lambda dt: self._try_init_clock(), 0.5)
            else:
                print("Failed to initialize clock after 10 attempts")

    def on_leave(self):
        # Stop the timer when leaving the page
        if hasattr(self, '_clock_ev'):
            self._clock_ev.cancel()

    def update_clock(self):
        now = datetime.now().strftime("%H:%M")
        try:
            if hasattr(self, 'ids') and self.ids and 'clock_label' in self.ids:
                self.ids.clock_label.text = now
                if 'clock_shadow_label' in self.ids:
                    self.ids.clock_shadow_label.text = now
                # Mark as initialized once successful
                self._clock_initialized = True
            elif not self._clock_initialized:
                # Only print warning during initialization
                available_ids = list(self.ids.keys()) if hasattr(self, 'ids') and self.ids else []
                print(f"Warning: Clock widgets not ready yet. Available ids: {available_ids}")
        except Exception as e:
            print(f"Error updating clock: {e}")