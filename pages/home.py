from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime

class HomeScreen(MDScreen):
    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self.post_init(), 0)

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
