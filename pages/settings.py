from utils.common import BasePage, config_manager
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from datetime import datetime
import os
import logging

logger = logging.getLogger("SettingsScreen")

class SettingsScreen(BasePage):
    """УПРОЩЕННЫЙ экран настроек"""
    
    # Theme properties
    current_theme = StringProperty("minecraft")
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
        """Вход на экран"""
        try:
            self.load_settings()
            self.check_dark_mode_availability()
            self.update_sensor_status()
            
            # Update sensor status periodically
            self.schedule_timer(self.update_sensor_status, 5)
            
            logger.info("Settings screen initialized")
            
        except Exception as e:
            logger.error(f"Error in on_pre_enter: {e}")
    
    def check_dark_mode_availability(self):
        """Проверить доступность тёмной темы"""
        try:
            app = self.get_app()
            if not app:
                self.dark_mode_available = False
                return
                
            self.dark_mode_available = app.theme_manager.is_dark_theme_available()
            
            if not self.dark_mode_available:
                if app.theme_manager.create_default_dark_theme():
                    self.dark_mode_available = True
                    logger.info("✅ Dark theme created successfully")
                else:
                    self.dark_mode_enabled = False
                    logger.warning("❌ Dark theme not available")
            
            logger.info(f"Dark mode available: {self.dark_mode_available}")
            
        except Exception as e:
            logger.error(f"Error checking dark mode availability: {e}")
            self.dark_mode_available = False
    
    def load_settings(self):
        """Загрузить настройки"""
        try:
            settings = config_manager.get_config('user')
            
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
    
    def update_sensor_status(self, dt=None):
        """Обновить статус датчиков"""
        try:
            app = self.get_app()
            if not app:
                return
                
            if hasattr(app, 'sensor_service') and app.sensor_service:
                light_status = app.sensor_service.get_light_sensor_status()
                self.light_sensor_available = True
                
                # Update UI if available
                status_widget = self.safe_get_widget('light_sensor_status')
                if status_widget:
                    current_level = light_status.get('current_level', True)
                    using_mock = light_status.get('using_mock', True)
                    
                    status_text = "Light" if current_level else "Dark"
                    sensor_type = "Mock" if using_mock else "Real"
                    
                    status_widget.text = f"Sensor: {status_text} ({sensor_type})"
                    
                    # Set color based on sensor type
                    if using_mock:
                        status_widget.color = [0.8, 0.8, 0, 1]  # Yellow
                    else:
                        status_widget.color = [0, 0.8, 0, 1]  # Green
            else:
                self.light_sensor_available = False
                status_widget = self.safe_get_widget('light_sensor_status')
                if status_widget:
                    status_widget.text = "Sensor: Offline"
                    status_widget.color = [0.8, 0, 0, 1]  # Red
                    
        except Exception as e:
            logger.error(f"Error updating sensor status: {e}")
    
    def save_all_settings(self):
        """Сохранить все настройки"""
        try:
            app = self.get_app()
            if app:
                app.play_sound("success")
            
            # Get values from UI
            username_widget = self.safe_get_widget('username_input')
            if username_widget:
                self.username = username_widget.text
            
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
            
            # Save configuration
            config_manager.update_config('user', settings)
            config_manager.save_config('user')
            
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
                    logger.info(f"Manual theme change: {old_mode} → {new_mode}")
                    app.switch_theme_mode(new_mode)
                
            logger.info("✅ All settings saved successfully")
                
        except Exception as e:
            logger.error(f"❌ Error saving settings: {e}")
            app = self.get_app()
            if app:
                app.play_sound("error")
    
    def toggle_dark_mode(self, enabled):
        """Переключить dark mode"""
        app = self.get_app()
        
        # Check if dark mode is available
        if enabled and not self.dark_mode_available:
            logger.warning("Cannot enable dark mode - not available")
            if app:
                app.play_sound("error")
            self.dark_mode_enabled = False
            
            # Update UI button
            button = self.safe_get_widget('dark_mode_button')
            if button:
                button.text = "OFF"
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
        button = self.safe_get_widget('dark_mode_button')
        if button:
            button.text = "ON" if enabled else "OFF"
        
        logger.info(f"Dark mode toggled: {enabled}")
    
    def toggle_auto_theme(self, enabled):
        """Переключить автотему"""
        app = self.get_app()
        
        # Check prerequisites for auto theme
        if enabled and not self.dark_mode_available:
            logger.warning("Cannot enable auto theme - dark theme not available")
            if app:
                app.play_sound("error")
            self.auto_theme_enabled = False
            
            # Update UI button
            button = self.safe_get_widget('auto_theme_button')
            if button:
                button.text = "OFF"
            return
        
        # Update state
        self.auto_theme_enabled = enabled
        
        # Play sound
        if app and enabled:
            app.play_sound("success")
        
        # Update UI button text
        button = self.safe_get_widget('auto_theme_button')
        if button:
            button.text = "ON" if enabled else "OFF"
        
        logger.info(f"Auto theme toggled: {enabled}")
    
    def set_threshold_delay(self, value):
        """Установить задержку переключения темы"""
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
    
    def manual_theme_test(self):
        """УПРОЩЕННЫЙ тест ручного переключения темы"""
        app = self.get_app()
        if not app:
            return
            
        try:
            # Check if we can perform the test
            if not self.dark_mode_available:
                logger.warning("Cannot test theme - dark mode not available")
                app.play_sound("error")
                return
            
            # УПРОЩЕННОЕ переключение темы
            current_mode = app.theme_mode
            new_mode = "dark" if current_mode == "light" else "light"
            
            logger.info(f"🧪 Manual theme test: switching to {new_mode} for 3 seconds")
            
            # Switch theme
            if app.switch_theme_mode(new_mode):
                app.play_sound("success")
                
                # Show notification
                if hasattr(app, 'notification_service'):
                    app.notification_service.add(f"Theme test: {new_mode} mode", "system")
                
                # Schedule switch back after 3 seconds
                Clock.schedule_once(
                    lambda dt: self._switch_back_from_test(current_mode), 
                    3
                )
            else:
                app.play_sound("error")
                logger.error("❌ Theme test failed")
                
        except Exception as e:
            logger.error(f"❌ Error in manual theme test: {e}")
            if app:
                app.play_sound("error")
    
    def _switch_back_from_test(self, original_mode):
        """Возвращаем тему обратно после теста"""
        try:
            app = self.get_app()
            if not app:
                return
                
            logger.info(f"🔄 Switching back to {original_mode}")
            
            if app.switch_theme_mode(original_mode):
                if hasattr(app, 'notification_service'):
                    app.notification_service.add(f"Theme test completed - returned to {original_mode}", "system")
                logger.info(f"✅ Theme test completed successfully")
            else:
                logger.error(f"❌ Failed to switch back to {original_mode}")
                
        except Exception as e:
            logger.error(f"❌ Error switching back from test: {e}")
    
    def update_birthdate(self):
        """Обновить дату рождения из UI"""
        try:
            day_widget = self.safe_get_widget('birth_day')
            month_widget = self.safe_get_widget('birth_month')
            year_widget = self.safe_get_widget('birth_year')
            
            if day_widget and month_widget and year_widget:
                day_str = day_widget.text.strip()
                month_str = month_widget.text.strip()
                year_str = year_widget.text.strip()
                
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
        """Получить дату рождения как строку"""
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
            return "2000-01-01"