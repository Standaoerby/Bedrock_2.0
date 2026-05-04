"""
Themed widgets for Bedrock 2.0 — pure Kivy replacements for the
<ThemedLabel@Label>/<ThemedButton@Button>/<ThemedPanel@BoxLayout> KV
template rules.

Per-instance colors and font sizes are honored. Theme reload re-paints
through the Python `_refresh` method (one-direction binding from
app.theme_config → widget). KV bindings on instances are not fought.

`color_role` selects which entry in `theme_config["colors"]` to use.
`size_role` selects which entry in `theme_config["font_sizes"]` to use.

Default values fall through cleanly when the theme dict doesn't have
the requested key.
"""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty


_DEFAULT_COLOR = [1, 1, 1, 1]
_DEFAULT_FONT_SIZE = "20sp"
_DEFAULT_FONT_NAME = "Minecraftia"


def _color_for(theme_config, role, fallback=None):
    """Resolve color_role → rgba list. role can be a key in theme_config['colors']
    or a top-level key (font_color, etc)."""
    if not theme_config:
        return fallback or _DEFAULT_COLOR
    colors = theme_config.get("colors", {}) or {}
    if role in colors:
        return colors[role]
    # Fallback to top-level theme color (e.g. font_color)
    if role in theme_config:
        return theme_config[role]
    if "font_color" in theme_config:
        return theme_config["font_color"]
    return fallback or _DEFAULT_COLOR


def _font_size_for(theme_config, role, fallback=None):
    if not theme_config:
        return fallback or _DEFAULT_FONT_SIZE
    sizes = theme_config.get("font_sizes", {}) or {}
    return sizes.get(role, fallback or _DEFAULT_FONT_SIZE)


class _ThemeBound:
    """Mixin: bind to app.theme_config and call self._refresh on change.
    Subclasses provide _refresh()."""

    def _bind_theme(self):
        app = App.get_running_app()
        if app is None:
            return  # building before App.run() — KV will dispatch later
        app.bind(theme_config=lambda *_: self._refresh())
        self._refresh()


class ThemedLabel(Label, _ThemeBound):
    color_role = StringProperty("font_default")
    size_role = StringProperty("default")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(color_role=lambda *_: self._refresh(),
                  size_role=lambda *_: self._refresh())
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        self.color = _color_for(cfg, self.color_role)
        self.font_size = _font_size_for(cfg, self.size_role)


class ThemedButton(Button, _ThemeBound):
    color_role = StringProperty("font_default")
    size_role = StringProperty("default")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(color_role=lambda *_: self._refresh(),
                  size_role=lambda *_: self._refresh())
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        self.color = _color_for(cfg, self.color_role)
        self.font_size = _font_size_for(cfg, self.size_role)
        self.background_normal = cfg.get("button_normal", "")
        self.background_down = cfg.get("button_active", cfg.get("button_normal", ""))


class ThemedPanel(BoxLayout, _ThemeBound):
    """BoxLayout with themed rounded background. Use panel_bg + panel_radius
    from theme.json."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._bg_color = None
        self._bg_rect = None
        self.bind(pos=lambda *_: self._update_geometry(),
                  size=lambda *_: self._update_geometry())
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        rgba = cfg.get("panel_bg", [0, 0, 0, 0.2])
        radius = cfg.get("panel_radius", 16)

        self.canvas.before.clear()
        with self.canvas.before:
            self._bg_color = Color(*rgba)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])

    def _update_geometry(self):
        if self._bg_rect is not None:
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size
