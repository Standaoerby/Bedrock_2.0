#!/bin/bash

# =============================================================================
# BEDROCK 2.0 - ROBUST UPDATE SCRIPT FOR PI 5
# Улучшенная версия с обработкой rsync ошибок
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
PI_HOST="192.168.1.243"    # ВАШ IP PI
PI_USER="standa"           # ВАШ ПОЛЬЗОВАТЕЛЬ
PI_PASS="crossover"        # ВАШ ПАРОЛЬ
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"  # ПУТЬ К ПРОЕКТУ
REMOTE_APP_PATH="/home/standa/bedrock-app"          # ПУТЬ НА PI

# Script configuration
LAUNCHER_NAME="bedrock_launcher.py"
MANAGE_SCRIPT="/home/$PI_USER/manage_bedrock.sh"
MAX_RETRY_ATTEMPTS=3
SYNC_TIMEOUT=600  # 10 minutes

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }
log_debug() { echo -e "${CYAN}[DEBUG]${NC} $1"; }

# Enhanced SSH execution with retry
ssh_execute_with_retry() {
    local command="$1"
    local description="${2:-Executing command}"
    local max_attempts="${3:-2}"
    local timeout_seconds="${4:-30}"
    
    for attempt in $(seq 1 $max_attempts); do
        log_debug "SSH attempt $attempt/$max_attempts: $description"
        
        if timeout "$timeout_seconds" sshpass -p "$PI_PASS" ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "$command"; then
            return 0
        else
            local exit_code=$?
            if [ $attempt -eq $max_attempts ]; then
                log_error "SSH failed after $max_attempts attempts: $description (exit code: $exit_code)"
                return $exit_code
            else
                log_warning "SSH attempt $attempt failed, retrying..."
                sleep 2
            fi
        fi
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if sshpass is installed
    if ! command -v sshpass &> /dev/null; then
        log_warning "sshpass not found. Installing..."
        sudo apt update && sudo apt install -y sshpass rsync
    fi
    
    # Check project directory
    if [[ ! -d "$LOCAL_PROJECT_PATH" ]] || [[ ! -f "$LOCAL_PROJECT_PATH/main.py" ]]; then
        log_error "Project not found at: $LOCAL_PROJECT_PATH"
        exit 1
    fi
    
    # Test SSH connection
    log_info "Testing SSH connection to $PI_USER@$PI_HOST..."
    if ! ssh_execute_with_retry "echo 'SSH test successful'" "Testing SSH connection" 2 10; then
        log_error "Cannot connect to Pi at $PI_USER@$PI_HOST"
        log_error "Please check network connection and credentials"
        exit 1
    fi
    
    log_success "Prerequisites check passed ✓"
}

# Show update info
show_update_info() {
    echo ""
    log_critical "🔄 BEDROCK ROBUST UPDATE v2.2"
    echo ""
    echo "Source: $LOCAL_PROJECT_PATH"
    echo "Target: $PI_USER@$PI_HOST:$REMOTE_APP_PATH"
    echo "Launcher: $LAUNCHER_NAME"
    echo "Max retries: $MAX_RETRY_ATTEMPTS"
    echo "Sync timeout: ${SYNC_TIMEOUT}s"
    echo ""
}

# Enhanced app stopping with verification
stop_app_robust() {
    log_info "Stopping Bedrock app (robust method)..."
    
    # Step 1: Check if app is running
    if ! ssh_execute_with_retry "pgrep -f 'python.*main.py' >/dev/null 2>&1" "Checking if app is running" 1 10; then
        log_info "No running app found - proceeding with sync"
        return 0
    fi
    
    log_info "Found running app, stopping it..."
    
    # Step 2: Try graceful shutdown
    ssh_execute_with_retry "
        echo 'Step 1: Graceful shutdown...'
        pkill -TERM -f 'python.*main.py' 2>/dev/null || true
        pkill -TERM -f 'bedrock.*py' 2>/dev/null || true
        sleep 3
        
        if pgrep -f 'python.*main.py' >/dev/null 2>&1; then
            echo 'Step 2: Force kill...'
            pkill -KILL -f 'python.*main.py' 2>/dev/null || true
            pkill -KILL -f 'bedrock.*py' 2>/dev/null || true
            sleep 2
        fi
        
        echo 'Step 3: Verification...'
        if pgrep -f 'python.*main.py' >/dev/null 2>&1; then
            echo 'WARNING: Some processes may still be running'
            ps aux | grep -E '(python.*main|bedrock)' | grep -v grep | head -3
            exit 1
        else
            echo 'All processes stopped successfully'
            exit 0
        fi
    " "Stopping app processes" 1 30
    
    # Step 3: Additional cleanup if needed
    log_info "Performing additional cleanup..."
    ssh_execute_with_retry "
        # Clean up any temporary files that might be locked
        find $REMOTE_APP_PATH -name '*.tmp' -delete 2>/dev/null || true
        find $REMOTE_APP_PATH -name '.#*' -delete 2>/dev/null || true
        
        # Ensure log directory is writable
        mkdir -p $REMOTE_APP_PATH/logs
        chmod 755 $REMOTE_APP_PATH/logs
        
        echo 'Cleanup completed'
    " "System cleanup" 1 15
    
    log_success "App stopped and cleanup completed ✓"
}

# Parse .gitignore (same as before)
parse_gitignore() {
    local gitignore_file="$LOCAL_PROJECT_PATH/.gitignore"
    local exclude_args=""
    
    if [[ -f "$gitignore_file" ]]; then
        while IFS= read -r line; do
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [[ -z "$line" ]] && continue
            
            if [[ "$line" == */ ]]; then
                exclude_args="$exclude_args --exclude=${line} --exclude=${line%/}"
            elif [[ "$line" == *"*"* ]]; then
                exclude_args="$exclude_args --exclude=${line}"
            else
                exclude_args="$exclude_args --exclude=${line} --exclude=${line}/"
            fi
        done < "$gitignore_file"
    else
        exclude_args="--exclude=__pycache__/ --exclude=*.pyc --exclude=*.pyo --exclude=.git/ --exclude=venv/ --exclude=logs/*.log --exclude=*.tmp --exclude=.DS_Store --exclude=Thumbs.db"
    fi
    
    echo "$exclude_args"
}

# Enhanced sync with retry and better error handling
sync_files_robust() {
    log_info "Starting robust file synchronization..."
    
    local exclude_rules
    exclude_rules=$(parse_gitignore)
    
    local attempt=1
    local sync_success=false
    
    while [ $attempt -le $MAX_RETRY_ATTEMPTS ] && [ "$sync_success" = false ]; do
        log_info "Sync attempt $attempt/$MAX_RETRY_ATTEMPTS..."
        
        # Prepare rsync command
        local rsync_cmd=(
            timeout "$SYNC_TIMEOUT" sshpass -p "$PI_PASS" rsync
            --archive
            --verbose
            --compress
            --checksum
            --human-readable
            --progress
            --partial
            --partial-dir=.rsync-partial
            --timeout=60
        )
        
        # Add exclude rules
        if [[ -n "$exclude_rules" ]]; then
            while IFS= read -r exclude_rule; do
                if [[ -n "$exclude_rule" ]]; then
                    rsync_cmd+=("$exclude_rule")
                fi
            done <<< "$(echo "$exclude_rules" | tr ' ' '\n')"
        fi
        
        # Add final arguments
        rsync_cmd+=(
            -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30"
            "$LOCAL_PROJECT_PATH/"
            "$PI_USER@$PI_HOST:$REMOTE_APP_PATH/"
        )
        
        # Execute rsync and capture exit code
        set +e  # Temporarily disable error exit
        "${rsync_cmd[@]}"
        local rsync_exit_code=$?
        set -e  # Re-enable error exit
        
        # Analyze rsync exit code
        case $rsync_exit_code in
            0)
                log_success "Files synchronized successfully ✓"
                sync_success=true
                ;;
            23)
                log_warning "rsync partial success (code 23) - some files couldn't be transferred"
                log_info "This is often due to locked files or permission issues"
                
                # Check if enough files were transferred
                log_info "Verifying critical files on Pi..."
                if ssh_execute_with_retry "
                    cd $REMOTE_APP_PATH && 
                    [ -f main.py ] && [ -f $LAUNCHER_NAME ] && [ -f requirements.txt ] && 
                    echo 'Critical files verified'
                " "Verifying critical files" 1 15; then
                    log_success "Critical files are present - considering sync successful ✓"
                    sync_success=true
                else
                    log_warning "Some critical files missing - will retry"
                fi
                ;;
            24)
                log_warning "rsync warning (code 24) - some files vanished during transfer"
                log_success "This is usually not critical - considering successful ✓"
                sync_success=true
                ;;
            30)
                log_error "rsync timeout (code 30)"
                if [ $attempt -eq $MAX_RETRY_ATTEMPTS ]; then
                    log_error "Sync failed after $MAX_RETRY_ATTEMPTS attempts due to timeout"
                    return 1
                fi
                ;;
            *)
                log_error "rsync failed with exit code $rsync_exit_code"
                if [ $attempt -eq $MAX_RETRY_ATTEMPTS ]; then
                    log_error "Sync failed after $MAX_RETRY_ATTEMPTS attempts"
                    return 1
                fi
                ;;
        esac
        
        if [ "$sync_success" = false ]; then
            log_warning "Waiting before retry..."
            sleep 3
        fi
        
        ((attempt++))
    done
    
    if [ "$sync_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Check app status
check_app_status() {
    log_info "Checking app status..."
    
    # Wait for potential autostart
    sleep 5
    
    if ssh_execute_with_retry "pgrep -f 'python.*main.py' >/dev/null 2>&1" "Checking app status" 1 10; then
        local pid_info
        pid_info=$(ssh_execute_with_retry "pgrep -f 'python.*main.py' | head -1" "Getting PID" 1 10)
        log_success "✅ App is running (PID: $pid_info)"
        return 0
    else
        log_warning "⚠️  App not running - may restart automatically"
        return 1
    fi
}

# Manual restart with enhanced error handling
manual_restart() {
    log_info "Performing manual restart..."
    
    # First, ensure app is stopped
    stop_app_robust
    
    # Try management script first
    if ssh_execute_with_retry "[ -f $MANAGE_SCRIPT ]" "Checking management script" 1 10; then
        log_info "Using management script for restart..."
        if ssh_execute_with_retry "$MANAGE_SCRIPT restart" "Management script restart" 1 45; then
            log_success "Management script restart completed"
        else
            log_warning "Management script failed, trying direct launch..."
            direct_launch
        fi
    else
        log_info "Management script not found, using direct launch..."
        direct_launch
    fi
    
    # Verify restart
    sleep 5
    if check_app_status >/dev/null 2>&1; then
        log_success "Manual restart successful ✓"
    else
        log_error "Manual restart failed - check logs with: $0 --logs"
        return 1
    fi
}

# Direct launch function
direct_launch() {
    log_info "Launching app directly..."
    ssh_execute_with_retry "
        cd $REMOTE_APP_PATH &&
        source venv/bin/activate &&
        export DISPLAY=:0 &&
        nohup python $LAUNCHER_NAME > logs/manual_start.log 2>&1 &
        echo 'Direct launch initiated'
    " "Direct app launch" 1 30
}

# Show comprehensive logs
show_comprehensive_logs() {
    log_info "📋 Comprehensive logs from Pi:"
    echo ""
    
    ssh_execute_with_retry "
        echo '=== SYSTEM STATUS ==='
        uptime
        echo ''
        echo 'Disk space:'
        df -h $REMOTE_APP_PATH | tail -1
        echo ''
        
        echo '=== PROCESS STATUS ==='
        if pgrep -f 'python.*main.py' >/dev/null 2>&1; then
            echo 'Running processes:'
            ps aux | grep -E '(python.*main|bedrock)' | grep -v grep
        else
            echo 'No Bedrock processes running'
        fi
        echo ''
        
        echo '=== RECENT LOGS ==='
        echo '--- Autostart Log ---'
        tail -10 $REMOTE_APP_PATH/logs/autostart.log 2>/dev/null || echo 'No autostart log'
        echo ''
        echo '--- Launcher Log ---'
        tail -10 $REMOTE_APP_PATH/logs/launcher.log 2>/dev/null || echo 'No launcher log'
        echo ''
        echo '--- App Log ---'
        tail -10 $REMOTE_APP_PATH/logs/app.log 2>/dev/null || echo 'No app log'
        echo ''
        echo '--- Error Log ---'
        tail -5 $REMOTE_APP_PATH/logs/startup_error.log 2>/dev/null || echo 'No error log'
        echo ''
        echo '--- Manual Start Log ---'
        tail -5 $REMOTE_APP_PATH/logs/manual_start.log 2>/dev/null || echo 'No manual start log'
    " "Getting comprehensive logs" 1 45
}

# Main function
main() {
    show_update_info
    
    check_prerequisites
    stop_app_robust
    
    if sync_files_robust; then
        log_success "Synchronization completed successfully ✓"
    else
        log_error "Synchronization failed after $MAX_RETRY_ATTEMPTS attempts"
        log_info "Try running with --restart flag for manual restart"
        exit 1
    fi
    
    check_app_status
    
    echo ""
    log_success "🎉 ROBUST UPDATE COMPLETED"
    echo ""
    echo "Use '$0 --logs' to see detailed logs"
    echo "Use '$0 --restart' if app didn't start automatically"
}

# Command line handling
case "${1:-}" in
    "--restart"|"-r")
        log_critical "Update with manual restart..."
        show_update_info
        check_prerequisites
        stop_app_robust
        if sync_files_robust; then
            manual_restart
        else
            log_error "Sync failed, cannot restart"
            exit 1
        fi
        ;;
    "--logs"|"-l")
        check_prerequisites
        show_comprehensive_logs
        ;;
    "--status"|"-s")
        check_prerequisites
        check_app_status
        ;;
    "--help"|"-h")
        echo "Bedrock 2.0 Robust Update Script v2.2"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (no args)       - Robust update with retry logic"
        echo "  -r, --restart   - Update + guaranteed manual restart"
        echo "  -s, --status    - Check app status only"
        echo "  -l, --logs      - Show comprehensive logs"
        echo "  -h, --help      - Show this help"
        echo ""
        echo "Configuration:"
        echo "  Pi Host: $PI_HOST"
        echo "  Pi User: $PI_USER"
        echo "  Max Retries: $MAX_RETRY_ATTEMPTS"
        echo "  Sync Timeout: ${SYNC_TIMEOUT}s"
        echo ""
        echo "Features:"
        echo "  ✓ Handles rsync error codes 23, 24, 30"
        echo "  ✓ Retry logic for failed operations"
        echo "  ✓ Partial transfer recovery"
        echo "  ✓ Enhanced error diagnostics"
        echo "  ✓ Robust process management"
        echo ""
        ;;
    *)
        main
        ;;
esac