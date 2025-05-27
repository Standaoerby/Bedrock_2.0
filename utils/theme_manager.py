"""
Упрощенный менеджер тем для Bedrock
"""
import os
import json
import logging
from kivy.cache import Cache
from kivy.clock import Clock, mainthread
from utils.common import safe_json_load, safe_json_save, Constants

logger = logging.getLogger("ThemeManager")

class ThemeManager:
    """Упрощенное управление темами приложения"""
    
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
            
            # ИСПРАВЛЕНО: Корректные цвета для тёмной темы
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
                
                # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Светлые цвета шрифта для тёмной темы
                "font_color": [0.9, 0.9, 0.95, 1],  # Почти белый для тёмного фона
                
                "font_sizes": {
                    "tiny": "12sp", "small": "14sp", "default": "16sp",
                    "medium": "20sp", "large": "24sp", "xlarge": "32sp", "huge": "240sp"
                },
                "colors": {
                    "primary": [0.2, 0.4, 0.8, 1],
                    "secondary": [0.6, 0.3, 0.8, 1],
                    "accent": [1, 0.6, 0, 1],
                    "active": [0.3, 0.8, 0.3, 1],  # Зелёный для активных элементов
                    "inactive": [0.5, 0.5, 0.5, 1],  # Серый для неактивных
                    "semi_active": [0.6, 0.8, 0.6, 1],
                    "warning": [0.9, 0.7, 0.1, 1],
                    "error": [0.9, 0.2, 0.2, 1],
                    "success": [0.2, 0.8, 0.2, 1],
                    
                    # ИСПРАВЛЕНО: Светлые цвета шрифта для тёмной темы
                    "font_default": [0.9, 0.9, 0.95, 1],
                    "font_highlight": [0.95, 0.95, 1, 1],  # Ещё светлее для выделения
                    "font_secondary": [0.8, 0.85, 0.9, 1],
                    "font_action": [0.5, 0.9, 0.5, 1],
                    
                    "shadow": [0.9, 0.9, 0.9, 0.3],
                    "trend_up": [1, 0.5, 0.5, 1],
                    "trend_down": [0.4, 0.7, 1, 1]
                },
                "menu_selected_color": [0.95, 0.95, 1, 1],  # Яркий для выбранного меню
                "menu_unselected_color": [0.6, 0.6, 0.7, 1],  # Тусклый для невыбранного
                "grid_unit": "32dp",
                "padding": "15dp"
            }
            
            theme_file = os.path.join(dark_theme_dir, "theme.json")
            result = safe_json_save(theme_file, dark_config)
            
            if result:
                logger.info("✅ Dark theme created successfully")
            else:
                logger.error("❌ Failed to create dark theme")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating dark theme: {e}")
            return False
    
    def is_dark_theme_available(self):
        """Проверить доступность тёмной темы"""
        path = f"{Constants.THEMES_DIR}/{self.current_theme}/dark/theme.json"
        return os.path.exists(path)
    
    @mainthread
    def switch_theme_mode(self, mode):
        """УПРОЩЕННОЕ переключение режима темы"""
        if self._switching or mode not in ["light", "dark"] or mode == self.current_mode:
            logger.debug(f"Skipping theme switch: switching={self._switching}, mode={mode}, current={self.current_mode}")
            return True
        
        try:
            self._switching = True
            logger.info(f"🎨 Switching theme: {self.current_mode} → {mode}")
            
            # Проверить доступность тёмной темы
            if mode == "dark" and not self.is_dark_theme_available():
                logger.warning("Dark theme not available, creating...")
                if not self.create_default_dark_theme():
                    logger.error("Failed to create dark theme")
                    self._switching = False
                    return False
            
            # Загрузить новую конфигурацию
            new_config = self.load_theme_config(self.current_theme, mode)
            if not new_config:
                logger.error("Failed to load theme config")
                self._switching = False
                return False
            
            # КРИТИЧЕСКАЯ ОТЛАДКА: Проверяем цвета шрифта
            old_font_color = self.theme_config.get("font_color", [1, 1, 1, 1])
            new_font_color = new_config.get("font_color", [1, 1, 1, 1])
            
            logger.info(f"🎨 Font color change: {old_font_color} → {new_font_color}")
            
            # Атомарное обновление
            self.current_mode = mode
            self.theme_config = new_config
            
            # Обновить app
            self.app.theme_mode = mode
            self.app.theme_config = new_config
            
            # УПРОЩЕННОЕ обновление UI
            self._simple_refresh_ui()
            
            # Разблокировка через секунду
            Clock.schedule_once(lambda dt: setattr(self, '_switching', False), 1.0)
            
            logger.info(f"✅ Theme switched to {mode}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error switching theme: {e}")
            self._switching = False
            return False
    
    def _simple_refresh_ui(self):
        """УПРОЩЕННОЕ обновление UI после смены темы"""
        try:
            # 1. Очистить кэш изображений
            for category in ['kv.image', 'kv.texture', 'kv.atlas']:
                try:
                    Cache.remove(category)
                except:
                    pass
            
            # 2. КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Принудительно диспетчеризуем theme_config
            logger.info("🔄 Dispatching theme_config property change...")
            
            # Это заставит все биндинги в .kv файлах обновиться
            self.app.property('theme_config').dispatch(self.app)
            
            # 3. Обновить фон через короткую задержку
            Clock.schedule_once(self._update_background, 0.1)
            
            # 4. Обновить overlay изображения
            Clock.schedule_once(self._update_overlays, 0.2)
            
            logger.info("✅ Simple UI refresh completed")
            
        except Exception as e:
            logger.error(f"❌ Error in simple UI refresh: {e}")
    
    def _update_background(self, dt):
        """Обновить фоновое изображение"""
        try:
            if hasattr(self.app.root, 'ids'):
                bg_widget = getattr(self.app.root.ids, 'background_image', None)
                if bg_widget and hasattr(bg_widget, 'source'):
                    new_source = self.theme_config.get("background_image", "")
                    if new_source != bg_widget.source:
                        bg_widget.source = new_source
                        logger.debug(f"Background updated: {new_source}")
        except Exception as e:
            logger.error(f"Error updating background: {e}")
    
    def _update_overlays(self, dt):
        """Обновить overlay изображения"""
        try:
            screen_manager = getattr(self.app.root.ids, 'screen_manager', None)
            if not screen_manager:
                return
            
            overlay_images = self.theme_config.get("overlay_images", {})
            
            for screen in screen_manager.screens:
                screen_name = getattr(screen, 'name', '')
                if screen_name in overlay_images:
                    # Найти overlay виджет на экране
                    overlay_id = f"{screen_name}_overlay"
                    if hasattr(screen.ids, overlay_id):
                        overlay_widget = getattr(screen.ids, overlay_id)
                        if hasattr(overlay_widget, 'source'):
                            new_source = overlay_images[screen_name]
                            if new_source != overlay_widget.source:
                                overlay_widget.source = new_source
                                logger.debug(f"Overlay updated: {screen_name} -> {new_source}")
                        
        except Exception as e:
            logger.error(f"Error updating overlays: {e}")
    
    def get_overlay_image(self, page):
        """Получить overlay изображение для страницы"""
        return self.theme_config.get("overlay_images", {}).get(page, "")
    
    def init_theme(self, theme_name, theme_mode):
        """Инициализировать тему"""
        self.current_theme = theme_name
        self.current_mode = theme_mode
        self.theme_config = self.load_theme_config(theme_name, theme_mode)
        
        # ОТЛАДКА: Проверяем цвета при инициализации
        font_color = self.theme_config.get("font_color", [1, 1, 1, 1])
        logger.info(f"🎨 Theme initialized: {theme_name}/{theme_mode}, font_color={font_color}")
        
        return self.theme_config