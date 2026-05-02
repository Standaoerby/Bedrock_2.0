from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Translate
from kivy.properties import NumericProperty, StringProperty


class MarqueeLabel(Label):
    """Horizontally-scrolling label.

    The transform is set up once via PushMatrix/Translate/PopMatrix wrapping the
    label's own canvas — only Translate.x is mutated on every animation tick, so
    we don't allocate or rebuild graphics instructions per frame.
    """

    scroll_x = NumericProperty(0)
    full_text = StringProperty("")
    _marquee_ev = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            PushMatrix()
            self._translate = Translate(0, 0, 0)
        with self.canvas.after:
            PopMatrix()

        self.bind(
            full_text=self.start_marquee,
            size=self.start_marquee,
            texture_size=self.start_marquee,
        )
        self.full_text = self.text

    def start_marquee(self, *args):
        self.scroll_x = 0
        self.text = self.full_text
        if self._marquee_ev:
            self._marquee_ev.cancel()
            self._marquee_ev = None
        # Only animate when the text is actually wider than the visible area
        if self.texture_size[0] > self.width:
            self._marquee_ev = Clock.schedule_interval(self._animate, 1 / 30.)

    def _animate(self, dt):
        self.scroll_x -= 1.5  # px per frame
        # When the whole string has scrolled off, snap back to the right edge
        if abs(self.scroll_x) > self.texture_size[0]:
            self.scroll_x = self.width

    def on_scroll_x(self, _instance, value):
        # Mutate the existing transform — no canvas rebuild
        self._translate.x = value
