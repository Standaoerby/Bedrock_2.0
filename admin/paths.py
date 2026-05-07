"""Single source of truth for filesystem paths shared between admin
modules. Kept tiny so it imports cleanly anywhere."""
from pathlib import Path

# admin/ -> repo root
ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = ROOT / "config"
THEMES_DIR = ROOT / "themes"
CACHE_DIR = ROOT / "cache"
LOGS_DIR = ROOT / "logs"

ADMIN_CONFIG = CONFIG_DIR / "admin.json"
USER_CONFIG = CONFIG_DIR / "user.json"
ALARM_CONFIG = CONFIG_DIR / "alarm.json"
SCHEDULE_CONFIG = CONFIG_DIR / "schedule.json"
PIGS_CONFIG = CONFIG_DIR / "pigs.json"
WEATHER_CACHE = CACHE_DIR / "weather.json"
