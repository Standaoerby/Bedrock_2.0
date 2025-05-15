import json
import os
from datetime import datetime

class NotificationService:
    def __init__(self, path="config/notifications.json"):
        self.path = path
        self.notifications = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.notifications = json.load(f)
        else:
            self.notifications = []
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.notifications, f, ensure_ascii=False, indent=2)

    def add(self, text, category, time=None):
        """Добавить уведомление"""
        if time is None:
            time = datetime.now().isoformat(timespec='minutes')
        note = {
            "time": time,           # строка, например 2024-05-15T16:25
            "text": text,           # строка уведомления
            "category": category,   # "экстра", "школьный", "системный" и т.д.
            "read": False
        }
        self.notifications.append(note)
        self.save()

    def list_unread(self):
        """Список всех НЕпрочитанных уведомлений"""
        return [n for n in self.notifications if not n.get("read", False)]

    def list_all(self, reverse=True):
        """Список всех уведомлений (по умолчанию — последние сверху)"""
        if reverse:
            return list(reversed(self.notifications))
        return self.notifications

    def mark_as_read(self, idx):
        """Пометить уведомление как прочитанное по индексу"""
        if 0 <= idx < len(self.notifications):
            self.notifications[idx]["read"] = True
            self.save()

    def remove(self, idx):
        """Удалить уведомление по индексу"""
        if 0 <= idx < len(self.notifications):
            del self.notifications[idx]
            self.save()

    def clear_all(self):
        """Удалить все уведомления"""
        self.notifications = []
        self.save()

    def get_last_notification(self):
        if self.notifications:
            return self.notifications[-1]
        return None
