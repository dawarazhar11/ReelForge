#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
clear
echo -e "${BLUE}┌───────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Server Configuration${BLUE}      │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────┘${NC}"
echo ""

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# Check if .env file exists, create if not
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Creating new .env file...${NC}"
    touch "$ENV_FILE"
else
    echo -e "${YELLOW}Updating existing .env file...${NC}"
    # Backup the existing file
    cp "$ENV_FILE" "${ENV_FILE}.backup"
    echo -e "${GREEN}Backed up existing .env file to ${ENV_FILE}.backup${NC}"
fi

# Current settings
if [ -f "$ENV_FILE" ]; then
    # Extract values from .env file
    CURRENT_OLLAMA_HOST=$(grep -E "^OLLAMA_HOST=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    CURRENT_OLLAMA_PORT=$(grep -E "^OLLAMA_PORT=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    CURRENT_COMFYUI_HOST=$(grep -E "^COMFYUI_HOST=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    CURRENT_COMFYUI_PORT=$(grep -E "^COMFYUI_PORT=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
fi

# Default values if not found
CURRENT_OLLAMA_HOST="${CURRENT_OLLAMA_HOST:-http://100.115.243.42}"
CURRENT_OLLAMA_PORT="${CURRENT_OLLAMA_PORT:-11434}"
CURRENT_COMFYUI_HOST="${CURRENT_COMFYUI_HOST:-100.115.243.42}"
CURRENT_COMFYUI_PORT="${CURRENT_COMFYUI_PORT:-8000}"

# Display current settings
echo -e "${YELLOW}Current server configurations:${NC}"
echo -e "  Ollama Server: ${GREEN}${CURRENT_OLLAMA_HOST}:${CURRENT_OLLAMA_PORT}${NC}"
echo -e "  ComfyUI Server: ${GREEN}${CURRENT_COMFYUI_HOST}:${CURRENT_COMFYUI_PORT}${NC}"
echo ""

# Show configuration options
echo -e "${YELLOW}Configuration options:${NC}"
echo -e "1. Use current settings"
echo -e "2. Use standard local settings (recommended for local installations)"
echo -e "   - Ollama: http://localhost:11434"
echo -e "   - ComfyUI: 127.0.0.1:8188"
echo -e "3. Use custom settings (enter manually)"
echo -e "4. Use custom remote settings (100.115.243.42)"
echo -e "   - Ollama: http://100.115.243.42:11434"
echo -e "   - ComfyUI: 100.115.243.42:8000"
echo ""

# Ask for configuration choice
read -p "Enter your choice (1-4): " CONFIG_CHOICE

case $CONFIG_CHOICE in
    1)
        # Keep current settings
        OLLAMA_HOST="$CURRENT_OLLAMA_HOST"
        OLLAMA_PORT="$CURRENT_OLLAMA_PORT"
        COMFYUI_HOST="$CURRENT_COMFYUI_HOST"
        COMFYUI_PORT="$CURRENT_COMFYUI_PORT"
        echo -e "${GREEN}Keeping current settings.${NC}"
        ;;
    2)
        # Use standard local settings
        OLLAMA_HOST="http://localhost"
        OLLAMA_PORT="11434"
        COMFYUI_HOST="127.0.0.1"
        COMFYUI_PORT="8188"
        echo -e "${GREEN}Using standard local settings.${NC}"
        ;;
    3)
        # Custom settings - ask for each value
        echo -e "${YELLOW}Enter new server configurations:${NC}"
        echo ""

        # Ollama settings
        echo -e "${BLUE}Ollama Server Configuration:${NC}"
        read -p "Ollama host (e.g., http://localhost or http://100.115.243.42) [${CURRENT_OLLAMA_HOST}]: " OLLAMA_HOST_INPUT
        read -p "Ollama port (e.g., 11434) [${CURRENT_OLLAMA_PORT}]: " OLLAMA_PORT_INPUT

        # ComfyUI settings
        echo -e "${BLUE}ComfyUI Server Configuration:${NC}"
        read -p "ComfyUI host (e.g., 127.0.0.1 or 100.115.243.42) [${CURRENT_COMFYUI_HOST}]: " COMFYUI_HOST_INPUT
        read -p "ComfyUI port (e.g., 8188 or 8000) [${CURRENT_COMFYUI_PORT}]: " COMFYUI_PORT_INPUT

        # Use default values if no input
        OLLAMA_HOST="${OLLAMA_HOST_INPUT:-$CURRENT_OLLAMA_HOST}"
        OLLAMA_PORT="${OLLAMA_PORT_INPUT:-$CURRENT_OLLAMA_PORT}"
        COMFYUI_HOST="${COMFYUI_HOST_INPUT:-$CURRENT_COMFYUI_HOST}"
        COMFYUI_PORT="${COMFYUI_PORT_INPUT:-$CURRENT_COMFYUI_PORT}"
        ;;
    4)
        # Use custom remote settings
        OLLAMA_HOST="http://100.115.243.42"
        OLLAMA_PORT="11434"
        COMFYUI_HOST="100.115.243.42"
        COMFYUI_PORT="8000"
        echo -e "${GREEN}Using custom remote settings (100.115.243.42).${NC}"
        ;;
    *)
        # Invalid choice - keep current settings
        echo -e "${RED}Invalid choice. Keeping current settings.${NC}"
        OLLAMA_HOST="$CURRENT_OLLAMA_HOST"
        OLLAMA_PORT="$CURRENT_OLLAMA_PORT"
        COMFYUI_HOST="$CURRENT_COMFYUI_HOST"
        COMFYUI_PORT="$CURRENT_COMFYUI_PORT"
        ;;
esac

# Update .env file
echo "# AI Money Printer Server Configuration" > "$ENV_FILE"
echo "# Generated on $(date)" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"
echo "# Ollama Server Configuration" >> "$ENV_FILE"
echo "OLLAMA_HOST=\"$OLLAMA_HOST\"" >> "$ENV_FILE"
echo "OLLAMA_PORT=\"$OLLAMA_PORT\"" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"
echo "# ComfyUI Server Configuration" >> "$ENV_FILE"
echo "COMFYUI_HOST=\"$COMFYUI_HOST\"" >> "$ENV_FILE"
echo "COMFYUI_PORT=\"$COMFYUI_PORT\"" >> "$ENV_FILE"

# Make the file executable
chmod +x "$ENV_FILE"

echo ""
echo -e "${GREEN}Server configurations updated successfully!${NC}"
echo -e "${GREEN}Settings saved to ${ENV_FILE}${NC}"
echo ""
echo -e "${YELLOW}New server configurations:${NC}"
echo -e "  Ollama Server: ${GREEN}${OLLAMA_HOST}:${OLLAMA_PORT}${NC}"
echo -e "  ComfyUI Server: ${GREEN}${COMFYUI_HOST}:${COMFYUI_PORT}${NC}"
echo ""

# Create .command version for macOS
COMMAND_FILE="${SCRIPT_DIR}/configure_servers.command"
cp "$0" "$COMMAND_FILE"
chmod +x "$COMMAND_FILE"
echo -e "${GREEN}Created macOS clickable file: configure_servers.command${NC}"
echo -e "${YELLOW}You can double-click this file to reconfigure servers in the future.${NC}"
echo ""

# Ask if user wants to test the connections
echo -e "${YELLOW}Do you want to test the connections to these servers? (y/n)${NC}"
read -p "Test connections? " TEST_CONNECTIONS_INPUT

if [[ "$TEST_CONNECTIONS_INPUT" == "y" || "$TEST_CONNECTIONS_INPUT" == "Y" ]]; then
    echo -e "${BLUE}Testing Ollama server connection...${NC}"
    OLLAMA_URL="${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags"
    
    # Remove http:// for curl if it exists
    CURL_URL="$OLLAMA_URL"
    if [[ "$CURL_URL" != http* ]]; then
        CURL_URL="http://$CURL_URL"
    fi
    
    if curl -s --head --request GET "$CURL_URL" | grep "200 OK" > /dev/null; then
        echo -e "${GREEN}✅ Ollama server is accessible at ${CURL_URL}${NC}"
    else
        echo -e "${RED}❌ Could not connect to Ollama server at ${CURL_URL}${NC}"
        echo -e "${YELLOW}Make sure the Ollama server is running and the address is correct.${NC}"
    fi
    
    echo -e "${BLUE}Testing ComfyUI server connection...${NC}"
    COMFYUI_URL="http://${COMFYUI_HOST}:${COMFYUI_PORT}"
    
    if curl -s --head --request GET "$COMFYUI_URL" | grep "200 OK" > /dev/null; then
        echo -e "${GREEN}✅ ComfyUI server is accessible at ${COMFYUI_URL}${NC}"
    else
        echo -e "${RED}❌ Could not connect to ComfyUI server at ${COMFYUI_URL}${NC}"
        echo -e "${YELLOW}Make sure the ComfyUI server is running and the address is correct.${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Configuration complete!${NC}"
echo -e "${YELLOW}Please restart the application to apply the new server configurations.${NC}"
echo "" 