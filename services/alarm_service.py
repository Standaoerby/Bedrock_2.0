import json
import os
import logging
import traceback

logger = logging.getLogger("AlarmService")

class AlarmService:
    def __init__(self, path="config/alarm.json"):
        self.path = path
        self.alarm = None
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.alarm = data
                    elif isinstance(data, list) and data:
                        self.alarm = data[0]
                    else:
                        self.create_default_alarm()
                
                logger.info(f"Alarm loaded: {self.alarm}")
            else:
                self.create_default_alarm()
        except Exception as e:
            logger.error(f"Error loading alarm settings: {e}")
            logger.error(traceback.format_exc())
            self.create_default_alarm()

    def create_default_alarm(self):
        self.alarm = {
            "time": "07:30",
            "enabled": True,
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtone": "morning.mp3",
            "fadein": False
        }
        # Make sure the config directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.save()
        logger.info("Created default alarm settings")

    def save(self):
        try:
            # Make sure the config directory exists
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.alarm, f, ensure_ascii=False, indent=2)
            logger.info(f"Alarm saved: {self.alarm}")
        except Exception as e:
            logger.error(f"Error saving alarm settings: {e}")
            logger.error(traceback.format_exc())

    def get_alarm(self):
        return self.alarm

    def set_alarm(self, alarm):
        self.alarm = alarm
        self.save()
        
    def verify_ringtones(self):
        """Verify that ringtone files exist and are valid"""
        if not self.alarm:
            return False
            
        ringtone = self.alarm.get("ringtone")
        if not ringtone:
            return False
            
        # Check if ringtone file exists
        folder = "media/ringtones"
        path = os.path.join(folder, ringtone)
        
        if not os.path.exists(path):
            logger.warning(f"Ringtone file not found: {path}")
            return False
            
        # File exists
        return True