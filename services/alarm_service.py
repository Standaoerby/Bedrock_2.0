"""
Alarm service for managing alarm clock functionality
"""
import os
import json
import logging
import time
import threading
from datetime import datetime, timedelta

# Initialize logging
logger = logging.getLogger("AlarmService")

class AlarmService:
    """Service for managing alarm settings and notifications"""
    
    def __init__(self):
        """Initialize alarm service"""
        self.config_file = os.path.join("config", "alarm.json")
        self.active_alarms = []
        self.alarm_check_thread = None
        self.running = False
        self.last_check_day = -1
        
        # Create necessary directories
        os.makedirs("config", exist_ok=True)
        
        # Load default settings
        self.default_alarm = {
            "time": "07:30",
            "enabled": True,
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtone": "morning.mp3",
            "fadein": False,
        }
        
        # Load configuration
        self.load_config()
        
        # Start background thread
        self.start()
    
    def start(self):
        """Start the alarm service background thread"""
        if self.alarm_check_thread is None or not self.alarm_check_thread.is_alive():
            self.running = True
            self.alarm_check_thread = threading.Thread(target=self._check_alarms_loop, daemon=True)
            self.alarm_check_thread.start()
            logger.info("Alarm service started")
    
    def stop(self):
        """Stop the alarm service background thread"""
        self.running = False
        if self.alarm_check_thread and self.alarm_check_thread.is_alive():
            self.alarm_check_thread.join(timeout=1.0)
        logger.info("Alarm service stopped")
    
    def load_config(self):
        """Load alarm configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self.alarm_data = json.load(f)
                logger.info(f"Loaded alarm configuration from {self.config_file}")
            else:
                # Use default settings if file doesn't exist
                self.alarm_data = {"alarm": self.default_alarm}
                self.save_config()
                logger.info("Created default alarm configuration")
        except Exception as e:
            logger.error(f"Error loading alarm configuration: {e}")
            self.alarm_data = {"alarm": self.default_alarm}
    
    def save_config(self):
        """Save alarm configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.alarm_data, f, indent=2)
            logger.info(f"Saved alarm configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving alarm configuration: {e}")
            return False
    
    def get_alarm(self):
        """Get the current alarm settings"""
        return self.alarm_data.get("alarm", self.default_alarm)
    
    def set_alarm(self, alarm_settings):
        """Update the alarm settings"""
        self.alarm_data["alarm"] = alarm_settings
        self.save_config()
        return True
    
    def _check_alarms_loop(self):
        """Background thread for checking alarms"""
        logger.info("Alarm check thread started")
        
        # Sleep a bit on startup to let the app initialize fully
        time.sleep(5)
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check alarms once per minute maximum
                time.sleep(60 - now.second % 60)
                
                # Only process alarms if enabled
                alarm = self.get_alarm()
                if not alarm.get("enabled", False):
                    continue
                
                # Get current time
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                day_name = now.strftime("%a")  # Mon, Tue, etc.
                
                # Check if today is in the repeat days
                repeat_days = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
                
                if day_name in repeat_days:
                    # Check if it's time to trigger the alarm
                    alarm_time = alarm.get("time", "07:30")
                    
                    # Only trigger once per minute window
                    if current_time == alarm_time and now.day != self.last_check_day:
                        logger.info(f"Alarm triggered at {current_time}")
                        self.last_check_day = now.day
                        
                        # Trigger the alarm if the app is running
                        self._trigger_alarm(alarm)
            
            except Exception as e:
                logger.error(f"Error in alarm check thread: {e}")
                time.sleep(60)  # Sleep and retry
    
    def _trigger_alarm(self, alarm):
        """Trigger the alarm - notify the app and launch alarm"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if app:
                ringtone = alarm.get("ringtone", "morning.mp3")
                fadein = alarm.get("fadein", False)
                
                # Отправляем уведомление через notification_service
                if hasattr(app, 'notification_service'):
                    app.notification_service.show_notification(
                        title="Alarm", 
                        message=f"It's time! {alarm.get('time', '')}", 
                        notification_type="alarm",
                        data={"ringtone": ringtone, "fadein": fadein}
                    )
                    logger.info(f"Alarm notification sent: {ringtone}, fadein: {fadein}")
                
                # Запускаем будильник напрямую через alarm_clock
                if hasattr(app, 'alarm_clock'):
                    app.alarm_clock.trigger_alarm(ringtone, fadein)
                    logger.info(f"Alarm triggered via alarm_clock: {ringtone}, fadein: {fadein}")
                    return True
                else:
                    logger.warning("App.alarm_clock not available")
            else:
                logger.warning("App not available")
        except Exception as e:
            logger.error(f"Error triggering alarm: {e}")
        
        return False
    
    def test_alarm(self):
        """Test the alarm by triggering it immediately (for debugging)"""
        alarm = self.get_alarm()
        return self._trigger_alarm(alarm)