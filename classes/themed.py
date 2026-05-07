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
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
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
    """Themed label. If color_role is empty, the per-instance color set
    via KV is respected (no override). Same for size_role / font_size."""
    color_role = StringProperty("")  # empty = don't touch color
    size_role = StringProperty("")   # empty = don't touch font_size

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
        if self.color_role:
            self.color = _color_for(cfg, self.color_role)
        if self.size_role:
            self.font_size = _font_size_for(cfg, self.size_role)


class ThemedButton(Button, _ThemeBound):
    color_role = StringProperty("")
    size_role = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(color_role=lambda *_: self._refresh(),
                  size_role=lambda *_: self._refresh())
        # Drop the Kivy 9-patch atlas so background_color isn't tinted
        # by it — colors come straight from theme.colors.button_bg.
        self.background_normal = ""
        self.background_down = ""
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        colors = cfg.get("colors", {}) or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        if self.color_role:
            self.color = _color_for(cfg, self.color_role)
        if self.size_role:
            self.font_size = _font_size_for(cfg, self.size_role)
        # Themed flat bg + pressed state — both required for dark mode
        # readability where Kivy's white default would make font_default
        # (cream) text invisible.
        self.background_color = colors.get("button_bg", [1, 1, 1, 1])


class ThemedToggleButton(ToggleButton, _ThemeBound):
    """ToggleButton that picks up font_name + size + color from theme,
    AND replaces Kivy's default blue/grey atlas with theme-driven flat
    colours (active → 'active' role, normal → 'inactive' role).

    Same opt-in pattern as ThemedButton (color_role / size_role) for the
    text. background_color is recomputed when state flips.
    """
    color_role = StringProperty("")
    size_role = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(color_role=lambda *_: self._refresh(),
                  size_role=lambda *_: self._refresh(),
                  state=lambda *_: self._refresh())
        # Drop the atlas so background_color isn't tinted by Kivy's
        # default 9-patch blue/grey artwork.
        self.background_normal = ""
        self.background_down = ""
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        if self.color_role:
            self.color = _color_for(cfg, self.color_role)
        if self.size_role:
            self.font_size = _font_size_for(cfg, self.size_role)
        # Flat themed background — active when toggled down.
        colors = cfg.get("colors", {}) or {}
        if self.state == "down":
            self.background_color = colors.get("active", [0.3, 0.7, 0.4, 1])
        else:
            self.background_color = colors.get("inactive", [0.65, 0.67, 0.72, 1])


class ThemedTextInput(TextInput, _ThemeBound):
    """TextInput that picks up font_name + font_size from the active theme.

    KV expressions like `font_name: app.theme_config.get("font_name", ...)`
    are *supposed* to re-evaluate when DictProperty reassigns, but in
    practice the .get() chain doesn't always fire — especially after the
    first dispatch on a fresh dict. Doing it from Python via
    `_ThemeBound._bind_theme` is reliable.

    `size_role` selects the font_sizes key (default "medium").
    """
    size_role = StringProperty("medium")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(size_role=lambda *_: self._refresh())
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        colors = cfg.get("colors", {}) or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        if self.size_role:
            self.font_size = _font_size_for(cfg, self.size_role)
        # Themed input: bg + text color so dark mode doesn't render a
        # white box with invisible text. Cursor + selection use accent.
        self.background_color = colors.get("input_bg", [1, 1, 1, 1])
        self.foreground_color = colors.get("font_default", [0, 0, 0, 1])
        primary = colors.get("primary", [0.4, 0.6, 0.9, 1])
        self.cursor_color = primary
        self.selection_color = (primary[0], primary[1], primary[2], 0.3)


class ShadowLabel(Label, _ThemeBound):
    """Drop-shadow Label for the clock. Reads font_name + huge font_size
    from the active theme; chooses shadow color based on theme_mode
    (light → shadow_light, dark → shadow_dark).

    Plain `<Label>` in KV with `font_name: app.theme_config.get(...)`
    didn't reliably re-fire on theme switch, so this lives in Python.
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self._bind_theme()
        # Mode flips dispatch the shadow color too.
        app = App.get_running_app()
        if app is not None:
            app.bind(theme_mode=lambda *_: self._refresh())

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        self.font_size = _font_size_for(cfg, "huge", "160sp")
        colors = cfg.get("colors", {}) or {}
        if app.theme_mode == "dark":
            self.color = colors.get("shadow_dark", [1, 1, 1, 0.35])
        else:
            self.color = colors.get("shadow_light", [0, 0, 0, 0.5])


class ScreenOverlay(Image, _ThemeBound):
    """Per-screen decorative image. The actual texture path comes from
    `theme_config["overlay_images"][page_key]`.

    Why a Python class instead of `<ScreenOverlay@Image>` in KV: the KV
    binding `app.theme_config.get("overlay_images", {}).get(...)` is a
    chained .get() through a DictProperty and doesn't reliably re-fire
    on theme switch. With Python-side binding we explicitly reassign
    `source` (and `opacity`) on every theme reload, so switching from
    minecraft → clean actually drops the old texture.
    """
    page_key = StringProperty("")

    def __init__(self, **kw):
        kw.setdefault("fit_mode", "fill")
        kw.setdefault("size_hint", (1, 1))
        kw.setdefault("pos_hint", {"center_x": 0.5, "center_y": 0.5})
        super().__init__(**kw)
        self.bind(page_key=lambda *_: self._refresh())
        self._bind_theme()

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        overlays = cfg.get("overlay_images", {}) or {}
        new_source = overlays.get(self.page_key, "") if self.page_key else ""
        # Always reassign so Image notices an empty-string transition and
        # drops the old texture.
        self.source = new_source
        # overlay_opacity from theme.json controls how strongly the
        # decorative artwork shows through panels. Default 0.5 is a
        # compromise — text on top of panels stays readable but the art
        # still reads as decoration. Themes can override per-mood.
        # 0 only when the theme has no overlay for this page.
        if new_source:
            self.opacity = float(cfg.get("overlay_opacity", 0.5))
        else:
            self.opacity = 0.0


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


class ThemedSpinnerOption(SpinnerOption):
    """Spinner dropdown row. Default Kivy SpinnerOption uses system font
    at 15sp with a fixed 44px height — looks foreign next to our pixel
    Minecraftia. This subclass pulls font_name / font_size / color /
    height / button background from theme_config."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._refresh()
        app = App.get_running_app()
        if app is not None:
            app.bind(theme_config=lambda *_: self._refresh())

    def _refresh(self, *_):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        colors = cfg.get("colors", {}) or {}
        layout = cfg.get("layout", {}) or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        self.font_size = _font_size_for(cfg, "medium", "22sp")
        self.color = _color_for(cfg, "font_default")
        self.background_normal = ""
        self.background_down = ""
        self.background_color = colors.get("button_bg", [1, 1, 1, 1])
        # 48 dp default height, configurable via layout.widget_height_md
        self.height = layout.get("widget_height_md", 48)


class ThemedSpinner(Spinner, _ThemeBound):
    """Spinner with a themed dropdown — uses ThemedSpinnerOption rows.
    The Spinner button itself reads color_role / size_role like
    ThemedButton.

    Fixes the open-then-immediately-close bug on touchscreens: Kivy's
    default Spinner toggles the dropdown on `on_release`, so the very
    same touch's release event can land on the freshly-opened DropDown's
    auto-dismiss handler and shut it down. We override _toggle_dropdown
    to schedule the actual `is_open = True` one frame later — by then
    the originating touch is fully consumed.
    """

    color_role = StringProperty("")
    size_role = StringProperty("")

    def __init__(self, **kw):
        # Inject our option class before super().__init__ so the first
        # dropdown opening uses it.
        kw.setdefault("option_cls", ThemedSpinnerOption)
        super().__init__(**kw)
        self.bind(color_role=lambda *_: self._refresh(),
                  size_role=lambda *_: self._refresh())
        self._pending_open = None
        self._bind_theme()

    def _toggle_dropdown(self, *_):
        # If a deferred open is in flight, cancelling here lets a fast
        # double-tap (open then close inside 150ms) actually keep the
        # spinner closed — without the cancel, the scheduled is_open=True
        # would fire after the close path and reopen the dropdown.
        if self._pending_open is not None:
            self._pending_open.cancel()
            self._pending_open = None

        # Closing is fine to do synchronously.
        if self.is_open:
            self.is_open = False
            return
        # Opening: defer ~150ms so the originating touch event chain
        # (down/move/up + any debounce duplicates from MTD) is fully
        # consumed before the DropDown is mapped — otherwise a tap
        # registered after-the-open lands on auto_dismiss.
        self._pending_open = Clock.schedule_once(self._do_open, 0.15)

    def _do_open(self, _dt):
        self._pending_open = None
        self.is_open = True

    def _refresh(self):
        app = App.get_running_app()
        if app is None:
            return
        cfg = app.theme_config or {}
        colors = cfg.get("colors", {}) or {}
        self.font_name = cfg.get("font_name", _DEFAULT_FONT_NAME)
        if self.color_role:
            self.color = _color_for(cfg, self.color_role)
        if self.size_role:
            self.font_size = _font_size_for(cfg, self.size_role)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = colors.get("button_bg", [1, 1, 1, 1])
