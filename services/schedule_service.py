import requests, json, os, time
from datetime import datetime, timedelta
class ScheduleService:
    def __init__(self, path="config/schedule.json"):
        self.path = path
        self.schedule = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.schedule = json.load(f)
        else:
            self.schedule = {str(d): [] for d in range(1,8)}
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.schedule, f, ensure_ascii=False, indent=2)

    def add_lesson(self, day, lesson):
        self.schedule[str(day)].append(lesson)
        self.save()
