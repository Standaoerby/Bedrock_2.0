#!/bin/bash

# SSH Key Setup Script for Bedrock Deployment
# This script sets up SSH key authentication for passwordless deployment

PI_HOST="192.168.1.233"
PI_USER="standa"
PI_PASS="crossover"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
info() { echo -e "${BLUE}[INFO] $1${NC}"; }

# Check if we're in WSL
check_wsl() {
    if ! grep -q "microsoft" /proc/version 2>/dev/null; then
        error "This script should be run from WSL"
        exit 1
    fi
    log "Running in WSL environment ✓"
}

# Install required tools
install_tools() {
    if ! command -v sshpass &> /dev/null; then
        log "Installing sshpass..."
        sudo apt update
        sudo apt install -y sshpass
    fi
    
    if ! command -v ssh-keygen &> /dev/null; then
        log "Installing OpenSSH client..."
        sudo apt install -y openssh-client
    fi
    
    log "Tools ready ✓"
}

# Generate SSH key if it doesn't exist
generate_ssh_key() {
    SSH_KEY_PATH="$HOME/.ssh/id_rsa"
    
    if [ -f "$SSH_KEY_PATH" ]; then
        log "SSH key already exists at $SSH_KEY_PATH"
        return 0
    fi
    
    log "Generating SSH key pair..."
    
    # Create .ssh directory if it doesn't exist
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    
    # Generate key without passphrase for automation
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -C "bedrock-deployment@$(hostname)"
    
    log "SSH key generated ✓"
}

# Copy SSH key to Raspberry Pi
copy_ssh_key() {
    SSH_KEY_PATH="$HOME/.ssh/id_rsa.pub"
    
    if [ ! -f "$SSH_KEY_PATH" ]; then
        error "SSH public key not found at $SSH_KEY_PATH"
        return 1
    fi
    
    log "Copying SSH key to Raspberry Pi..."
    
    # Use sshpass to copy the key
    sshpass -p "$PI_PASS" ssh-copy-id -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST"
    
    if [ $? -eq 0 ]; then
        log "SSH key copied successfully ✓"
        return 0
    else
        error "Failed to copy SSH key"
        return 1
    fi
}

# Test SSH key authentication
test_ssh_key() {
    log "Testing SSH key authentication..."
    
    # Try to connect without password
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o PasswordAuthentication=no "$PI_USER@$PI_HOST" "echo 'SSH key authentication successful'" 2>/dev/null; then
        log "SSH key authentication working ✓"
        return 0
    else
        error "SSH key authentication failed"
        return 1
    fi
}

# Create updated deployment scripts without passwords
create_secure_scripts() {
    log "Creating secure deployment scripts..."
    
    # Create secure deploy script
    cat > deploy_secure.sh << 'EOF'
#!/bin/bash

# Secure Bedrock App Deployment Script (using SSH keys)
# Run from WSL on Windows 11

set -e

# Configuration
PI_HOST="192.168.1.233"
PI_USER="standa"
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"
REMOTE_PROJECT_PATH="/home/standa/bedrock-app"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
info() { echo -e "${BLUE}[INFO] $1${NC}"; }

# Execute command on remote Pi (no password needed)
remote_exec() {
    ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "$1"
}

# Test SSH connection
test_connection() {
    log "Testing SSH connection..."
    if remote_exec "echo 'Connection successful'"; then
        log "SSH connection successful ✓"
    else
        error "SSH connection failed"
        error "Make sure SSH keys are set up correctly"
        exit 1
    fi
}

# Sync files using rsync with SSH keys
sync_files() {
    log "Syncing project files..."
    
    EXCLUDE_FILE=$(mktemp)
    cat > "$EXCLUDE_FILE" << 'EXCLUDE_EOF'
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
EXCLUDE_EOF

    rsync -avz --delete \
        --exclude-from="$EXCLUDE_FILE" \
        --progress \
        -e "ssh -o StrictHostKeyChecking=no" \
        "$LOCAL_PROJECT_PATH/" \
        "$PI_USER@$PI_HOST:$REMOTE_PROJECT_PATH/"
    
    rm "$EXCLUDE_FILE"
    log "File sync completed ✓"
}

# Update Python dependencies
update_deps() {
    log "Updating Python dependencies..."
    remote_exec "
        cd $REMOTE_PROJECT_PATH
        source venv/bin/activate
        pip install -r requirements.txt --upgrade
    "
    log "Dependencies updated ✓"
}

# Main deployment
main() {
    log "Starting secure deployment..."
    test_connection
    sync_files
    update_deps
    log "Secure deployment completed! 🎉"
}

main "$@"
EOF

    chmod +x deploy_secure.sh
    
    # Create secure update script
    cat > update_secure.sh << 'EOF'
#!/bin/bash

# Secure update script for Bedrock app (using SSH keys)

PI_HOST="192.168.1.233"
PI_USER="standa"
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"
REMOTE_PROJECT_PATH="/home/standa/bedrock-app"

echo "Updating Bedrock app securely..."

# Sync only changed files
EXCLUDE_FILE=$(mktemp)
cat > "$EXCLUDE_FILE" << 'EXCLUDE_EOF'
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
EXCLUDE_EOF

rsync -avz --delete \
    --exclude-from="$EXCLUDE_FILE" \
    --progress \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_PROJECT_PATH/" \
    "$PI_USER@$PI_HOST:$REMOTE_PROJECT_PATH/"

rm "$EXCLUDE_FILE"

# Update dependencies if needed
ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "
    cd $REMOTE_PROJECT_PATH
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
"

echo "Secure update completed!"
EOF

    chmod +x update_secure.sh
    
    log "Secure scripts created:"
    info "  • deploy_secure.sh - For full deployment without passwords"
    info "  • update_secure.sh - For updates without passwords"
}

# Add SSH config for easier connection
setup_ssh_config() {
    log "Setting up SSH config..."
    
    SSH_CONFIG="$HOME/.ssh/config"
    
    # Create SSH config directory if it doesn't exist
    mkdir -p "$HOME/.ssh"
    
    # Check if config already has our Pi entry
    if grep -q "Host bedrock-pi" "$SSH_CONFIG" 2>/dev/null; then
        log "SSH config already contains bedrock-pi entry"
        return 0
    fi
    
    # Add Pi configuration
    cat >> "$SSH_CONFIG" << EOF

# Bedrock Raspberry Pi
Host bedrock-pi
    HostName $PI_HOST
    User $PI_USER
    StrictHostKeyChecking no
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF

    chmod 600 "$SSH_CONFIG"
    
    log "SSH config updated. You can now connect with: ssh bedrock-pi"
}

# Create convenience aliases
create_aliases() {
    log "Creating convenient aliases..."
    
    BASHRC="$HOME/.bashrc"
    
    # Check if aliases already exist
    if grep -q "# Bedrock Pi aliases" "$BASHRC" 2>/dev/null; then
        log "Aliases already exist in .bashrc"
        return 0
    fi
    
    # Add aliases
    cat >> "$BASHRC" << 'EOF'

# Bedrock Pi aliases
alias pi-connect="ssh bedrock-pi"
alias pi-logs="ssh bedrock-pi 'tail -f /home/standa/bedrock-app/logs/bedrock.log'"
alias pi-status="ssh bedrock-pi '/home/standa/manage_bedrock.sh status'"
alias pi-restart="ssh bedrock-pi '/home/standa/manage_bedrock.sh restart'"
alias pi-deploy="./deploy_secure.sh"
alias pi-update="./update_secure.sh"
EOF

    log "Aliases added to .bashrc. Reload with: source ~/.bashrc"
    info "New aliases available:"
    info "  • pi-connect  - Connect to Pi"
    info "  • pi-logs     - View live logs"
    info "  • pi-status   - Check app status"
    info "  • pi-restart  - Restart app"
    info "  • pi-deploy   - Deploy app"
    info "  • pi-update   - Update app"
}

# Main setup function
main() {
    log "Setting up SSH keys for Bedrock deployment..."
    
    check_wsl
    install_tools
    generate_ssh_key
    
    if copy_ssh_key && test_ssh_key; then
        setup_ssh_config
        create_secure_scripts
        create_aliases
        
        log "SSH key setup completed successfully! 🎉"
        info "You can now deploy without passwords using:"
        info "  ./deploy_secure.sh"
        info "  ./update_secure.sh"
        warn "Don't forget to reload your shell: source ~/.bashrc"
    else
        error "SSH key setup failed"
        warn "You can still use the original scripts with passwords"
        exit 1
    fi
}

# Run main function
main "$@"