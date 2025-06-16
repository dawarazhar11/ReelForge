#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}┌───────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Fixed Distribution Package${BLUE}  │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────┘${NC}"
echo ""

# Ensure all scripts are executable
chmod +x *.sh fix_moviepy.py clear_broll_cache.py fix_assembly_sequence.py manual_start.command 2>/dev/null || true

# Check if required tools are installed
if ! command -v zip &> /dev/null; then
    echo -e "${YELLOW}Installing zip utility...${NC}"
    brew install zip
fi

# Ask for main application file
MAIN_APP_FILE="Home.py"
if [ ! -f "$MAIN_APP_FILE" ]; then
    echo -e "${RED}Warning: Home.py not found. Please specify your main application file:${NC}"
    read -p "Enter the main application filename: " MAIN_APP_FILE
    
    if [ ! -f "$MAIN_APP_FILE" ]; then
        echo -e "${RED}Error: File not found. Cannot continue.${NC}"
        exit 1
    fi
fi

# Create distribution directory
DIST_DIR="dist_package"
mkdir -p "$DIST_DIR"

echo -e "${YELLOW}Creating fixed distribution package...${NC}"

# Copy required files
echo -e "${YELLOW}Copying application files...${NC}"

# Essential files to include
cp setup_mac.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: setup_mac.sh not found${NC}"
cp run_app.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: run_app.sh not found${NC}"
cp start.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: start.sh not found${NC}"
cp build_macos_app.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: build_macos_app.sh not found${NC}"
cp setup.py "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: setup.py not found${NC}"
cp README.md "$DIST_DIR/" 2>/dev/null || echo -e "${YELLOW}Warning: README.md not found${NC}"
cp manual_start.command "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: manual_start.command not found${NC}"

# Copy the fix scripts
cp fix_dependencies.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: fix_dependencies.sh not found${NC}"
cp fix_moviepy.py "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: fix_moviepy.py not found${NC}"
cp clear_broll_cache.py "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: clear_broll_cache.py not found${NC}"
cp refresh_broll.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: refresh_broll.sh not found${NC}"
cp fix_assembly_sequence.py "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: fix_assembly_sequence.py not found${NC}"
cp fix_repeated_segments.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: fix_repeated_segments.sh not found${NC}"
cp install_video_deps.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: install_video_deps.sh not found${NC}"
cp fix_whisper.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: fix_whisper.sh not found${NC}"
cp complete_installer.sh "$DIST_DIR/" 2>/dev/null || echo -e "${RED}Warning: complete_installer.sh not found${NC}"

# Copy the main application file
if [ -f "$MAIN_APP_FILE" ]; then
    # Get the filename without path
    MAIN_APP_FILENAME=$(basename "$MAIN_APP_FILE")
    
    # Copy the file
    cp "$MAIN_APP_FILE" "$DIST_DIR/$MAIN_APP_FILENAME"
    echo -e "${GREEN}Copied main application file: $MAIN_APP_FILENAME${NC}"
    
    # Update run_app.sh to use the correct filename
    if [ -f "$DIST_DIR/run_app.sh" ]; then
        sed -i '' "s/streamlit run [A-Za-z0-9_]*.py/streamlit run $MAIN_APP_FILENAME/g" "$DIST_DIR/run_app.sh"
        echo -e "${GREEN}Updated run_app.sh to use $MAIN_APP_FILENAME${NC}"
    fi
    
    # Update setup.py to use the correct filename
    if [ -f "$DIST_DIR/setup.py" ]; then
        sed -i '' "s/APP = \['[A-Za-z0-9_]*.py'\]/APP = \['$MAIN_APP_FILENAME'\]/g" "$DIST_DIR/setup.py"
        echo -e "${GREEN}Updated setup.py to use $MAIN_APP_FILENAME${NC}"
    fi
    
    # Update build_macos_app.sh to use the correct filename
    if [ -f "$DIST_DIR/build_macos_app.sh" ]; then
        sed -i '' "s/[A-Za-z0-9_]*.py/$MAIN_APP_FILENAME/g" "$DIST_DIR/build_macos_app.sh"
        echo -e "${GREEN}Updated build_macos_app.sh to use $MAIN_APP_FILENAME${NC}"
    fi
else
    echo -e "${RED}Error: Main application file not found. Distribution will be incomplete.${NC}"
    exit 1
fi

# Copy directories if they exist
for dir in assets utils components pages models services config; do
    if [ -d "$dir" ]; then
        cp -R "$dir" "$DIST_DIR/"
        echo -e "${GREEN}Copied directory: $dir${NC}"
    fi
done

# Copy requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    cp requirements.txt "$DIST_DIR/"
    echo -e "${GREEN}Copied requirements.txt${NC}"
else
    # Create a basic requirements.txt if none exists
    echo -e "${YELLOW}Creating basic requirements.txt...${NC}"
    cat > "$DIST_DIR/requirements.txt" << EOL
streamlit>=1.30.0
pillow>=10.0.0
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
pydub>=0.25.1
moviepy>=1.0.3
python-dotenv>=1.0.0
requests>=2.28.1
opencv-python>=4.7.0
websocket-client>=1.6.0
ffmpeg-python>=0.2.0
EOL
fi

# Create a simple install script
cat > "$DIST_DIR/install.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
./setup_mac.sh
EOL
chmod +x "$DIST_DIR/install.command"

# Create a comprehensive install script
cat > "$DIST_DIR/complete_install.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
./complete_installer.sh
EOL
chmod +x "$DIST_DIR/complete_install.command"

# Create a quick fix script
cat > "$DIST_DIR/fix_app.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Running dependency fix script..."
./fix_dependencies.sh
EOL
chmod +x "$DIST_DIR/fix_app.command"

# Create a B-roll refresh script
cat > "$DIST_DIR/refresh_broll.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Running B-Roll cache refresh script..."
./refresh_broll.sh
EOL
chmod +x "$DIST_DIR/refresh_broll.command"

# Create a fix repeated segments script
cat > "$DIST_DIR/fix_repeated_segments.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Running fix for repeated segments..."
./fix_repeated_segments.sh
EOL
chmod +x "$DIST_DIR/fix_repeated_segments.command"

# Create a video dependencies installer script
cat > "$DIST_DIR/install_video_deps.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Running video dependencies installer..."
./install_video_deps.sh
EOL
chmod +x "$DIST_DIR/install_video_deps.command"

# Create a Whisper fix script
cat > "$DIST_DIR/fix_whisper.command" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Running Whisper fix installer..."
./fix_whisper.sh
EOL
chmod +x "$DIST_DIR/fix_whisper.command"

# Create ZIP archive
VERSION=$(date +"%Y%m%d")
ZIP_NAME="AI_Money_Printer_Fixed_${VERSION}.zip"

echo -e "${YELLOW}Creating ZIP archive: $ZIP_NAME...${NC}"
cd "$DIST_DIR"
zip -r "../$ZIP_NAME" ./*
cd ..

echo -e "${GREEN}Fixed distribution package created successfully: ${YELLOW}$ZIP_NAME${NC}"
echo -e "${YELLOW}Instructions for users:${NC}"
echo -e "1. Unzip the archive"
echo -e "2. Double-click complete_install.command for a full installation including Homebrew and Python"
echo -e "3. OR double-click install.command for a standard installation (requires Python)"
echo -e "4. If the app doesn't start automatically, double-click manual_start.command"
echo -e "5. If you encounter dependency issues, double-click fix_app.command"
echo -e "6. If B-roll content isn't showing correctly, double-click refresh_broll.command"
echo -e "7. If the first segment repeats at the end, double-click fix_repeated_segments.command"
echo -e "8. If you have issues with Whisper/captioning, double-click fix_whisper.command"

# Cleanup
echo -e "${YELLOW}Cleaning up temporary files...${NC}"
rm -rf "$DIST_DIR"

echo -e "${GREEN}All done!${NC}" 