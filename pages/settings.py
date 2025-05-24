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
    
    # NEW: Auto theme properties
    auto_theme_enabled = BooleanProperty(True)
    light_sensor_available = BooleanProperty(False)
    current_light_level = BooleanProperty(True)  # True = light, False = dark
    light_sensor_threshold = NumericProperty(2)  # seconds
    
    # NEW: Volume properties
    current_volume = NumericProperty(50)
    volume_buttons_available = BooleanProperty(False)
    
    def on_pre_enter(self):
        self.scan_available_themes()
        self.load_settings()
        self.check_dark_mode_availability()
        self.update_dark_mode_button()
        
        # NEW: Load sensor and volume status
        self.update_sensor_status()
        self.update_volume_status()
        
        # Schedule periodic updates for sensor readings
        Clock.schedule_interval(self.update_sensor_status, 5)  # Every 5 seconds
    
    def on_leave(self):
        # Stop periodic updates
        Clock.unschedule(self.update_sensor_status)
    
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
                
                logger.debug(f"Found themes: {themes}")
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
        
        self.dark_mode_available = os.path.exists(dark_path) and os.path.isdir(dark_path)
        logger.debug(f"Dark mode for theme '{self.current_theme}': {'available' if self.dark_mode_available else 'unavailable'}")
        
        # If dark mode is not available, force disable it
        if not self.dark_mode_available:
            self.dark_mode_enabled = False
    
    def update_dark_mode_button(self):
        """Update the dark mode button UI"""
        if hasattr(self.ids, "dark_mode_button"):
            self.ids.dark_mode_button.text = "ON" if self.dark_mode_enabled else "OFF"
            self.ids.dark_mode_button.disabled = not self.dark_mode_available
            # Update color based on state
            app = self.get_app()
            if app:
                if self.dark_mode_enabled:
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
                
                # NEW: Auto theme settings
                self.auto_theme_enabled = settings.get("auto_theme_enabled", True)
                self.light_sensor_threshold = settings.get("theme_switch_delay", 5)
                
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
    
    # NEW: Update sensor status
    def update_sensor_status(self, dt=None):
        """Update sensor status and readings"""
        app = self.get_app()
        if app and hasattr(app, 'sensor_service'):
            # Update light sensor status
            light_status = app.get_light_sensor_status()
            self.light_sensor_available = light_status.get('gpio_available', False)
            self.current_light_level = light_status.get('current_level', True)
            
            # Update UI elements if they exist
            if hasattr(self.ids, 'light_sensor_status'):
                if self.light_sensor_available:
                    status_text = "Light" if self.current_light_level else "Dark"
                    self.ids.light_sensor_status.text = f"Sensor: {status_text}"
                    self.ids.light_sensor_status.color = [0, 0.8, 0, 1]  # Green
                else:
                    self.ids.light_sensor_status.text = "Sensor: Offline"
                    self.ids.light_sensor_status.color = [0.8, 0.8, 0, 1]  # Yellow
    
    # NEW: Update volume status
    def update_volume_status(self):
        """Update volume control status"""
        app = self.get_app()
        if app and hasattr(app, 'volume_service'):
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
                # NEW: Auto theme settings
                "auto_theme_enabled": self.auto_theme_enabled,
                "theme_switch_delay": int(self.light_sensor_threshold)
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
                app.theme_name = self.current_theme
                app.theme_mode = "dark" if self.dark_mode_enabled else "light"
                
                # NEW: Update auto theme setting
                app.set_auto_theme_enabled(self.auto_theme_enabled)
                
                # Import the load_theme_config function from main
                try:
                    from main import load_theme_config
                    app.theme_config = load_theme_config(app.theme_name, app.theme_mode)
                except ImportError:
                    # Fallback if import fails - recreate the theme config directly
                    logger.warning("Could not import load_theme_config, using fallback")
                    path = f"themes/{app.theme_name}/{app.theme_mode}/theme.json"
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            app.theme_config = json.load(f)
                    except Exception as e:
                        logger.error(f"Error loading theme: {e}")
                        # Fallback to default theme config
                        app.theme_config = {
                            "background_image": "",
                            "menu_button_normal": "",
                            "font_name": "Minecraftia",
                            "font_color": [1, 1, 1, 1],
                            "menu_selected_color": [1, 1, 1, 1],
                            "menu_unselected_color": [0.7, 0.7, 0.7, 1],
                            "overlay_images": {}
                        }
                
                logger.info(f"App settings updated: {app.theme_name}, {app.theme_mode}")
                
                # Reload screens to apply new theme
                app.root.ids.screen_manager.current = "settings"
            else:
                logger.error("Could not get app instance")
                
            logger.info("Settings saved successfully!")
        except Exception as e:
            import traceback
            logger.error(f"Error saving settings: {e}")
            logger.error(traceback.format_exc())
    
    def change_theme(self, theme):
        """Change current theme"""
        if theme != self.current_theme:
            self.current_theme = theme
            self.check_dark_mode_availability()
            self.update_dark_mode_button()
            
            # If selected theme doesn't have dark mode, disable the option
            if not self.dark_mode_available:
                self.dark_mode_enabled = False
    
    def toggle_dark_mode(self, enabled):
        """Enable/disable dark mode"""
        app = self.get_app()
        if self.dark_mode_available:
            self.dark_mode_enabled = enabled
            if enabled:
                app.play_sound("success")
            self.update_dark_mode_button()
        else:
            self.dark_mode_enabled = False
    
    # NEW: Auto theme methods
    def toggle_auto_theme(self, enabled):
        """Enable/disable auto theme switching"""
        self.auto_theme_enabled = enabled
        app = self.get_app()
        if app:
            if enabled and self.light_sensor_available:
                app.play_sound("success")
            elif enabled and not self.light_sensor_available:
                app.play_sound("error")
            
            # Update auto theme button UI
            if hasattr(self.ids, 'auto_theme_button'):
                self.ids.auto_theme_button.text = "ON" if enabled else "OFF"
                if enabled:
                    self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
                else:
                    self.ids.auto_theme_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
    
    def test_light_sensor(self):
        """Test light sensor reading"""
        app = self.get_app()
        if app and hasattr(app, 'sensor_service'):
            light_status = app.get_light_sensor_status()
            light_level = "Light" if light_status.get('current_level', True) else "Dark"
            raw_value = light_status.get('raw_value', 0)
            
            # Show temporary notification or update UI
            logger.info(f"Light sensor test: {light_level} (raw: {raw_value})")
            app.play_sound("click")
            
            # Update status immediately
            self.update_sensor_status()
    
    # NEW: Volume control methods
    def test_volume_up(self):
        """Test volume up"""
        app = self.get_app()
        if app and hasattr(app, 'volume_service'):
            current = app.volume_service.get_volume()
            app.volume_service.set_volume(min(current + 10, 100))
            self.update_volume_status()
            app.play_sound("success")
    
    def test_volume_down(self):
        """Test volume down"""
        app = self.get_app()
        if app and hasattr(app, 'volume_service'):
            current = app.volume_service.get_volume()
            app.volume_service.set_volume(max(current - 10, 0))
            self.update_volume_status()
            app.play_sound("click")
    
    def set_threshold_delay(self, value):
        """Set theme switch delay threshold"""
        self.light_sensor_threshold = int(value)
        app = self.get_app()
        if app and hasattr(app, 'sensor_service'):
            app.sensor_service.calibrate_light_sensor(int(value))
        logger.info(f"Theme switch delay set to {value} seconds")
    
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