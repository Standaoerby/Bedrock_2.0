"""Auto-theme service — picks light/dark variant from a strategy.

Three strategies, one runtime selector:

- "ldr"     LDR on BCM 12 via SensorService.read_light_level(). Polls
            every LDR_INTERVAL_SEC, requires `threshold` consecutive
            stable readings of the new state before switching, so a
            cloud or shadow doesn't cause a flicker.
- "astral"  astronomical sunrise/sunset for the location stored in
            user.json (lat/lon defaults: Camden, London). Polls once a
            minute — the granularity of the input is itself minutes, so
            no point checking faster.
- "off"     no-op. Manual variant control via Settings/admin only.

Switching is non-persisting: app.apply_theme(..., persist=False) so the
config keeps the user's last *manual* choice. Otherwise auto would
overwrite theme_mode every minute and the manual toggle would be
defeated on next start.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Protocol

from kivy.clock import Clock

from app.events import event_bus

logger = logging.getLogger(__name__)

LDR_INTERVAL_SEC = 2.0
ASTRAL_INTERVAL_SEC = 60.0
DEFAULT_LDR_THRESHOLD = 3  # samples in a row before flip


class _Strategy(Protocol):
    def check(self) -> Optional[str]:
        """Return 'light' / 'dark' / None (None = strategy can't decide)."""


class OffStrategy:
    name = "off"
    interval = ASTRAL_INTERVAL_SEC  # arbitrary — never fires a switch

    def check(self) -> Optional[str]:
        return None


class LDRStrategy:
    name = "ldr"
    interval = LDR_INTERVAL_SEC

    def __init__(self, sensor_service) -> None:
        self.sensor = sensor_service

    def check(self) -> Optional[str]:
        level = self.sensor.read_light_level()
        if level is None:
            return None
        return "light" if level else "dark"


class AstralStrategy:
    name = "astral"
    interval = ASTRAL_INTERVAL_SEC

    def __init__(self, lat: float, lon: float, tz: str = "UTC") -> None:
        # Imported lazily so a missing astral install only breaks the
        # astral strategy, not LDR / off.
        from astral import LocationInfo
        self.location = LocationInfo("custom", "custom", tz, lat, lon)
        self._cached_for: Optional[str] = None
        self._cached_sun: Optional[dict] = None

    def _sun_for_today(self) -> dict:
        from astral.sun import sun
        today = datetime.now().astimezone().date().isoformat()
        if today != self._cached_for or self._cached_sun is None:
            self._cached_sun = sun(self.location.observer, date=datetime.now().date())
            self._cached_for = today
        return self._cached_sun

    def check(self) -> Optional[str]:
        try:
            s = self._sun_for_today()
        except Exception as e:
            logger.warning(f"astral sun calc failed: {e}")
            return None
        now = datetime.now(s["sunrise"].tzinfo)
        return "light" if s["sunrise"] <= now <= s["sunset"] else "dark"

    def describe(self) -> str:
        try:
            s = self._sun_for_today()
            return (
                f"Sunrise {s['sunrise'].astimezone().strftime('%H:%M')} · "
                f"Sunset {s['sunset'].astimezone().strftime('%H:%M')}"
            )
        except Exception:
            return "astral data unavailable"


class AutoThemeService:
    """Owns the active strategy and the Kivy Clock event that drives it.

    Lives on the Kivy main thread — no extra threading layer. That keeps
    GPIO access serialised with the rest of the panel and avoids the
    GPIO-double-claim race that bit the 1.0.x branch (see RECOVERY.md)."""

    VALID_STRATEGIES = {"off", "ldr", "astral"}

    def __init__(self, app) -> None:
        self.app = app
        self._strategy: _Strategy = OffStrategy()
        self._strategy_name: str = "off"
        self._event = None
        self._threshold = DEFAULT_LDR_THRESHOLD
        # Threshold tracking for LDR — reset on strategy change.
        self._stable_target: Optional[str] = None
        self._stable_count: int = 0

    def _build(self, name: str) -> Optional[_Strategy]:
        if name == "off":
            return OffStrategy()
        if name == "ldr":
            sensor = getattr(self.app, "sensor_service", None)
            if sensor is None or not hasattr(sensor, "read_light_level"):
                logger.warning("ldr strategy requested but sensor_service unavailable")
                return None
            return LDRStrategy(sensor)
        if name == "astral":
            prefs = self.app.user_prefs()
            lat = float(prefs.get("lat", 51.5390))
            lon = float(prefs.get("lon", -0.1426))
            try:
                return AstralStrategy(lat, lon)
            except Exception as e:
                logger.warning(f"astral strategy unavailable: {e}")
                return None
        return None

    def set_strategy(self, name: str, *, persist: bool = True) -> bool:
        if name not in self.VALID_STRATEGIES:
            logger.warning(f"unknown auto-theme strategy: {name}")
            return False
        new = self._build(name)
        if new is None:
            return False
        # Cancel previous polling event before swapping
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self._strategy = new
        self._strategy_name = name
        self._stable_target = None
        self._stable_count = 0
        if name != "off":
            self._event = Clock.schedule_interval(self._tick, new.interval)
            # First check immediately so manual toggle takes effect now,
            # not after one full interval.
            Clock.schedule_once(self._tick, 0.1)
        if persist:
            self.app._persist_user_pref("auto_theme_strategy", name)
        logger.info(f"auto-theme strategy set: {name}")
        event_bus.publish("auto_theme_strategy_changed", {"strategy": name})
        return True

    def set_threshold(self, threshold: int) -> None:
        self._threshold = max(1, min(int(threshold), 10))

    def _tick(self, _dt) -> None:
        target = self._strategy.check()
        if target is None:
            return
        # No-op if already in target mode — but reset stable counter so
        # the next genuine flip starts fresh.
        if target == self.app.theme_mode:
            self._stable_target = None
            self._stable_count = 0
            return
        if self._strategy_name == "ldr":
            if target == self._stable_target:
                self._stable_count += 1
            else:
                self._stable_target = target
                self._stable_count = 1
            if self._stable_count < self._threshold:
                return
        # Apply without persisting — manual mode preference stays the
        # source of truth in user.json.
        if self.app.apply_theme(self.app.theme_name, target, persist=False):
            logger.info(
                f"auto-theme switched: {self.app.theme_mode} "
                f"(strategy={self._strategy_name}, target={target})"
            )
            event_bus.publish("theme_changed", {
                "theme": self.app.theme_name,
                "mode": target,
                "auto": True,
                "strategy": self._strategy_name,
            })
        self._stable_target = None
        self._stable_count = 0

    def status(self) -> dict:
        out = {
            "strategy": self._strategy_name,
            "running": self._event is not None,
        }
        if isinstance(self._strategy, AstralStrategy):
            out["description"] = self._strategy.describe()
        elif isinstance(self._strategy, LDRStrategy):
            sensor = getattr(self.app, "sensor_service", None)
            if sensor is not None and hasattr(sensor, "get_light_status"):
                out.update(sensor.get_light_status())
        return out

    def stop(self) -> None:
        if self._event is not None:
            self._event.cancel()
            self._event = None
