#!/bin/bash

# =============================================================================
# BEDROCK 2.0 - ИСПРАВЛЕННЫЙ СКРИПТ УПРАВЛЕНИЯ С ПРАВИЛЬНЫМИ ПЕРЕМЕННЫМИ ОКРУЖЕНИЯ
# Исправлена проблема с DISPLAY и переменными окружения
# =============================================================================

# Configuration
APP_DIR="/home/standa/bedrock-app"
APP_NAME="python.*bedrock_launcher.py"
LAUNCHER="bedrock_launcher.py"
VENV_PATH="$APP_DIR/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# НОВОЕ: Функция для установки переменных окружения
setup_environment() {
    log_info "Setting up environment variables..."
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Устанавливаем DISPLAY если не установлен
    if [[ -z "$DISPLAY" ]]; then
        export DISPLAY=:0
        log_info "DISPLAY set to :0"
    else
        log_info "DISPLAY already set to: $DISPLAY"
    fi
    
    # ИСПРАВЛЕНИЕ: Устанавливаем все переменные Kivy/SDL
    export KIVY_GL_BACKEND=sdl2
    export KIVY_WINDOW=sdl2
    export SDL_VIDEO_FULLSCREEN_HEAD=0
    export SDL_VIDEODRIVER=x11
    
    log_success "Environment variables configured"
    
    # НОВОЕ: Проверяем доступность дисплея
    if ! check_display_available; then
        log_warning "Display may not be fully available yet"
        return 1
    else
        log_success "Display is available"
        return 0
    fi
}

# НОВОЕ: Проверка доступности дисплея
check_display_available() {
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if timeout 5 xset q >/dev/null 2>&1; then
            return 0  # Display available
        fi
        
        log_info "Waiting for display... attempt $attempt/$max_attempts"
        sleep 2
        ((attempt++))
    done
    
    return 1  # Display not available after max attempts
}

# Check if we're in the right directory
check_environment() {
    if [[ ! -d "$APP_DIR" ]]; then
        log_error "App directory not found: $APP_DIR"
        exit 1
    fi
    
    if [[ ! -f "$APP_DIR/$LAUNCHER" ]]; then
        log_error "Launcher not found: $APP_DIR/$LAUNCHER"
        exit 1
    fi
    
    if [[ ! -d "$VENV_PATH" ]]; then
        log_error "Virtual environment not found: $VENV_PATH"
        exit 1
    fi
}

# Get app status
get_app_status() {
    if pgrep -f "$APP_NAME" >/dev/null 2>&1; then
        return 0  # Running
    else
        return 1  # Not running
    fi
}

# ИСПРАВЛЕННАЯ функция запуска приложения
start_app() {
    log_info "Starting Bedrock application..."
    
    if get_app_status; then
        log_warning "Application is already running"
        show_status
        return 0
    fi
    
    cd "$APP_DIR" || exit 1
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Устанавливаем переменные окружения
    if ! setup_environment; then
        log_error "Failed to setup environment - display may not be ready"
        log_info "Try waiting and running again, or check if X11 is running"
        return 1
    fi
    
    # Activate virtual environment and start app
    source "$VENV_PATH/bin/activate"
    
    # ДОБАВЛЕНО: Дополнительная проверка что все переменные установлены
    log_info "Environment check:"
    log_info "  DISPLAY: ${DISPLAY:-NOT SET}"
    log_info "  KIVY_GL_BACKEND: ${KIVY_GL_BACKEND:-NOT SET}"
    log_info "  KIVY_WINDOW: ${KIVY_WINDOW:-NOT SET}"
    log_info "  SDL_VIDEODRIVER: ${SDL_VIDEODRIVER:-NOT SET}"
    
    # Start in background with logging
    nohup python "$LAUNCHER" > logs/app.log 2>&1 &
    APP_PID=$!
    
    # Wait a bit and check if it started successfully
    sleep 5
    
    if get_app_status; then
        log_success "Application started successfully (PID: $APP_PID)"
        
        # Проверяем fullscreen через 15 секунд (дольше для стабильности)
        sleep 15
        check_fullscreen
    else
        log_error "Application failed to start"
        log_info "Check logs: tail -20 $APP_DIR/logs/app.log"
        return 1
    fi
}

# УЛУЧШЕННАЯ проверка fullscreen режима
check_fullscreen() {
    log_info "Checking fullscreen mode..."
    
    # ИСПРАВЛЕНИЕ: Проверяем что DISPLAY доступен
    if [[ -z "$DISPLAY" ]]; then
        export DISPLAY=:0
    fi
    
    # Проверяем размер окна приложения
    if command -v xwininfo >/dev/null 2>&1; then
        # ИСПРАВЛЕНИЕ: Добавляем таймаут для xwininfo
        if timeout 10 xwininfo -root -tree 2>/dev/null | grep -i bedrock >/dev/null; then
            WINDOW_ID=$(timeout 10 xwininfo -root -tree 2>/dev/null | grep -i bedrock | head -1 | awk '{print $1}')
            
            if [[ -n "$WINDOW_ID" ]]; then
                WINDOW_INFO=$(timeout 5 xwininfo -id "$WINDOW_ID" 2>/dev/null)
                if [[ -n "$WINDOW_INFO" ]]; then
                    WIDTH=$(echo "$WINDOW_INFO" | grep "Width:" | awk '{print $2}')
                    HEIGHT=$(echo "$WINDOW_INFO" | grep "Height:" | awk '{print $2}')
                    
                    if [[ "$WIDTH" == "1024" && "$HEIGHT" == "600" ]]; then
                        log_success "✅ Fullscreen mode active: ${WIDTH}x${HEIGHT}"
                    elif [[ -n "$WIDTH" && -n "$HEIGHT" ]]; then
                        log_warning "⚠️ Window size: ${WIDTH}x${HEIGHT} (expected 1024x600)"
                    else
                        log_warning "⚠️ Could not determine window size"
                    fi
                else
                    log_warning "⚠️ Could not get window info"
                fi
            else
                log_warning "⚠️ Could not find Bedrock window ID"
            fi
        else
            log_warning "⚠️ Could not find Bedrock window or xwininfo timed out"
        fi
    else
        log_info "xwininfo not available for fullscreen check"
    fi
}

# Stop the application
stop_app() {
    log_info "Stopping Bedrock application..."
    
    if ! get_app_status; then
        log_warning "Application is not running"
        return 0
    fi
    
    # Try graceful shutdown first
    pkill -TERM -f "$APP_NAME" 2>/dev/null
    
    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
        if ! get_app_status; then
            log_success "Application stopped gracefully"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    log_warning "Forcing application shutdown..."
    pkill -KILL -f "$APP_NAME" 2>/dev/null
    
    sleep 2
    
    if ! get_app_status; then
        log_success "Application stopped"
    else
        log_error "Failed to stop application"
        return 1
    fi
}

# Restart the application
restart_app() {
    log_info "Restarting Bedrock application..."
    
    stop_app
    sleep 3
    start_app
}

# УЛУЧШЕННАЯ функция отображения статуса
show_status() {
    echo "=== BEDROCK APPLICATION STATUS ==="
    
    if get_app_status; then
        PIDS=$(pgrep -f "$APP_NAME")
        log_success "Application is RUNNING"
        
        for pid in $PIDS; do
            echo "  PID: $pid"
            ps -p $pid -o pid,ppid,etime,cmd --no-headers 2>/dev/null || echo "  Process details unavailable"
        done
    else
        log_warning "Application is NOT RUNNING"
    fi
    
    echo ""
    echo "=== ENVIRONMENT STATUS ==="
    echo "  DISPLAY: ${DISPLAY:-Not set}"
    echo "  KIVY_GL_BACKEND: ${KIVY_GL_BACKEND:-Not set}"
    echo "  KIVY_WINDOW: ${KIVY_WINDOW:-Not set}"
    echo "  SDL_VIDEO_FULLSCREEN_HEAD: ${SDL_VIDEO_FULLSCREEN_HEAD:-Not set}"
    echo "  SDL_VIDEODRIVER: ${SDL_VIDEODRIVER:-Not set}"
    
    # НОВОЕ: Проверяем доступность дисплея
    echo ""
    echo "=== DISPLAY STATUS ==="
    if [[ -n "$DISPLAY" ]]; then
        if timeout 5 xset q >/dev/null 2>&1; then
            log_success "X11 Display: AVAILABLE"
            # Получаем информацию о разрешении
            if command -v xrandr >/dev/null 2>&1; then
                SCREEN_INFO=$(timeout 5 xrandr 2>/dev/null | grep "connected primary" | head -1)
                if [[ -n "$SCREEN_INFO" ]]; then
                    echo "  Screen: $SCREEN_INFO"
                fi
            fi
        else
            log_error "X11 Display: NOT AVAILABLE"
        fi
    else
        log_error "DISPLAY variable not set"
    fi
    
    echo ""
    echo "=== SYSTEM INFORMATION ==="
    echo "  Directory: $APP_DIR"
    echo "  Launcher: $LAUNCHER"
    echo "  Virtual Env: $VENV_PATH"
    echo "  Uptime: $(uptime)"
    echo "  Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
    echo "  Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
    
    # Проверяем автостарт
    echo ""
    echo "=== AUTOSTART STATUS ==="
    if [[ -f "$HOME/.config/autostart/bedrock.desktop" ]]; then
        log_success "Autostart: ENABLED"
        echo "  File: $HOME/.config/autostart/bedrock.desktop"
    else
        log_warning "Autostart: DISABLED"
    fi
}

# Show recent logs
show_logs() {
    local lines=${1:-20}
    
    echo "=== RECENT APPLICATION LOGS ==="
    
    # Main application log
    if [[ -f "$APP_DIR/logs/app.log" ]]; then
        echo "--- Main Application Log (last $lines lines) ---"
        tail -$lines "$APP_DIR/logs/app.log"
    else
        log_warning "Main application log not found"
    fi
    
    echo ""
    
    # Launcher log
    if [[ -f "$APP_DIR/logs/launcher.log" ]]; then
        echo "--- Launcher Log (last $lines lines) ---"
        tail -$lines "$APP_DIR/logs/launcher.log"
    fi
    
    echo ""
    
    # Autostart log
    if [[ -f "$APP_DIR/logs/autostart.log" ]]; then
        echo "--- Autostart Log (last $lines lines) ---"
        tail -$lines "$APP_DIR/logs/autostart.log"
    fi
    
    echo ""
    
    # Error log
    if [[ -f "$APP_DIR/logs/startup_error.log" ]]; then
        echo "--- Startup Errors (last $lines lines) ---"
        tail -$lines "$APP_DIR/logs/startup_error.log"
    fi
}

# ИСПРАВЛЕННАЯ функция принудительного fullscreen
force_fullscreen() {
    log_info "Force starting in fullscreen mode..."
    
    stop_app
    sleep 2
    
    cd "$APP_DIR" || exit 1
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Устанавливаем переменные окружения
    if ! setup_environment; then
        log_error "Failed to setup environment for fullscreen mode"
        return 1
    fi
    
    source "$VENV_PATH/bin/activate"
    
    # Убеждаемся что курсор скрыт
    if command -v unclutter >/dev/null 2>&1; then
        unclutter -idle 1 -root &
        log_info "Cursor hidden with unclutter"
    fi
    
    # Start with explicit fullscreen
    nohup python "$LAUNCHER" > logs/fullscreen.log 2>&1 &
    
    sleep 5
    
    if get_app_status; then
        log_success "Application started in fullscreen mode"
        sleep 15
        check_fullscreen
    else
        log_error "Failed to start in fullscreen mode"
        log_info "Check logs: tail -20 $APP_DIR/logs/fullscreen.log"
    fi
}

# Run health check
health_check() {
    log_info "Running health check..."
    
    cd "$APP_DIR" || exit 1
    source "$VENV_PATH/bin/activate"
    
    if [[ -f "health_check.py" ]]; then
        python health_check.py "$@"
    else
        log_error "Health check script not found"
        return 1
    fi
}

# Test theme switching
test_theme() {
    log_info "Testing theme switching..."
    
    cd "$APP_DIR" || exit 1
    source "$VENV_PATH/bin/activate"
    
    python -c "
try:
    from utils.theme_manager import ThemeManager
    from main import BedrockApp
    
    # Create minimal app instance for testing
    class TestApp:
        def __init__(self):
            self.theme_name = 'minecraft'
            self.theme_mode = 'light'
            self.theme_config = {}
    
    app = TestApp()    
    tm = ThemeManager(app)
    
    print('✅ ThemeManager created successfully')
    
    # Test theme loading
    light_config = tm.load_theme_config('minecraft', 'light')
    if light_config:
        print('✅ Light theme loaded successfully')
        print(f'   Font color: {light_config.get(\"font_color\", \"Not found\")}')
    else:
        print('❌ Failed to load light theme')
    
    # Test dark theme availability
    if tm.is_dark_theme_available():
        print('✅ Dark theme is available')
        dark_config = tm.load_theme_config('minecraft', 'dark')
        if dark_config:
            print('✅ Dark theme loaded successfully')
            print(f'   Font color: {dark_config.get(\"font_color\", \"Not found\")}')
        else:
            print('❌ Failed to load dark theme')
    else:
        print('⚠️  Dark theme not available - creating default...')
        if tm.create_default_dark_theme():
            print('✅ Default dark theme created')
        else:
            print('❌ Failed to create dark theme')
    
    print('🎉 Theme test completed successfully')

except Exception as e:
    print(f'❌ Theme test failed: {e}')
    import traceback
    traceback.print_exc()
"
}

# УЛУЧШЕННАЯ диагностика дисплея
display_info() {
    log_info "Display diagnostic information..."
    
    echo "=== DISPLAY CONFIGURATION ==="
    echo "DISPLAY variable: ${DISPLAY:-Not set}"
    
    # ИСПРАВЛЕНИЕ: Устанавливаем DISPLAY если не установлен
    if [[ -z "$DISPLAY" ]]; then
        export DISPLAY=:0
        echo "DISPLAY set to :0 for diagnostics"
    fi
    
    # Проверяем доступность X11
    echo ""
    echo "--- X11 Server Status ---"
    if timeout 5 xset q >/dev/null 2>&1; then
        log_success "X11 server is running and accessible"
        
        # Информация о дисплее
        echo "X11 server info:"
        timeout 5 xset q 2>/dev/null | head -5
    else
        log_error "X11 server is not accessible"
        echo "This usually means:"
        echo "  1. X11 hasn't started yet (try waiting)"
        echo "  2. User doesn't have permission to access display"
        echo "  3. DISPLAY variable is wrong"
    fi
    
    if command -v xrandr >/dev/null 2>&1; then
        echo ""
        echo "--- Screen Resolution ---"
        if timeout 10 xrandr 2>/dev/null | grep -E "(connected|Screen)" | head -5; then
            log_success "Screen information retrieved"
        else
            log_error "Could not get screen information"
        fi
    fi
    
    if command -v xwininfo >/dev/null 2>&1; then
        echo ""
        echo "--- Active Windows ---"
        if timeout 10 xwininfo -root -tree 2>/dev/null | grep -E "(Bedrock|python)" | head -5; then
            log_success "Window information retrieved"
        else
            log_warning "No Bedrock windows found or xwininfo failed"
        fi
    fi
    
    echo ""
    echo "--- Environment Variables ---"
    echo "KIVY_GL_BACKEND: ${KIVY_GL_BACKEND:-Not set}"
    echo "KIVY_WINDOW: ${KIVY_WINDOW:-Not set}"
    echo "SDL_VIDEO_FULLSCREEN_HEAD: ${SDL_VIDEO_FULLSCREEN_HEAD:-Not set}"
    echo "SDL_VIDEODRIVER: ${SDL_VIDEODRIVER:-Not set}"
    
    echo ""
    echo "--- Desktop Environment ---"
    echo "XDG_CURRENT_DESKTOP: ${XDG_CURRENT_DESKTOP:-Not set}"
    echo "XDG_SESSION_TYPE: ${XDG_SESSION_TYPE:-Not set}"
    echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-Not set}"
    
    echo ""
    echo "--- Process Information ---"
    echo "X11 processes:"
    ps aux | grep -E "(Xorg|X |startx)" | grep -v grep | head -3
    
    echo ""
    echo "Desktop processes:"
    ps aux | grep -E "(lxsession|openbox|xfce|gnome)" | grep -v grep | head -3
}

# НОВОЕ: Функция исправления автостарта
fix_autostart() {
    log_info "Fixing autostart configuration..."
    
    # Создаем правильный autostart файл
    AUTOSTART_DIR="$HOME/.config/autostart"
    AUTOSTART_FILE="$AUTOSTART_DIR/bedrock.desktop"
    
    mkdir -p "$AUTOSTART_DIR"
    
    # Удаляем старые файлы
    rm -f "$AUTOSTART_DIR"/bedrock*.desktop
    
    cat > "$AUTOSTART_FILE" << 'EOF'
[Desktop Entry]
Type=Application
Name=Bedrock 2.0 - Pi 5 Kiosk (FIXED)
Comment=Bedrock 2.0 fullscreen application - ENVIRONMENT VARIABLES FIXED
Exec=bash -c "sleep 20 && export DISPLAY=:0 && export KIVY_GL_BACKEND=sdl2 && export KIVY_WINDOW=sdl2 && export SDL_VIDEO_FULLSCREEN_HEAD=0 && export SDL_VIDEODRIVER=x11 && cd /home/standa/bedrock-app && source venv/bin/activate && python bedrock_launcher.py >> logs/autostart.log 2>&1"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
Terminal=false
Categories=Kiosk;System;Utility;
Icon=/home/standa/bedrock-app/assets/images/bedrock_icon.png
X-GNOME-Autostart-Delay=20
X-KDE-autostart-after=panel
EOF
    
    chmod +x "$AUTOSTART_FILE"
    
    log_success "Autostart file fixed: $AUTOSTART_FILE"
    log_info "Changes will take effect after next reboot"
}

# Show help
show_help() {
    echo "Bedrock 2.0 Management Script - FIXED VERSION with Environment Variables"
    echo ""
    echo "USAGE: $0 COMMAND [OPTIONS]"
    echo ""
    echo "COMMANDS:"
    echo "  start          Start the Bedrock application"
    echo "  stop           Stop the Bedrock application"
    echo "  restart        Restart the Bedrock application"
    echo "  status         Show application status and system info"
    echo "  logs [N]       Show recent logs (default: 20 lines)"
    echo "  force-full     Force start in fullscreen mode"
    echo "  health         Run health check"
    echo "  health --fix   Run health check with auto-fixes"
    echo "  test-theme     Test theme switching functionality"
    echo "  display        Show display diagnostic information"
    echo "  fix-autostart  Fix autostart configuration"
    echo "  help           Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 start                    # Start application"
    echo "  $0 logs 50                  # Show last 50 log lines"
    echo "  $0 health --fix             # Run health check with fixes"
    echo "  $0 force-full               # Force fullscreen start"
    echo "  $0 display                  # Show display info"
    echo "  $0 fix-autostart            # Fix autostart issues"
    echo ""
    echo "TROUBLESHOOTING:"
    echo "  If DISPLAY errors: run 'fix-autostart' and reboot"
    echo "  If app won't start: check 'display' and 'status'"
    echo "  For fullscreen issues: try 'force-full'"
    echo ""
    echo "FILES:"
    echo "  App Directory: $APP_DIR"
    echo "  Launcher: $LAUNCHER"
    echo "  Virtual Env: $VENV_PATH"
    echo "  Autostart: ~/.config/autostart/bedrock.desktop"
}

# Main function
main() {
    # Check environment first
    check_environment
    
    case "${1:-help}" in
        start)
            start_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            restart_app
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-20}"
            ;;
        force-full|force-fullscreen)
            force_fullscreen
            ;;
        health)
            shift  # Remove 'health' from args
            health_check "$@"
            ;;
        test-theme|theme-test)
            test_theme
            ;;
        display|disp)
            display_info
            ;;
        fix-autostart)
            fix_autostart
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"