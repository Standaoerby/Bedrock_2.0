from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.app import App
from kivy.properties import StringProperty

from classes.base_screen import BaseScreen


def _theme_color(role, fallback):
    cfg = App.get_running_app().theme_config or {}
    return cfg.get("colors", {}).get(role, fallback)


def _theme_font(size_role, fallback="14sp"):
    cfg = App.get_running_app().theme_config or {}
    return cfg.get("font_sizes", {}).get(size_role, fallback)


def _theme_font_name():
    cfg = App.get_running_app().theme_config or {}
    return cfg.get("font_name", "Minecraftia")


class DayForecastItem(BoxLayout):
    """One row in the weekly forecast (day | temp | condition | %)."""

    def __init__(self, day_data, **kw):
        super().__init__(**kw)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 36
        self.spacing = 8

        day_name = day_data.get("day", "")
        is_weekend = day_name in ("Sat", "Sun")
        day_color = _theme_color(
            "weekend" if is_weekend else "weekday",
            [0.9, 0.2, 0.2, 1] if is_weekend else [0.2, 0.4, 0.9, 1],
        )

        font_name = _theme_font_name()
        font_size = _theme_font("small")
        text_color = _theme_color("font_default", [1, 1, 1, 1])

        self.add_widget(Label(
            text=day_name, font_name=font_name, font_size=font_size,
            halign="left", size_hint_x=0.15, color=day_color,
        ))
        self.add_widget(Label(
            text=f"{day_data.get('temp_max', 0):.1f}°C",
            font_name=font_name, font_size=font_size,
            halign="left", size_hint_x=0.2, color=text_color,
        ))
        self.add_widget(Label(
            text=day_data.get("condition", ""),
            font_name=font_name, font_size=font_size,
            halign="left", size_hint_x=0.4, color=text_color,
        ))
        self.add_widget(Label(
            text=f"{day_data.get('precipitation_probability', 0)}%",
            font_name=font_name, font_size=font_size,
            halign="left", size_hint_x=0.25, color=text_color,
        ))


class WeatherScreen(BaseScreen):
    page_key = StringProperty("weather")

    def do_on_pre_enter(self):
        self.schedule_once(self.display_weather, 0)
        self.add_interval(self.display_weather, 60)

    def display_weather(self):
        app = self.get_app()
        weather = app.weather_service.get_weather()
        sensors = app.sensor_service.get_readings()

        cur = weather.get("current", {}) or {}
        if "current_temp" in self.ids:
            self.ids.current_temp.text = f"{cur.get('temperature', 0):.1f}°C"
        if "current_condition" in self.ids:
            self.ids.current_condition.text = f"{cur.get('condition', 'Unknown')}"
        if "current_precipitation" in self.ids:
            self.ids.current_precipitation.text = f"Precipitation: {cur.get('precipitation_probability', 0)}%"

        if "sensor_temp" in self.ids:
            self.ids.sensor_temp.text = f"Temperature: {sensors.get('temperature', 0):.1f}°C"
            self.ids.sensor_humidity.text = f"Humidity: {sensors.get('humidity', 0):.1f}%"
            self.ids.sensor_co2.text = f"CO2: {sensors.get('co2', 0)} ppm"
            self.ids.sensor_tvoc.text = f"TVOC: {sensors.get('tvoc', 0)} ppb"
            self.ids.air_quality.text = f"Air Quality: {sensors.get('air_quality', 'Unknown')}"

        weekly = weather.get("weekly_forecast", []) or []
        cont = self.ids.get("weekly_forecast_container")
        if cont is not None:
            cont.clear_widgets()
            if weekly:
                for d in weekly:
                    cont.add_widget(DayForecastItem(d))
            else:
                cont.add_widget(Label(
                    text="No weekly forecast data available",
                    font_name=_theme_font_name(),
                    font_size=_theme_font("medium", "20sp"),
                    color=_theme_color("font_default", [1, 1, 1, 1]),
                    halign="center", valign="center",
                    size_hint_y=None, height=60,
                ))

    def update_weather(self):
        """Refresh button — synchronous fetch of weather + sensors."""
        app = self.get_app()
        app.sensor_service.update_readings()
        app.weather_service.force_update()
        self.display_weather()
