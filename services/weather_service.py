import requests, json, os, time
from datetime import datetime, timedelta

class WeatherService:
    def __init__(self, lat, lon, path="cache/weather.json"):
        self.lat = lat
        self.lon = lon
        self.path = path
        self.weather = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.weather = json.load(f)
        else:
            self.weather = {}
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.weather, f, ensure_ascii=False, indent=2)

    def needs_update(self):
        updated = self.weather.get("updated")
        if not updated:
            return True
        last = datetime.fromisoformat(updated)
        return (datetime.now() - last) > timedelta(hours=3)

    def update(self):
        # open-meteo, бесплатный, не требует ключа
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current_weather=true&hourly=temperature_2m,precipitation,weathercode"
        data = requests.get(url, timeout=10).json()
        current = data.get("current_weather", {})
        # находим прогноз через 5 часов
        from datetime import datetime
        now = datetime.now()
        try:
            idx_5h = data["hourly"]["time"].index(
                (now + timedelta(hours=5)).replace(minute=0, second=0, microsecond=0).isoformat()[:13] + ":00"
            )
            forecast_5h = {
                "temperature": data["hourly"]["temperature_2m"][idx_5h],
                "precipitation": data["hourly"]["precipitation"][idx_5h],
                "condition": data["hourly"]["weathercode"][idx_5h]
            }
        except Exception:
            forecast_5h = {}

        self.weather = {
            "current": {
                "time": current.get("time"),
                "temperature": current.get("temperature"),
                "precipitation": current.get("precipitation", 0),
                "condition": current.get("weathercode")
            },
            "forecast_5h": forecast_5h,
            "updated": now.isoformat()
        }
        self.save()
