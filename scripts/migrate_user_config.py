"""Migrate config/user_config.json (0.5.5) → config/user.json (2.0).

One-shot. Reads the old config, builds the 2.0 shape, merges with an
existing user.json (so unknown keys aren't clobbered), backs up
overwrites with a timestamp suffix. Splits the nested `alarm` block
into config/alarm.json (the 2.0 schema keeps alarm separate).

Usage:
    python scripts/migrate_user_config.py [--dry-run] [<old_path>]

Default <old_path> is config/user_config.json. Pass `--no-alarm` to
skip the alarm.json half.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_OLD = Path("config/user_config.json")
NEW_USER = Path("config/user.json")
NEW_ALARM = Path("config/alarm.json")


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"failed to read {path}: {e}", file=sys.stderr)
        return None


def migrate_user(old: dict) -> dict:
    """Build the 2.0 user.json shape from a 0.5.5 user_config.json."""
    new: dict = {}
    if "theme" in old:
        new["theme"] = old["theme"]
    # variant → theme_mode (0.5.5 used "variant", 2.0 uses "theme_mode")
    if "variant" in old:
        new["theme_mode"] = old["variant"]
    if "username" in old:
        new["username"] = old["username"]
    # birthday → birthdate
    if "birthday" in old:
        new["birthdate"] = old["birthday"]
    if "language" in old:
        new["language"] = old["language"]
    # auto_theme_enabled (bool) → auto_theme_strategy ("ldr" / "off").
    # If 0.5.5 had it on, default to ldr (sensor was the original
    # path). Astral is a 2.0-only option — not auto-selected here.
    if "auto_theme_strategy" in old:
        new["auto_theme_strategy"] = old["auto_theme_strategy"]
    elif "auto_theme_enabled" in old:
        new["auto_theme_strategy"] = "ldr" if old["auto_theme_enabled"] else "off"
    if "light_sensor_threshold" in old:
        try:
            new["light_sensor_threshold"] = int(old["light_sensor_threshold"])
        except (TypeError, ValueError):
            pass
    # location.{latitude,longitude} → top-level lat/lon (2.0 weather
    # service reads these from user.json directly).
    loc = old.get("location") or {}
    if "latitude" in loc:
        try:
            new["lat"] = float(loc["latitude"])
        except (TypeError, ValueError):
            pass
    if "longitude" in loc:
        try:
            new["lon"] = float(loc["longitude"])
        except (TypeError, ValueError):
            pass
    return new


def migrate_alarm(old: dict) -> Optional[dict]:
    """Split the nested 0.5.5 `alarm: {enabled, time, days}` into the
    standalone alarm.json shape. Returns None if no alarm section."""
    src = old.get("alarm")
    if not isinstance(src, dict):
        return None
    return {
        "enabled": bool(src.get("enabled", False)),
        "time": src.get("time", "07:30"),
        # 0.5.5 used "days", 2.0 uses "repeat" — accept either as input.
        "repeat": src.get("repeat", src.get("days", [])),
        "ringtone": src.get("ringtone", "morning.mp3"),
        "fadein": bool(src.get("fadein", False)),
    }


def _write_with_backup(target: Path, payload: dict, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would write {target}:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = target.with_suffix(target.suffix + f".{ts}.bak")
        shutil.copy2(target, backup)
        print(f"backup: {backup}")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"wrote {target}")


def main() -> int:
    p = argparse.ArgumentParser(description="Migrate 0.5.5 user_config.json → 2.0 user.json")
    p.add_argument("old", nargs="?", default=str(DEFAULT_OLD))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-alarm", action="store_true", help="skip writing alarm.json")
    args = p.parse_args()

    old_path = Path(args.old)
    old = _load(old_path)
    if old is None:
        print(f"no old config at {old_path}", file=sys.stderr)
        return 1

    user_patch = migrate_user(old)
    existing = _load(NEW_USER) or {}
    # Merge direction: existing.update(user_patch) — values from the old
    # 0.5.5 config OVERRIDE the existing 2.0 user.json for keys the old
    # config sets. 2.0-only keys absent from the old config (e.g.
    # temp_offset, humidity_offset, theme_mode if not migrated from
    # `variant`) are preserved untouched. This is the desired direction
    # for "migrate from old config": migration is the source of truth
    # for any key the old config provides.
    existing.update(user_patch)
    _write_with_backup(NEW_USER, existing, args.dry_run)

    if not args.no_alarm:
        alarm_payload = migrate_alarm(old)
        if alarm_payload:
            existing_alarm = _load(NEW_ALARM) or {}
            existing_alarm.update(alarm_payload)
            _write_with_backup(NEW_ALARM, existing_alarm, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
