from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class DayForecastItem(BoxLayout):
    """Widget for displaying a single day's forecast in the weekly view"""
    def __init__(self, day_data, **kwargs):
        super(DayForecastItem, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 36  # Slightly reduced height for each day row
        self.spacing = 8
        
        # Get app for theme access
        from kivy.app import App
        app = App.get_running_app()
        
        # Day name (e.g., "Mon")
        day_name = day_data.get("day", "")
        
        # Determine if it's a weekend (Sat or Sun)
        is_weekend = day_name in ["Sat", "Sun"]
        
        # Set color based on weekday/weekend
        if is_weekend:
            day_color = [0.9, 0.2, 0.2, 1]  # Red for weekends
        else:
            day_color = [0.2, 0.4, 0.9, 1]  # Blue for weekdays
        
        day_label = Label(
            text=day_name,
            font_name=app.theme_config["font_name"],
            font_size=app.theme_config.get("font_sizes", {}).get("small", "14sp"),
            halign="left",
            size_hint_x=0.15,
            color=day_color  # Apply weekday/weekend color
        )
        
        # Max temperature only
        temp_max = day_data.get("temp_max", 0)
        temp_label = Label(
            text=f"{temp_max:.1f}°C",
            font_name=app.theme_config["font_name"],
            font_size=app.theme_config.get("font_sizes", {}).get("small", "14sp"),
            halign="left",  # Left-aligned
            size_hint_x=0.2
        )
        
        # Weather condition
        condition_label = Label(
            text=day_data.get("condition", ""),
            font_name=app.theme_config["font_name"],
            font_size=app.theme_config.get("font_sizes", {}).get("small", "14sp"),
            halign="left",  # Left-aligned
            size_hint_x=0.4
        )
        
        # Precipitation probability
        precip = day_data.get("precipitation_probability", 0)
        precip_label = Label(
            text=f"{precip}%",
            font_name=app.theme_config["font_name"],
            font_size=app.theme_config.get("font_sizes", {}).get("small", "14sp"),
            halign="left",  # Left-aligned
            size_hint_x=0.25
        )
        
        # Add all components to the layout
        self.add_widget(day_label)
        self.add_widget(temp_label)
        self.add_widget(condition_label)
        self.add_widget(precip_label)

class WeatherScreen(MDScreen):
    def on_pre_enter(self):
        # Delay display to avoid accessing ids too early
        Clock.schedule_once(lambda dt: self.display_weather(), 0)
        
        # Start regular updates
        self._update_ev = Clock.schedule_interval(lambda dt: self.display_weather(), 60)  # Update every minute
    
    def on_leave(self):
        # Stop updates when leaving screen
        if hasattr(self, '_update_ev'):
            self._update_ev.cancel()
        
    def display_weather(self):
        app = self.get_app()
        weather = app.weather_service.get_weather()
        sensors = app.sensor_service.get_readings()  # Get sensor readings
        
        # Current weather
        cur = weather.get("current", {})
        if cur:
            # Update current weather labels
            self.ids.current_temp.text = f"{cur.get('temperature', 0):.1f}°C"
            self.ids.current_condition.text = f"{cur.get('condition', 'Unknown')}"
            self.ids.current_precipitation.text = f"Precipitation: {cur.get('precipitation_probability', 0)}%"
        
        # Update sensor data fields with real readings
        self.ids.sensor_temp.text = f"Temperature: {sensors.get('temperature', 0):.1f}°C"
        self.ids.sensor_humidity.text = f"Humidity: {sensors.get('humidity', 0):.1f}%"
        self.ids.sensor_co2.text = f"CO2: {sensors.get('co2', 0)} ppm"
        self.ids.sensor_tvoc.text = f"TVOC: {sensors.get('tvoc', 0)} ppb"
        self.ids.air_quality.text = f"Air Quality: {sensors.get('air_quality', 'Unknown')}"
        
        # Weekly forecast
        weekly_forecast = weather.get("weekly_forecast", [])
        weekly_container = self.ids.weekly_forecast_container
        
        # Clear previous widgets
        weekly_container.clear_widgets()
        
        # Add day items
        if weekly_forecast:
            for day_data in weekly_forecast:
                day_item = DayForecastItem(day_data)
                weekly_container.add_widget(day_item)
        else:
            # No weekly data available
            no_data_label = Label(
                text="No weekly forecast data available",
                font_name=app.theme_config["font_name"],
                font_size=app.theme_config.get("font_sizes", {}).get("medium", "20sp"),
                halign="center",
                valign="center",
                size_hint_y=None,
                height=60
            )
            weekly_container.add_widget(no_data_label)

    def update_weather(self):
        """Force weather data update"""
        app = self.get_app()
        # Play click sound (already handled in kv file)
        
        # Update sensor readings
        app.sensor_service.update_readings()
        
        # Update weather data
        app.weather_service.fetch_weather()
        
        # Update display
        self.display_weather()
        
    def get_app(self):
        from kivy.app import App
        return App.get_running_app()