import requests
import json
import os
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

    def fetch_weather(self):
        # Бесплатный open-meteo.com, никакого ключа!
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
            f"&current_weather=true&hourly=temperature_2m,precipitation_probability,weathercode"
        )
        data = requests.get(url, timeout=10).json()
        now = datetime.now()
        # Текущее
        current = data["current_weather"]
        # Индекс прогноза через 5 часов
        times = data["hourly"]["time"]
        t_5h = (now + timedelta(hours=5)).replace(minute=0, second=0, microsecond=0).isoformat()
        try:
            idx_5h = times.index(t_5h)
        except ValueError:
            idx_5h = -1

        forecast_5h = {
            "temperature": data["hourly"]["temperature_2m"][idx_5h] if idx_5h >= 0 else None,
            "precipitation_probability": data["hourly"]["precipitation_probability"][idx_5h] if idx_5h >= 0 else None,
            "weathercode": data["hourly"]["weathercode"][idx_5h] if idx_5h >= 0 else None
        } if idx_5h >= 0 else {}

        # Маппинг weathercode в понятные статусы (на русском)
        weather_map = {
            0: "солнечно",
            1: "частично облачно",
            2: "пасмурно",
            3: "туман",
            45: "туман",
            48: "изморозь",
            51: "морось",
            61: "дождь",
            71: "снег",
            95: "гроза",
            # и т.д. — можно расширять!
        }
        current_condition = weather_map.get(current["weathercode"], "неизвестно")
        forecast_condition = weather_map.get(forecast_5h.get("weathercode"), "неизвестно") if forecast_5h else "нет данных"

        self.weather = {
            "current": {
                "time": current["time"],
                "temperature": current["temperature"],
                "condition": current_condition,
                "precipitation_probability": data["hourly"]["precipitation_probability"][0],  # ближайший час
            },
            "forecast_5h": {
                "temperature": forecast_5h.get("temperature"),
                "condition": forecast_condition,
                "precipitation_probability": forecast_5h.get("precipitation_probability")
            },
            "updated": now.isoformat()
        }
        self.save()

    def get_weather(self):
        if self.needs_update():
            self.fetch_weather()
        return self.weather
