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
echo -e "${BLUE}┌───────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│     ${GREEN}AI Money Printer - macOS Installer${BLUE}        │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────┘${NC}"
echo ""

# Check for admin permissions if needed
check_admin() {
    echo -e "${YELLOW}Checking permissions...${NC}"
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Some installations may require admin privileges.${NC}"
        echo -e "You may be prompted for your password during installation."
    fi
}

# Check system requirements
check_system() {
    echo -e "${YELLOW}Checking system requirements...${NC}"
    
    # Check macOS version
    OS_VERSION=$(sw_vers -productVersion)
    echo -e "macOS version: ${GREEN}$OS_VERSION${NC}"
    
    # Check available disk space
    AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
    echo -e "Available disk space: ${GREEN}$AVAILABLE_SPACE${NC}"
    
    # Check CPU architecture
    CPU_ARCH=$(uname -m)
    echo -e "CPU architecture: ${GREEN}$CPU_ARCH${NC}"
}

# Install Homebrew if it's not already installed
install_homebrew() {
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
}

# Install Python if it's not already installed
install_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}Installing Python 3...${NC}"
        brew install python
    else
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${GREEN}Python $PYTHON_VERSION is already installed.${NC}"
    fi
}

# Install app dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing application dependencies...${NC}"
    
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
    python3 -m ensurepip --upgrade
    
    # Install virtualenv
    pip3 install virtualenv
}

# Setup application
setup_application() {
    echo -e "${YELLOW}Setting up AI Money Printer...${NC}"
    
    # Create application directory
    APP_DIR="$HOME/Applications/AiMoneyPrinter"
    mkdir -p "$APP_DIR"
    
    # Copy files to application directory
    echo -e "${YELLOW}Copying application files...${NC}"
    
    # Ask for installation source
    echo -e "${YELLOW}Please specify the installation source:${NC}"
    echo -e "  ${GREEN}1${NC}) Current directory (if you're already in the app directory)"
    echo -e "  ${GREEN}2${NC}) Specify a different directory"
    echo -e "  ${GREEN}3${NC}) Download from GitHub (coming soon)"
    
    read -p "Enter your choice [1-3]: " source_choice
    
    case $source_choice in
        1)
            # Copy from current directory
            echo -e "${YELLOW}Copying files from current directory...${NC}"
            cp -R . "$APP_DIR"
            ;;
        2)
            # Specify source directory
            read -p "Enter the full path to the source directory: " SOURCE_DIR
            if [ -d "$SOURCE_DIR" ]; then
                echo -e "${YELLOW}Copying files from $SOURCE_DIR...${NC}"
                cp -R "$SOURCE_DIR"/* "$APP_DIR"
            else
                echo -e "${RED}Source directory not found. Installation aborted.${NC}"
                exit 1
            fi
            ;;
        3)
            # GitHub download option (placeholder for future)
            echo -e "${RED}GitHub download option coming soon. Please choose another option.${NC}"
            setup_application
            return
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            setup_application
            return
            ;;
    esac
    
    # Make scripts executable
    chmod +x "$APP_DIR"/*.sh
    
    # Create virtual environment
    cd "$APP_DIR"
    python3 -m virtualenv venv
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    
    # Install from requirements.txt if it exists
    if [ -f "requirements.txt" ]; then
        echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
        pip install -r requirements.txt
    else
        echo -e "${YELLOW}Installing required packages...${NC}"
        pip install streamlit requests pillow numpy websocket-client pydub moviepy opencv-python matplotlib pandas python-dotenv
    fi
    
    # Verify critical dependencies are installed
    echo -e "${YELLOW}Verifying critical dependencies...${NC}"
    
    # Check for moviepy and install if needed
    if ! python3 -c "import moviepy.editor" &>/dev/null; then
        echo -e "${YELLOW}Installing moviepy (required for video processing)...${NC}"
        pip install moviepy>=1.0.3
    else
        echo -e "${GREEN}moviepy is already installed.${NC}"
    fi
    
    # Check for other critical dependencies
    for module in "pydub" "cv2" "matplotlib" "pandas"; do
        if ! python3 -c "import $module" &>/dev/null; then
            echo -e "${YELLOW}Installing $module...${NC}"
            pip install $module
        else
            echo -e "${GREEN}$module is already installed.${NC}"
        fi
    done
    
    # Run the video dependencies installer script
    echo -e "${YELLOW}Running comprehensive video dependencies installer...${NC}"
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
    
    # Deactivate virtual environment
    deactivate
}

# Create desktop shortcut
create_shortcut() {
    echo -e "${YELLOW}Creating application shortcut...${NC}"
    
    APP_DIR="$HOME/Applications/AiMoneyPrinter"
    
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
    
    echo -e "${GREEN}Shortcut created in $APPLICATIONS_DIR${NC}"
}

# Final setup and instructions
finish_setup() {
    APP_DIR="$HOME/Applications/AiMoneyPrinter"
    
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
}

# Main installation process
main() {
    check_admin
    check_system
    install_homebrew
    install_python
    install_dependencies
    setup_application
    create_shortcut
    finish_setup
}

# Run the installation
main 