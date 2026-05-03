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
                # No cache yet — leave self.weather empty so needs_update()
                # returns True on the first get_weather() call. Otherwise
                # the placeholder "20.0 Unknown" sticks for 6 hours because
                # save() with a fresh "updated" timestamp would suppress the
                # next fetch.
                self.weather = {
                    "current": {},
                    "forecast_5h": {},
                    "weekly_forecast": [],
                    # No "updated" → needs_update() returns True
                }
        except Exception as e:
            print(f"Error loading weather data: {e}")
            traceback.print_exc()
            # Same reason as above — no "updated" so a fetch is forced.
            self.weather = {
                "current": {},
                "forecast_5h": {},
                "weekly_forecast": [],
            }

    def save(self):
        try:
            # Create cache directory if it doesn't exist
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.weather, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving weather data: {e}")
            traceback.print_exc()

    def needs_update(self):
        updated = self.weather.get("updated")
        if not updated:
            return True
        try:
            last = datetime.fromisoformat(updated)
            # Increased update interval to save resources on RPi
            return (datetime.now() - last) > timedelta(hours=6)
        except Exception as e:
            print(f"Error checking if weather needs update: {e}")
            return True

    def fetch_weather(self):
        try:
            print(f"Fetching weather for lat={self.lat}, lon={self.lon}")
            
            # Extended API call to include daily forecast
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
                f"&current_weather=true"
                f"&hourly=temperature_2m,precipitation_probability,weathercode"
                f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                f"&timezone=auto&forecast_days=7"  # Get 7 days forecast
            )
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            print(f"API response status: {response.status_code}")
            print(f"API response data: {data}")
            
            now = datetime.now()
            times = data["hourly"]["time"]

            # Current weather
            current = data["current_weather"]

            # 5-hour forecast index
            t_5h = (now + timedelta(hours=5)).replace(minute=0, second=0, microsecond=0).isoformat()
            try:
                idx_5h = times.index(t_5h)
            except ValueError:
                idx_5h = -1

            # If no 5-hour forecast, look for same time tomorrow
            if idx_5h < 0:
                t_24h = (now + timedelta(hours=24)).replace(minute=0, second=0, microsecond=0).isoformat()
                try:
                    idx_5h = times.index(t_24h)
                except ValueError:
                    # fallback — closest future time
                    idx_5h = next((i for i, t in enumerate(times) if t > now.isoformat()), -1)

            if idx_5h >= 0:
                forecast_5h = {
                    "temperature": data["hourly"]["temperature_2m"][idx_5h],
                    "precipitation_probability": data["hourly"]["precipitation_probability"][idx_5h],
                    "weathercode": data["hourly"]["weathercode"][idx_5h]
                }
            else:
                forecast_5h = {}

            # Weather code mapping to English status
            weather_map = {
                0: "Clear Sky", 
                1: "Mostly Clear",
                2: "Partly Cloudy",
                3: "Cloudy",
                45: "Fog",
                48: "Depositing Rime Fog",
                51: "Light Drizzle",
                53: "Moderate Drizzle",
                55: "Dense Drizzle",
                61: "Slight Rain",
                63: "Moderate Rain",
                65: "Heavy Rain",
                71: "Slight Snow",
                73: "Moderate Snow",
                75: "Heavy Snow",
                80: "Slight Rain Showers",
                81: "Moderate Rain Showers",
                82: "Violent Rain Showers",
                85: "Slight Snow Showers",
                86: "Heavy Snow Showers",
                95: "Thunderstorm",
                96: "Thunderstorm with Slight Hail",
                99: "Thunderstorm with Heavy Hail"
            }
            
            current_condition = weather_map.get(current.get("weathercode", -1), "Unknown")
            forecast_condition = weather_map.get(forecast_5h.get("weathercode", -1), "Unknown") if forecast_5h else "Unknown"
            
            # Process weekly forecast data
            weekly_forecast = []
            if "daily" in data:
                # Get day names
                day_names = []
                for date_str in data["daily"]["time"]:
                    try:
                        date_obj = datetime.fromisoformat(date_str)
                        # Get abbreviated day name (Mon, Tue, etc.)
                        day_name = date_obj.strftime("%a")
                        day_names.append(day_name)
                    except Exception as e:
                        print(f"Error parsing date {date_str}: {e}")
                        day_names.append("???")
                
                # Build weekly forecast data
                for i in range(len(data["daily"]["time"])):
                    try:
                        day_code = data["daily"]["weathercode"][i]
                        day_condition = weather_map.get(day_code, "Unknown")
                        day_forecast = {
                            "day": day_names[i],
                            "date": data["daily"]["time"][i],
                            "temp_max": data["daily"]["temperature_2m_max"][i],
                            "temp_min": data["daily"]["temperature_2m_min"][i],
                            "condition": day_condition,
                            "precipitation_probability": data["daily"]["precipitation_probability_max"][i]
                        }
                        weekly_forecast.append(day_forecast)
                    except Exception as e:
                        print(f"Error processing day {i}: {e}")
            
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
                "weekly_forecast": weekly_forecast,  # Added weekly forecast
                "updated": now.isoformat()
            }
            self.save()
            return True
            
        except Exception as e:
            print(f"Error fetching weather: {e}")
            traceback.print_exc()
            return False

    def get_weather(self):
        # Trigger refresh asynchronously so the UI never blocks on a 10s
        # HTTP timeout when Wi-Fi flaps. Cached weather is returned
        # immediately; the next call will see the new data.
        if self.needs_update() and not getattr(self, "_fetch_in_flight", False):
            self._fetch_in_flight = True
            import threading

            def _bg():
                try:
                    self.fetch_weather()
                finally:
                    self._fetch_in_flight = False

            threading.Thread(target=_bg, daemon=True).start()
        return self.weather

    def force_update(self):
        """Synchronous fetch for explicit user action (Refresh button)."""
        return self.fetch_weather()