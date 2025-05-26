from utils.common import BasePage, Constants
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.properties import BooleanProperty
import logging

logger = logging.getLogger("WeatherScreen")

class DayForecastItem(BoxLayout):
    """Виджет для отображения прогноза на день"""
    
    def __init__(self, day_data, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(50)
        self.spacing = dp(8)
        
        # Get app for theme access
        app = self.get_app()
        
        # Day name
        day_name = day_data.get("day", "")
        is_weekend = day_name in ["Sat", "Sun"]
        day_color = [0.9, 0.2, 0.2, 1] if is_weekend else [0.2, 0.4, 0.9, 1]
        
        day_label = Label(
            text=day_name,
            font_name=app.theme_config["font_name"],
            font_size="18sp",
            halign="left",
            size_hint_x=0.15,
            color=day_color
        )
        
        # Temperature
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
        
        # Add all components
        self.add_widget(day_label)
        self.add_widget(temp_label)
        self.add_widget(condition_label)
        self.add_widget(precip_label)
    
    def get_app(self):
        from kivy.app import App
        return App.get_running_app()

class WeatherScreen(BasePage):
    """Экран погоды"""
    
    # Properties to track sensor status
    sensor_available = BooleanProperty(False)
    using_mock_sensors = BooleanProperty(True)
    
    def on_pre_enter(self):
        """Вход на экран"""
        logger.info("Entering WeatherScreen")
        
        # Force update of all data
        self.update_sensor_data()
        self.update_weather_data()
        self.display_weather()
        
        # Start regular updates
        self.schedule_timer(lambda dt: self.update_weather_data(), 3600)  # Hourly
        self.schedule_timer(lambda dt: self.update_sensor_data(), Constants.SENSOR_UPDATE_INTERVAL)
        self.schedule_timer(lambda dt: self.display_weather(), Constants.SENSOR_UPDATE_INTERVAL)
        
        logger.info("Weather screen initialized")
    
    def update_weather_data(self):
        """Обновить данные о погоде"""
        app = self.get_app()
        if hasattr(app, 'weather_service') and app.weather_service:
            app.weather_service.fetch_weather()
    
    def update_sensor_data(self):
        """Обновить показания датчиков"""
        app = self.get_app()
        if hasattr(app, 'sensor_service') and app.sensor_service:
            app.sensor_service.update_readings()
            self.sensor_available = app.sensor_service.sensor_available
            self.using_mock_sensors = getattr(app.sensor_service, 'using_mock_sensors', True)
        else:
            self.sensor_available = False
            self.using_mock_sensors = True
    
    def display_weather(self):
        """Отобразить погоду и данные датчиков"""
        app = self.get_app()
        weather = app.weather_service.get_weather() if hasattr(app, 'weather_service') and app.weather_service else {}
        
        # Get sensor readings
        sensors = {}
        if hasattr(app, 'sensor_service') and app.sensor_service:
            sensors = app.sensor_service.get_readings()
            self.sensor_available = app.sensor_service.sensor_available
            self.using_mock_sensors = getattr(app.sensor_service, 'using_mock_sensors', True)
        else:
            self.sensor_available = False
            self.using_mock_sensors = True
        
        # Current weather
        current = weather.get("current", {})
        if current:
            temp = current.get('temperature', 0)
            self.safe_set_widget_text('current_temp', f"{temp:.1f}°C")
            
            # Set temperature color
            temp_widget = self.safe_get_widget('current_temp')
            if temp_widget:
                if temp < 15:
                    temp_widget.color = [1, 1, 1, 1]  # White for cold
                else:
                    temp_widget.color = [1, 0.6, 0, 1]  # Orange for warm
            
            self.safe_set_widget_text('current_condition', current.get('condition', 'Unknown'))
            self.safe_set_widget_text('current_precipitation', f"Rain: {current.get('precipitation_probability', 0)}%")
        
        # Update sensor readings
        temp_value = sensors.get('temperature', 0)
        humidity_value = sensors.get('humidity', 0)
        co2_value = sensors.get('co2', 0)
        tvoc_value = sensors.get('tvoc', 0)
        air_quality = sensors.get('air_quality', 'Unknown')
        
        # Add sensor status indicator
        sensor_status = ""
        if not self.sensor_available:
            sensor_status = " [OFFLINE]"
        elif self.using_mock_sensors:
            sensor_status = " [MOCK]"
        else:
            sensor_status = " [REAL]"
        
        self.safe_set_widget_text('sensor_temp', f"Temperature: {temp_value:.1f}°C{sensor_status}")
        self.safe_set_widget_text('sensor_humidity', f"Humidity: {humidity_value:.1f}%")
        self.safe_set_widget_text('sensor_combined', f"CO2: {co2_value} ppm, TVOC: {tvoc_value} ppb")
        self.safe_set_widget_text('air_quality', f"Air Quality: {air_quality}")
        
        # Weekly forecast
        weekly_forecast = weather.get("weekly_forecast", [])
        weekly_container = self.safe_get_widget('weekly_forecast_container')
        
        if weekly_container:
            # Clear previous widgets
            weekly_container.clear_widgets()
            
            # Add day items
            if weekly_forecast:
                for day_data in weekly_forecast:
                    day_item = DayForecastItem(day_data)
                    weekly_container.add_widget(day_item)
                
                # Ensure minimum height for scrolling
                if len(weekly_forecast) < 7:
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
                
                # Add padding
                padding = BoxLayout(size_hint_y=None, height=dp(200))
                weekly_container.add_widget(padding)
            
            # Force layout update
            self.schedule_once(lambda dt: self._update_scroll_size(), 0.2)

    def _update_scroll_size(self):
        """Обновить размер прокрутки"""
        container = self.safe_get_widget('weekly_forecast_container')
        if container:
            min_height = dp(300)
            if container.height < min_height:
                container.height = min_height

    def update_weather(self):
        """Принудительно обновить погоду"""
        logger.info("Manual refresh requested")
        self.update_weather_data()
        self.update_sensor_data()
        self.display_weather()