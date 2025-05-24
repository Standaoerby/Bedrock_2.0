from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty, NumericProperty
from kivy.clock import Clock
import json
import os
from datetime import datetime, time
import logging

logger = logging.getLogger("SettingsScreen")

class SettingsScreen(MDScreen):
    # Existing properties
    current_theme = StringProperty("minecraft")
    available_themes = ListProperty([])
    dark_mode_enabled = BooleanProperty(False)
    dark_mode_available = BooleanProperty(False)
    username = StringProperty("")
    
    # Birth date properties
    birth_day = StringProperty("")
    birth_month = StringProperty("")
    birth_year = StringProperty("")
    
    # Auto theme properties - ИСПРАВЛЕНО
    auto_theme_enabled = BooleanProperty(True)
    light_sensor_available = BooleanProperty(False)
    current_light_level = BooleanProperty(True)  # True = light, False = dark
    light_sensor_threshold = NumericProperty(5)  # seconds (theme switch delay)
    
    # Volume properties
    current_volume = NumericProperty(50)
    volume_buttons_available = BooleanProperty(False)
    
    def on_pre_enter(self):
        logger.info("=== ENTERING SETTINGS SCREEN ===")
        self.scan_available_themes()
        self.load_settings()
        self.check_dark_mode_availability()
        self.update_dark_mode_button()
        
        # Load sensor and volume status
        self.update_sensor_status()
        self.update_volume_status()
        
        # Schedule periodic updates for sensor readings (чаще обновляем)
        self._sensor_update_event = Clock.schedule_interval(self.update_sensor_status, 2)  # Every 2 seconds
    
    def on_leave(self):
        logger.info("Leaving settings screen")
        # Stop periodic updates
        if hasattr(self, '_sensor_update_event'):
            self._sensor_update_event.cancel()
    
    def scan_available_themes(self):
        """Scan themes/ directory for available themes"""
        themes_dir = "themes"
        themes = []
        
        try:
            if os.path.exists(themes_dir) and os.path.isdir(themes_dir):
                # Get all folders in themes/ directory
                theme_folders = [f for f in os.listdir(themes_dir) 
                               if os.path.isdir(os.path.join(themes_dir, f))]
                
                # Check each folder for valid theme structure
                for theme in theme_folders:
                    theme_path = os.path.join(themes_dir, theme)
                    # Check for light or dark folders
                    if os.path.exists(os.path.join(theme_path, "light")) or \
                       os.path.exists(os.path.join(theme_path, "dark")):
                        themes.append(theme)
                
                logger.info(f"Found themes: {themes}")
            else:
                logger.warning(f"Themes directory '{themes_dir}' not found")
        except Exception as e:
            logger.error(f"Error scanning themes: {e}")
        
        # Update available themes list
        self.available_themes = themes if themes else ["minecraft"]  # Default to minecraft
    
    def check_dark_mode_availability(self):
        """Check if dark mode is available for current theme"""
        theme_path = os.path.join("themes", self.current_theme)
        dark_path = os.path.join(theme_path, "dark")
        dark_theme_file = os.path.join(dark_path, "theme.json")
        
        self.dark_mode_available = os.path.exists(dark_theme_file)
        logger.info(f"Dark mode for theme '{self.current_theme}': {'available' if self.dark_mode_available else 'unavailable'}")
        logger.info(f"Checked path: {dark_theme_file}")
        
        # If dark mode is not available, force disable it
        if not self.dark_mode_available:
            self.dark_mode_enabled = False
            logger.info("Dark mode disabled because theme not available")
    
    def update_dark_mode_button(self):
        """Update the dark mode button UI"""
        if hasattr(self.ids, "dark_mode_button"):
            self.ids.dark_mode_button.text = "ON" if self.dark_mode_enabled else "OFF"
            self.ids.dark_mode_button.disabled = not self.dark_mode_available
            # Update color based on state
            app = self.get_app()
            if app:
                if self.dark_mode_enabled and self.dark_mode_available:
                    self.ids.dark_mode_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
                else:
                    self.ids.dark_mode_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
    
    def load_settings(self):
        """Load settings from configuration file"""
        try:
            with open("config/user.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                
                # Set values from file
                self.current_theme = settings.get("theme", "minecraft")
                self.dark_mode_enabled = settings.get("theme_mode", "light") == "dark"
                self.username = settings.get("username", "")
                
                # Auto theme settings - ИСПРАВЛЕНО
                self.auto_theme_enabled = settings.get("auto_theme_enabled", True)
                self.light_sensor_threshold = settings.get("theme_switch_delay", 5)
                
                logger.info(f"Loaded settings: theme={self.current_theme}, mode={'dark' if self.dark_mode_enabled else 'light'}")
                logger.info(f"Auto theme enabled: {self.auto_theme_enabled}, delay: {self.light_sensor_threshold}s")
                
                # Parse birth date
                birthdate = settings.get("birthdate", "")
                if birthdate:
                    try:
                        date = datetime.strptime(birthdate, "%Y-%m-%d")
                        self.birth_year = str(date.year)
                        self.birth_month = str(date.month)
                        self.birth_day = str(date.day)
                    except:
                        self.birth_year = ""
                        self.birth_month = ""
                        self.birth_day = ""
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def update_sensor_status(self, dt=None):
        """Update sensor status and readings - ИСПРАВЛЕНО"""
        try:
            app = self.get_app()
            if app and hasattr(app, 'sensor_service') and app.sensor_service:
                # Get detailed sensor status
                light_status = app.sensor_service.get_light_sensor_status()
                
                # Update properties
                self.light_sensor_available = light_status.get('gpio_available', False) or not light_status.get('using_mock', True)
                self.current_light_level = light_status.get('current_level', True)
                
                # Update UI elements if they exist
                if hasattr(self.ids, 'light_sensor_status'):
                    if self.light_sensor_available:
                        status_text = "Light" if self.current_light_level else "Dark"
                        sensor_type = "Real" if not light_status.get('using_mock', True) else "Mock"
                        self.ids.light_sensor_status.text = f"Sensor: {status_text} ({sensor_type})"
                        
                        # Color based on sensor type
                        if light_status.get('using_mock', True):
                            self.ids.light_sensor_status.color = [0.8, 0.8, 0, 1]  # Yellow for mock
                        else:
                            self.ids.light_sensor_status.color = [0, 0.8, 0, 1]  # Green for real
                            
                        # Debug info - показываем каждые 10 обновлений
                        if not hasattr(self, '_debug_counter'):
                            self._debug_counter = 0
                        self._debug_counter += 1
                        
                        if self._debug_counter % 20 == 0:  # Every 20 updates (40 seconds)
                            raw_val = light_status.get('raw_value', 0)
                            change_pending = light_status.get('change_pending', False)
                            consecutive = light_status.get('consecutive_readings', 0)
                            logger.debug(f"Sensor UI update: raw={raw_val}, level={status_text}, pending={change_pending}, consecutive={consecutive}")
                    else:
                        self.ids.light_sensor_status.text = "Sensor: Offline"
                        self.ids.light_sensor_status.color = [0.8, 0, 0, 1]  # Red
                        
                # Update auto theme button state
                if hasattr(self.ids, 'auto_theme_button'):
                    # Disable only if sensor is completely unavailable (not even mock)
                    sensor_completely_unavailable = not app.sensor_service.sensor_available
                    self.ids.auto_theme_button.disabled = sensor_completely_unavailable
                    
                    if self.auto_theme_enabled and not sensor_completely_unavailable:
                        self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
                    else:
                        self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
            else:
                # Sensor service not available
                self.light_sensor_available = False
                if hasattr(self.ids, 'light_sensor_status'):
                    self.ids.light_sensor_status.text = "Sensor: Not Available"
                    self.ids.light_sensor_status.color = [0.8, 0, 0, 1]  # Red
                    
        except Exception as e:
            logger.error(f"Error updating sensor status: {e}")
    
    def update_volume_status(self):
        """Update volume control status"""
        try:
            app = self.get_app()
            if app and hasattr(app, 'volume_service') and app.volume_service:
                volume_status = app.volume_service.get_status()
                self.volume_buttons_available = volume_status.get('gpio_available', False)
                self.current_volume = volume_status.get('current_volume', 50)
                
                # Update UI elements if they exist
                if hasattr(self.ids, 'volume_status'):
                    if self.volume_buttons_available:
                        self.ids.volume_status.text = f"Volume: {self.current_volume}%"
                        self.ids.volume_status.color = [0, 0.8, 0, 1]  # Green
                    else:
                        self.ids.volume_status.text = "Volume Buttons: Offline"
                        self.ids.volume_status.color = [0.8, 0.8, 0, 1]  # Yellow
            else:
                # Volume service not available
                self.volume_buttons_available = False
                if hasattr(self.ids, 'volume_status'):
                    self.ids.volume_status.text = "Volume: Not Available"
                    self.ids.volume_status.color = [0.8, 0, 0, 1]  # Red
                    
        except Exception as e:
            logger.error(f"Error updating volume status: {e}")
    
    def save_all_settings(self):
        """Save all settings to file"""
        try:
            # Play UI sound
            app = self.get_app()
            if app:
                app.play_sound("success")
            
            # Get values from input fields (they may have changed)
            if hasattr(self.ids, 'username_input'):
                self.username = self.ids.username_input.text
                
            # Update birth date from fields
            self.update_birthdate()
            
            # Form settings object
            settings = {
                "theme": self.current_theme,
                "theme_mode": "dark" if self.dark_mode_enabled else "light",
                "auto_dark_mode": True,  # Automatic dark theme switching
                "username": self.username,
                "birthdate": self.get_birthdate_string(),
                # Auto theme settings - ИСПРАВЛЕНО
                "auto_theme_enabled": self.auto_theme_enabled,
                "theme_switch_delay": int(self.light_sensor_threshold),
                # Volume settings
                "volume_settings": {
                    "enabled": True,
                    "step": 5,
                    "min_volume": 0,
                    "max_volume": 100,
                    "feedback_sounds": True
                },
                # Sensor settings
                "sensor_settings": {
                    "light_sensor_enabled": True,
                    "calibration_time": int(self.light_sensor_threshold),
                    "mock_mode": False
                }
            }
            
            logger.info(f"Saving settings: {settings}")
            
            # Create config directory if it doesn't exist
            if not os.path.exists("config"):
                os.makedirs("config")
                logger.info("Created config directory")
                
            # Save settings
            with open("config/user.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            # Update app settings
            app = self.get_app()
            if app:
                old_theme_mode = app.theme_mode
                old_auto_theme = app.auto_theme_enabled
                
                app.theme_name = self.current_theme
                app.theme_mode = "dark" if self.dark_mode_enabled else "light"
                
                logger.info(f"App theme mode: {old_theme_mode} → {app.theme_mode}")
                
                # Update auto theme setting
                app.set_auto_theme_enabled(self.auto_theme_enabled)
                logger.info(f"Auto theme enabled: {old_auto_theme} → {self.auto_theme_enabled}")
                
                # Update sensor threshold
                if hasattr(app, 'sensor_service') and app.sensor_service:
                    app.sensor_service.calibrate_light_sensor(int(self.light_sensor_threshold))
                    logger.info(f"Updated sensor threshold to {self.light_sensor_threshold}s")
                
                # Switch theme if mode changed
                if old_theme_mode != app.theme_mode:
                    logger.info(f"Theme mode changed, switching: {old_theme_mode} → {app.theme_mode}")
                    if app.switch_theme_mode(app.theme_mode):
                        logger.info("✅ Theme switched successfully")
                    else:
                        logger.error("❌ Theme switch failed")
                else:
                    # Just reload theme config
                    try:
                        from main import load_theme_config
                        app.theme_config = load_theme_config(app.theme_name, app.theme_mode)
                        logger.info("Theme config reloaded")
                    except Exception as e:
                        logger.error(f"Error reloading theme config: {e}")
                
                logger.info(f"✅ App settings updated successfully")
            else:
                logger.error("Could not get app instance")
                
            logger.info("✅ Settings saved successfully!")
        except Exception as e:
            import traceback
            logger.error(f"❌ Error saving settings: {e}")
            logger.error(traceback.format_exc())
    
    def change_theme(self, theme):
        """Change current theme"""
        if theme != self.current_theme:
            logger.info(f"Changing theme: {self.current_theme} → {theme}")
            self.current_theme = theme
            self.check_dark_mode_availability()
            self.update_dark_mode_button()
            
            # If selected theme doesn't have dark mode, disable the option
            if not self.dark_mode_available:
                self.dark_mode_enabled = False
                logger.info("Dark mode disabled due to theme change")
    
    def toggle_dark_mode(self, enabled):
        """Enable/disable dark mode"""
        app = self.get_app()
        
        logger.info(f"Toggle dark mode: {self.dark_mode_enabled} → {enabled}")
        logger.info(f"Dark mode available: {self.dark_mode_available}")
        
        if self.dark_mode_available:
            self.dark_mode_enabled = enabled
            if enabled:
                app.play_sound("success")
            self.update_dark_mode_button()
            logger.info(f"Dark mode toggled to: {enabled}")
        else:
            self.dark_mode_enabled = False
            logger.warning("Cannot enable dark mode - theme not available")
            if app:
                app.play_sound("error")
    
    def toggle_auto_theme(self, enabled):
        """Enable/disable auto theme switching - УЛУЧШЕНО"""
        app = self.get_app()
        
        logger.info(f"=== TOGGLE AUTO THEME ===")
        logger.info(f"Current state: {self.auto_theme_enabled}")
        logger.info(f"New state: {enabled}")
        logger.info(f"Light sensor available: {self.light_sensor_available}")
        logger.info(f"Dark mode available: {self.dark_mode_available}")
        
        # Check prerequisites
        can_enable = True
        reasons = []
        
        if enabled:
            if not self.dark_mode_available:
                can_enable = False
                reasons.append("Dark theme not available")
            
            # Allow both real and mock sensors for testing
            app_has_sensors = app and hasattr(app, 'sensor_service') and app.sensor_service and app.sensor_service.sensor_available
            if not app_has_sensors:
                can_enable = False
                reasons.append("Sensor service not available")
        
        if enabled and not can_enable:
            logger.warning(f"Cannot enable auto theme: {', '.join(reasons)}")
            if app:
                app.play_sound("error")
            # Keep disabled
            self.auto_theme_enabled = False
        else:
            # Update state
            self.auto_theme_enabled = enabled
            
            if app:
                if enabled:
                    app.play_sound("success")
                    logger.info("🟢 Auto theme enabled")
                else:
                    logger.info("🔴 Auto theme disabled")
            
        # Update auto theme button UI
        if hasattr(self.ids, 'auto_theme_button'):
            self.ids.auto_theme_button.text = "ON" if self.auto_theme_enabled else "OFF"
            if app:
                if self.auto_theme_enabled:
                    self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
                else:
                    self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
        
        logger.info(f"Final auto theme state: {self.auto_theme_enabled}")
    
    def test_light_sensor(self):
        """Test light sensor reading - УЛУЧШЕНО"""
        app = self.get_app()
        if app and hasattr(app, 'sensor_service') and app.sensor_service:
            logger.info("=== LIGHT SENSOR TEST ===")
            sensor_status = app.sensor_service.get_light_sensor_status()
            
            # Log current status
            logger.info("Current sensor status:")
            for key, value in sensor_status.items():
                logger.info(f"  {key}: {value}")
            
            app.play_sound("click")
            
            # Start test in background
            import threading
            test_thread = threading.Thread(
                target=app.sensor_service.test_light_sensor, 
                args=(15,),  # 15 seconds test
                daemon=True
            )
            test_thread.start()
            
            # Show current status immediately
            light_level = "Light" if sensor_status.get('current_level', True) else "Dark"
            raw_value = sensor_status.get('raw_value', 0)
            using_mock = sensor_status.get('using_mock', True)
            sensor_type = "Mock" if using_mock else "Real"
            
            logger.info(f"Current light sensor reading: {light_level} (raw: {raw_value}, type: {sensor_type})")
            
            # Force immediate UI update
            self.update_sensor_status()
        else:
            logger.error("Cannot test light sensor - service not available")
            if app:
                app.play_sound("error")
    
    def set_threshold_delay(self, value):
        """Set theme switch delay threshold"""
        old_value = self.light_sensor_threshold
        self.light_sensor_threshold = max(1, min(int(value), 10))  # Clamp between 1-10 seconds
        
        logger.info(f"Theme switch delay: {old_value}s → {self.light_sensor_threshold}s")
        
        app = self.get_app()
        if app and hasattr(app, 'sensor_service') and app.sensor_service:
            app.sensor_service.calibrate_light_sensor(self.light_sensor_threshold)
    
    def test_volume_up(self):
        """Test volume up"""
        app = self.get_app()
        if app and hasattr(app, 'volume_service') and app.volume_service:
            current = app.volume_service.get_volume()
            new_volume = min(current + 10, 100)
            if app.volume_service.set_volume(new_volume):
                self.current_volume = new_volume
                self.update_volume_status()
                app.play_sound("success")
                logger.info(f"Volume increased to {new_volume}%")
            else:
                app.play_sound("error")
        else:
            if app:
                app.play_sound("error")
    
    def test_volume_down(self):
        """Test volume down"""
        app = self.get_app()
        if app and hasattr(app, 'volume_service') and app.volume_service:
            current = app.volume_service.get_volume()
            new_volume = max(current - 10, 0)
            if app.volume_service.set_volume(new_volume):
                self.current_volume = new_volume
                self.update_volume_status()
                app.play_sound("click")
                logger.info(f"Volume decreased to {new_volume}%")
            else:
                app.play_sound("error")
        else:
            if app:
                app.play_sound("error")
    
    def update_birthdate(self):
        """Update combined birth date from individual fields"""
        try:
            # Get values from input fields if available
            if hasattr(self.ids, 'birth_day') and hasattr(self.ids, 'birth_month') and hasattr(self.ids, 'birth_year'):
                day_text = self.ids.birth_day.text.strip()
                month_text = self.ids.birth_month.text.strip()
                year_text = self.ids.birth_year.text.strip()
                
                # Only update if all fields are filled
                if day_text and month_text and year_text:
                    day = int(day_text)
                    month = int(month_text)
                    year = int(year_text)
                    
                    # Basic validation
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                        self.birth_day = str(day)
                        self.birth_month = str(month)
                        self.birth_year = str(year)
                        logger.debug(f"Birth date updated: {day}/{month}/{year}")
                    else:
                        logger.warning(f"Invalid date: {day}/{month}/{year}")
                else:
                    logger.debug("Not all date fields filled")
        except Exception as e:
            logger.error(f"Error updating birth date: {e}")
    
    def get_birthdate_string(self):
        """Get birth date string in YYYY-MM-DD format"""
        try:
            day = int(self.birth_day) if self.birth_day else 1
            month = int(self.birth_month) if self.birth_month else 1
            year = int(self.birth_year) if self.birth_year else 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return "2000-01-01"  # Default value
    
    def get_app(self):
        """Get app instance"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            return app
        except Exception as e:
            logger.error(f"Error getting app: {e}")
            return None