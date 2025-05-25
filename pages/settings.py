from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger("SettingsScreen")

class SettingsScreen(MDScreen):
    # Theme properties
    current_theme = StringProperty("minecraft")
    available_themes = ["minecraft"]
    dark_mode_enabled = BooleanProperty(False)
    dark_mode_available = BooleanProperty(False)
    
    # User properties
    username = StringProperty("")
    birth_day = StringProperty("")
    birth_month = StringProperty("")
    birth_year = StringProperty("")
    
    # Auto theme properties
    auto_theme_enabled = BooleanProperty(True)
    light_sensor_available = BooleanProperty(False)
    light_sensor_threshold = NumericProperty(2)
    
    def on_pre_enter(self):
        """Called when entering the screen"""
        self.load_settings()
        self.check_dark_mode_availability()
        self.update_sensor_status()
        
        # Update sensor status periodically
        self._sensor_update_event = Clock.schedule_interval(self.update_sensor_status, 5)
    
    def on_leave(self):
        """Called when leaving the screen"""
        if hasattr(self, '_sensor_update_event'):
            self._sensor_update_event.cancel()
    
    def check_dark_mode_availability(self):
        """Check if dark mode is available"""
        dark_theme_path = f"themes/{self.current_theme}/dark/theme.json"
        self.dark_mode_available = os.path.exists(dark_theme_path)
        
        if not self.dark_mode_available:
            self.dark_mode_enabled = False
    
    def load_settings(self):
        """Load settings from config file"""
        try:
            with open("config/user.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                
                # Load basic settings
                self.current_theme = settings.get("theme", "minecraft")
                self.dark_mode_enabled = settings.get("theme_mode", "light") == "dark"
                self.username = settings.get("username", "")
                self.auto_theme_enabled = settings.get("auto_theme_enabled", True)
                self.light_sensor_threshold = settings.get("theme_switch_delay", 2)
                
                # Parse birth date
                birthdate = settings.get("birthdate", "")
                if birthdate:
                    try:
                        date = datetime.strptime(birthdate, "%Y-%m-%d")
                        self.birth_year = str(date.year)
                        self.birth_month = str(date.month)
                        self.birth_day = str(date.day)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def update_sensor_status(self, dt=None):
        """Update sensor status"""
        try:
            app = self.get_app()
            if app and hasattr(app, 'sensor_service') and app.sensor_service:
                light_status = app.sensor_service.get_light_sensor_status()
                
                self.light_sensor_available = True  # Always show as available
                
                # Update UI
                if hasattr(self.ids, 'light_sensor_status'):
                    current_level = light_status.get('current_level', True)
                    status_text = "Light" if current_level else "Dark"
                    sensor_type = "Real" if not light_status.get('using_mock', True) else "Mock"
                    
                    self.ids.light_sensor_status.text = f"Sensor: {status_text} ({sensor_type})"
                    
                    # Set color
                    if light_status.get('using_mock', True):
                        self.ids.light_sensor_status.color = [0.8, 0.8, 0, 1]  # Yellow
                    else:
                        self.ids.light_sensor_status.color = [0, 0.8, 0, 1]  # Green
            else:
                self.light_sensor_available = False
                if hasattr(self.ids, 'light_sensor_status'):
                    self.ids.light_sensor_status.text = "Sensor: Offline"
                    self.ids.light_sensor_status.color = [0.8, 0, 0, 1]  # Red
                    
        except Exception as e:
            logger.error(f"Error updating sensor status: {e}")
    
    def save_all_settings(self):
        """Save all settings"""
        try:
            app = self.get_app()
            if app:
                app.play_sound("success")
            
            # Get values from UI
            if hasattr(self.ids, 'username_input'):
                self.username = self.ids.username_input.text
            
            self.update_birthdate()
            
            # Create settings object
            settings = {
                "theme": self.current_theme,
                "theme_mode": "dark" if self.dark_mode_enabled else "light",
                "username": self.username,
                "birthdate": self.get_birthdate_string(),
                "auto_theme_enabled": self.auto_theme_enabled,
                "theme_switch_delay": int(self.light_sensor_threshold)
            }
            
            # Save to file
            os.makedirs("config", exist_ok=True)
            with open("config/user.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            # Update app
            if app:
                old_mode = app.theme_mode
                app.theme_name = self.current_theme
                new_mode = "dark" if self.dark_mode_enabled else "light"
                app.set_auto_theme_enabled(self.auto_theme_enabled)
                
                # Switch theme if changed
                if old_mode != new_mode:
                    app.switch_theme_mode(new_mode)
                
            logger.info("Settings saved successfully")
                
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def change_theme(self, theme):
        """Change current theme"""
        if theme != self.current_theme:
            self.current_theme = theme
            self.check_dark_mode_availability()
    
    def toggle_dark_mode(self, enabled):
        """Toggle dark mode"""
        app = self.get_app()
        
        if self.dark_mode_available:
            self.dark_mode_enabled = enabled
            if enabled and app:
                app.play_sound("success")
        else:
            self.dark_mode_enabled = False
            if app:
                app.play_sound("error")
    
    def toggle_auto_theme(self, enabled):
        """Toggle auto theme switching"""
        app = self.get_app()
        
        # Check if we can enable auto theme
        if enabled and not self.dark_mode_available:
            logger.warning("Cannot enable auto theme - dark theme not available")
            if app:
                app.play_sound("error")
            self.auto_theme_enabled = False
            return
        
        self.auto_theme_enabled = enabled
        
        if app:
            if enabled:
                app.play_sound("success")
            
            # Update button color
            if hasattr(self.ids, 'auto_theme_button'):
                if self.auto_theme_enabled:
                    self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
                else:
                    self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
    
    def set_threshold_delay(self, value):
        """Set theme switch delay"""
        self.light_sensor_threshold = max(1, min(int(value), 5))
        
        app = self.get_app()
        if app and hasattr(app, 'sensor_service') and app.sensor_service:
            app.sensor_service.calibrate_light_sensor(self.light_sensor_threshold)
    
    def manual_theme_test(self):
        """Simple manual theme test - just switch mode immediately"""
        app = self.get_app()
        if not app:
            return
            
        # Toggle theme mode for testing
        new_mode = "dark" if app.theme_mode == "light" else "light"
        
        logger.info(f"Manual theme test: switching to {new_mode}")
        
        if app.switch_theme_mode(new_mode):
            app.play_sound("success")
            
            # Switch back after 3 seconds
            Clock.schedule_once(lambda dt: app.switch_theme_mode(app.theme_mode), 3)
        else:
            app.play_sound("error")
    
    def update_birthdate(self):
        """Update birth date from UI fields"""
        try:
            if hasattr(self.ids, 'birth_day') and hasattr(self.ids, 'birth_month') and hasattr(self.ids, 'birth_year'):
                day_text = self.ids.birth_day.text.strip()
                month_text = self.ids.birth_month.text.strip()
                year_text = self.ids.birth_year.text.strip()
                
                if day_text and month_text and year_text:
                    day = int(day_text)
                    month = int(month_text)
                    year = int(year_text)
                    
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                        self.birth_day = str(day)
                        self.birth_month = str(month)
                        self.birth_year = str(year)
        except Exception:
            pass
    
    def get_birthdate_string(self):
        """Get birth date as string"""
        try:
            day = int(self.birth_day) if self.birth_day else 1
            month = int(self.birth_month) if self.birth_month else 1
            year = int(self.birth_year) if self.birth_year else 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return "2000-01-01"
    
    def get_app(self):
        """Get app instance"""
        from kivy.app import App
        return App.get_running_app()