"""Volume control service — pipewire `wpctl` + optional GPIO buttons.

Backend resolution at start() time:

- Pi 5 / Trixie: `wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.65` and
  `wpctl get-volume @DEFAULT_AUDIO_SINK@` against the running pipewire-
  pulse session. This is the path actually exposed by the panel; we
  don't fall back to amixer because Trixie's ALSA stack is a pipewire
  shim — talking to it directly fights pipewire.
- Windows / dev: in-memory cache only. The UI still works, but no
  system audio gets touched. Spelling pycaw out as a Windows backend
  isn't worth the dependency for a dev-only nicety.
- Anywhere else: in-memory cache.

Optional GPIO hardware buttons on BCM 23 (volume up) and 24 (volume down)
through `gpiozero.Button`. gpiozero's Pi 5 backend relies on lgpio, which
the sensor service already imports — so we don't double-claim the chip.
Buttons are opt-in: if gpiozero isn't importable (Windows) or button
init fails (no buttons wired) the service still works through the UI.

Step / range: 5% per click, 0–100. Debounce on hardware buttons is
handled by gpiozero's `bounce_time`; the UI is debounced by Kivy itself.
"""
from __future__ import annotations

import logging
import platform
import re
import shutil
import subprocess
from typing import Callable, Optional

from kivy.clock import Clock

from app.events import event_bus

logger = logging.getLogger(__name__)

VOLUME_UP_PIN = 23
VOLUME_DOWN_PIN = 24
DEFAULT_STEP = 5
MIN_VOLUME = 0
MAX_VOLUME = 100
WPCTL_SINK = "@DEFAULT_AUDIO_SINK@"
POLL_INTERVAL_SEC = 5.0  # external changes (admin/wpctl on shell)
BUTTON_BOUNCE_TIME = 0.2

try:
    from gpiozero import Button as _GpioButton  # type: ignore
    _GPIOZERO_AVAILABLE = True
except ImportError:
    _GpioButton = None  # type: ignore
    _GPIOZERO_AVAILABLE = False


class _Backend:
    """Backend protocol — get_percent() and set_percent() round-trip
    system volume in 0..100. None implementations leave system audio
    alone but keep the cached value in sync."""

    name: str = "none"

    def get_percent(self) -> Optional[int]:
        return None

    def set_percent(self, pct: int) -> bool:
        return True


class _CacheBackend(_Backend):
    name = "cache"

    def __init__(self) -> None:
        self._pct = 50

    def get_percent(self) -> int:
        return self._pct

    def set_percent(self, pct: int) -> bool:
        self._pct = pct
        return True


class _WpctlBackend(_Backend):
    name = "wpctl"
    _PARSE = re.compile(r"Volume:\s*([\d.]+)")

    def get_percent(self) -> Optional[int]:
        try:
            out = subprocess.check_output(
                ["wpctl", "get-volume", WPCTL_SINK],
                text=True,
                timeout=2,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return None
        m = self._PARSE.search(out)
        if not m:
            return None
        try:
            return int(round(float(m.group(1)) * 100))
        except ValueError:
            return None

    def set_percent(self, pct: int) -> bool:
        frac = max(0.0, min(pct, 100)) / 100.0
        try:
            subprocess.check_call(
                ["wpctl", "set-volume", WPCTL_SINK, f"{frac:.2f}"],
                timeout=2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            logger.warning(f"wpctl set-volume {pct}%% failed: {e}")
            return False


def _resolve_backend() -> _Backend:
    if platform.system() == "Linux" and shutil.which("wpctl"):
        return _WpctlBackend()
    return _CacheBackend()


class VolumeService:
    def __init__(self, app) -> None:
        self.app = app
        self._backend: _Backend = _CacheBackend()
        self._volume: int = 50
        self._step: int = DEFAULT_STEP
        self._button_up = None
        self._button_down = None
        self._poll_event = None
        self._on_change: Optional[Callable[[int, str], None]] = None

    # ── Lifecycle ─────────────────────────────────────────────────────
    def start(self) -> None:
        self._backend = _resolve_backend()
        # Initial sync: pull current system volume so UI matches reality.
        self._refresh(emit_event=False)
        self._init_buttons()
        # Re-poll periodically so external volume changes (admin web UI,
        # `wpctl` on shell, headphone unplug) reflect in our cache.
        self._poll_event = Clock.schedule_interval(self._refresh, POLL_INTERVAL_SEC)
        logger.info(
            f"volume service started (backend={self._backend.name}, "
            f"buttons={'on' if self._button_up else 'off'}, volume={self._volume}%)"
        )

    def stop(self) -> None:
        if self._poll_event is not None:
            self._poll_event.cancel()
            self._poll_event = None
        for btn in (self._button_up, self._button_down):
            if btn is not None:
                try:
                    btn.close()
                except Exception:
                    pass
        self._button_up = None
        self._button_down = None
        logger.info("volume service stopped")

    # ── GPIO buttons (optional) ───────────────────────────────────────
    def _init_buttons(self) -> None:
        if not _GPIOZERO_AVAILABLE:
            return
        try:
            self._button_up = _GpioButton(
                VOLUME_UP_PIN, pull_up=True, bounce_time=BUTTON_BOUNCE_TIME
            )
            self._button_up.when_pressed = lambda: Clock.schedule_once(
                lambda _dt: self.step_up(), 0
            )
            self._button_down = _GpioButton(
                VOLUME_DOWN_PIN, pull_up=True, bounce_time=BUTTON_BOUNCE_TIME
            )
            self._button_down.when_pressed = lambda: Clock.schedule_once(
                lambda _dt: self.step_down(), 0
            )
            logger.info(
                f"volume buttons ready on BCM {VOLUME_UP_PIN}/{VOLUME_DOWN_PIN}"
            )
        except Exception as e:
            # Hardware not present, pin in use, permission — log and
            # fall back to UI-only control.
            logger.warning(f"volume button init failed: {e}")
            self._button_up = None
            self._button_down = None

    # ── Public API ────────────────────────────────────────────────────
    def get_volume(self) -> int:
        return self._volume

    def set_volume(self, pct: int, source: str = "ui") -> bool:
        new = max(MIN_VOLUME, min(int(pct), MAX_VOLUME))
        if new == self._volume:
            return True
        if not self._backend.set_percent(new):
            return False
        self._volume = new
        self._emit_change(source)
        return True

    def step_up(self) -> None:
        self.set_volume(self._volume + self._step, source="up")

    def step_down(self) -> None:
        self.set_volume(self._volume - self._step, source="down")

    def set_step(self, step: int) -> None:
        self._step = max(1, min(int(step), 50))

    def set_change_callback(self, fn: Optional[Callable[[int, str], None]]) -> None:
        self._on_change = fn

    def status(self) -> dict:
        return {
            "backend": self._backend.name,
            "volume": self._volume,
            "step": self._step,
            "buttons_available": self._button_up is not None,
            "button_pins": {"up": VOLUME_UP_PIN, "down": VOLUME_DOWN_PIN},
        }

    # ── Internals ─────────────────────────────────────────────────────
    def _refresh(self, _dt=None, *, emit_event: bool = True) -> None:
        sys_vol = self._backend.get_percent()
        if sys_vol is None:
            return
        if sys_vol == self._volume:
            return
        self._volume = sys_vol
        if emit_event:
            self._emit_change("external")

    def _emit_change(self, source: str) -> None:
        if self._on_change is not None:
            try:
                self._on_change(self._volume, source)
            except Exception:
                logger.exception("volume change callback failed")
        event_bus.publish("volume_changed", {"volume": self._volume, "source": source})
