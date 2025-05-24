#!/bin/bash

# Check Fullscreen Mode Script
# Run from WSL to check if Bedrock app is running in fullscreen mode on Pi

PI_HOST="192.168.1.233"
PI_USER="standa"
PI_PASS="crossover"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
info() { echo -e "${BLUE}[INFO] $1${NC}"; }

# Execute command on remote Pi
remote_exec() {
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "$1"
}

# Test connection
test_connection() {
    if ! command -v sshpass &> /dev/null; then
        error "sshpass not found. Install with: sudo apt install sshpass"
        exit 1
    fi
    
    if ! remote_exec "echo 'Connected'" >/dev/null 2>&1; then
        error "Cannot connect to Raspberry Pi at $PI_HOST"
        exit 1
    fi
    
    log "Connected to Raspberry Pi ✓"
}

# Check if app is running
check_app_running() {
    log "Checking if Bedrock app is running..."
    
    if remote_exec "pgrep -f 'python.*main.py' > /dev/null"; then
        PID=$(remote_exec "pgrep -f 'python.*main.py'")
        log "✓ Bedrock app is running (PID: $PID)"
        return 0
    else
        warn "✗ Bedrock app is not running"
        return 1
    fi
}

# Check display configuration
check_display_config() {
    log "Checking display configuration..."
    
    # Check boot config
    log "Boot configuration:"
    remote_exec "sudo grep -E 'hdmi_|gpu_mem|disable_overscan' /boot/firmware/config.txt | tail -10"
    
    echo
    log "Display environment:"
    remote_exec "echo \"DISPLAY: \$DISPLAY\""
    
    # Check X server
    if remote_exec "pgrep -x Xorg > /dev/null"; then
        log "✓ X server is running"
    else
        warn "✗ X server not running"
    fi
    
    # Check resolution
    log "Attempting to get current resolution..."
    RESOLUTION=$(remote_exec "DISPLAY=:0 xrandr 2>/dev/null | grep '*' | awk '{print \$1}' | head -1" || echo "unknown")
    if [ "$RESOLUTION" != "unknown" ] && [ -n "$RESOLUTION" ]; then
        log "Current resolution: $RESOLUTION"
        if [ "$RESOLUTION" = "1024x600" ]; then
            log "✓ Correct resolution set"
        else
            warn "✗ Resolution is not 1024x600"
        fi
    else
        warn "Could not determine resolution (may be normal via SSH)"
    fi
}

# Check fullscreen environment
check_fullscreen_env() {
    log "Checking fullscreen environment variables..."
    
    remote_exec "
        echo 'Environment variables for fullscreen:'
        echo \"KIVY_GL_BACKEND=\$KIVY_GL_BACKEND\"
        echo \"KIVY_WINDOW=\$KIVY_WINDOW\"
        echo \"SDL_VIDEO_FULLSCREEN_HEAD=\$SDL_VIDEO_FULLSCREEN_HEAD\"
        echo \"SDL_VIDEODRIVER=\$SDL_VIDEODRIVER\"
        
        echo
        echo 'Checking startup script environment:'
        if [ -f /home/standa/bedrock_start.sh ]; then
            echo '✓ Startup script exists'
            grep -E 'KIVY_|SDL_' /home/standa/bedrock_start.sh | head -5
        else
            echo '✗ Startup script not found'
        fi
    "
}

# Test fullscreen capability
test_fullscreen() {
    log "Testing fullscreen capability..."
    
    if remote_exec "[ -f /home/standa/bedrock-app/test_fullscreen.py ]"; then
        log "Running fullscreen test (this will show briefly on the Pi screen)..."
        
        # Run test in background and capture result
        TEST_RESULT=$(remote_exec "
            cd /home/standa/bedrock-app
            source venv/bin/activate
            export DISPLAY=:0
            timeout 15 python test_fullscreen.py > /tmp/fullscreen_test.log 2>&1 &
            TEST_PID=\$!
            sleep 12
            if kill -0 \$TEST_PID 2>/dev/null; then
                echo 'Test running successfully'
                kill \$TEST_PID 2>/dev/null || true
            else
                echo 'Test completed or failed'
            fi
            cat /tmp/fullscreen_test.log 2>/dev/null || echo 'No test output'
        ")
        
        log "Test result: $TEST_RESULT"
    else
        warn "Fullscreen test script not found"
        info "Creating test script..."
        
        # Create simple test script
        remote_exec "
            cd /home/standa/bedrock-app
            cat > test_fullscreen.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'

try:
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.core.window import Window
    from kivy.clock import Clock
    
    class TestApp(App):
        def build(self):
            Window.fullscreen = True
            Window.borderless = True
            label = Label(text='Fullscreen Test\\nThis will close in 10 seconds', font_size='30sp')
            Clock.schedule_once(lambda dt: self.stop(), 10)
            return label
    
    TestApp().run()
    print('Fullscreen test completed successfully')
except Exception as e:
    print(f'Fullscreen test failed: {e}')
    sys.exit(1)
EOF
            chmod +x test_fullscreen.py
            echo 'Test script created'
        "
    fi
}

# Check audio output
check_audio() {
    log "Checking audio configuration..."
    
    remote_exec "
        echo 'Audio devices:'
        aplay -l 2>/dev/null | grep -E 'card|device' || echo 'Could not list audio devices'
        
        echo
        echo 'Current audio routing:'
        amixer cget numid=3 2>/dev/null | grep -E 'values|name' || echo 'Could not get audio routing'
        
        echo
        echo 'HDMI audio test:'
        amixer cset numid=3 2 >/dev/null 2>&1 && echo '✓ HDMI audio set' || echo '✗ Could not set HDMI audio'
    "
}

# Get system performance
check_performance() {
    log "Checking system performance..."
    
    remote_exec "
        echo 'System load:'
        uptime
        
        echo
        echo 'Memory usage:'
        free -h
        
        echo
        echo 'GPU memory:'
        vcgencmd get_mem arm
        vcgencmd get_mem gpu
        
        echo
        echo 'Temperature:'
        vcgencmd measure_temp
        
        if pgrep -f 'python.*main.py' > /dev/null; then
            echo
            echo 'Bedrock app resource usage:'
            ps aux | grep 'python.*main.py' | grep -v grep | awk '{print \"CPU: \" \$3 \"%, Memory: \" \$4 \"%\"}'
        fi
    "
}

# Show application logs
show_recent_logs() {
    log "Recent application logs:"
    
    remote_exec "
        if [ -f /home/standa/bedrock-app/logs/bedrock.log ]; then
            echo 'Application log (last 10 lines):'
            tail -10 /home/standa/bedrock-app/logs/bedrock.log
        fi
        
        echo
        if [ -f /home/standa/bedrock-app/logs/startup.log ]; then
            echo 'Startup log (last 5 lines):'
            tail -5 /home/standa/bedrock-app/logs/startup.log
        fi
        
        echo
        if [ -f /home/standa/bedrock-app/logs/app.log ]; then
            echo 'App output log (last 5 lines):'
            tail -5 /home/standa/bedrock-app/logs/app.log
        fi
    "
}

# Restart app in fullscreen mode
restart_fullscreen() {
    log "Restarting app in fullscreen mode..."
    
    remote_exec "
        # Kill existing app
        pkill -f 'python.*main.py' || true
        sleep 3
        
        # Run management script to restart
        if [ -f /home/standa/manage_bedrock.sh ]; then
            /home/standa/manage_bedrock.sh force-full
        else
            # Manual restart
            cd /home/standa/bedrock-app
            export DISPLAY=:0
            export KIVY_GL_BACKEND=sdl2
            export KIVY_WINDOW=sdl2
            export SDL_VIDEO_FULLSCREEN_HEAD=0
            
            source venv/bin/activate
            nohup python main.py > logs/app.log 2>&1 &
            
            echo 'App restarted manually'
        fi
    "
    
    sleep 5
    check_app_running
}

# Main function
main() {
    echo "=== Bedrock App Fullscreen Check ==="
    echo
    
    test_connection
    echo
    
    check_app_running
    echo
    
    check_display_config
    echo
    
    check_fullscreen_env
    echo
    
    check_audio
    echo
    
    check_performance
    echo
    
    case "${1:-}" in
        test)
            test_fullscreen
            ;;
        restart)
            restart_fullscreen
            ;;
        logs)
            show_recent_logs
            ;;
        *)
            info "Additional commands:"
            info "  $0 test     - Run fullscreen test"
            info "  $0 restart  - Restart app in fullscreen mode"
            info "  $0 logs     - Show recent logs"
            ;;
    esac
    
    echo
    log "Fullscreen check completed!"
    info "If the app is not in fullscreen mode, try:"
    info "  $0 restart"
    info "Or manually: ssh $PI_USER@$PI_HOST './manage_bedrock.sh force-full'"
}

main "$@"