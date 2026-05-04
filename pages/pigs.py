import os
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, ColorProperty, StringProperty
from kivy.graphics import Color, Rectangle

from classes.base_screen import BaseScreen


class CustomProgressBar(BoxLayout):
    """Simple horizontal bar drawn directly on the canvas. value 0..100,
    bar_color rgba."""
    value = NumericProperty(50)
    bar_color = ColorProperty([0, 0.6, 0.8, 1])

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            self.bg_color = Color(0.2, 0.2, 0.2, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            self.fg_color = Color(*self.bar_color)
            self.fg_rect = Rectangle(pos=self.pos, size=(0, 0))
        self.bind(size=self._redraw, pos=self._redraw,
                  value=self._redraw, bar_color=self._redraw)

    def _redraw(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.fg_color.rgba = self.bar_color
        self.fg_rect.pos = self.pos
        self.fg_rect.size = (self.width * (self.value / 100.0), self.height)


class PigsScreen(BaseScreen):
    page_key = StringProperty("pigs")

    def do_on_pre_enter(self):
        self.update_bars()
        # Bars change slowly — refresh every 20 minutes is plenty.
        self.add_interval(self.update_bars, 20 * 60)

    def update_bars(self):
        vals, integral = self.get_app().pigs_service.get_all_values()
        if "water_bar" in self.ids:
            self.ids.water_bar.value = vals["water"]
        if "food_bar" in self.ids:
            self.ids.food_bar.value = vals["food"]
        if "clean_bar" in self.ids:
            self.ids.clean_bar.value = vals["clean"]

        percent = int(integral * 100)
        self._update_pigs_image(percent)

    def _update_pigs_image(self, percent):
        if 85 <= percent <= 100:
            image_file = "pigs_1.png"
        elif 50 <= percent < 85:
            image_file = "pigs_2.png"
        elif 20 <= percent < 50:
            image_file = "pigs_3.png"
        else:
            image_file = "pigs_4.png"
        image_path = os.path.join("assets", "images", image_file)
        if "pigs_image" in self.ids and os.path.exists(image_path):
            self.ids.pigs_image.source = image_path

    def reset_bar(self, key):
        self.get_app().pigs_service.reset_bar(key)
        self.update_bars()
