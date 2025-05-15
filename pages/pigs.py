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
        self.ids.water_bar.value = vals["water"]
        self.ids.food_bar.value = vals["food"]
        self.ids.clean_bar.value = vals["clean"]
        # Интегральный статус
        percent = int(integral * 100)
        if percent == 0:
            status = "💀"
        elif 1 <= percent < 25:
            status = "😨"
        elif 25 <= percent < 50:
            status = "☹️"
        elif 50 <= percent < 75:
            status = "🙂"
        elif 75 <= percent < 100:
            status = "😀"
        else:
            status = "🐷"
        self.ids.pigs_status_label.text = f"Статус: {status} ({percent}%)"

    def reset_bar(self, key):
        app = self.get_app()
        app.pigs_service.reset_bar(key)
        self.update_bars()

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
