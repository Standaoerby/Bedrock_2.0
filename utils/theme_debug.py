"""
Утилиты для отладки переключения тем в приложении Bedrock
"""
import logging
import os
from kivy.cache import Cache
from kivy.clock import Clock

logger = logging.getLogger("ThemeDebug")

class ThemeDebugger:
    """Класс для отладки проблем с переключением тем"""
    
    def __init__(self, app):
        self.app = app
        
    def debug_theme_state(self, detailed=False):
        """Отладочная информация о состоянии темы"""
        try:
            logger.info("=== THEME DEBUG INFO ===")
            logger.info(f"Current theme: {self.app.theme_name}")
            logger.info(f"Current mode: {self.app.theme_mode}")
            logger.info(f"Auto theme enabled: {self.app.auto_theme_enabled}")
            
            # Theme config info
            theme_config = self.app.theme_config
            logger.info(f"Theme config keys: {list(theme_config.keys())}")
            
            if detailed:
                logger.info(f"Background image: {theme_config.get('background_image', 'None')}")
                logger.info(f"Font color: {theme_config.get('font_color', 'None')}")
                logger.info(f"Panel background: {theme_config.get('panel_bg', 'None')}")
                
                # Check if files exist
                bg_image = theme_config.get('background_image', '')
                if bg_image:
                    exists = os.path.exists(bg_image)
                    logger.info(f"Background image exists: {exists} ({bg_image})")
            
            # Widget state info
            if hasattr(self.app, 'root') and self.app.root:
                self._debug_widget_state()
            
            # Sensor info
            if hasattr(self.app, 'sensor_service') and self.app.sensor_service:
                light_level = self.app.sensor_service.get_light_level()
                light_status = self.app.sensor_service.get_light_sensor_status()
                logger.info(f"Light sensor: Level={'Light' if light_level else 'Dark'}, Mock={light_status.get('using_mock', True)}")
            
            logger.info("=== END THEME DEBUG ===")
            
        except Exception as e:
            logger.error(f"Error in theme debug: {e}")
    
    def _debug_widget_state(self):
        """Отладка состояния виджетов"""
        try:
            screen_manager = getattr(self.app.root.ids, 'screen_manager', None)
            if not screen_manager:
                logger.warning("Screen manager not found")
                return
                
            current_screen = screen_manager.get_screen(screen_manager.current)
            logger.info(f"Current screen: {current_screen.name}")
            
            # Check first few widgets for theme properties
            widget_count = 0
            for widget in current_screen.walk():
                if widget_count >= 5:  # Limit to first 5 widgets
                    break
                    
                widget_info = []
                if hasattr(widget, 'color'):
                    widget_info.append(f"color={widget.color}")
                if hasattr(widget, 'source'):
                    widget_info.append(f"source={widget.source}")
                if hasattr(widget, 'background_normal'):
                    widget_info.append(f"bg_normal={widget.background_normal}")
                
                if widget_info:
                    logger.info(f"Widget {widget.__class__.__name__}: {', '.join(widget_info)}")
                    widget_count += 1
                    
        except Exception as e:
            logger.error(f"Error debugging widget state: {e}")
    
    def debug_cache_state(self):
        """Отладка состояния кэша"""
        try:
            logger.info("=== CACHE DEBUG INFO ===")
            
            cache_categories = ['kv.image', 'kv.texture', 'kv.atlas', 'kv.loader']
            for category in cache_categories:
                try:
                    # Get cache statistics if available
                    cache_info = Cache._categories.get(category, {})
                    logger.info(f"Cache {category}: Available={category in Cache._categories}")
                except Exception as e:
                    logger.warning(f"Could not get cache info for {category}: {e}")
            
            logger.info("=== END CACHE DEBUG ===")
            
        except Exception as e:
            logger.error(f"Error debugging cache: {e}")
    
    def test_theme_files(self):
        """Проверка существования файлов темы"""
        try:
            logger.info("=== THEME FILES TEST ===")
            
            for mode in ['light', 'dark']:
                theme_dir = f"themes/{self.app.theme_name}/{mode}"
                theme_file = os.path.join(theme_dir, "theme.json")
                
                logger.info(f"Theme {mode}:")
                logger.info(f"  Directory exists: {os.path.exists(theme_dir)}")
                logger.info(f"  Config file exists: {os.path.exists(theme_file)}")
                
                if os.path.exists(theme_file):
                    try:
                        import json
                        with open(theme_file, 'r') as f:
                            config = json.load(f)
                        
                        # Check key files
                        key_files = ['background_image', 'menu_button_normal', 'button_normal']
                        for key in key_files:
                            file_path = config.get(key, '')
                            if file_path:
                                exists = os.path.exists(file_path)
                                logger.info(f"  {key}: {exists} ({file_path})")
                    except Exception as e:
                        logger.error(f"  Error reading config: {e}")
            
            logger.info("=== END THEME FILES TEST ===")
            
        except Exception as e:
            logger.error(f"Error testing theme files: {e}")
    
    def force_theme_refresh(self):
        """Принудительное обновление темы для тестирования"""
        try:
            logger.info("Forcing theme refresh...")
            
            # Clear cache
            cache_categories = ['kv.image', 'kv.texture', 'kv.atlas']
            for category in cache_categories:
                try:
                    Cache.remove(category)
                except:
                    pass
            
            # Trigger property update
            self.app.property('theme_config').dispatch(self.app)
            
            # Force widget updates
            def update_widgets(dt):
                try:
                    if hasattr(self.app, 'root') and self.app.root:
                        screen_manager = getattr(self.app.root.ids, 'screen_manager', None)
                        if screen_manager:
                            for screen in screen_manager.screens:
                                for widget in screen.walk():
                                    if hasattr(widget, 'canvas'):
                                        widget.canvas.ask_update()
                    logger.info("Theme refresh completed")
                except Exception as e:
                    logger.error(f"Error in widget update: {e}")
            
            Clock.schedule_once(update_widgets, 0.1)
            
        except Exception as e:
            logger.error(f"Error forcing theme refresh: {e}")
    
    def log_theme_switch_attempt(self, from_mode, to_mode):
        """Логирование попытки переключения темы"""
        logger.info(f"THEME SWITCH: {from_mode} → {to_mode}")
        
        # Check prerequisites
        dark_theme_path = f"themes/{self.app.theme_name}/dark/theme.json"
        dark_available = os.path.exists(dark_theme_path)
        
        logger.info(f"Dark theme available: {dark_available}")
        
        if to_mode == "dark" and not dark_available:
            logger.warning("Cannot switch to dark mode - theme file missing")
            return False
        
        return True
    
    def create_theme_test_widget(self):
        """Создание тестового виджета для проверки темы"""
        try:
            from kivy.uix.label import Label
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            
            layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            
            # Test label with theme colors
            test_label = Label(
                text=f"Theme Test\nMode: {self.app.theme_mode}\nFont: {self.app.theme_config.get('font_name', 'Default')}",
                font_name=self.app.theme_config.get('font_name', 'Roboto'),
                color=self.app.theme_config.get('font_color', [1, 1, 1, 1]),
                font_size='20sp'
            )
            
            layout.add_widget(test_label)
            
            # Create popup
            popup = Popup(
                title='Theme Test Widget',
                content=layout,
                size_hint=(0.6, 0.4),
                auto_dismiss=True
            )
            
            # Auto close after 3 seconds
            Clock.schedule_once(lambda dt: popup.dismiss(), 3)
            
            popup.open()
            logger.info("Theme test widget created")
            
        except Exception as e:
            logger.error(f"Error creating theme test widget: {e}")

# Convenience function for quick debugging
def debug_theme(app, detailed=False):
    """Быстрая отладка темы"""
    debugger = ThemeDebugger(app)
    debugger.debug_theme_state(detailed)
    
def test_theme_files(app):
    """Быстрая проверка файлов темы"""
    debugger = ThemeDebugger(app)
    debugger.test_theme_files()