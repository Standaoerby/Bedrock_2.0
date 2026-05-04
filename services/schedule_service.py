"""
ScheduleService — weekly lesson schedule persisted to JSON.

Stored as `{"1": [lesson, ...], "2": [...], ..., "7": [...]}` keyed by ISO
weekday number (1=Monday, 7=Sunday). load() guarantees every key 1..7
exists so add_lesson() never KeyErrors on a fresh install.
"""
import logging

from services._jsonstore import JsonStore

logger = logging.getLogger(__name__)


def _empty_week() -> dict:
    return {str(d): [] for d in range(1, 8)}


class ScheduleService:
    def __init__(self, path: str = "config/schedule.json"):
        self._store = JsonStore(path, _empty_week, logger=logger)
        self.schedule: dict = {}
        self.load()

    def load(self) -> None:
        data = self._store.load()
        if not isinstance(data, dict):
            logger.warning(f"unexpected schedule.json shape ({type(data).__name__}); resetting")
            data = _empty_week()
        # Ensure every day key exists so add_lesson never KeyErrors.
        for k, v in _empty_week().items():
            data.setdefault(k, v)
        self.schedule = data

    def save(self) -> None:
        self._store.save(self.schedule)

    def add_lesson(self, day, lesson) -> None:
        self.schedule[str(day)].append(lesson)
        self.save()
