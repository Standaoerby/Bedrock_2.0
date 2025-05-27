import os
import sys
import threading
import logging
import re
from datetime import datetime

# Configure Kivy before any imports
from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '0')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'show_cursor', '0')

# Environment variables
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Kivy imports
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle

# KivyMD imports  
from kivymd.app import MDApp

# Project imports
from utils.common import Constants, config_manager, BasePage
from utils.theme_manager import ThemeManager
from utils.error_handler import ErrorHandler

# Services
from services.alarm_service import AlarmService
from services.weather_service import WeatherService
from services.schedule_service import ScheduleService
from services.pigs_service import PigsService
from services.notifications_service import NotificationService
from services.sensor_service import SensorService
from services.sound_service import SoundService
from services.volume_service import VolumeControlService
from classes.alarm_clock import AlarmClock
from classes.marquee import MarqueeLabel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BedrockApp")

# Register font
try:
    LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
except Exception as e:
    logger.error(f"Error registering font: {e}")

# Import screens
from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.weather import WeatherScreen
from pages.schedule import ScheduleScreen
from pages.pigs import PigsScreen
from pages.settings import SettingsScreen

class ThemedPanel(BoxLayout):
    """Панель с автообновлением фона при смене темы"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = None
        self.bg_rect = None
        self.bind(pos=self.update_rect, size=self.update_rect)
        Clock.schedule_once(self.update_background, 0.1)
    
    def update_background(self, *args):
        """Обновление фона панели"""
        try:
            app = self.get_app()
            if not app or not hasattr(app, 'theme_config'):
                Clock.schedule_once(self.update_background, 0.5)
                return
            
            self.canvas.before.clear()
            
            with self.canvas.before:
                panel_bg = app.theme_config.get("panel_bg", [0, 0, 0, 0.2])
                panel_radius = app.theme_config.get("panel_radius", 16)
                
                self.bg_color = Color(*panel_bg)
                self.bg_rect = RoundedRectangle(
                    pos=self.pos,
                    size=self.size,
                    radius=[panel_radius]
                )
                
        except Exception as e:
            logger.error(f"Error updating ThemedPanel background: {e}")
    
    def update_rect(self, *args):
        """Обновление размера/позиции фона"""
        if self.bg_rect:
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
    
    def get_app(self):
        from kivy.app import App
        return App.get_running_app()

class BedrockApp(MDApp):
    """Главное приложение Bedrock"""
    
    # Properties
    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)
    ui_scale = NumericProperty(1.0)
    font_scale = NumericProperty(1.0)
    
    # UI metrics
    ui_metrics = DictProperty({
        'menu_height': Constants.MENU_HEIGHT,
        'menu_padding': 10,
        'content_padding': 15,
        'widget_spacing': 10,
        'widget_height': 48,
        'small_widget_height': 36,
    })
    
    # Theme properties
    theme_name = StringProperty(Constants.DEFAULT_THEME)
    theme_mode = StringProperty(Constants.DEFAULT_MODE)
    theme_config = DictProperty({})
    auto_theme_enabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load user configuration
        self.user_config = config_manager.get_config('user')
        
        # Initialize theme properties
        self.theme_name = self.user_config.get("theme", Constants.DEFAULT_THEME)
        self.theme_mode = self.user_config.get("theme_mode", Constants.DEFAULT_MODE)
        self.auto_theme_enabled = self.user_config.get("auto_theme_enabled", True)
        
        # Initialize theme manager
        self.theme_manager = ThemeManager(self)
        self.theme_config = self.theme_manager.init_theme(self.theme_name, self.theme_mode)
        
        # Initialize sound service
        self.sound_service = SoundService()
        
        # Auto theme state
        self._auto_theme_event = None

    def build(self):
        """Построить приложение"""
        logger.info("Building app...")
        
        try:
            self.ensure_directories()
            self._init_services()
            return Builder.load_file('main.kv')
        except Exception as e:
            logger.error(f"Error building app: {e}")
            raise

    def ensure_directories(self):
        """Убедиться что все директории существуют"""
        dirs = [
            "assets/fonts", "assets/sounds", "assets/images",
            "themes/minecraft/light", "themes/minecraft/dark",
            "media/ringtones", "cache", "config", "logs"
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)

    def _init_services(self):
        """Инициализировать все сервисы"""
        try:
            # Core services
            self.alarm_service = AlarmService()
            self.weather_service = WeatherService(lat=51.5390, lon=-0.1426)
            self.schedule_service = ScheduleService()
            self.pigs_service = PigsService()
            self.notification_service = NotificationService()
            
            # Hardware services
            self.alarm_clock = AlarmClock(self)
            self.volume_service = VolumeControlService(self)
            
            # Initialize sensors in background
            self.sensor_service = SensorService()
            threading.Thread(target=self._init_sensors_async, daemon=True).start()
            
            logger.info("Services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise

    def _init_sensors_async(self):
        """Инициализировать датчики в фоновом потоке"""
        try:
            self.sensor_service.start()
            
            # Configure sensor
            switch_delay = self.user_config.get("theme_switch_delay", 2)
            self.sensor_service.calibrate_light_sensor(switch_delay)
            
            # Start volume control
            if self.volume_service.start():
                self.volume_service.set_volume_change_callback(self._on_volume_changed)
                
        except Exception as e:
            logger.error(f"Error starting async services: {e}")

    # Utility methods
    def scale_font(self, size):
        """Масштабировать размер шрифта"""
        if isinstance(size, str):
            match = re.match(r'(\d+)(\w+)', size)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return f"{int(value * self.font_scale)}{unit}"
        try:
            return f"{int(float(size) * self.font_scale)}sp"
        except (ValueError, TypeError):
            return "14sp"

    def scale_size(self, size):
        """Масштабировать размер виджета"""
        if isinstance(size, (list, tuple)):
            return [self.scale_size(item) for item in size]
        
        if isinstance(size, str):
            match = re.match(r'(\d+)(\w+)', size)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return f"{int(value * self.ui_scale)}{unit}"
        
        try:
            return int(float(size) * self.ui_scale)
        except (TypeError, ValueError):
            return size

    def play_sound(self, sound_name="click"):
        """Воспроизвести звук"""
        self.sound_service.play_sound(sound_name)

    def get_overlay_image(self, page):
        """Получить overlay изображение для страницы"""
        return self.theme_manager.get_overlay_image(page)

    @property
    def font_name(self):
        """Получить имя шрифта из конфигурации темы"""
        return self.theme_config.get("font_name", Constants.DEFAULT_FONT)

    # Theme management
    def switch_theme_mode(self, mode):
        """Переключить режим темы"""
        return self.theme_manager.switch_theme_mode(mode)

    def set_auto_theme_enabled(self, enabled):
        """Включить/выключить автопереключение темы"""
        self.auto_theme_enabled = enabled
        self.user_config["auto_theme_enabled"] = enabled
        config_manager.update_config('user', {"auto_theme_enabled": enabled})
        config_manager.save_config('user')
        
        if enabled and not self._auto_theme_event:
            Clock.schedule_once(self._start_auto_theme, 1)
        elif not enabled and self._auto_theme_event:
            self._auto_theme_event.cancel()
            self._auto_theme_event = None
            
        logger.info(f"Auto theme switching {'enabled' if enabled else 'disabled'}")

    # App lifecycle
    def on_start(self):
        """Запуск приложения"""
        logger.info("App starting...")
        try:
            self.root.ids.screen_manager.bind(current=self._update_current_screen)
            
            self.alarm_clock.start()
            # Initialize theme based on current light level with better timing
            Clock.schedule_once(self._initialize_theme_on_startup, 5)  # Увеличено с 2 до 5 секунд
            
            # НОВОЕ: Дополнительная проверка через 10 секунд для подстраховки
            Clock.schedule_once(self._secondary_theme_check, 10)
            
            # Start auto theme monitoring
            Clock.schedule_once(self._start_auto_theme, 8)  # Увеличено с 4 до 8 секунд
                
        except Exception as e:
            logger.error(f"Error in on_start: {e}")

    def _initialize_theme_on_startup(self, dt):
        """Установить корректную тему при запуске"""
        try:
            if not self.auto_theme_enabled:
                logger.info("Auto theme disabled, keeping current theme")
                return
                
            if not self.sensor_service:
                logger.warning("Sensor service not available for theme initialization")
                return
            
            # ИСПРАВЛЕНО: Проверяем что сенсор действительно инициализирован
            if not hasattr(self.sensor_service, 'sensor_available') or not self.sensor_service.sensor_available:
                logger.warning("Sensor not yet available, scheduling retry")
                Clock.schedule_once(self._initialize_theme_on_startup, 3)
                return
            
            # Даем сенсору время стабилизироваться
            logger.info("Waiting for sensor stabilization...")
            Clock.schedule_once(self._apply_startup_theme, 2)
            
        except Exception as e:
            logger.error(f"Error initializing startup theme: {e}")

    def _apply_startup_theme(self, dt):
        """Применить тему при запуске после стабилизации сенсора"""
        try:
            current_light = self.sensor_service.get_light_level()
            target_mode = "light" if current_light else "dark"
            
            logger.info(f"Startup sensor reading: {'Light' if current_light else 'Dark'}")
            logger.info(f"Current theme mode: {self.theme_mode}")
            logger.info(f"Target theme mode: {target_mode}")
            
            if target_mode != self.theme_mode:
                logger.info(f"🎨 Setting startup theme: {self.theme_mode} → {target_mode}")
                if self.switch_theme_mode(target_mode):
                    self.notification_service.add(f"Theme set to {target_mode} mode", "system")
                    logger.success(f"Startup theme changed to {target_mode}")
                else:
                    logger.error(f"Failed to change startup theme to {target_mode}")
            else:
                logger.info(f"Theme already correct: {target_mode}")
                
        except Exception as e:
            logger.error(f"Error applying startup theme: {e}")

    def _secondary_theme_check(self, dt):
        """Вторичная проверка темы через 10 секунд после запуска"""
        try:
            if not self.auto_theme_enabled or not self.sensor_service:
                return
                
            current_light = self.sensor_service.get_light_level()
            target_mode = "light" if current_light else "dark"
            
            logger.info(f"Secondary theme check: sensor={'Light' if current_light else 'Dark'}, current_mode={self.theme_mode}")
            
            if target_mode != self.theme_mode:
                logger.info(f"🔄 Secondary theme correction: {self.theme_mode} → {target_mode}")
                if self.switch_theme_mode(target_mode):
                    self.notification_service.add(f"Theme corrected to {target_mode}", "system")
                    self.play_sound("success")
            
        except Exception as e:
            logger.error(f"Error in secondary theme check: {e}")

    def _start_auto_theme(self, dt):
        """Запустить мониторинг автотемы"""
        if self.auto_theme_enabled and self.sensor_service:
            logger.info("Starting auto theme monitoring...")
            
            switch_delay = self.user_config.get("theme_switch_delay", 2)
            self.sensor_service.calibrate_light_sensor(switch_delay)
            
            self._auto_theme_event = Clock.schedule_interval(self._check_auto_theme, 5)
    def _check_auto_theme(self, dt):
        """Проверить автопереключение темы"""
        if not self.auto_theme_enabled or not self.sensor_service:
            return
            
        try:
            if self.sensor_service.is_light_changed():
                current_light = self.sensor_service.get_light_level()
                target_mode = "light" if current_light else "dark"
                
                if target_mode != self.theme_mode:
                    logger.info(f"Auto theme switch: {self.theme_mode} → {target_mode}")
                    if self.switch_theme_mode(target_mode):
                        self.notification_service.add(f"Theme switched to {target_mode}", "system")
                        self.play_sound("success")
                    
        except Exception as e:
            logger.error(f"Error in auto theme check: {e}")

    def _update_current_screen(self, instance, value):
        """Обновить текущий экран"""
        self.current_screen = value
        if not self.menu_navigation:
            self.play_sound("success")
        self.menu_navigation = False

    def _on_volume_changed(self, volume, action):
        """Callback для изменений громкости"""
        pass  # Обрабатывается сервисом

    def on_stop(self):
        """Остановка приложения"""
        logger.info("App stopping...")
        
        # Stop auto theme monitoring
        if self._auto_theme_event:
            self._auto_theme_event.cancel()
        
        # Stop services
        services_to_stop = [
            ('sensor_service', 'stop'),
            ('volume_service', 'stop'),
            ('sound_service', 'cleanup'),
            ('alarm_clock', 'stop'),
            ('alarm_service', 'stop')
        ]
        
        for service_name, method_name in services_to_stop:
            if hasattr(self, service_name):
                try:
                    service = getattr(self, service_name)
                    if hasattr(service, method_name):
                        getattr(service, method_name)()
                        logger.info(f"{service_name} stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")

if __name__ == "__main__":
    logger.info("Starting Bedrock App")
    try:
        BedrockApp().run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()