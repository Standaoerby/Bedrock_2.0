"""
OverflowColumn — vertical column that becomes scrollable when its content
overflows.

Drop-in replacement for `BoxLayout(orientation='vertical')` in places where
content height isn't bounded by the layout: long schedules, sensor lists
that may grow, settings forms that get bigger on themes with large fonts.

Behavior:
- When `inner_minimum_height <= height`, behaves like a plain BoxLayout —
  scrollbar is hidden, no scroll possible (effective_disable).
- When content overflows, a thin scrollbar appears and vertical scroll
  is enabled.

KV usage:

    OverflowColumn:
        spacing: app.ui_metrics["spacing_sm"]
        padding: app.ui_metrics["padding_md"]

        ThemedLabel:
            text: "..."
        ThemedLabel:
            text: "..."

`spacing` and `padding` set on the OverflowColumn are forwarded to the
internal BoxLayout — they don't apply to the ScrollView outer frame.

Children added via add_widget() are routed to the inner BoxLayout.
clear_widgets() clears the inner BoxLayout. self.ids inside KV reach
through to the inner widgets transparently because Kivy assigns ids on
the visited widgets, not on this wrapper.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import NumericProperty, VariableListProperty


class OverflowColumn(ScrollView):
    spacing = NumericProperty(0)
    # VariableListProperty so KV `padding: 4` and `padding: [4, 8]` both
    # expand to a 4-element list, matching BoxLayout's own behavior.
    padding = VariableListProperty([0, 0, 0, 0], length=4)

    def __init__(self, **kw):
        # Forward layout-related kwargs to the inner BoxLayout instead of
        # the ScrollView frame.
        inner_spacing = kw.pop("spacing", 0)
        inner_padding = kw.pop("padding", [0, 0, 0, 0])
        super().__init__(**kw)
        # Vertical-only scroll, thin bar.
        self.do_scroll_x = False
        self.do_scroll_y = True
        self.bar_width = 4
        self.bar_color = (0.5, 0.5, 0.5, 0.55)
        self.bar_inactive_color = (0.5, 0.5, 0.5, 0.0)
        self.scroll_type = ["bars", "content"]

        self._inner = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=inner_spacing,
            padding=inner_padding,
        )
        # Inner expands vertically with its content; ScrollView decides
        # whether scrolling is needed based on inner.height vs self.height.
        self._inner.bind(minimum_height=self._inner.setter("height"))
        super().add_widget(self._inner)

        # Keep external setters wired to the inner box so KV/Python edits
        # land where they're visible.
        self.spacing = inner_spacing
        self.padding = list(inner_padding) if isinstance(inner_padding, (list, tuple)) else [inner_padding] * 4
        self.bind(spacing=self._sync_spacing, padding=self._sync_padding)

    def _sync_spacing(self, _instance, value):
        self._inner.spacing = value

    def _sync_padding(self, _instance, value):
        self._inner.padding = value

    # Route children to the inner BoxLayout so KV sub-widgets land in the
    # scrollable area, not on the ScrollView itself (which only accepts
    # one viewport child).
    def add_widget(self, widget, *args, **kwargs):
        if widget is self._inner:
            super().add_widget(widget, *args, **kwargs)
        else:
            self._inner.add_widget(widget, *args, **kwargs)

    def remove_widget(self, widget):
        if widget is self._inner:
            super().remove_widget(widget)
        else:
            self._inner.remove_widget(widget)

    def clear_widgets(self, children=None):
        if children is None:
            self._inner.clear_widgets()
        else:
            self._inner.clear_widgets(children=children)
