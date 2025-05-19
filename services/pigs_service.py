import json
import os
from datetime import datetime

class PigsService:
    def __init__(self, config_path="config/pigs.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        # Set default configuration
        default_config = {
            "pigs": [
                {"name": "Korovka"},
                {"name": "Karamelka"}
            ],
            "bars": {
                "water": {
                    "label": "Water",
                    "max_hours": 8,
                    "last_reset": self.get_current_time_str()
                },
                "food": {
                    "label": "Food",
                    "max_hours": 6,
                    "last_reset": self.get_current_time_str()
                },
                "clean": {
                    "label": "Cleaning",
                    "max_hours": 12,
                    "last_reset": self.get_current_time_str()
                }
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            else:
                # Create directory if not exists
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                
                # Save default config
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
        except Exception as e:
            print(f"Error loading pigs config: {e}")
            return default_config
    
    def save_config(self):
        try:
            # Make sure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving pigs config: {e}")
    
    def get_current_time_str(self):
        return datetime.now().isoformat()
    
    def parse_iso_datetime(self, datetime_str):
        """Parse ISO format datetime string without dateutil dependency"""
        try:
            # Handle fractional seconds
            if '.' in datetime_str:
                datetime_str = datetime_str.split('.')[0]
                
            # Handle timezone info
            if '+' in datetime_str:
                datetime_str = datetime_str.split('+')[0]
            elif 'Z' in datetime_str:
                datetime_str = datetime_str.replace('Z', '')
                
            # Parse the clean datetime string
            dt_format = "%Y-%m-%dT%H:%M:%S"
            return datetime.strptime(datetime_str, dt_format)
        except Exception as e:
            print(f"Error parsing datetime: {e}")
            return datetime.now()
    
    def get_bar_percentage(self, key):
        """
        Calculate percentage of time remaining for a bar
        Returns percentage from 0 to 100
        """
        bar_config = self.config["bars"].get(key, {})
        max_hours = bar_config.get("max_hours", 24)
        last_reset_str = bar_config.get("last_reset", self.get_current_time_str())
        
        try:
            # Parse datetime without using dateutil
            last_reset = self.parse_iso_datetime(last_reset_str)
            now = datetime.now()
            
            # Calculate elapsed time in hours
            elapsed_hours = (now - last_reset).total_seconds() / 3600
            
            # Calculate percentage remaining
            if elapsed_hours >= max_hours:
                return 0  # Fully depleted
            
            # Calculate percentage remaining (inverse of progress)
            percentage = 100 - (elapsed_hours / max_hours * 100)
            return max(0, min(100, percentage))  # Ensure within [0, 100] range
            
        except Exception as e:
            print(f"Error calculating bar percentage: {e}")
            return 50  # Default value on error
    
    def get_all_values(self):
        """
        Get all bar values and calculate overall status
        Returns (dict of bar percentages, overall status as 0-1 float)
        """
        result = {}
        total_percentage = 0
        
        for key in self.config["bars"].keys():
            percentage = self.get_bar_percentage(key)
            result[key] = percentage
            total_percentage += percentage
        
        # Average percentage across all bars
        overall_status = total_percentage / len(self.config["bars"]) / 100
        
        return result, overall_status
    
    def reset_bar(self, key):
        """Reset a specific bar to full"""
        if key in self.config["bars"]:
            self.config["bars"][key]["last_reset"] = self.get_current_time_str()
            self.save_config()
            print(f"Bar {key} has been reset")
        else:
            print(f"Error: Bar {key} not found in config")