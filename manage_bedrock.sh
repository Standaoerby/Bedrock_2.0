#!/bin/bash

# =============================================================================
# BEDROCK 2.0 - ИСПРАВЛЕННЫЙ СКРИПТ УПРАВЛЕНИЯ
# Единый скрипт управления приложением на Raspberry Pi 5
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

# Start the application
start_app() {
    log_info "Starting Bedrock application..."
    
    if get_app_status; then
        log_warning "Application is already running"
        show_status
        return 0
    fi
    
    cd "$APP_DIR" || exit 1
    
    # Activate virtual environment and start app
    source "$VENV_PATH/bin/activate"
    
    # ИСПРАВЛЕНО: Устанавливаем переменные окружения для fullscreen
    export DISPLAY=:0
    export KIVY_GL_BACKEND=sdl2
    export KIVY_WINDOW=sdl2
    export SDL_VIDEO_FULLSCREEN_HEAD=0
    export SDL_VIDEODRIVER=x11
    
    # Start in background with logging
    nohup python "$LAUNCHER" > logs/app.log 2>&1 &
    APP_PID=$!
    
    # Wait a bit and check if it started successfully
    sleep 5
    
    if get_app_status; then
        log_success "Application started successfully (PID: $APP_PID)"
        
        # НОВОЕ: Проверяем fullscreen через 10 секунд
        sleep 10
        check_fullscreen
    else
        log_error "Application failed to start"
        log_info "Check logs: tail -20 $APP_DIR/logs/app.log"
        return 1
    fi
}

# НОВОЕ: Проверка fullscreen режима
check_fullscreen() {
    log_info "Checking fullscreen mode..."
    
    # Проверяем размер окна приложения
    if command -v xwininfo >/dev/null 2>&1; then
        # Ищем окно Bedrock
        WINDOW_ID=$(xwininfo -root -tree | grep -i bedrock | head -1 | awk '{print $1}')
        
        if [[ -n "$WINDOW_ID" ]]; then
            WINDOW_INFO=$(xwininfo -id "$WINDOW_ID" 2>/dev/null)
            WIDTH=$(echo "$WINDOW_INFO" | grep "Width:" | awk '{print $2}')
            HEIGHT=$(echo "$WINDOW_INFO" | grep "Height:" | awk '{print $2}')
            
            if [[ "$WIDTH" == "1024" && "$HEIGHT" == "600" ]]; then
                log_success "✅ Fullscreen mode active: ${WIDTH}x${HEIGHT}"
            else
                log_warning "⚠️ Window size: ${WIDTH}x${HEIGHT} (expected 1024x600)"
            fi
        else
            log_warning "⚠️ Could not find Bedrock window"
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

# Show application status
show_status() {
    echo "=== BEDROCK APPLICATION STATUS ==="
    
    if get_app_status; then
        PIDS=$(pgrep -f "$APP_NAME")
        log_success "Application is RUNNING"
        
        for pid in $PIDS; do
            echo "  PID: $pid"
            ps -p $pid -o pid,ppid,etime,cmd --no-headers 2>/dev/null || echo "  Process details unavailable"
        done
        
        # НОВОЕ: Показываем информацию о дисплее
        if [[ -n "$DISPLAY" ]]; then
            echo "  Display: $DISPLAY"
            
            # Проверяем размер экрана
            if command -v xrandr >/dev/null 2>&1; then
                SCREEN_INFO=$(xrandr 2>/dev/null | grep "connected primary" | head -1)
                if [[ -n "$SCREEN_INFO" ]]; then
                    echo "  Screen: $SCREEN_INFO"
                fi
            fi
        fi
    else
        log_warning "Application is NOT RUNNING"
    fi
    
    echo ""
    echo "=== SYSTEM INFORMATION ==="
    echo "  Directory: $APP_DIR"
    echo "  Launcher: $LAUNCHER"
    echo "  Virtual Env: $VENV_PATH"
    echo "  Display: ${DISPLAY:-Not set}"
    echo "  Uptime: $(uptime)"
    echo "  Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
    echo "  Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
    
    # НОВОЕ: Проверяем автостарт
    echo ""
    echo "=== AUTOSTART STATUS ==="
    if [[ -f "$HOME/.config/autostart/bedrock.desktop" ]]; then
        log_success "Autostart: ENABLED"
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

# Force fullscreen start
force_fullscreen() {
    log_info "Force starting in fullscreen mode..."
    
    stop_app
    sleep 2
    
    cd "$APP_DIR" || exit 1
    source "$VENV_PATH/bin/activate"
    
    # ИСПРАВЛЕНО: Принудительные настройки fullscreen
    export DISPLAY=:0
    export KIVY_GL_BACKEND=sdl2
    export KIVY_WINDOW=sdl2
    export SDL_VIDEO_FULLSCREEN_HEAD=0
    export SDL_VIDEODRIVER=x11
    
    # Убеждаемся что курсор скрыт
    if command -v unclutter >/dev/null 2>&1; then
        unclutter -idle 1 -root &
    fi
    
    # Start with explicit fullscreen
    nohup python "$LAUNCHER" > logs/fullscreen.log 2>&1 &
    
    sleep 5
    
    if get_app_status; then
        log_success "Application started in fullscreen mode"
        sleep 10
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

# НОВОЕ: Диагностика дисплея
display_info() {
    log_info "Display diagnostic information..."
    
    echo "=== DISPLAY CONFIGURATION ==="
    echo "DISPLAY variable: ${DISPLAY:-Not set}"
    
    if command -v xrandr >/dev/null 2>&1; then
        echo ""
        echo "--- Screen Resolution ---"
        xrandr | grep -E "(connected|Screen)"
    fi
    
    if command -v xwininfo >/dev/null 2>&1; then
        echo ""
        echo "--- Active Windows ---"
        xwininfo -root -tree | grep -E "(Bedrock|python)" | head -5
    fi
    
    echo ""
    echo "--- Environment Variables ---"
    echo "KIVY_GL_BACKEND: ${KIVY_GL_BACKEND:-Not set}"
    echo "KIVY_WINDOW: ${KIVY_WINDOW:-Not set}"
    echo "SDL_VIDEO_FULLSCREEN_HEAD: ${SDL_VIDEO_FULLSCREEN_HEAD:-Not set}"
    echo "SDL_VIDEODRIVER: ${SDL_VIDEODRIVER:-Not set}"
}

# Show help
show_help() {
    echo "Bedrock 2.0 Management Script - FIXED VERSION"
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
    echo "  help           Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 start                    # Start application"
    echo "  $0 logs 50                  # Show last 50 log lines"
    echo "  $0 health --fix             # Run health check with fixes"
    echo "  $0 force-full               # Force fullscreen start"
    echo "  $0 display                  # Show display info"
    echo ""
    echo "FILES:"
    echo "  App Directory: $APP_DIR"
    echo "  Launcher: $LAUNCHER"
    echo "  Virtual Env: $VENV_PATH"
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