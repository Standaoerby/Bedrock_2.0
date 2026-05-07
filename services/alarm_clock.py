"""
AlarmClock — periodic check (every CHECK_INTERVAL_SEC, default 30) that
fires AlarmPopup when the configured time matches and today's day-of-week
is in the repeat list.

Dedupe via `_last_trigger_key = "<date> <HH:MM>"` so the 30-second polling
cadence never fires the same alarm twice within a single minute window.
The dedupe key intentionally survives popup dismissal — clearing it would
let the next tick re-fire immediately. The minute boundary clears it
naturally.

Snooze: a one-shot scheduled trigger N minutes in the future. Skips the
day-of-week / time match (it's a deliberate user action), but reuses
trigger_alarm() so the same popup + ringtone path runs. Cleared on any
fresh popup or stop_alarm().
"""
import logging
from datetime import datetime

from kivy.clock import Clock

from classes.alarm_popup import AlarmPopup

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SEC = 30
DEFAULT_SNOOZE_MINUTES = 5


class AlarmClock:
    def __init__(self, app, check_interval: int = CHECK_INTERVAL_SEC):
        self.app = app
        self.check_interval = check_interval
        self.alarm_event = None
        self.active_popup = None
        self._last_trigger_key: str | None = None
        self._snooze_event = None

    def start(self) -> None:
        self.alarm_event = Clock.schedule_interval(self.check_alarm, self.check_interval)
        logger.info("alarm clock started")

    def stop(self) -> None:
        if self.alarm_event:
            self.alarm_event.cancel()
            self.alarm_event = None
        logger.info("alarm clock stopped")

    def check_alarm(self, _dt) -> None:
        now = datetime.now()
        date_today = now.date()
        day_short = now.strftime("%a")           # Mon / Tue / ...
        time_str = now.strftime("%H:%M")

        alarm = self.app.alarm_service.get_alarm()
        if not alarm:
            return

        if not alarm.get("enabled", False):
            return
        if time_str != alarm.get("time", ""):
            return
        if day_short not in alarm.get("repeat", []):
            return

        minute_key = f"{date_today} {time_str}"
        if minute_key == self._last_trigger_key:
            return  # already fired this minute
        self._last_trigger_key = minute_key

        ringtone = alarm.get("ringtone", "morning.mp3")
        fadein = alarm.get("fadein", False)
        logger.info(f"alarm triggered time={time_str} day={day_short} ringtone={ringtone}")
        self.trigger_alarm(ringtone, fadein)

    def trigger_alarm(self, ringtone: str, fadein: bool) -> None:
        if self.active_popup:
            logger.debug("trigger_alarm: popup already active, skipping")
            return
        try:
            self.active_popup = AlarmPopup(ringtone=ringtone, fadein=fadein)
            self.active_popup.bind(on_dismiss=self._on_popup_dismiss)
            self.active_popup.on_snooze = lambda minutes=DEFAULT_SNOOZE_MINUTES: self.snooze(minutes)
            self.active_popup.open()
            self.active_popup.start_alarm()
            logger.info(f"alarm popup opened ringtone={ringtone} fadein={fadein}")
        except Exception:
            # Broad except is justified here: a popup-construction crash
            # mustn't break the whole alarm-checking interval. We log the
            # traceback and clear active_popup so the next tick can retry.
            logger.exception("trigger_alarm crashed")
            self.active_popup = None

    def _on_popup_dismiss(self, _instance) -> None:
        self.active_popup = None

    def stop_alarm(self) -> None:
        if self._snooze_event is not None:
            self._snooze_event.cancel()
            self._snooze_event = None
        if self.active_popup:
            self.active_popup.stop_alarm()
            self.active_popup = None

    def snooze(self, minutes: int = DEFAULT_SNOOZE_MINUTES) -> None:
        """Dismiss the current popup and re-fire the alarm in `minutes`.
        Cancels any in-flight snooze first so repeated taps don't stack."""
        # Resolve ringtone/fadein from the alarm config — popup may
        # already be tearing down by the time the snooze timer fires.
        alarm = self.app.alarm_service.get_alarm() if self.app.alarm_service else None
        ringtone = (alarm or {}).get("ringtone", "morning.mp3")
        fadein = (alarm or {}).get("fadein", False)

        if self._snooze_event is not None:
            self._snooze_event.cancel()
            self._snooze_event = None
        if self.active_popup:
            self.active_popup.stop_alarm()
            self.active_popup = None

        delay = max(1, int(minutes)) * 60
        logger.info(f"alarm snoozed for {minutes}min (ringtone={ringtone})")

        def _wake(_dt):
            self._snooze_event = None
            self.trigger_alarm(ringtone, fadein)

        self._snooze_event = Clock.schedule_once(_wake, delay)
