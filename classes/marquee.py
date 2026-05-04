from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Translate
from kivy.properties import NumericProperty, StringProperty


class MarqueeLabel(Label):
    """Horizontally-scrolling label.

    The transform is set up once via PushMatrix/Translate/PopMatrix wrapping the
    label's own canvas — only Translate.x is mutated on every animation tick, so
    we don't allocate or rebuild graphics instructions per frame.

    Picks up font_name + font_size + color from app.theme_config via a
    Python-side binding (the KV `app.theme_config.get(...)` chain doesn't
    reliably re-fire after a theme switch).
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

        app = App.get_running_app()
        if app is not None:
            app.bind(theme_config=lambda *_: self._apply_theme())
            self._apply_theme()

    def _apply_theme(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        self.font_name = cfg.get("font_name", "Minecraftia")
        sizes = cfg.get("font_sizes", {}) or {}
        self.font_size = sizes.get("medium", "20sp")
        colors = cfg.get("colors", {}) or {}
        self.color = colors.get("font_default", [1, 1, 1, 1])

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
