#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}┌───────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Whisper Fix Installer${BLUE}  │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────┘${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo -e "${YELLOW}Please install Python 3 first.${NC}"
    exit 1
fi

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}No active virtual environment detected.${NC}"
    
    # Check if we're in the app directory
    if [ -d "venv" ]; then
        echo -e "${YELLOW}Activating local virtual environment...${NC}"
        source venv/bin/activate
        ACTIVATED_ENV=true
    else
        echo -e "${YELLOW}Looking for virtual environment in standard locations...${NC}"
        
        # Check for common virtual environment locations
        if [ -d "$HOME/Applications/AiMoneyPrinter/venv" ]; then
            echo -e "${YELLOW}Found virtual environment in $HOME/Applications/AiMoneyPrinter${NC}"
            source "$HOME/Applications/AiMoneyPrinter/venv/bin/activate"
            cd "$HOME/Applications/AiMoneyPrinter"
            ACTIVATED_ENV=true
        else
            echo -e "${RED}No virtual environment found.${NC}"
            echo -e "${YELLOW}Installing globally (not recommended).${NC}"
            echo -e "${YELLOW}Press Ctrl+C to cancel or any key to continue...${NC}"
            read -n 1
        fi
    fi
fi

echo -e "${YELLOW}Uninstalling any existing Whisper packages...${NC}"
pip uninstall -y openai-whisper whisper 2>/dev/null || true

echo -e "${YELLOW}Installing Whisper dependencies...${NC}"
pip install torch tqdm more-itertools numpy "transformers>=4.19.0" "ffmpeg-python==0.2.0"

echo -e "${YELLOW}Installing Whisper directly from GitHub...${NC}"
pip install git+https://github.com/openai/whisper.git

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Whisper installation successful!${NC}"
    
    # Test the installation
    echo -e "${YELLOW}Testing Whisper installation...${NC}"
    if python3 -c "import whisper; print(f'Whisper version: {whisper.__version__}')" 2>/dev/null; then
        echo -e "${GREEN}Whisper is working correctly!${NC}"
    else
        echo -e "${RED}Warning: Whisper import test failed.${NC}"
        echo -e "${YELLOW}This might be due to missing dependencies.${NC}"
    fi
else
    echo -e "${RED}Failed to install Whisper.${NC}"
    echo -e "${YELLOW}Please check the error messages above.${NC}"
fi

# Deactivate virtual environment if we activated it
if [ "$ACTIVATED_ENV" = true ]; then
    echo -e "${YELLOW}Deactivating virtual environment...${NC}"
    deactivate
fi

echo -e "${GREEN}Done!${NC}" 