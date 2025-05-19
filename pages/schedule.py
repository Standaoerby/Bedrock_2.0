from kivymd.uix.screen import MDScreen
from datetime import datetime, timedelta
from kivy.properties import BooleanProperty, StringProperty

DAYS_RU = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday", 
    5: "Friday",
    6: "Saturday",
    7: "Sunday"
}

DAYS_SHORT = {
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday"
}

TYPES_RU = {"0": "School", "1": "Extra"}

class ScheduleScreen(MDScreen):
    week_mode = BooleanProperty(False)
    today_date = StringProperty("")
    today_day = StringProperty("")
    tomorrow_date = StringProperty("")
    tomorrow_day = StringProperty("")

    def on_pre_enter(self):
        self.show_today_tomorrow()

    def show_today_tomorrow(self):
        """Display today and tomorrow schedules with times"""
        self.week_mode = False
        
        # Get today and tomorrow dates
        today_date = datetime.now()
        tomorrow_date = today_date + timedelta(days=1)
        
        # Get day numbers (1-7 for Monday-Sunday)
        today_daynum = today_date.isoweekday()
        tomorrow_daynum = tomorrow_date.isoweekday()
        
        # Set date and day properties for display in the format "15 May, Thursday"
        self.today_date = today_date.strftime("%d %b")
        self.today_day = DAYS_RU[today_daynum]
        self.tomorrow_date = tomorrow_date.strftime("%d %b")
        self.tomorrow_day = DAYS_RU[tomorrow_daynum]
        
        # Get schedule data
        app = self.get_app()
        schedule = app.schedule_service.schedule

        def lessons_text(day, only_subjects=False):
            lessons = schedule.get(str(day), [])
            if not lessons:
                return "Free Day"
            if only_subjects:
                return "\n".join(l["subject"] for l in lessons)
            return "\n".join(f'{l["start"]} — {l["subject"]}' for l in lessons)
        
        self.ids.today_label.text = lessons_text(today_daynum)
        self.ids.tomorrow_label.text = lessons_text(tomorrow_daynum, only_subjects=True)


    def show_week(self):
        """Display weekly schedule in 5 fixed columns without bullets"""
        self.week_mode = True
        app = self.get_app()
        schedule = app.schedule_service.schedule
        
        # Fill content for each day column (Monday-Friday)
        for day_num in range(1, 6):  # 1-5 (Monday-Friday)
            lessons = schedule.get(str(day_num), [])
            day_id = DAYS_SHORT[day_num] + "_label"  # e.g., "monday_label"
            
            if not lessons:
                # No lessons this day
                self.ids[day_id].text = "Free Day"
            else:
                # Get unique subjects for this day (no duplicates)
                subjects = {}
                for l in lessons:
                    subject = l.get("subject", "")
                    subjects[subject] = True
                
                # Add each unique subject to the text
                subjects_text = "\n".join(subject for subject in subjects)
                self.ids[day_id].text = subjects_text

    def toggle_week_mode(self):
        """Toggle between daily and weekly views"""
        app = self.get_app()
        # Sound is already played by the button's on_press event in kv file
        
        if self.week_mode:
            self.show_today_tomorrow()
        else:
            self.show_week()
            
        # Play a success sound when view is changed
        app.play_sound("success")

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()