import streamlit as st

# Set page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="B-Roll Video Production | AI Money Printer",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

import os
import sys
import json
import requests
import time
from pathlib import Path
import base64
import threading
from datetime import datetime
import random
import traceback
import copy
import uuid
import logging
import tempfile
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import custom helper module for ComfyUI integration
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app"))
import comfyui_helpers

# Fix import paths for components and utilities
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"Added {parent_dir} to path")

# Try to import local modules
try:
    from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation, render_step_navigation
    from components.progress import render_step_header
    from utils.session_state import get_settings, get_project_path, mark_step_complete
    from utils.progress_tracker import start_comfyui_tracking
    from utils.video.assembly import render_video, extract_audio, download_video
    from utils.fonts.text_effects import add_captions_to_video
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Failed to import local modules: {str(e)}")
    st.stop()

# Try to import the new ComfyUI WebSocket client
try:
    from utils.ai.comfyui_websocket import (
        load_workflow_file,
        modify_workflow,
        submit_workflow,
        get_output_images,
        wait_for_prompt_completion,
        check_prompt_status
    )
    COMFYUI_WEBSOCKET_AVAILABLE = True
    # Use info after imports to avoid Streamlit error
    websocket_status = "ComfyUI WebSocket client available. Using WebSocket API for improved stability."
except ImportError:
    COMFYUI_WEBSOCKET_AVAILABLE = False
    # Use warning after imports to avoid Streamlit error
    websocket_status = "ComfyUI WebSocket client not available. Using fallback HTTP API."

# Load custom CSS
def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Display WebSocket status after page config
if COMFYUI_WEBSOCKET_AVAILABLE:
    st.info(websocket_status)
else:
    st.warning(websocket_status)

# Style for horizontal navigation
st.markdown("""
<style>
    .horizontal-nav {
        margin-bottom: 20px;
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    
    .horizontal-nav button {
        background-color: transparent;
        border: none;
        font-size: 1.2rem;
        margin: 0 5px;
        transition: all 0.3s;
    }
    
    .horizontal-nav button:hover {
        transform: scale(1.2);
    }
</style>
""", unsafe_allow_html=True)

# Add horizontal navigation
st.markdown("<div class='horizontal-nav'>", unsafe_allow_html=True)
render_horizontal_navigation()
st.markdown("</div>", unsafe_allow_html=True)

# Apply custom CSS to fix sidebar text color
st.markdown("""
<style>
    /* Target sidebar with higher specificity */
    [data-testid="stSidebar"] {
        background-color: white !important;
    }
    
    /* Ensure all text inside sidebar is black */
    [data-testid="stSidebar"] * {
        color: black !important;
    }
    
    /* Make sidebar buttons light blue */
    [data-testid="stSidebar"] button {
        background-color: #e6f2ff !important; /* Light blue background */
        color: #0066cc !important; /* Darker blue text */
        border-radius: 6px !important;
    }
    
    /* Hover effect for sidebar buttons */
    [data-testid="stSidebar"] button:hover {
        background-color: #cce6ff !important; /* Slightly darker blue on hover */
    }
    
    /* Target specific sidebar elements with higher specificity */
    .st-emotion-cache-16txtl3, 
    .st-emotion-cache-16idsys, 
    .st-emotion-cache-7ym5gk,
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] span {
        color: black !important;
    }
    
    /* Target sidebar navigation specifically */
    section[data-testid="stSidebar"] > div > div > div > div > div > ul,
    section[data-testid="stSidebar"] > div > div > div > div > div > ul * {
        color: black !important;
    }
    
    /* Ensure sidebar background stays white even after loading */
    section[data-testid="stSidebar"] > div {
        background-color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Render navigation sidebar
render_custom_sidebar()

# Load settings
settings = get_settings()
project_path = get_project_path()

# Constants
OLLAMA_API_URL = "http://100.115.243.42:11434/api"
COMFYUI_IMAGE_API_URL = "http://100.115.243.42:8000"
COMFYUI_VIDEO_API_URL = "http://100.115.243.42:8000"
JSON_TEMPLATES = {
    "image": {
        "flux_schnell": "app/flux_schnell.json",  # Make flux_schnell the first option (default)
        "default": "app/image_homepc.json",
        "lora": "app/lora.json",
        "flux": "app/flux_dev_checkpoint.json"
    },
    "video": "app/wan.json"
}

# Initialize session state variables
if "segments" not in st.session_state:
    st.session_state.segments = []
if "broll_prompts" not in st.session_state:
    st.session_state.broll_prompts = {}
if "broll_type" not in st.session_state:
    st.session_state.broll_type = "video"  # Default to video if not specified
if "content_status" not in st.session_state:
    st.session_state.content_status = {
        "broll": {},
        "aroll": {}
    }
if "parallel_tasks" not in st.session_state:
    st.session_state.parallel_tasks = {
        "running": False,
        "completed": 0,
        "total": 0
    }
if "broll_fetch_ids" not in st.session_state:
    # Initialize with default B-Roll IDs
    st.session_state.broll_fetch_ids = {
        "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",  # SEG1
        "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257",  # SEG2
        "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"   # SEG3
    }
if "workflow_selection" not in st.session_state:
    st.session_state.workflow_selection = {
        "image": "default"
    }
if "manual_upload" not in st.session_state:
    st.session_state.manual_upload = False
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "batch_process_status" not in st.session_state:
    st.session_state.batch_process_status = {
        "submitted": False,
        "prompt_ids": {},
        "errors": {}
    }
if "debug_info" not in st.session_state:
    st.session_state.debug_info = []

# Function to load saved script and segments# Function to load saved script and segments (for B-Roll only)
def load_script_data():
    script_file = project_path / "script.json"
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                segments = data.get("segments", [])
                
                # Print debug info
                print(f"Debug - Loading script data: Found {len(segments)} segments in script.json")
                
                # Validate segments
                if not segments:
                    print("Warning: No segments found in script.json")
                    return False
                    
                # Count segments by type
                broll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll")
                other_count = len(segments) - broll_count
                
                print(f"Debug - Found {broll_count} B-Roll and {other_count} other segments")
                
                # Only update if we have valid B-Roll segments
                if broll_count > 0:
                    # Filter for B-Roll segments only
                    st.session_state.segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
                    return True
                else:
                    print("Warning: No valid B-Roll segments found in script.json")
                    return False
        except json.JSONDecodeError:
            print("Error: Failed to parse script.json")
            return False
    else:
        print(f"Warning: Script file not found at {script_file}")
        return False
# Function to load saved B-Roll prompts
def load_broll_prompts():
    prompts_file = project_path / "broll_prompts.json"
    if prompts_file.exists():
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                
                # Print debug info
                print(f"Debug - Loading B-Roll prompts: {prompts_file}")
                
                # Store the complete data structure for reference
                st.session_state.broll_prompts_full = data
                
                # Handle different data formats for backward compatibility
                if "prompts" in data:
                    st.session_state.broll_prompts = data
                    print(f"Debug - Found {len(data['prompts'])} prompts in nested structure")
                else:
                    st.session_state.broll_prompts = data
                    print(f"Debug - Found {len(data)} items in flat structure")
                
                # Load B-Roll type if available
                if "broll_type" in data:
                    st.session_state.broll_type = data["broll_type"]
                    print(f"Debug - B-Roll type from prompts: {st.session_state.broll_type}")
                
                # Load image template if available
                if "image_template" in data and data["image_template"]:
                    st.session_state.workflow_selection["image"] = data["image_template"]
                    print(f"Debug - Image template from prompts: {st.session_state.workflow_selection['image']}")
                
                return True
        except Exception as e:
            print(f"Error loading B-Roll prompts: {str(e)}")
            return False
    return False

# Function to load content status
def load_content_status():
    status_file = project_path / "content_status.json"
    if status_file.exists():
        try:
            with open(status_file, "r") as f:
                content_status = json.load(f)
                st.session_state.content_status = content_status
                
                # Also update broll_fetch_ids from content_status
                if "broll" in content_status:
                    for segment_id, segment_data in content_status["broll"].items():
                        if "prompt_id" in segment_data:
                            if "broll_fetch_ids" not in st.session_state:
                                st.session_state.broll_fetch_ids = {}
                            st.session_state.broll_fetch_ids[segment_id] = segment_data["prompt_id"]
                
            return True
        except json.JSONDecodeError:
            st.warning("Content status file exists but contains invalid JSON. Creating a new one.")
            # Initialize with default values
            st.session_state.content_status = {"broll": {}}
            save_content_status()
            return False
        except Exception as e:
            st.error(f"Error loading content status: {str(e)}")
            return False
    return False
# Function to save content status
def save_content_status():
    status_file = project_path / "content_status.json"
    with open(status_file, "w") as f:
        json.dump(st.session_state.content_status, f, indent=4)
    return True

# Function to update content status
def update_content_status(segment_id, segment_type, status, message=None, prompt_id=None, file_path=None, content_type=None, timestamp=None):
    """
    Update the content status for a specific segment
    
    Args:
        segment_id: ID of the segment (e.g., "segment_0")
        segment_type: Type of content ("aroll" or "broll")
        status: Status of the content generation ("complete", "error", "processing", "waiting", "fetching")
        message: Optional message to display (error message, progress info, etc.)
        prompt_id: Optional ID of the prompt submitted to ComfyUI
        file_path: Optional path to the generated file
        content_type: Optional type of content generated ("video" or "image")
        timestamp: Optional timestamp for the update
    """
    # Initialize content_status if it doesn't exist
    if "content_status" not in st.session_state:
        st.session_state.content_status = {
            "broll": {},
            "aroll": {}
        }
    
    # Initialize segment type if it doesn't exist
    if segment_type not in st.session_state.content_status:
        st.session_state.content_status[segment_type] = {}
    
    # Create or update status for the segment
    segment_status = {
        "status": status,
        "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add optional fields if provided
    if message:
        segment_status["message"] = message
    if prompt_id:
        segment_status["prompt_id"] = prompt_id
    if file_path:
        segment_status["file_path"] = file_path
    if content_type:
        segment_status["content_type"] = content_type
    
    # Update the status
    st.session_state.content_status[segment_type][segment_id] = segment_status
    
    # Save the updated status to file
    save_content_status()
    
    return True

# Function to replace template values in ComfyUI workflow JSON
def prepare_comfyui_workflow(template_file, prompt, negative_prompt, resolution="1080x1920"):
    try:
        # Load the template workflow
        with open(template_file, "r") as f:
            workflow = json.load(f)
        
        # Extract width and height from resolution
        width, height = map(int, resolution.split("x"))
        
        # Modify the workflow with our prompt and resolution
        # This depends on the specific structure of your workflow templates
        # The actual node IDs and parameter names will vary
        for node_id, node in workflow.items():
            if "inputs" in node:
                if "prompt" in node["inputs"]:
                    node["inputs"]["prompt"] = prompt
                if "negative" in node["inputs"]:
                    node["inputs"]["negative"] = negative_prompt
                if "text" in node["inputs"] and "CLIPTextEncode" in node.get("class_type", ""):
                    # Check for positive/negative prompt encoding nodes
                    if "Positive" in node.get("_meta", {}).get("title", ""):
                        node["inputs"]["text"] = prompt
                    elif "Negative" in node.get("_meta", {}).get("title", ""):
                        node["inputs"]["text"] = negative_prompt
                if "width" in node["inputs"]:
                    node["inputs"]["width"] = width
                if "height" in node["inputs"]:
                    node["inputs"]["height"] = height
        
        return workflow
    except FileNotFoundError:
        st.error(f"Error: Workflow template file not found: {template_file}")
        return None
    except json.JSONDecodeError:
        st.error(f"Error: Invalid JSON in workflow template: {template_file}")
        return None
    except Exception as e:
        st.error(f"Error preparing workflow: {str(e)}")
        return None

# Function to submit job to ComfyUI
def submit_comfyui_workflow(workflow):
    """
    Submit a workflow to ComfyUI server.
    
    Args:
        workflow: The ComfyUI workflow to submit
        
    Returns:
        Dictionary with prompt_id if successful, error message if failed
    """
    # If the WebSocket client is available, use it
    if COMFYUI_WEBSOCKET_AVAILABLE:
        try:
            # Determine which API URL to use based on the workflow type
            api_url = COMFYUI_VIDEO_API_URL
            
            # Log the workflow submission
            st.session_state.debug_info.append(f"Submitting workflow to {api_url} using WebSocket client")
            logger.info(f"Submitting workflow to {api_url} using WebSocket client")
            
            # Add more detailed debugging info
            print(f"DEBUG: Submitting workflow to {api_url}")
            print(f"DEBUG: Workflow node count: {len(workflow) if workflow else 'None'}")
            
            # Verify the workflow is valid before submitting
            if not workflow or not isinstance(workflow, dict) or len(workflow) == 0:
                error_msg = "Invalid workflow: Empty or not a dictionary"
                st.session_state.debug_info.append(error_msg)
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            # Submit the workflow
            prompt_id = submit_workflow(
                workflow,
                server_url=api_url,
                extra_data={"source": "ai_money_printer"}
            )
            
            if prompt_id:
                st.session_state.debug_info.append(f"Workflow submitted successfully. Prompt ID: {prompt_id}")
                logger.info(f"Workflow submitted successfully. Prompt ID: {prompt_id}")
                return {
                    "status": "success",
                    "prompt_id": prompt_id
                }
            else:
                error_msg = "Failed to submit workflow: No prompt ID returned"
                st.session_state.debug_info.append(error_msg)
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"Error submitting workflow via WebSocket: {str(e)}"
            st.session_state.debug_info.append(error_msg)
            logger.error(error_msg)
            print(f"DEBUG: Exception in WebSocket submission: {str(e)}")
            print(f"DEBUG: Falling back to HTTP API method")
            # Continue to fallback method
    
    # Fallback to the old HTTP API method
    try:
        # Create unique client_id for this session
        client_id = str(uuid.uuid4())
        
        # Prepare data
        data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        # Convert to JSON
        json_data = json.dumps(data).encode('utf-8')
        
        # Determine which API URL to use based on the workflow type
        api_url = COMFYUI_VIDEO_API_URL
        
        # Log the workflow submission
        st.session_state.debug_info.append(f"Submitting workflow to {api_url} using HTTP API")
        logger.info(f"Submitting workflow to {api_url} using HTTP API")
        print(f"DEBUG: Submitting workflow to {api_url} using HTTP API")
        
        # Add connection debugging
        try:
            # Test connection first
            connection_test = requests.get(f"{api_url}/history", timeout=5)
            print(f"DEBUG: Connection test status: {connection_test.status_code}")
            if connection_test.status_code != 200:
                print(f"DEBUG: Connection test failed with status {connection_test.status_code}")
        except Exception as conn_e:
            print(f"DEBUG: Connection test exception: {str(conn_e)}")
        
        # Send request with longer timeout
        response = requests.post(f"{api_url}/prompt", data=json_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")
            if prompt_id:
                st.session_state.debug_info.append(f"Workflow submitted successfully. Prompt ID: {prompt_id}")
                logger.info(f"Workflow submitted successfully. Prompt ID: {prompt_id}")
                return {
                    "status": "success",
                    "prompt_id": prompt_id
                }
            else:
                error_msg = "No prompt ID returned"
                st.session_state.debug_info.append(error_msg)
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg
                }
        else:
            error_msg = f"Error submitting workflow: Status code {response.status_code}, Response: {response.text}"
            st.session_state.debug_info.append(error_msg)
            logger.error(error_msg)
            print(f"DEBUG: HTTP response error: {response.status_code} - {response.text}")
            return {
                "status": "error",
                "error": error_msg
            }
    except requests.exceptions.ConnectionError as conn_err:
        error_msg = f"Connection error: Failed to connect to ComfyUI server at {api_url}. Please check if ComfyUI is running."
        st.session_state.debug_info.append(error_msg)
        logger.error(f"Connection error: {str(conn_err)}")
        print(f"DEBUG: Connection error: {str(conn_err)}")
        return {
            "status": "error",
            "error": error_msg
        }
    except requests.exceptions.Timeout as timeout_err:
        error_msg = f"Timeout error: ComfyUI server at {api_url} took too long to respond. The server might be busy."
        st.session_state.debug_info.append(error_msg)
        logger.error(f"Timeout error: {str(timeout_err)}")
        print(f"DEBUG: Timeout error: {str(timeout_err)}")
        return {
            "status": "error",
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error submitting workflow: {str(e)}"
        st.session_state.debug_info.append(error_msg)
        logger.error(error_msg)
        print(f"DEBUG: General exception: {str(e)}")
        return {
            "status": "error",
            "error": error_msg
        }

def check_comfyui_job_status(api_url, prompt_id):
    """
    Check the status of a ComfyUI job.
    
    Args:
        api_url: The ComfyUI API URL
        prompt_id: The prompt ID to check
        
    Returns:
        Dictionary with status information
    """
    # If the WebSocket client is available, use it
    if COMFYUI_WEBSOCKET_AVAILABLE:
        try:
            # Log the status check
            st.session_state.debug_info.append(f"Checking job status for prompt {prompt_id} using WebSocket client")
            logger.info(f"Checking job status for prompt {prompt_id} using WebSocket client")
            
            # Check the status
            status_info = check_prompt_status(prompt_id, server_url=api_url)
            
            # Log the result
            status = status_info.get("status", "unknown")
            st.session_state.debug_info.append(f"Job status: {status}")
            logger.info(f"Job status: {status}")
            
            # Map the status to the expected format
            if status == "complete":
                return {
                    "status": "success",
                    "data": status_info
                }
            elif status == "running" or status == "pending":
                return {
                    "status": "processing",
                    "data": status_info
                }
            elif status == "error":
                return {
                    "status": "error",
                    "error": status_info.get("message", "Unknown error")
                }
            else:
                return {
                    "status": "unknown",
                    "data": status_info
                }
                
        except Exception as e:
            error_msg = f"Error checking job status: {str(e)}"
            st.session_state.debug_info.append(error_msg)
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
    
    # Fallback to the old HTTP API method
    try:
        # Log the status check
        st.session_state.debug_info.append(f"Checking job status for prompt {prompt_id} using HTTP API")
        logger.info(f"Checking job status for prompt {prompt_id} using HTTP API")
        
        # First try direct history endpoint
        direct_history_url = f"{api_url}/history/{prompt_id}"
        st.session_state.debug_info.append(f"Checking direct history endpoint: {direct_history_url}")
        direct_response = requests.get(direct_history_url, timeout=10)
        
        if direct_response.status_code == 200:
            direct_data = direct_response.json()
            st.session_state.debug_info.append(f"Direct history response type: {type(direct_data).__name__}")
            
            # Handle dictionary format with prompt_id as key
            if isinstance(direct_data, dict) and prompt_id in direct_data:
                job_data = direct_data[prompt_id]
                st.session_state.debug_info.append(f"Found job data in direct history endpoint")
                
                # Check if the prompt has outputs (completed)
                if "outputs" in job_data and job_data["outputs"]:
                    st.session_state.debug_info.append(f"Job complete. Found in direct history with outputs.")
                    logger.info(f"Job complete. Found in direct history with outputs.")
                    return {
                        "status": "success",
                        "data": job_data
                    }
                else:
                    st.session_state.debug_info.append(f"Job still processing. Found in direct history but no outputs yet.")
                    logger.info(f"Job still processing. Found in direct history but no outputs yet.")
                    return {
                        "status": "processing",
                        "data": job_data
                    }
            # Handle dictionary format with data directly
            elif isinstance(direct_data, dict) and "outputs" in direct_data:
                st.session_state.debug_info.append(f"Found job data directly in response")
                
                if direct_data["outputs"]:
                    st.session_state.debug_info.append(f"Job complete. Found outputs directly in response.")
                    logger.info(f"Job complete. Found outputs directly in response.")
                    return {
                        "status": "success",
                        "data": direct_data
                    }
                else:
                    st.session_state.debug_info.append(f"Job still processing. No outputs in direct response.")
                    logger.info(f"Job still processing. No outputs in direct response.")
                    return {
                        "status": "processing",
                        "data": direct_data
                    }
        
        # Check the history endpoint next
        history_url = f"{api_url}/history"
        st.session_state.debug_info.append(f"Checking history endpoint: {history_url}")
        history_response = requests.get(history_url, timeout=10)
        
        if history_response.status_code == 200:
            history_data = history_response.json()
            st.session_state.debug_info.append(f"History data type: {type(history_data).__name__}")
            
            # Handle dictionary format (traditional ComfyUI format)
            if isinstance(history_data, dict):
                st.session_state.debug_info.append(f"History contains {len(history_data)} items (dictionary format)")
                # Look for exact or partial match in the keys
                for item_id, item_data in history_data.items():
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        st.session_state.debug_info.append(f"Found matching prompt ID in history: {item_id}")
                        logger.info(f"Found matching prompt ID in history: {item_id}")
                        
                        # Check if the prompt has outputs (completed)
                        if "outputs" in item_data and item_data["outputs"]:
                            st.session_state.debug_info.append(f"Job complete. Found in history with outputs.")
                            logger.info(f"Job complete. Found in history with outputs.")
                            return {
                                "status": "success",
                                "data": item_data
                            }
                        else:
                            st.session_state.debug_info.append(f"Job still processing. Found in history but no outputs yet.")
                            logger.info(f"Job still processing. Found in history but no outputs yet.")
                            return {
                                "status": "processing",
                                "data": item_data
                            }
            # Handle list format (newer ComfyUI versions)
            elif isinstance(history_data, list):
                st.session_state.debug_info.append(f"History contains {len(history_data)} items (list format)")
                # Look for exact or partial match in the list
                for item in history_data:
                    if not isinstance(item, dict) or "prompt_id" not in item:
                        continue
                    
                    item_id = item["prompt_id"]
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        st.session_state.debug_info.append(f"Found matching prompt ID in history: {item_id}")
                        logger.info(f"Found matching prompt ID in history: {item_id}")
                        
                        # Check if the prompt has outputs (completed)
                        if "outputs" in item and item["outputs"]:
                            st.session_state.debug_info.append(f"Job complete. Found in history with outputs.")
                            logger.info(f"Job complete. Found in history with outputs.")
                            return {
                                "status": "success",
                                "data": item
                            }
                        else:
                            st.session_state.debug_info.append(f"Job still processing. Found in history but no outputs yet.")
                            logger.info(f"Job still processing. Found in history but no outputs yet.")
                            return {
                                "status": "processing",
                                "data": item
                            }
        
        # If not found in history, check the queue
        queue_url = f"{api_url}/queue"
        st.session_state.debug_info.append(f"Checking queue endpoint: {queue_url}")
        queue_response = requests.get(queue_url, timeout=10)
        
        if queue_response.status_code == 200:
            queue_data = queue_response.json()
            st.session_state.debug_info.append(f"Queue data keys: {list(queue_data.keys())}")
            
            # Check different queue formats
            # Check 'running_items' and 'queue_running' fields
            running_fields = ["queue_running", "running_items", "running"]
            for field in running_fields:
                if field in queue_data:
                    running_items = queue_data[field]
                    st.session_state.debug_info.append(f"Found running items in field '{field}': {type(running_items)}")
                    
                    # Handle different formats
                    if isinstance(running_items, dict):
                        running_items = [running_items]
                    
                    if isinstance(running_items, list):
                        for item in running_items:
                            # Format 1: Each item is a dict with prompt_id
                            if isinstance(item, dict) and "prompt_id" in item:
                                item_id = item["prompt_id"]
                                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                    st.session_state.debug_info.append(f"Job is currently running in queue.")
                                    logger.info(f"Job is currently running in queue.")
                                    return {
                                        "status": "processing",
                                        "data": item
                                    }
                            # Format 2: Each item is a list with prompt_id at index 1
                            elif isinstance(item, list) and len(item) > 1:
                                item_id = item[1]
                                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                    st.session_state.debug_info.append(f"Job is currently running in queue.")
                                    logger.info(f"Job is currently running in queue.")
                                    return {
                                        "status": "processing",
                                        "data": {"prompt_id": item_id}
                                    }
            
            # Check 'queue_pending' and 'pending_items' fields
            pending_fields = ["queue_pending", "pending_items", "pending"]
            for field in pending_fields:
                if field in queue_data:
                    pending_items = queue_data[field]
                    st.session_state.debug_info.append(f"Found pending items in field '{field}': {type(pending_items)}")
                    
                    # Handle different formats
                    if isinstance(pending_items, dict):
                        pending_items = [pending_items]
                        
                    if isinstance(pending_items, list):
                        for item in pending_items:
                            # Format 1: Each item is a dict with prompt_id
                            if isinstance(item, dict) and "prompt_id" in item:
                                item_id = item["prompt_id"]
                                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                    st.session_state.debug_info.append(f"Job is pending in queue.")
                                    logger.info(f"Job is pending in queue.")
                                    return {
                                        "status": "processing",
                                        "data": item
                                    }
                            # Format 2: Each item is a list with prompt_id at index 1
                            elif isinstance(item, list) and len(item) > 1:
                                item_id = item[1]
                                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                    st.session_state.debug_info.append(f"Job is pending in queue.")
                                    logger.info(f"Job is pending in queue.")
                                    return {
                                        "status": "processing",
                                        "data": {"prompt_id": item_id}
                                    }
        
        # If we get here, the prompt ID wasn't found in history or queue
        st.session_state.debug_info.append(f"Job not found in history or queue.")
        logger.warning(f"Job not found in history or queue.")
        return {
            "status": "unknown",
            "error": "Job not found in history or queue"
        }
        
    except Exception as e:
        error_msg = f"Error checking job status: {str(e)}"
        st.session_state.debug_info.append(error_msg)
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg
        }

# Function to get file from ComfyUI node
def get_comfyui_file(api_url, filename, node_id=""):
    try:
        # ComfyUI uses /view endpoint for files
        file_url = f"{api_url}/view?filename={filename}"
        
        # Get the file
        response = requests.get(file_url)
        
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Error getting file: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error downloading file: {str(e)}")
        return None

# Function to fetch ComfyUI job history
def fetch_comfyui_job_history(api_url, limit=20):
    """Fetch recent job history from ComfyUI API
    
    Args:
        api_url: URL to the ComfyUI API
        limit: Maximum number of history items to return
        
    Returns:
        A list of job history items (prompt_id, timestamp, status)
    """
    try:
        # ComfyUI stores history at /history endpoint
        response = requests.get(f"{api_url}/history", timeout=10)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"Error fetching history: {response.status_code}"}
            
        data = response.json()
        
        # Debug the API response format
        print(f"ComfyUI API response type: {type(data)}")
        
        # Process the history data - handle both dict and list response formats
        history_items = []
        
        # If data is a list (newer ComfyUI versions may return a list)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "prompt_id" in item:
                    # Extract data from list format
                    prompt_id = item.get("prompt_id", "unknown")
                    timestamp = item.get("created_at", "Unknown")
                    status = item.get("status", "Unknown")
                    
                    # Try to get prompt text if available
                    prompt_text = ""
                    outputs = {}
                    
                    history_items.append({
                        "prompt_id": prompt_id,
                        "timestamp": timestamp,
                        "status": status,
                        "prompt_text": prompt_text,
                        "outputs": outputs
                    })
        # If data is a dictionary (traditional ComfyUI format)
        elif isinstance(data, dict):
            for prompt_id, job_info in data.items():
                # Skip if job_info is not a dictionary
                if not isinstance(job_info, dict):
                    continue
                    
                # Extract timestamp if available
                timestamp = "Unknown"
                if "prompt" in job_info and isinstance(job_info["prompt"], dict):
                    if "extra_data" in job_info["prompt"] and isinstance(job_info["prompt"]["extra_data"], dict):
                        extra_data = job_info["prompt"]["extra_data"]
                        if "datetime" in extra_data:
                            timestamp = extra_data["datetime"]
                
                # Determine job status
                status = "Unknown"
                if "status" in job_info and isinstance(job_info["status"], dict):
                    if "status_str" in job_info["status"]:
                        status = job_info["status"]["status_str"]
                    elif "completed" in job_info["status"] and job_info["status"]["completed"] == True:
                        status = "success"
                            
                # Extract prompt text if available
                prompt_text = ""
                outputs = {}
                if "outputs" in job_info and isinstance(job_info["outputs"], dict):
                    outputs = job_info["outputs"]
                
                # Get first part of prompt from any text encode node
                if "prompt" in job_info and isinstance(job_info["prompt"], dict) and "nodes" in job_info["prompt"]:
                    nodes = job_info["prompt"]["nodes"]
                    if isinstance(nodes, dict):
                        for node_id, node_data in nodes.items():
                            if isinstance(node_data, dict) and node_data.get("class_type", "") == "CLIPTextEncode" and "inputs" in node_data:
                                if "text" in node_data["inputs"] and "Negative" not in node_data.get("_meta", {}).get("title", ""):
                                    prompt_text = node_data["inputs"]["text"]
                                    if len(prompt_text) > 80:
                                        prompt_text = prompt_text[:77] + "..."
                                    break
                
                # Add to history items
                history_items.append({
                    "prompt_id": prompt_id,
                    "timestamp": timestamp,
                    "status": status,
                    "prompt_text": prompt_text,
                    "outputs": outputs
                })
        else:
            return {"status": "error", "message": f"Unexpected response format from ComfyUI API: {type(data)}"}
        
        # Sort by timestamp (newest first) and limit number of items
        # Use a safer sorting approach that handles missing or invalid timestamps
        try:
            history_items.sort(key=lambda x: x["timestamp"], reverse=True)
        except Exception as sort_error:
            print(f"Warning: Could not sort history items: {str(sort_error)}")
            
        if limit > 0 and len(history_items) > limit:
            history_items = history_items[:limit]
            
        return {"status": "success", "data": history_items}
    
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Timeout while fetching job history"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": f"Could not connect to ComfyUI API at {api_url}"}
    except Exception as e:
        return {"status": "error", "message": f"Error fetching job history: {str(e)}"}

# Function to fetch content by ID from ComfyUI
def fetch_comfyui_content_by_id(api_url, prompt_id, max_retries=3, retry_delay=5):
    """
    Fetch content by ID from ComfyUI with retry logic
    """
    # Use the correct ComfyUI server URL
    api_url = "http://100.115.243.42:8000"
    print(f"\n=== Fetching content for prompt_id: {prompt_id} ===")
    print(f"API URL: {api_url}")
    
    # Validate input parameters
    if not prompt_id:
        error_msg = "No prompt ID provided"
        print(f"ERROR: {error_msg}")
        return {"status": "error", "message": error_msg}
    
    # Try a server health check first
    try:
        print("Performing server health check...")
        health_check = requests.get(f"{api_url}/history", timeout=5)
        print(f"Server health check status: {health_check.status_code}")
        if health_check.status_code != 200:
            error_msg = f"ComfyUI server may be unavailable. Health check failed with status {health_check.status_code}"
            print(f"WARNING: {error_msg}")
            # Continue anyway, but log the warning
    except Exception as e:
        error_msg = f"ComfyUI server health check failed: {str(e)}"
        print(f"WARNING: {error_msg}")
        # Continue anyway, but log the warning
    
    # If the WebSocket client is available, use it
    if COMFYUI_WEBSOCKET_AVAILABLE:
        try:
            # Check job status
            print(f"Checking job status using WebSocket client")
            status_info = check_prompt_status(prompt_id, server_url=api_url)
            
            print(f"Job status: {status_info['status']}")
            print(f"Status info details: {json.dumps(status_info, indent=2)}")
            
            if status_info["status"] == "complete":
                # Get the full prompt ID if it was a partial match
                full_prompt_id = status_info.get("prompt_id", prompt_id)
                if full_prompt_id != prompt_id:
                    print(f"Found full prompt ID: {full_prompt_id}")
                    prompt_id = full_prompt_id
                
                # Get output files
                print(f"Getting output files")
                output_dir = Path(tempfile.mkdtemp())
                output_paths = get_output_images(
                    prompt_id,
                    server_url=api_url,
                    output_dir=output_dir
                )
                
                if output_paths:
                    print(f"Found {len(output_paths)} output files")
                    for path in output_paths:
                        print(f"  - {path}")
                    
                    # Return the first output file
                    output_path = output_paths[0]
                    with open(output_path, "rb") as f:
                        content = f.read()
                    
                    # Determine file extension
                    file_extension = os.path.splitext(output_path)[1].lower()
                    if not file_extension:
                        file_extension = ".mp4"  # Default to mp4 if no extension
                    
                    # Clean up temporary directory
                    shutil.rmtree(output_dir, ignore_errors=True)
                    
                    return {
                        "status": "success",
                        "content": content,
                        "file_extension": file_extension,
                        "prompt_id": prompt_id
                    }
                else:
                    error_msg = "No output files found for this job"
                    print(f"ERROR: {error_msg}")
                    return {"status": "error", "message": error_msg}
            
            elif status_info["status"] == "running" or status_info["status"] == "pending":
                message = f"Job is still {status_info['status']}"
                print(f"STATUS: {message}")
                return {"status": "processing", "message": message}
            
            else:
                error_msg = f"Job status is {status_info['status']}"
                print(f"ERROR: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Error using WebSocket client: {str(e)}"
            print(f"ERROR: {error_msg}")
            print("Falling back to traditional method")
    
    # Traditional method using direct HTTP requests
    def make_request(url, method='get', timeout=60, **kwargs):
        """Helper function to make requests with retry logic"""
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries} for {url}")
                if method.lower() == 'get':
                    response = requests.get(url, timeout=timeout, **kwargs)
                elif method.lower() == 'head':
                    response = requests.head(url, timeout=timeout, **kwargs)
                return response
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Timeout on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    print(f"Connection error on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
    
    try:
        # First try direct history endpoint for the prompt
        direct_url = f"{api_url}/history/{prompt_id}"
        print(f"\n1. Checking direct history endpoint: {direct_url}")
        
        try:
            direct_response = make_request(direct_url, timeout=30)
            print(f"Direct history response status: {direct_response.status_code}")
            
            if direct_response.status_code == 200:
                direct_data = direct_response.json()
                print(f"Direct history response type: {type(direct_data).__name__}")
                
                # Process the direct history data
                if direct_data:
                    # Handle the case when this returns the exact job
                    outputs = None
                    
                    if isinstance(direct_data, dict):
                        # The response might be the job data directly
                        outputs = direct_data.get("outputs", {})
                        
                        if outputs and len(outputs) > 0:
                            print(f"Found outputs in direct history endpoint")
                            # Find output file(s)
                            for node_id, node_data in outputs.items():
                                # Handle videos first
                                for media_type in ["videos", "gifs"]:
                                    if media_type in node_data:
                                        for media_item in node_data[media_type]:
                                            filename = media_item.get("filename", "")
                                            if filename:
                                                print(f"Found {media_type} file: {filename}")
                                                # Download the file
                                                file_url = f"{api_url}/view?filename={filename}"
                                                try:
                                                    content_response = requests.get(file_url, timeout=30)
                                                    if content_response.status_code == 200:
                                                        return {
                                                            "status": "success",
                                                            "content": content_response.content,
                                                            "filename": filename,
                                                            "type": "video"
                                                        }
                                                except Exception as e:
                                                    print(f"Error downloading file {filename}: {str(e)}")
                                
                                # Then handle images
                                if "images" in node_data:
                                    for image_data in node_data["images"]:
                                        filename = image_data.get("filename", "")
                                        if filename:
                                            print(f"Found image file: {filename}")
                                            # Download the file
                                            file_url = f"{api_url}/view?filename={filename}"
                                            try:
                                                content_response = requests.get(file_url, timeout=30)
                                                if content_response.status_code == 200:
                                                    return {
                                                        "status": "success",
                                                        "content": content_response.content,
                                                        "filename": filename,
                                                        "type": "image"
                                                    }
                                            except Exception as e:
                                                print(f"Error downloading file {filename}: {str(e)}")
                    
                    # If we couldn't find outputs but found the job, it's still processing
                    if direct_data and not outputs:
                        print("Job found but still processing")
                        return {"status": "processing", "message": "Job still processing"}
        except Exception as e:
            print(f"Error checking direct history endpoint: {str(e)}")
            # Continue to check full history
        
        # If direct history didn't work, check full history
        history_url = f"{api_url}/history"
        print(f"\n2. Checking full history at: {history_url}")
        
        history_response = make_request(history_url, timeout=60)
        print(f"History response status: {history_response.status_code}")
        
        if history_response.status_code != 200:
            error_msg = f"Error fetching history: {history_response.status_code}. Server might be busy, try again later."
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        history_data = history_response.json()
        print(f"History data type: {type(history_data).__name__}")
        
        # Handle both dictionary and list formats
        job_data = None
        if isinstance(history_data, dict):
            # Look for exact or partial match in the keys
            for item_id, item_data in history_data.items():
                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                    print(f"Found matching prompt ID in history: {item_id}")
                    job_data = item_data
                    prompt_id = item_id  # Use the full ID
                    break
        elif isinstance(history_data, list):
            for item in history_data:
                if isinstance(item, dict) and "prompt_id" in item:
                    item_id = item["prompt_id"]
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        print(f"Found matching prompt ID in history: {item_id}")
                        job_data = item
                        prompt_id = item_id  # Use the full ID
                        break
        
        if not job_data:
            # Check if the job is in queue
            queue_url = f"{api_url}/queue"
            try:
                queue_response = make_request(queue_url, timeout=10)
                print(f"Queue response status: {queue_response.status_code}")
                
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    print(f"Queue data type: {type(queue_data).__name__}")
                    
                    # Check if our job is in queue
                    queue_items = []
                    if isinstance(queue_data, dict) and "queue_running" in queue_data:
                        queue_items.extend(queue_data.get("queue_running", []))
                        queue_items.extend(queue_data.get("queue_pending", []))
                    elif isinstance(queue_data, list):
                        queue_items = queue_data
                    
                    for queue_item in queue_items:
                        if isinstance(queue_item, dict) and "prompt_id" in queue_item:
                            item_id = queue_item["prompt_id"]
                            if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                print(f"Found job in queue with ID: {item_id}")
                                return {"status": "processing", "message": "Job is queued for processing"}
            except Exception as e:
                print(f"Error checking queue: {str(e)}")
            
            error_msg = f"Prompt ID '{prompt_id}' not found in history or queue. The job may have been deleted or hasn't been submitted yet."
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
        
        # Get job info - fixed to handle different formats
        # Bug fix: Check the structure of job_data to correctly extract outputs
        job_info = None
        outputs = None
        
        # Handle dictionary format (traditional ComfyUI format)
        if isinstance(history_data, dict):
            # If job_data is the item data itself
            job_info = job_data
            outputs = job_info.get("outputs", {})
        # Handle list format (newer ComfyUI versions)
        elif isinstance(history_data, list):
            # If job_data is an item in the list
            job_info = job_data
            outputs = job_info.get("outputs", {})
        
        # Check if job completed
        if not outputs:
            print("Job found but no outputs yet")
            return {
                "status": "processing",
                "message": "Job still processing"
            }
        
        # Find output file
        for node_id, node_data in outputs.items():
            # Check for images
            if "images" in node_data:
                for image_data in node_data["images"]:
                    filename = image_data.get("filename", "")
                    
                    if filename:
                        print(f"Found image file: {filename}")
                        # Download file
                        file_url = f"{api_url}/view?filename={filename}"
                        try:
                            content_response = requests.get(file_url, timeout=30)
                            
                            if content_response.status_code == 200:
                                return {
                                    "status": "success",
                                    "content": content_response.content,
                                    "filename": filename,
                                    "type": "image"
                                }
                        except Exception as e:
                            print(f"Error downloading file {filename}: {str(e)}")
            
            # Check for videos
            for media_type in ["videos", "gifs"]:
                if media_type in node_data:
                    for media_item in node_data[media_type]:
                        filename = media_item.get("filename", "")
                        
                        if filename:
                            print(f"Found {media_type} file: {filename}")
                            # Download file
                            file_url = f"{api_url}/view?filename={filename}"
                            try:
                                content_response = requests.get(file_url, timeout=60)
                                
                                if content_response.status_code == 200:
                                    return {
                                        "status": "success",
                                        "content": content_response.content,
                                        "filename": filename,
                                        "type": "video"
                                    }
                            except Exception as e:
                                print(f"Error downloading file {filename}: {str(e)}")
        
        # If we got here, we found the job but couldn't get content
        error_msg = "No output files found for completed job"
        print(f"ERROR: {error_msg}")
        return {"status": "error", "message": error_msg}
    except requests.exceptions.ConnectionError as conn_err:
        error_msg = f"Connection error: Failed to connect to ComfyUI server at {api_url}. Please check if ComfyUI is running."
        print(f"ERROR: {error_msg}")
        return {"status": "error", "message": error_msg}
    except requests.exceptions.Timeout as timeout_err:
        error_msg = f"Timeout error: ComfyUI server at {api_url} took too long to respond. The server might be busy."
        st.session_state.debug_info.append(error_msg)
        logger.error(f"Timeout error: {str(timeout_err)}")
        print(f"DEBUG: Timeout error: {str(timeout_err)}")
        return {
            "status": "error",
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error fetching content: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"status": "error", "message": error_msg}

# Function to save media content to file
def save_media_content(content, segment_type, segment_id, file_extension):
    # Create directories if they don't exist
    media_dir = project_path / "media" / segment_type
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{segment_type}_{segment_id}_{timestamp}.{file_extension}"
    
    # Save file
    file_path = media_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return relative path from project directory
    return str(file_path)

# Function for batch processing prompts
def batch_process_broll_prompts():
    """Submit all B-Roll prompts to the video server for processing"""
    broll_segments = [s for s in st.session_state.segments if s["type"] == "B-Roll"]
    prompt_ids = {}
    errors = {}
    
    # Reset batch process status
    st.session_state.batch_process_status["submitted"] = True
    st.session_state.batch_process_status["prompt_ids"] = {}
    st.session_state.batch_process_status["errors"] = {}
    
    # Get the workflow template path for video
    template_file = JSON_TEMPLATES["video"]
    
    # Debug information
    print(f"Debug - Starting batch processing for {len(broll_segments)} B-Roll segments")
    
    # First verify connection to ComfyUI server
    api_url = COMFYUI_VIDEO_API_URL
    try:
        print(f"Debug - Testing connection to ComfyUI server at {api_url}")
        connection_test = requests.get(f"{api_url}/history", timeout=5)
        print(f"Debug - Server connection test status: {connection_test.status_code}")
        
        if connection_test.status_code != 200:
            error_msg = f"ComfyUI server returned status {connection_test.status_code} - server may be unavailable"
            print(f"Error - {error_msg}")
            st.error(f"⚠️ Server connection error: {error_msg}")
            return {}, {"general": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = f"Failed to connect to ComfyUI server at {api_url}. Please check if the server is running."
        print(f"Error - {error_msg}")
        st.error(f"⚠️ Connection error: {error_msg}")
        return {}, {"general": error_msg}
    except requests.exceptions.Timeout:
        error_msg = f"Connection to ComfyUI server at {api_url} timed out. Server might be busy."
        print(f"Error - {error_msg}")
        st.error(f"⚠️ Timeout error: {error_msg}")
        return {}, {"general": error_msg}
    except Exception as e:
        error_msg = f"Error connecting to ComfyUI server: {str(e)}"
        print(f"Error - {error_msg}")
        st.error(f"⚠️ Connection error: {error_msg}")
        return {}, {"general": error_msg}
    
    # Extract prompts data correctly based on structure
    prompts_data = {}
    if hasattr(st.session_state, 'broll_prompts_full') and st.session_state.broll_prompts_full:
        if "prompts" in st.session_state.broll_prompts_full:
            prompts_data = st.session_state.broll_prompts_full["prompts"]
            print(f"Debug - Using prompts from broll_prompts_full: {len(prompts_data)} prompts")
    elif hasattr(st.session_state, 'broll_prompts'):
        if isinstance(st.session_state.broll_prompts, dict):
            if "prompts" in st.session_state.broll_prompts:
                prompts_data = st.session_state.broll_prompts["prompts"]
                print(f"Debug - Using prompts from nested broll_prompts: {len(prompts_data)} prompts")
            else:
                prompts_data = st.session_state.broll_prompts
                print(f"Debug - Using prompts directly from broll_prompts: {len(prompts_data)} prompts")
    
    if not prompts_data:
        st.error("No B-Roll prompts found. Please generate prompts first.")
        return {}, {"general": "No prompts found"}
    
    print(f"Debug - Available prompt segment IDs: {list(prompts_data.keys())}")
    
    # Process each B-Roll segment
    for i, segment in enumerate(broll_segments):
        segment_id = f"segment_{i}"
        
        # Check if we have prompts for this segment
        if segment_id in prompts_data:
            prompt_data = prompts_data[segment_id]
            
            # Handle both dictionary and string formats
            if isinstance(prompt_data, dict):
                prompt_text = prompt_data.get("prompt", "")
                negative_prompt = prompt_data.get("negative_prompt", "ugly, blurry, low quality")
            else:
                prompt_text = str(prompt_data)
                negative_prompt = "ugly, blurry, low quality"
            
            print(f"Debug - Processing segment {segment_id} with prompt: {prompt_text[:50]}...")
            
            # Prepare the workflow
            workflow = prepare_comfyui_workflow(
                template_file,
                prompt_text,
                negative_prompt,
                resolution="1080x1920"
            )
            
            # Validate the workflow before submitting
            if not workflow or not isinstance(workflow, dict) or len(workflow) == 0:
                error_msg = "Failed to create valid workflow from template"
                errors[segment_id] = error_msg
                st.session_state.batch_process_status["errors"][segment_id] = error_msg
                update_content_status(
                    segment_id=segment_id,
                    segment_type="broll",
                    status="error",
                    message=f"Invalid workflow: {error_msg}"
                )
                st.error(f"Failed to prepare workflow for B-Roll Segment {i+1}: {error_msg}")
                continue
            
            # Display the prepared prompt in the UI
            st.info(f"Preparing prompt for Segment {i+1}...")
            st.text_area(f"Segment {i+1} Prompt", value=prompt_text, height=150, key=f"prompt_view_{i}")
            
            try:
                # Submit the workflow to ComfyUI
                result = submit_comfyui_workflow(workflow)
                
                if result["status"] == "success":
                    prompt_id = result["prompt_id"]
                    
                    # Store the prompt ID
                    prompt_ids[segment_id] = prompt_id
                    st.session_state.batch_process_status["prompt_ids"][segment_id] = prompt_id
                    
                    # Update content status
                    update_content_status(
                        segment_id=segment_id,
                        segment_type="broll",
                        status="processing",
                        message=f"Submitted to video server (ID: {prompt_id})",
                        prompt_id=prompt_id
                    )
                    
                    st.success(f"Submitted B-Roll Segment {i+1} with ID: {prompt_id}")
                else:
                    # Enhanced error handling for different types of errors
                    error_msg = result.get("error", "Unknown error")
                    
                    # Provide more context for common errors
                    if "Unknown error" in error_msg:
                        error_msg = "Server returned 'Unknown error'. The ComfyUI server might be busy or unable to process the request. Please check ComfyUI logs."
                    elif "Connection" in error_msg:
                        error_msg = f"{error_msg}. Please ensure ComfyUI is running and accessible."
                    elif "Timeout" in error_msg:
                        error_msg = f"{error_msg}. The server might be busy with other tasks."
                        
                    errors[segment_id] = error_msg
                    st.session_state.batch_process_status["errors"][segment_id] = error_msg
                    
                    # Update content status
                    update_content_status(
                        segment_id=segment_id,
                        segment_type="broll",
                        status="error",
                        message=f"Submission failed: {error_msg}"
                    )
                    
                    st.error(f"Failed to submit B-Roll Segment {i+1}: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                errors[segment_id] = error_msg
                st.session_state.batch_process_status["errors"][segment_id] = error_msg
                
                # Update content status
                update_content_status(
                    segment_id=segment_id,
                    segment_type="broll",
                    status="error",
                    message=f"Exception: {error_msg}"
                )
                
                st.error(f"Exception while submitting B-Roll Segment {i+1}: {error_msg}")
        else:
            print(f"Debug - No prompts found for segment {segment_id}")
            print(f"Debug - Available segments: {list(prompts_data.keys())}")
            
            # Update content status to show missing prompt
            update_content_status(
                segment_id=segment_id,
                segment_type="broll",
                status="error",
                message="No prompt available. Please create a B-Roll prompt first."
            )
            
            st.warning(f"No prompt found for B-Roll Segment {i+1}. Please generate prompts first.")
    
    # Return results
    return prompt_ids, errors

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=3,
    prev_step_path="pages/4_BRoll_Prompts.py",
    next_step_path="pages/6_Video_Assembly.py"
)

# Debug section (hidden by default)
with st.expander("Debug Information", expanded=False):
    st.markdown("### Session State Debug")
    
    st.markdown("#### Segments Information")
    segments = st.session_state.segments if hasattr(st.session_state, 'segments') else []
    st.write(f"Total segments: {len(segments)}")
    
    # Count segment types
    a_roll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    b_roll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    invalid_segments = [s for s in segments if not isinstance(s, dict) or "type" not in s or s.get("type") not in ["A-Roll", "B-Roll"]]
    
    st.write(f"A-Roll segments: {len(a_roll_segments)}")
    st.write(f"B-Roll segments: {len(b_roll_segments)}")
    st.write(f"Invalid segments: {len(invalid_segments)}")
    
    if st.button("Show Full Segments Data"):
        st.json(segments)
    
    st.markdown("#### B-Roll Prompts Information")
    prompts = st.session_state.broll_prompts if hasattr(st.session_state, 'broll_prompts') else {}
    st.write(f"B-Roll prompts object type: {type(prompts).__name__}")
    
    if isinstance(prompts, dict):
        if "prompts" in prompts:
            prompt_count = len(prompts.get("prompts", {}))
            st.write(f"Number of individual prompts: {prompt_count}")
        else:
            st.write("No 'prompts' key found in broll_prompts")
    
    if st.button("Show Full B-Roll Prompts Data"):
        st.json(prompts)
    
    st.markdown("#### Project Path")
    st.write(f"Project path: {project_path}")
    
    # Button to check if files exist
    if st.button("Check Project Files"):
        script_file = project_path / "script.json"
        prompts_file = project_path / "broll_prompts.json"
        
        st.write(f"script.json exists: {script_file.exists()}")
        st.write(f"broll_prompts.json exists: {prompts_file.exists()}")
        
        if script_file.exists():
            try:
                with open(script_file, "r") as f:
                    script_data = json.load(f)
                    st.write(f"script.json is valid JSON: True")
                    st.write(f"script.json has 'segments' key: {'segments' in script_data}")
                    if 'segments' in script_data:
                        st.write(f"Number of segments in file: {len(script_data['segments'])}")
            except json.JSONDecodeError:
                st.write(f"script.json is valid JSON: False")
            except Exception as e:
                st.write(f"Error reading script.json: {str(e)}")
        
        if prompts_file.exists():
            try:
                with open(prompts_file, "r") as f:
                    prompts_data = json.load(f)
                    st.write(f"broll_prompts.json is valid JSON: True")
                    st.write(f"broll_prompts.json has 'prompts' key: {'prompts' in prompts_data}")
                    if 'prompts' in prompts_data:
                        st.write(f"Number of prompts in file: {len(prompts_data['prompts'])}")
            except json.JSONDecodeError:
                st.write(f"broll_prompts.json is valid JSON: False")
            except Exception as e:
                st.write(f"Error reading broll_prompts.json: {str(e)}")
    
    # Refresh button
    if st.button("Reload Page Data"):
        _ = load_script_data()
        _ = load_broll_prompts()
        _ = load_content_status()
        st.rerun() 

# Add this function to allow clearing cached IDs
def clear_fetch_ids():
    """Clear cached IDs for A-Roll and B-Roll content"""
    if "aroll_fetch_ids" in st.session_state:
        st.session_state.aroll_fetch_ids = {}
    if "broll_fetch_ids" in st.session_state:
        st.session_state.broll_fetch_ids = {}
    st.success("✅ Content cache cleared successfully. New content will be generated on the next run.")
    
    # Also clear any active tracking
    if "active_trackers" in st.session_state:
        st.session_state.active_trackers = []

# Add a new UI section for cache management
with st.expander("🧹 Cache Management"):
    st.markdown("""
    ### Clear Content Cache
    
    If you're experiencing issues with content generation, or if you want to force regeneration of all content,
    you can clear the cached content IDs here.
    
    **Note:** This won't delete any previously generated files, but will ensure new content is generated
    the next time you run the generation process.
    """)
    
    if st.button("🗑️ Clear Content Cache", key="clear_cache"):
        clear_fetch_ids()

# Load workflow files
def load_workflow(workflow_type="video"):
    """Load a workflow template file based on the type of content to generate"""
    try:
        # First, prioritize by content type
        if workflow_type == "image":
            # For image generation, prioritize flux_schnell.json
            primary_path = os.path.join(os.getcwd(), "flux_schnell.json")
            if os.path.exists(primary_path):
                print(f"Found image workflow file at: {primary_path}")
                try:
                    with open(primary_path, "r") as f:
                        workflow = json.load(f)
                    
                    if workflow and len(workflow) > 0:
                        print(f"✅ Loaded image workflow from {primary_path} with {len(workflow)} nodes")
                        return workflow
                except Exception as e:
                    print(f"Error loading image workflow: {str(e)}")
        else:
            # For video generation, prioritize wan.json
            wan_path = os.path.join(os.getcwd(), "wan.json")
            if os.path.exists(wan_path):
                print(f"Found WAN workflow file at: {wan_path}")
                try:
                    with open(wan_path, "r") as f:
                        workflow = json.load(f)
                    
                    if workflow and len(workflow) > 0:
                        print(f"✅ Loaded video workflow from {wan_path} with {len(workflow)} nodes")
                        # Add back the code to identify text nodes
                        text_nodes = [k for k in workflow.keys() 
                                    if "class_type" in workflow[k] and 
                                    workflow[k]["class_type"] == "CLIPTextEncode"]
                        
                        if len(text_nodes) >= 2:
                            print(f"✅ Found {len(text_nodes)} text nodes in workflow")
                        else:
                            print(f"⚠️ Warning: Only found {len(text_nodes)} text nodes in workflow, might not work correctly")
                        
                        return workflow
                except Exception as e:
                    print(f"Error loading WAN workflow: {str(e)}")
        
        # If we didn't return early, try loading from other possible paths
        possible_paths = []
        
        # First try main workflow files
        if workflow_type == "image":
            possible_paths.append(os.path.join(os.getcwd(), "flux_schnell.json"))
        else:
            possible_paths.append(os.path.join(os.getcwd(), "wan.json"))
        
        # Standard locations
        possible_paths.extend([
            os.path.join(os.getcwd(), "workflows", f"{workflow_type}_workflow.json"),
            os.path.join(os.getcwd(), "workflows", "default_workflow.json"),
            os.path.join(os.getcwd(), "workflows", "workflow.json")
        ])
        
        # Try each path
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found workflow file at: {path}")
                try:
                    with open(path, "r") as f:
                        workflow = json.load(f)
                    
                    if workflow and len(workflow) > 0:
                        print(f"✅ Loaded workflow from {path} with {len(workflow)} nodes")
                        return workflow
                except Exception as e:
                    print(f"Error loading workflow from {path}: {str(e)}")
                    continue
        
        # If we get here, create a simplified workflow
        print("⚠️ No workflow file found, creating simplified workflow")
        if workflow_type == "image":
            return create_simplified_image_workflow()
        else:
            return create_simplified_video_workflow()
    
    except Exception as e:
        print(f"Error in load_workflow: {str(e)}")
        if workflow_type == "image":
            return create_simplified_image_workflow()
        else:
            return create_simplified_video_workflow()

def create_simplified_image_workflow():
    """Create a simplified image workflow that works with ComfyUI"""
    # This is a minimal workflow for generating an image with ComfyUI
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "A beautiful scene with mountains and trees",
                "clip": ["5", 0]
            }
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "ugly, blurry, low quality",
                "clip": ["5", 0]
            }
        },
        "3": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1080,
                "height": 1920,
                "batch_size": 1
            }
        },
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 123456789,
                "steps": 20,
                "cfg": 7,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["5", 0],
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["3", 0]
            }
        },
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "flux1-schnell-fp8.safetensors"
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["4", 0],
                "vae": ["5", 2]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "ComfyUI"
            }
        }
    }
    return workflow

def create_simplified_video_workflow():
    """Create a simplified video workflow that works with ComfyUI"""
    # This is a minimal workflow for generating a video with ComfyUI
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "A beautiful scene with mountains and trees",
                "clip": ["5", 0]
            }
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "ugly, blurry, low quality",
                "clip": ["5", 0]
            }
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 123456789,
                "steps": 20,
                "cfg": 7,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["5", 0],
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["4", 0]
            }
        },
        "4": {
            "class_type": "EmptyLatentVideo",
            "inputs": {
                "width": 1080,
                "height": 1920,
                "batch_size": 1,
                "length": 24,
                "fps": 8
            }
        },
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "flux1-schnell-fp8.safetensors"
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["5", 2]
            }
        },
        "7": {
            "class_type": "SaveAnimation",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "ComfyUI",
                "fps": 8,
                "format": "mp4",
                "quality": 95
            }
        }
    }
    return workflow

# Function to modify workflow with custom parameters
def modify_workflow(workflow, params):
    """Modify the loaded workflow JSON with custom parameters"""
    try:
        if workflow is None:
            print("❌ Error: Workflow is None, cannot modify")
            return None
            
        # Create a deep copy to avoid modifying the original
        modified_workflow = copy.deepcopy(workflow)
        
        # Debug - display params being applied
        print(f"Workflow modification params: {params}")
        
        # Check if this is a WAN workflow with EmptyHunyuanLatentVideo or other specialized nodes
        is_wan_workflow = False
        has_hunyuan_latent = False
        
        for node_id, node in modified_workflow.items():
            if "class_type" in node:
                if node["class_type"] == "EmptyHunyuanLatentVideo":
                    has_hunyuan_latent = True
                    print(f"✅ Found EmptyHunyuanLatentVideo node: {node_id}")
                elif node["class_type"] in ["UNETLoader", "CLIPLoader", "ModelLoader"]:
                    is_wan_workflow = True
                    print(f"✅ Found WAN model loader node: {node_id}")
                # Check for specific WAN model names in inputs
                elif ("inputs" in node and 
                     ("unet_name" in node["inputs"] and "wan" in str(node["inputs"]["unet_name"]).lower()) or
                     ("clip_name" in node["inputs"] and "umt5" in str(node["inputs"]["clip_name"]).lower()) or
                     ("ckpt_name" in node["inputs"] and "wan" in str(node["inputs"]["ckpt_name"]).lower())):
                    is_wan_workflow = True
                    print(f"✅ Found WAN model reference in node: {node_id}")
        
        # Check if this workflow is from wan.json file
        is_from_wan_file = False
        wan_path = os.path.join(os.getcwd(), "wan.json")
        if os.path.exists(wan_path):
            try:
                with open(wan_path, "r") as f:
                    wan_workflow = json.load(f)
                # Simple size comparison to check if it's the same workflow
                if len(wan_workflow) == len(workflow):
                    is_from_wan_file = True
                    print("✅ Using workflow from wan.json file - will bypass validation")
            except Exception as e:
                print(f"Error checking if workflow is from wan.json: {str(e)}")
                pass
        
        # Set flag to bypass validation if this is a WAN workflow or from wan.json
        bypass_validation = is_wan_workflow or has_hunyuan_latent or is_from_wan_file
        
        if is_wan_workflow and has_hunyuan_latent:
            print("✅ Detected WAN workflow with EmptyHunyuanLatentVideo - special handling enabled")
        
        # Make sure prompt is not empty
        prompt = params.get("prompt", "")
        negative_prompt = params.get("negative_prompt", "")
        
        if not prompt:
            print("⚠️ Warning: Empty prompt provided, using default")
            prompt = "A beautiful scene with mountains and trees"
        
        if not negative_prompt:
            negative_prompt = "ugly, blurry, low quality"
        
        # Find text input nodes (for prompt) - search for nodes with CLIPTextEncode class_type
        text_nodes = [k for k in modified_workflow.keys() 
                     if "class_type" in modified_workflow[k] and 
                     modified_workflow[k]["class_type"] == "CLIPTextEncode"]
        
        print(f"Found {len(text_nodes)} CLIPTextEncode nodes: {text_nodes}")
        
        # Find negative text nodes - typically the second CLIPTextEncode node
        if len(text_nodes) >= 2:
            # First node for positive prompt, second for negative
            pos_node_id = text_nodes[0]
            neg_node_id = text_nodes[1]
            
            # Set prompts
            if "inputs" in modified_workflow[pos_node_id]:
                modified_workflow[pos_node_id]["inputs"]["text"] = prompt
                print(f"Set positive prompt in node {pos_node_id}: {prompt[:50]}...")
                
            if "inputs" in modified_workflow[neg_node_id]:
                modified_workflow[neg_node_id]["inputs"]["text"] = negative_prompt
                print(f"Set negative prompt in node {neg_node_id}: {negative_prompt[:50]}...")
        
        # Set resolution if specified
        width = params.get("width", 1080)
        height = params.get("height", 1920)
        
        # Find nodes with width and height inputs
        for node_id, node in modified_workflow.items():
            if "class_type" in node and "inputs" in node:
                # Check if node has both width and height inputs
                if "width" in node["inputs"] and "height" in node["inputs"]:
                    modified_workflow[node_id]["inputs"]["width"] = width
                    modified_workflow[node_id]["inputs"]["height"] = height
                    print(f"Set dimensions in node {node_id}: {width}x{height}")
        
        # Set seed if specified
        seed = params.get("seed", random.randint(0, 999999999))
        
        # Find nodes that might have seed inputs
        for node_id, node in modified_workflow.items():
            if "class_type" in node and "inputs" in node and "seed" in node["inputs"]:
                # Directly assign the seed without any processing
                modified_workflow[node_id]["inputs"]["seed"] = seed
                print(f"Set seed in node {node_id}: {seed}")
        
        # If set to bypass validation, return the modified workflow directly
        if bypass_validation:
            print("🚀 Using workflow with specialized nodes directly - bypassing validation")
            return modified_workflow
        
        # Otherwise proceed with validation
        if not validate_workflow(modified_workflow):
            print("⚠️ Warning: Workflow validation failed, but will attempt to use original workflow anyway.")
            # Only use fallback if workflow is completely invalid, not just for missing EmptyHunyuanLatentVideo
            if not text_nodes or len(text_nodes) < 1:
                print("❌ Critical validation error: No text nodes found, using fallback workflow")
                if "video" in params and params["video"]:
                    return create_simplified_video_workflow()
                else:
                    return create_simplified_image_workflow()
        
        return modified_workflow
        
    except Exception as e:
        print(f"Error modifying workflow: {str(e)}")
        traceback.print_exc()
        # On any exception, return a failsafe workflow
        if "video" in params and params["video"]:
            workflow = create_simplified_video_workflow()
        else:
            workflow = create_simplified_image_workflow()
            
        # Apply the prompt directly to the new workflow
        prompt = params.get("prompt", "A beautiful scene")
        negative_prompt = params.get("negative_prompt", "ugly, blurry, low quality")
        workflow["1"]["inputs"]["text"] = prompt
        workflow["2"]["inputs"]["text"] = negative_prompt
        return workflow

def validate_workflow(workflow):
    """Validate that the workflow has all the required components"""
    try:
        # Check for required node types
        required_classes = {
            "CLIPTextEncode": 0,
            "KSampler": 0
        }
        
        # Either EmptyLatentImage, EmptyLatentVideo, or EmptyHunyuanLatentVideo should be present
        latent_found = False
        has_hunyuan_latent = False
        
        # Special nodes for WAN workflows
        wan_specialized_nodes = ["EmptyHunyuanLatentVideo", "UNETLoader", "CLIPLoader"]
        found_wan_nodes = False
        
        # List of valid models according to server
        valid_models = [
            "Juggernaut_X_RunDiffusion.safetensors",
            "LTXV\\ltxv-13b-0.9.7-dev-fp8.safetensors",
            "dreamshaper_8.safetensors",
            "flux1-dev-fp8.safetensors",
            "flux1-schnell-fp8.safetensors",
            "v1-5-pruned-emaonly-fp16.safetensors",
            # Add common models that might also be valid
            "LCM_Dreamshaper_v7.safetensors",
            "realisticVisionV51_v51VAE.safetensors",
            "dreamshaper_v8.safetensors",
            "sd_xl_base_1.0.safetensors",
            "sd_xl_refiner_1.0.safetensors",
            # Add WAN models
            "wan2.1_t2v_1.3B_fp16.safetensors",
            "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "wan_2.1_vae.safetensors"
        ]
        
        # Check each node in the workflow
        for node_id, node in workflow.items():
            if "class_type" not in node:
                continue
                
            # Check required classes
            if node["class_type"] in required_classes:
                required_classes[node["class_type"]] += 1
                
            # Check for latent nodes - including EmptyHunyuanLatentVideo
            if node["class_type"] in ["EmptyLatentImage", "EmptyLatentVideo", "EmptyHunyuanLatentVideo", "EmptySD3LatentImage"]:
                latent_found = True
                
                # Specifically flag Hunyuan latent for special handling
                if node["class_type"] == "EmptyHunyuanLatentVideo":
                    has_hunyuan_latent = True
                    print(f"✅ Found EmptyHunyuanLatentVideo node: {node_id}")
            
            # Check for specialized WAN nodes
            if node["class_type"] in wan_specialized_nodes:
                found_wan_nodes = True
                print(f"✅ Found specialized WAN node: {node_id} ({node['class_type']})")
                
            # Check for model loaders that might have valid models
            if node["class_type"] in ["CheckpointLoaderSimple", "UNETLoader", "CLIPLoader"] and "inputs" in node:
                if "ckpt_name" in node["inputs"] and node["inputs"]["ckpt_name"] in valid_models:
                    print(f"✅ Valid model found in {node['class_type']}: {node['inputs']['ckpt_name']}")
                elif "unet_name" in node["inputs"] and node["inputs"]["unet_name"] in valid_models:
                    print(f"✅ Valid UNET found in {node['class_type']}: {node['inputs']['unet_name']}")
                elif "clip_name" in node["inputs"] and node["inputs"]["clip_name"] in valid_models:
                    print(f"✅ Valid CLIP found in {node['class_type']}: {node['inputs']['clip_name']}")
        
        # If this is a WAN workflow with specialized nodes, accept it regardless of other checks
        if found_wan_nodes or has_hunyuan_latent:
            print("✅ Specialized WAN workflow detected - bypassing standard validation")
            return True
            
        # Check if we found all required classes
        for class_type, count in required_classes.items():
            if count == 0:
                print(f"⚠️ Workflow missing required class: {class_type}")
                return False
        
        # Check if we found a latent node
        if not latent_found:
            print("⚠️ Workflow missing EmptyLatentImage or EmptyLatentVideo node, will use fallback workflow")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error validating workflow: {str(e)}")
        traceback.print_exc()
        return False

# Function to fetch content by prompt ID
def fetch_content_by_id(prompt_id, api_url):
    """Fetch content by prompt ID from ComfyUI history"""
    try:
        # Log attempt
        print(f"Fetching content for prompt ID: {prompt_id}")
        
        # First try direct history endpoint
        direct_url = f"{api_url}/history/{prompt_id}"
        print(f"Checking direct history endpoint: {direct_url}")
        
        try:
            direct_response = requests.get(direct_url, timeout=15)
            
            if direct_response.status_code == 200:
                direct_data = direct_response.json()
                print(f"Direct history response type: {type(direct_data).__name__}")
                
                if isinstance(direct_data, dict):
                    # Check if it has outputs
                    if "outputs" in direct_data and direct_data["outputs"]:
                        # Find output file(s)
                        for node_id, output_data in direct_data["outputs"].items():
                            # Check for images
                            if "images" in output_data and output_data["images"]:
                                for img in output_data["images"]:
                                    if "filename" in img:
                                        print(f"Found image: {img['filename']}")
                                        # Fetch the image
                                        file_url = f"{api_url}/view?filename={img['filename']}"
                                        content_response = requests.get(file_url, timeout=60)
                                        if content_response.status_code == 200:
            return {
                                                "status": "success",
                                                "content": content_response.content,
                                                "filename": img["filename"],
                                                "type": "image"
                                            }
                            
                            # Check for videos
                            for media_type in ["videos", "gifs"]:
                                if media_type in output_data and output_data[media_type]:
                                    for vid in output_data[media_type]:
                                        if "filename" in vid:
                                            print(f"Found {media_type}: {vid['filename']}")
                                            # Fetch the video
                                            file_url = f"{api_url}/view?filename={vid['filename']}"
                                            content_response = requests.get(file_url, timeout=120)
                                            if content_response.status_code == 200:
            return {
                                                    "status": "success",
                                                    "content": content_response.content,
                                                    "filename": vid["filename"],
                                                    "type": "video"
                                                }
                    
                    # If we found the prompt but no outputs, it's still processing
            return {
                "status": "processing",
                        "message": f"Job found in history but still processing"
                    }
        except Exception as e:
            print(f"Error checking direct history: {str(e)}")
        
        # If direct history check failed, try fetching from general history
        try:
            history_url = f"{api_url}/history"
            print(f"Fetching history from: {history_url}")
            history_response = requests.get(history_url, timeout=15)
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                
                # Handle different history response formats
                if isinstance(history_data, dict):
                    # Format: {prompt_id: {data}}
                    for item_id, item_data in history_data.items():
                        # Check if this is our prompt (exact match or starts with)
                        if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                            print(f"Found matching prompt ID in history: {item_id}")
                            
                            # Check if it has outputs
                            outputs = item_data.get("outputs", {})
                            if outputs:
                                # Find output file(s)
                                for node_id, output_data in outputs.items():
                                    # Check for images
                                    if "images" in output_data and output_data["images"]:
                                        for img in output_data["images"]:
                                            if "filename" in img:
                                                print(f"Found image: {img['filename']}")
                                                # Fetch the image
                                                file_url = f"{api_url}/view?filename={img['filename']}"
                                                content_response = requests.get(file_url, timeout=60)
                        if content_response.status_code == 200:
                            return {
                                "status": "success",
                                "content": content_response.content,
                                                        "filename": img["filename"],
                                "type": "image"
                            }
            
            # Check for videos
            for media_type in ["videos", "gifs"]:
                                        if media_type in output_data and output_data[media_type]:
                                            for vid in output_data[media_type]:
                                                if "filename" in vid:
                                                    print(f"Found {media_type}: {vid['filename']}")
                                                    # Fetch the video
                                                    file_url = f"{api_url}/view?filename={vid['filename']}"
                                                    content_response = requests.get(file_url, timeout=120)
                            if content_response.status_code == 200:
                                return {
                                    "status": "success",
                                    "content": content_response.content,
                                                            "filename": vid["filename"],
                                    "type": "video"
                                }
        
                            # If we found the prompt but no outputs, it's still processing
                        return {
                                "status": "processing",
                                "message": f"Job found in history but still processing"
                            }
                # Handle list format and other checks from the original code
                elif isinstance(history_data, list):
                    # List format: [{prompt_id: ..., data: ...}, ...]
                    for item in history_data:
                        if isinstance(item, dict):
                            # Check different possible ID field names
                            for id_field in ["prompt_id", "id"]:
                                if id_field in item:
                                    item_id = item[id_field]
                                    # Check for exact or partial match
                                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                        print(f"Found prompt in history (list format): {item_id}")
                                        
                                        # Check if job has outputs
                                        if "outputs" in item and item["outputs"]:
                                            # Process outputs similar to above
        return {
                                                "status": "processing",
                                                "message": f"Job found in history but still processing"
                                            }
        except Exception as e:
            print(f"Error fetching history: {str(e)}")
        
        # If we get here, try checking queue status
        try:
            queue_url = f"{api_url}/queue"
            queue_response = requests.get(queue_url, timeout=15)
            
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                print(f"Queue data keys: {list(queue_data.keys())}")
                
                # Check if job is in queue
                for status_type in ["queue_running", "running_items", "running", "queue_pending", "pending_items", "pending"]:
                    if status_type in queue_data:
                        print(f"Found {status_type} in queue data")
                        return {
                            "status": "processing",
                            "message": f"Job is in queue ({status_type})"
                        }
    except Exception as e:
            print(f"Error checking queue: {str(e)}")
        
        # If we get here, we couldn't find the prompt or content
        return {
            "status": "error",
            "message": f"Prompt ID not found: {prompt_id}"
        }
    
    except Exception as e:
        error_msg = f"Error fetching content: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

# Function to periodically fetch content until it's available or max attempts reached
def periodic_content_fetch(prompt_id, api_url, max_attempts=120, interval=5):
    """Periodically fetch content by prompt ID until it's available or max attempts reached"""
    status_placeholder = st.empty()
    status_placeholder.info(f"⏳ Waiting for content generation to complete (ID: {prompt_id})...")
    
    for attempt in range(1, max_attempts + 1):
        status_placeholder.text(f"Fetch attempt {attempt}/{max_attempts}... (waiting for ComfyUI to process)")
        
        # First check direct history endpoint
        try:
            direct_url = f"{api_url}/history/{prompt_id}"
            status_placeholder.text(f"Checking direct history endpoint: {direct_url}")
            direct_response = requests.get(direct_url, timeout=15)
            
            if direct_response.status_code == 200:
                direct_data = direct_response.json()
                status_placeholder.text(f"Direct response type: {type(direct_data).__name__}")
                
                # Handle direct history response
                if isinstance(direct_data, dict):
                    # Check if it has outputs
                    if "outputs" in direct_data and direct_data["outputs"]:
                        status_placeholder.text(f"Found outputs in direct history")
                        # Extract file from outputs
                        for node_id, output_data in direct_data["outputs"].items():
                            if "images" in output_data and output_data["images"]:
                                for img in output_data["images"]:
                                    if "filename" in img:
                                        status_placeholder.text(f"Found image: {img['filename']}")
                                        file_url = f"{api_url}/view?filename={img['filename']}"
                                        content_response = requests.get(file_url, timeout=60)
                                        if content_response.status_code == 200:
                                            status_placeholder.success("✅ Content successfully generated!")
                                            return {
                                                "status": "success",
                                                "content": content_response.content,
                                                "filename": img["filename"],
                                                "type": "image"
                                            }
                            for media_type in ["videos", "gifs"]:
                                if media_type in output_data and output_data[media_type]:
                                    for vid in output_data[media_type]:
                                        if "filename" in vid:
                                            status_placeholder.text(f"Found {media_type}: {vid['filename']}")
                                            file_url = f"{api_url}/view?filename={vid['filename']}"
                                            content_response = requests.get(file_url, timeout=120)
                                            if content_response.status_code == 200:
                                                status_placeholder.success("✅ Content successfully generated!")
                                                return {
                                                    "status": "success",
                                                    "content": content_response.content,
                                                    "filename": vid["filename"],
                                                    "type": "video"
                                                }
                    else:
                        status_placeholder.text(f"Job found in direct history but still processing (no outputs yet)")
        except Exception as e:
            status_placeholder.text(f"Error checking direct history: {str(e)}")
        
        # Try to fetch content using the standard method
        result = fetch_content_by_id(prompt_id, api_url)
        
        if result["status"] == "success":
            status_placeholder.success("✅ Content successfully generated!")
            return result
        elif result["status"] == "processing":
            # If the job is still processing, wait and try again
            status_placeholder.info(f"⏳ Job is still processing (attempt {attempt}/{max_attempts})...")
            time.sleep(interval)
            continue
        elif result["status"] == "error" and "not found" in result.get("message", "").lower():
            # Check if the job is in the queue but not in history yet
            try:
                queue_url = f"{api_url}/queue"
                queue_response = requests.get(queue_url, timeout=10)
                
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    
                    # Log queue data for debugging
                    status_placeholder.text(f"Queue data keys: {list(queue_data.keys())}")
                    
                    # Check if the job is in the queue (running or pending)
                    in_queue = False
                    
                    # Check running items - handle different formats
                    running_fields = ["queue_running", "running_items", "running"]
                    for field in running_fields:
                        if field in queue_data:
                            running_items = queue_data[field]
                            status_placeholder.text(f"Found running items in field '{field}': {type(running_items)}")
                            
                            # List format
                            if isinstance(running_items, list):
                                for item in running_items:
                                    # Dict with prompt_id
                                    if isinstance(item, dict) and "prompt_id" in item:
                                        item_id = item["prompt_id"]
                                        if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                            in_queue = True
                                            status_placeholder.info(f"⏳ Job is currently running in queue (attempt {attempt}/{max_attempts})...")
                                            break
                                    # List with prompt_id at index 1
                                    elif isinstance(item, list) and len(item) > 1:
                                        item_id = item[1]
                                        if isinstance(item_id, str) and (item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id)):
                                            in_queue = True
                                            status_placeholder.info(f"⏳ Job is currently running in queue (attempt {attempt}/{max_attempts})...")
                                            break
                            # Dict format
                            elif isinstance(running_items, dict):
                                for item_id, item_data in running_items.items():
                                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                        in_queue = True
                                        status_placeholder.info(f"⏳ Job is currently running in queue (attempt {attempt}/{max_attempts})...")
                                        break
                    
                    # Check pending items if not found in running
                    if not in_queue:
                        pending_fields = ["queue_pending", "pending_items", "pending"]
                        for field in pending_fields:
                            if field in queue_data:
                                pending_items = queue_data[field]
                                status_placeholder.text(f"Found pending items in field '{field}': {type(pending_items)}")
                                
                                # List format
                                if isinstance(pending_items, list):
                                    for item in pending_items:
                                        # Dict with prompt_id
                                        if isinstance(item, dict) and "prompt_id" in item:
                                            item_id = item["prompt_id"]
                                            if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                                in_queue = True
                                                status_placeholder.info(f"⏳ Job is pending in queue (attempt {attempt}/{max_attempts})...")
                                                break
                                        # List with prompt_id at index 1
                                        elif isinstance(item, list) and len(item) > 1:
                                            item_id = item[1]
                                            if isinstance(item_id, str) and (item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id)):
                                                in_queue = True
                                                status_placeholder.info(f"⏳ Job is pending in queue (attempt {attempt}/{max_attempts})...")
                                                break
                                # Dict format
                                elif isinstance(pending_items, dict):
                                    for item_id, item_data in pending_items.items():
                                        if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                                            in_queue = True
                                            status_placeholder.info(f"⏳ Job is pending in queue (attempt {attempt}/{max_attempts})...")
                                            break
                    
                    if in_queue:
                        # If the job is in the queue, wait and try again
                        time.sleep(interval)
                        continue
            except Exception as e:
                status_placeholder.text(f"Error checking queue: {str(e)}")
            
            # If not in queue and not in history, try one more time with a direct history request
            try:
                # Try direct history endpoint with the prompt ID
                direct_history_url = f"{api_url}/history/{prompt_id}"
                direct_history_response = requests.get(direct_history_url, timeout=10)
                
                if direct_history_response.status_code == 200:
                    status_placeholder.text(f"Found job via direct history endpoint")
                    status_placeholder.info(f"⏳ Job found via direct history endpoint, waiting for completion...")
                    time.sleep(interval)
                    continue
            except Exception as e:
                status_placeholder.text(f"Error checking direct history: {str(e)}")
            
            # Check for VHS_VideoCombine outputs
            try:
                # Some systems use a different filename pattern - try common patterns
                status_placeholder.text("Checking for common video output file patterns...")
                
                # Common patterns for AnimateDiff and VHS_VideoCombine
                patterns = [
                    f"AnimateDiff_{prompt_id[:8]}.mp4",
                    f"ComfyUI_{prompt_id[:8]}.mp4",
                    "animation_00001.mp4",
                    "animation_00002.mp4",
                    "ComfyUI.mp4"
                ]
                
                for filename in patterns:
                    file_url = f"{api_url}/view?filename={filename}"
                    status_placeholder.text(f"Checking {file_url}")
                    
                    try:
                        head_response = requests.head(file_url, timeout=5)
                        if head_response.status_code == 200:
                            # File exists, try to download it
                            content_response = requests.get(file_url, timeout=60)
                            if content_response.status_code == 200:
                                status_placeholder.success(f"✅ Found video using pattern match: {filename}")
                                return {
                                    "status": "success",
                                    "content": content_response.content,
                                    "filename": filename,
                                    "type": "video"
                                }
                    except Exception as e:
                        status_placeholder.text(f"Error checking pattern {filename}: {str(e)}")
                        continue
            except Exception as e:
                status_placeholder.text(f"Error checking common patterns: {str(e)}")
            
            # If still not found, it's likely the job was deleted or never submitted
            status_placeholder.warning("⚠️ Prompt ID not found in history or queue. Will keep trying...")
        
        # Wait before trying again
        time.sleep(interval)
    
    # If we reached max attempts
    status_placeholder.error("❌ Timed out waiting for content")
    return {
        "status": "error",
        "message": f"Timed out after {max_attempts} attempts"
    }

# Function to save media content to file
def save_media_content(content, segment_type, segment_id, file_extension):
    """Save media content to a file"""
    # Create directories if they don't exist
    media_dir = project_path / "media" / segment_type
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{segment_type}_{segment_id}_{timestamp}.{file_extension}"
    
    # Save file
    file_path = media_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return relative path from project directory
    return str(file_path)

# Function to generate B-Roll sequentially
def generate_broll_sequentially(segments_data, api_url=None):
    """Generate B-Roll content sequentially with proper tracking"""
    if api_url is None:
        api_url = "http://100.115.243.42:8000"
    
    # Track progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Store results
    results = {}
    total_segments = len(segments_data)
    
    # Process each segment
    for idx, (segment_id, segment_data) in enumerate(segments_data.items()):
        # Update progress
        progress_value = idx / total_segments
        progress_bar.progress(progress_value)
        status_text.text(f"Processing segment {idx+1}/{total_segments}: {segment_id}")
        
        # Create segment container for output
        segment_container = st.container()
        
        with segment_container:
            st.subheader(f"Segment {segment_id}")
            
            # Check segment_data type and handle accordingly
            if isinstance(segment_data, dict):
                # It's a dictionary, use get() method
                is_video = segment_data.get("is_video", True)
                prompt_text = segment_data.get("prompt", "")
                negative_prompt = segment_data.get("negative_prompt", "ugly, blurry, low quality")
            elif isinstance(segment_data, str):
                # It's a string, use it directly as the prompt
                is_video = True  # Default to video for string prompts
                prompt_text = segment_data
                negative_prompt = "ugly, blurry, low quality"
            else:
                # Unknown type, log and skip
                st.error(f"Unknown data type for segment {segment_id}: {type(segment_data)}")
                results[segment_id] = {"status": "error", "message": f"Invalid data type: {type(segment_data)}"}
                continue
                
            content_type = "video" if is_video else "image"
            
            # Create client ID for tracking
            client_id = f"streamlit_broll_{segment_id}_{int(time.time())}"
            
            # Load workflow
            workflow = load_workflow("video" if is_video else "image")
            if workflow is None:
                st.error(f"Failed to load workflow for {segment_id}")
                results[segment_id] = {"status": "error", "message": "Failed to load workflow"}
                continue
                
            # Get parameters
            params = {
                "prompt": prompt_text,
                "negative_prompt": negative_prompt,
                "width": 1080,
                "height": 1920,
                "seed": random.randint(1, 999999999)
            }
            
            # Display the prompt
            st.text_area("Prompt", value=prompt_text, height=100)
            
            # Modify workflow
            modified_workflow = modify_workflow(workflow, params)
            if modified_workflow is None:
                st.error(f"Failed to modify workflow for {segment_id}")
                results[segment_id] = {"status": "error", "message": "Failed to modify workflow"}
                continue
            
            # Submit job
            st.info(f"Submitting {content_type} generation job")
            
            try:
                # Submit the workflow to ComfyUI
                result = submit_comfyui_workflow(modified_workflow)
                
                if result["status"] != "success":
                    st.error(f"Failed to submit job: {result.get('message', 'Unknown error')}")
                    results[segment_id] = {"status": "error", "message": f"Job submission failed: {result.get('message', 'Unknown error')}"}
                    continue
                    
                prompt_id = result["prompt_id"]
                st.info(f"Job submitted with ID: {prompt_id}")
                
                # Store the prompt ID
                if "broll_fetch_ids" not in st.session_state:
                    st.session_state.broll_fetch_ids = {}
                st.session_state.broll_fetch_ids[segment_id] = prompt_id
                
                # Fetch content
                st.info("Waiting for content generation to complete...")
                fetch_result = periodic_content_fetch(prompt_id, api_url)
                
                if fetch_result["status"] == "success":
                    # Save content
                    content = fetch_result["content"]
                    file_ext = "mp4" if is_video else "png"
                    file_path = save_media_content(content, "broll", segment_id, file_ext)
                    
                    # Update status
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "complete",
                        "file_path": file_path,
                        "prompt_id": prompt_id,
                        "content_type": content_type,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Display result
                    st.success(f"Successfully generated {content_type} for segment {segment_id}")
                    if is_video:
                        st.video(file_path)
                    else:
                        st.image(file_path)
                        
                    results[segment_id] = {
                        "status": "success", 
                        "file_path": file_path,
                        "prompt_id": prompt_id
                    }
                else:
                    # Try direct download for AnimateDiff patterns
                    if is_video:
                        downloaded = False
                        possible_files = [f"animation_{i:05d}.mp4" for i in range(1, 10)]
                        
                        for filename in possible_files:
                            file_url = f"{api_url}/view?filename={filename}"
                            try:
                                response = requests.head(file_url, timeout=5)
                                if response.status_code == 200:
                                    content_response = requests.get(file_url, timeout=60)
                                    if content_response.status_code == 200:
                                        # Save file
                                        file_path = save_media_content(content_response.content, "broll", segment_id, "mp4")
                                        
                                        # Update status
                                        st.session_state.content_status["broll"][segment_id] = {
                                            "status": "complete",
                                            "file_path": file_path,
                                            "prompt_id": prompt_id,
                                            "content_type": "video",
                                            "filename": filename,
                                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        }
                                        
                                        st.success(f"Found and downloaded video from pattern {filename}")
                                        st.video(file_path)
                                        
                                        results[segment_id] = {
                                            "status": "success", 
                                            "file_path": file_path,
                                            "prompt_id": prompt_id
                                        }
                                        downloaded = True
                                        break
                            except Exception as e:
                                st.warning(f"Error checking file {filename}: {str(e)}")
                    
                        if not downloaded:
                            st.error(f"Failed to generate content: {fetch_result.get('message', 'Unknown error')}")
                            results[segment_id] = {"status": "error", "message": fetch_result.get('message', 'Content generation failed')}
                    else:
                        st.error(f"Failed to generate content: {fetch_result.get('message', 'Unknown error')}")
                        results[segment_id] = {"status": "error", "message": fetch_result.get('message', 'Content generation failed')}
            except Exception as e:
                st.error(f"Error processing segment {segment_id}: {str(e)}")
                results[segment_id] = {"status": "error", "message": str(e)}
            
            # Add a separator between segments
            st.divider()
            
            # Wait a bit before next job to give ComfyUI time to recover
            if idx < total_segments - 1:
                time.sleep(3)
    
    # Update final progress
    progress_bar.progress(1.0)
    status_text.text(f"Completed processing {total_segments} segments!")
    
    return results

# Define the B-Roll generation UI function
def render_broll_generation_section(unique_key="main"):
    """Render the B-Roll generation section with a single 'Generate All B-Roll' button
    
    Args:
        unique_key: A unique identifier to append to widget keys to avoid duplicates
    """
    # Create a single column for B-roll generation (removing the two-column approach)
    broll_gen_col = st.container()
    
    with broll_gen_col:
        if st.button("🎨 Generate All B-Roll", type="primary", key=f"generate_broll_{unique_key}", use_container_width=True):
            # Capture all required data before starting the thread
            temp_segments = st.session_state.segments.copy() if hasattr(st.session_state, 'segments') and st.session_state.segments else []
            
            # Check how broll_prompts is structured and extract appropriately
            broll_prompts = {}
            if hasattr(st.session_state, 'broll_prompts_full') and st.session_state.broll_prompts_full:
                # First try the full structure that has both prompts and metadata
                if "prompts" in st.session_state.broll_prompts_full:
                    broll_prompts = st.session_state.broll_prompts_full["prompts"]
                    print(f"Debug - Using prompts from broll_prompts_full structure: {len(broll_prompts)} prompts")
            elif hasattr(st.session_state, 'broll_prompts'):
                # Fallback to direct structure
                if isinstance(st.session_state.broll_prompts, dict):
                    if "prompts" in st.session_state.broll_prompts:
                        broll_prompts = st.session_state.broll_prompts["prompts"]
                        print(f"Debug - Using prompts from nested broll_prompts structure: {len(broll_prompts)} prompts")
                    else:
                        broll_prompts = st.session_state.broll_prompts
                        print(f"Debug - Using prompts directly from broll_prompts: {len(broll_prompts)} prompts")
            
            # Debug log what we found
            print(f"Debug - Segments count: {len(temp_segments)}")
            print(f"Debug - Available prompts: {list(broll_prompts.keys())}")
            
            # Process segments - this should work whether we have segment objects or just segment IDs
            broll_segments = {}
            
            # First try with direct matching if we have actual segment objects
            if temp_segments:
                for i, seg in enumerate(temp_segments):
                    segment_id = f"segment_{i}"
                    # Check both possible structures for prompts
                    if segment_id in broll_prompts:
                        broll_segments[segment_id] = broll_prompts[segment_id]
                        print(f"Debug - Found prompt for segment {segment_id}")
            
            # If we still don't have any segments, try using the prompts directly
            if not broll_segments and broll_prompts:
                print(f"Debug - Using prompts directly as no matching segments found")
                broll_segments = broll_prompts
            
            # Final check
            if not broll_segments:
                # Try loading script.json directly as a last resort
                script_file = project_path / "script.json"
                if script_file.exists():
                    try:
                        with open(script_file, "r") as f:
                            script_data = json.load(f)
                            if "segments" in script_data:
                                # Find B-Roll segments
                                for i, segment in enumerate(script_data["segments"]):
                                    if isinstance(segment, dict) and segment.get("type") == "B-Roll":
                                        segment_id = f"segment_{i}"
                                        if segment_id in broll_prompts:
                                            broll_segments[segment_id] = broll_prompts[segment_id]
                                            print(f"Debug - Found prompt for B-Roll segment {segment_id} from script.json")
                    except Exception as e:
                        print(f"Error loading script.json: {str(e)}")
            
            if not broll_segments:
                st.error("No B-roll segments to process. Please create segments and generate prompts first.")
                st.info("Go to 'A-Roll Transcription' to create segments with B-Roll prompts.")
            else:
                # Generate B-roll sequentially
                st.subheader("B-Roll Generation in Progress")
                print(f"Debug - Proceeding with {len(broll_segments)} B-Roll segments")
                result = generate_broll_sequentially(broll_segments)
                
                # Save updated content status
                save_content_status()
                
                # Show summary
                success_count = sum(1 for r in result.values() if r.get('status') == 'success')
                st.success(f"Completed B-roll generation: {success_count} successful out of {len(broll_segments)} segments.")
                
                # Mark step as complete if all segments succeeded
                if success_count == len(broll_segments):
                    mark_step_complete('content_production')
                    st.balloons()  # Add some fun!

# Main B-Roll content generation section
def main():
    # Header and instructions
    st.title("B-Roll Video Production")
    render_step_header(3, "B-Roll Video Production", 6)
    
    st.write("""
    Generate B-Roll visuals based on your script and prompts. This step turns your B-Roll text prompts into visual content 
    that will be combined with your A-Roll video in the next step.
    """)
    
    # Load data
    has_script = load_script_data()
    has_prompts = load_broll_prompts()
    has_status = load_content_status()
    
    if not has_script:
        st.error("No script found. Please complete the Script Segmentation or A-Roll Transcription step first.")
        return
    
    if not has_prompts:
        st.warning("No B-Roll prompts found. We'll use default placeholders for now.")
    
    # Display info about B-Roll type
    broll_type = st.session_state.get("broll_type", "video").lower()

    # If broll_type is "mixed" or another unexpected value, default to video
    if broll_type not in ["video", "image"]:
        broll_type = "video"
        st.warning("B-Roll type could not be determined. Defaulting to video.")

    st.info(f"B-Roll type: **{broll_type.upper()}**")
    
    # Create tabs to organize content
    broll_tabs = st.tabs(["Content Generation", "Status & Preview"])
    
    with broll_tabs[0]:
        # Simple section for fetching existing B-Roll by ID
        st.subheader("Fetch Existing B-Roll Content")
        
        # Get B-Roll segments
        broll_segments = [segment for segment in st.session_state.segments if segment["type"] == "B-Roll"]
        
        if not broll_segments:
            st.warning("No B-Roll segments found. Please complete the A-Roll Transcription step first.")
            return
        
        # Show simplified ID input form
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            col1, col2 = st.columns([4, 1])
            
            with col1:
                b_roll_id = st.text_input(
                    f"B-Roll ID for Segment {i+1}",
                    value=st.session_state.broll_fetch_ids.get(segment_id, ""),
                    key=f"broll_id_segment_{segment_id}_{int(time.time())}"
                )
                st.session_state.broll_fetch_ids[segment_id] = b_roll_id
                
            with col2:
                if st.button("Reset", key=f"reset_btn_{segment_id}"):
                    # Default IDs if needed
                    default_ids = {
                        "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",
                        "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257"
                    }
                    st.session_state.broll_fetch_ids[segment_id] = default_ids.get(segment_id, "")
                    st.rerun()
        
        # Fetch button
        if st.button("🔄 Fetch B-Roll Content", type="primary", key="fetch_broll_button"):
            with st.spinner("Fetching content from provided IDs..."):
                fetch_success = False
                
                # Count the number of IDs we have
                broll_id_count = sum(1 for id in st.session_state.broll_fetch_ids.values() if id)
                
                st.info(f"Found {broll_id_count} B-Roll IDs to fetch")
                    
                # Process B-Roll IDs
                for segment_id, prompt_id in st.session_state.broll_fetch_ids.items():
                    if not prompt_id:
                        continue
                    
                    # Set status to "fetching" to show progress
                    update_content_status(
                        segment_id=segment_id,
                        segment_type="broll",
                        status="fetching",
                        message=f"Fetching content for ID: {prompt_id}",
                        prompt_id=prompt_id
                    )
                    
                    # Get the appropriate API URL - assuming video API
                    api_url = COMFYUI_VIDEO_API_URL
                    
                    # Fetch the content
                    result = fetch_comfyui_content_by_id(api_url, prompt_id)
                    
                    if result["status"] == "success":
                        # Determine file extension based on content type
                        content_type = result.get("type", "image")
                        file_ext = "mp4" if content_type == "video" else "png"
                        
                        # Save the fetched content
                        file_path = save_media_content(
                            result["content"], 
                            "broll",
                            segment_id,
                            file_ext
                        )
                        
                        # Update content status
                        update_content_status(
                            segment_id=segment_id,
                            segment_type="broll",
                            status="complete",
                            file_path=file_path,
                            prompt_id=prompt_id,
                            content_type=content_type,
                            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        fetch_success = True
                        st.success(f"Successfully fetched content for segment {segment_id}")
                    elif result["status"] == "processing":
                        # Content is still being generated
                        update_content_status(
                            segment_id=segment_id,
                            segment_type="broll",
                            status="waiting",
                            message="ComfyUI job still processing. Try again later.",
                            prompt_id=prompt_id,
                            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        st.warning(f"Content for segment {segment_id} is still processing. Try again later.")
                    else:
                        # Error fetching content
                        update_content_status(
                            segment_id=segment_id,
                            segment_type="broll",
                            status="error",
                            message=result.get("message", "Unknown error fetching content"),
                            prompt_id=prompt_id,
                            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        st.error(f"Error fetching content for segment {segment_id}: {result.get('message', 'Unknown error')}")
                
                # Save the updated content status
                save_content_status()
                
                if fetch_success:
                    st.success("Successfully fetched content from provided IDs!")
                else:
                    st.warning("No content was fetched. Please check your IDs and try again.")
        
        st.divider()
        
        # B-Roll generation section
        st.subheader("Generate B-Roll Content")
        st.write("Generate new B-Roll video content based on your prompts.")
        
        # Create a single button for B-roll generation
        if st.button("🎨 Generate All B-Roll", type="primary", use_container_width=True, key="generate_all_broll"):
            # Capture all required data before starting the processing
            temp_segments = st.session_state.segments.copy() if hasattr(st.session_state, 'segments') and st.session_state.segments else []
            
            # Check how broll_prompts is structured and extract appropriately
            broll_prompts = {}
            if hasattr(st.session_state, 'broll_prompts_full') and st.session_state.broll_prompts_full:
                # First try the full structure that has both prompts and metadata
                if "prompts" in st.session_state.broll_prompts_full:
                    broll_prompts = st.session_state.broll_prompts_full["prompts"]
                    print(f"Debug - Using prompts from broll_prompts_full structure: {len(broll_prompts)} prompts")
            elif hasattr(st.session_state, 'broll_prompts'):
                # Fallback to direct structure
                if isinstance(st.session_state.broll_prompts, dict):
                    if "prompts" in st.session_state.broll_prompts:
                        broll_prompts = st.session_state.broll_prompts["prompts"]
                        print(f"Debug - Using prompts from nested broll_prompts structure: {len(broll_prompts)} prompts")
                    else:
                        broll_prompts = st.session_state.broll_prompts
                        print(f"Debug - Using prompts directly from broll_prompts: {len(broll_prompts)} prompts")
            
            # Debug log what we found
            print(f"Debug - Segments count: {len(temp_segments)}")
            print(f"Debug - Available prompts: {list(broll_prompts.keys())}")
            
            # Process segments - this should work whether we have segment objects or just segment IDs
            broll_segments = {}
            
            # First try with direct matching if we have actual segment objects
            if temp_segments:
                for i, seg in enumerate(temp_segments):
                    segment_id = f"segment_{i}"
                    # Check both possible structures for prompts
                    if segment_id in broll_prompts:
                        broll_segments[segment_id] = broll_prompts[segment_id]
                        print(f"Debug - Found prompt for segment {segment_id}")
            
            # If we still don't have any segments, try using the prompts directly
            if not broll_segments and broll_prompts:
                print(f"Debug - Using prompts directly as no matching segments found")
                broll_segments = broll_prompts
            
            # Final check
            if not broll_segments:
                # Try loading script.json directly as a last resort
                script_file = project_path / "script.json"
                if script_file.exists():
                    try:
                        with open(script_file, "r") as f:
                            script_data = json.load(f)
                            if "segments" in script_data:
                                # Find B-Roll segments
                                for i, segment in enumerate(script_data["segments"]):
                                    if isinstance(segment, dict) and segment.get("type") == "B-Roll":
                                        segment_id = f"segment_{i}"
                                        if segment_id in broll_prompts:
                                            broll_segments[segment_id] = broll_prompts[segment_id]
                                            print(f"Debug - Found prompt for B-Roll segment {segment_id} from script.json")
                    except Exception as e:
                        print(f"Error loading script.json: {str(e)}")
            
            if not broll_segments:
                st.error("No B-roll segments to process. Please create segments and generate prompts first.")
                st.info("Go to 'A-Roll Transcription' to create segments with B-Roll prompts.")
            else:
                # Generate B-roll sequentially
                st.subheader("B-Roll Generation in Progress")
                print(f"Debug - Proceeding with {len(broll_segments)} B-Roll segments")
                result = generate_broll_sequentially(broll_segments)
                
                # Save updated content status
                save_content_status()
                
                # Show summary
                success_count = sum(1 for r in result.values() if r.get('status') == 'success')
                st.success(f"Completed B-roll generation: {success_count} successful out of {len(broll_segments)} segments.")
                
                # Mark step as complete if all segments succeeded
                if success_count == len(broll_segments):
                    mark_step_complete('content_production')
                    st.balloons()  # Add some fun!
    
    with broll_tabs[1]:
        # Display generation status
        st.subheader("B-Roll Status")
        
        if "broll" in st.session_state.content_status and st.session_state.content_status["broll"]:
            for i, segment in enumerate(broll_segments):
                segment_id = f"segment_{i}"
                if segment_id in st.session_state.content_status["broll"]:
                    status = st.session_state.content_status["broll"][segment_id]
                    
                    with st.expander(f"B-Roll Segment {i+1}", expanded=False):
                        # Display prompt info
                        if "prompts" in st.session_state.broll_prompts and segment_id in st.session_state.broll_prompts["prompts"]:
                            prompt_data = st.session_state.broll_prompts["prompts"][segment_id]
                            if isinstance(prompt_data, dict):
                                prompt_text = prompt_data.get("prompt", "No prompt available")
                            else:
                                prompt_text = prompt_data
                            st.markdown(f"**Prompt:** {prompt_text}")
                        
                        # Display status and result
                        if status['status'] == "complete":
                            st.markdown(f"**Status:** ✅ Completed")
                            if 'file_path' in status:
                                st.markdown(f"**File:** {status['file_path']}")
                                # Try to display the video or image if available
                                try:
                                    if status['file_path'].endswith(('.mp4', '.mov')):
                                        st.video(status['file_path'])
                                    elif status['file_path'].endswith(('.png', '.jpg', '.jpeg')):
                                        st.image(status['file_path'])
                                except Exception as e:
                                    st.error(f"Error displaying file: {str(e)}")
                        elif status['status'] == "error":
                            st.error(f"**Status:** ❌ Error")
                            st.error(f"**Error:** {status.get('message', 'Unknown error')}")
                        elif status['status'] == "processing":
                            st.info(f"**Status:** ⚙️ Processing")
                            st.info(f"**Message:** {status.get('message', 'Processing...')}")
                        elif status['status'] == "waiting":
                            st.info(f"**Status:** ⏳ Waiting")
                            st.info(f"**Message:** {status.get('message', 'Waiting for ComfyUI...')}")
                        elif status['status'] == "fetching":
                            st.info(f"**Status:** 🔄 Fetching")
                            st.info(f"**Message:** {status.get('message', 'Fetching content...')}")
                        else:
                            st.info(f"**Status:** ℹ️ {status['status']}")
                            
                        # Show retry button for error or waiting status
                        if status['status'] in ["error", "waiting"]:
                            if st.button(f"Retry for Segment {i+1}", key=f"retry_{segment_id}"):
                                # Remove the status entry to allow retrying
                                if segment_id in st.session_state.content_status["broll"]:
                                    del st.session_state.content_status["broll"][segment_id]
                                st.rerun()
        else:
            st.info("No B-Roll content has been generated yet.")
    
    # Navigation buttons
    st.divider()
    render_step_navigation(
        current_step=3,
        prev_step_path="pages/4.5_ARoll_Transcription.py",
        next_step_path="pages/6_Video_Assembly.py"
    )

def get_correct_workflow_file(content_type):
    """Determine the correct workflow file based on content type
    This function bypasses any issues with the load_workflow function
    """
    try:
        # For image content, always use flux_schnell.json
        if content_type == "image":
            flux_path = os.path.join(os.getcwd(), "flux_schnell.json")
            if os.path.exists(flux_path):
                print(f"Using image workflow: {flux_path}")
if __name__ == "__main__":
    main()