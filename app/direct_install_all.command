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
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Direct Installer${BLUE}             │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "${YELLOW}This script will install AI Money Printer with ALL dependencies${NC}"
echo -e "${YELLOW}including video processing and captioning.${NC}"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if Homebrew is installed
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

# Install required system packages
echo -e "${YELLOW}Installing required system packages...${NC}"
brew install python3 ffmpeg || {
    echo -e "${RED}Failed to install required packages. Please install Python 3 and ffmpeg manually.${NC}"
    exit 1
}

# Set up virtual environment
echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
pip3 install virtualenv || pip3 install venv || {
    echo -e "${RED}Failed to install virtualenv. Continuing without it...${NC}"
}

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m virtualenv .venv || python3 -m venv .venv || {
        echo -e "${RED}Failed to create virtual environment. Continuing without it...${NC}"
    }
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source .venv/bin/activate || {
        echo -e "${RED}Failed to activate virtual environment. Continuing without it...${NC}"
    }
fi

# Upgrade pip to latest version
echo -e "${YELLOW}Upgrading pip to latest version...${NC}"
python3 -m pip install --upgrade pip || {
    echo -e "${RED}Failed to upgrade pip. Continuing with current version...${NC}"
}

# Install all required packages with multiple retries
install_with_retry() {
    package=$1
    max_attempts=3
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo -e "${YELLOW}Installing $package (attempt $attempt of $max_attempts)...${NC}"
        pip install $package && {
            echo -e "${GREEN}Successfully installed $package!${NC}"
            return 0
        }
        
        echo -e "${YELLOW}Attempt $attempt failed. Retrying...${NC}"
        attempt=$((attempt + 1))
        sleep 1
    done
    
    echo -e "${RED}Failed to install $package after $max_attempts attempts.${NC}"
    return 1
}

# Install all required packages
echo -e "${YELLOW}Installing all required packages...${NC}"

# Install core dependencies from requirements.txt
if [ -f "temp_extract/requirements.txt" ]; then
    echo -e "${YELLOW}Installing from requirements.txt...${NC}"
    pip install -r temp_extract/requirements.txt || {
        echo -e "${RED}Failed to install from requirements.txt.${NC}"
        echo -e "${YELLOW}Will try to install essential packages individually...${NC}"
    }
fi

# Essential packages - install one by one with retries
echo -e "${YELLOW}Installing essential packages individually (with retry)...${NC}"

# Core packages
install_with_retry "streamlit>=1.30.0"
install_with_retry "watchdog>=3.0.0"
install_with_retry "pillow>=10.0.0"
install_with_retry "pandas>=2.0.0"
install_with_retry "numpy>=1.24.0"
install_with_retry "matplotlib>=3.7.0"
install_with_retry "requests>=2.28.1"
install_with_retry "opencv-python>=4.7.0"
install_with_retry "websocket-client>=1.6.0"

# Special attention to problematic packages
echo -e "${YELLOW}Installing potentially problematic packages with special attention...${NC}"
install_with_retry "python-dotenv>=1.0.0"
install_with_retry "pydub>=0.25.1"
install_with_retry "moviepy>=1.0.3"
install_with_retry "ffmpeg-python>=0.2.0"
install_with_retry "imageio-ffmpeg>=0.4.7"

# Verify critical packages were installed correctly
echo -e "${YELLOW}Verifying critical package installations...${NC}"

# Create a temporary test script
cat > verify_imports.py << EOL
import sys

def check_import(module_name):
    try:
        __import__(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {str(e)}")
        return False

# Check core packages
critical_packages = [
    "streamlit", 
    "moviepy", 
    "moviepy.editor", 
    "dotenv",
    "numpy", 
    "pandas",
    "PIL",
    "matplotlib",
    "requests",
    "cv2",
    "ffmpeg"
]

all_ok = True
for package in critical_packages:
    if not check_import(package):
        all_ok = False

if all_ok:
    print("\n✅ All critical packages verified successfully!")
    sys.exit(0)
else:
    print("\n❌ Some packages failed verification. Will try reinstalling.")
    sys.exit(1)
EOL

# Run verification
python3 verify_imports.py
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Some packages failed verification. Attempting to reinstall...${NC}"
    
    # Forcefully reinstall problematic packages
    pip install --force-reinstall moviepy python-dotenv
    
    # Try installing with alternative method if moviepy or dotenv failed
    echo -e "${YELLOW}Installing moviepy with alternative method...${NC}"
    pip install --upgrade --force-reinstall moviepy
    
    echo -e "${YELLOW}Installing python-dotenv with alternative method...${NC}"
    pip install --upgrade --force-reinstall python-dotenv
    
    # Run verification again
    echo -e "${YELLOW}Running verification again...${NC}"
    python3 verify_imports.py || {
        echo -e "${RED}Some packages still failed verification.${NC}"
        echo -e "${YELLOW}The application may not work properly.${NC}"
    }
fi

# Clean up verification script
rm verify_imports.py

# Install Whisper and its dependencies
echo -e "${YELLOW}Installing Whisper and its dependencies...${NC}"
pip install torch tqdm more-itertools numpy "transformers>=4.19.0" || {
    echo -e "${RED}Failed to install Whisper dependencies.${NC}"
    echo -e "${YELLOW}Continuing anyway...${NC}"
}

# Install Whisper from GitHub
echo -e "${YELLOW}Installing Whisper from GitHub (this may take a while)...${NC}"
pip install git+https://github.com/openai/whisper.git || {
    echo -e "${RED}Failed to install Whisper from GitHub.${NC}"
    echo -e "${YELLOW}The application may still work without Whisper.${NC}"
}

# Create a final package verification script
cat > final_verification.py << EOL
import importlib.util
import sys

def check_package(package_name, module_name=None):
    if module_name is None:
        module_name = package_name
    
    spec = importlib.util.find_spec(module_name)
    if spec is not None:
        print(f"✅ {package_name} is installed")
        return True
    else:
        print(f"❌ {package_name} is NOT installed")
        return False

# Check essential packages
packages = {
    "moviepy": "moviepy",
    "moviepy.editor": "moviepy.editor",
    "python-dotenv": "dotenv",
    "numpy": "numpy",
    "streamlit": "streamlit",
    "pandas": "pandas",
    "Pillow": "PIL",
    "ffmpeg-python": "ffmpeg",
    "opencv-python": "cv2"
}

missing = []
for package, module in packages.items():
    if not check_package(package, module):
        missing.append(package)

if missing:
    print(f"\n❌ Missing packages: {', '.join(missing)}")
    sys.exit(1)
else:
    print("\n✅ All essential packages are installed!")
    sys.exit(0)
EOL

echo -e "${YELLOW}Running final package verification...${NC}"
python3 final_verification.py
verification_result=$?

# Clean up verification script
rm final_verification.py

# Print completion message
if [ $verification_result -eq 0 ]; then
    echo -e "${GREEN}Installation complete and verified!${NC}"
else
    echo -e "${YELLOW}Installation complete, but some packages could not be verified.${NC}"
    echo -e "${YELLOW}The application may not work properly.${NC}"
fi

echo -e "${YELLOW}All dependencies have been installed, including video processing and captioning.${NC}"
echo ""

# Check for the main application file
echo -e "${YELLOW}Checking for main application file...${NC}"
if [ -f "Home.py" ]; then
    echo -e "${GREEN}Found main application file: Home.py${NC}"
    echo -e "${YELLOW}You can run the application with: ${GREEN}streamlit run Home.py${NC}"
else
    echo -e "${YELLOW}Main application file not found.${NC}"
    echo -e "${YELLOW}You may need to run the application manually.${NC}"
fi

# Deactivate virtual environment if active
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

echo -e "${GREEN}Installation process completed!${NC}" 