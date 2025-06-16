#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building AI Money Printer macOS App...${NC}"

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

# Setup build virtual environment
if [ -d "build_venv" ]; then
    echo -e "${YELLOW}Removing old build environment...${NC}"
    rm -rf build_venv
fi

echo -e "${YELLOW}Creating build virtual environment...${NC}"
virtualenv build_venv

# Activate virtual environment
echo "Activating build virtual environment..."
source build_venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install streamlit requests pillow numpy websocket-client
fi

# Install PyInstaller and py2app
echo -e "${YELLOW}Installing build tools...${NC}"
pip install pyinstaller py2app

# Clean up previous builds
echo -e "${YELLOW}Cleaning up previous builds...${NC}"
rm -rf build dist

# First attempt: Try py2app (macOS specific)
echo -e "${YELLOW}Building with py2app...${NC}"
python setup.py py2app -A

# Second attempt: Try PyInstaller as a fallback
if [ ! -d "dist/AI Money Printer.app" ]; then
    echo -e "${YELLOW}Falling back to PyInstaller...${NC}"
    pyinstaller --name="AI Money Printer" \
                --windowed \
                --add-data="assets:assets" \
                --hidden-import=streamlit.runtime.scriptrunner.magic_funcs \
                --collect-all streamlit \
                hume.py
fi

echo -e "${GREEN}Build complete!${NC}"
echo -e "The application is available in the ${YELLOW}dist${NC} folder."

# Deactivate virtual environment
deactivate

# Cleanup build environment
echo -e "${YELLOW}Cleaning up build environment...${NC}"
rm -rf build_venv

echo -e "${GREEN}Done!${NC}" 