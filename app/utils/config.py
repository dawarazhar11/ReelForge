import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f".env file not found at {env_path}. Using default values or environment variables.")

# Server configuration with defaults
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://100.115.243.42')
OLLAMA_PORT = os.getenv('OLLAMA_PORT', '11434')
COMFYUI_HOST = os.getenv('COMFYUI_HOST', '100.115.243.42')
COMFYUI_PORT = os.getenv('COMFYUI_PORT', '8000')

# Constructed URLs
OLLAMA_API_URL = f"{OLLAMA_HOST}:{OLLAMA_PORT}"
if not OLLAMA_API_URL.startswith('http'):
    OLLAMA_API_URL = f"http://{OLLAMA_API_URL}"

COMFYUI_API_URL = f"{COMFYUI_HOST}:{COMFYUI_PORT}"
if not COMFYUI_API_URL.startswith('http'):
    COMFYUI_API_URL = f"http://{COMFYUI_API_URL}"

# Log the configured URLs
logger.info(f"Ollama API URL: {OLLAMA_API_URL}")
logger.info(f"ComfyUI API URL: {COMFYUI_API_URL}")

def get_ollama_api_url():
    """Get the Ollama API URL from environment variables"""
    return OLLAMA_API_URL

def get_comfyui_api_url():
    """Get the ComfyUI API URL from environment variables"""
    return COMFYUI_API_URL

def get_comfyui_host():
    """Get the ComfyUI host from environment variables"""
    return COMFYUI_HOST

def get_comfyui_port():
    """Get the ComfyUI port from environment variables"""
    return COMFYUI_PORT 