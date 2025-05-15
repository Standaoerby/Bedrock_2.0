import json
import os
from datetime import datetime, timedelta

class PigsService:
    def __init__(self, path="config/pigs.json"):
        self.path = path
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            # Стартовые значения
            now = datetime.now().replace(microsecond=0).isoformat()
            self.data = {
                "pigs": [{"name": "Пятачок"}, {"name": "Фунтик"}],
                "bars": {
                    "water": {"label": "Вода", "max_hours": 8, "last_reset": now},
                    "food":  {"label": "Еда",  "max_hours": 6, "last_reset": now},
                    "clean": {"label": "Очистка", "max_hours": 12, "last_reset": now}
                }
            }
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_bar_value(self, key):
        bar = self.data["bars"][key]
        max_s = bar["max_hours"] * 3600
        last = datetime.fromisoformat(bar["last_reset"])
        now = datetime.now()
        passed = (now - last).total_seconds()
        value = max(0.0, 1.0 - passed / max_s)
        return value

    def get_all_values(self):
        vals = {k: self.get_bar_value(k) for k in self.data["bars"]}
        integral = sum(vals.values()) / len(vals)
        return vals, integral

    def reset_bar(self, key):
        self.data["bars"][key]["last_reset"] = datetime.now().replace(microsecond=0).isoformat()
        self.save()
