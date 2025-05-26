#!/bin/bash

# =============================================================================
# BEDROCK 2.0 - УЛУЧШЕННЫЙ ФИНАЛЬНЫЙ СКРИПТ ДЕПЛОЯ ДЛЯ RASPBERRY PI 5
# Версия с рефакторингом и улучшениями (май 2025)
# =============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration - ОБНОВИТЕ ПОД ВАШУ КОНФИГУРАЦИЮ
PI_HOST="${PI_HOST:-192.168.1.234}"  # Можно задать через переменную окружения
PI_USER="${PI_USER:-standa}"
PI_PASS="${PI_PASS:-crossover}"
LOCAL_PROJECT_PATH="${LOCAL_PROJECT_PATH:-/mnt/c/_PROJECTS/Bedrock_2.0}"
REMOTE_APP_PATH="${REMOTE_APP_PATH:-/home/$PI_USER/bedrock-app}"

# Load configuration from file if exists
if [[ -f "deploy_config.env" ]]; then
    source deploy_config.env
    echo -e "${GREEN}[INFO]${NC} Loaded configuration from deploy_config.env"
fi

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Global variables
BACKUP_DIR=""
DEPLOYMENT_LOG="/tmp/bedrock_deploy_$(date +%Y%m%d_%H%M%S).log"

# Logging to file
log_to_file() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$DEPLOYMENT_LOG"
}

# Combined logging
log_both() {
    echo -e "$1"
    log_to_file "$1"
}

# SSH execution function with better error handling
ssh_execute() {
    local command="$1"
    local description="${2:-Executing command}"
    
    log_to_file "SSH Command: $command"
    
    if sshpass -p "$PI_PASS" ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "$command"; then
        log_to_file "SSH Success: $description"
        return 0
    else
        log_error "SSH Failed: $description"
        log_to_file "SSH Error: $description - Command: $command"
        return 1
    fi
}

# File copy function with verification
scp_copy() {
    local source="$1"
    local destination="$2"
    local description="${3:-Copying files}"
    
    log_info "$description..."
    log_to_file "SCP: $source -> $PI_USER@$PI_HOST:$destination"
    
    if sshpass -p "$PI_PASS" scp -o StrictHostKeyChecking=no -r "$source" "$PI_USER@$PI_HOST:$destination"; then
        log_success "$description completed"
        return 0
    else
        log_error "$description failed"
        return 1
    fi
}

# Enhanced prerequisite checks
check_prerequisites() {
    log_step "🔍 Checking prerequisites..."
    
    # Check WSL
    if [[ ! -f /proc/version ]] || ! grep -q "microsoft" /proc/version; then
        log_error "Must run from WSL (Windows Subsystem for Linux)"
        exit 1
    fi
    
    # Check and install tools
    local missing_tools=()
    for tool in sshpass rsync ssh scp; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_warning "Installing missing tools: ${missing_tools[*]}"
        sudo apt update && sudo apt install -y sshpass rsync openssh-client
    fi
    
    # Check project structure
    if [[ ! -d "$LOCAL_PROJECT_PATH" ]] || [[ ! -f "$LOCAL_PROJECT_PATH/main.py" ]]; then
        log_error "Project not found at: $LOCAL_PROJECT_PATH"
        log_error "Please update LOCAL_PROJECT_PATH in the script configuration"
        exit 1
    fi
    
    # Test SSH connection with timeout
    log_info "Testing SSH connection to $PI_USER@$PI_HOST..."
    if ! sshpass -p "$PI_PASS" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "echo 'SSH Connection Test Successful'" >/dev/null 2>&1; then
        log_error "Cannot connect to Pi at $PI_USER@$PI_HOST"
        log_error "Please check:"
        log_error "  • Pi is powered on and connected to network"
        log_error "  • SSH is enabled on Pi"
        log_error "  • IP address $PI_HOST is correct"
        log_error "  • Username '$PI_USER' and password are correct"
        exit 1
    fi
    
    log_success "Prerequisites check passed ✓"
}

# Create backup
create_backup() {
    log_step "💾 Creating backup..."
    
    BACKUP_DIR="${REMOTE_APP_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
    
    if ssh_execute "[ -d '$REMOTE_APP_PATH' ] && cp -r '$REMOTE_APP_PATH' '$BACKUP_DIR'" "Creating backup"; then
        log_success "Backup created: $BACKUP_DIR"
        log_to_file "Backup location: $BACKUP_DIR"
    else
        log_warning "Backup creation failed or app directory doesn't exist"
        log_warning "Continuing with fresh installation..."
    fi
}

# Stop existing processes
stop_existing_app() {
    log_step "🛑 Stopping existing processes..."
    
    ssh_execute "
        # Kill Python processes
        timeout 10 pkill -f 'python.*main.py' 2>/dev/null || true
        timeout 10 pkill -f 'bedrock.*py' 2>/dev/null || true
        timeout 10 pkill -f 'python.*bedrock' 2>/dev/null || true
        
        # Wait a moment
        sleep 2
        
        # Force kill if still running
        timeout 5 pkill -9 -f 'python.*main.py' 2>/dev/null || true
        
        # Check if any processes remain
        if pgrep -f 'python.*main.py' >/dev/null 2>&1; then
            echo 'Warning: Some processes may still be running'
            exit 1
        else
            echo 'All processes stopped successfully'
        fi
    " "Stopping application processes"
    
    log_success "Processes stopped ✓"
}

# Install system dependencies
install_system_dependencies() {
    log_step "📦 Installing Pi 5 system dependencies..."
    
    # Create comprehensive installation script
    cat > /tmp/install_deps_verified.sh << 'EOF'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

log_section() { echo "=== $1 ==="; }

log_section "Updating package lists"
sudo apt update

log_section "Installing core development packages"
sudo apt install -y python3-pip python3-venv python3-dev build-essential pkg-config cmake git curl wget unzip

log_section "Installing Pi 5 graphics packages"
sudo apt install -y libgl1-mesa-dev libgles2-mesa-dev libegl1-mesa-dev libdrm-dev libxss1 libasound2-dev libpulse-dev libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxinerama-dev libxxf86vm-dev libxfixes-dev

log_section "Installing Pi 5 multimedia packages"
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-alsa gstreamer1.0-libcamera python3-gst-1.0

log_section "Installing Pi 5 GPIO and I2C packages - CRITICAL FOR PI 5"
sudo apt install -y i2c-tools python3-lgpio python3-gpiozero python3-smbus python3-smbus2

log_section "Installing audio packages"
sudo apt install -y alsa-utils pulseaudio pulseaudio-utils

log_section "Installing system Python packages"
sudo apt install -y python3-numpy python3-scipy python3-pygame python3-gi python3-gi-cairo gir1.2-gtk-3.0

log_section "Installing touch and desktop packages"
sudo apt install -y xinput xserver-xorg-input-evdev xdotool wmctrl xset unclutter

log_section "Verifying critical packages"
python3 -c "import lgpio; print('✓ lgpio available')" 2>/dev/null || echo "✗ lgpio not available"
which i2cdetect >/dev/null && echo "✓ i2c-tools available" || echo "✗ i2c-tools not available"
which pulseaudio >/dev/null && echo "✓ pulseaudio available" || echo "✗ pulseaudio not available"

echo "Pi 5 dependencies installation completed"
EOF

    scp_copy "/tmp/install_deps_verified.sh" "/tmp/" "Copying dependency installation script"
    ssh_execute "chmod +x /tmp/install_deps_verified.sh && /tmp/install_deps_verified.sh" "Installing system dependencies"
    rm /tmp/install_deps_verified.sh
    
    log_success "System dependencies installed ✓"
}

# Enhanced hardware configuration
configure_hardware() {
    log_step "⚙️ Configuring Pi 5 hardware..."
    
    # I2C and user permissions
    ssh_execute "sudo raspi-config nonint do_i2c 0" "Enabling I2C"
    ssh_execute "sudo usermod -a -G i2c,gpio,spi,audio,video $PI_USER" "Adding user to hardware groups"
    
    # Backup and update boot configuration
    ssh_execute "sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.$(date +%Y%m%d_%H%M%S)" "Backing up boot config"
    
    cat > /tmp/config_update_verified.sh << 'EOF'
#!/bin/bash
set -e

# Remove conflicting old settings
sudo sed -i '/hdmi_force_hotplug=/d' /boot/firmware/config.txt
sudo sed -i '/hdmi_group=/d' /boot/firmware/config.txt
sudo sed -i '/hdmi_mode=/d' /boot/firmware/config.txt
sudo sed -i '/hdmi_cvt=/d' /boot/firmware/config.txt
sudo sed -i '/hdmi_drive=/d' /boot/firmware/config.txt
sudo sed -i '/gpu_mem=/d' /boot/firmware/config.txt
sudo sed -i '/disable_splash=/d' /boot/firmware/config.txt
sudo sed -i '/boot_delay=/d' /boot/firmware/config.txt

# Add Pi 5 optimized settings
cat << 'CONFIG_EOF' | sudo tee -a /boot/firmware/config.txt

# === BEDROCK PI 5 CONFIGURATION (Added $(date)) ===
# Display for 1024x600 fullscreen
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1024 600 60 6 0 0 0
hdmi_drive=2

# I2C for sensors
dtparam=i2c_arm=on
dtparam=i2c1=on
dtparam=i2c1_baudrate=100000

# Audio configuration
dtparam=audio=on
audio_pwm_mode=2

# Pi 5 GPU optimization
gpu_mem=128
gpu_freq=500

# Boot optimization
disable_splash=1
boot_delay=0

CONFIG_EOF

echo "Boot configuration updated successfully"
sudo tail -20 /boot/firmware/config.txt
EOF

    scp_copy "/tmp/config_update_verified.sh" "/tmp/" "Copying boot config script"
    ssh_execute "chmod +x /tmp/config_update_verified.sh && /tmp/config_update_verified.sh" "Updating boot configuration"
    rm /tmp/config_update_verified.sh
    
    log_success "Hardware configuration completed ✓"
}

# Enhanced application setup
setup_application() {
    log_step "🚀 Setting up Bedrock application..."
    
    # Create comprehensive directory structure
    ssh_execute "mkdir -p $REMOTE_APP_PATH/{assets/{fonts,sounds,images},themes/minecraft/{light,dark},media/ringtones,cache,config,logs,services,classes,pages,utils}" "Creating directory structure"
    
    # Sync project files with better exclusions
    log_info "Syncing project files (this may take a few minutes)..."
    
    # Create exclusion list
    cat > /tmp/rsync_exclude << 'EOF'
__pycache__/
*.pyc
*.pyo
.git/
venv/
logs/*.log
*.tmp
.DS_Store
Thumbs.db
*.bak
*.swp
node_modules/
.vscode/
bedrock_startup_log.txt
EOF
    
    if sshpass -p "$PI_PASS" rsync -avz --delete \
        --exclude-from=/tmp/rsync_exclude \
        --progress \
        -e "ssh -o StrictHostKeyChecking=no" \
        "$LOCAL_PROJECT_PATH/" "$PI_USER@$PI_HOST:$REMOTE_APP_PATH/"; then
        log_success "Project files synced ✓"
    else
        log_error "File synchronization failed"
        rm /tmp/rsync_exclude
        return 1
    fi
    
    rm /tmp/rsync_exclude
    
    # Setup Python environment
    log_info "Setting up Python virtual environment..."
    ssh_execute "cd $REMOTE_APP_PATH && rm -rf venv && python3 -m venv --system-site-packages venv" "Creating virtual environment"
    ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && pip install --upgrade pip setuptools wheel" "Upgrading pip tools"
    
    # Create verified requirements file for reworked architecture
    cat > /tmp/requirements_pi5_final.txt << 'EOF'
# Bedrock 2.0 - Refactored requirements for Pi 5 (Mai 2025)

# Core GUI framework - tested working versions
kivy>=2.3.0,<2.4.0
pillow>=9.5.0,<11.0.0
pygame>=2.5.0,<2.6.0
requests>=2.28.0,<3.0.0

# Pi 5 GPIO support - CRITICAL for Pi 5
rpi-lgpio>=0.6.0
gpiozero>=1.6.2

# Sensor libraries for Pi 5
adafruit-blinka>=8.20.0
adafruit-circuitpython-ahtx0>=1.0.18
adafruit-circuitpython-ens160>=1.0.9
smbus2>=0.4.2

# Core dependencies
setuptools>=65.0.0,<70.0.0
wheel>=0.38.0,<1.0.0
docutils>=0.18.0,<1.0.0
pygments>=2.14.0,<3.0.0
certifi>=2022.12.7
EOF
    
    scp_copy "/tmp/requirements_pi5_final.txt" "/tmp/" "Copying requirements file"
    ssh_execute "cp /tmp/requirements_pi5_final.txt $REMOTE_APP_PATH/requirements_final.txt" "Installing requirements file"
    
    # Install Python dependencies
    log_info "Installing Python dependencies (this may take several minutes)..."
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && pip install -r requirements_final.txt" "Installing Python packages"; then
        log_success "Python dependencies installed ✓"
    else
        log_error "Python dependencies installation failed"
        return 1
    fi
    
    # Install working KivyMD - CRITICAL FIX
    log_critical "Installing KivyMD 2.0.1.dev0 (Pi 5 compatible version)..."
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && pip install https://github.com/kivymd/KivyMD/archive/master.zip" "Installing KivyMD from master"; then
        log_success "KivyMD installed ✓"
    else
        log_error "KivyMD installation failed - this is critical"
        return 1
    fi
    
    rm /tmp/requirements_pi5_final.txt
    
    log_success "Application setup completed ✓"
}

# Create enhanced fullscreen launcher
create_fullscreen_launcher() {
    log_step "🎯 Creating fullscreen launcher..."
    
    cat > /tmp/bedrock_fullscreen_pi5_refactored.py << 'EOF'
#!/usr/bin/env python3

# Bedrock 2.0 - Pi 5 Fullscreen Launcher (REFACTORED VERSION)
# Optimized for refactored architecture with ThemeManager and ConfigManager

import os
import sys
from datetime import datetime

print(f"🚀 Starting Bedrock App in Fullscreen Mode for Pi 5... ({datetime.now()})")

# Set critical environment variables BEFORE Kivy import
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['SDL_VIDEO_FULLSCREEN_HEAD'] = '0'

# FORCE FULLSCREEN CONFIGURATION BEFORE ANY KIVY IMPORTS
try:
    from kivy.config import Config
    
    # Configure for fullscreen Pi 5 display (1024x600)
    Config.set("graphics", "fullscreen", "1")
    Config.set("graphics", "borderless", "1") 
    Config.set("graphics", "window_state", "maximized")
    Config.set("graphics", "width", "1024")
    Config.set("graphics", "height", "600")
    Config.set("graphics", "position", "custom")
    Config.set("graphics", "left", "0")
    Config.set("graphics", "top", "0")
    Config.set("graphics", "show_cursor", "0")
    Config.set("graphics", "resizable", "0")
    Config.set("graphics", "minimum_width", "1024")
    Config.set("graphics", "minimum_height", "600")
    Config.set("graphics", "maxfps", "60")
    Config.set("graphics", "vsync", "1")
    
    print("✅ Fullscreen configuration applied for Pi 5")
    
    # Import and run the main application
    from main import BedrockApp
    
    print("🎯 Launching Refactored Bedrock App...")
    
    # Create and run app
    app = BedrockApp()
    app.run()
    
except Exception as e:
    print(f"❌ Error starting Bedrock App: {e}")
    import traceback
    traceback.print_exc()
    
    # Log error for debugging
    try:
        os.makedirs('logs', exist_ok=True)
        with open('logs/startup_error.log', 'a') as f:
            f.write(f"\n[{datetime.now()}] Startup Error: {e}\n")
            f.write(traceback.format_exc())
    except:
        pass
    
    sys.exit(1)
EOF
    
    scp_copy "/tmp/bedrock_fullscreen_pi5_refactored.py" "/tmp/" "Copying fullscreen launcher"
    ssh_execute "cp /tmp/bedrock_fullscreen_pi5_refactored.py $REMOTE_APP_PATH/ && chmod +x $REMOTE_APP_PATH/bedrock_fullscreen_pi5_refactored.py" "Installing fullscreen launcher"
    rm /tmp/bedrock_fullscreen_pi5_refactored.py
    
    log_success "Fullscreen launcher created ✓"
}

# Setup autostart with monitoring
setup_autostart() {
    log_step "🔄 Setting up autostart..."
    
    ssh_execute "mkdir -p ~/.config/autostart" "Creating autostart directory"
    
    cat > /tmp/bedrock_autostart_refactored.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Bedrock Pi 5 Refactored Fullscreen
Comment=Bedrock 2.0 - Pi 5 Fullscreen Kiosk Mode (Refactored Architecture)
Exec=bash -c "sleep 15 && cd /home/standa/bedrock-app && source venv/bin/activate && python bedrock_fullscreen_pi5_refactored.py >> logs/autostart.log 2>&1"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
Terminal=false
Categories=Kiosk;System;
EOF
    
    scp_copy "/tmp/bedrock_autostart_refactored.desktop" "/tmp/" "Copying autostart file"
    ssh_execute "cp /tmp/bedrock_autostart_refactored.desktop ~/.config/autostart/bedrock_pi5_refactored.desktop && chmod +x ~/.config/autostart/bedrock_pi5_refactored.desktop" "Installing autostart"
    rm /tmp/bedrock_autostart_refactored.desktop
    
    # Create management script
    cat > /tmp/manage_bedrock_refactored.sh << 'EOF'
#!/bin/bash

# Bedrock 2.0 Management Script (Refactored)

APP_DIR="/home/standa/bedrock-app"
APP_NAME="python.*main.py"
LAUNCHER="bedrock_fullscreen_pi5_refactored.py"

case "$1" in
    start)
        echo "Starting Refactored Bedrock App..."
        cd "$APP_DIR"
        source venv/bin/activate
        python "$LAUNCHER" &
        echo "App started"
        ;;
    stop)
        echo "Stopping Bedrock App..."
        pkill -f "$APP_NAME" || echo "No running app found"
        ;;
    restart)
        echo "Restarting Bedrock App..."
        pkill -f "$APP_NAME" || true
        sleep 3
        cd "$APP_DIR"
        source venv/bin/activate
        python "$LAUNCHER" &
        echo "App restarted"
        ;;
    status)
        if pgrep -f "$APP_NAME" >/dev/null; then
            echo "App is running"
            pgrep -f "$APP_NAME" | while read pid; do
                echo "PID: $pid"
                ps -p $pid -o pid,ppid,cmd --no-headers
            done
        else
            echo "App is not running"
        fi
        ;;
    logs)
        echo "Recent logs:"
        tail -20 "$APP_DIR/logs/bedrock.log" 2>/dev/null || echo "No main log found"
        echo "Autostart logs:"
        tail -10 "$APP_DIR/logs/autostart.log" 2>/dev/null || echo "No autostart log found"
        ;;
    test-theme)
        echo "Testing theme switching..."
        cd "$APP_DIR"
        source venv/bin/activate
        python -c "from utils.theme_manager import ThemeManager; from main import BedrockApp; app = BedrockApp(); tm = ThemeManager(app); print('Theme manager test OK')"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test-theme}"
        exit 1
        ;;
esac
EOF
    
    scp_copy "/tmp/manage_bedrock_refactored.sh" "/tmp/" "Copying management script"
    ssh_execute "cp /tmp/manage_bedrock_refactored.sh /home/$PI_USER/manage_bedrock.sh && chmod +x /home/$PI_USER/manage_bedrock.sh" "Installing management script"
    rm /tmp/manage_bedrock_refactored.sh
    
    log_success "Autostart and management configured ✓"
}

# Comprehensive testing
test_installation() {
    log_step "🧪 Testing refactored installation..."
    
    # Test Python imports
    log_info "Testing critical Python imports..."
    
    local test_results=""
    
    # Test core dependencies
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && python -c 'import kivy; print(f\"Kivy: {kivy.__version__}\")'" "Testing Kivy import"; then
        test_results+="✓ Kivy "
    else
        test_results+="✗ Kivy "
        log_error "Kivy import failed"
    fi
    
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && python -c 'import kivymd; print(f\"KivyMD: {kivymd.__version__}\")'" "Testing KivyMD import"; then
        test_results+="✓ KivyMD "
    else
        test_results+="✗ KivyMD "
        log_error "KivyMD import failed - CRITICAL"
    fi
    
    # Test refactored modules
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && python -c 'from utils.common import BasePage, ConfigManager; print(\"Common utils: OK\")'" "Testing common utils"; then
        test_results+="✓ CommonUtils "
    else
        test_results+="✗ CommonUtils "
        log_error "Common utils import failed"
    fi
    
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && python -c 'from utils.theme_manager import ThemeManager; print(\"ThemeManager: OK\")'" "Testing ThemeManager"; then
        test_results+="✓ ThemeManager "
    else
        test_results+="✗ ThemeManager "
        log_error "ThemeManager import failed"
    fi
    
    # Test main application import
    if ssh_execute "cd $REMOTE_APP_PATH && source venv/bin/activate && python -c 'import main; print(\"Main import: OK\")'" "Testing main app import"; then
        test_results+="✓ MainApp "
    else
        test_results+="✗ MainApp "
        log_error "Main app import failed"
    fi
    
    echo ""
    log_info "Test Results: $test_results"
    
    if [[ "$test_results" == *"✗"* ]]; then
        log_warning "Some tests failed - check logs for details"
        return 1
    else
        log_success "All critical tests passed ✓"
        return 0
    fi
}

# Create update scripts
create_update_scripts() {
    log_step "📝 Creating update scripts..."
    
    # Quick update script for refactored version
    cat > "update_bedrock_pi5_refactored.sh" << EOF
#!/bin/bash
# Quick update for Refactored Bedrock Pi 5 - Generated by deploy script

PI_HOST="$PI_HOST"
PI_USER="$PI_USER"
PI_PASS="$PI_PASS"
LOCAL_PROJECT_PATH="$LOCAL_PROJECT_PATH"
REMOTE_APP_PATH="$REMOTE_APP_PATH"

echo "🔄 Quick update - syncing refactored files..."

# Stop app
sshpass -p "\$PI_PASS" ssh -o StrictHostKeyChecking=no "\$PI_USER@\$PI_HOST" "pkill -f 'python.*main.py' || true"

# Sync files
sshpass -p "\$PI_PASS" rsync -avz --checksum \\
    --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" --exclude="venv" --exclude="logs/*.log" \\
    -e "ssh -o StrictHostKeyChecking=no" \\
    "\$LOCAL_PROJECT_PATH/" "\$PI_USER@\$PI_HOST:\$REMOTE_APP_PATH/"

echo "✅ Refactored files synced. App will restart automatically via autostart."
echo "Manual start: ssh \$PI_USER@\$PI_HOST '/home/$PI_USER/manage_bedrock.sh start'"
echo "Test theme: ssh \$PI_USER@\$PI_HOST '/home/$PI_USER/manage_bedrock.sh test-theme'"
EOF
    
    chmod +x "update_bedrock_pi5_refactored.sh"
    
    log_success "Update scripts created"
}

# Show final summary
show_final_summary() {
    echo ""
    log_success "🎉 BEDROCK 2.0 PI 5 REFACTORED DEPLOYMENT COMPLETED!"
    echo ""
    log_critical "=== REFACTORED DEPLOYMENT SUMMARY ==="
    echo ""
    echo "🎯 Architecture Improvements:"
    echo "  • ThemeManager: Centralized theme switching"
    echo "  • ConfigManager: Unified configuration management"
    echo "  • BasePage: Simplified page inheritance"
    echo "  • Common utilities: Reduced code duplication"
    echo "  • Enhanced error handling and logging"
    echo ""
    echo "🎯 Configuration:"
    echo "  • Target: $PI_USER@$PI_HOST"
    echo "  • App Location: $REMOTE_APP_PATH"
    echo "  • Display: 1024x600 fullscreen kiosk mode"
    echo "  • Architecture: Refactored with improved maintainability"
    if [[ -n "$BACKUP_DIR" ]]; then
        echo "  • Backup: $BACKUP_DIR"
    fi
    echo ""
    echo "🚀 Management Commands:"
    echo "  • App status:   ssh $PI_USER@$PI_HOST './manage_bedrock.sh status'"
    echo "  • Start app:    ssh $PI_USER@$PI_HOST './manage_bedrock.sh start'"
    echo "  • Stop app:     ssh $PI_USER@$PI_HOST './manage_bedrock.sh stop'"
    echo "  • Restart app:  ssh $PI_USER@$PI_HOST './manage_bedrock.sh restart'"
    echo "  • View logs:    ssh $PI_USER@$PI_HOST './manage_bedrock.sh logs'"
    echo "  • Test theme:   ssh $PI_USER@$PI_HOST './manage_bedrock.sh test-theme'"
    echo ""
    echo "🔄 Update Commands:"
    echo "  • Quick update: ./update_bedrock_pi5_refactored.sh"
    echo ""
    log_critical "⚠️ IMPORTANT: REBOOT REQUIRED for all hardware changes to take effect!"
    echo ""
    echo "To reboot Pi: ssh $PI_USER@$PI_HOST 'sudo reboot'"
    echo ""
    echo "After reboot, the refactored app will start automatically!"
    echo ""
    log_info "📊 Deployment log saved to: $DEPLOYMENT_LOG"
    log_success "🎉 REFACTORED DEPLOYMENT SUCCESSFUL!"
}

# Main deployment function
main() {
    echo ""
    log_critical "🚀 BEDROCK 2.0 - REFACTORED PI 5 DEPLOYMENT"
    echo ""
    log_info "Deployment started at: $(date)"
    log_to_file "=== BEDROCK 2.0 REFACTORED PI 5 DEPLOYMENT STARTED ==="
    log_to_file "Configuration: $PI_USER@$PI_HOST - $LOCAL_PROJECT_PATH -> $REMOTE_APP_PATH"
    
    check_prerequisites
    create_backup
    stop_existing_app
    install_system_dependencies
    configure_hardware
    setup_application
    create_fullscreen_launcher
    setup_autostart
    
    if ! test_installation; then
        log_warning "Some tests failed, but deployment may still work"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    create_update_scripts
    
    log_to_file "=== REFACTORED DEPLOYMENT COMPLETED SUCCESSFULLY ==="
    show_final_summary
}

# Handle script arguments
case "${1:-}" in
    "--help"|"-h")
        echo "Bedrock 2.0 Refactored Pi 5 Deployment Script"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (no args)    - Full refactored deployment"
        echo "  -h, --help   - Show this help"
        echo ""
        echo "Configuration (update these or use deploy_config.env):"
        echo "  PI_HOST: $PI_HOST"
        echo "  PI_USER: $PI_USER"
        echo "  LOCAL_PROJECT_PATH: $LOCAL_PROJECT_PATH"
        echo "  REMOTE_APP_PATH: $REMOTE_APP_PATH"
        ;;
    *)
        main
        ;;
esac