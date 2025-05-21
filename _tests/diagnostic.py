from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.pickers.timepicker import MDTimePickerInput
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, DictProperty
from kivy.uix.label import Label
import os
import time
import json
import re
import threading
import traceback

# Настройка и включение отладки
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BedrockApp")
logger.setLevel(logging.DEBUG)

# Вывод версии Python для отладки
import sys
logger.info(f"Python version: {sys.version}")
logger.info(f"Running on platform: {sys.platform}")

# Отладочная информация о модулях
logger.info("Importing modules...")

# Создаем файл для логов критических ошибок
with open('bedrock_startup_log.txt', 'w') as log_file:
    log_file.write(f"Starting app at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"Python version: {sys.version}\n")
    log_file.write(f"Platform: {sys.platform}\n")

# Configure environment variables - these work with the launch script
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# Raspberry Pi specific settings - use SDL2 rather than EGL for better compatibility
if sys.platform.startswith('linux'):
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['KIVY_LOG_LEVEL'] = 'debug'

# Register font
print("DEBUG: Registering fonts...")
try:
    LabelBase.register(name="Minecraftia", fn_regular="assets/fonts/Minecraftia-Regular.ttf")
    print("DEBUG: Font registered successfully")
except Exception as e:
    print(f"DEBUG ERROR: Font registration failed: {e}")

print("DEBUG: Importing screen modules...")
try:
    # Import screens WITHOUT actual imports - avoid potential issues
    print("DEBUG: Will defer actual screen imports to minimize errors")
except Exception as e:
    print(f"DEBUG ERROR: Screen import preparation failed: {e}")

def load_theme_config(theme="minecraft", mode="light"):
    print(f"DEBUG: Loading theme config for {theme}/{mode}")
    path = f"themes/{theme}/{mode}/theme.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"DEBUG: Successfully loaded theme from {path}")
        return config
    except Exception as e:
        print(f"DEBUG ERROR: Theme loading failed: {e}")
        return {"background_image": "", "menu_button_normal": "", "font_name": "Minecraftia", 
                "font_color": [1, 1, 1, 1], "menu_selected_color": [1, 1, 1, 1], 
                "menu_unselected_color": [0.7, 0.7, 0.7, 1], "overlay_images": {}}
    
# Import Config BEFORE anything creates a Window 
print("DEBUG: Configuring Window settings")
from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '0')
Config.set('graphics', 'top', '0')
Config.set('graphics', 'borderless', '0')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'window_state', 'visible')
Config.set('graphics', 'resizable', '0')    
Config.set('graphics', 'show_cursor', '0')
print("DEBUG: Window configuration complete")

# KivyMD import check
try:
    from kivymd.app import MDApp
    print("DEBUG: MDApp imported successfully")
except Exception as e:
    print(f"DEBUG ERROR: MDApp import failed: {e}")

class DiagnosticApp(MDApp):
    current_screen = StringProperty("home")
    menu_navigation = BooleanProperty(False)
    
    # Fixed scaling parameters - no platform detection
    ui_scale = NumericProperty(1.0)
    font_scale = NumericProperty(1.0)
    padding_scale = NumericProperty(1.0)
    
    # Common UI metrics
    ui_metrics = DictProperty({
        'menu_height': 70,
        'menu_padding': 10,
        'content_padding': 15,
        'widget_spacing': 10,
        'widget_height': 48,
        'small_widget_height': 36,
    })

    def __init__(self, **kwargs):
        print("DEBUG: DiagnosticApp.__init__ started")
        
        # Initialize theme_config BEFORE parent init to ensure it's available for KV loading
        self.theme_name = "minecraft"
        self.theme_mode = "light"
        try:
            self.theme_config = load_theme_config(self.theme_name, self.theme_mode)
            print("DEBUG: Theme initialized in __init__")
        except Exception as e:
            print(f"DEBUG ERROR: Theme init failed in __init__: {e}")
            # Set default fallback theme
            self.theme_config = {
                "background_image": "",
                "menu_button_normal": "",
                "font_name": "Minecraftia",
                "font_color": [1, 1, 1, 1],
                "menu_selected_color": [1, 1, 1, 1],
                "menu_unselected_color": [0.7, 0.7, 0.7, 1],
                "overlay_images": {}
            }
        
        # Initialize basic properties
        self.sounds = {}
        self.last_sound_time = 0
        self.last_sound_name = ""
        
        print("DEBUG: About to call super().__init__")
        # Call parent init after our initializations
        super(DiagnosticApp, self).__init__(**kwargs)
        print("DEBUG: super().__init__ completed")

    def build(self):
        print("\nDEBUG: DiagnosticApp.build started")
        
        # Create a simple diagnostic UI instead of loading the main app
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.core.window import Window
        
        print("DEBUG: Setting window properties")
        try:
            Window.size = (1024, 600)
            Window.left = 0
            Window.top = 0
            print(f"DEBUG: Window size set to: {Window.size}, position: ({Window.left}, {Window.top})")
        except Exception as e:
            print(f"DEBUG ERROR: Window configuration failed: {e}")
        
        # Create a simple UI for diagnostics
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Add header
        header = Label(
            text="Bedrock App Diagnostic",
            font_size='30sp',
            size_hint_y=0.1
        )
        layout.add_widget(header)
        
        # Add diagnostic info
        info_layout = BoxLayout(orientation='vertical', size_hint_y=0.7)
        
        # Check theme loading
        theme_result = "SUCCESS" if hasattr(self, 'theme_config') else "FAILED"
        theme_info = Label(
            text=f"Theme Loading: {theme_result}",
            font_size='20sp',
            color=(0,1,0,1) if theme_result == "SUCCESS" else (1,0,0,1)
        )
        info_layout.add_widget(theme_info)
        
        # Check asset directories
        asset_checks = []
        for path in ["themes/minecraft/light", "assets/fonts", "assets/sounds"]:
            exists = os.path.exists(path)
            asset_checks.append((path, exists))
        
        for path, exists in asset_checks:
            status = "Found" if exists else "MISSING"
            color = (0,1,0,1) if exists else (1,0,0,1)
            asset_info = Label(
                text=f"{path}: {status}",
                font_size='16sp',
                color=color
            )
            info_layout.add_widget(asset_info)
        
        # Add buttons for step-by-step testing
        btn_layout = BoxLayout(orientation='vertical', size_hint_y=0.2, spacing=5)
        
        test_sounds_btn = Button(
            text="Step 1: Test Sound Loading",
            font_size='18sp',
            on_press=self.test_sounds
        )
        btn_layout.add_widget(test_sounds_btn)
        
        test_services_btn = Button(
            text="Step 2: Test Service Init",
            font_size='18sp',
            on_press=self.test_services
        )
        btn_layout.add_widget(test_services_btn)
        
        test_ui_btn = Button(
            text="Step 3: Test UI Loading",
            font_size='18sp',
            on_press=self.test_ui_loading
        )
        btn_layout.add_widget(test_ui_btn)
        
        run_app_btn = Button(
            text="Run Full Application",
            font_size='18sp',
            on_press=self.run_full_app
        )
        btn_layout.add_widget(run_app_btn)
        
        # Add sections to main layout
        layout.add_widget(info_layout)
        layout.add_widget(btn_layout)
        
        print("DEBUG: Diagnostic UI created")
        return layout

    def test_sounds(self, instance):
        print("\nDEBUG: Testing sound loading...")
        status_label = instance.parent.parent.children[1].children[0]
        
        try:
            from kivy.core.audio import SoundLoader
            sound_files = {
                "click": ["assets/sounds/click.ogg"],
                "success": ["assets/sounds/success.ogg"],
                "error": ["assets/sounds/error.ogg"]
            }
            
            for name, paths in sound_files.items():
                for path in paths:
                    if os.path.exists(path):
                        print(f"DEBUG: Found sound file {path}")
                        sound = SoundLoader.load(path)
                        if sound:
                            print(f"DEBUG: Successfully loaded sound: {name}")
                            sound.play()
                            time.sleep(0.2)
                            sound.stop()
                        else:
                            print(f"DEBUG ERROR: Could not load sound: {name}")
            
            status_label.text = "Sound Test: SUCCESS"
            status_label.color = (0,1,0,1)
            return True
        except Exception as e:
            print(f"DEBUG ERROR: Sound test failed: {e}")
            status_label.text = f"Sound Test: FAILED\n{str(e)}"
            status_label.color = (1,0,0,1)
            return False

    def test_services(self, instance):
        print("\nDEBUG: Testing service initialization...")
        status_label = instance.parent.parent.children[1].children[0]
        
        try:
            # Try importing services one by one
            print("DEBUG: Importing AlarmService...")
            from services.alarm_service import AlarmService
            alarm = AlarmService()
            print("DEBUG: AlarmService OK")
            
            print("DEBUG: Importing WeatherService...")
            from services.weather_service import WeatherService
            weather = WeatherService(lat=51.5390, lon=-0.1426)
            print("DEBUG: WeatherService OK")
            
            print("DEBUG: Importing ScheduleService...")
            from services.schedule_service import ScheduleService
            schedule = ScheduleService()
            print("DEBUG: ScheduleService OK")
            
            print("DEBUG: Importing PigsService...")
            from services.pigs_service import PigsService
            pigs = PigsService()
            print("DEBUG: PigsService OK")
            
            print("DEBUG: Importing NotificationService...")
            from services.notifications_service import NotificationService
            notif = NotificationService()
            print("DEBUG: NotificationService OK")
            
            print("DEBUG: Importing SensorService...")
            from services.sensor_service import SensorService
            sensor = SensorService()
            print("DEBUG: SensorService OK")
            
            status_label.text = "Services Test: SUCCESS"
            status_label.color = (0,1,0,1)
            return True
        except Exception as e:
            print(f"DEBUG ERROR: Service test failed: {e}")
            status_label.text = f"Services Test: FAILED\n{str(e)}"
            status_label.color = (1,0,0,1)
            return False

    def test_ui_loading(self, instance):
        print("\nDEBUG: Testing UI loading...")
        status_label = instance.parent.parent.children[1].children[0]
        
        try:
            # Try importing screens
            print("DEBUG: Importing screen classes...")
            from pages.home import HomeScreen
            from pages.alarm import AlarmScreen
            from pages.weather import WeatherScreen
            from pages.schedule import ScheduleScreen
            from pages.pigs import PigsScreen
            from pages.settings import SettingsScreen
            print("DEBUG: Screen imports OK")
            
            # Try loading main.kv
            print("DEBUG: Loading main.kv...")
            from kivy.lang import Builder
            ui = Builder.load_file('main.kv')
            print("DEBUG: main.kv loaded successfully!")
            
            status_label.text = "UI Loading Test: SUCCESS"
            status_label.color = (0,1,0,1)
            return True
        except Exception as e:
            print(f"DEBUG ERROR: UI loading test failed: {e}")
            status_label.text = f"UI Loading Test: FAILED\n{str(e)}"
            status_label.color = (1,0,0,1)
            traceback.print_exc()
            return False

    def run_full_app(self, instance):
        print("\nDEBUG: Attempting to run full app...")
        
        try:
            # Try importing the real app module and running it
            import main
            self.stop()
            main.BedrockApp().run()
            return True
        except Exception as e:
            print(f"DEBUG ERROR: Full app failed to start: {e}")
            traceback.print_exc()
            return False

    def scale_font(self, size):
        """Scale font size"""
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
        """Scale widget size"""
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

    def get_overlay_image(self, page):
        return self.theme_config["overlay_images"].get(page, "")

    @property
    def font_name(self):
        return self.theme_config.get("font_name", "Minecraftia")

if __name__ == "__main__":
    print("DEBUG: Starting DiagnosticApp...")
    try:
        DiagnosticApp().run()
    except Exception as e:
        print(f"DEBUG CRITICAL ERROR: DiagnosticApp failed: {e}")
        traceback.print_exc()