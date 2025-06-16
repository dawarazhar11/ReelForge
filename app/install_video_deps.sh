#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}┌───────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Video Dependencies${BLUE}      │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────┘${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo -e "${YELLOW}Please install Python 3 first.${NC}"
    exit 1
fi

# Check if the dependencies script exists
if [ ! -f "utils/video/dependencies.py" ]; then
    echo -e "${RED}Error: Video dependencies script not found.${NC}"
    echo -e "${YELLOW}Make sure you're running this script from the application directory.${NC}"
    exit 1
fi

# Make the script executable
chmod +x utils/video/dependencies.py

# Run the dependencies script
echo -e "${YELLOW}Running video dependencies installer...${NC}"
echo -e "${YELLOW}This will install all required packages for video processing.${NC}"
echo ""

python3 utils/video/dependencies.py

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Video dependencies installation complete!${NC}"
    echo -e "${YELLOW}You can now use the video processing features.${NC}"
else
    echo -e "${RED}Error: Failed to install video dependencies.${NC}"
    echo -e "${YELLOW}Please check the error messages above.${NC}"
fi 