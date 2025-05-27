#!/bin/bash

# =============================================================================
# BEDROCK 2.0 - FIXED UPDATE SCRIPT FOR PI 5
# Упрощённая версия без сложных SSH команд
# =============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
PI_HOST="192.168.1.243"
PI_USER="standa"
PI_PASS="crossover"
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"
REMOTE_APP_PATH="/home/standa/bedrock-app"
LAUNCHER_NAME="bedrock_launcher.py"
MANAGE_SCRIPT="/home/$PI_USER/manage_bedrock.sh"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }

# Simple SSH execution
ssh_simple() {
    local command="$1"
    local timeout_seconds="${2:-20}"
    
    timeout "$timeout_seconds" sshpass -p "$PI_PASS" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "$command"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v sshpass &> /dev/null; then
        log_warning "Installing sshpass..."
        sudo apt update && sudo apt install -y sshpass rsync
    fi
    
    if [[ ! -d "$LOCAL_PROJECT_PATH" ]] || [[ ! -f "$LOCAL_PROJECT_PATH/main.py" ]]; then
        log_error "Project not found at: $LOCAL_PROJECT_PATH"
        exit 1
    fi
    
    if ! ssh_simple "echo 'SSH OK'" 10; then
        log_error "Cannot connect to Pi"
        exit 1
    fi
    
    log_success "Prerequisites OK ✓"
}

# Stop app with simple commands
stop_app() {
    log_info "Stopping Bedrock app..."
    
    # Check if running
    if ! ssh_simple "pgrep -f '$LAUNCHER_NAME' >/dev/null 2>&1" 10; then
        log_info "No app running"
        return 0
    fi
    
    # Simple kill
    ssh_simple "pkill -KILL -f '$LAUNCHER_NAME'" 10 || true
    ssh_simple "pkill -KILL -f 'bedrock'" 10 || true
    
    sleep 2
    log_success "App stopped ✓"
}

# Sync files
sync_files() {
    log_info "Syncing files..."
    
    if sshpass -p "$PI_PASS" rsync -avz --checksum \
        --exclude="__pycache__/" --exclude="*.pyc" --exclude="*.pyo" \
        --exclude=".git/" --exclude="venv/" --exclude="logs/*.log" \
        --exclude="*.tmp" --exclude=".DS_Store" --exclude="Thumbs.db" \
        -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20" \
        "$LOCAL_PROJECT_PATH/" "$PI_USER@$PI_HOST:$REMOTE_APP_PATH/"; then
        
        log_success "Files synced ✓"
        return 0
    else
        local exit_code=$?
        case $exit_code in
            23|24)
                log_warning "Sync completed with warnings (code $exit_code)"
                if ssh_simple "[ -f $REMOTE_APP_PATH/main.py ]" 10; then
                    log_success "Critical files verified ✓"
                    return 0
                fi
                ;;
        esac
        log_error "Sync failed with code $exit_code"
        return 1
    fi
}

# Check status
check_status() {
    sleep 3
    
    if ssh_simple "pgrep -f '$LAUNCHER_NAME' >/dev/null 2>&1" 10; then
        local pid=$(ssh_simple "pgrep -f '$LAUNCHER_NAME' | head -1" 10 2>/dev/null || echo "unknown")
        log_success "✅ App running (PID: $pid)"
        return 0
    else
        log_warning "⚠️  App not running"
        return 1
    fi
}

# Restart app
restart_app() {
    log_info "Restarting app..."
    
    stop_app
    
    # Try management script first
    if ssh_simple "[ -f $MANAGE_SCRIPT ]" 10; then
        if ssh_simple "$MANAGE_SCRIPT start" 30; then
            log_success "Restarted via management script ✓"
            return 0
        fi
    fi
    
    # Direct start
    ssh_simple "cd $REMOTE_APP_PATH && source venv/bin/activate && export DISPLAY=:0 && nohup python $LAUNCHER_NAME > logs/update_restart.log 2>&1 &" 20
    
    sleep 5
    if check_status >/dev/null 2>&1; then
        log_success "App restarted ✓"
    else
        log_warning "Restart may have failed - check logs"
    fi
}

# Show logs
show_logs() {
    log_info "Recent logs:"
    
    ssh_simple "
        echo '=== PROCESS STATUS ==='
        ps aux | grep python | grep -v grep | head -3
        echo ''
        echo '=== APP LOGS ==='
        tail -15 $REMOTE_APP_PATH/logs/autostart.log 2>/dev/null || echo 'No autostart log'
        echo ''
        tail -10 $REMOTE_APP_PATH/logs/update_restart.log 2>/dev/null || echo 'No restart log'
    " 30
}

# Main function
main() {
    echo ""
    log_critical "🔄 BEDROCK SIMPLE UPDATE"
    echo ""
    echo "Source: $LOCAL_PROJECT_PATH"
    echo "Target: $PI_USER@$PI_HOST:$REMOTE_APP_PATH"
    echo ""
    
    check_prerequisites
    stop_app
    
    if sync_files; then
        log_success "Update completed ✓"
    else
        log_error "Update failed"
        exit 1
    fi
    
    check_status
    
    echo ""
    log_success "🎉 UPDATE DONE"
    echo ""
    echo "Commands:"
    echo "  $0 --status    # Check status"
    echo "  $0 --restart   # Force restart"
    echo "  $0 --logs      # Show logs"
}

# Command line handling
case "${1:-}" in
    "--restart"|"-r")
        check_prerequisites
        restart_app
        ;;
    "--logs"|"-l")
        check_prerequisites
        show_logs
        ;;
    "--status"|"-s")
        check_prerequisites
        check_status
        ;;
    "--help"|"-h")
        echo "Bedrock Simple Update Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (no args)  - Update files"
        echo "  -r         - Force restart"
        echo "  -s         - Check status"
        echo "  -l         - Show logs"
        echo "  -h         - Help"
        ;;
    *)
        main
        ;;
esac