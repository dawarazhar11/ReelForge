# AI Money Printer - Complete Ollama Setup Guide

This guide will walk you through the complete process of setting up Ollama for use with AI Money Printer.

## Step 1: Install Ollama and the Required Model

First, you need to install Ollama and download the required model:

1. Double-click `install_ollama.command`
2. The script will:
   - Install Ollama if it's not already installed
   - Start the Ollama service
   - Download the required model (`mistral:7b-instruct-v0.3-q4_K_M`)

## Step 2: Configure Server Addresses

After installing Ollama locally, you need to configure AI Money Printer to use your local instance:

1. Double-click `configure_servers.command`
2. Select option 2: "Use standard local settings"
   - This will set Ollama to `http://localhost:11434`
   - And ComfyUI to `127.0.0.1:8188`
3. If you're using a remote server, select option 4 or enter custom settings with option 3

## Step 3: Test the Connection

The configuration script will offer to test the connections to your servers. This helps verify that everything is set up correctly.

## Step 4: Restart the Application

After configuring the server addresses, restart the application to apply the changes.

## Troubleshooting

### Ollama Installation Issues

- **Homebrew errors**: Try the direct installation method with `curl -fsSL https://ollama.com/install.sh | sh`
- **Permission errors**: You may need to run the installation with sudo
- **Service not starting**: Try starting Ollama manually from the Applications folder

### Model Download Issues

- **Download fails**: Check your internet connection and try again
- **Insufficient space**: Ensure you have at least 10GB of free disk space
- **Timeout errors**: Large model downloads may take time; try again on a faster connection

### Connection Issues

- **Connection refused**: Ensure the Ollama service is running
- **Wrong address**: Double-check the host and port in your configuration
- **Firewall blocking**: Check if a firewall is blocking the connection

## Advanced: Using a Different Model

If you want to use a different model:

1. Download it with `ollama pull <model-name>`
2. Edit the DEFAULT_MODEL variable in `utils/ai/ollama_client.py`

## Need More Help?

- See [OLLAMA_INSTALLATION.md](OLLAMA_INSTALLATION.md) for detailed installation instructions
- See [SERVER_CONFIG.md](SERVER_CONFIG.md) for detailed server configuration instructions
- Visit [ollama.com](https://ollama.com) for more information about Ollama 