import streamlit as st
import os
import sys
from pathlib import Path
import numpy as np
import time
from datetime import datetime
import cv2
import traceback
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import base64
from matplotlib.figure import Figure

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path")
    print("Successfully imported local modules")

# Add the app directory to the Python path to allow importing from our fix script
app_dir = Path(__file__).parent.parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Attempt to import the direct assembly function from our fix script
try:
    from video_assembly_streamlit_fix import direct_assembly as fixed_assembly
    FIXED_ASSEMBLY_AVAILABLE = True
except ImportError:
    FIXED_ASSEMBLY_AVAILABLE = False

# Define render_sequence_timeline function here, before it's needed
def render_sequence_timeline(sequence):
    """
    Render a timeline visualization of the video sequence showing
    how segments are arranged and where audio comes from
    
    Args:
        sequence: List of video segments to assemble
        
    Returns:
        str: Base64 encoded image of the timeline
    """
    if not sequence:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 4))
    
    # Track durations and start times
    current_time = 0
    y_positions = {"video": 0.6, "audio": 0.2}
    colors = {
        "aroll_video": "#4CAF50",  # Green
        "broll_video": "#2196F3",  # Blue
        "aroll_audio": "#FF9800",  # Orange
    }
    
    # Set up the plot
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 30)  # Adjust based on expected total duration
    ax.set_xlabel("Time (seconds)")
    ax.set_yticks([y_positions["video"], y_positions["audio"]])
    ax.set_yticklabels(["Video", "Audio"])
    ax.grid(axis="x", linestyle="--", alpha=0.7)
    ax.set_title("Sequence Timeline")
    
    # Track start times for each segment
    start_times = []
    segment_durations = []
    
    # Estimate durations (in practice, you would get these from the actual video files)
    # For this visualization, we'll use average durations
    avg_duration = 7  # seconds per segment - typical short segment
    
    # Loop through sequences and draw rectangles for each segment
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        segment_duration = avg_duration  # In a real implementation, get actual duration
        segment_durations.append(segment_duration)
        start_times.append(current_time)
        
        # Draw video track
        if item["type"] == "aroll_full":
            # A-Roll video track
            video_rect = patches.Rectangle(
                (current_time, y_positions["video"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["aroll_video"],
                alpha=0.8,
                label="A-Roll Video" if i == 0 else None
            )
            ax.add_patch(video_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["video"], 
                f"A-{segment_id.split('_')[-1]}", 
                ha="center", 
                va="center",
                color="white",
                fontweight="bold"
            )
            
            # A-Roll audio track (same source)
            audio_rect = patches.Rectangle(
                (current_time, y_positions["audio"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["aroll_audio"],
                alpha=0.8,
                label="A-Roll Audio" if i == 0 else None
            )
            ax.add_patch(audio_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["audio"], 
                f"A-{segment_id.split('_')[-1]}", 
                ha="center", 
                va="center",
                color="black",
                fontweight="bold"
            )
        else:  # broll_with_aroll_audio
            broll_id = item.get("broll_id", "").split("_")[-1]
            # B-Roll video track
            video_rect = patches.Rectangle(
                (current_time, y_positions["video"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["broll_video"],
                alpha=0.8,
                label="B-Roll Video" if i == 0 or (i > 0 and sequence[i-1]["type"] != "broll_with_aroll_audio") else None
            )
            ax.add_patch(video_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["video"], 
                f"B-{broll_id}", 
                ha="center", 
                va="center",
                color="white",
                fontweight="bold"
            )
            
            # A-Roll audio track
            audio_rect = patches.Rectangle(
                (current_time, y_positions["audio"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["aroll_audio"],
                alpha=0.8,
                label="A-Roll Audio" if i == 0 or (i > 0 and sequence[i-1]["type"] != "broll_with_aroll_audio") else None
            )
            ax.add_patch(audio_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["audio"], 
                f"A-{segment_id.split('_')[-1]}", 
                ha="center", 
                va="center",
                color="black",
                fontweight="bold"
            )
        
        current_time += segment_duration
    
    # Adjust the x-axis to fit the content
    ax.set_xlim(0, current_time + 2)
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right")
    
    # Convert plot to image
    buf = io.BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    
    # Encode the image to base64 string
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    
    return img_str

# Now import our helper modules
try:
    from utils.video.assembly import (
        assemble_video as helper_assemble_video,
        check_file,
        MOVIEPY_AVAILABLE
    )
    from utils.video.simple_assembly import simple_assemble_video
except ImportError as e:
    print(f"Error importing video assembly module: {str(e)}")
    # Alternative import paths in case the first one fails
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.video.assembly import (
            assemble_video as helper_assemble_video,
            check_file,
            MOVIEPY_AVAILABLE
        )
        from utils.video.simple_assembly import simple_assemble_video
        print("Successfully imported video assembly module using alternative path")
    except ImportError as e2:
        print(f"Alternative import also failed: {str(e2)}")
        # Create fallback values if import fails
        helper_assemble_video = None
        check_file = None
        MOVIEPY_AVAILABLE = False
        simple_assemble_video = None

# Try to import MoviePy, show helpful error if not available
try:
    import moviepy.editor as mp
    from moviepy.video.fx import resize, speedx
    MOVIEPY_AVAILABLE = True
except ImportError:
    st.error("MoviePy is not available. Installing required packages...")
    st.info("Please run: `pip install moviepy==1.0.3` in your virtual environment")
    MOVIEPY_AVAILABLE = False
    # Create dummy classes/functions to avoid errors
    class DummyMoviePy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    mp = DummyMoviePy()
    resize = lambda *args, **kwargs: None
    speedx = lambda *args, **kwargs: None

# Import other modules
from components.progress import render_step_header
from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation, render_step_navigation
from utils.session_state import get_settings, get_project_path, mark_step_complete

# Rest of the imports
import json
from pathlib import Path
import subprocess

# Add utils.video.broll_defaults import
from utils.video.broll_defaults import apply_default_broll_ids, update_session_state_with_defaults

# Set page configuration
st.set_page_config(
    page_title="Video Assembly | AI Money Printer",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

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

# Render navigation sidebar
render_custom_sidebar()

# Page header
st.title("6. Video Assembly")
st.markdown("Combine A-Roll and B-Roll videos into a complete short-form video.")

# Notification about image support
st.info("🖼️ **NEW FEATURE**: You can now use images (PNG, JPG) as B-roll content! They will automatically be converted into video clips matching the A-roll audio duration.")

# Load settings and project path
settings = get_settings()
project_path = get_project_path()

# Initialize session state variables
if "video_assembly" not in st.session_state:
    st.session_state.video_assembly = {
        "status": "not_started",
        "progress": 0,
        "output_path": None,
        "error": None,
        "sequence": []
    }

# Function to load content status
def load_content_status():
    """Load content status from both A-roll and B-roll status files"""
    content_status = {
        "aroll": {},
        "broll": {}
    }
    
    # Load B-roll status
    broll_status_file = project_path / "content_status.json"
    print(f"Checking B-Roll status file at: {broll_status_file}")
    if broll_status_file.exists():
        try:
            with open(broll_status_file, "r") as f:
                broll_data = json.load(f)
                if "broll" in broll_data:
                    content_status["broll"] = broll_data["broll"]
                    print(f"Loaded {len(broll_data['broll'])} B-Roll segments")
                else:
                    print("No 'broll' key found in content_status.json")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading B-Roll status: {str(e)}")
    else:
        print(f"B-Roll status file not found at {broll_status_file}")
    
    # Load A-roll status - try multiple potential paths
    aroll_status_files = [
        project_path / "aroll_status.json",
        Path("config/user_data/my_short_video/aroll_status.json"),  # Common default location
        Path("config/user_data/my_project/aroll_status.json"),
        Path(os.getcwd()) / "aroll_status.json"
    ]
    
    for aroll_status_file in aroll_status_files:
        print(f"Checking A-Roll status file at: {aroll_status_file}")
        if aroll_status_file.exists():
            try:
                with open(aroll_status_file, "r") as f:
                    content_status["aroll"] = json.load(f)
                    print(f"Loaded {len(content_status['aroll'])} A-Roll segments from {aroll_status_file}")
                    break  # Successfully loaded, so break the loop
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading A-Roll status from {aroll_status_file}: {str(e)}")
    else:
        print("No A-Roll status file found in any of the checked locations")
    
    # Store in session state
    st.session_state.content_status = content_status
    
    # Print a summary for debugging
    print(f"Content status summary: {len(content_status['aroll'])} A-Roll segments, {len(content_status['broll'])} B-Roll segments")
    print(f"A-Roll keys: {list(content_status['aroll'].keys())}")
    print(f"B-Roll keys: {list(content_status['broll'].keys())}")
    
    return content_status

# Function to load segments
def load_segments():
    script_file = project_path / "script.json"
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                segments = data.get("segments", [])
                
                # Ensure all A-Roll segments have segment_id values
                aroll_count = 0
                for i, segment in enumerate(segments):
                    if isinstance(segment, dict) and segment.get("type") == "A-Roll":
                        # If no segment_id, set one based on aroll_count
                        if "segment_id" not in segment:
                            segment["segment_id"] = f"segment_{aroll_count}"
                            print(f"Assigned segment_id {segment['segment_id']} to A-Roll segment at index {i}")
                        aroll_count += 1
                
                return segments
        except Exception as e:
            st.error(f"Error loading segments: {str(e)}")
            return []
    else:
        st.error("Script segments file not found. Please complete the Script Segmentation step first.")
        return []

# Function to resize video to target resolution (9:16 aspect ratio)
def resize_video(clip, target_resolution=(1080, 1920)):
    """Resize video clip to target resolution maintaining aspect ratio with padding if needed"""
    # Get original dimensions
    w, h = clip.size
    
    # Calculate target aspect ratio
    target_aspect = target_resolution[0] / target_resolution[1]  # width/height
    current_aspect = w / h
    
    if current_aspect > target_aspect:
        # Video is wider than target aspect ratio - fit to width
        new_width = target_resolution[0]
        new_height = int(new_width / current_aspect)
        resized_clip = clip.resize(width=new_width, height=new_height)
        
        # Add padding to top and bottom
        padding_top = (target_resolution[1] - new_height) // 2
        padding_bottom = target_resolution[1] - new_height - padding_top
        
        # Create black background
        bg = mp.ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
        
        # Position resized clip on background
        final_clip = mp.CompositeVideoClip([
            bg,
            resized_clip.set_position(("center", padding_top))
        ])
    else:
        # Video is taller than target aspect ratio - fit to height
        new_height = target_resolution[1]
        new_width = int(new_height * current_aspect)
        resized_clip = clip.resize(height=new_height, width=new_width)
        
        # Add padding to left and right
        padding_left = (target_resolution[0] - new_width) // 2
        
        # Create black background
        bg = mp.ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
        
        # Position resized clip on background
        final_clip = mp.CompositeVideoClip([
            bg,
            resized_clip.set_position((padding_left, 0))
        ])
        
    return final_clip.set_duration(clip.duration)

def get_aroll_filepath(segment_id, segment_data):
    """
    Get A-Roll filepath for a specific segment
    
    Args:
        segment_id: ID of the segment
        segment_data: Segment data object
        
    Returns:
        tuple: (filepath, success, error_message)
    """
    # First, check if the segment data has a file_path property (from segmentation)
    if "file_path" in segment_data and os.path.exists(segment_data["file_path"]):
        print(f"Found A-Roll file in segment data: {segment_data['file_path']}")
        return segment_data["file_path"], True, None
    
    # Next, check the status file for this segment
    aroll_status = st.session_state.content_status.get("aroll", {}).get(segment_id, {})
    
    print(f"Looking for A-Roll file for {segment_id}")
    print(f"Status data: {aroll_status}")
    
    # If we have a local path from the status file, use that
    if "local_path" in aroll_status and Path(aroll_status["local_path"]).exists():
        print(f"Found A-Roll file at: {aroll_status['local_path']}")
        return aroll_status["local_path"], True, None
    
    # Next, check media/a-roll directory for segment_id.mp4
    aroll_file = project_path / "media" / "a-roll" / f"{segment_id}.mp4"
    if aroll_file.exists():
        print(f"Found A-Roll file at: {aroll_file}")
        return str(aroll_file), True, None
    
    # Check for files with segment ID in different formats
    segment_num = segment_id.split('_')[-1] if '_' in segment_id else segment_id
    
    # Check for segment number in filename
    segment_patterns = [
        f"*segment_{segment_num}.mp4",
        f"*_segment_{segment_num}.mp4",
        f"*segment{segment_num}.mp4",
        f"*_segment{segment_num}.mp4",
        f"*seg_{segment_num}.mp4",
        f"*_{segment_num}.mp4",
        f"*{segment_num}.mp4"
    ]
    
    # Look for files matching patterns in a-roll directories
    potential_dirs = [
        project_path / "media" / "a-roll",
        project_path / "media" / "a-roll" / "segments",
        project_path / "media" / "aroll",
        project_path / "media" / "aroll" / "segments",
        Path("media") / "a-roll",
        Path("media") / "a-roll" / "segments",
        Path("media") / "aroll",
        Path("media") / "aroll" / "segments",
        app_root / "media" / "a-roll",
        app_root / "media" / "a-roll" / "segments",
        app_root / "media" / "aroll",
        app_root / "media" / "aroll" / "segments",
    ]
    
    import glob
    for directory in potential_dirs:
        if directory.exists():
            for pattern in segment_patterns:
                matches = glob.glob(str(directory / pattern))
                if matches:
                    print(f"Found A-Roll file matching pattern: {matches[0]}")
                    # Update the status to use this path in the future
                    aroll_status["local_path"] = matches[0]
                    st.session_state.content_status["aroll"][segment_id] = aroll_status
                    return matches[0], True, None
        
    # Try alternative paths
    alt_paths = [
        project_path / "media" / "a-roll" / f"{segment_id}.mp4",
        project_path / "media" / "aroll" / f"{segment_id}.mp4",
        Path("media") / "a-roll" / f"{segment_id}.mp4",
        Path("media") / "aroll" / f"{segment_id}.mp4",
        app_root / "media" / "a-roll" / f"{segment_id}.mp4",
        app_root / "media" / "aroll" / f"{segment_id}.mp4",
        # Add these additional potential paths
        Path(os.getcwd()) / "media" / "a-roll" / f"{segment_id}.mp4",
        Path(os.getcwd()) / "media" / "aroll" / f"{segment_id}.mp4",
        Path("/Users/dawarazhar/Desktop/AI-Money-Printer-Shorts/app") / "media" / "a-roll" / f"{segment_id}.mp4",
        Path("/Users/dawarazhar/Desktop/AI-Money-Printer-Shorts/app") / "media" / "aroll" / f"{segment_id}.mp4"
    ]
    
    for path in alt_paths:
        if path.exists():
            print(f"Found A-Roll file at alternative path: {path}")
            # Update the status to use this path in the future
            aroll_status["local_path"] = str(path)
            st.session_state.content_status["aroll"][segment_id] = aroll_status
            return str(path), True, None
    
    # If not found, check if we need to extract from HeyGen URL
    if "video_url" in aroll_status and aroll_status["video_url"]:
        try:
            # Import HeyGen API helper
            try:
                from utils.heygen_api import HeyGenAPI
            except ImportError:
                return None, False, f"HeyGen API module not found"
            
            # Create output directory if it doesn't exist
            output_dir = project_path / "media" / "a-roll"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Download the video
            api_key = os.environ.get("HEYGEN_API_KEY", "")
            if not api_key:
                return None, False, f"HeyGen API key not found in environment variables"
            
            heygen_api = HeyGenAPI(api_key)
            output_path = str(output_dir / f"{segment_id}.mp4")
            
            print(f"Downloading A-Roll video from HeyGen URL to: {output_path}")
            download_result = heygen_api.download_video(aroll_status["video_url"], output_path)
            
            if download_result["status"] == "success":
                # Update status file
                aroll_status["local_path"] = output_path
                aroll_status["downloaded"] = True
                st.session_state.content_status["aroll"][segment_id] = aroll_status
                
                # Save updated status to the correct location
                aroll_status_file = project_path / "aroll_status.json"
                with open(aroll_status_file, "w") as f:
                    json.dump(st.session_state.content_status["aroll"], f, indent=2)
                
                return output_path, True, None
            else:
                return None, False, f"Failed to download video: {download_result.get('message', 'Unknown error')}"
        except Exception as e:
            return None, False, f"Exception while downloading video: {str(e)}"
    
    # Debug information
    print(f"Could not find A-Roll file for {segment_id}")
    print(f"Checked paths:")
    print(f"  - {aroll_status.get('local_path', 'No local_path in status')}")
    print(f"  - {aroll_file}")
    for path in alt_paths:
        print(f"  - {path}")
    print(f"Status data: {aroll_status}")
    
    # Not found anywhere, return error
    return None, False, f"A-Roll file for {segment_id} not found. Please make sure you've generated A-Roll videos in the A-Roll Transcription step."

def get_broll_filepath(segment_id, segment_data):
    """
    Get the filepath for a B-Roll segment, supporting different path formats
    Always prioritizes videos over images, and finds the most recent files by modification time
    
    Args:
        segment_id: ID of the segment (e.g., 'segment_0')
        segment_data: Data for the segment
        
    Returns:
        str: Path to the B-Roll file if found, None otherwise
    """
    # Track matching files with their modification times, separating videos and images
    matching_videos = []
    matching_images = []
    
    # Get content_type if available from the segment data
    content_type = segment_data.get("content_type", None)
    
    # Check the file path in the content status
    if "file_path" in segment_data:
        file_path = segment_data["file_path"]
        
        # If the file path is just a filename without directory, prepend media/b-roll/
        if not os.path.dirname(file_path):
            media_path = f"media/b-roll/{file_path}"
            if os.path.exists(media_path):
                file_ext = os.path.splitext(media_path)[1].lower()
                mod_time = os.path.getmtime(media_path)
                
                if file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                    matching_videos.append((media_path, mod_time))
                    print(f"Found B-Roll video: {media_path} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
                elif file_ext in ['.png', '.jpg', '.jpeg']:
                    matching_images.append((media_path, mod_time))
                    print(f"Found B-Roll image: {media_path} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
        
        # Check if the provided path exists directly
        if os.path.exists(file_path):
            file_ext = os.path.splitext(file_path)[1].lower()
            mod_time = os.path.getmtime(file_path)
            
            if file_ext in ['.mp4', '.mov', '.avi', '.webm']:
                matching_videos.append((file_path, mod_time))
                print(f"Found B-Roll video: {file_path} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
            elif file_ext in ['.png', '.jpg', '.jpeg']:
                matching_images.append((file_path, mod_time))
                print(f"Found B-Roll image: {file_path} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Try alternative formats if the primary file path doesn't exist
    segment_num = segment_id.split('_')[-1]
    prompt_id = segment_data.get('prompt_id', '')
    
    # Check for both video and image file extensions
    video_extensions = [".mp4", ".mov", ".avi", ".webm"]
    image_extensions = [".png", ".jpg", ".jpeg"]
    all_extensions = video_extensions + image_extensions
    
    # Search in multiple potential directories
    potential_dirs = [
        os.path.join(project_path, "media", "b-roll"),
        os.path.join(project_path, "media", "broll"),
        os.path.join("media", "b-roll"),
        os.path.join("media", "broll"),
        os.path.join(app_root, "media", "b-roll"),
        os.path.join(app_root, "media", "broll"),
        os.path.join("config", "user_data", "my_short_video", "media", "broll"),
        os.path.join("config", "user_data", "my_short_video", "media", "b-roll")
    ]
    
    # Different file naming patterns to try
    base_patterns = [
        # Common formats
        f"broll_segment_{segment_num}",
        f"fetched_broll_segment_{segment_num}",
        f"broll_video_segment_{segment_num}",
        # Additional patterns
        f"image_{segment_num}",
        f"broll_{segment_num}",
        f"video_{segment_num}"
    ]
    
    # Try each pattern with each extension in each potential directory
    for directory in potential_dirs:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if any(pattern in filename for pattern in base_patterns):
                    file_path = os.path.join(directory, filename)
                    file_ext = os.path.splitext(filename)[1].lower()
                    mod_time = os.path.getmtime(file_path)
                    
                    # Categorize as video or image
                    if file_ext in video_extensions:
                        matching_videos.append((file_path, mod_time))
                        print(f"Found B-Roll video by pattern: {filename}")
                    elif file_ext in image_extensions:
                        matching_images.append((file_path, mod_time))
                        print(f"Found B-Roll image by pattern: {filename}")
    
    # Sort both lists by modification time (newest first)
    matching_videos.sort(key=lambda x: x[1], reverse=True)
    matching_images.sort(key=lambda x: x[1], reverse=True)
    
    # If content_type is specified, prioritize that type
    if content_type == "video" and matching_videos:
        newest_file = matching_videos[0][0]
        mod_time = matching_videos[0][1]
        print(f"Using newest B-Roll VIDEO for {segment_id}: {newest_file} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
        # Update segment_data to use this file path
        segment_data["file_path"] = newest_file
        return newest_file
    elif content_type == "image" and matching_images:
        newest_file = matching_images[0][0]
        mod_time = matching_images[0][1]
        print(f"Using newest B-Roll IMAGE for {segment_id}: {newest_file} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
        # Update segment_data to use this file path
        segment_data["file_path"] = newest_file
        return newest_file
    
    # If no content_type specified or no match found for that type, prioritize videos over images
    if matching_videos:
        newest_file = matching_videos[0][0]
        mod_time = matching_videos[0][1]
        print(f"Using newest B-Roll VIDEO for {segment_id}: {newest_file} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
        # Update segment_data to use this file path
        segment_data["file_path"] = newest_file
        segment_data["content_type"] = "video"
        return newest_file
    elif matching_images:
        newest_file = matching_images[0][0]
        mod_time = matching_images[0][1]
        print(f"Using newest B-Roll IMAGE for {segment_id}: {newest_file} (modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')})")
        # Update segment_data to use this file path
        segment_data["file_path"] = newest_file
        segment_data["content_type"] = "image"
        return newest_file
    
    print(f"B-Roll file not found for {segment_id}")
    return None

# Function to create assembly sequence
def create_assembly_sequence():
    """
    Create a sequence of video segments for assembly based on the content status
    and selected sequence pattern
    
    Returns:
        dict: Result containing status and sequence
    """
    # Get content status
    content_status = load_content_status()
    if not content_status:
        return {"status": "error", "message": "Could not load content status"}
        
    aroll_segments = content_status.get("aroll", {})
    broll_segments = content_status.get("broll", {})
    
    # Initialize the used_aroll_segments tracking set
    used_aroll_segments = set()
    
    print(f"Found {len(aroll_segments)} A-Roll segments and {len(broll_segments)} B-Roll segments")
    print(f"A-Roll keys: {list(aroll_segments.keys())}")
    print(f"B-Roll keys: {list(broll_segments.keys())}")
    
    # Get the script segments
    script_segments = load_segments()
    aroll_script_segments = [s for s in script_segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    
    print(f"Found {len(aroll_script_segments)} A-Roll segments in script.json")
    for i, segment in enumerate(aroll_script_segments):
        segment_id = segment.get("segment_id", f"segment_{i}")
        file_path = segment.get("file_path", "Not found")
        exists = "✓" if file_path != "Not found" and os.path.exists(file_path) else "✗"
        print(f"  Script segment {i}: ID={segment_id}, Path={file_path} {exists}")
    
    # Map segment indices to segment_ids
    segment_id_map = {}
    for i, segment in enumerate(aroll_script_segments):
        segment_id = segment.get("segment_id", f"segment_{i}")
        segment_id_map[i] = segment_id
        # Also create reverse mapping for lookup by segment_id
        segment_id_map[segment_id] = i
    
    # Get selected sequence pattern
    selected_sequence = st.session_state.get("selected_sequence", "No Overlap (Prevents audio repetition - recommended)")
    
    # If Custom is selected and we already have a manually created sequence, preserve it
    if "Custom" in selected_sequence and "video_assembly" in st.session_state and "sequence" in st.session_state.video_assembly:
        existing_sequence = st.session_state.video_assembly.get("sequence", [])
        if existing_sequence:
            return {"status": "success", "sequence": existing_sequence}
    
    # Create a sequence for assembly based on the selected pattern
    assembly_sequence = []
    
    # Check how many segments we have
    total_aroll_segments = len(aroll_script_segments)
    total_broll_segments = len(broll_segments)
    
    if total_aroll_segments == 0:
        return {"status": "error", "message": "No A-Roll segments found. Please go to the A-Roll Transcription page to create A-Roll videos first."}
    
    # Helper function to extract duration information from segment data
    def extract_duration_info(segment_data):
        """Extract duration information from segment data"""
        start_time = segment_data.get("start_time", 0)
        end_time = segment_data.get("end_time", 0)
        duration = segment_data.get("duration", 0)
        
        # If we have start and end times but no duration, calculate it
        if duration == 0 and end_time > start_time:
            duration = end_time - start_time
            print(f"Calculated duration from timestamps: {duration}s")
        
        return {
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration
        }
    
    # No Overlap pattern (prioritizes preventing audio repetition)
    if "No Overlap" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
        # First, identify all available A-Roll segments
        available_aroll_segments = []
        for i in range(total_aroll_segments):
            segment_id = segment_id_map.get(i, f"segment_{i}")
            segment_data = next((s for s in aroll_script_segments if s.get("segment_id") == segment_id), 
                               aroll_script_segments[i] if i < len(aroll_script_segments) else None)
            
            if segment_data:
                aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment_data)
                if aroll_path:
                    # Extract duration information
                    duration_info = extract_duration_info(segment_data)
                    
                    available_aroll_segments.append({
                        "segment_id": segment_id,
                        "segment_data": segment_data,
                        "aroll_path": aroll_path,
                        "index": i,
                        "start_time": duration_info["start_time"],
                        "end_time": duration_info["end_time"],
                        "duration": duration_info["duration"]
                    })
        
        print(f"Found {len(available_aroll_segments)} available A-Roll segments")
        
        # First segment is A-Roll only (if we have enough segments)
        if len(available_aroll_segments) > 0:
            first_segment = available_aroll_segments[0]
            segment_id = first_segment["segment_id"]
            aroll_path = first_segment["aroll_path"]
            
            print(f"Adding A-Roll segment 0 (ID: {segment_id}) with path: {aroll_path}")
            assembly_sequence.append({
                "type": "aroll_full",
                "aroll_path": aroll_path,
                "broll_path": None,
                "segment_id": segment_id,
                "start_time": first_segment.get("start_time", 0),
                "end_time": first_segment.get("end_time", 0),
                "duration": first_segment.get("duration", 0)
            })
            # Mark as used
            used_aroll_segments.add(segment_id)
            
            # Remove from available segments
            available_aroll_segments = available_aroll_segments[1:]
        
        # Last segment is A-Roll only (if we have enough segments)
        last_segment = None
        if len(available_aroll_segments) > 1:
            last_segment = available_aroll_segments[-1]
            available_aroll_segments = available_aroll_segments[:-1]
        
        # Middle segments use B-Roll visuals with A-Roll audio
        for i, aroll_segment in enumerate(available_aroll_segments):
            segment_id = aroll_segment["segment_id"]
            aroll_path = aroll_segment["aroll_path"]
            
            # Use the appropriate B-Roll segment or cycle through available ones
            broll_index = i % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if broll_segment_id in broll_segments:
                broll_data = broll_segments[broll_segment_id]
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                if broll_path:
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {segment_id}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": segment_id,
                        "broll_id": broll_segment_id,
                        "start_time": aroll_segment.get("start_time", 0),
                        "end_time": aroll_segment.get("end_time", 0),
                        "duration": aroll_segment.get("duration", 0)
                    })
                    # Mark as used
                    used_aroll_segments.add(segment_id)
                else:
                    st.error(f"B-Roll file not found for {broll_segment_id}")
            else:
                # If no matching B-Roll, use A-Roll visuals
                print(f"No B-Roll segment available for {segment_id}, using A-Roll visuals")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": segment_id,
                    "start_time": aroll_segment.get("start_time", 0),
                    "end_time": aroll_segment.get("end_time", 0),
                    "duration": aroll_segment.get("duration", 0)
                })
                # Mark as used
                used_aroll_segments.add(segment_id)
        
        # Add the last segment if we saved one
        if last_segment:
            segment_id = last_segment["segment_id"]
            aroll_path = last_segment["aroll_path"]
            
            print(f"Adding final A-Roll segment (ID: {segment_id}) with path: {aroll_path}")
            assembly_sequence.append({
                "type": "aroll_full",
                "aroll_path": aroll_path,
                "broll_path": None,
                "segment_id": segment_id,
                "start_time": last_segment.get("start_time", 0),
                "end_time": last_segment.get("end_time", 0),
                "duration": last_segment.get("duration", 0)
            })
            # Mark as used
            used_aroll_segments.add(segment_id)
    
    # B-Roll Full (all visuals are B-Roll with A-Roll audio)
    elif "B-Roll Full" in selected_sequence:
        # All segments use B-Roll visuals with A-Roll audio
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
        # First arrange all A-Roll segments sequentially, with B-Roll visuals
        for i in range(total_aroll_segments):
            # Use the mapped segment_id if available
            segment_id = segment_id_map.get(i, f"segment_{i}")
            
            # Skip if this A-Roll segment was already used
            if segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {segment_id} to prevent audio overlap")
                continue
                
            # Use the appropriate B-Roll segment or cycle through available ones
            # To prevent audio overlaps, each A-Roll segment is used exactly once
            broll_index = i % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            # Get the segment data
            segment_data = next((s for s in aroll_script_segments if s.get("segment_id") == segment_id), 
                              aroll_script_segments[i] if i < len(aroll_script_segments) else None)
            
            if segment_data and broll_segment_id in broll_segments:
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                # Extract duration information
                duration_info = extract_duration_info(segment_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i} (ID: {segment_id})")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": segment_id,
                        "broll_id": broll_segment_id,
                        "start_time": duration_info["start_time"],
                        "end_time": duration_info["end_time"],
                        "duration": duration_info["duration"]
                    })
                    # Mark this A-Roll segment as used
                    used_aroll_segments.add(segment_id)
                    
                    print(f"✅ Added audio segment {segment_id} to sequence position {len(assembly_sequence)}")
    # Standard pattern (original implementation)
    elif "Standard" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
        # First segment is A-Roll only
        first_segment_id = segment_id_map.get(0, "segment_0")
        first_segment = next((s for s in aroll_script_segments if s.get("segment_id") == first_segment_id), 
                            aroll_script_segments[0] if aroll_script_segments else None)
        
        if first_segment:
            aroll_path, aroll_success, aroll_error = get_aroll_filepath(first_segment_id, first_segment)
            
            # Extract duration information
            duration_info = extract_duration_info(first_segment)
            
            if aroll_path:
                print(f"Adding A-Roll segment 0 (ID: {first_segment_id}) with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": first_segment_id,
                    "start_time": duration_info["start_time"],
                    "end_time": duration_info["end_time"],
                    "duration": duration_info["duration"]
                })
                # Mark as used
                used_aroll_segments.add(first_segment_id)
            else:
                st.error(f"A-Roll file not found for first segment: {first_segment.get('file_path', 'No path specified')}")
        
        # Middle segments: B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments - 1):
            # Use the mapped segment_id if available
            segment_id = segment_id_map.get(i, f"segment_{i}")
            
            # Skip if this A-Roll segment was already used
            if segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {segment_id} to prevent audio overlap")
                continue
                
            broll_segment_id = f"segment_{i-1}"  # B-Roll segments are named "segment_X" in content_status.json
            
            # Get the segment data
            segment_data = next((s for s in aroll_script_segments if s.get("segment_id") == segment_id), None)
            if not segment_data and i < len(aroll_script_segments):
                segment_data = aroll_script_segments[i]
            
            if segment_data and broll_segment_id in broll_segments:
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                # Extract duration information
                duration_info = extract_duration_info(segment_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {i-1} with A-Roll segment {i} (ID: {segment_id})")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": segment_id,
                        "broll_id": broll_segment_id,
                        "start_time": duration_info["start_time"],
                        "end_time": duration_info["end_time"],
                        "duration": duration_info["duration"]
                    })
                    # Mark as used
                    used_aroll_segments.add(segment_id)
                else:
                    if not aroll_path:
                        st.error(f"A-Roll file not found for {segment_id}")
                    if not broll_path:
                        st.error(f"B-Roll file not found for {broll_segment_id}")
        
        # Last segment is A-Roll only
        last_idx = total_aroll_segments - 1
        last_segment_id = segment_id_map.get(last_idx, f"segment_{last_idx}")
        
        # Get the last segment data
        last_segment = next((s for s in aroll_script_segments if s.get("segment_id") == last_segment_id), 
                          aroll_script_segments[last_idx] if last_idx < len(aroll_script_segments) else None)
        
        # Skip if this A-Roll segment was already used
        if last_segment_id not in used_aroll_segments and last_segment:
            aroll_path, aroll_success, aroll_error = get_aroll_filepath(last_segment_id, last_segment)
            
            # Extract duration information
            duration_info = extract_duration_info(last_segment)
            
            if aroll_path:
                print(f"Adding final A-Roll segment (ID: {last_segment_id}) with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": last_segment_id,
                    "start_time": duration_info["start_time"],
                    "end_time": duration_info["end_time"],
                    "duration": duration_info["duration"]
                })
                # Mark as used
                used_aroll_segments.add(last_segment_id)
    
    # A-Roll Bookends pattern (similar changes needed for other patterns)
    elif "Bookends" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
        # First segment is A-Roll only
        first_segment_id = segment_id_map.get(0, "segment_0")
        first_segment = next((s for s in aroll_script_segments if s.get("segment_id") == first_segment_id), 
                            aroll_script_segments[0] if aroll_script_segments else None)
        
        if first_segment:
            aroll_path, aroll_success, aroll_error = get_aroll_filepath(first_segment_id, first_segment)
            
            # Extract duration information
            duration_info = extract_duration_info(first_segment)
            
            if aroll_path:
                print(f"Adding A-Roll segment 0 (ID: {first_segment_id}) with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": first_segment_id,
                    "start_time": duration_info["start_time"],
                    "end_time": duration_info["end_time"],
                    "duration": duration_info["duration"]
                })
                # Mark as used
                used_aroll_segments.add(first_segment_id)
        
        # All middle segments use B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments - 1):
            # Use the mapped segment_id if available
            segment_id = segment_id_map.get(i, f"segment_{i}")
            
            # Skip if this A-Roll segment was already used
            if segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {segment_id} to prevent audio overlap")
                continue
                
            # Get the segment data
            segment_data = next((s for s in aroll_script_segments if s.get("segment_id") == segment_id), None)
            if not segment_data and i < len(aroll_script_segments):
                segment_data = aroll_script_segments[i]
            
            # Use the appropriate B-Roll segment or cycle through available ones
            broll_index = (i - 1) % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if segment_data and broll_segment_id in broll_segments:
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                # Extract duration information
                duration_info = extract_duration_info(segment_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i} (ID: {segment_id})")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": segment_id,
                        "broll_id": broll_segment_id,
                        "start_time": duration_info["start_time"],
                        "end_time": duration_info["end_time"],
                        "duration": duration_info["duration"]
                    })
                    # Mark as used
                    used_aroll_segments.add(segment_id)
        
        # Last segment is A-Roll only
        last_idx = total_aroll_segments - 1
        last_segment_id = segment_id_map.get(last_idx, f"segment_{last_idx}")
        
        # Get the last segment data
        last_segment = next((s for s in aroll_script_segments if s.get("segment_id") == last_segment_id), 
                          aroll_script_segments[last_idx] if last_idx < len(aroll_script_segments) else None)
        
        # Skip if this A-Roll segment was already used
        if last_segment_id not in used_aroll_segments and last_segment:
            aroll_path, aroll_success, aroll_error = get_aroll_filepath(last_segment_id, last_segment)
            
            # Extract duration information
            duration_info = extract_duration_info(last_segment)
            
            if aroll_path:
                print(f"Adding final A-Roll segment (ID: {last_segment_id}) with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": last_segment_id,
                    "start_time": duration_info["start_time"],
                    "end_time": duration_info["end_time"],
                    "duration": duration_info["duration"]
                })
                # Mark as used
                used_aroll_segments.add(last_segment_id)
    
    # Final summary of what was included
    print(f"Created assembly sequence with {len(assembly_sequence)} items")
    print(f"Used {len(used_aroll_segments)}/{total_aroll_segments} A-Roll segments")
    
    if assembly_sequence:
        return {
            "status": "success",
            "sequence": assembly_sequence
        }
    else:
        return {
            "status": "error",
            "message": "No valid segments found for assembly"
        }

def check_for_audio_overlaps(sequence):
    """
    Check for potential audio overlaps in the sequence and display warnings in UI
    
    Args:
        sequence: List of video segments to assemble
    """
    used_audio_segments = {}
    overlaps = []
    segment_details = []
    
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        
        # Track which A-Roll audio segments are being used
        if segment_id in used_audio_segments:
            overlaps.append({
                "segment": i+1, 
                "audio_id": segment_id,
                "previous_use": used_audio_segments[segment_id]["index"]+1,
                "previous_type": used_audio_segments[segment_id]["type"]
            })
            
            # Add this segment to the details with overlap flag
            segment_details.append({
                "index": i,
                "segment_id": segment_id,
                "type": item["type"],
                "has_overlap": True,
                "original_index": used_audio_segments[segment_id]["index"]
            })
        else:
            used_audio_segments[segment_id] = {
                "index": i,
                "type": item["type"]
            }
            
            # Add to details without overlap flag
            segment_details.append({
                "index": i,
                "segment_id": segment_id,
                "type": item["type"],
                "has_overlap": False
            })
    
    if overlaps:
        st.warning("⚠️ **Audio Overlap Warning**: Your sequence contains multiple uses of the same audio segments.", icon="⚠️")
        st.markdown("This may cause audio to be repeated or overlapped in your final video.")
        
        # Create a detailed timeline visualization
        st.markdown("### 🔊 Audio Track Sequence")
        st.markdown("The following shows your audio track sequence, with overlaps highlighted:")
        
        # Create a formatted table of segments
        segments_md = "| # | Segment ID | Type | Status |\n"
        segments_md += "| --- | --- | --- | --- |\n"
        
        for segment in segment_details:
            status = "⚠️ **OVERLAP**" if segment["has_overlap"] else "✅ OK"
            overlap_info = f" (duplicate of #{segment['original_index']+1})" if segment["has_overlap"] else ""
            type_display = "A-Roll Full" if segment["type"] == "aroll_full" else "B-Roll with A-Roll Audio"
            segments_md += f"| {segment['index']+1} | {segment['segment_id']} | {type_display} | {status}{overlap_info} |\n"
        
        st.markdown(segments_md)
        
        for overlap in overlaps:
            st.warning(f"**Segment {overlap['segment']}** uses the same audio ({overlap['audio_id']}) as segment {overlap['previous_use']}")
        
        st.markdown("""
        **To fix audio overlaps:**
        
        1. **Best solution:** Use the Custom arrangement to control exactly which audio segments are used
        2. Try a different sequence pattern that doesn't reuse audio segments
        3. Use "B-Roll Full" preset which is designed to ensure each A-Roll audio segment is used exactly once
        """)
        
        # Display additional debugging info in an expander
        with st.expander("Advanced Audio Overlap Analysis"):
            st.markdown(f"**Total segments:** {len(sequence)}")
            st.markdown(f"**Unique audio tracks:** {len(used_audio_segments)}")
            st.markdown(f"**Overlapping audio tracks:** {len(overlaps)}")
            
            # Display the actual sequence composition
            sequence_details = ""
            for i, item in enumerate(sequence):
                segment_id = item.get("segment_id", "unknown")
                type_str = item.get("type", "unknown")
                aroll_path = item.get("aroll_path", "none")
                broll_path = item.get("broll_path", "none")
                
                sequence_details += f"**Segment {i+1}:** {segment_id} ({type_str})\n"
                sequence_details += f"  - A-Roll: {os.path.basename(aroll_path)}\n"
                if broll_path != "none":
                    sequence_details += f"  - B-Roll: {os.path.basename(broll_path)}\n"
                sequence_details += "\n"
            
            st.markdown(sequence_details)
        
        return True
    return False

# Replace the assemble_video function to include fallback to simple_assembly
def assemble_video():
    """
    Assemble the final video from A-Roll and B-Roll segments
    """
    if not MOVIEPY_AVAILABLE:
        st.error("MoviePy is not available. Installing required packages...")
        st.info("Please run: `pip install moviepy==1.0.3` in your virtual environment")
        return

    # If we're using Custom arrangement and already have a sequence, use it directly
    if ("Custom" in st.session_state.get("selected_sequence", "") and 
        "sequence" in st.session_state.video_assembly and 
        st.session_state.video_assembly["sequence"]):
        assembly_sequence = st.session_state.video_assembly["sequence"]
        # Verify the sequence has at least one item
        if not assembly_sequence:
            st.error("No valid segments found in the custom sequence. Please create a sequence first.")
            return
        sequence_result = {"status": "success", "sequence": assembly_sequence}
        print("Using existing custom sequence for assembly")
    else:
        # Get the assembly sequence
        sequence_result = create_assembly_sequence()
        
    if sequence_result["status"] != "success":
        error_message = sequence_result.get("message", "Failed to create assembly sequence")
        st.error(error_message)
        
        # Add navigation button if no A-Roll segments found
        if "No A-Roll segments found" in error_message:
            st.warning("You need to create A-Roll segments first.")
            
            # Add button to navigate to A-Roll Transcription page
            if st.button("Go to A-Roll Transcription", type="primary"):
                st.switch_page("pages/4.5_ARoll_Transcription.py")
        
        return
    
    # Get the assembly sequence from the result
    assembly_sequence = sequence_result["sequence"]
        
    # Check for audio overlaps and warn the user
    has_overlaps = check_for_audio_overlaps(assembly_sequence)
    if has_overlaps:
        continue_anyway = st.checkbox("Continue with assembly despite audio overlaps", value=False)
        if not continue_anyway:
            st.warning("Video assembly paused until audio overlaps are resolved or you choose to continue anyway.")
            return
    
    # Parse selected resolution
    resolution_options = {"1080x1920 (9:16)": (1080, 1920), 
                         "720x1280 (9:16)": (720, 1280), 
                         "1920x1080 (16:9)": (1920, 1080)}
    selected_resolution = st.session_state.get("selected_resolution", "1080x1920 (9:16)")
    width, height = resolution_options[selected_resolution]
    
    # Set up progress reporting
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    def update_progress(progress, message):
        # Update the progress bar and text
        progress_bar.progress(min(1.0, progress / 100))
        progress_text.text(f"{message} ({int(progress)}%)")
    
    # Perform the video assembly using our helper
    st.info("Assembling video, please wait...")
    update_progress(0, "Starting video assembly")
    
    # Create output directory if it doesn't exist
    output_dir = project_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Display assembly method options
    assembly_col1, assembly_col2 = st.columns(2)
    
    with assembly_col1:
        use_simple_assembly = st.session_state.get("use_simple_assembly", False)
        st.checkbox("Use simple assembly (FFmpeg direct)", value=use_simple_assembly, 
                    help="Use this if you experience issues with MoviePy", 
                    key="use_simple_assembly")
    
    with assembly_col2:
        # Only show fixed assembly option if available
        if FIXED_ASSEMBLY_AVAILABLE:
            use_fixed_assembly = st.session_state.get("use_fixed_assembly", True)
            st.checkbox("Use fixed assembly (Accurate B-Roll durations)", value=use_fixed_assembly,
                       help="Fix the issue where B-Roll images have incorrect durations", 
                       key="use_fixed_assembly")
    
    try:
        # Check if we should use the fixed assembly method
        if FIXED_ASSEMBLY_AVAILABLE and st.session_state.get("use_fixed_assembly", True):
            # Use the fixed assembly method that correctly handles B-Roll image durations
            update_progress(10, "Using fixed assembly method for accurate B-Roll durations")
            
            # Get project directory
            project_dir = str(project_path)
            
            # Generate a unique output name
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"fixed_assembly_{timestamp}"
            
            # Call the fixed assembly function
            result = {"status": "error", "message": "Not started"}
            
            try:
                # Run the fixed assembly
                output_path = fixed_assembly(project_dir, output_name)
                
                if output_path:
                    result = {
                        "status": "success",
                        "message": "Video assembled successfully with accurate B-Roll durations",
                        "output_path": output_path
                    }
                else:
                    result = {
                        "status": "error",
                        "message": "Fixed assembly failed to generate an output video"
                    }
            except Exception as e:
                import traceback
                result = {
                    "status": "error",
                    "message": f"Error during fixed assembly: {str(e)}",
                    "traceback": traceback.format_exc()
                }
        
        # Try primary or simple assembly methods if fixed assembly wasn't used or failed
        elif not st.session_state.get("use_simple_assembly", False):
            # Call our helper function
            result = helper_assemble_video(
                sequence=assembly_sequence,
                target_resolution=(width, height),
                output_dir=str(output_dir),
                progress_callback=update_progress
            )
            
            # If primary method failed and simple assembly is available, try it
            if result["status"] == "error" and simple_assemble_video:
                st.warning("Primary assembly method failed. Trying simple assembly fallback...")
                update_progress(0, "Starting simple assembly fallback")
                
                # Try fallback method
                result = simple_assemble_video(
                    sequence=assembly_sequence,
                    output_path=None,  # Use default path
                    target_resolution=(width, height),
                    progress_callback=update_progress
                )
        else:
            # Use simple assembly method directly
            result = simple_assemble_video(
                sequence=assembly_sequence,
                output_path=None,  # Use default path
                target_resolution=(width, height),
                progress_callback=update_progress
            )
        
        # Process result
        if result["status"] == "success":
            st.session_state.video_assembly["status"] = "complete"
            st.session_state.video_assembly["output_path"] = result["output_path"]
            
            # Mark step as complete
            mark_step_complete("video_assembly")
            
            st.success(f"Video assembled successfully!")
            update_progress(100, "Video assembly complete")
            st.rerun()
        else:
            st.session_state.video_assembly["status"] = "error"
            st.session_state.video_assembly["error"] = result["message"]
            
            # Display detailed error information
            st.error(f"Video assembly failed: {result['message']}")
            if "missing_files" in result:
                st.warning("Missing files:")
                for missing in result["missing_files"]:
                    st.warning(f" - {missing}")
            
            # Show traceback in expander if available
            if "traceback" in result:
                with st.expander("Error Details"):
                    st.code(result["traceback"])
                    
    except Exception as e:
        st.session_state.video_assembly["status"] = "error"
        st.session_state.video_assembly["error"] = str(e)
        
        st.error(f"Unexpected error during video assembly: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# Replace the assembly options section with this improved version
st.subheader("Assembly Options")

# Add sequence selection with improved descriptions
sequence_options = [
    "No Overlap (Prevents audio repetition - recommended)",
    "Standard (A-Roll start, B-Roll middle with A-Roll audio, A-Roll end)",
    "A-Roll Bookends (A-Roll at start and end only, B-Roll middle with A-Roll audio)",
    "A-Roll Sandwich (A-Roll at start, middle, and end; B-Roll with A-Roll audio between)",
    "B-Roll Heavy (Only first segment uses A-Roll visual; rest use B-Roll with A-Roll audio)",
    "B-Roll Full (All segments use B-Roll visuals with A-Roll audio) - Prevents audio overlaps",
    "Custom (Manual Arrangement)"
]
st.session_state.selected_sequence = st.selectbox(
    "Sequence Pattern:", 
    sequence_options,
    index=sequence_options.index(st.session_state.get("selected_sequence", sequence_options[0])),
    key="sequence_selectbox"
)

# Add warning about audio overlaps in certain presets
if not "No Overlap" in st.session_state.selected_sequence and not "B-Roll Full" in st.session_state.selected_sequence and not "Custom" in st.session_state.selected_sequence:
    st.info("""
    ℹ️ **Note:** Some sequence patterns may cause audio overlaps if there are more A-Roll segments than B-Roll segments.
    If you experience audio overlaps, try the "No Overlap" or "B-Roll Full" preset to prevent audio repetition.
    """)

# If Custom is selected, enable manual editing
if st.session_state.selected_sequence == "Custom (Manual Arrangement)" and not st.session_state.get("enable_manual_editing", False):
    st.session_state.enable_manual_editing = True
    st.rerun()

# Resolution selection
resolution_options = ["1080x1920 (9:16)", "720x1280 (9:16)", "1920x1080 (16:9)"]
st.session_state.selected_resolution = st.selectbox(
    "Output Resolution:", 
    resolution_options,
    index=resolution_options.index(st.session_state.get("selected_resolution", "1080x1920 (9:16)")),
    key="resolution_selectbox_main"
)

# Add a dependency check option
if st.button("Check Dependencies", type="secondary", help="Check if all required packages are installed", key="check_deps_main"):
    with st.spinner("Checking dependencies..."):
        try:
            subprocess.run([sys.executable, "utils/video/dependencies.py"], check=True)
            st.success("All dependencies are installed!")
        except Exception as e:
            st.error(f"Error checking dependencies: {str(e)}")
            st.info("Please run `python utils/video/dependencies.py` manually to install required packages")

# Replace the assembly button with an improved version
if st.button("🎬 Assemble Video", type="primary", use_container_width=True, key="assemble_video_main"):
    assemble_video()

# Display output video if completed
if st.session_state.video_assembly["status"] == "complete" and st.session_state.video_assembly["output_path"]:
    st.subheader("Output Video")
    output_path = st.session_state.video_assembly["output_path"]
    
    if os.path.exists(output_path):
        # Display video
        st.video(output_path)
        
        # Download button
        with open(output_path, "rb") as file:
            st.download_button(
                label="📥 Download Video",
                data=file,
                file_name=os.path.basename(output_path),
                mime="video/mp4"
            )
    else:
        st.error("Video file not found. It may have been moved or deleted.")

# Video Assembly Page
render_step_header(6, "Video Assembly", 8)
st.title("🎬 Video Assembly")
st.markdown("""
Create your final video by assembling A-Roll and B-Roll segments.
This step will combine all the visual assets into a single, coherent video.
""")

# Check if MoviePy is available
if not MOVIEPY_AVAILABLE:
    st.error("⚠️ MoviePy is not available. Video assembly requires MoviePy.")
    st.info("Please install MoviePy by running: `pip install moviepy==1.0.3`")
    
    with st.expander("Installation Instructions"):
        st.markdown("""
        ### Installing MoviePy
        
        1. **Activate your virtual environment**: 
           ```bash
           source .venv/bin/activate
           ```
        
        2. **Install MoviePy and dependencies**:
           ```bash
           pip install moviepy==1.0.3 ffmpeg-python
           ```
           
        3. **Install FFMPEG (if not already installed)**:
           
           On Mac:
           ```bash
           brew install ffmpeg
           ```
           
           On Ubuntu/Debian:
           ```bash
           sudo apt-get install ffmpeg
           ```
           
           On Windows:
           - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
           - Add to your PATH
        
        4. **Restart the Streamlit app**:
           ```bash
           streamlit run pages/6_Video_Assembly.py
           ```
        """)
    st.stop()

# Load content status and segments
content_status = load_content_status()
segments = load_segments()

if content_status and segments:
    # Display summary of available content
    st.subheader("Content Summary")
    
    # Count A-Roll and B-Roll segments
    aroll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    broll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    
    # Count completed segments - a segment is complete if it has a file_path or local_path
    aroll_completed = 0
    for i, segment in enumerate(aroll_segments):
        # Get segment_id from the segment itself or create one from index
        segment_id = segment.get("segment_id", f"segment_{i}")
        
        # Check multiple indicators that a segment is "complete"
        segment_data = content_status["aroll"].get(segment_id, {})
        
        # First check if the segment itself has a file_path that exists
        has_file_path = False
        if "file_path" in segment and os.path.exists(segment["file_path"]):
            has_file_path = True
            print(f"Segment {segment_id} has valid file_path: {segment['file_path']}")
        
        # Next check if the segment status has a local_path that exists
        has_local_path = False
        if "local_path" in segment_data and os.path.exists(segment_data["local_path"]):
            has_local_path = True
            print(f"Segment {segment_id} has valid local_path: {segment_data['local_path']}")
        
        # Then try to find the file using our path resolution function
        found_file = False
        resolved_path, success, _ = get_aroll_filepath(segment_id, segment)
        if success and resolved_path and os.path.exists(resolved_path):
            found_file = True
            print(f"Segment {segment_id} found via path resolution: {resolved_path}")
        
        # Also check the directory for any files matching this segment pattern
        segment_pattern_found = False
        segment_num = segment_id.split('_')[-1] if '_' in segment_id else segment_id
        
        # Check for files with segment ID in different formats
        segment_patterns = [
            f"*segment_{segment_num}.mp4",
            f"*_segment_{segment_num}.mp4",
            f"*segment{segment_num}.mp4",
            f"*_segment{segment_num}.mp4",
            f"*seg_{segment_num}.mp4",
            f"*_{segment_num}.mp4",
            f"*{segment_num}.mp4"
        ]
        
        # Look for files matching patterns in a-roll directories
        potential_dirs = [
            project_path / "media" / "a-roll",
            project_path / "media" / "a-roll" / "segments",
            project_path / "media" / "aroll",
            project_path / "media" / "aroll" / "segments"
        ]
        
        import glob
        for directory in potential_dirs:
            if directory.exists():
                for pattern in segment_patterns:
                    matches = glob.glob(str(directory / pattern))
                    if matches:
                        segment_pattern_found = True
                        print(f"Segment {segment_id} found matching pattern: {matches[0]}")
                        break
                if segment_pattern_found:
                    break
        
        # Finally check for segment status being explicitly marked as complete
        has_complete_status = segment_data.get("status") == "complete"
        
        # Count as completed if any of the above checks passed
        if has_file_path or has_local_path or found_file or has_complete_status or segment_pattern_found:
            aroll_completed += 1
            print(f"Marking segment {segment_id} as completed")
        else:
            print(f"Segment {segment_id} is not completed: file_path={has_file_path}, local_path={has_local_path}, resolved_path={found_file}, pattern={segment_pattern_found}, status={has_complete_status}")
    
    broll_completed = sum(1 for i in range(len(broll_segments)) 
                         if f"segment_{i}" in content_status["broll"] and 
                         content_status["broll"][f"segment_{i}"].get("status") == "complete")
    
    # Display counts
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"A-Roll Segments: {aroll_completed}/{len(aroll_segments)} completed")
    with col2:
        st.info(f"B-Roll Segments: {broll_completed}/{len(broll_segments)} completed")
    
    # Display assembly sequence
    st.subheader("Assembly Sequence")
    
    # Add a toggle for manual sequence editing
    enable_manual_editing = st.toggle("Enable Manual Sequence Editor", 
                                     value=st.session_state.get("enable_manual_editing", False),
                                     key="enable_manual_editing_toggle")
    st.session_state.enable_manual_editing = enable_manual_editing
    
    # Create assembly sequence if not already created
    if "sequence" not in st.session_state.video_assembly or not st.session_state.video_assembly["sequence"]:
        sequence_result = create_assembly_sequence()
        if sequence_result["status"] == "success":
            st.session_state.video_assembly["sequence"] = sequence_result["sequence"]
        else:
            st.error(sequence_result["message"])
            st.stop()
    
    # If sequence exists but doesn't match the current selection, regenerate it
    # Only if manual editing is not enabled
    if not enable_manual_editing:
        selected_sequence = st.session_state.get("selected_sequence", "")
        if selected_sequence != st.session_state.video_assembly.get("selected_sequence", ""):
            sequence_result = create_assembly_sequence()
            if sequence_result["status"] == "success":
                st.session_state.video_assembly["sequence"] = sequence_result["sequence"]
                st.session_state.video_assembly["selected_sequence"] = selected_sequence
            else:
                st.error(sequence_result["message"])
                st.stop()
    
    # Manual sequence editor
    if enable_manual_editing:
        st.markdown("### Manual Sequence Editor")
        st.markdown("Arrange your segments by dragging and dropping them in the desired order. "
                    "The audio from A-Roll segments will be preserved regardless of visual placement.")
        
        # Initialize available segments data if not already available
        if "available_segments" not in st.session_state:
            # Load content status
            content_status = load_content_status()
            if not content_status:
                st.error("Could not load content status. Please complete the Content Production step first.")
                st.stop()
                
            aroll_segments = content_status.get("aroll", {})
            broll_segments = content_status.get("broll", {})
            
            if not aroll_segments:
                st.error("No A-Roll segments found. Please complete the Content Production step first.")
                st.stop()
            
            # Create lists of available segments
            aroll_items = []
            for segment_id, segment_data in aroll_segments.items():
                segment_num = int(segment_id.split("_")[-1])
                filepath, success, error = get_aroll_filepath(segment_id, segment_data)
                if filepath:
                    aroll_items.append({
                        "segment_id": segment_id,
                        "segment_num": segment_num,
                        "filepath": filepath,
                        "type": "aroll"
                    })
            
            broll_items = []
            for segment_id, segment_data in broll_segments.items():
                segment_num = int(segment_id.split("_")[-1])
                filepath = get_broll_filepath(segment_id, segment_data)
                if filepath:
                    broll_items.append({
                        "segment_id": segment_id,
                        "segment_num": segment_num,
                        "filepath": filepath,
                        "type": "broll"
                    })
            
            # Sort by segment number
            aroll_items.sort(key=lambda x: x["segment_num"])
            broll_items.sort(key=lambda x: x["segment_num"])
            
            if not aroll_items:
                st.error("No valid A-Roll files found. Please check A-Roll Transcription status.")
                st.stop()
                
            st.session_state.available_segments = {
                "aroll": aroll_items,
                "broll": broll_items
            }
        
        # Helpful instruction message when first using the editor
        if st.session_state.get("first_time_manual_edit", True):
            st.info("""
            **How to use the manual editor:**
            1. Add segments using the buttons on the left panel
            2. Rearrange them using the arrows
            3. Click 'Apply Manual Sequence' when done
            
            You can create any combination of A-Roll videos and B-Roll videos with A-Roll audio.
            """)
            st.session_state.first_time_manual_edit = False
        
        # If we don't have a manual sequence yet, initialize it based on the current sequence
        if "manual_sequence" not in st.session_state:
            st.session_state.manual_sequence = []
            # Get the current sequence - either from session state or generate a new one
            if ("sequence" in st.session_state.video_assembly and 
                st.session_state.video_assembly["sequence"]):
                sequence = st.session_state.video_assembly["sequence"]
            else:
                # Generate a default sequence
                sequence_result = create_assembly_sequence()
                if sequence_result["status"] == "success":
                    sequence = sequence_result["sequence"]
                    st.session_state.video_assembly["sequence"] = sequence
                else:
                    # Handle error by showing a message and providing an empty sequence
                    st.error(f"Could not generate initial sequence: {sequence_result.get('message', 'Unknown error')}")
                    st.info("Please add segments manually using the controls below.")
                    sequence = []
            
            # Populate manual sequence from the sequence
            for item in sequence:
                if item["type"] == "aroll_full":
                    segment_id = item["segment_id"]
                    segment_num = int(segment_id.split("_")[-1])
                    st.session_state.manual_sequence.append({
                        "type": "aroll_full",
                        "aroll_segment_id": segment_id,
                        "aroll_segment_num": segment_num,
                        "aroll_path": item["aroll_path"]
                    })
                elif item["type"] == "broll_with_aroll_audio":
                    aroll_segment_id = item["segment_id"]
                    broll_segment_id = item["broll_id"]
                    aroll_segment_num = int(aroll_segment_id.split("_")[-1])
                    broll_segment_num = int(broll_segment_id.split("_")[-1])
                    st.session_state.manual_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_segment_id": aroll_segment_id,
                        "broll_segment_id": broll_segment_id,
                        "aroll_segment_num": aroll_segment_num,
                        "broll_segment_num": broll_segment_num,
                        "aroll_path": item["aroll_path"],
                        "broll_path": item["broll_path"]
                    })
        
        # Create two columns: one for available segments, one for sequence
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("#### Available Segments")
            
            # A-Roll segments
            st.markdown("**A-Roll Segments**")
            for item in st.session_state.available_segments["aroll"]:
                segment_num = item["segment_num"]
                segment_id = item["segment_id"]
                
                # Create buttons for adding segments
                if st.button(f"Add A-Roll {segment_num + 1}", key=f"add_aroll_{segment_num}"):
                    # Find the corresponding aroll item
                    aroll_path = item["filepath"]
                    
                    # Add to manual sequence
                    st.session_state.manual_sequence.append({
                        "type": "aroll_full",
                        "aroll_segment_id": segment_id,
                        "aroll_segment_num": segment_num,
                        "aroll_path": aroll_path
                    })
                    st.rerun()
            
            # B-Roll segments with A-Roll audio selection
            st.markdown("**B-Roll Segments**")
            for b_item in st.session_state.available_segments["broll"]:
                b_segment_num = b_item["segment_num"]
                b_segment_id = b_item["segment_id"]
                b_filepath = b_item["filepath"]
                
                # Add selection for which A-Roll audio to use
                aroll_options = [f"A-Roll {a['segment_num'] + 1}" for a in st.session_state.available_segments["aroll"]]
                selected_aroll = st.selectbox(
                    f"Audio for B-Roll {b_segment_num + 1}:",
                    aroll_options,
                    key=f"aroll_select_{b_segment_num}"
                )
                
                # Get the selected A-Roll index
                selected_aroll_num = int(selected_aroll.split(" ")[-1]) - 1
                
                # Find corresponding A-Roll
                aroll_item = next((a for a in st.session_state.available_segments["aroll"] 
                                  if a["segment_num"] == selected_aroll_num), None)
                
                if aroll_item:
                    a_segment_id = aroll_item["segment_id"]
                    a_segment_num = aroll_item["segment_num"]
                    a_filepath = aroll_item["filepath"]
                    
                    # Button to add B-Roll with A-Roll audio
                    if st.button(f"Add B-Roll {b_segment_num + 1}", key=f"add_broll_{b_segment_num}"):
                        st.session_state.manual_sequence.append({
                            "type": "broll_with_aroll_audio",
                            "aroll_segment_id": a_segment_id,
                            "broll_segment_id": b_segment_id,
                            "aroll_segment_num": a_segment_num,
                            "broll_segment_num": b_segment_num,
                            "aroll_path": a_filepath,
                            "broll_path": b_filepath
                        })
                        st.rerun()
        
        with col2:
            st.markdown("#### Current Sequence")
            st.markdown("Drag and drop segments to rearrange. The final video will follow this order.")
            
            # Display the current manual sequence
            if st.session_state.manual_sequence:
                # Track audio segments to detect duplicates
                used_audio_segments = {}
                has_audio_overlaps = False
                
                # Use columns to create a row for each segment with buttons
                for i, item in enumerate(st.session_state.manual_sequence):
                    cols = st.columns([3, 1, 1, 1])
                    
                    # Check if this is an audio overlap
                    is_overlap = False
                    segment_id = None
                    
                    if item["type"] == "aroll_full":
                        segment_id = item["aroll_segment_id"]
                    else:  # broll_with_aroll_audio
                        segment_id = item["aroll_segment_id"]
                        
                    if segment_id in used_audio_segments:
                        is_overlap = True
                        has_audio_overlaps = True
                    else:
                        used_audio_segments[segment_id] = i
                    
                    # Display segment info with warning if it's an overlap
                    if item["type"] == "aroll_full":
                        segment_num = item["aroll_segment_num"]
                        
                        # Add warning color if this is an overlap
                        border_color = "#FF5733" if is_overlap else "#4CAF50"
                        bg_color = "#FFEBEE" if is_overlap else "#E8F5E9"
                        warning_text = "<br><small>⚠️ <strong>DUPLICATE AUDIO</strong></small>" if is_overlap else ""
                        
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid {border_color}; padding:8px; border-radius:5px; background-color:{bg_color};">
                            <strong>A-Roll {segment_num + 1}</strong><br>
                            <small>Full A-Roll segment{warning_text}</small>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:  # broll_with_aroll_audio
                        a_segment_num = item["aroll_segment_num"]
                        b_segment_num = item["broll_segment_num"]
                        
                        # Add warning color if this is an overlap
                        border_color = "#FF5733" if is_overlap else "#2196F3"
                        bg_color = "#FFEBEE" if is_overlap else "#E3F2FD"
                        warning_text = "<br><small>⚠️ <strong>DUPLICATE AUDIO</strong></small>" if is_overlap else ""
                        
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid {border_color}; padding:8px; border-radius:5px; background-color:{bg_color};">
                            <strong>B-Roll {b_segment_num + 1} + A-Roll {a_segment_num + 1} Audio</strong><br>
                            <small>B-Roll visuals with A-Roll audio{warning_text}</small>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    
                    # Move up button (except for first segment)
                    if i > 0:
                        if cols[1].button("↑", key=f"move_up_{i}"):
                            # Swap with previous segment
                            st.session_state.manual_sequence[i], st.session_state.manual_sequence[i-1] = \
                                st.session_state.manual_sequence[i-1], st.session_state.manual_sequence[i]
                            st.rerun()
                    
                    # Move down button (except for last segment)
                    if i < len(st.session_state.manual_sequence) - 1:
                        if cols[2].button("↓", key=f"move_down_{i}"):
                            # Swap with next segment
                            st.session_state.manual_sequence[i], st.session_state.manual_sequence[i+1] = \
                                st.session_state.manual_sequence[i+1], st.session_state.manual_sequence[i]
                            st.rerun()
                    
                    # Remove button
                    if cols[3].button("✖", key=f"remove_{i}"):
                        # Remove this segment
                        st.session_state.manual_sequence.pop(i)
                        st.rerun()
                
                # Show audio flow visualization if we have at least two segments
                if len(st.session_state.manual_sequence) >= 2:
                    st.markdown("### 🔊 Audio Flow Visualization")
                    st.markdown("This shows how audio flows through your sequence:")
                    
                    # Create a visual representation of the audio flow
                    audio_flow = ""
                    for i, item in enumerate(st.session_state.manual_sequence):
                        if item["type"] == "aroll_full":
                            segment_num = item["aroll_segment_num"]
                            segment_id = item["aroll_segment_id"]
                            
                            # Check if this is an audio overlap
                            if segment_id in used_audio_segments and used_audio_segments[segment_id] != i:
                                audio_flow += f"**[A-{segment_num+1}]** ⚠️ → "
                            else:
                                audio_flow += f"**[A-{segment_num+1}]** → "
                        else:  # broll_with_aroll_audio
                            a_segment_num = item["aroll_segment_num"]
                            segment_id = item["aroll_segment_id"]
                            
                            # Check if this is an audio overlap
                            if segment_id in used_audio_segments and used_audio_segments[segment_id] != i:
                                audio_flow += f"**[A-{a_segment_num+1}]** ⚠️ → "
                            else:
                                audio_flow += f"**[A-{a_segment_num+1}]** → "
                    
                    # Remove the last arrow
                    audio_flow = audio_flow[:-4]
                    
                    # Display the audio flow
                    st.markdown(audio_flow)
                    
                    # Show warning if there are audio overlaps
                    if has_audio_overlaps:
                        st.warning("⚠️ Your sequence contains duplicate audio segments that may cause audio overlaps. Items marked with ⚠️ use audio that appears earlier in the sequence.")
                
                # Button to clear the sequence
                if st.button("Clear Sequence", key="clear_sequence"):
                    st.session_state.manual_sequence = []
                    st.rerun()
                
                # Button to update the assembly sequence with the manual sequence
                if st.button("Apply Manual Sequence", key="apply_manual", type="primary"):
                    # Check if we have any segments in the manual sequence
                    if not st.session_state.manual_sequence:
                        st.error("Cannot apply an empty sequence. Please add at least one segment first.")
                        st.stop()
                        
                    # Convert manual sequence to assembly sequence format
                    assembly_sequence = []
                    
                    for item in st.session_state.manual_sequence:
                        if item["type"] == "aroll_full":
                            assembly_sequence.append({
                                "type": "aroll_full",
                                "aroll_path": item["aroll_path"],
                                "broll_path": None,
                                "segment_id": item["aroll_segment_id"]
                            })
                        else:  # broll_with_aroll_audio
                            assembly_sequence.append({
                                "type": "broll_with_aroll_audio",
                                "aroll_path": item["aroll_path"],
                                "broll_path": item["broll_path"],
                                "segment_id": item["aroll_segment_id"],
                                "broll_id": item["broll_segment_id"]
                            })
                    
                    # Update the sequence
                    st.session_state.video_assembly["sequence"] = assembly_sequence
                    st.session_state.video_assembly["selected_sequence"] = "Custom (Manual Arrangement)"
                    
                    # Success message
                    st.success("Manual sequence applied!")
                    
                    # Make sure the sequence is immediately available for assembly
                    if assembly_sequence:
                        # Verify all paths exist
                        missing_files = []
                        for seq_item in assembly_sequence:
                            if "aroll_path" in seq_item and not os.path.exists(seq_item["aroll_path"]):
                                missing_files.append(f"A-Roll file not found: {seq_item['aroll_path']}")
                            if "broll_path" in seq_item and seq_item["broll_path"] and not os.path.exists(seq_item["broll_path"]):
                                missing_files.append(f"B-Roll file not found: {seq_item['broll_path']}")
                        
                        if missing_files:
                            st.error("Missing files in sequence:")
                            for msg in missing_files:
                                st.warning(msg)
                        else:
                            st.success("All files in sequence are valid!")
                    
                    st.rerun()
            else:
                st.info("No segments in the sequence yet. Add segments from the left panel.")
    
    # Display sequence preview
    st.markdown("The video will be assembled in the following sequence:")
    
    # Check if we have a valid sequence to display
    if not st.session_state.video_assembly.get("sequence"):
        st.warning("No sequence defined yet. Please select a sequence pattern or create a custom arrangement.")
    else:
        # Use cols to create a sequence preview
        cols = st.columns(min(8, len(st.session_state.video_assembly["sequence"])))
        
        # Create visual sequence preview with simple boxes
        for i, (item, col) in enumerate(zip(st.session_state.video_assembly["sequence"], cols)):
            segment_type = item["type"]
            segment_id = item.get("segment_id", "").split("_")[-1]  # Extract segment number
            
            if segment_type == "aroll_full":
                col.markdown(
                    f"""
                    <div style="text-align:center; border:2px solid #4CAF50; padding:8px; border-radius:5px; background-color:#E8F5E9;">
                    <strong>A-{int(segment_id) + 1}</strong><br>
                    <small>A-Roll video<br>A-Roll audio</small>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            elif segment_type == "broll_with_aroll_audio":
                broll_id = item.get("broll_id", "").split("_")[-1]
                col.markdown(
                    f"""
                    <div style="text-align:center; border:2px solid #2196F3; padding:8px; border-radius:5px; background-color:#E3F2FD;">
                    <strong>B-{int(broll_id) + 1} + A-{int(segment_id) + 1}</strong><br>
                    <small>B-Roll video<br>A-Roll audio</small>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        
        # Full text description of sequence
        st.markdown("#### Detailed Sequence:")
        for i, item in enumerate(st.session_state.video_assembly["sequence"]):
            if item["type"] == "aroll_full":
                segment_num = item['segment_id'].split('_')[-1]
                st.markdown(f"**{i+1}.** A-Roll Segment {int(segment_num) + 1} (full video and audio)")
            elif item["type"] == "broll_with_aroll_audio":
                broll_num = item['broll_id'].split('_')[-1]
                segment_num = item['segment_id'].split('_')[-1]
                st.markdown(f"**{i+1}.** B-Roll Segment {int(broll_num) + 1} visuals + A-Roll Segment {int(segment_num) + 1} audio")
    
    # Show timeline visualization
    st.markdown("#### Timeline Visualization:")
    
    # Generate timeline visualization
    timeline_img = render_sequence_timeline(st.session_state.video_assembly["sequence"])
    
    if timeline_img:
        st.markdown(f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{timeline_img}" style="max-width: 100%; height: auto;">
            </div>
            <p style="text-align: center; font-size: 0.8em; color: #666;">
                Timeline showing video and audio tracks. Green = A-Roll video, Blue = B-Roll video, Orange = A-Roll audio.
            </p>
        """, unsafe_allow_html=True)
        
        # Add note about potential audio overlaps
        st.markdown("""
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <p style="margin: 0; font-size: 0.9em;">
                    <strong>Note:</strong> If you notice audio overlaps or issues in the final video, try adjusting the sequence 
                    to ensure each A-Roll audio segment is used only once, or use the Custom Arrangement for more control.
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Generate a sequence to view the timeline visualization.")

    # Assembly options
    st.subheader("Assembly Options")
    resolution_options = ["1080x1920 (9:16)", "720x1280 (9:16)", "1920x1080 (16:9)"]
    st.session_state.selected_resolution = st.selectbox(
        "Output Resolution:", 
        resolution_options,
        index=resolution_options.index(st.session_state.get("selected_resolution", "1080x1920 (9:16)")),
        key="resolution_selectbox_secondary"
    )

    # Add a dependency check option
    if st.button("Check Dependencies", type="secondary", help="Check if all required packages are installed", key="check_deps_secondary"):
        with st.spinner("Checking dependencies..."):
            try:
                subprocess.run([sys.executable, "utils/video/dependencies.py"], check=True)
                st.success("All dependencies are installed!")
            except Exception as e:
                st.error(f"Error checking dependencies: {str(e)}")
                st.info("Please run `python utils/video/dependencies.py` manually to install required packages")

# Add call to apply default B-roll IDs in the initialization section
# ... existing code ...
# Initialize content status
if "content_status" not in st.session_state:
    content_status = load_content_status()
    if content_status:
        st.session_state.content_status = content_status
        
        # Apply default B-roll IDs to content status
        if apply_default_broll_ids(st.session_state.content_status):
            save_content_status()  # Save if changes were made
            
        # Update session state with default B-roll IDs
        update_session_state_with_defaults(st.session_state)
    else:
        st.session_state.content_status = {"aroll": {}, "broll": {}}

# Add step navigation
st.markdown("---")
render_step_navigation(
    current_step=7,
    prev_step_path="pages/5B_BRoll_Video_Production.py",
    next_step_path="pages/7_Caption_The_Dreams.py"
)

# After the content summary section
# Add debugging information
with st.expander("Debug Information", expanded=False):
    st.subheader("A-Roll Segments Debug Info")
    st.write("This information can help diagnose issues with segment paths and identification")
    
    # Debug A-Roll segments from script.json
    st.markdown("### A-Roll Segments from Script")
    segment_count = len(aroll_segments)
    st.info(f"Total A-Roll segments in script: {segment_count}")
    
    for i, segment in enumerate(aroll_segments):
        segment_id = segment.get("segment_id", f"segment_{i}")
        file_path = segment.get("file_path", "Not found")
        exists = "✅" if file_path != "Not found" and os.path.exists(file_path) else "❌"
        start_time = segment.get("start_time", "Not set")
        end_time = segment.get("end_time", "Not set")
        
        # Show detailed information
        st.markdown(f"**Segment {i}:** ID=`{segment_id}`")
        st.markdown(f"&nbsp;&nbsp;Path=`{file_path}` {exists}")
        st.markdown(f"&nbsp;&nbsp;Timing: {start_time}s to {end_time}s")
        
        # Try to find the file using get_aroll_filepath
        resolved_path, success, error = get_aroll_filepath(segment_id, segment)
        resolution_status = "✅ Found" if success else "❌ Not found"
        st.markdown(f"&nbsp;&nbsp;Path Resolution: {resolution_status}")
        st.markdown(f"&nbsp;&nbsp;Resolved Path: `{resolved_path}`")
        if error:
            st.error(f"&nbsp;&nbsp;Error: {error}")
    
    # Debug content status
    st.markdown("### Content Status")
    st.info(f"Total A-Roll segments in content_status: {len(content_status['aroll'])}")
    
    for segment_id, segment_data in content_status["aroll"].items():
        local_path = segment_data.get("local_path", "Not found")
        exists = "✅" if local_path != "Not found" and os.path.exists(local_path) else "❌"
        st.markdown(f"**{segment_id}:** Local Path=`{local_path}` {exists}")
        st.markdown(f"&nbsp;&nbsp;Status=`{segment_data.get('status', 'Unknown')}`")
        
        # Check if any video_url exists
        if "video_url" in segment_data:
            st.markdown(f"&nbsp;&nbsp;Video URL: `{segment_data['video_url']}`")
    
    # Debug file search results
    st.markdown("### File Path Search Results")
    for i, segment in enumerate(aroll_segments):
        segment_id = segment.get("segment_id", f"segment_{i}")
        
        # Try to find the file using get_aroll_filepath
        test_path, success, error = get_aroll_filepath(segment_id, segment)
        
        status = "✅ Found" if success else "❌ Not found"
        file_exists = os.path.exists(test_path) if test_path else False
        file_status = "✅ File exists" if file_exists else "❌ File missing"
        
        st.markdown(f"**Search for {segment_id}:** {status}, {file_status}")
        st.markdown(f"&nbsp;&nbsp;Path=`{test_path}`")
        if error:
            st.error(f"&nbsp;&nbsp;Error: {error}")
            
    # List available files in media directory
    media_dir = os.path.join(project_path, "media", "a-roll")
    segments_dir = os.path.join(project_path, "media", "a-roll", "segments")
    
    st.markdown("### Available Files in A-Roll Directory")
    
    # Function to list files in directory
    def list_files_in_dir(directory, prefix=""):
        if os.path.exists(directory):
            files = os.listdir(directory)
            for file in files:
                if file.endswith('.mp4'):
                    full_path = os.path.join(directory, file)
                    exists = "✅" if os.path.exists(full_path) else "❌"
                    st.markdown(f"- {prefix}`{file}` {exists}")
        else:
            st.warning(f"Directory not found: {directory}")
    
    # List files in main directory
    list_files_in_dir(media_dir, "Main: ")
    
    # List files in segments directory
    if os.path.exists(segments_dir):
        list_files_in_dir(segments_dir, "Segments: ")
    
    # Show the complete segment count information
    st.markdown("### Segment Count Summary")
    st.markdown(f"- Script segments: {len(aroll_segments)}")
    st.markdown(f"- Content status entries: {len(content_status['aroll'])}")
    st.markdown(f"- Completed segments: {aroll_completed}/{len(aroll_segments)}")
    
    # Show paths being checked
    st.markdown("### Path Information")
    st.markdown(f"- Project path: `{project_path}`")
    st.markdown(f"- Media path: `{media_dir}`")
    st.markdown(f"- Segments path: `{segments_dir}`")