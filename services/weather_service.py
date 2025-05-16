import requests
import json
import os
import traceback
from datetime import datetime, timedelta

class WeatherService:
    def __init__(self, lat, lon, path="cache/weather.json"):
        self.lat = lat
        self.lon = lon
        self.path = path
        self.weather = {}
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.weather = json.load(f)
                print(f"Loaded weather data: {self.weather}")
            else:
                self.weather = {
                    "current": {
                        "time": datetime.now().isoformat(),
                        "temperature": 20.0,
                        "condition": "Unknown",
                        "precipitation_probability": 0
                    },
                    "forecast_5h": {
                        "temperature": 20.0,
                        "condition": "Unknown",
                        "precipitation_probability": 0
                    },
                    "updated": datetime.now().isoformat()
                }
                # Создаем директорию cache, если она не существует
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                self.save()
        except Exception as e:
            print(f"Error loading weather data: {e}")
            traceback.print_exc()
            self.weather = {
                "current": {
                    "temperature": 20.0,
                    "condition": "Error loading data",
                    "precipitation_probability": 0
                },
                "forecast_5h": {},
                "updated": datetime.now().isoformat()
            }

    def save(self):
        try:
            # Создаем директорию cache, если она не существует
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.weather, f, ensure_ascii=False, indent=2)
            print(f"Saved weather data: {self.weather}")
        except Exception as e:
            print(f"Error saving weather data: {e}")
            traceback.print_exc()

    def needs_update(self):
        updated = self.weather.get("updated")
        if not updated:
            return True
        try:
            last = datetime.fromisoformat(updated)
            # Увеличиваем интервал между запросами на RPi для экономии ресурсов
            return (datetime.now() - last) > timedelta(hours=6)  # Увеличено с 3 до 6 часов
        except Exception as e:
            print(f"Error checking if weather needs update: {e}")
            return True

    def fetch_weather(self):
        try:
            print(f"Fetching weather for lat={self.lat}, lon={self.lon}")
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
                f"&current_weather=true&hourly=temperature_2m,precipitation_probability,weathercode"
            )
            response = requests.get(url, timeout=10)
            data = response.json()
            
            print(f"API response status: {response.status_code}")
            print(f"API response data: {data}")
            
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

            # Маппинг погодных кодов в статусы на английском
            weather_map = {
                0: "Sunny",
                1: "Bit Cloudy",
                2: "Cloudy",
                3: "Fog",
                45: "Fog",
                48: "Frost",
                51: "Drizzle",
                61: "Rain",
                71: "Snow",
                95: "Storm",
            }
            current_condition = weather_map.get(current.get("weathercode", -1), "Unknown")
            forecast_condition = weather_map.get(forecast_5h.get("weathercode", -1), "Unknown") if forecast_5h else "Unknown"

            self.weather = {
                "current": {
                    "time": current.get("time", now.isoformat()),
                    "temperature": current.get("temperature", 0),
                    "condition": current_condition,
                    "precipitation_probability": data["hourly"]["precipitation_probability"][0] if len(data["hourly"]["precipitation_probability"]) > 0 else 0,
                },
                "forecast_5h": {
                    "temperature": forecast_5h.get("temperature"),
                    "condition": forecast_condition,
                    "precipitation_probability": forecast_5h.get("precipitation_probability")
                },
                "updated": now.isoformat()
            }
            self.save()
            return True
            
        except Exception as e:
            print(f"Error fetching weather: {e}")
            traceback.print_exc()
            return False

    def get_weather(self):
        if self.needs_update():
            print("Weather data needs update, fetching...")
            self.fetch_weather()
        return self.weather