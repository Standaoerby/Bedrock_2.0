#!/usr/bin/env python3

"""
Bedrock 2.0 - УПРОЩЕННЫЙ Pi 5 Launcher
Исправленная версия с надёжным fullscreen для Raspberry Pi 5
"""

import os
import sys
from datetime import datetime

def setup_environment():
    """УПРОЩЕННАЯ настройка окружения для Pi 5"""
    print(f"🔧 Setting up Pi 5 environment...")
    
    # КРИТИЧЕСКИЕ environment variables для Pi 5
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'
    os.environ['SDL_VIDEODRIVER'] = 'x11'
    
    # ИСПРАВЛЕНИЕ: Убираем конфликтующие переменные
    # os.environ['KIVY_NO_CONFIG'] = '1'  # Убрано - может мешать fullscreen
    # os.environ['KIVY_NO_FILELOG'] = '1'  # Убрано - нужны логи
    
    print("✅ Environment configured for Pi 5")

def configure_kivy_fullscreen():
    """ИСПРАВЛЕННАЯ настройка Kivy для fullscreen режима"""
    print("🎯 Configuring Kivy for fullscreen...")
    
    try:
        from kivy.config import Config
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Простая и надёжная конфигурация fullscreen
        # Graphics settings для Pi 5 (1024x600 touchscreen)
        Config.set("graphics", "width", "1024")
        Config.set("graphics", "height", "600")
        Config.set("graphics", "fullscreen", "1")  # ОСНОВНАЯ настройка fullscreen
        Config.set("graphics", "borderless", "1")
        Config.set("graphics", "resizable", "0")
        Config.set("graphics", "show_cursor", "0")
        
        # УБРАНО: Проблемные настройки
        # Config.set("graphics", "window_state", "maximized")  # Может конфликтовать с fullscreen
        # Config.set("graphics", "position", "custom")         # Не нужно для fullscreen
        # Config.set("graphics", "left", "0")                  # Не нужно для fullscreen
        # Config.set("graphics", "top", "0")                   # Не нужно для fullscreen
        
        # Performance settings для Pi 5
        Config.set("graphics", "maxfps", "60")
        Config.set("graphics", "vsync", "1")
        Config.set("graphics", "multisamples", "0")  # Отключаем для производительности
        
        # Input settings для touchscreen
        Config.set("input", "mouse", "mouse,multitouch_on_demand")
        
        # Desktop settings
        Config.set("kivy", "desktop", "1")
        Config.set("kivy", "exit_on_escape", "0")  # Предотвращаем случайный выход
        
        print("✅ Kivy configured for Pi 5 fullscreen")
        return True
        
    except Exception as e:
        print(f"❌ Error configuring Kivy: {e}")
        return False

def log_startup_info():
    """Логирование информации о запуске"""
    startup_time = datetime.now()
    
    print(f"🚀 Starting Bedrock 2.0 for Raspberry Pi 5")
    print(f"📅 Startup time: {startup_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python version: {sys.version}")
    print(f"🖥️  Platform: {sys.platform}")
    
    # Log to file for debugging
    try:
        os.makedirs('logs', exist_ok=True)
        with open('logs/launcher.log', 'a') as f:
            f.write(f"\n[{startup_time}] Bedrock 2.0 Launcher Started\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Working directory: {os.getcwd()}\n")
    except Exception as e:
        print(f"⚠️  Could not write to log file: {e}")

def check_dependencies():
    """УПРОЩЕННАЯ проверка критических зависимостей"""
    print("🔍 Checking dependencies...")
    
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
            print(f"  ✅ {module} - {description}")
        except ImportError:
            print(f"  ❌ {module} - {description} (MISSING)")
            missing_deps.append(module)
    
    if missing_deps:
        print(f"❌ Missing critical dependencies: {', '.join(missing_deps)}")
        print("💡 Run: source venv/bin/activate && pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies available")
    return True

def launch_application():
    """УПРОЩЕННЫЙ запуск основного приложения"""
    print("🎯 Launching Bedrock application...")
    
    try:
        # Import и создание основного приложения
        from main import BedrockApp
        
        print("✅ Main application imported successfully")
        
        # ИСПРАВЛЕНИЕ: Дополнительная проверка что Kivy настроен правильно
        try:
            from kivy.core.window import Window
            print(f"🖥️  Window size will be: {Window.width}x{Window.height}")
            print(f"🖥️  Fullscreen mode: {Window.fullscreen}")
        except Exception as e:
            print(f"⚠️  Could not check window settings: {e}")
        
        # Создание и запуск приложения
        app = BedrockApp()
        print("🚀 Starting application main loop...")
        
        app.run()
        
        print("✅ Application finished normally")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Check that main.py exists and all dependencies are installed")
        return False
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        
        # Log detailed error для отладки
        import traceback
        error_details = traceback.format_exc()
        
        try:
            os.makedirs('logs', exist_ok=True)
            with open('logs/startup_error.log', 'a') as f:
                f.write(f"\n[{datetime.now()}] Launcher Error:\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback:\n{error_details}\n")
        except:
            pass
        
        print("📋 Error details:")
        print(error_details)
        return False

def main():
    """УПРОЩЕННАЯ главная функция лаунчера"""
    print("=" * 60)
    print("🎮 BEDROCK 2.0 - RASPBERRY PI 5 LAUNCHER (FIXED)")
    print("=" * 60)
    
    try:
        # Step 1: Setup environment
        setup_environment()
        
        # Step 2: Log startup information  
        log_startup_info()
        
        # Step 3: Check dependencies
        if not check_dependencies():
            print("❌ Dependency check failed")
            sys.exit(1)
        
        # Step 4: Configure Kivy для fullscreen
        if not configure_kivy_fullscreen():
            print("❌ Kivy configuration failed")
            sys.exit(1)
        
        # Step 5: Launch application
        if not launch_application():
            print("❌ Application launch failed")
            sys.exit(1)
            
        print("🎉 Bedrock launcher finished successfully")
        
    except KeyboardInterrupt:
        print("\n⚠️  Launcher interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"❌ Fatal launcher error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()