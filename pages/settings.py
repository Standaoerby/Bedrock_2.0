from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
import json
import os
from datetime import datetime
import logging
from utils.error_handler import ErrorHandler

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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sensor_update_event = None
        self._settings_loaded = False

    def on_pre_enter(self):
        """Called when entering the screen"""
        try:
            self.load_settings()
            self.check_dark_mode_availability()
            self.update_sensor_status()
            
            # Update sensor status periodically
            if self._sensor_update_event:
                self._sensor_update_event.cancel()
            self._sensor_update_event = Clock.schedule_interval(self.update_sensor_status, 5)
            
            self._settings_loaded = True
            logger.info("Settings screen initialized")
            
        except Exception as e:
            logger.error(f"Error in on_pre_enter: {e}")
    
    def on_leave(self):
        """Called when leaving the screen"""
        try:
            if self._sensor_update_event:
                self._sensor_update_event.cancel()
                self._sensor_update_event = None
        except Exception as e:
            logger.error(f"Error in on_leave: {e}")
    
    @ErrorHandler.handle_exception
    def check_dark_mode_availability(self):
        """Check if dark mode is available"""
        try:
            dark_theme_path = f"themes/{self.current_theme}/dark/theme.json"
            self.dark_mode_available = os.path.exists(dark_theme_path)
            
            if not self.dark_mode_available:
                logger.info("Dark theme not available - creating default")
                app = self.get_app()
                if app and hasattr(app, 'theme_manager'):
                    # Try to create dark theme
                    if app.theme_manager.create_default_dark_theme():
                        self.dark_mode_available = True
                        logger.info("Dark theme created successfully")
                    else:
                        self.dark_mode_enabled = False
                        logger.warning("Failed to create dark theme")
            
            logger.info(f"Dark mode available: {self.dark_mode_available}")
            
        except Exception as e:
            logger.error(f"Error checking dark mode availability: {e}")
            self.dark_mode_available = False
    
    @ErrorHandler.handle_exception
    def load_settings(self):
        """Load settings from config file"""
        try:
            config_path = "config/user.json"
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            else:
                # Create default settings
                settings = {
                    "theme": "minecraft",
                    "theme_mode": "light",
                    "username": "",
                    "birthdate": "2000-01-01",
                    "auto_theme_enabled": True,
                    "theme_switch_delay": 2
                }
                
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
                except ValueError as e:
                    logger.warning(f"Invalid birthdate format: {birthdate}, error: {e}")
                    self.birth_year = "2000"
                    self.birth_month = "1"
                    self.birth_day = "1"
            
            logger.info("Settings loaded successfully")
                        
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Set safe defaults
            self.current_theme = "minecraft"
            self.dark_mode_enabled = False
            self.username = ""
            self.auto_theme_enabled = True
            self.light_sensor_threshold = 2
    
    @ErrorHandler.handle_exception
    def update_sensor_status(self, dt=None):
        """Update sensor status"""
        try:
            app = self.get_app()
            if not app:
                return
                
            # Check if sensor service is available and running
            if hasattr(app, 'sensor_service') and app.sensor_service:
                light_status = app.sensor_service.get_light_sensor_status()
                
                self.light_sensor_available = True
                
                # Update UI if IDs are available
                if hasattr(self, 'ids') and hasattr(self.ids, 'light_sensor_status'):
                    current_level = light_status.get('current_level', True)
                    using_mock = light_status.get('using_mock', True)
                    
                    status_text = "Light" if current_level else "Dark"
                    sensor_type = "Mock" if using_mock else "Real"
                    
                    self.ids.light_sensor_status.text = f"Sensor: {status_text} ({sensor_type})"
                    
                    # Set color based on sensor type
                    if using_mock:
                        self.ids.light_sensor_status.color = [0.8, 0.8, 0, 1]  # Yellow for mock
                    else:
                        self.ids.light_sensor_status.color = [0, 0.8, 0, 1]  # Green for real
            else:
                self.light_sensor_available = False
                if hasattr(self, 'ids') and hasattr(self.ids, 'light_sensor_status'):
                    self.ids.light_sensor_status.text = "Sensor: Offline"
                    self.ids.light_sensor_status.color = [0.8, 0, 0, 1]  # Red for offline
                    
        except Exception as e:
            logger.error(f"Error updating sensor status: {e}")
    
    @ErrorHandler.handle_exception
    def toggle_dark_mode(self, enabled):
        """УПРОЩЕННОЕ переключение dark mode"""
        app = self.get_app()
        
        # Check if dark mode is available
        if enabled and not self.dark_mode_available:
            logger.warning("Cannot enable dark mode - not available")
            if app:
                app.play_sound("error")
            self.dark_mode_enabled = False
            
            # Update UI button
            if hasattr(self, 'ids') and hasattr(self.ids, 'dark_mode_button'):
                self.ids.dark_mode_button.text = "OFF"
            return
        
        # Update state
        self.dark_mode_enabled = enabled
        
        # Play sound
        if app:
            if enabled:
                app.play_sound("success")
            else:
                app.play_sound("click")
        
        # Update UI button text
        if hasattr(self, 'ids') and hasattr(self.ids, 'dark_mode_button'):
            self.ids.dark_mode_button.text = "ON" if enabled else "OFF"
        
        logger.info(f"Dark mode toggled: {enabled}")
    
    @ErrorHandler.handle_exception
    def toggle_auto_theme(self, enabled):
        """Toggle auto theme switching"""
        app = self.get_app()
        
        # Check prerequisites for auto theme
        if enabled and not self.dark_mode_available:
            logger.warning("Cannot enable auto theme - dark theme not available")
            if app:
                app.play_sound("error")
            self.auto_theme_enabled = False
            
            # Update UI button
            if hasattr(self, 'ids') and hasattr(self.ids, 'auto_theme_button'):
                self.ids.auto_theme_button.text = "OFF"
            return
        
        # Update state
        self.auto_theme_enabled = enabled
        
        # Play sound
        if app and enabled:
            app.play_sound("success")
        
        # Update UI button text
        if hasattr(self, 'ids') and hasattr(self.ids, 'auto_theme_button'):
            self.ids.auto_theme_button.text = "ON" if enabled else "OFF"
        
        logger.info(f"Auto theme toggled: {enabled}")
    
    @ErrorHandler.handle_exception
    def set_threshold_delay(self, value):
        """Set theme switch delay"""
        try:
            new_threshold = max(1, min(int(value), 5))
            self.light_sensor_threshold = new_threshold
            
            # Update sensor calibration immediately
            app = self.get_app()
            if app and hasattr(app, 'sensor_service') and app.sensor_service:
                app.sensor_service.calibrate_light_sensor(self.light_sensor_threshold)
                logger.info(f"Sensor threshold updated: {new_threshold}s")
                
        except Exception as e:
            logger.error(f"Error setting threshold delay: {e}")
    
    @ErrorHandler.handle_exception
    def manual_theme_test(self):
        """УПРОЩЕННЫЙ manual theme test"""
        app = self.get_app()
        if not app:
            return
            
        try:
            # Check if we can perform the test
            if not self.dark_mode_available:
                logger.warning("Cannot test theme - dark mode not available")
                app.play_sound("error")
                return
            
            # Check if switching is in progress
            if app.theme_manager.is_switching():
                logger.warning("Theme switch in progress, test cancelled")
                app.play_sound("error")
                return
            
            # Toggle theme mode for testing
            current_mode = app.theme_mode
            new_mode = "dark" if current_mode == "light" else "light"
            
            logger.info(f"Manual theme test: switching to {new_mode} for 3 seconds")
            
            # Switch theme
            if app.switch_theme_mode(new_mode):
                app.play_sound("success")
                
                # Schedule switch back after 3 seconds
                def switch_back(dt):
                    try:
                        # Only switch back if we're still in test mode
                        if app.theme_mode == new_mode:
                            if app.switch_theme_mode(current_mode):
                                logger.info(f"Theme test completed - switched back to {current_mode}")
                            else:
                                logger.error("Failed to switch back after theme test")
                        else:
                            logger.info("Theme changed during test - skip switch back")
                    except Exception as e:
                        logger.error(f"Error switching back after theme test: {e}")
                
                Clock.schedule_once(switch_back, 3)
            else:
                app.play_sound("error")
                logger.error("Theme test failed - could not switch theme")
                
        except Exception as e:
            logger.error(f"Error in manual theme test: {e}")
            if app:
                app.play_sound("error")
    
    @ErrorHandler.handle_exception
    def save_all_settings(self):
        """УПРОЩЕННОЕ сохранение настроек"""
        try:
            app = self.get_app()
            if app:
                app.play_sound("success")
            
            # Get values from UI
            if hasattr(self, 'ids'):
                if hasattr(self.ids, 'username_input'):
                    self.username = self.ids.username_input.text
                
                # Update birthdate from UI fields
                self.update_birthdate()
            
            # Create settings object
            settings = {
                "theme": self.current_theme,
                "theme_mode": "dark" if self.dark_mode_enabled else "light",
                "username": self.username,
                "birthdate": self.get_birthdate_string(),
                "auto_theme_enabled": self.auto_theme_enabled,
                "theme_switch_delay": int(self.light_sensor_threshold),
                "volume_settings": {
                    "enabled": True,
                    "step": 5,
                    "min_volume": 0,
                    "max_volume": 100,
                    "feedback_sounds": True
                },
                "sensor_settings": {
                    "light_sensor_enabled": True,
                    "calibration_time": int(self.light_sensor_threshold),
                    "mock_mode": False
                }
            }
            
            # Save to file
            os.makedirs("config", exist_ok=True)
            with open("config/user.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            # Update app
            if app:
                old_mode = app.theme_mode
                new_mode = "dark" if self.dark_mode_enabled else "light"
                
                # Update app properties
                app.theme_name = self.current_theme
                app.user_config.update(settings)
                
                # Update auto theme setting
                app.set_auto_theme_enabled(self.auto_theme_enabled)
                
                # Recalibrate sensor if settings changed
                if hasattr(app, 'sensor_service') and app.sensor_service:
                    app.sensor_service.calibrate_light_sensor(int(self.light_sensor_threshold))
                
                # Switch theme if manually changed
                if old_mode != new_mode:
                    logger.info(f"Manual theme change requested: {old_mode} → {new_mode}")
                    if not app.theme_manager.is_switching():
                        app.switch_theme_mode(new_mode)
                    else:
                        logger.info("Theme switch delayed - another switch in progress")
                
            logger.info("All settings saved successfully")
                
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            app = self.get_app()
            if app:
                app.play_sound("error")
    
    @ErrorHandler.handle_exception
    def update_birthdate(self):
        """Update birth date from UI fields"""
        try:
            if not hasattr(self, 'ids'):
                return
                
            # Get values from UI
            day_text = getattr(self.ids, 'birth_day', None)
            month_text = getattr(self.ids, 'birth_month', None)
            year_text = getattr(self.ids, 'birth_year', None)
            
            if day_text and month_text and year_text:
                day_str = day_text.text.strip() if hasattr(day_text, 'text') else str(self.birth_day)
                month_str = month_text.text.strip() if hasattr(month_text, 'text') else str(self.birth_month)
                year_str = year_text.text.strip() if hasattr(year_text, 'text') else str(self.birth_year)
                
                if day_str and month_str and year_str:
                    day = int(day_str)
                    month = int(month_str)
                    year = int(year_str)
                    
                    # Validate date ranges
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                        self.birth_day = str(day)
                        self.birth_month = str(month)
                        self.birth_year = str(year)
                        logger.debug(f"Birthdate updated: {day}/{month}/{year}")
                    else:
                        logger.warning(f"Invalid date values: {day}/{month}/{year}")
                        
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error updating birthdate: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating birthdate: {e}")
    
    def get_birthdate_string(self):
        """Get birth date as formatted string"""
        try:
            day = int(self.birth_day) if self.birth_day else 1
            month = int(self.birth_month) if self.birth_month else 1
            year = int(self.birth_year) if self.birth_year else 2000
            
            # Validate and correct if necessary
            day = max(1, min(day, 31))
            month = max(1, min(month, 12))
            year = max(1900, min(year, 2100))
            
            return f"{year:04d}-{month:02d}-{day:02d}"
        except Exception as e:
            logger.error(f"Error formatting birthdate: {e}")
            return "2000-01-01"
    
    def get_app(self):
        """Get app instance"""
        from kivy.app import App
        return App.get_running_app()