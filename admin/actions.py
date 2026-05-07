"""Side-effecting operations triggered from the admin UI: restart the
panel service, take a screenshot, etc. Kept separate so route handlers
stay thin and these can be unit-tested in isolation."""
from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .bedrock_state import is_pi
from .paths import CACHE_DIR


def restart_bedrock() -> tuple[bool, str]:
    """Restart the Kivy panel service. Returns (ok, message)."""
    if not is_pi():
        return False, "restart only available on Pi"
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", "bedrock.service"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return True, "bedrock restarted"
        return False, result.stderr.strip() or "restart returned non-zero"
    except (subprocess.SubprocessError, OSError) as e:
        return False, str(e)


def take_screenshot() -> tuple[bool, str, Optional[Path]]:
    """Capture the current panel screen via xdotool + ImageMagick's
    `import`. Returns (ok, message, path-on-disk-if-any).

    Saves to cache/admin_screenshot.png so subsequent calls overwrite.
    """
    if not is_pi():
        return False, "screenshot only available on Pi", None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / "admin_screenshot.png"
    env = {
        **os.environ,
        "DISPLAY": ":0",
        "XAUTHORITY": "/home/pi/.Xauthority",
    }
    try:
        wid = subprocess.run(
            ["xdotool", "getactivewindow"],
            env=env, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if not wid:
            return False, "no active window", None
        result = subprocess.run(
            ["import", "-window", wid, str(out_path)],
            env=env, capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or "import failed", None
        return True, "screenshot saved", out_path
    except (subprocess.SubprocessError, OSError) as e:
        return False, str(e), None


def switch_screen(screen_name: str) -> tuple[bool, str]:
    """Press the F-key that maps to a Bedrock screen.
    F1=home F2=alarm F3=schedule F4=weather F5=pigs F6=settings."""
    keymap = {
        "home": "F1", "alarm": "F2", "schedule": "F3",
        "weather": "F4", "pigs": "F5", "settings": "F6",
    }
    key = keymap.get(screen_name)
    if not key:
        return False, f"unknown screen: {screen_name}"
    if not is_pi():
        return False, "screen switch only on Pi"
    env = {
        **os.environ,
        "DISPLAY": ":0",
        "XAUTHORITY": "/home/pi/.Xauthority",
    }
    try:
        wid = subprocess.run(
            ["xdotool", "getactivewindow"],
            env=env, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if not wid:
            return False, "no active window", None
        subprocess.run(
            ["xdotool", "key", "--window", wid, key],
            env=env, capture_output=True, timeout=5,
        )
        # Give the screen change a moment to settle
        time.sleep(0.4)
        return True, f"switched to {screen_name}"
    except (subprocess.SubprocessError, OSError) as e:
        return False, str(e)
