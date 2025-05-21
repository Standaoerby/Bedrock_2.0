from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.properties import BooleanProperty
import logging
from utils.error_handler import ErrorHandler

# Setup logging
logger = logging.getLogger("WeatherScreen")

class DayForecastItem(BoxLayout):
    """Widget for displaying a single day's forecast in the weekly view"""
    def __init__(self, day_data, **kwargs):
        super(DayForecastItem, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(50)  # Increased height for better touch targets
        self.spacing = dp(8)
        
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
            font_size="18sp",
            halign="left",
            size_hint_x=0.15,
            color=day_color
        )
        
        # Max temperature only
        temp_max = day_data.get("temp_max", 0)
        temp_label = Label(
            text=f"{temp_max:.1f}°C",
            font_name=app.theme_config["font_name"],
            font_size="18sp",
            halign="left",
            size_hint_x=0.2
        )
        
        # Weather condition
        condition_label = Label(
            text=day_data.get("condition", ""),
            font_name=app.theme_config["font_name"],
            font_size="18sp",
            halign="left",
            size_hint_x=0.4
        )
        
        # Precipitation probability
        precip = day_data.get("precipitation_probability", 0)
        precip_label = Label(
            text=f"{precip}%",
            font_name=app.theme_config["font_name"],
            font_size="18sp",
            halign="left",
            size_hint_x=0.25
        )
        
        # Add all components to the layout
        self.add_widget(day_label)
        self.add_widget(temp_label)
        self.add_widget(condition_label)
        self.add_widget(precip_label)

class WeatherScreen(MDScreen):
    # Properties to track sensor status
    sensor_available = BooleanProperty(False)
    using_mock_sensors = BooleanProperty(True)
    
    def on_pre_enter(self):
        # Force update of all data when entering screen
        logger.info("Entering WeatherScreen - forcing data update")
        self.update_sensor_data()
        self.update_weather_data()
        self.display_weather()
        
        # Start regular updates
        self._weather_update_ev = Clock.schedule_interval(lambda dt: self.update_weather_data(), 3600)  # Hourly
        self._sensor_update_ev = Clock.schedule_interval(lambda dt: self.update_sensor_data(), 30)  # Every 30 seconds
        self._display_update_ev = Clock.schedule_interval(lambda dt: self.display_weather(), 30)  # Update display every 30 seconds
        
        logger.info("Update timers initialized")
    
    def on_leave(self):
        # Stop updates when leaving screen
        logger.info("Leaving WeatherScreen - stopping update timers")
        if hasattr(self, '_weather_update_ev'):
            self._weather_update_ev.cancel()
        if hasattr(self, '_sensor_update_ev'):
            self._sensor_update_ev.cancel()
        if hasattr(self, '_display_update_ev'):
            self._display_update_ev.cancel()
    
    @ErrorHandler.handle_exception
    def update_weather_data(self):
        """Update only weather data from service"""
        app = self.get_app()
        if hasattr(app, 'weather_service') and app.weather_service:
            app.weather_service.fetch_weather()
    
    @ErrorHandler.handle_exception
    def update_sensor_data(self):
        """Update only sensor readings"""
        app = self.get_app()
        if hasattr(app, 'sensor_service') and app.sensor_service:
            # Update sensor readings
            app.sensor_service.update_readings()
            
            # Get sensor status from service
            self.sensor_available = app.sensor_service.sensor_available
            self.using_mock_sensors = getattr(app.sensor_service, 'using_mock_sensors', True)
        else:
            # No sensor service available
            self.sensor_available = False
            self.using_mock_sensors = True
    
    @ErrorHandler.handle_exception
    def display_weather(self):
        """Display weather and sensor data on the screen"""
        app = self.get_app()
        weather = app.weather_service.get_weather() if hasattr(app, 'weather_service') and app.weather_service else {}
        
        # Get sensor readings with proper null checks
        sensors = {}
        if hasattr(app, 'sensor_service') and app.sensor_service:
            # Get readings from sensors
            sensors = app.sensor_service.get_readings()
            
            # Update sensor availability status
            self.sensor_available = app.sensor_service.sensor_available
            self.using_mock_sensors = getattr(app.sensor_service, 'using_mock_sensors', True)
        else:
            # No sensor service available
            self.sensor_available = False
            self.using_mock_sensors = True
        
        # Current weather
        cur = weather.get("current", {})
        if cur:
            # Update current temperature with temperature value only
            temp = cur.get('temperature', 0)
            self.ids.current_temp.text = f"{temp:.1f}°C"
            
            # Set the color of temperature based on value
            if temp < 15:
                self.ids.current_temp.color = [1, 1, 1, 1]  # White for cold
            else:
                self.ids.current_temp.color = [1, 0.6, 0, 1]  # Orange for warm
            
            # Update condition text separately
            self.ids.current_condition.text = f"{cur.get('condition', 'Unknown')}"
            
            # Update precipitation text
            self.ids.current_precipitation.text = f"Rain: {cur.get('precipitation_probability', 0)}%"
        
        # Update sensor readings even if unavailable (will show zeros)
        temp_value = sensors.get('temperature', 0)
        self.ids.sensor_temp.text = f"Temperature: {temp_value:.1f}°C"
        
        humidity_value = sensors.get('humidity', 0)
        self.ids.sensor_humidity.text = f"Humidity: {humidity_value:.1f}%"
        
        # Add sensor status indicator
        sensor_status = ""
        if not self.sensor_available:
            sensor_status = " [OFFLINE]"
        elif self.using_mock_sensors:
            sensor_status = " [MOCK]"
        else:
            sensor_status = " [REAL]"
            
        # Add status to temperature
        self.ids.sensor_temp.text += sensor_status
        
        # Combined CO2 and TVOC on one line
        co2_value = sensors.get('co2', 0)
        tvoc_value = sensors.get('tvoc', 0)
        self.ids.sensor_combined.text = f"CO2: {co2_value} ppm, TVOC: {tvoc_value} ppb"
        
        # Air quality display
        air_quality = sensors.get('air_quality', 'Unknown')
        self.ids.air_quality.text = f"Air Quality: {air_quality}"
        
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
            
            # Ensure minimum height for scrolling
            if len(weekly_forecast) < 7:  # Add padding if fewer than 7 days
                padding_height = (7 - len(weekly_forecast)) * dp(50)
                padding = BoxLayout(size_hint_y=None, height=padding_height)
                weekly_container.add_widget(padding)
        else:
            # No weekly data available
            no_data_label = Label(
                text="No weekly forecast data available",
                font_name=app.theme_config["font_name"],
                font_size="24sp",
                halign="center",
                valign="center",
                size_hint_y=None,
                height=dp(100)
            )
            weekly_container.add_widget(no_data_label)
            
            # Add padding to ensure scrollability
            padding = BoxLayout(size_hint_y=None, height=dp(200))
            weekly_container.add_widget(padding)
        
        # Force layout update
        Clock.schedule_once(lambda dt: self._update_scroll_size(), 0.2)

    def _update_scroll_size(self):
        """Ensure ScrollView content is properly sized"""
        if hasattr(self.ids, 'weekly_forecast_container'):
            container = self.ids.weekly_forecast_container
            
            # Make sure content is taller than viewport
            min_height = dp(300)
            if container.height < min_height:
                container.height = min_height

    def update_weather(self):
        """Force weather data update - public method for manual refresh"""
        logger.info("Manual refresh requested")
        self.update_weather_data()
        self.update_sensor_data()
        self.display_weather()
        
    def get_app(self):
        from kivy.app import App
        return App.get_running_app()