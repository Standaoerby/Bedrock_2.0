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
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
            f"&current_weather=true&hourly=temperature_2m,precipitation_probability,weathercode"
        )
        data = requests.get(url, timeout=10).json()
        now = datetime.now()
        times = data["hourly"]["time"]

        # Текущее значение
        current = data["current_weather"]

        # Индекс прогноза через 5 часов
        t_5h = (now + timedelta(hours=5)).replace(minute=0, second=0, microsecond=0).isoformat()
        try:
            idx_5h = times.index(t_5h)
        except ValueError:
            idx_5h = -1

        # Если нет прогноза через 5 часов, ищем прогноз на то же время завтра
        if idx_5h < 0:
            t_24h = (now + timedelta(hours=24)).replace(minute=0, second=0, microsecond=0).isoformat()
            try:
                idx_5h = times.index(t_24h)
            except ValueError:
                # fallback — ближайшее будущее значение
                idx_5h = next((i for i, t in enumerate(times) if t > now.isoformat()), -1)

        if idx_5h >= 0:
            forecast_5h = {
                "temperature": data["hourly"]["temperature_2m"][idx_5h],
                "precipitation_probability": data["hourly"]["precipitation_probability"][idx_5h],
                "weathercode": data["hourly"]["weathercode"][idx_5h]
            }
        else:
            forecast_5h = {}

        # Маппинг погодных кодов в статусы на русском
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
