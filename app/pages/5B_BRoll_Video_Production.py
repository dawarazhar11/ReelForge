import streamlit as st
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

# Import custom helper module for ComfyUI integration
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app"))
import comfyui_helpers

# Fix import paths for components and utilities
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"Added {parent_dir} to path")

# Try to import local modules# Try to import local modules
try:
    from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation, render_step_navigation
    from components.progress import render_step_header
    from utils.session_state import get_settings, get_project_path, mark_step_complete
    from utils.progress_tracker import start_comfyui_tracking
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Failed to import local modules: {str(e)}")
    st.stop()
# Set page configuration
st.set_page_config(
    page_title="B-Roll Video Production | AI Money Printer",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

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
COMFYUI_VIDEO_API_URL = "http://100.86.185.76:8000"
JSON_TEMPLATES = {
    "image": {
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
if "max_broll_segments" not in st.session_state:
    st.session_state.max_broll_segments = 999  # Default to process all segments

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
    
    # Print more debug info
    print(f"Debug - Looking for B-Roll prompts at: {prompts_file.absolute()}")
    
    if prompts_file.exists():
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                
                # Print debug info
                print(f"Debug - Loading B-Roll prompts from {prompts_file}")
                print(f"Debug - JSON data keys: {list(data.keys())}")
                
                # Validate data structure
                if not isinstance(data, dict):
                    print("Error: B-Roll prompts file has invalid format")
                    return False
                
                # Handle different JSON structures
                if "prompts" in data and isinstance(data["prompts"], dict):
                    # New format: {"prompts": {"segment_0": {...}, ...}, "broll_type": "..."}
                    prompts_data = data["prompts"]
                    broll_type = data.get("broll_type", "video")
                    
                    # Count prompts
                    prompt_count = sum(1 for segment_id, prompt_data in prompts_data.items() 
                                     if isinstance(prompt_data, dict) and "prompt" in prompt_data)
                    
                    print(f"Debug - Found {prompt_count} B-Roll prompts")
                    print(f"Debug - Segment IDs: {list(prompts_data.keys())}")
                    
                    # Update session state if we have valid prompts
                    if prompt_count > 0:
                        st.session_state.broll_prompts = data
                        st.session_state.broll_type = broll_type
                        return True
                else:
                    # Legacy format: {"segment_0": {...}, ...}
                    # Count prompts
                    prompt_count = sum(1 for segment_id, prompt_data in data.items() 
                                     if isinstance(prompt_data, dict) and "prompt" in prompt_data)
                    
                    print(f"Debug - Found {prompt_count} B-Roll prompts")
                    
                    # Update session state if we have valid prompts
                    if prompt_count > 0:
                        st.session_state.broll_prompts = {"prompts": data, "broll_type": "video"}
                        return True
                
                print("Warning: No valid B-Roll prompts found")
                return False
        except json.JSONDecodeError:
            print(f"Error: broll_prompts.json is not valid JSON")
            return False
        except Exception as e:
            print(f"Error loading B-Roll prompts: {str(e)}")
            return False
    else:
        print(f"B-Roll prompts file not found at: {prompts_file.absolute()}")
        
        # Try alternate location
        alt_prompts_file = Path("config/user_data/my_short_video/broll_prompts.json")
        print(f"Trying alternate location: {alt_prompts_file.absolute()}")
        
        if alt_prompts_file.exists():
            try:
                with open(alt_prompts_file, "r") as f:
                    data = json.load(f)
                    
                    # Print debug info
                    print(f"Debug - Loading B-Roll prompts from alternate location: {alt_prompts_file}")
                    print(f"Debug - JSON data keys: {list(data.keys())}")
                    
                    # Validate data structure
                    if not isinstance(data, dict):
                        print("Error: B-Roll prompts file has invalid format")
                        return False
                    
                    # Handle different JSON structures
                    if "prompts" in data and isinstance(data["prompts"], dict):
                        # New format: {"prompts": {"segment_0": {...}, ...}, "broll_type": "..."}
                        prompts_data = data["prompts"]
                        broll_type = data.get("broll_type", "video")
                        
                        # Count prompts
                        prompt_count = sum(1 for segment_id, prompt_data in prompts_data.items() 
                                         if isinstance(prompt_data, dict) and "prompt" in prompt_data)
                        
                        print(f"Debug - Found {prompt_count} B-Roll prompts")
                        print(f"Debug - Segment IDs: {list(prompts_data.keys())}")
                        
                        # Update session state if we have valid prompts
                        if prompt_count > 0:
                            st.session_state.broll_prompts = data
                            st.session_state.broll_type = broll_type
                            return True
                    else:
                        # Legacy format: {"segment_0": {...}, ...}
                        # Count prompts
                        prompt_count = sum(1 for segment_id, prompt_data in data.items() 
                                         if isinstance(prompt_data, dict) and "prompt" in prompt_data)
                        
                        print(f"Debug - Found {prompt_count} B-Roll prompts")
                        
                        # Update session state if we have valid prompts
                        if prompt_count > 0:
                            st.session_state.broll_prompts = {"prompts": data, "broll_type": "video"}
                            return True
                    
                    print("Warning: No valid B-Roll prompts found in alternate location")
                    return False
            except json.JSONDecodeError:
                print(f"Error: broll_prompts.json is not valid JSON")
                return False
            except Exception as e:
                print(f"Error loading B-Roll prompts: {str(e)}")
                return False
        
        print("B-Roll prompts file not found in any location")
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
    Submit a workflow to ComfyUI and return a standardized result
    
    Args:
        workflow: The prepared ComfyUI workflow to submit
        
    Returns:
        dict: Result with status and prompt_id fields
    """
    try:
        # Validate the workflow
        if not workflow:
            return {"status": "error", "message": "Invalid workflow - cannot submit"}
        
        # Use the correct ComfyUI server URL
        api_url = COMFYUI_VIDEO_API_URL
        print(f"Submitting job to ComfyUI at: {api_url}")
        
        # Submit the workflow
        response = requests.post(f"{api_url}/prompt", json=workflow, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Job submitted successfully. Response: {result}")
            
            # Extract the prompt_id from the response
            if "prompt_id" in result:
                prompt_id = result["prompt_id"]
                
                # Save the prompt_id for tracking
                if "broll_fetch_ids" not in st.session_state:
                    st.session_state.broll_fetch_ids = {}
                
                # Set up progress tracking
                tracker = start_comfyui_tracking(prompt_id, api_url)
                if "active_trackers" not in st.session_state:
                    st.session_state.active_trackers = []
                st.session_state.active_trackers.append(tracker)
                
                return {
                    "status": "success",
                    "prompt_id": prompt_id,
                    "message": "Job submitted successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"No prompt_id in response: {result}"
                }
        else:
            error_message = f"Error submitting job. Status code: {response.status_code}"
            print(error_message)
            try:
                error_detail = response.json()
                print(f"Response content: {error_detail}")
            except:
                error_detail = response.text
                print(f"Response text: {error_detail}")
            
            return {
                "status": "error",
                "message": error_message,
                "detail": str(error_detail)
            }
    except Exception as e:
        error_message = f"Exception while submitting job: {str(e)}"
        print(error_message)
        return {
            "status": "error",
            "message": error_message
        }

# Function to check ComfyUI job status
def check_comfyui_job_status(api_url, prompt_id):
    """
    Check the status of a ComfyUI job
    """
    try:
        # Use the correct ComfyUI server URL
        api_url = "http://100.115.243.42:8000"
        print(f"Checking job status at: {api_url}/history/{prompt_id}")
        
        response = requests.get(f"{api_url}/history/{prompt_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error checking job status. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error checking job status: {str(e)}")
        return None

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
        # First check if the job exists in history
        history_url = f"{api_url}/history/{prompt_id}"
        print(f"\n1. Checking history at: {history_url}")
        
        history_response = make_request(history_url, timeout=60)
        print(f"History response status: {history_response.status_code}")
        
        if history_response.status_code != 200:
            error_msg = f"Error fetching history: {history_response.status_code}. Server might be busy, try again later."
            print(error_msg)
            return {"status": "error", "message": error_msg}
            
        job_data = history_response.json()
        print(f"Job data keys: {list(job_data.keys())}")
        
        if prompt_id not in job_data:
            error_msg = f"Prompt ID '{prompt_id}' not found in history. The job may have been deleted or hasn't been submitted yet."
            print(error_msg)
            st.warning(error_msg)
            return {"status": "error", "message": "Prompt ID not found in history"}
            
        # Get the job data
        job_info = job_data[prompt_id]
        print(f"\n2. Job info keys: {list(job_info.keys())}")
        
        # Check if job has outputs
        if "outputs" in job_info and job_info["outputs"]:
            outputs = job_info["outputs"]
            print(f"\n3. Output nodes: {list(outputs.keys())}")
            
            # Iterate through output nodes to find image/video output
            for node_id, node_data in outputs.items():
                print(f"\n4. Processing node: {node_id}")
                print(f"Node data keys: {list(node_data.keys())}")
                
                # Check for images
                if "images" in node_data:
                    print(f"Found {len(node_data['images'])} images")
                    for image_data in node_data["images"]:
                        filename = image_data["filename"]
                        file_type = image_data.get("type", "image")
                        print(f"Processing image: {filename} (type: {file_type})")
                        
                        # Download the file
                        file_url = f"{api_url}/view?filename={filename}"
                        print(f"Downloading from: {file_url}")
                        
                        content_response = make_request(file_url, timeout=120)
                        if content_response.status_code == 200:
                            print(f"Successfully downloaded image: {filename}")
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "prompt_id": prompt_id,
                                "type": file_type
                            }
                        else:
                            print(f"Failed to download image. Status code: {content_response.status_code}")
                
                # Check for videos and other media files
                for media_type in ["videos", "gifs", "mp4"]:
                    if media_type in node_data:
                        print(f"Found {len(node_data[media_type])} {media_type}")
                        for media_item in node_data[media_type]:
                            filename = media_item.get("filename", "")
                            if filename:
                                # Determine actual file type from extension
                                file_ext = os.path.splitext(filename)[1].lower()
                                actual_type = "video" if file_ext == ".mp4" else media_type
                                
                                print(f"Processing {actual_type}: {filename}")
                                
                                # Download the file
                                file_url = f"{api_url}/view?filename={filename}"
                                print(f"Downloading from: {file_url}")
                                
                                content_response = make_request(file_url, timeout=180)
                                if content_response.status_code == 200:
                                    print(f"Successfully downloaded {actual_type}: {filename}")
                                    return {
                                        "status": "success",
                                        "content": content_response.content,
                                        "filename": filename,
                                        "prompt_id": prompt_id,
                                        "type": actual_type
                                    }
                                else:
                                    print(f"Failed to download {actual_type}. Status code: {content_response.status_code}")
            
            # Check for AnimateDiff outputs
            print("\n5. Checking for AnimateDiff outputs")
            possible_files = [f"animation_{i:05d}.mp4" for i in range(1, 10)]
            for filename in possible_files:
                try:
                    file_url = f"{api_url}/view?filename={filename}"
                    print(f"Checking: {file_url}")
                    
                    response = make_request(file_url, method='head', timeout=30)
                    if response.status_code == 200:
                        print(f"Found AnimateDiff file: {filename}")
                        content_response = make_request(file_url, timeout=180)
                        if content_response.status_code == 200:
                            print(f"Successfully downloaded AnimateDiff output: {filename}")
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "prompt_id": prompt_id,
                                "type": "video",
                                "note": "Found using filename pattern"
                            }
                except Exception as e:
                    print(f"Error checking AnimateDiff file {filename}: {str(e)}")
            
            # If we got here, we couldn't find any output files
            error_msg = "No output file found in job results"
            print(error_msg)
            return {"status": "error", "message": error_msg}
        else:
            # Job is still processing
            status_msg = "Job is still processing"
            print(status_msg)
            return {"status": "processing", "message": status_msg}
            
    except requests.exceptions.Timeout as e:
        error_msg = f"Timeout while fetching content after {max_retries} attempts. The server may be busy. Error: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Could not connect to ComfyUI API at {api_url} after {max_retries} attempts. The server might be down. Error: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Error fetching content: {str(e)}"
        print(error_msg)
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
    """Submit B-Roll prompts to the video server for processing, respecting the max_broll_segments limit"""
    broll_segments = [s for s in st.session_state.segments if s["type"] == "B-Roll"]
    prompt_ids = {}
    errors = {}
    
    # Apply segment limit
    max_segments = min(st.session_state.max_broll_segments, len(broll_segments))
    limited_broll_segments = broll_segments[:max_segments]
    
    # Show message about segment limit
    if max_segments < len(broll_segments):
        st.info(f"Processing {max_segments} out of {len(broll_segments)} B-Roll segments based on your limit setting.")
    else:
        st.info(f"Processing all {len(broll_segments)} B-Roll segments.")
    
    # Reset batch process status
    st.session_state.batch_process_status["submitted"] = True
    st.session_state.batch_process_status["prompt_ids"] = {}
    st.session_state.batch_process_status["errors"] = {}
    
    # Get the workflow template path for video
    template_file = JSON_TEMPLATES["video"]
    
    # Debug information
    print(f"Debug - Starting batch processing for {len(limited_broll_segments)} of {len(broll_segments)} B-Roll segments")
    print(f"Debug - B-Roll prompts keys: {list(st.session_state.broll_prompts.keys())}")
    if "prompts" in st.session_state.broll_prompts:
        print(f"Debug - Prompts sub-keys: {list(st.session_state.broll_prompts['prompts'].keys())}")
    
    # Process each B-Roll segment up to the limit
    for i, segment in enumerate(limited_broll_segments):
        segment_id = f"segment_{i}"
        
        # Check if we have prompts for this segment
        if "prompts" in st.session_state.broll_prompts and segment_id in st.session_state.broll_prompts["prompts"]:
            prompt_data = st.session_state.broll_prompts["prompts"][segment_id]
            
            print(f"Debug - Processing segment {segment_id} with prompt data: {prompt_data.keys() if isinstance(prompt_data, dict) else 'not a dict'}")
            
            # Prepare the workflow
            workflow = prepare_comfyui_workflow(
                template_file,
                prompt_data["prompt"],
                prompt_data.get("negative_prompt", "ugly, blurry, low quality"),
                resolution="1080x1920"
            )
            
            # Display the prepared prompt in the UI
            st.info(f"Preparing prompt for Segment {i+1}...")
            st.text_area(f"Segment {i+1} Prompt", value=prompt_data["prompt"], height=150, key=f"prompt_view_{i}")
            
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
                    error_msg = result.get("message", "Unknown error")
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
            print(f"Debug - Available segments: {list(st.session_state.broll_prompts.get('prompts', {}).keys())}")
            
            # Update content status to show missing prompt
            update_content_status(
                segment_id=segment_id,
                segment_type="broll",
                status="error",
                message="No prompt available. Please create a B-Roll prompt first."
            )
            
            st.warning(f"No prompt found for B-Roll Segment {i+1}. Please generate prompts first.")
    
    # Return results
    return {
        "status": "success" if not errors else "partial_success" if prompt_ids else "error",
        "prompt_ids": prompt_ids,
        "errors": errors
    }

# Function for A-Roll content generation only
def generate_aroll_content(segments, aroll_fetch_ids):
    """Generate A-Roll content only - DISABLED: Use 4.5_ARoll_Transcription.py instead"""
    # This function is disabled - A-Roll generation should be done in the dedicated 4.5 page
    st.warning("⚠️ A-Roll generation is disabled in this page. Please use the 'A-Roll Transcription' page instead.")
    
    # Mark as complete immediately to avoid issues
    if "parallel_tasks" in st.session_state:
        st.session_state.parallel_tasks["completed"] = 1
        st.session_state.parallel_tasks["running"] = False
        
    return {
        "status": "error",
        "message": "A-Roll generation is disabled in this page. Please use the 'A-Roll Transcription' page instead."
    }

# Function for parallel content generation
def generate_content_parallel(segments, broll_prompts, manual_upload, broll_fetch_ids, workflow_selection):
    """
    Generate B-Roll content for all segments, either through API or manual upload
    
    Args:
        segments: List of segments to generate B-Roll for
        broll_prompts: Dictionary of B-Roll prompts
        manual_upload: Whether to use manual upload
        broll_fetch_ids: IDs of B-Roll videos to fetch (if manual upload)
        workflow_selection: ComfyUI workflow selection
        
    Returns:
        dict: Status of content generation
    """
    # Only generate for B-Roll segments
    broll_segments = [s for s in segments if s.get("type") == "B-Roll"]
    
    if not broll_segments:
        st.warning("No B-Roll segments found. Please complete the Script Segmentation step first.")
        return {
            "status": "error",
            "message": "No B-Roll segments found"
        }
        
    # Initialize result
    result = {
        "status": "success",
        "generated": 0,
        "errors": {}
    }
    
    # Generate B-Roll content
    try:
        broll_result = generate_broll_content(
            broll_segments, 
            broll_prompts, 
            broll_fetch_ids, 
            workflow_selection
        )
        
        if "status" in broll_result and broll_result["status"] == "success":
            result["generated"] += broll_result.get("generated", 0)
            result["broll"] = broll_result
        else:
            result["errors"]["broll"] = broll_result.get("message", "Unknown error")
    except Exception as e:
        result["errors"]["broll"] = str(e)
    
    # Return overall results
    if result["errors"]:
        result["status"] = "partial"
        result["message"] = f"Completed with {len(result['errors'])} errors"
    
    if result["generated"] == 0 and result["errors"]:
        result["status"] = "error"
        result["message"] = "Failed to generate any content"
    
    return result

# Page header
render_step_header("5B B-Roll Video Production", "Generate B-Roll videos using ComfyUI")

# Add a strong visual alert about cache issues
st.error("""
## ⚠️ IMPORTANT: CLEAR CACHE ⚠️
If you're seeing old B-Roll IDs in the input fields, click the "CLEAR ALL CACHE" button below. 
This is a known issue with Streamlit's caching mechanism.
""")

# Add a clear cache button with more emphasis
if st.button("🔄 CLEAR ALL CACHE", type="primary", key="force_clear_cache", help="Completely reset all cache", use_container_width=True):
    # Perform a complete wipe of session state
    for key in list(st.session_state.keys()):
        if key.startswith("broll_") or "content_status" in key:
            del st.session_state[key]
    
    # Force reset broll_fetch_ids
    st.session_state.broll_fetch_ids = {
        "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",
        "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257", 
        "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"
    }
    
    # Also refresh content status from file
    status_file = project_path / "content_status.json"
    if status_file.exists():
        with open(status_file, "r") as f:
            st.session_state.content_status = json.load(f)
    
    # Show success and rerun
    st.success("Cache cleared! Reloading page...")
    time.sleep(1)
    st.rerun()

st.title("⚡ B-Roll Content Production")
st.markdown("""
This page is for generating visual B-Roll content for your video.

This step will use the prompts generated in the previous step to create all the visual B-Roll assets for your video.
""")

# Add a clear cache button
clear_cache_col1, clear_cache_col2 = st.columns([3, 1])
with clear_cache_col1:
    st.warning("**⚠️ If you see old B-Roll IDs in the input fields below, click the 'Reset B-Roll IDs' button →**")
    
with clear_cache_col2:
    if st.button("🔄 Reset B-Roll IDs", key="clear_cache_button", type="primary", help="Completely reset the B-Roll IDs to use the new values"):
        # Force complete reset
        if "content_status" in st.session_state:
            del st.session_state.content_status
        
        # Recreate broll_fetch_ids with the new IDs
        st.session_state.broll_fetch_ids = {
            "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",  # SEG1
            "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257",  # SEG2
            "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"   # SEG3
        }
        
        # Clear any keys that might have the old B-roll IDs cached
        keys_to_delete = []
        for key in st.session_state:
            if key.startswith("broll_id_segment_"):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del st.session_state[key]
            
        # Force the page to reload
        st.success("B-Roll IDs reset successfully! Reloading page...")
        time.sleep(1)
        st.rerun()

# Load required data
has_script = load_script_data()
has_prompts = load_broll_prompts()
_ = load_content_status()  # Load if exists, but no need to check return value

# Check for required data and provide clear guidance
if not has_script:
    st.error("No script segments found. Please complete the Script Segmentation step (Step 3) first.")
    with st.expander("How to create script segments"):
        st.markdown("""
        ### How to create script segments:
        1. Go to the **Script Segmentation** page (Step 3)
        2. Enter your script or generate one
        3. Segment the script into A-Roll (on-camera) and B-Roll (visual) segments
        4. Save your segmented script
        """)
    st.button("Go to Script Segmentation", on_click=lambda: st.switch_page("pages/3_Script_Segmentation.py"))
    st.stop()

if not has_prompts:
    st.error("No B-Roll prompts found. Please complete the B-Roll Prompt Generation step (Step 4) first.")
    with st.expander("How to generate B-Roll prompts"):
        st.markdown("""
        ### How to generate B-Roll prompts:
        1. Go to the **B-Roll Prompts** page (Step 4)
        2. Select your prompt generation style
        3. Generate prompts for each B-Roll segment
        4. Save your prompts
        """)
    st.button("Go to B-Roll Prompts", on_click=lambda: st.switch_page("pages/4_BRoll_Prompts.py"))
    st.stop()

# Verify segments are properly loaded and formatted
if not st.session_state.segments or len(st.session_state.segments) == 0:
    st.error("Script segments were loaded but appear to be empty. Please go back and complete the Script Segmentation step properly.")
    st.button("Go to Script Segmentation", on_click=lambda: st.switch_page("pages/3_Script_Segmentation.py"))
    st.stop()

# Count segments by type for verification
aroll_segments = [s for s in st.session_state.segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
broll_segments = [s for s in st.session_state.segments if isinstance(s, dict) and s.get("type") == "B-Roll"]

if len(aroll_segments) == 0 and len(broll_segments) == 0:
    st.error("Script segments were loaded but don't have proper type information (A-Roll/B-Roll). Please go back and complete the Script Segmentation step properly.")
    st.button("Go to Script Segmentation", on_click=lambda: st.switch_page("pages/3_Script_Segmentation.py"))
    st.stop()

# Show production options
st.subheader("Content Production Options")

# Add ComfyUI job history section
st.markdown("---")
st.subheader("🔍 ComfyUI Job History")
st.markdown("Fetch recent job IDs from ComfyUI to reuse existing content.")

fetch_col1, fetch_col2 = st.columns([3, 1])

with fetch_col1:
    api_selection = st.radio(
        "Select ComfyUI API:",
        options=["Image API", "Video API"],
        horizontal=True,
        key="comfyui_api_selection"
    )
    api_url = COMFYUI_IMAGE_API_URL if api_selection == "Image API" else COMFYUI_VIDEO_API_URL
    
with fetch_col2:
    history_limit = st.number_input("Max results:", min_value=5, max_value=50, value=20, step=5)
    fetch_button = st.button("🔄 Fetch Job History", type="primary", use_container_width=True)

# Initialize job history in session state if not present
if "comfyui_job_history" not in st.session_state:
    st.session_state.comfyui_job_history = {"image": [], "video": []}

# Handle fetch button click
if fetch_button:
    with st.spinner(f"Fetching job history from {api_selection}..."):
        api_key = "image" if api_selection == "Image API" else "video"
        result = fetch_comfyui_job_history(api_url, limit=history_limit)
        
        if result["status"] == "success":
            st.session_state.comfyui_job_history[api_key] = result["data"]
            st.success(f"Successfully fetched {len(result['data'])} jobs from {api_selection}")
        else:
            st.error(f"Error fetching job history: {result.get('message', 'Unknown error')}")

# Display job history
api_key = "image" if api_selection == "Image API" else "video"
if api_key in st.session_state.comfyui_job_history and st.session_state.comfyui_job_history[api_key]:
    # Add tabs for different view options
    history_tab1, history_tab2 = st.tabs(["Table View", "Detail View"])
    
    with history_tab1:
        # Create a dataframe from job history
        job_data = []
        for job in st.session_state.comfyui_job_history[api_key]:
            job_data.append({
                "Prompt ID": job["prompt_id"],
                "Status": job["status"],
                "Time": job["timestamp"],
            })
        
        # Display as a table
        st.dataframe(job_data)
    
    with history_tab2:
        # Show detailed view with more controls
        for job in st.session_state.comfyui_job_history[api_key]:
            with st.expander(f"Job: {job['prompt_id']}"):
                st.write(f"Status: {job['status']}")
                st.write(f"Time: {job['timestamp']}")
                
                # Add button to copy ID
                if st.button(f"Copy ID: {job['prompt_id'][:8]}...", key=f"copy_{job['prompt_id']}"):
                    st.success(f"Copied prompt ID: {job['prompt_id']}")
                    # Add to clipboard (as best we can in Streamlit)
                    st.write(f"<textarea id='clipboard_{job['prompt_id']}' style='position:absolute;left:-9999px'>{job['prompt_id']}</textarea>", unsafe_allow_html=True)
                    st.write(f"<script>document.getElementById('clipboard_{job['prompt_id']}').select();document.execCommand('copy');</script>", unsafe_allow_html=True)

# Setup batch processing

# B-Roll Processing Controls
st.markdown("---")
st.subheader("🔢 B-Roll Processing Controls")
st.markdown("Control how many B-Roll segments will be processed when you generate content.")

# Count total B-Roll segments
broll_segments = [s for s in st.session_state.segments if s.get("type") == "B-Roll"]
total_broll_segments = len(broll_segments)

# Create columns for the controls
controls_col1, controls_col2 = st.columns([3, 1])

with controls_col1:
    # Add slider to control max segments to process
    st.slider(
        "Maximum B-Roll Segments to Process",
        min_value=1,
        max_value=max(1, total_broll_segments),
        value=min(3, total_broll_segments) if total_broll_segments > 0 else 1,  # Default to 3 or less if fewer segments exist
        step=1,
        key="max_broll_segments",
        help="Limit the number of B-Roll segments that will be processed. This is useful if you only want to generate a few segments at a time."
    )
    
    # Add informational message
    if total_broll_segments > 0 and st.session_state.max_broll_segments < total_broll_segments:
        st.info(f"Only the first {st.session_state.max_broll_segments} of {total_broll_segments} B-Roll segments will be processed.")
    
with controls_col2:
    # Add a button to process all segments
    if st.button("Process All", key="process_all_button"):
        st.session_state.max_broll_segments = total_broll_segments
        st.success(f"Set to process all {total_broll_segments} segments")
        st.rerun()

# Add ComfyUI job history section
st.markdown("---")
st.subheader("🔍 ComfyUI Job History")
st.markdown("Fetch recent job IDs from ComfyUI to reuse existing content.")

fetch_col1, fetch_col2 = st.columns([3, 1])

with fetch_col1:
    api_selection = st.radio(
        "Select ComfyUI API:",
        options=["Image API", "Video API"],
        horizontal=True,
        key="comfyui_api_selection"
    )
    api_url = COMFYUI_IMAGE_API_URL if api_selection == "Image API" else COMFYUI_VIDEO_API_URL
    
with fetch_col2:
    history_limit = st.number_input("Max results:", min_value=5, max_value=50, value=20, step=5)
    fetch_button = st.button("🔄 Fetch Job History", type="primary", use_container_width=True)

# Initialize job history in session state if not present
if "comfyui_job_history" not in st.session_state:
    st.session_state.comfyui_job_history = {"image": [], "video": []}

# Handle fetch button click
if fetch_button:
    with st.spinner(f"Fetching job history from {api_selection}..."):
        api_key = "image" if api_selection == "Image API" else "video"
        result = fetch_comfyui_job_history(api_url, limit=history_limit)
        
        if result["status"] == "success":
            st.session_state.comfyui_job_history[api_key] = result["data"]
            st.success(f"Successfully fetched {len(result['data'])} jobs from {api_selection}")
        else:
            st.error(f"Error fetching job history: {result.get('message', 'Unknown error')}")

# Display job history
api_key = "image" if api_selection == "Image API" else "video"
if api_key in st.session_state.comfyui_job_history and st.session_state.comfyui_job_history[api_key]:
    # Add tabs for different view options
    history_tab1, history_tab2 = st.tabs(["Table View", "Detail View"])
    
    with history_tab1:
        # Create a dataframe from job history
        job_data = []
        for job in st.session_state.comfyui_job_history[api_key]:
            job_data.append({
                "Prompt ID": job["prompt_id"],
                "Status": job["status"],
                "Time": job["timestamp"],
            })
        
        # Display as a table
        st.dataframe(job_data)
    
    with history_tab2:
        # Show detailed view with more controls
        for job in st.session_state.comfyui_job_history[api_key]:
            with st.expander(f"Job: {job['prompt_id']}"):
                st.write(f"Status: {job['status']}")
                st.write(f"Time: {job['timestamp']}")
                
                # Add button to copy ID
                if st.button(f"Copy ID: {job['prompt_id'][:8]}...", key=f"copy_{job['prompt_id']}"):
                    st.success(f"Copied prompt ID: {job['prompt_id']}")
                    # Add to clipboard (as best we can in Streamlit)
                    st.write(f"<textarea id='clipboard_{job['prompt_id']}' style='position:absolute;left:-9999px'>{job['prompt_id']}</textarea>", unsafe_allow_html=True)
                    st.write(f"<script>document.getElementById('clipboard_{job['prompt_id']}').select();document.execCommand('copy');</script>", unsafe_allow_html=True)