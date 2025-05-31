#!/usr/bin/env python3

"""
Bedrock 2.0 - ИСПРАВЛЕННЫЙ Pi 5 Launcher для FULLSCREEN
Критические исправления для Raspberry Pi 5 + Pi OS Bookworm
"""

import os
import sys
from datetime import datetime

def setup_pi5_environment():
    """КРИТИЧЕСКАЯ НАСТРОЙКА ОКРУЖЕНИЯ ДЛЯ PI 5 FULLSCREEN"""
    print(f"🔧 Setting up Pi 5 environment for fullscreen...")
    
    # КРИТИЧЕСКИ ВАЖНО: Устанавливаем ДО импорта Kivy
    os.environ['DISPLAY'] = ':0.0'
    os.environ['XDG_SESSION_TYPE'] = 'x11'
    os.environ['XDG_RUNTIME_DIR'] = f'/run/user/{os.getuid()}'
    
    # SDL2 конфигурация для Pi 5
    os.environ['SDL_VIDEODRIVER'] = 'x11'
    os.environ['SDL_VIDEO_X11_FORCE_EGL'] = '1'
    os.environ['SDL_VIDEO_ALLOW_SCREENSAVER'] = '0'
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Убираем переменные которые мешают fullscreen
    for var in ['SDL_WINDOWID', 'KIVY_WINDOW_IMPL']:
        if var in os.environ:
            del os.environ[var]
            print(f"🗑️  Removed conflicting {var}")
    
    # Kivy конфигурация для Pi 5
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'gl'
    os.environ['USE_SDL2'] = '1'
    
    # GPU ускорение для Pi 5
    os.environ['MESA_GL_VERSION_OVERRIDE'] = '2.1'
    os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '120'
    os.environ['LIBGL_ALWAYS_SOFTWARE'] = '0'
    
    print("✅ Pi 5 environment configured for fullscreen")

def configure_kivy_fullscreen():
    """ИСПРАВЛЕННАЯ конфигурация Kivy для Pi 5 fullscreen"""
    print("🎯 Configuring Kivy for Pi 5 fullscreen...")
    
    try:
        # ВАЖНО: Импортируем Config ДО всех остальных модулей Kivy
        from kivy.config import Config
        
        # Убираем сохранение конфигурации в файл (может вызывать конфликты)
        Config.set('kivy', 'log_dir', 'logs')
        Config.set('kivy', 'log_enable', '1')
        
        # КРИТИЧЕСКИЕ настройки fullscreen для Pi 5
        Config.set("graphics", "fullscreen", "auto")
        Config.set("graphics", "width", "1024")
        Config.set("graphics", "height", "600")
        Config.set("graphics", "borderless", "1")
        Config.set("graphics", "resizable", "0")
        Config.set("graphics", "show_cursor", "1")  # Показываем курсор для отладки
        
        # ИСПРАВЛЕНО: Настройки позиционирования для fullscreen
        Config.set("graphics", "window_state", "maximized")
        Config.set("graphics", "position", "custom")
        Config.set("graphics", "left", "0")
        Config.set("graphics", "top", "0")
        Config.set("graphics", "minimum_width", "1024")
        Config.set("graphics", "minimum_height", "600")
        
        # Performance настройки для Pi 5
        Config.set("graphics", "maxfps", "60")
        Config.set("graphics", "vsync", "1")
        Config.set("graphics", "multisamples", "0")
        
        # Input настройки для touchscreen
        Config.set("input", "mouse", "mouse,multitouch_on_demand")
        
        # Desktop настройки для embedded режима
        Config.set("kivy", "desktop", "0")  # КРИТИЧНО: embedded режим
        Config.set("kivy", "exit_on_escape", "0")
        
        # НЕ сохраняем конфигурацию чтобы избежать конфликтов
        # Config.write()
        
        print("✅ Kivy configured for Pi 5 fullscreen")
        return True
        
    except Exception as e:
        print(f"❌ Error configuring Kivy: {e}")
        return False

def log_startup_info():
    """Расширенное логирование для отладки"""
    startup_time = datetime.now()
    
    print(f"🚀 Bedrock 2.0 Pi 5 Launcher - FULLSCREEN FIXED VERSION")
    print(f"📅 Startup: {startup_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version}")
    print(f"🖥️  Platform: {sys.platform}")
    print(f"👤 User: {os.getenv('USER', 'unknown')} (UID: {os.getuid()})")
    
    # Логируем критические переменные окружения
    critical_vars = [
        'DISPLAY', 'XDG_SESSION_TYPE', 'XDG_RUNTIME_DIR',
        'SDL_VIDEODRIVER', 'KIVY_WINDOW', 'KIVY_GL_BACKEND'
    ]
    
    print("🔍 Environment variables:")
    for var in critical_vars:
        value = os.getenv(var, 'NOT SET')
        print(f"  {var}: {value}")
    
    # Логируем в файл
    try:
        os.makedirs('logs', exist_ok=True)
        with open('logs/launcher.log', 'a') as f:
            f.write(f"\n[{startup_time}] Bedrock Pi 5 Launcher Started (FULLSCREEN FIXED)\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Working directory: {os.getcwd()}\n")
            for var in critical_vars:
                f.write(f"{var}: {os.getenv(var, 'NOT SET')}\n")
    except Exception as e:
        print(f"⚠️ Could not write to log: {e}")

def check_pi5_dependencies():
    """Проверка критических зависимостей для Pi 5"""
    print("🔍 Checking Pi 5 dependencies...")
    
    critical_imports = [
        ('kivy', 'Kivy GUI framework'),
        ('kivymd', 'KivyMD components'),
        ('pygame', 'Audio support'),
        ('requests', 'HTTP requests'),
    ]
    
    missing_deps = []
    
    for module, description in critical_imports:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} - MISSING")
            missing_deps.append(module)
    
    # Проверяем доступность дисплея
    try:
        import subprocess
        result = subprocess.run(['xset', 'q'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("  ✅ X11 display accessible")
        else:
            print("  ❌ X11 display not accessible")
            missing_deps.append("X11 display")
    except Exception as e:
        print(f"  ⚠️ Cannot check X11: {e}")
    
    if missing_deps:
        print(f"❌ Missing: {', '.join(missing_deps)}")
        return False
    
    print("✅ All Pi 5 dependencies available")
    return True

def launch_main_application():
    """ИСПРАВЛЕННЫЙ запуск основного приложения"""
    print("🎯 Launching main Bedrock application...")
    
    try:
        # КРИТИЧНО: Передаем конфигурацию в main.py через environment
        os.environ['BEDROCK_LAUNCHER_MODE'] = 'fullscreen'
        os.environ['BEDROCK_TARGET_WIDTH'] = '1024'
        os.environ['BEDROCK_TARGET_HEIGHT'] = '600'
        os.environ['BEDROCK_FULLSCREEN'] = 'auto'
        
        # Импортируем основное приложение
        from main import BedrockApp
        
        print("✅ Main application imported")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Убеждаемся что Kivy Window настроен правильно
        try:
            from kivy.core.window import Window
            print(f"🖥️ Initial Window size: {Window.size}")
            print(f"🖥️ Fullscreen mode: {Window.fullscreen}")
            
            # ПРИНУДИТЕЛЬНАЯ настройка fullscreen если нужно
            if Window.size != (1024, 600):
                print("🔧 Forcing window size to 1024x600")
                Window.size = (1024, 600)
            
            if not Window.fullscreen:
                print("🔧 Forcing fullscreen mode")
                Window.fullscreen = 'auto'
                
        except Exception as e:
            print(f"⚠️ Window check failed: {e}")
        
        # Создание и запуск приложения
        print("🚀 Creating application instance...")
        app = BedrockApp()
        
        print("🎮 Starting main application loop...")
        app.run()
        
        print("✅ Application finished normally")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Check that main.py exists and dependencies are installed")
        return False
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        
        # Детальное логирование ошибки
        import traceback
        error_details = traceback.format_exc()
        
        try:
            with open('logs/launcher_error.log', 'a') as f:
                f.write(f"\n[{datetime.now()}] Launcher Error:\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback:\n{error_details}\n")
        except:
            pass
        
        print("📋 Error details saved to logs/launcher_error.log")
        print(error_details)
        return False

def main():
    """ИСПРАВЛЕННАЯ главная функция лаунчера для Pi 5"""
    print("=" * 70)
    print("🎮 BEDROCK 2.0 - PI 5 FULLSCREEN LAUNCHER (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
    print("=" * 70)
    
    try:
        # Step 1: КРИТИЧЕСКАЯ настройка окружения ДО импорта Kivy
        setup_pi5_environment()
        
        # Step 2: Логирование информации о запуске
        log_startup_info()
        
        # Step 3: Проверка зависимостей
        if not check_pi5_dependencies():
            print("❌ Dependency check failed")
            print("💡 Run: source venv/bin/activate && pip install -r requirements.txt")
            sys.exit(1)
        
        # Step 4: Конфигурация Kivy для fullscreen
        if not configure_kivy_fullscreen():
            print("❌ Kivy fullscreen configuration failed")
            sys.exit(1)
        
        # Step 5: Запуск основного приложения
        if not launch_main_application():
            print("❌ Main application launch failed")
            sys.exit(1)
            
        print("🎉 Bedrock launcher completed successfully")
        
    except KeyboardInterrupt:
        print("\n⚠️ Launcher interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"❌ Fatal launcher error: {e}")
        import traceback
        traceback.print_exc()
        
        # Сохраняем критическую ошибку
        try:
            with open('logs/launcher_fatal.log', 'a') as f:
                f.write(f"\n[{datetime.now()}] FATAL ERROR:\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
        except:
            pass
            
        sys.exit(1)

if __name__ == "__main__":
    main()