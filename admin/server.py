"""Flask app for the Bedrock 2.0 admin UI.

Single-file route registry — kept flat for the prototype. Split into
blueprints when it gets unwieldy.

Run:
    python -m admin.server
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, redirect, url_for, request, session, flash,
    jsonify, send_file, abort,
)

from . import auth, actions
from . import bedrock_state as state
from .config_io import read_json, write_json
from .paths import (
    CONFIG_DIR, THEMES_DIR, CACHE_DIR,
    USER_CONFIG, ALARM_CONFIG, SCHEDULE_CONFIG, PIGS_CONFIG,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = auth.get_secret_key()
    # Long sessions are fine — admin is local-only.
    app.permanent_session_lifetime = 60 * 60 * 24 * 7

    # ── Auth ──────────────────────────────────────────────────────────

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not auth.has_any_user():
            flash("No admin user configured. Run "
                  "`python -m admin.cli set-password admin` on the Pi.",
                  "error")
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            if auth.verify(username, password):
                session.permanent = True
                session["user"] = username
                return redirect(request.args.get("next") or url_for("dashboard"))
            flash("Invalid credentials", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("user", None)
        return redirect(url_for("login"))

    # ── Dashboard ─────────────────────────────────────────────────────

    @app.route("/")
    @auth.login_required
    def dashboard():
        user_cfg = read_json(USER_CONFIG, default={})
        return render_template(
            "dashboard.html",
            service=state.service_status(),
            weather=state.weather_snapshot(),
            sensors=state.sensors_snapshot(),
            user=user_cfg,
            alarm=read_json(ALARM_CONFIG, default={}),
            themes=_list_themes(),
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    # ── Themes ────────────────────────────────────────────────────────

    @app.route("/themes")
    @auth.login_required
    def themes():
        return render_template(
            "themes.html",
            themes=_list_themes(),
            current=read_json(USER_CONFIG, default={}),
        )

    @app.route("/themes/apply", methods=["POST"])
    @auth.login_required
    def themes_apply():
        theme = request.form.get("theme")
        mode = request.form.get("mode", "light")
        auto = request.form.get("auto_dark_mode") == "on"
        if not _theme_exists(theme, mode):
            flash(f"Theme '{theme}/{mode}' not found", "error")
            return redirect(url_for("themes"))
        cfg = read_json(USER_CONFIG, default={})
        cfg["theme"] = theme
        cfg["theme_mode"] = mode
        cfg["auto_dark_mode"] = auto
        write_json(USER_CONFIG, cfg)
        flash(f"Theme set to {theme}/{mode} — restart Bedrock to apply.", "success")
        return redirect(url_for("themes"))

    # ── Alarm ─────────────────────────────────────────────────────────

    @app.route("/alarm", methods=["GET", "POST"])
    @auth.login_required
    def alarm():
        if request.method == "POST":
            cfg = read_json(ALARM_CONFIG, default={})
            cfg["time"] = request.form.get("time", cfg.get("time", "07:00"))
            cfg["active"] = request.form.get("active") == "on"
            cfg["fade_in"] = request.form.get("fade_in") == "on"
            cfg["ringtone"] = request.form.get("ringtone", cfg.get("ringtone", ""))
            days = request.form.getlist("repeat")
            cfg["repeat"] = days
            write_json(ALARM_CONFIG, cfg)
            flash("Alarm saved", "success")
            return redirect(url_for("alarm"))
        return render_template(
            "alarm.html",
            alarm=read_json(ALARM_CONFIG, default={}),
            ringtones=_list_ringtones(),
        )

    # ── Settings (user.json) ──────────────────────────────────────────

    @app.route("/settings", methods=["GET", "POST"])
    @auth.login_required
    def settings():
        if request.method == "POST":
            cfg = read_json(USER_CONFIG, default={})
            cfg["username"] = request.form.get("username", cfg.get("username", ""))
            cfg["birthdate"] = request.form.get("birthdate", cfg.get("birthdate", ""))
            try:
                cfg["lat"] = float(request.form.get("lat") or cfg.get("lat", 51.539))
                cfg["lon"] = float(request.form.get("lon") or cfg.get("lon", -0.1426))
                cfg["temp_offset"] = float(request.form.get("temp_offset") or cfg.get("temp_offset", 0))
                cfg["humidity_offset"] = float(request.form.get("humidity_offset") or cfg.get("humidity_offset", 0))
            except ValueError:
                flash("Numeric fields must be numeric", "error")
                return redirect(url_for("settings"))
            write_json(USER_CONFIG, cfg)
            flash("Settings saved — sensor service picks up the new offsets on its next poll (~30s)", "success")
            return redirect(url_for("settings"))
        return render_template(
            "settings.html",
            user=read_json(USER_CONFIG, default={}),
            sensors=state.sensors_snapshot(),
        )

    # ── Schedule (raw JSON editor for the prototype) ──────────────────

    @app.route("/schedule", methods=["GET", "POST"])
    @auth.login_required
    def schedule():
        if request.method == "POST":
            raw = request.form.get("raw_json", "")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                flash(f"Invalid JSON: {e}", "error")
                return render_template("schedule.html", raw=raw)
            write_json(SCHEDULE_CONFIG, parsed)
            flash("Schedule saved", "success")
            return redirect(url_for("schedule"))
        cur = read_json(SCHEDULE_CONFIG, default={})
        return render_template(
            "schedule.html",
            raw=json.dumps(cur, ensure_ascii=False, indent=2),
        )

    # ── Pigs ──────────────────────────────────────────────────────────

    @app.route("/pigs", methods=["GET", "POST"])
    @auth.login_required
    def pigs():
        if request.method == "POST":
            cfg = read_json(PIGS_CONFIG, default={})
            for key in ("water", "food", "clean"):
                val = request.form.get(key)
                if val is not None:
                    try:
                        cfg[key] = max(0.0, min(1.0, float(val)))
                    except ValueError:
                        pass
            write_json(PIGS_CONFIG, cfg)
            flash("Pigs saved", "success")
            return redirect(url_for("pigs"))
        return render_template("pigs.html", pigs=read_json(PIGS_CONFIG, default={}))

    # ── Actions ───────────────────────────────────────────────────────

    @app.route("/actions/restart", methods=["POST"])
    @auth.login_required
    def action_restart():
        ok, msg = actions.restart_bedrock()
        flash(msg, "success" if ok else "error")
        return redirect(request.referrer or url_for("dashboard"))

    @app.route("/actions/screenshot", methods=["POST"])
    @auth.login_required
    def action_screenshot():
        ok, msg, _ = actions.take_screenshot()
        flash(msg, "success" if ok else "error")
        return redirect(request.referrer or url_for("dashboard"))

    @app.route("/actions/screen/<name>", methods=["POST"])
    @auth.login_required
    def action_switch_screen(name):
        ok, msg = actions.switch_screen(name)
        flash(msg, "success" if ok else "error")
        return redirect(request.referrer or url_for("dashboard"))

    @app.route("/screenshot.png")
    @auth.login_required
    def screenshot_image():
        # Capture on demand so the dashboard always shows fresh.
        actions.take_screenshot()
        path = CACHE_DIR / "admin_screenshot.png"
        if not path.exists():
            abort(404)
        return send_file(path, mimetype="image/png", max_age=0)

    # ── Read-only API ─────────────────────────────────────────────────

    @app.route("/api/status")
    @auth.login_required
    def api_status():
        return jsonify({
            "service": state.service_status(),
            "weather": state.weather_snapshot(),
            "user": read_json(USER_CONFIG, default={}),
            "alarm": read_json(ALARM_CONFIG, default={}),
        })

    return app


# ── Helpers ───────────────────────────────────────────────────────────

def _list_themes() -> list[dict]:
    """Return [{name, has_light, has_dark}, ...] for non-template themes."""
    if not THEMES_DIR.exists():
        return []
    out = []
    for entry in sorted(THEMES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        out.append({
            "name": entry.name,
            "has_light": (entry / "light" / "theme.json").exists(),
            "has_dark": (entry / "dark" / "theme.json").exists(),
        })
    return out


def _theme_exists(theme: str | None, mode: str) -> bool:
    if not theme or mode not in ("light", "dark"):
        return False
    return (THEMES_DIR / theme / mode / "theme.json").exists()


def _list_ringtones() -> list[str]:
    rings = (Path(__file__).resolve().parent.parent / "media" / "ringtones")
    if not rings.exists():
        return []
    return sorted(p.name for p in rings.iterdir()
                  if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".ogg"))


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8080, debug=False)
