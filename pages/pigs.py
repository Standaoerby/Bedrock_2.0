from kivymd.uix.screen import MDScreen
from kivy.clock import Clock

class PigsScreen(MDScreen):
    def on_enter(self):
        self.update_bars()
        self._clock_ev = Clock.schedule_interval(lambda dt: self.update_bars(), 60)  # обновление каждые 60 сек

    def on_leave(self):
        if hasattr(self, "_clock_ev"):
            self._clock_ev.cancel()

    def update_bars(self):
        app = self.get_app()
        vals, integral = app.pigs_service.get_all_values()
        # Update progress bars
        self.ids.water_bar.value = vals["water"]
        self.ids.food_bar.value = vals["food"]
        self.ids.clean_bar.value = vals["clean"]
        
        # Update status display
        percent = int(integral * 100)
        
        # Select emoji based on status percentage
        if percent == 0:
            status_emoji = "💀"  # Dead
        elif 1 <= percent < 25:
            status_emoji = "😨"  # Very worried
        elif 25 <= percent < 50:
            status_emoji = "☹️"  # Sad
        elif 50 <= percent < 75:
            status_emoji = "🙂"  # Slightly happy
        elif 75 <= percent < 100:
            status_emoji = "😀"  # Happy
        else:
            status_emoji = "🐷"  # Perfect
        
        # Update emoji and status text
        self.ids.status_emoji.text = status_emoji
        self.ids.pigs_status_label.text = f"Status: {percent}%"

    def reset_bar(self, key):
        app = self.get_app()
        app.pigs_service.reset_bar(key)
        self.update_bars()

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()