#!/bin/bash

# Test New Features Script for Bedrock 2.0
# Tests light sensor, volume buttons, and auto theme switching
# Run from WSL to deploy and test on Raspberry Pi

PI_HOST="192.168.1.233"
PI_USER="standa"
PI_PASS="crossover"
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"
REMOTE_PROJECT_PATH="/home/standa/bedrock-app"

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

# Deploy updated code
deploy_updates() {
    log "Deploying updated Bedrock code..."
    
    # Create exclude file for rsync
    EXCLUDE_FILE=$(mktemp)
    cat > "$EXCLUDE_FILE" << 'EOF'
.git/
.gitignore
venv/
__pycache__/
.pytest_cache/
.coverage
*.pyc
*.pyo
*.pyd
.DS_Store
Thumbs.db
*.log
EOF

    # Sync files
    rsync -avz --delete \
        --exclude-from="$EXCLUDE_FILE" \
        --progress \
        -e "sshpass -p $PI_PASS ssh -o StrictHostKeyChecking=no" \
        "$LOCAL_PROJECT_PATH/" \
        "$PI_USER@$PI_HOST:$REMOTE_PROJECT_PATH/"
    
    rm "$EXCLUDE_FILE"
    
    if [ $? -eq 0 ]; then
        log "✓ Code deployed successfully"
    else
        error "✗ Code deployment failed"
        exit 1
    fi
}

# Test connection
test_connection() {
    log "Testing connection to Raspberry Pi..."
    if remote_exec "echo 'Connected'" >/dev/null 2>&1; then
        log "✓ Connection successful"
    else
        error "✗ Cannot connect to Pi"
        exit 1
    fi
}

# Test GPIO sensors
test_gpio_sensors() {
    log "Testing GPIO sensors and buttons..."
    
    remote_exec "
        cd $REMOTE_PROJECT_PATH
        python3 << 'EOF'
import sys
import time
import os

# Add project to path
sys.path.append('/home/standa/bedrock-app')

try:
    # Test light sensor
    print('=== Testing Light Sensor ===')
    from services.sensor_service import SensorService
    
    sensor_service = SensorService()
    sensor_service.start()
    time.sleep(2)  # Let it initialize
    
    # Get readings
    readings = sensor_service.get_readings()
    light_status = sensor_service.get_light_sensor_status()
    
    print(f'Light Level: {\"Light\" if readings.get(\"light_level\") else \"Dark\"}')
    print(f'Raw Value: {readings.get(\"light_raw\", 0)}')
    print(f'GPIO Available: {light_status.get(\"gpio_available\", False)}')
    print(f'Using Mock: {light_status.get(\"using_mock\", True)}')
    
    sensor_service.stop()
    print('✓ Light sensor test completed')
    
except Exception as e:
    print(f'✗ Light sensor test failed: {e}')

try:
    # Test volume control
    print()
    print('=== Testing Volume Control ===')
    from services.volume_service import VolumeControlService
    
    volume_service = VolumeControlService()
    if volume_service.start():
        current_vol = volume_service.get_volume()
        print(f'Current Volume: {current_vol}%')
        
        # Test volume up
        volume_service.set_volume(min(current_vol + 10, 100))
        new_vol = volume_service.get_volume()
        print(f'After Volume Up: {new_vol}%')
        
        # Test volume down
        volume_service.set_volume(max(current_vol - 5, 0))
        final_vol = volume_service.get_volume()
        print(f'After Volume Down: {final_vol}%')
        
        # Restore original volume
        volume_service.set_volume(current_vol)
        print(f'Restored to: {volume_service.get_volume()}%')
        
        status = volume_service.get_status()
        print(f'GPIO Available: {status.get(\"gpio_available\", False)}')
        print(f'Button Pins: Up={status.get(\"button_pins\", {}).get(\"volume_up\", \"?\")} Down={status.get(\"button_pins\", {}).get(\"volume_down\", \"?\")}')
        
        volume_service.stop()
        print('✓ Volume control test completed')
    else:
        print('✗ Volume control failed to start')
        
except Exception as e:
    print(f'✗ Volume control test failed: {e}')

print()
print('=== GPIO Test Summary ===')
print('All tests completed. Check results above.')
EOF
    "
}

# Test auto theme switching
test_auto_theme() {
    log "Testing auto theme switching..."
    
    remote_exec "
        cd $REMOTE_PROJECT_PATH
        python3 << 'EOF'
import sys
import json
import os

sys.path.append('/home/standa/bedrock-app')

try:
    # Load current user config
    with open('config/user.json', 'r') as f:
        config = json.load(f)
    
    print('=== Current Theme Settings ===')
    print(f'Theme: {config.get(\"theme\", \"unknown\")}')
    print(f'Mode: {config.get(\"theme_mode\", \"unknown\")}')
    print(f'Auto Theme: {config.get(\"auto_theme_enabled\", False)}')
    print(f'Switch Delay: {config.get(\"theme_switch_delay\", 5)}s')
    
    # Check if themes exist
    theme_name = config.get('theme', 'minecraft')
    light_path = f'themes/{theme_name}/light/theme.json'
    dark_path = f'themes/{theme_name}/dark/theme.json'
    
    print()
    print('=== Theme Files ===')
    print(f'Light theme: {\"✓\" if os.path.exists(light_path) else \"✗\"} {light_path}')
    print(f'Dark theme: {\"✓\" if os.path.exists(dark_path) else \"✗\"} {dark_path}')
    
    if os.path.exists(dark_path):
        print('✓ Auto theme switching available')
    else:
        print('✗ Dark theme not available - auto switching disabled')
    
except Exception as e:
    print(f'✗ Theme test failed: {e}')
EOF
    "
}

# Interactive button test
test_buttons_interactive() {
    log "Starting interactive button test (30 seconds)..."
    log "Press volume buttons on the Pi now!"
    
    remote_exec "
        cd $REMOTE_PROJECT_PATH
        timeout 30 python3 << 'EOF'
import sys
import time

sys.path.append('/home/standa/bedrock-app')

try:
    from services.volume_service import VolumeControlService
    
    volume_service = VolumeControlService()
    if volume_service.start():
        print('Volume buttons ready - press them now!')
        print('Volume Up = GPIO 23, Volume Down = GPIO 24')
        print('Test will run for 30 seconds...')
        
        # Monitor for button presses
        volume_service.test_volume_buttons(30)
        
        volume_service.stop()
    else:
        print('Could not start volume service')
        
except KeyboardInterrupt:
    print('Button test interrupted')
except Exception as e:
    print(f'Button test error: {e}')
EOF
    "
    
    log "Interactive button test completed"
}

# Test light sensor changes
test_light_sensor_interactive() {
    log "Starting interactive light sensor test (20 seconds)..."
    log "Cover and uncover the light sensor now!"
    
    remote_exec "
        cd $REMOTE_PROJECT_PATH
        timeout 20 python3 << 'EOF'
import sys
import time

sys.path.append('/home/standa/bedrock-app')

try:
    from services.sensor_service import SensorService
    
    sensor_service = SensorService()
    sensor_service.start()
    time.sleep(2)
    
    print('Light sensor monitoring - cover/uncover sensor now!')
    print('Test will run for 20 seconds...')
    
    last_level = None
    for i in range(40):  # 20 seconds, check every 0.5s
        readings = sensor_service.get_readings()
        current_level = readings.get('light_level', True)
        raw_value = readings.get('light_raw', 0)
        
        if current_level != last_level:
            status = 'Light' if current_level else 'Dark'
            print(f'Light level changed: {status} (raw: {raw_value})')
            last_level = current_level
        
        time.sleep(0.5)
    
    sensor_service.stop()
    print('Light sensor test completed')
    
except Exception as e:
    print(f'Light sensor test error: {e}')
EOF
    "
    
    log "Interactive light sensor test completed"
}

# Run full application test
test_full_app() {
    log "Testing full application with new features..."
    
    # Stop any running instance
    remote_exec "pkill -f 'python.*main.py' || true"
    sleep 2
    
    # Start app in background for testing
    remote_exec "
        cd $REMOTE_PROJECT_PATH
        export DISPLAY=:0
        export KIVY_GL_BACKEND=sdl2
        export KIVY_WINDOW=sdl2
        
        source venv/bin/activate
        timeout 30 python main.py > /tmp/bedrock_test.log 2>&1 &
        TEST_PID=\$!
        
        echo 'App started with PID: '\$TEST_PID
        sleep 5
        
        if kill -0 \$TEST_PID 2>/dev/null; then
            echo '✓ App is running'
            sleep 20
            kill \$TEST_PID 2>/dev/null || true
            echo '✓ App test completed'
        else
            echo '✗ App failed to start'
        fi
        
        echo
        echo '=== App Log (last 10 lines) ==='
        tail -10 /tmp/bedrock_test.log 2>/dev/null || echo 'No log available'
    "
}

# System status check
check_system_status() {
    log "Checking system status..."
    
    remote_exec "
        echo '=== System Status ==='
        echo 'CPU Temperature:'
        vcgencmd measure_temp
        
        echo
        echo 'Memory Usage:'
        free -h
        
        echo
        echo 'GPIO Status:'
        gpio readall | grep -E '18|23|24'
        
        echo
        echo 'I2C Devices:'
        i2cdetect -y 1 2>/dev/null | grep -E '38|53' || echo 'No I2C devices found'
        
        echo
        echo 'Audio Devices:'
        aplay -l 2>/dev/null | head -5 || echo 'No audio devices'
        
        echo
        echo 'Current Volume:'
        amixer get Master | grep -o '[0-9]*%' | head -1 || echo 'Unknown'
    "
}

# Main test menu
main_menu() {
    while true; do
        echo
        echo "=== Bedrock 2.0 New Features Test Menu ==="
        echo "1. Deploy code updates"
        echo "2. Test GPIO sensors (light + volume)"
        echo "3. Test auto theme switching"
        echo "4. Interactive button test (30s)"
        echo "5. Interactive light sensor test (20s)"
        echo "6. Test full application (30s)"
        echo "7. Check system status"
        echo "8. Run all tests"
        echo "9. Exit"
        echo
        read -p "Select option (1-9): " choice
        
        case $choice in
            1)
                deploy_updates
                ;;
            2)
                test_gpio_sensors
                ;;
            3)
                test_auto_theme
                ;;
            4)
                test_buttons_interactive
                ;;
            5)
                test_light_sensor_interactive
                ;;
            6)
                test_full_app
                ;;
            7)
                check_system_status
                ;;
            8)
                log "Running all tests..."
                deploy_updates
                test_gpio_sensors
                test_auto_theme
                check_system_status
                warn "Interactive tests skipped in batch mode"
                ;;
            9)
                log "Exiting test menu"
                exit 0
                ;;
            *)
                warn "Invalid option. Please select 1-9."
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    if ! command -v sshpass &> /dev/null; then
        error "sshpass not found. Install with: sudo apt install sshpass"
        exit 1
    fi
    
    if ! command -v rsync &> /dev/null; then
        error "rsync not found. Install with: sudo apt install rsync"
        exit 1
    fi
    
    if [ ! -d "$LOCAL_PROJECT_PATH" ]; then
        error "Local project path not found: $LOCAL_PROJECT_PATH"
        exit 1
    fi
}

# Main execution
main() {
    log "Bedrock 2.0 New Features Testing Script"
    log "Target: $PI_USER@$PI_HOST"
    
    check_prerequisites
    test_connection
    
    if [ $# -eq 0 ]; then
        main_menu
    else
        case $1 in
            deploy)
                deploy_updates
                ;;
            sensors)
                test_gpio_sensors
                ;;
            theme)
                test_auto_theme
                ;;
            buttons)
                test_buttons_interactive
                ;;
            light)
                test_light_sensor_interactive
                ;;
            app)
                test_full_app
                ;;
            status)
                check_system_status
                ;;
            all)
                deploy_updates
                test_gpio_sensors
                test_auto_theme
                check_system_status
                ;;
            *)
                echo "Usage: $0 [deploy|sensors|theme|buttons|light|app|status|all]"
                echo "Or run without arguments for interactive menu"
                exit 1
                ;;
        esac
    fi
}

main "$@"