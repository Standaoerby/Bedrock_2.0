"""
NotificationService — append-only list of dated notes (for the home-screen
marquee + future inbox UI). Each entry: time / text / category / read.
Stored as a top-level JSON list.
"""
import logging
from datetime import datetime

from services._jsonstore import JsonStore

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, path: str = "config/notifications.json"):
        self._store = JsonStore(path, list, logger=logger)
        self.notifications: list = []
        self.load()

    def load(self) -> None:
        data = self._store.load()
        if not isinstance(data, list):
            logger.warning(f"unexpected notifications.json shape ({type(data).__name__}); starting empty")
            data = []
        self.notifications = data

    def save(self) -> None:
        self._store.save(self.notifications)

    # ── CRUD ──────────────────────────────────────────────────────────
    def add(self, text: str, category: str, time: str | None = None) -> None:
        if time is None:
            time = datetime.now().isoformat(timespec="minutes")
        self.notifications.append({
            "time": time,
            "text": text,
            "category": category,
            "read": False,
        })
        self.save()

    def list_unread(self) -> list:
        return [n for n in self.notifications if not n.get("read", False)]

    def list_all(self, reverse: bool = True) -> list:
        return list(reversed(self.notifications)) if reverse else self.notifications

    def mark_as_read(self, idx: int) -> None:
        if 0 <= idx < len(self.notifications):
            self.notifications[idx]["read"] = True
            self.save()

    def remove(self, idx: int) -> None:
        if 0 <= idx < len(self.notifications):
            del self.notifications[idx]
            self.save()

    def clear_all(self) -> None:
        self.notifications = []
        self.save()

    def get_last_notification(self) -> dict | None:
        return self.notifications[-1] if self.notifications else None
