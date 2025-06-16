#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}┌───────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - B-Roll Cache Refresh${BLUE}  │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────┘${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "clear_broll_cache.py" ]; then
    echo -e "${RED}Error: clear_broll_cache.py not found in current directory.${NC}"
    echo -e "${YELLOW}Please run this script from the application directory.${NC}"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found.${NC}"
    echo -e "${YELLOW}Please install Python 3 or make sure it's in your PATH.${NC}"
    exit 1
fi

# Make sure the script is executable
chmod +x clear_broll_cache.py

# Run the cache clearing script
echo -e "${YELLOW}Running B-Roll cache clearing script...${NC}"
python3 clear_broll_cache.py

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Cache clearing complete!${NC}"
    echo -e "${YELLOW}Now you can run the Video Assembly page to create a new video with the latest B-Roll content.${NC}"
    
    # Ask if the user wants to run the app
    read -p "Do you want to run the app now? (y/n): " run_app
    if [[ $run_app == "y" || $run_app == "Y" ]]; then
        if [ -f "run_app.sh" ]; then
            echo -e "${YELLOW}Starting the app...${NC}"
            ./run_app.sh
        else
            echo -e "${RED}Error: run_app.sh not found.${NC}"
            echo -e "${YELLOW}Please run the app manually.${NC}"
        fi
    else
        echo -e "${YELLOW}You can run the app later using ./run_app.sh${NC}"
    fi
else
    echo -e "${RED}Error: Failed to clear cache.${NC}"
    echo -e "${YELLOW}Please check the error message above.${NC}"
fi 