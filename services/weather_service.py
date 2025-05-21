import requests
import json
import os
import logging
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger("WeatherService")

# Weather code mapping to readable conditions
WEATHER_CONDITIONS = {
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

class WeatherService:
    """Service for fetching and managing weather data"""
    
    def __init__(self, lat, lon, path="cache/weather.json", update_interval=6):
        """
        Initialize the weather service
        
        Args:
            lat: Latitude
            lon: Longitude
            path: Path to cache file
            update_interval: Hours between updates
        """
        self.lat = lat
        self.lon = lon
        self.path = path
        self.update_interval = update_interval
        self.weather = {}
        self.api_url = self._build_api_url()
        
        # Load cached data
        self.load()
    
    def _build_api_url(self):
        """Build the Open-Meteo API URL with appropriate parameters"""
        return (
            f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
            f"&current_weather=true"
            f"&hourly=temperature_2m,precipitation_probability,weathercode"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=auto&forecast_days=7"
        )

    def load(self):
        """Load weather data from cache file"""
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.weather = json.load(f)
                logger.info(f"Loaded cached weather data from {self.path}")
            else:
                # Create default data structure
                self.weather = self._create_default_data()
                # Create cache directory if it doesn't exist
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                self.save()
                logger.info("Created default weather data")
        except Exception as e:
            logger.error(f"Error loading weather data: {e}", exc_info=True)
            # Fall back to defaults if there's an error
            self.weather = self._create_default_data()
    
    def _create_default_data(self):
        """Create default weather data structure"""
        return {
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
            "weekly_forecast": [],
            "updated": datetime.now().isoformat()
        }

    def save(self):
        """Save weather data to cache file"""
        try:
            # Create cache directory if it doesn't exist
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.weather, f, ensure_ascii=False, indent=2)
            logger.debug("Saved weather data to cache")
        except Exception as e:
            logger.error(f"Error saving weather data: {e}", exc_info=True)

    def needs_update(self):
        """Check if weather data needs to be updated"""
        updated = self.weather.get("updated")
        if not updated:
            return True
            
        try:
            last = datetime.fromisoformat(updated)
            # Check if update interval has passed
            return (datetime.now() - last) > timedelta(hours=self.update_interval)
        except Exception as e:
            logger.error(f"Error checking update time: {e}")
            return True

    def fetch_weather(self):
        """Fetch weather data from Open-Meteo API"""
        try:
            logger.info(f"Fetching weather for lat={self.lat}, lon={self.lon}")
            
            # Fetch data with timeout
            response = requests.get(self.api_url, timeout=10)
            
            # Check if request was successful
            if response.status_code != 200:
                logger.error(f"API request failed with status code {response.status_code}")
                return False
                
            # Parse JSON response
            data = response.json()
            logger.debug(f"Received weather data from API")
            
            # Process the API response
            self._process_api_response(data)
            
            # Save to cache
            self.save()
            return True
            
        except requests.exceptions.Timeout:
            logger.error("Weather API request timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Connection error while fetching weather data")
            return False
        except Exception as e:
            logger.error(f"Error fetching weather: {e}", exc_info=True)
            return False
    
    def _process_api_response(self, data):
        """Process the API response and update weather data"""
        try:
            now = datetime.now()
            
            # Extract time data
            times = data["hourly"]["time"]

            # Current weather
            current = data["current_weather"]

            # Find 5-hour forecast index
            t_5h = (now + timedelta(hours=5)).replace(minute=0, second=0, microsecond=0).isoformat()
            try:
                idx_5h = times.index(t_5h)
            except ValueError:
                idx_5h = -1

            # If no 5-hour forecast, look for closest alternative
            if idx_5h < 0:
                # Try same time tomorrow
                t_24h = (now + timedelta(hours=24)).replace(minute=0, second=0, microsecond=0).isoformat()
                try:
                    idx_5h = times.index(t_24h)
                except ValueError:
                    # fallback — closest future time
                    idx_5h = next((i for i, t in enumerate(times) if t > now.isoformat()), 0)

            # Extract 5-hour forecast if available
            if idx_5h >= 0 and idx_5h < len(data["hourly"]["temperature_2m"]):
                forecast_5h = {
                    "temperature": data["hourly"]["temperature_2m"][idx_5h],
                    "precipitation_probability": data["hourly"]["precipitation_probability"][idx_5h],
                    "weathercode": data["hourly"]["weathercode"][idx_5h]
                }
            else:
                forecast_5h = {}
            
            # Get text conditions
            current_condition = WEATHER_CONDITIONS.get(current.get("weathercode", -1), "Unknown")
            forecast_condition = WEATHER_CONDITIONS.get(forecast_5h.get("weathercode", -1), "Unknown") if forecast_5h else "Unknown"
            
            # Process weekly forecast data
            weekly_forecast = self._process_weekly_forecast(data)
            
            # Build weather data structure
            self.weather = {
                "current": {
                    "time": current.get("time", now.isoformat()),
                    "temperature": current.get("temperature", 0),
                    "condition": current_condition,
                    "precipitation_probability": data["hourly"]["precipitation_probability"][0] if "hourly" in data and "precipitation_probability" in data["hourly"] and len(data["hourly"]["precipitation_probability"]) > 0 else 0,
                },
                "forecast_5h": {
                    "temperature": forecast_5h.get("temperature"),
                    "condition": forecast_condition,
                    "precipitation_probability": forecast_5h.get("precipitation_probability")
                },
                "weekly_forecast": weekly_forecast,
                "updated": now.isoformat()
            }
            
            logger.info("Weather data updated successfully")
            
        except Exception as e:
            logger.error(f"Error processing weather data: {e}", exc_info=True)
            raise
    
    def _process_weekly_forecast(self, data):
        """Process weekly forecast data from API response"""
        weekly_forecast = []
        
        try:
            if "daily" not in data:
                return weekly_forecast
                
            # Get day names
            day_names = []
            for date_str in data["daily"]["time"]:
                try:
                    date_obj = datetime.fromisoformat(date_str)
                    # Get abbreviated day name (Mon, Tue, etc.)
                    day_name = date_obj.strftime("%a")
                    day_names.append(day_name)
                except Exception as e:
                    logger.error(f"Error parsing date {date_str}: {e}")
                    day_names.append("???")
            
            # Build weekly forecast data
            for i in range(len(data["daily"]["time"])):
                try:
                    day_code = data["daily"]["weathercode"][i]
                    day_condition = WEATHER_CONDITIONS.get(day_code, "Unknown")
                    
                    # Create day forecast object
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
                    logger.error(f"Error processing day {i}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing weekly forecast: {e}", exc_info=True)
            
        return weekly_forecast

    def get_weather(self):
        """Get current weather data, updating if needed"""
        if self.needs_update():
            logger.info("Weather data needs update, fetching...")
            self.fetch_weather()
        return self.weather
    
    def force_update(self):
        """Force an immediate update of weather data"""
        logger.info("Forcing weather update")
        return self.fetch_weather()