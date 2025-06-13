import streamlit as st

# Set page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="Video Assembly | AI Money Printer",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

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

# Get project path once at the beginning to ensure it's available throughout the file
project_path = get_project_path()

# Rest of the imports
import json
from pathlib import Path
import subprocess

# Add utils.video.broll_defaults import
from utils.video.broll_defaults import apply_default_broll_ids, update_session_state_with_defaults

# Add missing functions
def load_segments():
    """Load segments from script.json"""
    project_path = get_project_path()
    script_file = project_path / "script.json"
    if not script_file.exists():
        st.warning(f"Script file not found: {script_file}")
        return []
    
    try:
        with open(script_file, "r") as f:
            data = json.load(f)
            
            # Get segments from the new format (version 2.0+)
            segments = data.get("segments", [])
            
            # Log segment information
            aroll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll")
            broll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll")
            print(f"Loaded {len(segments)} total segments: {aroll_count} A-Roll and {broll_count} B-Roll segments")
            
            # Check if we have the new broll_percentage field
            if "broll_percentage" in data:
                st.session_state.broll_percentage = data.get("broll_percentage")
                print(f"Loaded B-Roll density percentage: {st.session_state.broll_percentage}%")
            
            return segments
    except Exception as e:
        st.warning(f"Error loading script: {str(e)}")
        return []

def load_content_status():
    """Load content status from content_status.json"""
    project_path = get_project_path()
    status_file = project_path / "content_status.json"
    if not status_file.exists():
        st.warning(f"Content status file not found: {status_file}")
        return {}
    
    try:
        with open(status_file, "r") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Error loading content status: {str(e)}")
        return {}

def get_aroll_filepath(segment_id, segment_data):
    """Get A-Roll filepath for a segment"""
    project_path = get_project_path()
    
    # First check if the segment has a file_path property from the new transcription workflow
    if "file_path" in segment_data:
        file_path = segment_data["file_path"]
        # Check if it's a relative path and make it absolute
        if not os.path.isabs(file_path):
            file_path = os.path.join(project_path, file_path)
            
        if os.path.exists(file_path):
            print(f"Segment {segment_id} found via direct file_path: {file_path}")
            return file_path, True, None
    
    # Check for segment-specific A-Roll in the new location (from A-roll Transcription page)
    segment_num = segment_id.split('_')[-1] if '_' in segment_id else segment_id
    possible_paths = [
        # New paths from A-Roll Transcription page
        project_path / "media" / "a-roll" / "segments" / f"segment_{segment_num}.mp4",
        project_path / "media" / "a-roll" / "segments" / f"main_aroll_segment_{segment_num}.mp4",
        
        # Legacy paths
        project_path / "aroll" / f"{segment_id}.mp4",
        project_path / "media" / "aroll" / f"{segment_id}.mp4",
        project_path / "media" / "a-roll" / f"{segment_id}.mp4"
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"Segment {segment_id} found via path resolution: {path}")
            return str(path), True, None
    
    # If segment has start_time and end_time defined, try to use the main A-roll video
    if "start_time" in segment_data and "end_time" in segment_data:
        # Look for the full A-Roll video
        full_aroll_paths = [
            project_path / "media" / "a-roll" / "main_aroll.mp4",
            project_path / "aroll_video.mp4",
            project_path / "media" / "aroll" / "main_aroll.mp4"
        ]
        for path in full_aroll_paths:
            if path.exists():
                print(f"Segment {segment_id} will use main A-Roll with timestamps: {path}")
                return str(path), True, None
    
    # Check for other video formats
    for ext in [".mov", ".avi", ".webm"]:
        alt_paths = [
            project_path / "media" / "a-roll" / "segments" / f"segment_{segment_num}{ext}",
            project_path / "aroll" / f"{segment_id}{ext}",
            project_path / "media" / "aroll" / f"{segment_id}{ext}",
            project_path / "media" / "a-roll" / f"{segment_id}{ext}"
        ]
        for path in alt_paths:
            if path.exists():
                print(f"Segment {segment_id} found via alternate format: {path}")
                return str(path), True, None
    
    # A-Roll not found
    print(f"A-Roll file not found for segment {segment_id}")
    return None, False, f"A-Roll file not found for {segment_id}"

def get_broll_filepath(segment_id, segment_data):
    """Get B-Roll filepath for a segment"""
    project_path = get_project_path()
    
    # First check if the segment has a file_path property from the new transcription workflow
    if "file_path" in segment_data:
        file_path = segment_data["file_path"]
        # Check if it's a relative path and make it absolute
        if not os.path.isabs(file_path):
            file_path = os.path.join(project_path, file_path)
            
        if os.path.exists(file_path):
            print(f"B-Roll {segment_id} found via direct file_path: {file_path}")
            return file_path
    
    # Get segment number in case the ID format is different
    segment_num = segment_id.split('_')[-1] if '_' in segment_id else segment_id
    
    # Check for segment-specific B-Roll in various locations
    possible_paths = [
        # New paths from A-Roll Transcription page
        project_path / "media" / "b-roll" / f"segment_{segment_num}.mp4",
        project_path / "media" / "b-roll" / f"broll_segment_{segment_num}.mp4",
        
        # Legacy paths
        project_path / "broll" / f"{segment_id}.mp4",
        project_path / "media" / "broll" / f"{segment_id}.mp4"
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"B-Roll {segment_id} found via path resolution: {path}")
            return str(path)
    
    # Check for image files (for static B-Roll)
    for ext in [".png", ".jpg", ".jpeg"]:
        img_paths = [
            project_path / "media" / "b-roll" / f"segment_{segment_num}{ext}",
            project_path / "media" / "b-roll" / f"broll_segment_{segment_num}{ext}",
            project_path / "broll" / f"{segment_id}{ext}"
        ]
        for path in img_paths:
            if path.exists():
                print(f"B-Roll image {segment_id} found: {path}")
                return str(path)
    
    # Check for other video formats
    for ext in [".mov", ".avi", ".webm"]:
        alt_paths = [
            project_path / "media" / "b-roll" / f"segment_{segment_num}{ext}",
            project_path / "media" / "b-roll" / f"broll_segment_{segment_num}{ext}",
            project_path / "broll" / f"{segment_id}{ext}"
        ]
        for path in alt_paths:
            if path.exists():
                print(f"B-Roll {segment_id} found via alternate format: {path}")
                return str(path)
    
    # B-Roll not found
    print(f"B-Roll file not found for segment {segment_id}")
    return None

# Create assembly sequence
def create_assembly_sequence():
    """
    Create a sequence of video segments for assembly
    
    Returns:
        dict: Result with status and sequence
    """
    project_path = get_project_path()
    
    # Load content status and segments
    script_segments = load_segments()
    
    if not script_segments:
        return {"status": "error", "message": "No segments found. Please complete the A-Roll Transcription step first."}
    
    # Get the B-Roll density percentage from session state
    broll_percentage = st.session_state.get("broll_percentage", 25)  # Default to 25% if not set
    print(f"Using B-Roll density percentage: {broll_percentage}%")
    
    # Separate A-Roll and B-Roll segments
    aroll_segments = [s for s in script_segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    broll_segments = [s for s in script_segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    
    if not aroll_segments:
        return {"status": "error", "message": "No A-Roll segments found in script."}
    
    print(f"Found {len(aroll_segments)} A-Roll segments and {len(broll_segments)} B-Roll segments")
    
    # Assembly sequence
    assembly_sequence = []
    
    # Determine how many A-Roll segments should have B-Roll overlaid based on percentage
    # Always keep first and last segments as pure A-Roll
    if len(aroll_segments) <= 2:
        # If we only have 1-2 A-Roll segments, don't add any B-Roll
        broll_count = 0
    else:
        # Calculate how many segments should have B-Roll based on percentage
        # Exclude first and last segments from the calculation
        middle_segments = len(aroll_segments) - 2
        broll_count = int(round(middle_segments * (broll_percentage / 100.0)))
        broll_count = min(broll_count, len(broll_segments))  # Can't use more B-Roll than we have
        broll_count = min(broll_count, middle_segments)      # Can't use more B-Roll than middle segments
    
    print(f"Will use {broll_count} B-Roll segments based on {broll_percentage}% density")
    
    # Create an assembly sequence ensuring first and last segments are A-Roll
    # First segment is always A-Roll
    first_segment = aroll_segments[0]
    segment_id = first_segment.get("id", first_segment.get("segment_id", "segment_0"))
    aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, first_segment)
    
    if aroll_path:
        assembly_sequence.append({
            "type": "aroll_full",
            "segment_id": segment_id,
            "aroll_path": aroll_path,
            "start_time": first_segment.get("start_time", 0),
            "end_time": first_segment.get("end_time", 0),
            "duration": first_segment.get("duration", 0),
            "content": first_segment.get("content", "")
        })
        print(f"Added first segment {segment_id} as A-Roll")
    
    # If we have B-Roll to use, distribute it across the middle segments
    if broll_count > 0 and len(aroll_segments) > 2:
        # Determine which middle segments should have B-Roll
        middle_aroll = aroll_segments[1:-1]  # Exclude first and last
        
        # If we have fewer B-Roll segments than the calculated count,
        # we'll distribute them evenly
        if broll_count < len(middle_aroll):
            # Calculate spacing to distribute B-Roll evenly
            step = len(middle_aroll) / broll_count
            broll_indices = [int(i * step) for i in range(broll_count)]
        else:
            # Use B-Roll for all middle segments
            broll_indices = list(range(len(middle_aroll)))
        
        # Process middle segments
        for i, segment in enumerate(middle_aroll):
            segment_id = segment.get("id", segment.get("segment_id", f"segment_{i+1}"))
            aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment)
            
            if not aroll_path:
                continue
            
            # Determine if this segment should have B-Roll
            if i in broll_indices and len(broll_segments) > 0:
                # Get the corresponding B-Roll segment
                broll_idx = broll_indices.index(i) % len(broll_segments)
                broll_segment = broll_segments[broll_idx]
                broll_id = broll_segment.get("id", broll_segment.get("segment_id", f"broll_{broll_idx}"))
                broll_path = get_broll_filepath(broll_id, broll_segment)
                
                if broll_path:
                    # Add B-Roll with A-Roll audio
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "segment_id": segment_id,
                        "broll_id": broll_id,
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "start_time": segment.get("start_time", 0),
                        "end_time": segment.get("end_time", 0),
                        "duration": segment.get("duration", 0),
                        "content": segment.get("content", "")
                    })
                    print(f"Added middle segment {segment_id} with B-Roll {broll_id}")
                else:
                    # Fall back to A-Roll if B-Roll path not found
                    assembly_sequence.append({
                        "type": "aroll_full",
                        "segment_id": segment_id,
                        "aroll_path": aroll_path,
                        "start_time": segment.get("start_time", 0),
                        "end_time": segment.get("end_time", 0),
                        "duration": segment.get("duration", 0),
                        "content": segment.get("content", "")
                    })
                    print(f"Added middle segment {segment_id} as A-Roll (B-Roll not found)")
            else:
                # Add as regular A-Roll
                assembly_sequence.append({
                    "type": "aroll_full",
                    "segment_id": segment_id,
                    "aroll_path": aroll_path,
                    "start_time": segment.get("start_time", 0),
                    "end_time": segment.get("end_time", 0),
                    "duration": segment.get("duration", 0),
                    "content": segment.get("content", "")
                })
                print(f"Added middle segment {segment_id} as A-Roll")
    else:
        # If we're not using B-Roll or have <= 2 segments, add remaining A-Roll segments (excluding last)
        for i, segment in enumerate(aroll_segments[1:-1] if len(aroll_segments) > 1 else []):
            segment_id = segment.get("id", segment.get("segment_id", f"segment_{i+1}"))
            aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment)
            
            if aroll_path:
                assembly_sequence.append({
                    "type": "aroll_full",
                    "segment_id": segment_id,
                    "aroll_path": aroll_path,
                    "start_time": segment.get("start_time", 0),
                    "end_time": segment.get("end_time", 0),
                    "duration": segment.get("duration", 0),
                    "content": segment.get("content", "")
                })
                print(f"Added middle segment {segment_id} as A-Roll (no B-Roll used)")
    
    # Last segment is always A-Roll
    if len(aroll_segments) > 1:
        last_segment = aroll_segments[-1]
        segment_id = last_segment.get("id", last_segment.get("segment_id", f"segment_{len(aroll_segments)-1}"))
        aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, last_segment)
        
        if aroll_path:
            assembly_sequence.append({
                "type": "aroll_full",
                "segment_id": segment_id,
                "aroll_path": aroll_path,
                "start_time": last_segment.get("start_time", 0),
                "end_time": last_segment.get("end_time", 0),
                "duration": last_segment.get("duration", 0),
                "content": last_segment.get("content", "")
            })
            print(f"Added last segment {segment_id} as A-Roll")
    
    if not assembly_sequence:
        return {"status": "error", "message": "Could not create assembly sequence. No valid segments found."}
    
    print(f"Created assembly sequence with {len(assembly_sequence)} segments")
    return {"status": "success", "sequence": assembly_sequence}

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
render_step_header(4, "Video Assembly", 6)
st.title("🎬 Video Assembly")
st.markdown("""
Create your final video by assembling A-Roll and B-Roll segments.
This step will combine all the visual assets into a single, coherent video.
""")

# Initialize video_assembly if it doesn't exist
if "video_assembly" not in st.session_state:
    st.session_state.video_assembly = {"sequence": []}

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

# Initialize video_assembly if it doesn't exist
if "video_assembly" not in st.session_state:
    st.session_state.video_assembly = {"sequence": []}

if "content_status" not in st.session_state:
    content_status = load_content_status()

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
        # Get project path for directory matching
        project_path = get_project_path()
        
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
                        segment_id = item["aroll_segment_id"]
                        
                        # Add warning color if this is an overlap
                        border_color = "#FF5733" if is_overlap else "#2196F3"
                        bg_color = "#FFEBEE" if is_overlap else "#E3F2FD"
                        warning_text = "<br><small>⚠️ <strong>DUPLICATE AUDIO</strong></small>" if is_overlap else ""
                        
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid {border_color}; padding:8px; border-radius:5px; background-color:{bg_color};">
                            <strong>B-Roll {a_segment_num + 1} + A-Roll {segment_num + 1} Audio</strong><br>
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

    # Add assembly button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### Assemble Video")
        st.markdown("Click the button below to assemble your video with the selected options.")
    with col2:
        # Add assemble button with different styling
        if st.button("🎬 Assemble Video", type="primary", key="assemble_button", help="Start the assembly process"):
            with st.spinner("Assembling video..."):
                try:
                    # Get sequence and output resolution
                    sequence = st.session_state.video_assembly.get("sequence", [])
                    
                    if not sequence:
                        st.error("No sequence defined. Please select a sequence template or create a custom arrangement.")
                        st.stop()
                    
                    # Get resolution settings
                    resolution_str = st.session_state.selected_resolution
                    width, height = map(int, resolution_str.split(" ")[0].split("x"))
                    
                    # Create output directory
                    output_dir = os.path.join(project_path, "media", "output")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Call assembly function with output_dir
                    result = helper_assemble_video(
                        sequence=sequence,
                        target_resolution=(width, height),
                        output_dir=output_dir
                    )
                    
                    if result["status"] == "success":
                        # Store the output path in session state for the Caption Dreams page to access
                        st.session_state.video_assembly["output_path"] = result["output_path"]
                        
                        st.success(f"Video assembled successfully!")
                        st.video(result["output_path"])
                        st.markdown(f"Video saved to: `{result['output_path']}`")
                    else:
                        st.error(f"Error assembling video: {result['message']}")
                except Exception as e:
                    st.error(f"Error assembling video: {str(e)}")
                    st.error(traceback.format_exc())

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
# Get project path
project_path = get_project_path()

if "content_status" not in st.session_state:
    content_status = load_content_status()
    if content_status:
        st.session_state.content_status = content_status
        
        # Only apply default B-roll IDs if no B-roll segments exist
        # This ensures percentage-based B-roll settings are preserved
        if "broll" not in st.session_state.content_status or len(st.session_state.content_status["broll"]) == 0:
            print("No B-roll segments found, applying defaults")
            if apply_default_broll_ids(st.session_state.content_status):
                # Save if changes were made
                try:
                    broll_status_file = project_path / "content_status.json"
                    with open(broll_status_file, "w") as f:
                        json.dump(st.session_state.content_status, f, indent=2)
                    print("Saved content_status.json with default B-roll IDs")
                except Exception as e:
                    print(f"Error saving content_status.json: {str(e)}")
                
            # Update session state with default B-roll IDs
            update_session_state_with_defaults(st.session_state)
        else:
            print(f"Preserving existing {len(st.session_state.content_status['broll'])} B-roll segments")
    else:
        st.session_state.content_status = {"aroll": {}, "broll": {}}

# Add step navigation
st.markdown("---")
render_step_navigation(
    current_step=4,
    prev_step_path="pages/5B_BRoll_Video_Production.py",
    next_step_path="pages/7_Caption_The_Dreams.py"
)

# After the content summary section
# Add debugging information
with st.expander("Debug Information", expanded=False):
    st.subheader("A-Roll Segments Debug Info")
    st.write("This information can help diagnose issues with segment paths and identification")
    
    # Get project path
    project_path = get_project_path()
    
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