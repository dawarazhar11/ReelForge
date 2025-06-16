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
echo -e "${BLUE}│  ${GREEN}AI Money Printer - Ollama Installation${BLUE}       │${NC}"
echo -e "${BLUE}└───────────────────────────────────────────────┘${NC}"
echo ""

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✅ Ollama is already installed.${NC}"
    OLLAMA_INSTALLED=true
else
    echo -e "${YELLOW}Ollama is not installed. Installing now...${NC}"
    OLLAMA_INSTALLED=false
    
    # Check if we're on macOS
    if [[ "$(uname)" == "Darwin" ]]; then
        # Check if Homebrew is installed
        if command -v brew &> /dev/null; then
            echo -e "${GREEN}Homebrew is installed. Using it to install Ollama...${NC}"
            brew install ollama
        else
            echo -e "${YELLOW}Homebrew is not installed. Installing Ollama using curl...${NC}"
            curl -fsSL https://ollama.com/install.sh | sh
        fi
    else
        # For Linux or other systems
        echo -e "${YELLOW}Installing Ollama using curl...${NC}"
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    # Check if installation was successful
    if command -v ollama &> /dev/null; then
        echo -e "${GREEN}✅ Ollama installed successfully.${NC}"
        OLLAMA_INSTALLED=true
    else
        echo -e "${RED}❌ Failed to install Ollama. Please install it manually from https://ollama.com${NC}"
        OLLAMA_INSTALLED=false
    fi
fi

# Check if Ollama service is running
if $OLLAMA_INSTALLED; then
    echo -e "${YELLOW}Checking if Ollama service is running...${NC}"
    
    # Try to list models to check if service is running
    if ollama list &> /dev/null; then
        echo -e "${GREEN}✅ Ollama service is running.${NC}"
        OLLAMA_RUNNING=true
    else
        echo -e "${YELLOW}Starting Ollama service...${NC}"
        
        # Start Ollama service
        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS
            open -a Ollama
            # Wait for service to start
            echo -e "${YELLOW}Waiting for Ollama service to start (this may take a few seconds)...${NC}"
            sleep 5
        else
            # Linux
            ollama serve &
            echo -e "${YELLOW}Waiting for Ollama service to start (this may take a few seconds)...${NC}"
            sleep 5
        fi
        
        # Check again if service is running
        if ollama list &> /dev/null; then
            echo -e "${GREEN}✅ Ollama service started successfully.${NC}"
            OLLAMA_RUNNING=true
        else
            echo -e "${RED}❌ Failed to start Ollama service. Please start it manually.${NC}"
            echo -e "${YELLOW}On macOS: Open the Ollama application from your Applications folder${NC}"
            echo -e "${YELLOW}On Linux: Run 'ollama serve' in a terminal${NC}"
            OLLAMA_RUNNING=false
        fi
    fi
fi

# Pull the required model if Ollama is running
if $OLLAMA_INSTALLED && $OLLAMA_RUNNING; then
    MODEL_NAME="mistral:7b-instruct-v0.3-q4_K_M"
    
    echo -e "${YELLOW}Checking if model '${MODEL_NAME}' is already downloaded...${NC}"
    
    # Check if model exists
    if ollama list | grep -q "$MODEL_NAME"; then
        echo -e "${GREEN}✅ Model '${MODEL_NAME}' is already downloaded.${NC}"
    else
        echo -e "${YELLOW}Pulling model '${MODEL_NAME}'...${NC}"
        echo -e "${YELLOW}This may take some time depending on your internet connection.${NC}"
        echo -e "${YELLOW}The model is approximately 4-5GB in size.${NC}"
        
        # Pull the model
        ollama pull "$MODEL_NAME"
        
        # Check if model was pulled successfully
        if ollama list | grep -q "$MODEL_NAME"; then
            echo -e "${GREEN}✅ Model '${MODEL_NAME}' downloaded successfully.${NC}"
        else
            echo -e "${RED}❌ Failed to download model '${MODEL_NAME}'.${NC}"
            echo -e "${YELLOW}You can try to download it manually using:${NC}"
            echo -e "   ollama pull $MODEL_NAME"
            echo -e ""
            echo -e "${YELLOW}Common issues:${NC}"
            echo -e "1. Insufficient disk space (need at least 10GB free)"
            echo -e "2. Slow or unstable internet connection"
            echo -e "3. Ollama service stopped during download"
            echo -e ""
            echo -e "${YELLOW}If you continue to have issues, you can:${NC}"
            echo -e "1. Try again later"
            echo -e "2. Use a different model by editing the .env file"
            echo -e "3. Connect to a remote Ollama server instead"
        fi
    fi
else
    echo -e "${YELLOW}Skipping model download since Ollama service is not running.${NC}"
    echo -e "${YELLOW}After starting the Ollama service, you can download the model manually:${NC}"
    echo -e "   ollama pull mistral:7b-instruct-v0.3-q4_K_M"
fi

# Create .command version for macOS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND_FILE="${SCRIPT_DIR}/install_ollama.command"
cp "$0" "$COMMAND_FILE"
chmod +x "$COMMAND_FILE"

echo ""
echo -e "${GREEN}Ollama setup process complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Configure your Ollama server address using 'configure_servers.command'"
echo -e "2. If you installed Ollama locally, set the address to 'http://localhost' with port '11434'"
echo -e "3. Restart the application to apply changes"
echo "" 