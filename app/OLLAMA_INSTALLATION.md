# AI Money Printer - Ollama Installation

This document explains how to install Ollama and the required model for AI Money Printer.

## Quick Start

1. Double-click the `install_ollama.command` file to run the installation utility
2. The script will install Ollama if it's not already installed
3. It will then download the required model (`mistral:7b-instruct-v0.3-q4_K_M`)
4. After installation, configure the server address using `configure_servers.command`

## Manual Installation

If the automatic installation doesn't work, you can follow these manual steps:

### 1. Install Ollama

#### macOS
```bash
# Using Homebrew
brew install ollama

# Or using the installer script
curl -fsSL https://ollama.com/install.sh | sh
```

#### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Start Ollama Service

- On macOS, open the Ollama application from your Applications folder
- On Linux, run `ollama serve` in a terminal

### 3. Pull the Required Model

```bash
ollama pull mistral:7b-instruct-v0.3-q4_K_M
```

Note: The model is approximately 4-5GB in size and may take some time to download depending on your internet connection.

## Configure Server Address

After installing Ollama locally, you need to configure AI Money Printer to use your local Ollama instance:

1. Double-click the `configure_servers.command` file
2. Choose option 2: "Use standard local settings" 
   - This will set Ollama to `http://localhost:11434`
   - And ComfyUI to `127.0.0.1:8188`
3. Alternatively, you can choose option 3 to enter custom settings
4. Restart the application to apply the changes

## Troubleshooting

If you encounter issues:

1. **Ollama not found**: Make sure Ollama is installed and in your PATH
2. **Service not running**: Make sure the Ollama service is running
3. **Model download fails**: Check your internet connection and try again
4. **Connection issues**: Ensure the server address is configured correctly

## System Requirements

- macOS 10.15 or later, or a compatible Linux distribution
- At least 8GB of RAM (16GB recommended)
- At least 10GB of free disk space for the model
- Internet connection for downloading the model 