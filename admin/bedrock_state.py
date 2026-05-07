"""Read-only snapshots of the running Bedrock service / state.

The admin UI displays sensors/weather/service status by reading the
same on-disk artifacts Bedrock writes (cache/, config/) plus shelling
out to systemctl. We don't import services/sensor_service or
WeatherService here — they hold I2C handles + worker threads that
shouldn't be duplicated by the admin process.
"""
from __future__ import annotations
import platform
import subprocess
from typing import Optional

from .config_io import read_json
from .paths import WEATHER_CACHE, CACHE_DIR

SENSORS_CACHE = CACHE_DIR / "sensors.json"


def is_pi() -> bool:
    return platform.system() != "Windows"


def service_status() -> dict:
    """Returns a small dict describing bedrock.service. On Windows
    (dev) returns a synthetic 'inactive' so the dashboard renders."""
    if not is_pi():
        return {
            "active": False,
            "uptime": "n/a (dev)",
            "since": "",
            "platform": "Windows",
        }
    try:
        active = subprocess.run(
            ["systemctl", "--user", "is-active", "bedrock.service"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        since = subprocess.run(
            ["systemctl", "--user", "show", "bedrock.service",
             "-p", "ActiveEnterTimestamp", "--value"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return {
            "active": active == "active",
            "raw_status": active,
            "since": since,
            "platform": "linux",
        }
    except (subprocess.SubprocessError, OSError) as e:
        return {"active": False, "error": str(e), "platform": "linux"}


def weather_snapshot() -> dict:
    """Latest weather payload as cached by WeatherService."""
    return read_json(WEATHER_CACHE, default={})


def sensors_snapshot() -> dict:
    """Latest sensor reading as written by SensorService to
    cache/sensors.json on every poll. Includes both raw and
    offset-corrected temperature/humidity so the calibration UI can
    show 'sensor sees X, you see X+offset'."""
    return read_json(SENSORS_CACHE, default={}) or {}
