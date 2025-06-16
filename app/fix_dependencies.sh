#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== AI Money Printer - Dependency Fix Script ===${NC}"
echo -e "${YELLOW}This script will fix the moviepy and other dependency issues${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "Home.py" ]; then
    echo -e "${RED}Error: Home.py not found in current directory.${NC}"
    echo -e "${YELLOW}Please run this script from the application directory.${NC}"
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}FFmpeg not found. Installing FFmpeg using Homebrew...${NC}"
    brew install ffmpeg
    
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${RED}Failed to install FFmpeg with Homebrew.${NC}"
        echo -e "${YELLOW}Trying alternative method...${NC}"
        pip install ffmpeg-python
    fi
fi

# Check if virtualenv exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Found virtual environment. Activating...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}Creating new virtual environment...${NC}"
    pip3 install virtualenv
    python3 -m virtualenv venv
    source venv/bin/activate
fi

# Install critical dependencies directly
echo -e "${YELLOW}Installing critical dependencies...${NC}"
pip install --upgrade pip
pip install moviepy==1.0.3
pip install pydub==0.25.1
pip install opencv-python==4.7.0
pip install matplotlib==3.7.0
pip install pandas==2.0.0
pip install python-dotenv==1.0.0
pip install streamlit==1.30.0
pip install ffmpeg-python

# Verify moviepy installation
echo -e "${YELLOW}Verifying moviepy installation...${NC}"
if python3 -c "import moviepy.editor" 2>/dev/null; then
    echo -e "${GREEN}moviepy is now properly installed!${NC}"
else
    echo -e "${RED}Still having issues with moviepy.${NC}"
    echo -e "${YELLOW}Trying alternative installation method...${NC}"
    pip uninstall -y moviepy
    pip install moviepy --no-cache-dir
    
    # Check again
    if python3 -c "import moviepy.editor" 2>/dev/null; then
        echo -e "${GREEN}moviepy is now properly installed!${NC}"
    else
        echo -e "${RED}Failed to install moviepy. Please try manually:${NC}"
        echo "pip install moviepy==1.0.3"
    fi
fi

# Create a test script to verify moviepy
echo -e "${YELLOW}Creating test script for moviepy...${NC}"
cat > test_moviepy.py << EOL
try:
    import moviepy.editor as mp
    print("MoviePy successfully imported!")
    print(f"MoviePy version: {mp.__version__}")
except ImportError as e:
    print(f"Error importing MoviePy: {e}")
EOL

# Run the test script
echo -e "${YELLOW}Running test script...${NC}"
python test_moviepy.py

echo -e "${GREEN}Fix complete! You can now try running the app again.${NC}"
echo -e "${YELLOW}To run the app, use: ./run_app.sh${NC}" 