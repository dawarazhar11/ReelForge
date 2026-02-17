"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# --- ComfyUI Configuration ---
COMFYUI_IMAGE_API_URL = os.getenv("COMFYUI_IMAGE_API_URL", "http://127.0.0.1:8000")
COMFYUI_VIDEO_API_URL = os.getenv("COMFYUI_VIDEO_API_URL", "http://127.0.0.1:8001")
COMFYUI_WS_HOST = os.getenv("COMFYUI_WS_HOST", "127.0.0.1")
COMFYUI_WS_PORT = os.getenv("COMFYUI_WS_PORT", "8000")

# --- Ollama Configuration ---
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://127.0.0.1:11434/api")

# --- HeyGen Configuration ---
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")

# --- Replicate Configuration ---
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# --- Paths ---
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent
WORKFLOWS_DIR = APP_DIR / "workflows"
FONTS_DIR = APP_DIR / "fonts"
MEDIA_DIR = APP_DIR / "media"
USER_DATA_DIR = APP_DIR / "config" / "user_data"
