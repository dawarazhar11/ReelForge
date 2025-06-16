#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
clear
echo -e "${BLUE}┌───────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Complete macOS Installer${BLUE}    │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "${YELLOW}This script will install:${NC}"
echo -e "  1. Homebrew (if not already installed)"
echo -e "  2. Python 3 (if not already installed)"
echo -e "  3. FFmpeg and other dependencies"
echo -e "  4. AI Money Printer application"
echo ""
echo -e "${YELLOW}Press Enter to continue or Ctrl+C to cancel...${NC}"
read

# Check system requirements
echo -e "${YELLOW}Checking system requirements...${NC}"
OS_VERSION=$(sw_vers -productVersion)
echo -e "macOS version: ${GREEN}$OS_VERSION${NC}"
AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
echo -e "Available disk space: ${GREEN}$AVAILABLE_SPACE${NC}"
CPU_ARCH=$(uname -m)
echo -e "CPU architecture: ${GREEN}$CPU_ARCH${NC}"

# Install Homebrew if it's not already installed
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Installing Homebrew package manager...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH based on architecture
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $HOME/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> $HOME/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}Homebrew is already installed.${NC}"
fi

# Install Python if it's not already installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Installing Python 3...${NC}"
    brew install python
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}Python $PYTHON_VERSION is already installed.${NC}"
fi

# Install Xcode command line tools if needed
if ! xcode-select -p &> /dev/null; then
    echo -e "${YELLOW}Installing Xcode Command Line Tools...${NC}"
    xcode-select --install
    echo -e "${YELLOW}Please wait for Xcode Command Line Tools to finish installing, then press any key to continue...${NC}"
    read -n 1
fi

# Install FFmpeg (required for video processing)
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}Installing FFmpeg (required for video processing)...${NC}"
    brew install ffmpeg
else
    echo -e "${GREEN}FFmpeg is already installed.${NC}"
fi

# Install or update pip
echo -e "${YELLOW}Updating pip...${NC}"
python3 -m ensurepip --upgrade

# Install virtualenv
echo -e "${YELLOW}Installing virtualenv...${NC}"
pip3 install virtualenv

# Setup application
echo -e "${YELLOW}Setting up AI Money Printer...${NC}"

# Create application directory
APP_DIR="$HOME/Applications/AiMoneyPrinter"
mkdir -p "$APP_DIR"

# Copy files to application directory
echo -e "${YELLOW}Copying application files...${NC}"
cp -R . "$APP_DIR"

# Make scripts executable
echo -e "${YELLOW}Making scripts executable...${NC}"
find "$APP_DIR" -name "*.sh" -exec chmod +x {} \;
find "$APP_DIR" -name "*.command" -exec chmod +x {} \;
find "$APP_DIR" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true

# Create virtual environment
cd "$APP_DIR"
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m virtualenv venv

# Activate virtual environment and install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
source venv/bin/activate

# Install from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install streamlit requests pillow numpy websocket-client pydub moviepy opencv-python matplotlib pandas python-dotenv
fi

# Run the video dependencies installer script
echo -e "${YELLOW}Installing comprehensive video dependencies...${NC}"
if [ -f "utils/video/dependencies.py" ]; then
    # Create a temporary script to automatically select option 2 (all dependencies)
    cat > temp_auto_select.py << EOL
import sys
import time

# Wait for the script to start
time.sleep(1)

# Send "2" to select all dependencies
sys.stdout.write("2\n")
sys.stdout.flush()

# Keep the script running to capture output
while True:
    time.sleep(0.1)
EOL
    
    # Run the dependencies script with automatic input
    python3 temp_auto_select.py | python3 utils/video/dependencies.py
    rm temp_auto_select.py
    
    echo -e "${GREEN}Video dependencies installation complete.${NC}"
else
    echo -e "${YELLOW}Video dependencies script not found. Skipping this step.${NC}"
fi

# Fix Whisper installation
echo -e "${YELLOW}Installing Whisper from GitHub...${NC}"
pip uninstall -y openai-whisper whisper 2>/dev/null || true
pip install torch tqdm more-itertools numpy "transformers>=4.19.0" "ffmpeg-python==0.2.0"
pip install git+https://github.com/openai/whisper.git

# Deactivate virtual environment
deactivate

# Create desktop shortcut
echo -e "${YELLOW}Creating application shortcut...${NC}"

# Create Applications folder shortcut
APPLICATIONS_DIR="$HOME/Applications"
mkdir -p "$APPLICATIONS_DIR"

# Create launcher script
cat > "$APP_DIR/launch.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
./start.sh
EOL

chmod +x "$APP_DIR/launch.command"

# Create symbolic link in Applications folder
ln -sf "$APP_DIR/launch.command" "$APPLICATIONS_DIR/AI Money Printer.command"

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${YELLOW}You can start AI Money Printer in these ways:${NC}"
echo -e "  1. Double-click 'AI Money Printer.command' in your Applications folder"
echo -e "  2. Run this command in Terminal: ${GREEN}$APP_DIR/start.sh${NC}"
echo ""
echo -e "${YELLOW}Would you like to launch AI Money Printer now? (y/n)${NC}"
read -p "Enter your choice: " launch_choice

case $launch_choice in
    [Yy]*)
        echo -e "${GREEN}Launching AI Money Printer...${NC}"
        cd "$APP_DIR"
        ./start.sh
        ;;
    *)
        echo -e "${GREEN}Installation complete. You can launch AI Money Printer later.${NC}"
        ;;
esac 