"""
AlarmService — single-alarm config persisted to JSON.

The live representation is a flat dict (`time`, `enabled`, `repeat`,
`ringtone`, `fadein`). Older versions of the app wrote a list with one
entry; load() tolerates that shape and migrates to the dict form on the
next save.
"""
import logging

from services._jsonstore import JsonStore

logger = logging.getLogger(__name__)

DEFAULT_ALARM = {
    "time": "07:30",
    "enabled": True,
    "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "ringtone": "morning.mp3",
    "fadein": False,
}


class AlarmService:
    def __init__(self, path: str = "config/alarm.json"):
        self._store = JsonStore(path, lambda: dict(DEFAULT_ALARM), logger=logger)
        self.alarm: dict = {}
        self.load()

    def load(self) -> None:
        data = self._store.load()
        # Tolerate the legacy list-with-one-entry format; everything else
        # falls back to defaults.
        if isinstance(data, dict):
            self.alarm = data
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            self.alarm = data[0]
            logger.info("migrating legacy list-form alarm.json to dict")
            self.save()
        else:
            logger.warning(f"unexpected alarm.json shape ({type(data).__name__}); resetting to defaults")
            self.alarm = dict(DEFAULT_ALARM)
            self.save()

    def save(self) -> None:
        if self._store.save(self.alarm):
            logger.info(f"alarm saved: {self.alarm}")

    def get_alarm(self) -> dict:
        return self.alarm

    def set_alarm(self, alarm: dict) -> None:
        self.alarm = alarm
        self.save()
