import requests, json, os, time
from datetime import datetime, timedelta
class AlarmService:
    def __init__(self, path="config/alarm.json"):
        self.path = path
        self.alarms = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.alarms = json.load(f)
        else:
            self.alarms = []
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.alarms, f, ensure_ascii=False, indent=2)

    def add_alarm(self, alarm):
        self.alarms.append(alarm)
        self.save()

    def update_alarm(self, idx, new_alarm):
        self.alarms[idx] = new_alarm
        self.save()

    def remove_alarm(self, idx):
        del self.alarms[idx]
        self.save()
