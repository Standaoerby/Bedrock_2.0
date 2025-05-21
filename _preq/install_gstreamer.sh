
#!/bin/bash
# Script to install GStreamer and required dependencies for the Bedrock application

set -e  # Exit on error

# Terminal colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing GStreamer dependencies for Bedrock App...${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    # freedesktop.org and systemd
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
elif type lsb_release >/dev/null 2>&1; then
    # linuxbase.org
    OS=$(lsb_release -si)
    VER=$(lsb_release -sr)
else
    echo -e "${RED}Cannot detect operating system!${NC}"
    exit 1
fi

echo -e "Detected OS: ${GREEN}$OS $VER${NC}"

# Install based on OS
case $OS in
    "Raspberry Pi OS" | "Raspbian"* | "Debian" | "Ubuntu" | "Linux Mint")
        echo -e "${BLUE}Installing GStreamer packages for Debian/Ubuntu based system...${NC}"
        
        echo -e "${GREEN}Updating package lists...${NC}"
        sudo apt-get update
        
        echo -e "${GREEN}Installing GStreamer packages...${NC}"
        sudo apt-get install -y \
            gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad \
            gstreamer1.0-plugins-ugly \
            gstreamer1.0-tools \
            python3-gst-1.0 \
            libgstreamer1.0-dev \
            libgstreamer-plugins-base1.0-dev
        
        # Install PyGObject dependencies
        echo -e "${GREEN}Installing PyGObject dependencies...${NC}"
        sudo apt-get install -y \
            python3-gi \
            python3-gi-cairo \
            gir1.2-gtk-3.0
        ;;
        
    *)
        echo -e "${RED}Unsupported operating system: $OS${NC}"
        echo "This script supports Debian-based distributions like Raspberry Pi OS, Debian, Ubuntu."
        echo "For other systems, please install GStreamer packages manually."
        exit 1
        ;;
esac

# Check installation
echo -e "${BLUE}Checking GStreamer installation...${NC}"

if command -v gst-inspect-1.0 >/dev/null 2>&1; then
    echo -e "${GREEN}GStreamer command-line tools installed successfully!${NC}"
    gst-inspect-1.0 --version
else
    echo -e "${RED}GStreamer installation may have failed. Command 'gst-inspect-1.0' not found.${NC}"
    exit 1
fi

# Check Python GStreamer binding
echo -e "${BLUE}Testing Python GStreamer binding...${NC}"
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print('GStreamer Python binding works!')" || {
    echo -e "${RED}Python GStreamer binding test failed!${NC}"
    exit 1
}

echo -e "${GREEN}GStreamer installation completed successfully!${NC}"
echo -e "${BLUE}You can now run the Bedrock application with GStreamer support.${NC}"