import json
import os
from datetime import datetime
from kivy.properties import StringProperty, BooleanProperty, ListProperty

from classes.base_screen import BaseScreen


USER_CONFIG = "config/user.json"


class SettingsScreen(BaseScreen):
    page_key = StringProperty("settings")

    current_theme = StringProperty("minecraft")
    available_themes = ListProperty([])
    dark_mode_enabled = BooleanProperty(False)
    dark_mode_available = BooleanProperty(False)
    username = StringProperty("")
    birth_day = StringProperty("")
    birth_month = StringProperty("")
    birth_year = StringProperty("")

    def do_on_pre_enter(self):
        self.scan_available_themes()
        self.load_settings()
        self.check_dark_mode_availability()

    def scan_available_themes(self):
        themes = []
        try:
            for entry in os.listdir("themes"):
                p = os.path.join("themes", entry)
                if os.path.isdir(p) and (
                    os.path.exists(os.path.join(p, "light"))
                    or os.path.exists(os.path.join(p, "dark"))
                ):
                    themes.append(entry)
        except (OSError, FileNotFoundError):
            pass
        self.available_themes = themes if themes else ["minecraft"]

    def check_dark_mode_availability(self):
        dark_path = os.path.join("themes", self.current_theme, "dark")
        self.dark_mode_available = os.path.isdir(dark_path)

    def load_settings(self):
        if not os.path.exists(USER_CONFIG):
            return
        try:
            with open(USER_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        self.current_theme = cfg.get("theme", "minecraft")
        self.dark_mode_enabled = cfg.get("theme_mode", "light") == "dark"
        self.username = cfg.get("username", "")
        birthdate = cfg.get("birthdate", "")
        if birthdate:
            try:
                d = datetime.strptime(birthdate, "%Y-%m-%d")
                self.birth_year = str(d.year)
                self.birth_month = str(d.month)
                self.birth_day = str(d.day)
            except ValueError:
                self.birth_year = self.birth_month = self.birth_day = ""

    def save_all_settings(self):
        if "username_input" in self.ids:
            self.username = self.ids.username_input.text
        self.update_birthdate()
        mode = "dark" if self.dark_mode_enabled else "light"

        os.makedirs("config", exist_ok=True)
        existing = {}
        if os.path.exists(USER_CONFIG):
            try:
                with open(USER_CONFIG, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = {}
        existing.update({
            "theme": self.current_theme,
            "theme_mode": mode,
            "username": self.username,
            "birthdate": self.get_birthdate_string(),
        })
        try:
            with open(USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"settings save failed: {e}")
            return

        app = self.get_app()
        if app and hasattr(app, "apply_theme"):
            app.apply_theme(self.current_theme, mode, persist=False)

    def change_theme(self, theme):
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self.check_dark_mode_availability()
        if not self.dark_mode_available:
            self.dark_mode_enabled = False
        app = self.get_app()
        if app and hasattr(app, "apply_theme"):
            mode = "dark" if self.dark_mode_enabled else "light"
            app.apply_theme(theme, mode)

    def toggle_dark_mode(self, enabled):
        if not self.dark_mode_available:
            self.dark_mode_enabled = False
            return
        self.dark_mode_enabled = bool(enabled)
        app = self.get_app()
        if app and hasattr(app, "apply_theme"):
            mode = "dark" if self.dark_mode_enabled else "light"
            app.apply_theme(self.current_theme, mode)

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
