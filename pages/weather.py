from kivymd.uix.screen import MDScreen

class WeatherScreen(MDScreen):
    def on_pre_enter(self):
        app = self.get_app()
        weather = app.weather_service.get_weather()
        cur = weather["current"]
        forecast = weather["forecast_5h"]
        self.ids.weather_label.text = (
            f'Сейчас: {cur["temperature"]}°C, {cur["condition"]}\n'
            f'Вероятность осадков: {cur["precipitation_probability"]}%\n\n'
            f'Через 5 часов: {forecast["temperature"]}°C, {forecast["condition"]}\n'
            f'Осадки: {forecast["precipitation_probability"]}%'
        )

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
