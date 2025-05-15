from kivymd.uix.screen import MDScreen

class AlarmScreen(MDScreen):
    def on_pre_enter(self):
        # Можно обновлять список будильников перед отображением
        self.update_alarms()

    def update_alarms(self):
        app = self.get_app()
        alarm_list = app.alarm_service.alarms
        text = "\n".join([
            f'{a["time"]} | {"ВКЛ" if a["enabled"] else "выкл"} | Повтор: {",".join(map(str, a["repeat"]))} | {a.get("label", "")}'
            for a in alarm_list
        ])
        self.ids.alarms_label.text = text

    def get_app(self):
        # Гарантировано получить App
        from kivy.app import App
        return App.get_running_app()
