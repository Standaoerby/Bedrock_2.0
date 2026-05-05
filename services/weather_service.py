"""
WeatherService — Open-Meteo client with a JSON cache.

Public surface (used by HomeScreen / WeatherScreen):
    get_weather()    → cached dict; triggers a background refresh when the
                       cache is older than UPDATE_INTERVAL_HOURS.
    force_update()   → synchronous fetch, returns success bool. Wired to a
                       Refresh button (no longer in UI but kept for tests
                       and future re-introduction).

The cache file shape:
    {
      "current":         {"time", "temperature", "condition",
                          "precipitation_probability"},
      "forecast_5h":     {"temperature", "condition",
                          "precipitation_probability"},
      "weekly_forecast": [ {day, date, temp_max, temp_min, condition,
                            precipitation_probability}, ... ],
      "updated":         ISO timestamp,  # missing → forces fetch
    }
"""
import logging
import threading
from datetime import datetime, timedelta

import requests

from services._jsonstore import JsonStore

logger = logging.getLogger(__name__)

UPDATE_INTERVAL_HOURS = 6
HTTP_TIMEOUT_SEC = 10
FORECAST_DAYS = 7

# Open-Meteo weathercode → readable English condition. Codes outside this
# table render as "Unknown".
WEATHER_CODE_MAP = {
    0:  "Clear Sky",
    1:  "Mostly Clear",
    2:  "Partly Cloudy",
    3:  "Cloudy",
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
    99: "Thunderstorm with Heavy Hail",
}


def _empty_cache() -> dict:
    """Default cache shape: empty data + no `updated` key so needs_update()
    returns True on the first get_weather() call. Including a fresh
    timestamp here would suppress the next fetch for 6 hours."""
    return {
        "current": {},
        "forecast_5h": {},
        "weekly_forecast": [],
    }


class WeatherService:
    def __init__(self, lat: float, lon: float, path: str = "cache/weather.json"):
        self.lat = lat
        self.lon = lon
        self._store = JsonStore(path, _empty_cache, logger=logger)
        self.weather: dict = {}
        # _fetch_in_flight is read on the UI thread (get_weather) and
        # cleared on the bg fetch thread; the lock makes the
        # check-and-set atomic so two near-simultaneous get_weather()
        # calls can't both kick off fetches.
        self._fetch_lock = threading.Lock()
        self._fetch_in_flight = False
        self.load()

    # ── Cache IO ──────────────────────────────────────────────────────
    def load(self) -> None:
        self.weather = self._store.load()
        if self.weather.get("updated"):
            logger.info(f"loaded cached weather (updated={self.weather['updated']})")
        else:
            logger.info("no cached weather; will fetch on next get_weather()")

    def save(self) -> None:
        self._store.save(self.weather)

    def needs_update(self) -> bool:
        updated = self.weather.get("updated")
        if not updated:
            return True
        try:
            last = datetime.fromisoformat(updated)
        except ValueError as e:
            logger.warning(f"bad `updated` timestamp {updated!r} ({e}); forcing refresh")
            return True
        return (datetime.now() - last) > timedelta(hours=UPDATE_INTERVAL_HOURS)

    # ── Fetch ─────────────────────────────────────────────────────────
    def fetch_weather(self) -> bool:
        """Synchronous Open-Meteo fetch. Returns True on success."""
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={self.lat}&longitude={self.lon}"
            "&current_weather=true"
            "&hourly=temperature_2m,precipitation_probability,weathercode"
            "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=auto&forecast_days={FORECAST_DAYS}"
        )
        logger.info(f"fetching weather lat={self.lat} lon={self.lon}")
        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT_SEC)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            # ValueError covers JSON decode failure on 200-OK garbage bodies.
            logger.error(f"weather fetch failed: {e}")
            return False

        try:
            self.weather = self._parse_response(data)
            self.weather["updated"] = datetime.now().isoformat()
            self.save()
            return True
        except (KeyError, IndexError, TypeError) as e:
            # API contract shifted (renamed/missing field). Don't crash —
            # just log and keep the prior cache.
            logger.error(f"weather response parsing failed: {e}")
            return False

    def _parse_response(self, data: dict) -> dict:
        now = datetime.now()
        hourly = data["hourly"]
        times = hourly["time"]
        current = data["current_weather"]

        # 5-hour forecast index: try the exact future hour; fall back to
        # +24h then to "first time strictly in the future".
        idx_5h = self._find_hour_index(times, now + timedelta(hours=5))
        if idx_5h < 0:
            idx_5h = self._find_hour_index(times, now + timedelta(hours=24))
        if idx_5h < 0:
            idx_5h = next(
                (i for i, t in enumerate(times) if t > now.isoformat()),
                -1,
            )

        forecast_5h: dict = {}
        if idx_5h >= 0:
            forecast_5h = {
                "temperature": hourly["temperature_2m"][idx_5h],
                "condition": WEATHER_CODE_MAP.get(hourly["weathercode"][idx_5h], "Unknown"),
                "precipitation_probability": hourly["precipitation_probability"][idx_5h],
            }

        current_block = {
            "time": current.get("time", now.isoformat()),
            "temperature": current.get("temperature", 0),
            "condition": WEATHER_CODE_MAP.get(current.get("weathercode", -1), "Unknown"),
            "precipitation_probability":
                hourly["precipitation_probability"][0]
                if hourly["precipitation_probability"]
                else 0,
        }

        weekly_forecast = self._parse_daily(data.get("daily"))

        return {
            "current": current_block,
            "forecast_5h": forecast_5h,
            "weekly_forecast": weekly_forecast,
        }

    @staticmethod
    def _find_hour_index(times: list, target: datetime) -> int:
        target_iso = target.replace(minute=0, second=0, microsecond=0).isoformat()
        try:
            return times.index(target_iso)
        except ValueError:
            return -1

    @staticmethod
    def _parse_daily(daily: dict | None) -> list:
        if not daily:
            return []
        out = []
        for i, date_str in enumerate(daily.get("time", [])):
            try:
                day_name = datetime.fromisoformat(date_str).strftime("%a")
            except ValueError:
                day_name = "???"
            try:
                code = daily["weathercode"][i]
                out.append({
                    "day": day_name,
                    "date": date_str,
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "condition": WEATHER_CODE_MAP.get(code, "Unknown"),
                    "precipitation_probability": daily["precipitation_probability_max"][i],
                })
            except (KeyError, IndexError) as e:
                logger.warning(f"daily forecast row {i} skipped ({e})")
        return out

    # ── Public API ────────────────────────────────────────────────────
    def get_weather(self) -> dict:
        """Return the cached dict. If stale and no fetch is already in
        flight, kick off a background fetch — the next call sees the new
        data. The UI never blocks on the 10s HTTP timeout."""
        if self.needs_update():
            with self._fetch_lock:
                if not self._fetch_in_flight:
                    self._fetch_in_flight = True
                    threading.Thread(target=self._bg_fetch, daemon=True).start()
        return self.weather

    def _bg_fetch(self) -> None:
        try:
            self.fetch_weather()
        finally:
            with self._fetch_lock:
                self._fetch_in_flight = False

    def force_update(self) -> bool:
        """Synchronous fetch for explicit user action (Refresh button)."""
        return self.fetch_weather()
