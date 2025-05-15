from kivymd.uix.screen import MDScreen
from datetime import datetime, timedelta

DAYS_RU = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday"
}
TYPES_RU = {"0": "School", "1": "Extra"}

class ScheduleScreen(MDScreen):
    week_mode = False

    def on_pre_enter(self):
        self.show_today_tomorrow()

    def show_today_tomorrow(self):
        self.week_mode = False
        today = datetime.now().isoweekday()  # 1=пн, ... 7=вс
        tomorrow = today + 1 if today < 7 else 1
        app = self.get_app()
        schedule = app.schedule_service.schedule

        def lessons_text(day):
            lessons = schedule.get(str(day), [])
            if not lessons:
                return "Free Day"
            return "\n".join(
                f'{l["start"]} — {l["subject"]}' #({TYPES_RU.get(l.get("type", "0"), "?")})'
                for l in lessons
            )
        self.ids.today_label.text = lessons_text(today)
        self.ids.tomorrow_label.text = lessons_text(tomorrow)
        self.ids.week_label.opacity = 0
        self.ids.week_button.text = "All week"

    def show_week(self):
        self.week_mode = True
        app = self.get_app()
        schedule = app.schedule_service.schedule
        text = ""
        for day_num in range(1, 8):
            lessons = schedule.get(str(day_num), [])
            if not lessons:
                continue
            text += f"[b]{DAYS_RU[day_num]}[/b]:\n"
            for l in lessons:
                t = l.get("start", "")
                subj = l.get("subject", "")
                typ = TYPES_RU.get(l.get("type", "0"), "?")
                text += f"   {t} — {subj} ({typ})\n"
            text += "\n"
        self.ids.week_label.text = text.strip()
        self.ids.week_label.opacity = 1
        self.ids.today_label.text = ""
        self.ids.tomorrow_label.text = ""
        self.ids.week_button.text = "Back to Today"

    def toggle_week_mode(self):
        if self.week_mode:
            self.show_today_tomorrow()
        else:
            self.show_week()

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()
