"""
Исправленный менеджер тем для Bedrock с принудительным обновлением UI
"""
import os
import json
import logging
from kivy.cache import Cache
from kivy.clock import Clock, mainthread
from utils.common import safe_json_load, safe_json_save, Constants

logger = logging.getLogger("ThemeManager")

class ThemeManager:
    """Исправленное управление темами приложения"""
    
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
        """Создать тёмную тему по умолчанию с ПРАВИЛЬНЫМИ цветами тени"""
        try:
            dark_theme_dir = f"{Constants.THEMES_DIR}/minecraft/dark"
            os.makedirs(dark_theme_dir, exist_ok=True)
            
            # ИСПРАВЛЕНО: Корректные цвета для тёмной темы, особенно тень
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
                    "active": [0.3, 0.8, 0.3, 1],
                    "inactive": [0.5, 0.5, 0.5, 1],
                    "semi_active": [0.6, 0.8, 0.6, 1],
                    "warning": [0.9, 0.7, 0.1, 1],
                    "error": [0.9, 0.2, 0.2, 1],
                    "success": [0.2, 0.8, 0.2, 1],
                    
                    # ИСПРАВЛЕНО: Светлые цвета шрифта для тёмной темы
                    "font_default": [0.9, 0.9, 0.95, 1],
                    "font_highlight": [0.95, 0.95, 1, 1],
                    "font_secondary": [0.8, 0.85, 0.9, 1],
                    "font_action": [0.5, 0.9, 0.5, 1],
                    
                    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Правильный цвет тени для тёмной темы
                    "shadow": [0.9, 0.9, 0.9, 0.3],  # Светлая тень для тёмного фона
                    "trend_up": [1, 0.5, 0.5, 1],
                    "trend_down": [0.4, 0.7, 1, 1]
                },
                "menu_selected_color": [0.95, 0.95, 1, 1],
                "menu_unselected_color": [0.6, 0.6, 0.7, 1],
                "grid_unit": "32dp",
                "padding": "15dp"
            }
            
            theme_file = os.path.join(dark_theme_dir, "theme.json")
            result = safe_json_save(theme_file, dark_config)
            
            if result:
                logger.info("✅ Dark theme created successfully with correct shadow colors")
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
        """ИСПРАВЛЕННОЕ переключение режима темы с принудительным обновлением UI"""
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
            
            # КРИТИЧЕСКАЯ ОТЛАДКА: Проверяем цвета
            old_font_color = self.theme_config.get("font_color", [1, 1, 1, 1])
            new_font_color = new_config.get("font_color", [1, 1, 1, 1])
            old_shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.2, 0.2, 0.2, 0.4])
            new_shadow_color = new_config.get("colors", {}).get("shadow", [0.2, 0.2, 0.2, 0.4])
            
            logger.info(f"🎨 Font color change: {old_font_color} → {new_font_color}")
            logger.info(f"🎨 Shadow color change: {old_shadow_color} → {new_shadow_color}")
            
            # Атомарное обновление
            old_mode = self.current_mode
            self.current_mode = mode
            self.theme_config = new_config
            
            # Обновить app
            self.app.theme_mode = mode
            self.app.theme_config = new_config
            
            # ИСПРАВЛЕННОЕ обновление UI с принудительной перерисовкой
            self._enhanced_refresh_ui(old_mode, mode)
            
            # Разблокировка через секунду
            Clock.schedule_once(lambda dt: setattr(self, '_switching', False), 1.0)
            
            logger.info(f"✅ Theme switched to {mode}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error switching theme: {e}")
            self._switching = False
            return False
    
    def _enhanced_refresh_ui(self, old_mode, new_mode):
        """НОВОЕ: Улучшенное обновление UI с принудительной перерисовкой часов"""
        try:
            logger.info(f"🔄 Enhanced UI refresh: {old_mode} → {new_mode}")
            
            # 1. Очистить кэш изображений
            for category in ['kv.image', 'kv.texture', 'kv.atlas']:
                try:
                    Cache.remove(category)
                except:
                    pass
            
            # 2. КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Многоэтапное обновление theme_config
            logger.info("🔄 Multi-stage theme_config dispatch...")
            
            # Первый dispatch
            self.app.property('theme_config').dispatch(self.app)
            
            # Короткая задержка и второй dispatch для надёжности
            Clock.schedule_once(lambda dt: self.app.property('theme_config').dispatch(self.app), 0.1)
            
            # 3. НОВОЕ: Принудительное обновление часов и тени
            Clock.schedule_once(lambda dt: self._force_update_clock_elements(), 0.2)
            
            # 4. Обновить фон
            Clock.schedule_once(self._update_background, 0.3)
            
            # 5. Обновить overlay изображения
            Clock.schedule_once(self._update_overlays, 0.4)
            
            # 6. НОВОЕ: Обновить ThemedPanel элементы
            Clock.schedule_once(self._force_update_themed_panels, 0.5)
            
            logger.info("✅ Enhanced UI refresh scheduled")
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced UI refresh: {e}")
    
    def _force_update_clock_elements(self):
        """НОВОЕ: Принудительное обновление часов и тени"""
        try:
            logger.info("🕒 Force updating clock elements...")
            
            screen_manager = getattr(self.app.root.ids, 'screen_manager', None)
            if not screen_manager:
                logger.warning("Screen manager not found")
                return
            
            # Находим home screen
            home_screen = None
            for screen in screen_manager.screens:
                if getattr(screen, 'name', '') == 'home':
                    home_screen = screen
                    break
            
            if not home_screen:
                logger.warning("Home screen not found")
                return
            
            # Получаем цвета из новой темы
            shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.2, 0.2, 0.2, 0.4])
            font_color = self.theme_config.get("font_color", [1, 1, 1, 1])
            
            logger.info(f"🎨 Applying clock colors: font={font_color}, shadow={shadow_color}")
            
            # Обновляем тень часов
            if hasattr(home_screen.ids, 'clock_shadow_label'):
                shadow_label = home_screen.ids.clock_shadow_label
                if shadow_label:
                    old_color = shadow_label.color
                    shadow_label.color = shadow_color
                    logger.info(f"🕒 Shadow color updated: {old_color} → {shadow_color}")
            
            # Обновляем основные часы
            if hasattr(home_screen.ids, 'clock_label'):
                clock_label = home_screen.ids.clock_label
                if clock_label:
                    old_color = clock_label.color
                    clock_label.color = font_color
                    logger.info(f"🕒 Clock color updated: {old_color} → {font_color}")
            
            # НОВОЕ: Принудительно перерисовываем canvas
            try:
                if hasattr(home_screen, 'canvas'):
                    home_screen.canvas.ask_update()
                    
                # Перерисовываем canvas всех дочерних элементов
                def redraw_widget_recursive(widget):
                    if hasattr(widget, 'canvas'):
                        widget.canvas.ask_update()
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            redraw_widget_recursive(child)
                
                redraw_widget_recursive(home_screen)
                logger.info("🎨 Canvas redraw completed")
                
            except Exception as canvas_error:
                logger.warning(f"Canvas redraw error: {canvas_error}")
            
            logger.info("✅ Clock elements force update completed")
            
        except Exception as e:
            logger.error(f"❌ Error force updating clock elements: {e}")
    
    def _force_update_themed_panels(self):
        """НОВОЕ: Принудительное обновление всех ThemedPanel"""
        try:
            logger.info("🔄 Force updating ThemedPanel elements...")
            
            def update_panels_recursive(widget):
                # Проверяем это ThemedPanel
                if widget.__class__.__name__ == 'ThemedPanel':
                    try:
                        if hasattr(widget, 'update_background'):
                            widget.update_background()
                            logger.debug(f"Updated ThemedPanel: {id(widget)}")
                    except Exception as panel_error:
                        logger.warning(f"Error updating panel {id(widget)}: {panel_error}")
                
                # Рекурсивно обновляем дочерние элементы
                if hasattr(widget, 'children'):
                    for child in widget.children:
                        update_panels_recursive(child)
            
            if self.app.root:
                update_panels_recursive(self.app.root)
                logger.info("✅ ThemedPanel force update completed")
                
        except Exception as e:
            logger.error(f"❌ Error force updating ThemedPanels: {e}")
    
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
        shadow_color = self.theme_config.get("colors", {}).get("shadow", [0.2, 0.2, 0.2, 0.4])
        logger.info(f"🎨 Theme initialized: {theme_name}/{theme_mode}")
        logger.info(f"🎨 Colors: font={font_color}, shadow={shadow_color}")
        
        return self.theme_config