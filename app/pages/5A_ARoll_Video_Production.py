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

# Import custom helper module for ComfyUI integration
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app"))

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
    from utils.heygen_api import HeyGenAPI
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Failed to import local modules: {str(e)}")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="A-Roll Video Production | RealForge",
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

# Initialize session state variables
if "segments" not in st.session_state:
    st.session_state.segments = []
if "aroll_status" not in st.session_state:
    st.session_state.aroll_status = {}
if "parallel_tasks" not in st.session_state:
    st.session_state.parallel_tasks = {
        "running": False,
        "completed": 0,
        "total": 0
    }
if "aroll_fetch_ids" not in st.session_state:
    # Initialize with default A-Roll IDs
    st.session_state.aroll_fetch_ids = {
        "segment_0": "5169ef5a328149a8b13c365ee7060106",  # SEG1
        "segment_1": "aed87db0234e4965825c7ee4c1067467",  # SEG2
        "segment_2": "e7d47355c21e4190bad8752c799343ee",  # SEG3
        "segment_3": "36064085e2a240768a8368bc6a911aea"   # SEG4
    }
if "avatar_type" not in st.session_state:
    st.session_state.avatar_type = "video"  # Can be "video" or "photo"
if "heygen_avatar_id" not in st.session_state:
    st.session_state.heygen_avatar_id = "Abigail_expressive_2024112501"
if "heygen_voice_id" not in st.session_state:
    st.session_state.heygen_voice_id = "fe612bdf07a94d5fa7b80bf1282937d1"  # Arthur Blackwood
if "heygen_photo_avatar_id" not in st.session_state:
    st.session_state.heygen_photo_avatar_id = "35e0f2af72874fd6bc6e20cb74aebe72"  # Default photo avatar ID
if "manual_upload" not in st.session_state:
    st.session_state.manual_upload = False
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "manual_ids" not in st.session_state:
    st.session_state.manual_ids = {}

# Function to load saved script and segments
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
                aroll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll")
                invalid_count = len(segments) - aroll_count
                
                print(f"Debug - Found {aroll_count} A-Roll and {invalid_count} invalid segments")
                
                # Only update if we have valid segments
                if aroll_count > 0:
                    st.session_state.segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
                    return True
                else:
                    print("Warning: No valid A-Roll segments found in script.json")
                    return False
        except json.JSONDecodeError:
            print("Error: Failed to parse script.json")
            return False
    else:
        print(f"Warning: Script file not found at {script_file}")
        return False

# Function to load content status
def load_aroll_status():
    aroll_status_file = project_path / "aroll_status.json"
    if aroll_status_file.exists():
        try:
            with open(aroll_status_file, "r") as f:
                st.session_state.aroll_status = json.load(f)
            print(f"Loaded A-Roll status from {aroll_status_file}")
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading A-Roll status: {str(e)}")
            return False
    return False

# Function to save content status
def save_aroll_status():
    aroll_status_file = project_path / "aroll_status.json"
    try:
        with open(aroll_status_file, "w") as f:
            json.dump(st.session_state.aroll_status, f, indent=2)
        print(f"Saved A-Roll status to {aroll_status_file}")
        return True
    except IOError as e:
        print(f"Error saving A-Roll status: {str(e)}")
        return False

# Function to save fetch IDs
def save_fetch_ids():
    fetch_ids_file = project_path / "aroll_fetch_ids.json"
    try:
        with open(fetch_ids_file, "w") as f:
            json.dump(st.session_state.aroll_fetch_ids, f, indent=2)
        print(f"Saved A-Roll fetch IDs to {fetch_ids_file}")
        return True
    except IOError as e:
        print(f"Error saving A-Roll fetch IDs: {str(e)}")
        return False

# Function to save media content
def save_media_content(content, segment_id, file_extension=".mp4"):
    # Create directories if they don't exist
    media_dir = project_path / "media" / "a-roll"
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename
    filename = f"{segment_id}{file_extension}"
    file_path = media_dir / filename
    
    try:
        # Save content to file
        with open(file_path, "wb") as f:
            f.write(content)
        
        print(f"Saved media content to {file_path}")
        return {
            "status": "success",
            "file_path": str(file_path),
            "message": f"Saved to {file_path}"
        }
    except Exception as e:
        print(f"Error saving media content: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to save media: {str(e)}"
        }

# Function to generate A-Roll content using HeyGen API
def generate_aroll_content(segments, api_key, avatar_type="video"):
    if not api_key:
        return {
            "status": "error",
            "message": "HeyGen API key is required"
        }
    
    # Initialize HeyGen API client
    heygen_api = HeyGenAPI(api_key)
    
    # Check if connection is working
    test_result = heygen_api.test_connection()
    if test_result["status"] != "success":
        return {
            "status": "error",
            "message": f"Failed to connect to HeyGen API: {test_result['message']}"
        }
    
    results = {
        "status": "success",
        "generated": 0,
        "errors": {},
        "videos": {}
    }
    
    # Get selected avatar and voice IDs
    if avatar_type == "video":
        avatar_id = st.session_state.heygen_avatar_id
        voice_id = st.session_state.heygen_voice_id
    else:  # photo avatar
        avatar_id = st.session_state.heygen_photo_avatar_id
        voice_id = st.session_state.heygen_voice_id
    
    # Process each A-Roll segment
    for segment in segments:
        segment_id = segment.get("id", "")
        segment_text = segment.get("content", "").strip()
        
        if not segment_id or not segment_text:
            continue
        
        # Update status
        st.session_state.aroll_status[segment_id] = {
            "status": "processing",
            "message": "Submitting to HeyGen API..."
        }
        save_aroll_status()
        
        # Generate A-Roll video
        try:
            if avatar_type == "video":
                video_result = heygen_api.create_talking_video(
                    text=segment_text,
                    avatar_id=avatar_id,
                    voice_id=voice_id
                )
            else:
                video_result = heygen_api.create_talking_photo(
                    text=segment_text,
                    avatar_id=avatar_id,
                    voice_id=voice_id
                )
            
            if video_result["status"] == "success":
                video_id = video_result["data"]["video_id"]
                
                # Store video ID for later retrieval
                st.session_state.aroll_fetch_ids[segment_id] = video_id
                
                # Update status
                st.session_state.aroll_status[segment_id] = {
                    "status": "submitted",
                    "message": f"Submitted to HeyGen (ID: {video_id})",
                    "video_id": video_id,
                    "avatar_type": avatar_type,
                    "timestamp": time.time()
                }
                
                results["generated"] += 1
                results["videos"][segment_id] = video_id
            else:
                error_message = video_result.get("message", "Unknown error")
                st.session_state.aroll_status[segment_id] = {
                    "status": "error",
                    "message": f"API Error: {error_message}"
                }
                results["errors"][segment_id] = error_message
        except Exception as e:
            st.session_state.aroll_status[segment_id] = {
                "status": "error",
                "message": f"Exception: {str(e)}"
            }
            results["errors"][segment_id] = str(e)
        
        # Save updated status
        save_aroll_status()
        save_fetch_ids()
    
    # Return overall results
    if results["generated"] > 0:
        return results
    else:
        results["status"] = "error"
        results["message"] = "Failed to generate any A-Roll videos"
        return results

# Function to check status of A-Roll videos
def check_aroll_status(api_key):
    if not api_key:
        return {
            "status": "error",
            "message": "HeyGen API key is required"
        }
    
    # Initialize HeyGen API client
    heygen_api = HeyGenAPI(api_key)
    
    results = {
        "status": "success",
        "checked": 0,
        "completed": 0,
        "errors": {},
        "videos": {}
    }
    
    # Check each video ID
    for segment_id, video_id in st.session_state.aroll_fetch_ids.items():
        if not video_id:
            continue
        
        # Get status from API
        try:
            status_result = heygen_api.check_video_status(video_id)
            
            if status_result["status"] == "success":
                video_status = status_result["data"].get("status", "unknown")
                video_url = status_result["data"].get("video_url", "")
                
                results["checked"] += 1
                results["videos"][segment_id] = {
                    "status": video_status,
                    "url": video_url
                }
                
                # Update session state status
                st.session_state.aroll_status[segment_id] = {
                    "status": video_status,
                    "message": f"Status: {video_status}",
                    "video_id": video_id,
                    "video_url": video_url,
                    "timestamp": time.time()
                }
                
                # If completed, download the video
                if video_status.lower() in ["completed", "ready", "success", "done"] and video_url:
                    # Download video
                    media_dir = project_path / "media" / "a-roll"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    output_path = str(media_dir / f"{segment_id}.mp4")
                    
                    download_result = heygen_api.download_video(video_url, output_path)
                    
                    if download_result["status"] == "success":
                        st.session_state.aroll_status[segment_id]["local_path"] = output_path
                        st.session_state.aroll_status[segment_id]["downloaded"] = True
                        results["completed"] += 1
                    else:
                        st.session_state.aroll_status[segment_id]["download_error"] = download_result["message"]
            else:
                error_message = status_result.get("message", "Unknown error")
                st.session_state.aroll_status[segment_id] = {
                    "status": "error",
                    "message": f"API Error: {error_message}",
                    "video_id": video_id,
                    "timestamp": time.time()
                }
                results["errors"][segment_id] = error_message
        except Exception as e:
            st.session_state.aroll_status[segment_id]["status"] = "error"
            st.session_state.aroll_status[segment_id]["message"] = f"Exception: {str(e)}"
            results["errors"][segment_id] = str(e)
        
        # Save updated status
        save_aroll_status()
    
    # Return overall results
    return results

# Function to manually fetch content by ID
def manual_fetch_content(api_key, segment_ids):
    if not api_key:
        return {
            "status": "error",
            "message": "HeyGen API key is required"
        }
    
    # Initialize HeyGen API client
    heygen_api = HeyGenAPI(api_key)
    
    results = {
        "status": "success",
        "checked": 0,
        "completed": 0,
        "errors": {},
        "videos": {}
    }
    
    # Fetch each video ID
    for segment_id, video_id in segment_ids.items():
        if not video_id:
            continue
        
        # Update status to show we're fetching
        st.session_state.aroll_status[segment_id] = {
            "status": "fetching",
            "message": f"Fetching content for ID: {video_id}",
            "video_id": video_id,
            "timestamp": time.time()
        }
        save_aroll_status()
        
        # Get status from API
        try:
            status_result = heygen_api.check_video_status(video_id)
            
            if status_result["status"] == "success":
                video_status = status_result["data"].get("status", "unknown")
                video_url = status_result["data"].get("video_url", "")
                
                results["checked"] += 1
                results["videos"][segment_id] = {
                    "status": video_status,
                    "url": video_url
                }
                
                # Update session state status
                st.session_state.aroll_status[segment_id] = {
                    "status": video_status,
                    "message": f"Status: {video_status}",
                    "video_id": video_id,
                    "video_url": video_url,
                    "timestamp": time.time()
                }
                
                # Store the ID in fetch IDs for future reference
                st.session_state.aroll_fetch_ids[segment_id] = video_id
                
                # If completed, download the video
                if video_status.lower() in ["completed", "ready", "success", "done"] and video_url:
                    # Download video
                    media_dir = project_path / "media" / "a-roll"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    output_path = str(media_dir / f"{segment_id}.mp4")
                    
                    download_result = heygen_api.download_video(video_url, output_path)
                    
                    if download_result["status"] == "success":
                        st.session_state.aroll_status[segment_id]["local_path"] = output_path
                        st.session_state.aroll_status[segment_id]["downloaded"] = True
                        results["completed"] += 1
                    else:
                        st.session_state.aroll_status[segment_id]["download_error"] = download_result["message"]
            else:
                error_message = status_result.get("message", "Unknown error")
                st.session_state.aroll_status[segment_id] = {
                    "status": "error",
                    "message": f"API Error: {error_message}",
                    "video_id": video_id,
                    "timestamp": time.time()
                }
                results["errors"][segment_id] = error_message
        except Exception as e:
            st.session_state.aroll_status[segment_id]["status"] = "error"
            st.session_state.aroll_status[segment_id]["message"] = f"Exception: {str(e)}"
            results["errors"][segment_id] = str(e)
        
        # Save updated status
        save_aroll_status()
        save_fetch_ids()
    
    # Return overall results
    return results

# Function to handle manual file uploads
def handle_manual_uploads(uploaded_files):
    for segment_id, file in uploaded_files.items():
        if file is not None:
            try:
                # Read file content
                content = file.read()
                
                # Save to media directory
                save_result = save_media_content(content, segment_id)
                
                if save_result["status"] == "success":
                    # Update status
                    st.session_state.aroll_status[segment_id] = {
                        "status": "completed",
                        "message": "Uploaded manually",
                        "local_path": save_result["file_path"],
                        "manually_uploaded": True,
                        "timestamp": time.time()
                    }
                else:
                    st.session_state.aroll_status[segment_id] = {
                        "status": "error",
                        "message": f"Upload failed: {save_result['message']}",
                        "manually_uploaded": True,
                        "timestamp": time.time()
                    }
            except Exception as e:
                st.session_state.aroll_status[segment_id] = {
                    "status": "error",
                    "message": f"Exception during upload: {str(e)}",
                    "manually_uploaded": True,
                    "timestamp": time.time()
                }
        
        # Save updated status
        save_aroll_status()

# Main app logic
def main():
    # Load data
    load_script_data()
    load_aroll_status()
    
    # Page header
    render_step_header("5A A-Roll Video Production", "Generate presenter video using HeyGen AI")
    
    if not st.session_state.segments:
        st.warning("No A-Roll segments found. Please create them in the Script Segmentation step.")
        st.stop()
    
    # Filter for A-Roll segments only
    aroll_segments = st.session_state.segments
    
    if not aroll_segments:
        st.warning("No A-Roll segments found. Please create A-Roll segments in the Script Segmentation step.")
        st.stop()
    
    # Display A-Roll settings
    with st.expander("A-Roll Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Function to save API key to environment variables 
            def save_heygen_api_key(api_key):
                if api_key:
                    # Set current session environment variable
                    os.environ["HEYGEN_API_KEY"] = api_key
                    st.success("HeyGen API key saved and will be used for this session")
                    # To save permanently, would need to modify .bashrc/.zshrc file
                    # which requires user intervention
            
            # Previous value for comparison
            prev_api_key = os.environ.get("HEYGEN_API_KEY", "")
            
            heygen_api_key = st.text_input(
                "HeyGen API Key", 
                type="password",
                help="Enter your HeyGen API key. You can get it from heygen.com/settings.",
                value=prev_api_key,
                key="heygen_api_key_input"
            )
            
            # If the API key changed, save it
            if heygen_api_key != prev_api_key:
                save_heygen_api_key(heygen_api_key)
        
        with col2:
            manual_upload = st.checkbox(
                "Enable manual upload",
                value=st.session_state.manual_upload,
                help="Upload A-Roll videos manually instead of generating them"
            )
            st.session_state.manual_upload = manual_upload
        
        if not manual_upload:
            # Avatar type selection
            avatar_type = st.radio(
                "Avatar Type",
                options=["Video Avatar", "Photo Avatar"],
                index=0 if st.session_state.avatar_type == "video" else 1,
                horizontal=True,
                help="Select avatar type to use for your A-Roll video"
            )
            st.session_state.avatar_type = "video" if avatar_type == "Video Avatar" else "photo"
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.session_state.avatar_type == "video":
                    # Video avatar options
                    avatar_options = {
                        "Abigail (Female)": "Abigail_expressive_2024112501",
                        "Arthur (Male)": "Arthur_expressive_2024112501"
                    }
                    
                    selected_avatar = st.selectbox(
                        "Video Avatar",
                        options=list(avatar_options.keys()),
                        index=0 if st.session_state.heygen_avatar_id == "Abigail_expressive_2024112501" else 1,
                        help="Select the avatar to use for your A-Roll video"
                    )
                    
                    st.session_state.heygen_avatar_id = avatar_options[selected_avatar]
                else:
                    # Photo avatar ID input
                    photo_avatar_id = st.text_input(
                        "Photo Avatar ID",
                        value=st.session_state.heygen_photo_avatar_id,
                        help="Enter the HeyGen Photo Avatar ID"
                    )
                    st.session_state.heygen_photo_avatar_id = photo_avatar_id
                    
                    st.info("Default photo avatar ID: 35e0f2af72874fd6bc6e20cb74aebe72")
            
            with col2:
                voice_options = {
                    "Arthur (Male)": "fe612bdf07a94d5fa7b80bf1282937d1",
                    "Matt (Male)": "9f8ff4eed26442168a8f2dc03c56e9ce",
                    "Sarah (Female)": "1582f2abbc114670b8999f22af70f09d"
                }
                
                selected_voice = st.selectbox(
                    "Voice",
                    options=list(voice_options.keys()),
                    index=0,
                    help="Select the voice to use for your A-Roll video"
                )
                
                st.session_state.heygen_voice_id = voice_options[selected_voice]
    
    # Create tabs for segment management and ID view
    tab1, tab2 = st.tabs(["A-Roll Segments", "Segment IDs"])
    
    with tab1:
        # Display A-Roll segments
        st.subheader("A-Roll Segments")
        
        for i, segment in enumerate(aroll_segments):
            segment_id = segment.get("id", f"segment_{i}")
            segment_text = segment.get("content", "").strip()
            
            # Get status for this segment
            segment_status = st.session_state.aroll_status.get(segment_id, {})
            status = segment_status.get("status", "not_started")
            message = segment_status.get("message", "Not started yet")
            
            with st.expander(f"Segment {i+1}: {segment_id}", expanded=True):
                # Display segment text
                st.markdown(f"**Text:** {segment_text}")
                
                # Display status
                status_color = {
                    "not_started": "gray",
                    "processing": "blue",
                    "submitted": "orange",
                    "completed": "green", 
                    "ready": "green",
                    "success": "green",
                    "done": "green",
                    "error": "red"
                }.get(status.lower(), "gray")
                
                st.markdown(f"**Status:** <span style='color:{status_color}'>{status}</span> - {message}", unsafe_allow_html=True)
                
                # Display manual upload field if enabled
                if manual_upload:
                    uploaded_file = st.file_uploader(
                        f"Upload video for {segment_id}",
                        type=["mp4", "mov"],
                        key=f"upload_{segment_id}"
                    )
                    
                    if uploaded_file:
                        st.session_state.uploaded_files[segment_id] = uploaded_file
                
                # Display video if available
                local_path = segment_status.get("local_path")
                if local_path and Path(local_path).exists():
                    st.video(local_path)
                    st.markdown(f"**Local file:** {local_path}")
                elif "video_url" in segment_status and segment_status["video_url"]:
                    st.markdown(f"**HeyGen URL:** [View Video]({segment_status['video_url']})")
    
    with tab2:
        st.subheader("Segment IDs")
        st.info("View and manage HeyGen IDs for each segment")
        
        # Create subtabs for viewing and entering IDs
        id_tab1, id_tab2 = st.tabs(["Current IDs", "Manual ID Entry"])
        
        with id_tab1:
            st.markdown("### Current Segment IDs")
            
            # Display current IDs in a table format
            id_data = []
            for i, segment in enumerate(aroll_segments):
                segment_id = segment.get("id", f"segment_{i}")
                fetch_id = st.session_state.aroll_fetch_ids.get(segment_id, "")
                segment_text = segment.get("content", "").strip()
                if len(segment_text) > 50:
                    segment_text = segment_text[:50] + "..."
                
                id_data.append({
                    "Segment": f"Segment {i+1}",
                    "ID": segment_id,
                    "Content": segment_text,
                    "HeyGen ID": fetch_id
                })
            
            # Display as table
            st.table(id_data)
            
            # Add preview section for fetched videos
            st.markdown("### Content Previews")
            st.info("Preview videos for segments with fetched content")
            
            # Create tabs for different segments
            preview_tabs = st.tabs([f"Segment {i+1}" for i in range(len(aroll_segments))])
            
            # Display previews in each tab
            for i, tab in enumerate(preview_tabs):
                segment_id = aroll_segments[i].get("id", f"segment_{i}")
                segment_status = st.session_state.aroll_status.get(segment_id, {})
                
                with tab:
                    # Show the segment text
                    segment_text = aroll_segments[i].get("content", "").strip()
                    st.markdown(f"**Text:** {segment_text}")
                    
                    fetch_id = st.session_state.aroll_fetch_ids.get(segment_id, "")
                    if fetch_id:
                        st.markdown(f"**HeyGen ID:** `{fetch_id}`")
                    
                    # Show preview if available
                    if segment_status.get("status") == "completed" and segment_status.get("local_path"):
                        local_path = segment_status.get("local_path")
                        if Path(local_path).exists():
                            st.video(local_path)
                            st.success("Video downloaded successfully")
                    elif segment_status.get("video_url"):
                        st.markdown(f"**Remote video available:** [View Video]({segment_status.get('video_url')})")
                        
                        # Add a download button
                        if st.button("Download Video", key=f"download_btn_{i}"):
                            with st.spinner("Downloading video..."):
                                try:
                                    if heygen_api_key:
                                        # Download using HeyGen API
                                        heygen_api = HeyGenAPI(heygen_api_key)
                                        media_dir = project_path / "media" / "a-roll"
                                        media_dir.mkdir(parents=True, exist_ok=True)
                                        output_path = str(media_dir / f"{segment_id}.mp4")
                                        
                                        download_result = heygen_api.download_video(segment_status.get("video_url"), output_path)
                                        
                                        if download_result["status"] == "success":
                                            st.session_state.aroll_status[segment_id]["local_path"] = output_path
                                            st.session_state.aroll_status[segment_id]["downloaded"] = True
                                            st.success(f"Video downloaded successfully to {output_path}")
                                            save_aroll_status()
                                            st.rerun()
                                        else:
                                            st.error(f"Error downloading video: {download_result.get('message')}")
                                    else:
                                        st.error("HeyGen API key is required to download videos")
                                except Exception as e:
                                    st.error(f"Error downloading video: {str(e)}")
                    elif segment_status.get("status") == "processing" or segment_status.get("status") == "submitted":
                        st.info(f"Video is being processed: {segment_status.get('message', 'In progress...')}")
                    else:
                        st.info("No video content available for this segment")
        
        with id_tab2:
            st.markdown("### Manual ID Entry")
            st.info("Enter HeyGen video IDs manually for each segment")
            
            # Create inputs for each segment
            manual_ids = {}
            for i, segment in enumerate(aroll_segments):
                segment_id = segment.get("id", f"segment_{i}")
                segment_text = segment.get("content", "").strip()
                if len(segment_text) > 30:
                    segment_text = segment_text[:30] + "..."
                
                # Create columns for segment info and ID input
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown(f"**Segment {i+1}:** {segment_text}")
                
                with col2:
                    manual_id = st.text_input(
                        f"ID for Segment {i+1}",
                        value=st.session_state.manual_ids.get(segment_id, ""),
                        key=f"manual_id_{segment_id}"
                    )
                    manual_ids[segment_id] = manual_id
                
                # Show preview if this segment has a fetched video
                segment_status = st.session_state.aroll_status.get(segment_id, {})
                if segment_status.get("status") == "completed" and segment_status.get("local_path"):
                    local_path = segment_status.get("local_path")
                    if Path(local_path).exists():
                        st.video(local_path)
                        st.markdown(f"**Fetched content preview for ID:** `{segment_status.get('video_id', 'Unknown')}`")
                elif segment_status.get("video_url"):
                    st.markdown(f"**Remote video available:** [View Video]({segment_status.get('video_url')})")
            
            # Save manual IDs to session state
            st.session_state.manual_ids = manual_ids
            
            # Add fetch button
            if st.button("Fetch Content from Manual IDs", type="primary"):
                if not heygen_api_key:
                    st.error("HeyGen API Key is required to fetch content")
                else:
                    # Filter out empty IDs
                    valid_ids = {k: v for k, v in manual_ids.items() if v}
                    
                    if not valid_ids:
                        st.warning("No valid IDs entered. Please enter at least one ID.")
                    else:
                        with st.spinner(f"Fetching content for {len(valid_ids)} IDs..."):
                            result = manual_fetch_content(heygen_api_key, valid_ids)
                            
                            if result["status"] == "success":
                                st.success(f"Successfully fetched {result['checked']} videos, {result['completed']} downloaded")
                            else:
                                st.error(f"Error: {result.get('message', 'Unknown error')}")
                            
                            if result.get("errors"):
                                st.error(f"Errors: {result['errors']}")
                        
                        st.rerun()
    
    # Action buttons
    st.subheader("Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if manual_upload and st.session_state.uploaded_files:
            if st.button("Process Uploaded Files", type="primary"):
                with st.spinner("Processing uploaded files..."):
                    handle_manual_uploads(st.session_state.uploaded_files)
                st.success("Files processed successfully!")
                st.rerun()
        elif not manual_upload:
            if st.button("Generate A-Roll Videos", type="primary", disabled=not heygen_api_key):
                avatar_type = st.session_state.avatar_type
                with st.spinner(f"Generating A-Roll videos with {avatar_type} avatars..."):
                    result = generate_aroll_content(aroll_segments, heygen_api_key, avatar_type)
                    
                    if result["status"] == "success":
                        st.success(f"Successfully submitted {result['generated']} videos for generation!")
                    else:
                        st.error(f"Error: {result.get('message', 'Unknown error')}")
                    
                    if result.get("errors"):
                        st.error(f"Errors: {result['errors']}")
                
                st.rerun()
    
    with col2:
        if st.button("Check Status", disabled=not heygen_api_key and not manual_upload):
            with st.spinner("Checking status of A-Roll videos..."):
                if not manual_upload:
                    result = check_aroll_status(heygen_api_key)
                    
                    if result["status"] == "success":
                        st.success(f"Checked {result['checked']} videos, {result['completed']} completed")
                    else:
                        st.error(f"Error: {result.get('message', 'Unknown error')}")
                    
                    if result.get("errors"):
                        st.error(f"Errors: {result['errors']}")
                else:
                    st.info("Manual upload mode: No status to check")
            
            st.rerun()
    
    with col3:
        if st.button("Mark Step Complete"):
            # Check if all segments have been processed
            all_completed = True
            
            for segment in aroll_segments:
                segment_id = segment.get("id", "")
                status = st.session_state.aroll_status.get(segment_id, {}).get("status", "").lower()
                
                if status not in ["completed", "ready", "success", "done"]:
                    all_completed = False
                    break
            
            if all_completed:
                mark_step_complete("aroll_production")
                st.success("A-Roll production complete! Proceed to the next step.")
            else:
                st.warning("Not all A-Roll videos are complete. Please finish processing all segments.")

    # Navigation buttons
    st.markdown("---")
    render_step_navigation(
        current_step=5,
        prev_step_path="pages/4_BRoll_Prompts.py",
        next_step_path="pages/5B_BRoll_Video_Production.py"
    )

# Run the app
if __name__ == "__main__":
    main() 