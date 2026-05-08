import json
import os
from datetime import datetime
from kivy.properties import (
    StringProperty,
    ListProperty,
    NumericProperty,
)

from classes.base_screen import BaseScreen


USER_CONFIG = "config/user.json"
AUTO_THEME_STRATEGIES = ["off", "ldr", "astral"]


class SettingsScreen(BaseScreen):
    page_key = StringProperty("settings")

    current_theme = StringProperty("minecraft")
    available_themes = ListProperty([])
    username = StringProperty("")
    birth_day = StringProperty("")
    birth_month = StringProperty("")
    birth_year = StringProperty("")
    language = StringProperty("en")
    available_languages = ListProperty(["en", "ru"])
    auto_theme_strategy = StringProperty("off")
    auto_theme_strategies = ListProperty(AUTO_THEME_STRATEGIES)
    auto_theme_status = StringProperty("")
    light_sensor_threshold = NumericProperty(3)
    current_volume = NumericProperty(50)
    volume_backend = StringProperty("")

    def do_on_pre_enter(self):
        self.scan_available_themes()
        self.load_settings()
        self._load_available_languages()
        self.refresh_auto_theme_status()
        self.refresh_volume_status()
        # 2s tick for live LDR status, 1s for volume — BaseScreen cancels on leave.
        self.add_interval(self.refresh_auto_theme_status, 2)
        self.add_interval(self.refresh_volume_status, 1)

    def scan_available_themes(self):
        themes = []
        try:
            for entry in os.listdir("themes"):
                # Skip hidden / template folders (e.g. _template).
                if entry.startswith((".", "_")):
                    continue
                p = os.path.join("themes", entry)
                if os.path.isdir(p) and (
                    os.path.exists(os.path.join(p, "light"))
                    or os.path.exists(os.path.join(p, "dark"))
                ):
                    themes.append(entry)
        except (OSError, FileNotFoundError):
            pass
        self.available_themes = sorted(themes) if themes else ["minecraft"]

    def load_settings(self):
        if not os.path.exists(USER_CONFIG):
            return
        try:
            with open(USER_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        self.current_theme = cfg.get("theme", "minecraft")
        self.username = cfg.get("username", "")
        self.language = cfg.get("language", "en")
        # Strategy: prefer the new key, fall back to legacy auto_dark_mode
        # bool that the admin UI used to write before this feature landed.
        if "auto_theme_strategy" in cfg:
            strategy = cfg.get("auto_theme_strategy", "off")
        else:
            strategy = "ldr" if cfg.get("auto_dark_mode") else "off"
        self.auto_theme_strategy = strategy if strategy in AUTO_THEME_STRATEGIES else "off"
        self.light_sensor_threshold = int(cfg.get("light_sensor_threshold", 3))
        birthdate = cfg.get("birthdate", "")
        if birthdate:
            try:
                d = datetime.strptime(birthdate, "%Y-%m-%d")
                self.birth_year = str(d.year)
                self.birth_month = str(d.month)
                self.birth_day = str(d.day)
            except ValueError:
                self.birth_year = self.birth_month = self.birth_day = ""

    def _load_available_languages(self):
        app = self.get_app()
        if app and hasattr(app, "translator"):
            self.available_languages = app.translator.available_languages()

    def save_all_settings(self):
        if "username_input" in self.ids:
            self.username = self.ids.username_input.text
        self.update_birthdate()

        os.makedirs("config", exist_ok=True)
        existing = {}
        if os.path.exists(USER_CONFIG):
            try:
                with open(USER_CONFIG, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = {}
        # theme_mode is owned by AutoThemeService (or admin web UI) — Settings
        # page no longer writes it. Keeping the existing value in user.json so
        # auto-strategy "off" still resolves to a sensible mode at startup.
        existing.update({
            "theme": self.current_theme,
            "username": self.username,
            "birthdate": self.get_birthdate_string(),
            "language": self.language,
            "auto_theme_strategy": self.auto_theme_strategy,
            "light_sensor_threshold": int(self.light_sensor_threshold),
        })
        try:
            with open(USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"settings save failed: {e}")
            return

        app = self.get_app()
        if app and hasattr(app, "apply_theme"):
            # Re-render with the currently active mode (auto-theme's choice
            # or the persisted one) — no manual override from Settings.
            app.apply_theme(self.current_theme, app.theme_mode, persist=False)

    def change_theme(self, theme):
        if theme == self.current_theme:
            return
        self.current_theme = theme
        app = self.get_app()
        if app and hasattr(app, "apply_theme"):
            app.apply_theme(theme, app.theme_mode)

    def change_language(self, language):
        if not language or language == self.language:
            return
        if language not in self.available_languages:
            return
        self.language = language
        app = self.get_app()
        if app and hasattr(app, "set_language"):
            app.set_language(language)

    def change_auto_theme_strategy(self, strategy):
        if strategy not in AUTO_THEME_STRATEGIES:
            return
        if strategy == self.auto_theme_strategy:
            return
        self.auto_theme_strategy = strategy
        app = self.get_app()
        ats = getattr(app, "auto_theme_service", None) if app else None
        if ats is not None:
            ats.set_strategy(strategy)
        self.refresh_auto_theme_status()

    def change_threshold(self, value):
        try:
            new = max(1, min(int(value), 10))
        except (TypeError, ValueError):
            return
        if new == self.light_sensor_threshold:
            return
        self.light_sensor_threshold = new
        app = self.get_app()
        ats = getattr(app, "auto_theme_service", None) if app else None
        if ats is not None:
            ats.set_threshold(new)

    def volume_up(self):
        app = self.get_app()
        vs = getattr(app, "volume_service", None) if app else None
        if vs is not None:
            vs.step_up()

    def volume_down(self):
        app = self.get_app()
        vs = getattr(app, "volume_service", None) if app else None
        if vs is not None:
            vs.step_down()

    def refresh_volume_status(self):
        app = self.get_app()
        vs = getattr(app, "volume_service", None) if app else None
        if vs is None:
            return
        status = vs.status()
        self.current_volume = status["volume"]
        self.volume_backend = status["backend"]

    def refresh_auto_theme_status(self):
        app = self.get_app()
        ats = getattr(app, "auto_theme_service", None) if app else None
        if ats is None:
            self.auto_theme_status = ""
            return
        s = ats.status()
        strategy = s.get("strategy", "off")
        if strategy == "off":
            self.auto_theme_status = "Off"
        elif strategy == "astral":
            self.auto_theme_status = s.get("description", "astral")
        elif strategy == "ldr":
            backend = s.get("backend", "none")
            light = s.get("current_light")
            light_str = "—" if light is None else ("light" if light else "dark")
            self.auto_theme_status = f"LDR · {backend} · now: {light_str}"
        else:
            self.auto_theme_status = strategy

    def update_birthdate(self):
        if not all(k in self.ids for k in ("birth_day", "birth_month", "birth_year")):
            return
        try:
            d = int(self.ids.birth_day.text.strip())
            m = int(self.ids.birth_month.text.strip())
            y = int(self.ids.birth_year.text.strip())
        except ValueError:
            return
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100:
            self.birth_day, self.birth_month, self.birth_year = str(d), str(m), str(y)

    def get_birthdate_string(self):
        try:
            d = int(self.birth_day) if self.birth_day else 1
            m = int(self.birth_month) if self.birth_month else 1
            y = int(self.birth_year) if self.birth_year else 2000
            return f"{y:04d}-{m:02d}-{d:02d}"
        except (TypeError, ValueError):
            return "2000-01-01"
