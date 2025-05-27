"""
Simplified Alarm service - только управление настройками
Логика проверки времени перенесена в AlarmClock
"""
import os
import json
import logging

logger = logging.getLogger("AlarmService")

class AlarmService:
    """Упрощённый сервис для управления настройками будильника"""
    
    def __init__(self):
        """Initialize alarm service"""
        self.config_file = os.path.join("config", "alarm.json")
        
        # Create necessary directories
        os.makedirs("config", exist_ok=True)
        
        # Default alarm settings
        self.default_alarm = {
            "time": "07:30",
            "enabled": True,  # По умолчанию включен
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtone": "robot.mp3",
            "fadein": False,
        }
        
        # Load configuration
        self.load_config()
        
        logger.info("AlarmService initialized (settings management only)")
    
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
        logger.info(f"Alarm settings updated: {alarm_settings}")
        return True
    
    def test_alarm(self):
        """Test the alarm by triggering it immediately"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if app and hasattr(app, 'alarm_clock'):
                alarm = self.get_alarm()
                ringtone = alarm.get("ringtone", "robot.mp3")
                fadein = alarm.get("fadein", False)
                
                logger.info("Testing alarm...")
                app.alarm_clock.trigger_alarm(ringtone, fadein)
                return True
            else:
                logger.error("App or alarm_clock not available for testing")
                return False
                
        except Exception as e:
            logger.error(f"Error testing alarm: {e}")
            return False
    
    def stop(self):
        """Stop method for compatibility (no background thread to stop)"""
        logger.info("AlarmService stopped (no background operations)")