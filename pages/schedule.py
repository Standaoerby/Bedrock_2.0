# pages/schedule.py
from utils.common import BasePage
from datetime import datetime
from kivy.properties import StringProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
import logging

logger = logging.getLogger("ScheduleScreen")

# Abbreviated day names
DAYS_ABBR = {
    1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI", 6: "SAT", 7: "SUN"
}

class ScheduleScreen(BasePage):
    """Экран расписания"""
    
    today_date = StringProperty("")
    today_day = StringProperty("")
    
    def on_pre_enter(self):
        """Вход на экран"""
        logger.info("Entering ScheduleScreen")
        
        self._setup_dates()
        self._create_weekly_schedule()
    
    def _setup_dates(self):
        """Настроить информацию о дате"""
        today = datetime.now()
        self.today_date = today.strftime("%d %b")
        self.today_day = DAYS_ABBR[today.isoweekday()]
    
    def _create_weekly_schedule(self):
        """Создать отображение недельного расписания"""
        app = self.get_app()
        
        # Clear existing widgets
        header_grid = self.safe_get_widget('header_grid')
        schedule_content = self.safe_get_widget('schedule_content')
        
        if header_grid:
            header_grid.clear_widgets()
        if schedule_content:
            schedule_content.clear_widgets()
        
        # Get today's weekday number
        today_num = datetime.now().isoweekday()
        
        # Add day headers
        if header_grid:
            for day_num in range(1, 6):  # 1-5 (Monday-Friday)
                day_name = DAYS_ABBR[day_num]
                
                # Use highlight color for current day
                if day_num == today_num:
                    color = app.theme_config.get("colors", {}).get("accent", [1, 0.8, 0, 1])
                else:
                    color = app.theme_config.get("colors", {}).get("font_highlight", [1, 1, 0.7, 1])
                
                header = Label(
                    text=day_name,
                    font_name=app.theme_config["font_name"],
                    font_size="18sp",
                    bold=True,
                    color=color
                )
                header_grid.add_widget(header)
        
        # Process each weekday schedule
        schedule = app.schedule_service.schedule
        
        # Add content for each day
        if schedule_content:
            for day_num in range(1, 6):  # 1-5 (Monday-Friday)
                day_lessons = schedule.get(str(day_num), [])
                
                # Create day column
                day_column = BoxLayout(
                    orientation="vertical",
                    size_hint_x=0.2
                )
                
                # Create container with background
                container = BoxLayout(orientation="vertical")
                
                # Set background color (highlight current day)
                with container.canvas.before:
                    if day_num == today_num:
                        Color(0.3, 0.3, 0.1, 0.8)  # Highlighted background
                    else:
                        Color(0.2, 0.2, 0.2, 0.8)  # Normal background
                    rect = Rectangle(pos=container.pos, size=container.size)
                
                # Bind rectangle to size and position changes
                def create_update_rect(rect):
                    def update_rect(instance, value):
                        rect.pos = instance.pos
                        rect.size = instance.size
                    return update_rect
                
                update_rect_fn = create_update_rect(rect)
                container.bind(pos=update_rect_fn, size=update_rect_fn)
                
                # Create scroll view
                scroll = ScrollView(
                    do_scroll_x=False,
                    do_scroll_y=True,
                    bar_width=dp(5),
                    bar_color=[0.7, 0.7, 0.7, 0.9],
                    bar_inactive_color=[0.5, 0.5, 0.5, 0.5]
                )
                
                # Create content layout
                content = BoxLayout(
                    orientation="vertical",
                    spacing=dp(2),
                    padding=dp(5),
                    size_hint_y=None
                )
                content.bind(minimum_height=content.setter('height'))
                
                # Fill with content
                if not day_lessons:
                    # No lessons for this day
                    label = Label(
                        text="Free Day",
                        font_name=app.theme_config["font_name"],
                        color=[1, 1, 1, 1],
                        font_size="16sp",
                        halign="left",
                        valign="top",
                        text_size=(dp(150), None),
                        size_hint_y=None,
                        height=dp(40)
                    )
                    content.add_widget(label)
                else:
                    # Add each subject
                    for lesson in day_lessons:
                        subject = lesson.get("subject", "")
                        
                        label = Label(
                            text=subject,
                            font_name=app.theme_config["font_name"],
                            color=[1, 1, 1, 1],
                            font_size="16sp",
                            halign="left",
                            valign="middle",
                            text_size=(dp(150), None),
                            size_hint_y=None,
                            height=dp(30),
                            padding=[dp(5), dp(2)]
                        )
                        content.add_widget(label)
                
                # Assemble the column
                scroll.add_widget(content)
                container.add_widget(scroll)
                day_column.add_widget(container)
                
                # Add to main content
                schedule_content.add_widget(day_column)

