from kivymd.uix.screen import MDScreen

class WeatherScreen(MDScreen):
    def on_pre_enter(self):
        # Чтобы не обращаться к ids слишком рано, делаем отложенный запуск
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.display_weather(), 0)

    def display_weather(self):
        app = self.get_app()
        weather = app.weather_service.get_weather()
        cur = weather.get("current", {})
        forecast = weather.get("forecast_5h", {})

        # Формируем строку для отображения
        lines = []

        # Сейчас
        if cur:
            lines.append(f'Сейчас: {cur.get("temperature", "—")}°C, {cur.get("condition", "—")}')
            lines.append(f'Вероятность осадков: {cur.get("precipitation_probability", "—")}%')

        # Прогноз на 5 часов/завтра/ближайшее
        if forecast and forecast.get("temperature") is not None:
            lines.append("")
            lines.append(f'Через 5 часов: {forecast.get("temperature", "—")}°C, {forecast.get("condition", "—")}')
            if forecast.get("precipitation_probability") is not None:
                lines.append(f'Вероятность осадков: {forecast["precipitation_probability"]}%')
        else:
            lines.append("")
            lines.append("Нет прогноза на 5 часов или завтра")

        self.ids.weather_label.text = "\n".join(lines)

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
