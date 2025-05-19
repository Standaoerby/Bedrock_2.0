from datetime import datetime
from kivy.clock import Clock
from classes.alarm_popup import AlarmPopup

class AlarmClock:
    """Manages alarm checking and triggering"""
    
    def __init__(self, app, check_interval=30):
        """
        Initialize alarm clock service
        
        Args:
            app: Main application instance
            check_interval: How often to check alarm time in seconds
        """
        self.app = app
        self.check_interval = check_interval
        self.alarm_event = None
        self.active_popup = None
        self.last_check_date = None  # To detect date changes
        
    def start(self):
        """Start the alarm clock service"""
        # Check every 30 seconds by default
        self.alarm_event = Clock.schedule_interval(self.check_alarm, self.check_interval)
        print("Alarm clock service started")
        
    def stop(self):
        """Stop the alarm clock service"""
        if self.alarm_event:
            self.alarm_event.cancel()
            self.alarm_event = None
        print("Alarm clock service stopped")
        
    def check_alarm(self, dt):
        """Check if it's time to trigger the alarm"""
        current_time = datetime.now()
        current_date = current_time.date()
        
        # If date changed, log it (helpful for debugging)
        if self.last_check_date != current_date:
            self.last_check_date = current_date
            print(f"Date changed to {current_date}")
            
        # Get current day of week (Mon, Tue, etc.)
        current_day = current_time.strftime("%a")
        
        # Format current time to HH:MM
        current_time_str = current_time.strftime("%H:%M")
        
        # Get alarm settings
        alarm = self.app.alarm_service.get_alarm()
        if not alarm:
            return
            
        alarm_time = alarm.get("time", "")
        alarm_enabled = alarm.get("enabled", False)
        alarm_repeat = alarm.get("repeat", [])
        alarm_ringtone = alarm.get("ringtone", "morning.mp3")
        alarm_fadein = alarm.get("fadein", False)
        
        # Check if alarm should trigger
        if (alarm_enabled and 
            current_time_str == alarm_time and 
            current_day in alarm_repeat):
            
            print(f"Alarm triggered! Time: {current_time_str}, Day: {current_day}")
            self.trigger_alarm(alarm_ringtone, alarm_fadein)
            
    def trigger_alarm(self, ringtone, fadein):
        """Show alarm popup and play sound"""
        # If there's already an active popup, don't create another one
        if self.active_popup:
            return
            
        # Create and show alarm popup
        self.active_popup = AlarmPopup(ringtone=ringtone, fadein=fadein)
        self.active_popup.bind(on_dismiss=self._on_popup_dismiss)
        self.active_popup.open()
        
        # Start playing the alarm sound
        self.active_popup.start_alarm()
        
    def _on_popup_dismiss(self, instance):
        """Called when popup is dismissed"""
        self.active_popup = None
        
    def stop_alarm(self):
        """Stop the currently active alarm if any"""
        if self.active_popup:
            self.active_popup.stop_alarm()
            self.active_popup = None