from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty

class MarqueeLabel(Label):
    scroll_x = NumericProperty(0)
    full_text = StringProperty("")
    _marquee_ev = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(full_text=self.start_marquee, size=self.start_marquee, texture_size=self.start_marquee)
        self.full_text = self.text

    def start_marquee(self, *args):
        self.scroll_x = 0
        self.text = self.full_text
        if self._marquee_ev:
            self._marquee_ev.cancel()
        # Проверка: нужна ли анимация
        if self.texture_size[0] > self.width:
            self._marquee_ev = Clock.schedule_interval(self._animate, 1/30.)

    def _animate(self, dt):
        self.scroll_x -= 1.5  # Скорость пикс/кадр, можешь поменять
        # Если вся строка ушла влево — сброс
        if abs(self.scroll_x) > self.texture_size[0]:
            self.scroll_x = self.width
        self.canvas.ask_update()

    def on_scroll_x(self, *args):
        self.refresh_text()

    def refresh_text(self):
        # Этот метод просто пересобирает текст при каждом кадре (делает видимость прокрутки)
        # По сути, ты задаёшь отступ по x через canvas.translate
        self.canvas.before.clear()
        with self.canvas.before:
            from kivy.graphics import PushMatrix, Translate
            PushMatrix()
            Translate(self.scroll_x, 0)
        self.canvas.after.clear()
        with self.canvas.after:
            from kivy.graphics import PopMatrix
            PopMatrix()
