#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
clear
echo -e "${BLUE}┌───────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Robust macOS Installer${BLUE}      │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "${YELLOW}This script will install AI Money Printer with extra safeguards${NC}"
echo -e "${YELLOW}to prevent installation from getting stuck.${NC}"
echo ""
echo -e "${YELLOW}Press Enter to continue or Ctrl+C to cancel...${NC}"
read

# Change to script directory
cd "$(dirname "$0")"

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to install a package with Homebrew if it doesn't exist
install_brew_package() {
    if ! command_exists "$1"; then
        echo -e "${YELLOW}Installing $1...${NC}"
        brew install "$1" || {
            echo -e "${RED}Failed to install $1. Please install it manually.${NC}"
            return 1
        }
    else
        echo -e "${GREEN}$1 is already installed.${NC}"
    fi
    return 0
}

# Function to create and activate virtual environment
setup_venv() {
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m virtualenv venv || python3 -m venv venv || {
            echo -e "${RED}Failed to create virtual environment.${NC}"
            return 1
        }
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate || {
        echo -e "${RED}Failed to activate virtual environment.${NC}"
        return 1
    }
    
    return 0
}

# Function to install Python packages
install_python_packages() {
    echo -e "${YELLOW}Installing Python packages...${NC}"
    
    # Install from requirements.txt if it exists
    if [ -f "requirements.txt" ]; then
        echo -e "${YELLOW}Installing from requirements.txt...${NC}"
        pip install -r requirements.txt || {
            echo -e "${RED}Failed to install from requirements.txt.${NC}"
            echo -e "${YELLOW}Trying to install essential packages individually...${NC}"
            pip install streamlit requests pillow numpy websocket-client pydub moviepy opencv-python matplotlib pandas python-dotenv || {
                echo -e "${RED}Failed to install essential packages.${NC}"
                return 1
            }
        }
    else
        # Install essential packages
        echo -e "${YELLOW}Installing essential Python packages...${NC}"
        pip install streamlit requests pillow numpy websocket-client pydub moviepy opencv-python matplotlib pandas python-dotenv || {
            echo -e "${RED}Failed to install essential packages.${NC}"
            return 1
        }
    fi
    
    return 0
}

# Function to install video dependencies with timeout
install_video_deps() {
    echo -e "${YELLOW}Installing video dependencies...${NC}"
    
    # Check if the dependencies script exists
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

        # Run the dependencies script with a timeout
        echo -e "${YELLOW}Running video dependencies installer (with 60 second timeout)...${NC}"
        timeout 60 python3 temp_auto_select.py | python3 utils/video/dependencies.py || {
            echo -e "${YELLOW}Video dependencies installation timed out or failed.${NC}"
            echo -e "${YELLOW}This is often normal - the script may have completed successfully.${NC}"
        }
        
        rm temp_auto_select.py
        
        # Force install key packages
        echo -e "${YELLOW}Ensuring key video packages are installed...${NC}"
        pip install ffmpeg-python imageio-ffmpeg || true
    else
        echo -e "${YELLOW}Video dependencies script not found. Installing basic video packages...${NC}"
        pip install ffmpeg-python imageio-ffmpeg || true
    fi
}

# Function to fix Whisper installation
fix_whisper() {
    echo -e "${YELLOW}Installing Whisper from GitHub...${NC}"
    pip uninstall -y openai-whisper whisper 2>/dev/null || true
    pip install torch tqdm more-itertools numpy "transformers>=4.19.0" "ffmpeg-python==0.2.0" || true
    pip install git+https://github.com/openai/whisper.git || {
        echo -e "${RED}Failed to install Whisper from GitHub.${NC}"
        echo -e "${YELLOW}The application may still work without Whisper.${NC}"
    }
}

# Main installation process
main() {
    # 1. Check system requirements
    echo -e "${YELLOW}Checking system requirements...${NC}"
    OS_VERSION=$(sw_vers -productVersion)
    echo -e "macOS version: ${GREEN}$OS_VERSION${NC}"
    AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
    echo -e "Available disk space: ${GREEN}$AVAILABLE_SPACE${NC}"
    CPU_ARCH=$(uname -m)
    echo -e "CPU architecture: ${GREEN}$CPU_ARCH${NC}"
    
    # 2. Install Homebrew if needed
    if ! command_exists brew; then
        echo -e "${YELLOW}Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
            echo -e "${RED}Failed to install Homebrew. Please install it manually.${NC}"
            exit 1
        }
        
        # Add Homebrew to PATH
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
    
    # 3. Install required system packages
    install_brew_package "python3" || exit 1
    install_brew_package "ffmpeg" || exit 1
    install_brew_package "pip" || true  # Optional
    
    # 4. Install Python virtualenv
    pip3 install virtualenv || pip3 install venv || {
        echo -e "${RED}Failed to install virtualenv. Continuing without it...${NC}"
    }
    
    # 5. Create application directory
    APP_DIR="$HOME/Applications/AiMoneyPrinter"
    mkdir -p "$APP_DIR"
    
    # 6. Copy files to application directory
    echo -e "${YELLOW}Copying application files...${NC}"
    cp -R . "$APP_DIR" || {
        echo -e "${RED}Failed to copy files to $APP_DIR.${NC}"
        exit 1
    }
    
    # 7. Make scripts executable
    echo -e "${YELLOW}Making scripts executable...${NC}"
    find "$APP_DIR" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
    find "$APP_DIR" -name "*.command" -exec chmod +x {} \; 2>/dev/null || true
    find "$APP_DIR" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
    
    # 8. Change to application directory
    cd "$APP_DIR" || {
        echo -e "${RED}Failed to change to application directory.${NC}"
        exit 1
    }
    
    # 9. Setup virtual environment
    setup_venv || {
        echo -e "${YELLOW}Continuing without virtual environment...${NC}"
    }
    
    # 10. Install Python packages
    install_python_packages || {
        echo -e "${RED}Failed to install Python packages.${NC}"
        echo -e "${YELLOW}The application may not work properly.${NC}"
    }
    
    # 11. Install video dependencies (with timeout to prevent hanging)
    install_video_deps
    
    # 12. Fix Whisper installation
    fix_whisper
    
    # 13. Deactivate virtual environment if active
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate
    fi
    
    # 14. Create shortcuts
    echo -e "${YELLOW}Creating application shortcuts...${NC}"
    
    # Create Applications folder shortcuts
    APPLICATIONS_DIR="$HOME/Applications"
    mkdir -p "$APPLICATIONS_DIR"
    
    # Create launcher scripts
    cat > "$APP_DIR/launch.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
./start.sh
EOL
    chmod +x "$APP_DIR/launch.command"
    
    # Create manual start script
    cat > "$APP_DIR/manual_start.command" << EOL
#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to script directory
cd "\$(dirname "\$0")"

echo -e "\${YELLOW}Starting AI Money Printer manually...\${NC}"

# Check if we're in a virtual environment
if [ -d "venv" ]; then
    echo -e "\${YELLOW}Using virtual environment...\${NC}"
    source venv/bin/activate
    
    # Check if streamlit is installed
    if ! command -v streamlit &> /dev/null; then
        echo -e "\${YELLOW}Installing streamlit...\${NC}"
        pip install streamlit
    fi
    
    # Find the main application file
    if [ -f "Home.py" ]; then
        MAIN_APP="Home.py"
    else
        # Look for any .py files in the current directory
        MAIN_APP=\$(find . -maxdepth 1 -name "*.py" | head -1)
        if [ -z "\$MAIN_APP" ]; then
            echo -e "\${YELLOW}No Python files found. Please enter the main application file name:\${NC}"
            read -p "Enter filename: " MAIN_APP
        fi
    fi
    
    echo -e "\${GREEN}Starting application: \$MAIN_APP\${NC}"
    streamlit run "\$MAIN_APP"
    
    # Deactivate virtual environment when done
    deactivate
else
    echo -e "\${YELLOW}No virtual environment found. Trying with system Python...\${NC}"
    
    # Check if streamlit is installed
    if ! command -v streamlit &> /dev/null; then
        echo -e "\${YELLOW}Installing streamlit...\${NC}"
        pip3 install streamlit
    fi
    
    # Find the main application file
    if [ -f "Home.py" ]; then
        MAIN_APP="Home.py"
    else
        # Look for any .py files in the current directory
        MAIN_APP=\$(find . -maxdepth 1 -name "*.py" | head -1)
        if [ -z "\$MAIN_APP" ]; then
            echo -e "\${YELLOW}No Python files found. Please enter the main application file name:\${NC}"
            read -p "Enter filename: " MAIN_APP
        fi
    fi
    
    echo -e "\${GREEN}Starting application: \$MAIN_APP\${NC}"
    streamlit run "\$MAIN_APP"
fi
EOL
    chmod +x "$APP_DIR/manual_start.command"
    
    # Create direct streamlit runner
    cat > "$APP_DIR/direct_run.command" << EOL
#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to script directory
cd "\$(dirname "\$0")"

echo -e "\${YELLOW}Starting AI Money Printer directly with streamlit...\${NC}"

# Check if we're in a virtual environment
if [ -d "venv" ]; then
    echo -e "\${YELLOW}Using virtual environment...\${NC}"
    source venv/bin/activate
fi

# Find the main application file
if [ -f "Home.py" ]; then
    MAIN_APP="Home.py"
else
    # Look for any .py files in the current directory
    MAIN_APP=\$(find . -maxdepth 1 -name "*.py" | head -1)
    if [ -z "\$MAIN_APP" ]; then
        echo -e "\${YELLOW}No Python files found. Please enter the main application file name:\${NC}"
        read -p "Enter filename: " MAIN_APP
    fi
fi

echo -e "\${GREEN}Starting application: \$MAIN_APP\${NC}"
python3 -m streamlit run "\$MAIN_APP"
EOL
    chmod +x "$APP_DIR/direct_run.command"
    
    # Create symbolic links in Applications folder
    ln -sf "$APP_DIR/launch.command" "$APPLICATIONS_DIR/AI Money Printer.command"
    ln -sf "$APP_DIR/manual_start.command" "$APPLICATIONS_DIR/AI Money Printer (Manual Start).command"
    ln -sf "$APP_DIR/direct_run.command" "$APPLICATIONS_DIR/AI Money Printer (Direct Run).command"
    
    # 15. Installation complete
    echo -e "${GREEN}Installation complete!${NC}"
    echo -e "${YELLOW}You can start AI Money Printer in these ways:${NC}"
    echo -e "  1. Double-click 'AI Money Printer.command' in your Applications folder"
    echo -e "  2. If that doesn't work, try 'AI Money Printer (Manual Start).command'"
    echo -e "  3. If that still doesn't work, try 'AI Money Printer (Direct Run).command'"
    echo -e "  4. Run this command in Terminal: ${GREEN}$APP_DIR/start.sh${NC}"
    echo -e "  5. Run this command in Terminal: ${GREEN}$APP_DIR/manual_start.command${NC}"
    echo -e "  6. Run this command in Terminal: ${GREEN}$APP_DIR/direct_run.command${NC}"
    echo ""
    
    # 16. Ask to launch now
    echo -e "${YELLOW}Would you like to launch AI Money Printer now? (y/n)${NC}"
    read -p "Enter your choice: " launch_choice
    
    case $launch_choice in
        [Yy]*)
            echo -e "${GREEN}Launching AI Money Printer...${NC}"
            # Try each method in sequence until one works
            if [ -f "$APP_DIR/direct_run.command" ]; then
                echo -e "${YELLOW}Trying direct run method...${NC}"
                "$APP_DIR/direct_run.command"
            elif [ -f "$APP_DIR/manual_start.command" ]; then
                echo -e "${YELLOW}Trying manual start method...${NC}"
                "$APP_DIR/manual_start.command"
            elif [ -f "$APP_DIR/start.sh" ]; then
                echo -e "${YELLOW}Trying standard start method...${NC}"
                "$APP_DIR/start.sh"
            else
                echo -e "${RED}No start scripts found.${NC}"
            fi
            ;;
        *)
            echo -e "${GREEN}Installation complete. You can launch AI Money Printer later.${NC}"
            ;;
    esac
}

# Run the main installation function
main 