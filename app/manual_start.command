#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to script directory
cd "$(dirname "$0")"

echo -e "${YELLOW}Starting AI Money Printer manually...${NC}"

# Check if we're in a virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}Using virtual environment...${NC}"
    source venv/bin/activate
    
    # Check if streamlit is installed
    if ! command -v streamlit &> /dev/null; then
        echo -e "${YELLOW}Installing streamlit...${NC}"
        pip install streamlit
    fi
    
    # Find the main application file
    if [ -f "Home.py" ]; then
        MAIN_APP="Home.py"
    else
        # Look for any .py files in the current directory
        MAIN_APP=$(find . -maxdepth 1 -name "*.py" | head -1)
        if [ -z "$MAIN_APP" ]; then
            echo -e "${YELLOW}No Python files found. Please enter the main application file name:${NC}"
            read -p "Enter filename: " MAIN_APP
        fi
    fi
    
    echo -e "${GREEN}Starting application: $MAIN_APP${NC}"
    streamlit run "$MAIN_APP"
    
    # Deactivate virtual environment when done
    deactivate
else
    echo -e "${YELLOW}No virtual environment found. Trying with system Python...${NC}"
    
    # Check if streamlit is installed
    if ! command -v streamlit &> /dev/null; then
        echo -e "${YELLOW}Installing streamlit...${NC}"
        pip3 install streamlit
    fi
    
    # Find the main application file
    if [ -f "Home.py" ]; then
        MAIN_APP="Home.py"
    else
        # Look for any .py files in the current directory
        MAIN_APP=$(find . -maxdepth 1 -name "*.py" | head -1)
        if [ -z "$MAIN_APP" ]; then
            echo -e "${YELLOW}No Python files found. Please enter the main application file name:${NC}"
            read -p "Enter filename: " MAIN_APP
        fi
    fi
    
    echo -e "${GREEN}Starting application: $MAIN_APP${NC}"
    streamlit run "$MAIN_APP"
fi 