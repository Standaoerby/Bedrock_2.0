"""
Менеджер тем для Bedrock
"""
import os
import json
import logging
from kivy.cache import Cache
from kivy.clock import Clock, mainthread
from utils.common import safe_json_load, safe_json_save, Constants

logger = logging.getLogger("ThemeManager")

class ThemeManager:
    """Управление темами приложения"""
    
    def __init__(self, app):
        self.app = app
        self._switching = False
        self.current_theme = Constants.DEFAULT_THEME
        self.current_mode = Constants.DEFAULT_MODE
        self.theme_config = {}
        
        # Создать тёмную тему если не существует
        self.ensure_dark_theme_exists()
    
    def load_theme_config(self, theme=None, mode=None):
        """Загрузить конфигурацию темы"""
        theme = theme or self.current_theme
        mode = mode or self.current_mode
        
        path = f"{Constants.THEMES_DIR}/{theme}/{mode}/theme.json"
        config = safe_json_load(path)
        
        if not config:
            logger.warning(f"Theme config not found: {path}")
            if mode == "dark":
                self.create_default_dark_theme()
                config = safe_json_load(path)
        
        return config or self._get_fallback_config()
    
    def _get_fallback_config(self):
        """Получить fallback конфигурацию темы"""
        return {
            "background_image": "",
            "font_name": Constants.DEFAULT_FONT,
            "font_color": [1, 1, 1, 1],
            "font_sizes": {
                "tiny": "12sp", "small": "14sp", "default": "18sp",
                "medium": "20sp", "large": "26sp", "xlarge": "34sp", "huge": "240sp"
            },
            "colors": {
                "active": [0, 1, 0, 1],
                "inactive": [0.6, 0.6, 0.6, 1],
                "shadow": [0.1, 0.1, 0.1, 0.5],
                "trend_up": [1, 0.3, 0.3, 1],
                "trend_down": [0.2, 0.6, 1, 1]
            },
            "overlay_images": {},
            "menu_selected_color": [1, 1, 1, 1],
            "menu_unselected_color": [0.7, 0.7, 0.7, 1],
            "panel_bg": [0, 0, 0, 0.2],
            "panel_radius": 16
        }
    
    def ensure_dark_theme_exists(self):
        """Убедиться что тёмная тема существует"""
        dark_theme_dir = f"{Constants.THEMES_DIR}/minecraft/dark"
        theme_file = os.path.join(dark_theme_dir, "theme.json")
        
        if not os.path.exists(theme_file):
            self.create_default_dark_theme()
    
    def create_default_dark_theme(self):
        """Создать тёмную тему по умолчанию"""
        try:
            dark_theme_dir = f"{Constants.THEMES_DIR}/minecraft/dark"
            os.makedirs(dark_theme_dir, exist_ok=True)
            
            dark_config = {
                "theme_name": "minecraft",
                "theme_mode": "dark",
                "background_image": "themes/minecraft/dark/background.png",
                "overlay_images": {
                    "home": "themes/minecraft/dark/overlay_home.png",
                    "alarm": "themes/minecraft/dark/overlay_alarm.png",
                    "schedule": "themes/minecraft/dark/overlay_schedule.png",
                    "weather": "themes/minecraft/dark/overlay_weather.png",
                    "pigs": "themes/minecraft/dark/overlay_pigs.png",
                    "settings": "themes/minecraft/dark/overlay_settings.png"
                },
                "menu_button_normal": "themes/minecraft/dark/menu_button.png",
                "menu_button_active": "themes/minecraft/dark/menu_button_active.png",
                "button_normal": "themes/minecraft/dark/button.png",
                "button_active": "themes/minecraft/dark/button_active.png",
                "panel_bg": [0.1, 0.1, 0.15, 0.85],
                "panel_radius": 8,
                "font_name": "Minecraftia",
                "font_color": [0.9, 0.9, 0.95, 1],
                "font_sizes": {
                    "tiny": "12sp", "small": "14sp", "default": "16sp",
                    "medium": "20sp", "large": "24sp", "xlarge": "32sp", "huge": "240sp"
                },
                "colors": {
                    "primary": [0.2, 0.4, 0.8, 1],
                    "secondary": [0.6, 0.3, 0.8, 1],
                    "accent": [1, 0.6, 0, 1],
                    "active": [0.2, 0.8, 0.2, 1],
                    "inactive": [0.4, 0.4, 0.4, 1],
                    "semi_active": [0.5, 0.7, 0.5, 1],
                    "warning": [0.9, 0.7, 0.1, 1],
                    "error": [0.9, 0.2, 0.2, 1],
                    "success": [0.2, 0.8, 0.2, 1],
                    "font_default": [0.9, 0.9, 0.95, 1],
                    "font_highlight": [0.8, 0.8, 0.9, 1],
                    "font_secondary": [0.7, 0.8, 0.9, 1],
                    "font_action": [0.4, 0.8, 0.4, 1],
                    "shadow": [0.9, 0.9, 0.9, 0.3],
                    "trend_up": [1, 0.5, 0.5, 1],
                    "trend_down": [0.4, 0.7, 1, 1]
                },
                "menu_selected_color": [0.9, 0.9, 0.95, 1],
                "menu_unselected_color": [0.6, 0.6, 0.7, 1],
                "grid_unit": "32dp",
                "padding": "15dp"
            }
            
            theme_file = os.path.join(dark_theme_dir, "theme.json")
            return safe_json_save(theme_file, dark_config)
            
        except Exception as e:
            logger.error(f"Error creating dark theme: {e}")
            return False
    
    def is_dark_theme_available(self):
        """Проверить доступность тёмной темы"""
        path = f"{Constants.THEMES_DIR}/{self.current_theme}/dark/theme.json"
        return os.path.exists(path)
    
    @mainthread
    def switch_theme_mode(self, mode):
        """Переключить режим темы"""
        if self._switching or mode not in ["light", "dark"] or mode == self.current_mode:
            return True
        
        try:
            self._switching = True
            
            # Проверить доступность тёмной темы
            if mode == "dark" and not self.is_dark_theme_available():
                if not self.create_default_dark_theme():
                    self._switching = False
                    return False
            
            logger.info(f"Switching theme: {self.current_mode} → {mode}")
            
            # Загрузить новую конфигурацию
            new_config = self.load_theme_config(self.current_theme, mode)
            if not new_config:
                self._switching = False
                return False
            
            # Атомарное обновление
            old_mode = self.current_mode
            self.current_mode = mode
            self.theme_config = new_config
            
            # Обновить app
            self.app.theme_mode = mode
            self.app.theme_config = new_config
            
            # Простое обновление UI
            self._refresh_ui()
            
            # Разблокировка
            Clock.schedule_once(lambda dt: setattr(self, '_switching', False), 0.5)
            
            logger.info(f"Theme switched to {mode}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching theme: {e}")
            self._switching = False
            return False
    
    def _refresh_ui(self):
        """Обновить UI после смены темы"""
        try:
            # Очистить кэш изображений
            for category in ['kv.image', 'kv.texture']:
                try:
                    Cache.remove(category)
                except:
                    pass
            
            # ИСПРАВЛЕНО: Принудительно обновляем все .kv биндинги для theme_config
            self.app.property('theme_config').dispatch(self.app)
            
            # Обновить фон
            self._update_background()
            
            # Обновить overlay изображения
            Clock.schedule_once(self._update_overlays, 0.1)
            
            # ДОБАВЛЕНО: Принудительное обновление всех виджетов
            Clock.schedule_once(self._force_widgets_redraw, 0.2)
            
        except Exception as e:
            logger.error(f"Error refreshing UI: {e}")
    
    def _force_widgets_redraw(self, dt):
        """НОВОЕ: Принудительно перерисовать все виджеты для обновления цветов"""
        try:
            if not self.app.root:
                return
                
            def update_widget_recursive(widget):
                """Рекурсивно обновляем все виджеты"""
                try:
                    # Обновляем canvas виджета
                    if hasattr(widget, 'canvas'):
                        widget.canvas.ask_update()
                    
                    # Для Label виджетов принудительно обновляем текстуру
                    if hasattr(widget, 'texture') and hasattr(widget, '_label'):
                        widget._label.refresh()
                    
                    # Обновляем детей
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            update_widget_recursive(child)
                            
                except Exception as e:
                    logger.debug(f"Error updating widget {widget}: {e}")
            
            # Обновляем все виджеты начиная с root
            update_widget_recursive(self.app.root)
            
            logger.info("✅ All widgets forced to redraw with new theme colors")
            
        except Exception as e:
            logger.error(f"Error in force widgets redraw: {e}")
    
    def _update_background(self):
        """Обновить фоновое изображение"""
        try:
            if hasattr(self.app.root, 'ids'):
                bg_widget = getattr(self.app.root.ids, 'background_image', None)
                if bg_widget and hasattr(bg_widget, 'source'):
                    new_source = self.theme_config.get("background_image", "")
                    bg_widget.source = new_source
        except Exception as e:
            logger.error(f"Error updating background: {e}")
    
    def _update_overlays(self, dt):
        """Обновить overlay изображения"""
        try:
            screen_manager = getattr(self.app.root.ids, 'screen_manager', None)
            if not screen_manager:
                return
            
            for screen in screen_manager.screens:
                screen_name = getattr(screen, 'name', '')
                if not screen_name:
                    continue
                
                new_overlay = self.get_overlay_image(screen_name)
                
                # Найти overlay виджет
                for widget in screen.walk():
                    if self._is_overlay_widget(widget, screen_name):
                        if hasattr(widget, 'source'):
                            widget.source = new_overlay
                        break
                        
        except Exception as e:
            logger.error(f"Error updating overlays: {e}")
    
    def _is_overlay_widget(self, widget, screen_name):
        """Проверить является ли виджет overlay изображением"""
        if not (hasattr(widget, 'source') and hasattr(widget, 'id')):
            return False
        
        widget_id = str(getattr(widget, 'id', ''))
        return widget_id.endswith('_overlay') or 'overlay' in widget_id.lower()
    
    def get_overlay_image(self, page):
        """Получить overlay изображение для страницы"""
        return self.theme_config.get("overlay_images", {}).get(page, "")
    
    def init_theme(self, theme_name, theme_mode):
        """Инициализировать тему"""
        self.current_theme = theme_name
        self.current_mode = theme_mode
        self.theme_config = self.load_theme_config(theme_name, theme_mode)
        return self.theme_config