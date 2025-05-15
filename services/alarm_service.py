import json
import os

class AlarmService:
    def __init__(self, path="config/alarm.json"):
        self.path = path
        self.alarm = None
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.alarm = data
                    elif isinstance(data, list) and data:
                        self.alarm = data[0]
                    else:
                        self.create_default_alarm()
            else:
                self.create_default_alarm()
        except Exception as e:
            print(f"Ошибка при загрузке настроек будильника: {e}")
            self.create_default_alarm()

    def create_default_alarm(self):
        self.alarm = {
            "time": "07:30",
            "enabled": True,
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtone": "morning.mp3",
            "fadein": False
        }
        # Убедимся, что директория config существует
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.save()

    def save(self):
        try:
            # Убедимся, что директория config существует
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.alarm, f, ensure_ascii=False, indent=2)
            print(f"Будильник успешно сохранен: {self.alarm}")
        except Exception as e:
            print(f"Ошибка при сохранении настроек будильника: {e}")

    def get_alarm(self):
        return self.alarm

    def set_alarm(self, alarm):
        self.alarm = alarm
        self.save()