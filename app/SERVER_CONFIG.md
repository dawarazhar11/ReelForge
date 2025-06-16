# AI Money Printer - Server Configuration

This document explains how to configure the AI Money Printer application to connect to Ollama and ComfyUI servers running on different machines or ports.

## Quick Start

1. Double-click the `configure_servers.command` file to run the configuration utility
2. Choose from the available configuration options:
   - Option 1: Keep current settings
   - Option 2: Use standard local settings (recommended for local installations)
   - Option 3: Enter custom settings manually
   - Option 4: Use custom remote settings (100.115.243.42)
3. Choose whether to test the connections
4. Restart the application to apply the new settings

## Installing Ollama Locally

If you don't have an Ollama server available, you can install it locally:

1. Double-click the `install_ollama.command` file to install Ollama and the required model
2. After installation, configure the server address to use your local Ollama instance (Option 2)
3. See [OLLAMA_INSTALLATION.md](OLLAMA_INSTALLATION.md) for detailed instructions

## Default Server Configuration

By default, the application can use these server addresses:

- **Standard Local Settings (Option 2):**
  - Ollama Server: http://localhost:11434
  - ComfyUI Server: 127.0.0.1:8188

- **Custom Remote Settings (Option 4):**
  - Ollama Server: http://100.115.243.42:11434
  - ComfyUI Server: 100.115.243.42:8000

## Manual Configuration

You can also manually edit the `.env` file in the application directory to set the server addresses:

```
# AI Money Printer Server Configuration

# Ollama Server Configuration
OLLAMA_HOST="http://localhost"
OLLAMA_PORT="11434"

# ComfyUI Server Configuration
COMFYUI_HOST="127.0.0.1"
COMFYUI_PORT="8188"
```

## Local Server Configuration

If you're running Ollama and ComfyUI on the same machine as the application, use:

```
# Ollama Server Configuration
OLLAMA_HOST="http://localhost"
OLLAMA_PORT="11434"

# ComfyUI Server Configuration
COMFYUI_HOST="localhost"
COMFYUI_PORT="8000"
```

## Troubleshooting

If you're having connection issues:

1. Ensure the Ollama and ComfyUI servers are running
2. Check firewall settings to ensure the ports are accessible
3. For servers on remote machines, ensure the IP address is correct and the machine is accessible
4. Use the "Test connections" option in the configuration utility to verify connectivity

## Advanced: Using Environment Variables

You can also set these configuration values using environment variables before running the application:

```
export OLLAMA_HOST="http://your-ollama-server"
export OLLAMA_PORT="11434"
export COMFYUI_HOST="your-comfyui-server"
export COMFYUI_PORT="8000"
```

Then start the application normally. 