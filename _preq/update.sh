#!/bin/bash

# =============================================================================
# BEDROCK 2.0 - ИСПРАВЛЕННЫЙ QUICK UPDATE SCRIPT FOR PI 5
# Быстрое обновление изменившихся файлов из Windows 11 на Pi OS
# =============================================================================

set -e

# Color codes - стандартизированные
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration - ОБНОВИТЕ ПОД ВАШУ КОНФИГУРАЦИЮ
PI_HOST="192.168.1.234"    # ВАШ IP PI
PI_USER="standa"           # ВАШ ПОЛЬЗОВАТЕЛЬ
PI_PASS="crossover"        # ВАШ ПАРОЛЬ
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"  # ПУТЬ К ПРОЕКТУ
REMOTE_APP_PATH="/home/standa/bedrock-app"          # ПУТЬ НА PI

# Logging functions - единообразные
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    # Check if sshpass is installed
    if ! command -v sshpass &> /dev/null; then
        log_warning "sshpass not found. Installing..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y sshpass rsync
        elif command -v yum &> /dev/null; then
            sudo yum install -y sshpass rsync
        elif command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass rsync
        else
            log_error "Please install sshpass and rsync manually"
            exit 1
        fi
    fi
    
    # Check project directory
    if [[ ! -d "$LOCAL_PROJECT_PATH" ]] || [[ ! -f "$LOCAL_PROJECT_PATH/main.py" ]]; then
        log_error "Project not found at: $LOCAL_PROJECT_PATH"
        log_error "Please update LOCAL_PROJECT_PATH in the script"
        exit 1
    fi
    
    # Test SSH connection
    if ! sshpass -p "$PI_PASS" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "echo 'SSH OK'" >/dev/null 2>&1; then
        log_error "Cannot connect to Pi at $PI_USER@$PI_HOST"
        log_error "Please check IP address, username, and password"
        exit 1
    fi
    
    log_success "Prerequisites check passed ✓"
}

# Show what will be updated
show_update_info() {
    echo ""
    log_critical "🔄 BEDROCK QUICK UPDATE (ИСПРАВЛЕННАЯ ВЕРСИЯ)"
    echo ""
    echo "Source: $LOCAL_PROJECT_PATH"
    echo "Target: $PI_USER@$PI_HOST:$REMOTE_APP_PATH"
    echo ""
    log_info "Will sync only changed files (using checksums)"
    log_info "Will use .gitignore rules for exclusions"
    echo ""
}

# Stop existing app
stop_app() {
    log_info "Stopping Bedrock app on Pi..."
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
        "timeout 10 pkill -f 'python.*main.py' 2>/dev/null || true; \
         timeout 10 pkill -f 'bedrock.*py' 2>/dev/null || true; \
         timeout 10 pkill -f 'python.*bedrock' 2>/dev/null || true"
    sleep 2
    log_success "App stopped ✓"
}

# Parse .gitignore and create rsync exclude options
parse_gitignore() {
    local gitignore_file="$LOCAL_PROJECT_PATH/.gitignore"
    local exclude_args=""
    
    if [[ -f "$gitignore_file" ]]; then
        log_info "Using .gitignore rules for exclusions"
        
        # Read .gitignore and convert to rsync exclude format
        while IFS= read -r line; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            
            # Remove leading/trailing whitespace
            line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            # Skip empty lines after trimming
            [[ -z "$line" ]] && continue
            
            # Convert gitignore patterns to rsync exclude patterns
            if [[ "$line" == */ ]]; then
                # Directory pattern - add both with and without trailing slash
                exclude_args="$exclude_args --exclude=${line} --exclude=${line%/}"
            elif [[ "$line" == *"*"* ]]; then
                # Wildcard pattern
                exclude_args="$exclude_args --exclude=${line}"
            else
                # Regular file/directory pattern - exclude both file and directory versions
                exclude_args="$exclude_args --exclude=${line} --exclude=${line}/"
            fi
        done < "$gitignore_file"
        
        log_info "Loaded exclusion rules from .gitignore"
    else
        log_warning ".gitignore not found, using default exclusions"
        # Default exclusions if no .gitignore
        exclude_args="--exclude=__pycache__/ --exclude=*.pyc --exclude=*.pyo --exclude=.git/ --exclude=venv/ --exclude=logs/*.log --exclude=*.tmp --exclude=.DS_Store --exclude=Thumbs.db"
    fi
    
    echo "$exclude_args"
}

# Sync changed files using .gitignore rules - ИСПРАВЛЕННАЯ ФУНКЦИЯ
sync_files() {
    log_info "Syncing changed files..."
    
    # Get exclusions from .gitignore - ТЕПЕРЬ ИСПОЛЬЗУЕТСЯ!
    local exclude_rules
    exclude_rules=$(parse_gitignore)
    
    log_info "Starting file synchronization with checksum verification..."
    
    # Use rsync with checksum to only sync changed files
    # ВАЖНО: Используем eval для правильной обработки строки с пробелами
    if eval "sshpass -p '$PI_PASS' rsync \
        --archive \
        --verbose \
        --compress \
        --checksum \
        --human-readable \
        --progress \
        $exclude_rules \
        -e 'ssh -o StrictHostKeyChecking=no' \
        '$LOCAL_PROJECT_PATH/' '$PI_USER@$PI_HOST:$REMOTE_APP_PATH/'"; then
        log_success "Files synchronized ✓"
        return 0
    else
        log_error "File synchronization failed"
        return 1
    fi
}

# Check app status
check_app_status() {
    log_info "Checking app status..."
    
    # Wait a moment for potential autostart
    sleep 5
    
    # Check if app is running
    if sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
        "pgrep -f 'python.*main.py' >/dev/null 2>&1"; then
        local pid
        pid=$(sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "pgrep -f 'python.*main.py'")
        log_success "✅ App is running (PID: $pid)"
        return 0
    else
        log_warning "⚠️  App not running - may restart automatically via autostart"
        log_info "Wait 10-15 seconds for autostart, or use manual restart"
        return 1
    fi
}

# Manual restart option
manual_restart() {
    log_info "Starting app manually..."
    
    # Try using management script first
    if sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "[ -f /home/$PI_USER/manage_bedrock.sh ]"; then
        log_info "Using management script..."
        sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "/home/$PI_USER/manage_bedrock.sh restart"
    else
        log_info "Using direct launch..."
        sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
            "cd $REMOTE_APP_PATH && source venv/bin/activate && nohup python bedrock_fullscreen_pi5_final.py > logs/manual_start.log 2>&1 &"
    fi
    
    sleep 3
    
    if check_app_status >/dev/null 2>&1; then
        log_success "Manual start successful ✓"
    else
        log_warning "Manual start may have failed - check logs"
    fi
}

# Show final summary
show_summary() {
    echo ""
    log_success "🎉 UPDATE COMPLETED"
    echo ""
    echo "📊 Summary:"
    echo "  • Files synced to: $PI_USER@$PI_HOST:$REMOTE_APP_PATH"
    echo "  • Exclusions: Used .gitignore rules"
    echo "  • App status: $(sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "pgrep -f 'python.*main.py' >/dev/null && echo 'Running' || echo 'Not running')"
    echo ""
    echo "🔧 Useful commands:"
    echo "  • Check app:    ssh $PI_USER@$PI_HOST 'pgrep -f python.*main.py && echo Running || echo Stopped'"
    echo "  • Stop app:     ssh $PI_USER@$PI_HOST 'pkill -f python.*main.py'"
    echo "  • Management:   ssh $PI_USER@$PI_HOST './manage_bedrock.sh status'"
    echo "  • Force start:  ssh $PI_USER@$PI_HOST './manage_bedrock.sh force-full'"
    echo "  • View logs:    ssh $PI_USER@$PI_HOST './manage_bedrock.sh logs'"
    echo "  • Reboot Pi:    ssh $PI_USER@$PI_HOST 'sudo reboot'"
    echo ""
    
    # Show what was excluded
    local gitignore_file="$LOCAL_PROJECT_PATH/.gitignore"
    if [[ -f "$gitignore_file" ]]; then
        echo "📄 Excluded patterns (from .gitignore):"
        grep -v '^#' "$gitignore_file" | grep -v '^$' | head -10 | sed 's/^/  • /' || true
        local total_patterns
        total_patterns=$(grep -v '^#' "$gitignore_file" | grep -v '^$' | wc -l)
        if [[ $total_patterns -gt 10 ]]; then
            echo "  • ... and $((total_patterns - 10)) more patterns"
        fi
        echo ""
    fi
}

# Show logs from Pi
show_pi_logs() {
    log_info "📋 Recent logs from Pi:"
    echo ""
    
    # Try different log locations
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "
        echo '=== AUTOSTART LOG ==='
        tail -10 $REMOTE_APP_PATH/logs/autostart.log 2>/dev/null || echo 'No autostart log found'
        echo ''
        echo '=== MAIN APPLICATION LOG ==='
        tail -10 $REMOTE_APP_PATH/logs/bedrock.log 2>/dev/null || echo 'No main log found'
        echo ''
        echo '=== STARTUP ERROR LOG ==='
        tail -5 $REMOTE_APP_PATH/logs/startup_error.log 2>/dev/null || echo 'No startup errors (good!)'
    "
}

# Main function
main() {
    show_update_info
    
    # Set up error handling
    set -e
    trap 'log_error "Update failed at step: $BASH_COMMAND"' ERR
    
    check_prerequisites
    stop_app
    
    if sync_files; then
        log_success "Synchronization completed ✓"
    else
        log_error "Synchronization failed"
        exit 1
    fi
    
    check_app_status
    show_summary
}

# Handle command line options
case "${1:-}" in
    "--restart"|"-r")
        log_critical "Update with manual restart..."
        main
        manual_restart
        ;;
    "--logs"|"-l")
        show_pi_logs
        ;;
    "--status"|"-s")
        log_info "Checking app status on Pi..."
        check_prerequisites
        check_app_status
        ;;
    "--help"|"-h")
        echo "Bedrock 2.0 Quick Update Script (Исправленная версия)"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (no args)       - Quick update (sync + autostart)"
        echo "  -r, --restart   - Update + manual restart"
        echo "  -s, --status    - Check app status only"
        echo "  -l, --logs      - Show recent logs from Pi"
        echo "  -h, --help      - Show this help"
        echo ""
        echo "Configuration:"
        echo "  Pi Host: $PI_HOST"
        echo "  Pi User: $PI_USER"
        echo "  Local:   $LOCAL_PROJECT_PATH"
        echo "  Remote:  $REMOTE_APP_PATH"
        echo ""
        echo "Features:"
        echo "  ✓ Uses .gitignore for exclusions"
        echo "  ✓ Checksum-based sync (only changed files)"
        echo "  ✓ Comprehensive error handling"
        echo "  ✓ App status monitoring"
        echo ""
        ;;
    *)
        main
        ;;
esac