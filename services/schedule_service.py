import json, os
import logging

logger = logging.getLogger("ScheduleService")


class ScheduleService:
    def __init__(self, path="config/schedule.json"):
        self.path = path
        self.schedule = {}
        self.load()

    def load(self):
        defaults = {str(d): [] for d in range(1, 8)}
        if not os.path.exists(self.path):
            self.schedule = defaults
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.schedule = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"schedule.json unreadable ({e}); using defaults")
            self.schedule = defaults
        # Ensure every day key exists so add_lesson never KeyErrors
        for k, v in defaults.items():
            self.schedule.setdefault(k, v)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.schedule, f, ensure_ascii=False, indent=2)

    def add_lesson(self, day, lesson):
        self.schedule[str(day)].append(lesson)
        self.save()
