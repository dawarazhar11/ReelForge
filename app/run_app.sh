#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Money Printer...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    echo "You can install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}pip3 is not installed. Installing pip...${NC}"
    python3 -m ensurepip --upgrade
fi

# Check if virtualenv is installed
if ! command -v virtualenv &> /dev/null; then
    echo -e "${YELLOW}virtualenv not found. Installing...${NC}"
    pip3 install virtualenv
fi

# Setup virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    virtualenv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}Installing required packages...${NC}"
    # Install core dependencies if requirements.txt doesn't exist
    pip install streamlit requests pillow numpy websocket-client
fi

# Check for critical dependencies and install if missing
echo -e "${YELLOW}Verifying critical dependencies...${NC}"

# Function to check if a Python module can be imported
check_module() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Array of critical modules
CRITICAL_MODULES=(
    "moviepy.editor"
    "pydub"
    "cv2"
    "matplotlib"
    "pandas"
    "dotenv"
)

# Check each module and install if missing
for module in "${CRITICAL_MODULES[@]}"; do
    module_name=$(echo $module | cut -d. -f1)
    if ! check_module $module; then
        echo -e "${YELLOW}Module '$module' not found. Installing $module_name...${NC}"
        case $module_name in
            "moviepy")
                pip install moviepy>=1.0.3
                ;;
            "pydub")
                pip install pydub>=0.25.1
                ;;
            "cv2")
                pip install opencv-python>=4.7.0
                ;;
            "matplotlib")
                pip install matplotlib>=3.7.0
                ;;
            "pandas")
                pip install pandas>=2.0.0
                ;;
            "dotenv")
                pip install python-dotenv>=1.0.0
                ;;
            *)
                pip install $module_name
                ;;
        esac
    else
        echo -e "${GREEN}Module '$module' is already installed.${NC}"
    fi
done

# Check for FFmpeg (required by moviepy)
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}FFmpeg not found, which is required for video processing.${NC}"
    echo -e "${YELLOW}Attempting to install FFmpeg using pip...${NC}"
    pip install ffmpeg-python
    
    # If still not available, provide instructions
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${RED}FFmpeg is still not available in PATH.${NC}"
        echo -e "${YELLOW}You may need to install FFmpeg manually:${NC}"
        echo -e "  macOS: brew install ffmpeg"
        echo -e "  Linux: apt-get install ffmpeg"
        echo -e "After installing, restart this script."
        read -p "Do you want to continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Run the app
echo -e "${GREEN}Launching app...${NC}"
streamlit run Home.py 