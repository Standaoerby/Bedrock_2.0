from datetime import datetime, timedelta
from kivy.properties import BooleanProperty, StringProperty

from classes.base_screen import BaseScreen


DAYS_FULL = {
    1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
    5: "Friday", 6: "Saturday", 7: "Sunday",
}

DAYS_SHORT = {
    1: "monday", 2: "tuesday", 3: "wednesday", 4: "thursday", 5: "friday",
}


class ScheduleScreen(BaseScreen):
    page_key = StringProperty("schedule")

    week_mode = BooleanProperty(False)
    today_date = StringProperty("")
    today_day = StringProperty("")
    tomorrow_date = StringProperty("")
    tomorrow_day = StringProperty("")

    def do_on_pre_enter(self):
        self.show_today_tomorrow()

    def show_today_tomorrow(self):
        self.week_mode = False
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        today_n = today.isoweekday()
        tomorrow_n = tomorrow.isoweekday()
        self.today_date = today.strftime("%d %b")
        self.today_day = DAYS_FULL[today_n]
        self.tomorrow_date = tomorrow.strftime("%d %b")
        self.tomorrow_day = DAYS_FULL[tomorrow_n]
        schedule = self.get_app().schedule_service.schedule

        def lessons_text(day, only_subjects=False):
            lessons = schedule.get(str(day), [])
            if not lessons:
                return "Free Day"
            if only_subjects:
                return "\n".join(l["subject"] for l in lessons)
            return "\n".join(f'{l["start"]} — {l["subject"]}' for l in lessons)

        if "today_label" in self.ids:
            self.ids.today_label.text = lessons_text(today_n)
        if "tomorrow_label" in self.ids:
            self.ids.tomorrow_label.text = lessons_text(tomorrow_n, only_subjects=True)

    def show_week(self):
        self.week_mode = True
        schedule = self.get_app().schedule_service.schedule
        for day_num in range(1, 6):
            lessons = schedule.get(str(day_num), [])
            day_id = DAYS_SHORT[day_num] + "_label"
            if day_id not in self.ids:
                continue
            if not lessons:
                self.ids[day_id].text = "Free Day"
            else:
                # Unique subjects (preserve order via dict)
                subjects = {l.get("subject", ""): True for l in lessons}
                self.ids[day_id].text = "\n".join(subjects)

    def toggle_week_mode(self):
        if self.week_mode:
            self.show_today_tomorrow()
        else:
            self.show_week()
        self.get_app().play_sound("success")
