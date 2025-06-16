#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Make sure run and build scripts are executable
chmod +x run_app.sh
chmod +x build_macos_app.sh

clear
echo -e "${BLUE}┌───────────────────────────────────────┐${NC}"
echo -e "${BLUE}│     ${GREEN}AI Money Printer - Starter Menu${BLUE}     │${NC}"
echo -e "${BLUE}└───────────────────────────────────────┘${NC}"
echo ""
echo -e "${YELLOW}Please select an option:${NC}"
echo ""
echo -e "  ${GREEN}1${NC}) Run the app"
echo -e "  ${GREEN}2${NC}) Build macOS application"
echo -e "  ${GREEN}3${NC}) Exit"
echo ""

read -p "Enter your choice [1-3]: " choice

case $choice in
    1)
        echo -e "${GREEN}Running the app...${NC}"
        ./run_app.sh
        ;;
    2)
        echo -e "${GREEN}Building macOS application...${NC}"
        ./build_macos_app.sh
        ;;
    3)
        echo -e "${GREEN}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option. Exiting.${NC}"
        exit 1
        ;;
esac 