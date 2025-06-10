import streamlit as st
import os
import sys
import json
import time
import tempfile
from pathlib import Path
import numpy as np
import re

# Add the app directory to Python path for relative imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app"))

# Fix import paths for components and utilities
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"Added {parent_dir} to path")

# Try to import local modules
try:
    from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation
    from components.progress import render_step_header
    from utils.session_state import get_settings, get_project_path, mark_step_complete
    from utils.audio.transcription import (
        extract_audio, 
        transcribe_video, 
        get_available_engines,
        check_module_availability
    )
    # Import new utilities for Ollama integration and segmentation
    from utils.ai.ollama_client import OllamaClient
    from utils.video.segmentation import (
        get_segment_timestamps,
        cut_video_segments,
        save_segment_metadata,
        load_segment_metadata,
        preview_segment
    )
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Failed to import local modules: {str(e)}")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="A-Roll Transcription | AI Money Printer",
    page_icon="🎤",
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
    
    /* Styling for the transcription segments */
    .segment-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: #f9f9f9;
    }
    
    .segment-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .segment-content {
        padding: 10px;
        background-color: white;
        border-radius: 5px;
        border-left: 4px solid #4CAF50;
    }
    
    /* B-Roll specific styling */
    .broll-segment-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: #f0f8ff;  /* Light blue background */
    }
    
    .broll-segment-content {
        padding: 10px;
        background-color: white;
        border-radius: 5px;
        border-left: 4px solid #2196F3;  /* Blue left border */
    }
    
    .timestamp {
        color: #666;
        font-size: 0.8em;
    }
    
    .edit-button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
    }
    
    .edit-button:hover {
        background-color: #45a049;
    }
    
    /* Theme selection styling */
    .theme-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: #fff8e1;  /* Light yellow background */
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
</style>
""", unsafe_allow_html=True)

# Render navigation sidebar
render_custom_sidebar()

# Load settings
settings = get_settings()
project_path = get_project_path()

# Initialize session state variables
if "transcription_data" not in st.session_state:
    st.session_state.transcription_data = None
if "a_roll_segments" not in st.session_state:
    st.session_state.a_roll_segments = []
if "b_roll_segments" not in st.session_state:
    st.session_state.b_roll_segments = []
if "uploaded_video" not in st.session_state:
    st.session_state.uploaded_video = None
if "transcription_complete" not in st.session_state:
    st.session_state.transcription_complete = False
if "segmentation_complete" not in st.session_state:
    st.session_state.segmentation_complete = False
if "segment_edit_index" not in st.session_state:
    st.session_state.segment_edit_index = -1
if "script_theme" not in st.session_state:
    st.session_state.script_theme = ""
if "broll_generation_strategy" not in st.session_state:
    st.session_state.broll_generation_strategy = "balanced"
# Add new session state variable for B-roll percentage
if "broll_percentage" not in st.session_state:
    st.session_state.broll_percentage = 25  # Default to 25%
# Add new session state variables for Ollama and automatic segmentation
if "ollama_client" not in st.session_state:
    st.session_state.ollama_client = OllamaClient(host="http://100.115.243.42:11434")
if "auto_segmentation_complete" not in st.session_state:
    st.session_state.auto_segmentation_complete = False
if "segment_files" not in st.session_state:
    st.session_state.segment_files = []

# Function to save the transcription data
def save_transcription_data(data):
    transcription_file = project_path / "transcription.json"
    try:
        with open(transcription_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved transcription to {transcription_file}")
        return True
    except IOError as e:
        print(f"Error saving transcription: {str(e)}")
        return False

# Function to load transcription data if it exists
def load_transcription_data():
    transcription_file = project_path / "transcription.json"
    if transcription_file.exists():
        try:
            with open(transcription_file, "r") as f:
                data = json.load(f)
                st.session_state.transcription_data = data
                st.session_state.transcription_complete = True
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading transcription: {str(e)}")
            return None
    return None

# Function to save A-roll segments
def save_a_roll_segments(segments):
    """Save A-roll segments to script.json"""
    # If we have B-Roll segments, use the new save_segments function
    if "b_roll_segments" in st.session_state and st.session_state.b_roll_segments:
        return save_segments(
            segments,
            st.session_state.b_roll_segments,
            st.session_state.script_theme,
            st.session_state.broll_percentage
        )
    
    script_file = project_path / "script.json"
    
    # Check if script.json already exists and load it
    existing_data = {}
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading existing script: {str(e)}")
    
    # Create full script text from segments
    full_script = " ".join([segment["content"] for segment in segments])
    
    # Prepare data to save
    data = {
        "full_script": full_script,
        "segments": segments,
        "theme": existing_data.get("theme", st.session_state.script_theme),
        "source": "transcription",
        "timestamp": time.time()
    }
    
    # Preserve any other fields from existing data
    for key, value in existing_data.items():
        if key not in data:
            data[key] = value
    
    # Save to file
    try:
        with open(script_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved A-roll segments to {script_file}")
        return True
    except IOError as e:
        print(f"Error saving A-roll segments: {str(e)}")
        return False

# Function to load A-roll segments if they exist
def load_a_roll_segments():
    script_file = project_path / "script.json"
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                
                # Check if the script was created from transcription
                if data.get("source") == "transcription":
                    segments = data.get("segments", [])
                    if segments:
                        # Extract A-Roll and B-Roll segments
                        a_roll_segments = [s for s in segments if s.get("type") == "A-Roll"]
                        b_roll_segments = [s for s in segments if s.get("type") == "B-Roll"]
                        
                        # Ensure all segments have timing information
                        for i, segment in enumerate(a_roll_segments):
                            if "start_time" not in segment:
                                segment["start_time"] = i * 10  # Default 10 seconds per segment
                            if "end_time" not in segment:
                                segment["end_time"] = (i + 1) * 10
                            if "duration" not in segment:
                                segment["duration"] = segment["end_time"] - segment["start_time"]
                        
                        # Store in session state
                        st.session_state.a_roll_segments = a_roll_segments
                        st.session_state.b_roll_segments = b_roll_segments
                        st.session_state.segmentation_complete = True
                        
                        # Load theme
                        if "theme" in data:
                            st.session_state.script_theme = data["theme"]
                        
                        return a_roll_segments
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading A-roll segments: {str(e)}")
            return None
    return None

# Function to segment the transcription
def segment_transcription(transcription, min_segment_duration=5, max_segment_duration=20):
    """
    Segment the transcription into smaller parts.
    
    Args:
        transcription: The full transcription text
        min_segment_duration: Minimum segment duration in seconds
        max_segment_duration: Maximum segment duration in seconds
        
    Returns:
        List of segments with start and end times
    """
    if not transcription or "segments" not in transcription:
        # If no segments are available, create a single segment from the full text
        text = transcription.get("text", "")
        if not text:
            return []
        
        return [{
            "type": "A-Roll",
            "content": text,
            "start_time": 0,
            "end_time": 0,
            "duration": 0
        }]
    
    # Extract segments from the transcription
    segments = []
    current_segment = {
        "type": "A-Roll",
        "content": "",
        "start_time": 0,
        "end_time": 0,
        "duration": 0
    }
    
    for segment in transcription["segments"]:
        text = segment.get("text", "").strip()
        if not text:
            continue
        
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        duration = end - start
        
        # Check if we should start a new segment
        if current_segment["duration"] + duration > max_segment_duration:
            # Finalize the current segment
            if current_segment["content"]:
                segments.append(current_segment)
            
            # Start a new segment
            current_segment = {
                "type": "A-Roll",
                "content": text,
                "start_time": start,
                "end_time": end,
                "duration": duration
            }
        else:
            # Add to the current segment
            if current_segment["content"]:
                current_segment["content"] += " "
            current_segment["content"] += text
            current_segment["end_time"] = end
            current_segment["duration"] = end - current_segment["start_time"]
    
    # Add the last segment if it has content
    if current_segment["content"]:
        segments.append(current_segment)
    
    # Check if we have very short segments that should be combined
    if len(segments) > 1:
        i = 0
        while i < len(segments) - 1:
            if segments[i]["duration"] < min_segment_duration:
                # Combine with the next segment
                next_segment = segments[i + 1]
                segments[i]["content"] += " " + next_segment["content"]
                segments[i]["end_time"] = next_segment["end_time"]
                segments[i]["duration"] = segments[i]["end_time"] - segments[i]["start_time"]
                
                # Remove the next segment
                segments.pop(i + 1)
            else:
                i += 1
    
    return segments

# Function to update segment content
def update_segment_content(index, new_content):
    if 0 <= index < len(st.session_state.a_roll_segments):
        # Update content while preserving timing information
        segment = st.session_state.a_roll_segments[index]
        segment["content"] = new_content
        
        # Ensure timing information is preserved
        if "start_time" not in segment:
            segment["start_time"] = index * 10  # Default 10 seconds per segment
        if "end_time" not in segment:
            segment["end_time"] = (index + 1) * 10
        if "duration" not in segment:
            segment["duration"] = segment["end_time"] - segment["start_time"]
        
        return True
    return False

# Function to ensure all segments have timing information
def ensure_segments_have_timing(segments, video_duration=None):
    """
    Add default timing information to segments that don't have it.
    Scales segments to fit within the video duration if provided.
    
    Args:
        segments: List of segments to process
        video_duration: Optional actual duration of the video in seconds
        
    Returns:
        Segments with timing information added
    """
    # Skip if no segments
    if not segments:
        return segments
    
    # If video duration is not provided, use 10 seconds per segment as default
    if not video_duration:
        for i, segment in enumerate(segments):
            if "start_time" not in segment:
                segment["start_time"] = i * 10  # Default 10 seconds per segment
            if "end_time" not in segment:
                segment["end_time"] = (i + 1) * 10
            if "duration" not in segment:
                segment["duration"] = segment["end_time"] - segment["start_time"]
    else:
        # Calculate segment durations proportionally to fit within video_duration
        segment_count = len(segments)
        average_duration = video_duration / segment_count if segment_count > 0 else 0
        
        # Assign timestamps proportionally
        current_time = 0
        for segment in segments:
            if "start_time" not in segment:
                segment["start_time"] = current_time
            
            # Determine the segment duration (use existing if available)
            if "duration" in segment and segment["duration"] > 0:
                duration = segment["duration"]
            else:
                duration = average_duration
                
            # Set end time based on start time + duration
            if "end_time" not in segment:
                segment["end_time"] = segment["start_time"] + duration
                
            # Update duration field for consistency
            segment["duration"] = segment["end_time"] - segment["start_time"]
            
            # Update current_time for next segment
            current_time = segment["end_time"]
    
    return segments

# Function to generate B-Roll segments based on A-Roll segments
def generate_broll_segments(a_roll_segments, theme, strategy="balanced", percentage=25):
    """
    Generate B-Roll segments based on A-Roll segments, a theme, and percentage distribution
    
    Args:
        a_roll_segments: List of A-Roll segments
        theme: Theme for the B-Roll content
        strategy: Legacy parameter for backward compatibility ('balanced', 'full-coverage', 'minimal')
        percentage: Percentage of A-Roll segments to have B-Roll (25, 50, or 75)
        
    Returns:
        List of B-Roll segments
    """
    if not a_roll_segments:
        return []
    
    b_roll_segments = []
    total_aroll_segments = len(a_roll_segments)
    
    # Convert legacy strategy to percentage if needed (for backward compatibility)
    if percentage is None:
        if strategy == "minimal":
            percentage = 25
        elif strategy == "maximum" or strategy == "full-coverage":
            percentage = 75
        else:  # balanced
            percentage = 50
    
    # Calculate number of B-Roll segments based on percentage
    if percentage == 25:
        # 25%: Intro after first segment, outro before last segment
        target_count = max(2, round(total_aroll_segments * 0.25))
    elif percentage == 75:
        # 75%: More B-Roll dominant
        target_count = max(2, round(total_aroll_segments * 0.75))
    else:
        # 50%: Balanced approach
        target_count = max(2, round(total_aroll_segments * 0.50))
    
    # Always include an intro B-Roll
    intro_broll = {
        "type": "B-Roll",
        "content": f"Introductory visual for {theme}",
        "duration": 3.0,  # Default duration in seconds
        "is_intro": True
    }
    b_roll_segments.append(intro_broll)
    
    # For very small target counts, just add intro and outro
    if target_count <= 2:
        # Add outro B-Roll
        outro_broll = {
            "type": "B-Roll",
            "content": f"Concluding visual for {theme}",
            "duration": 3.0,
            "is_outro": True
        }
        b_roll_segments.append(outro_broll)
        return b_roll_segments
    
    # For the remaining B-Roll segments, we'll distribute them based on the percentage
    remaining_brolls = target_count - 1  # Subtract 1 for the intro
    
    # Distribution logic based on percentage
    if percentage == 25:
        # 25%: Place one near the beginning and the rest near the end
        # (We already added intro, so just add one before the end)
        if remaining_brolls >= 1:
            outro_broll = {
                "type": "B-Roll",
                "content": f"Concluding visual for {theme}",
                "duration": 3.0,
                "is_outro": True,
                "related_aroll": total_aroll_segments - 1
            }
            b_roll_segments.append(outro_broll)
    
    elif percentage == 75:
        # 75%: Dense B-Roll coverage
        # Place remaining B-Rolls at regular intervals, but exclude positions right after intro and before outro
        if total_aroll_segments > 2:
            available_positions = list(range(1, total_aroll_segments - 1))
            
            # If we have more remaining_brolls than available positions, we'll just use all positions
            if remaining_brolls >= len(available_positions):
                positions_to_use = available_positions
            else:
                # Otherwise, distribute evenly
                step = len(available_positions) / remaining_brolls
                positions_to_use = [available_positions[min(int(i * step), len(available_positions) - 1)] 
                                   for i in range(remaining_brolls)]
            
            # Create B-Roll segments at the selected positions
            for pos in positions_to_use:
                content = a_roll_segments[pos]["content"]
                summary = content[:50] + "..." if len(content) > 50 else content
                
                broll = {
                    "type": "B-Roll",
                    "content": f"Visual representation of: {summary}",
                    "duration": 3.0,
                    "related_aroll": pos
                }
                b_roll_segments.append(broll)
            
            # Add outro B-Roll
            outro_broll = {
                "type": "B-Roll",
                "content": f"Concluding visual for {theme}",
                "duration": 3.0,
                "is_outro": True,
                "related_aroll": total_aroll_segments - 1
            }
            b_roll_segments.append(outro_broll)
    
    else:
        # 50%: Balanced distribution
        # Distribute remaining B-Rolls evenly across the video
        if total_aroll_segments > 2:
            step = total_aroll_segments / (remaining_brolls + 1)
            
            for i in range(1, remaining_brolls + 1):
                pos = min(int(i * step), total_aroll_segments - 1)
                
                content = a_roll_segments[pos]["content"]
                summary = content[:50] + "..." if len(content) > 50 else content
                
                broll = {
                    "type": "B-Roll",
                    "content": f"Visual representation of: {summary}",
                    "duration": 3.0,
                    "related_aroll": pos
                }
                b_roll_segments.append(broll)
            
            # Add outro B-Roll if it's not already covered by our distribution
            if int(remaining_brolls * step) < total_aroll_segments - 1:
                outro_broll = {
                    "type": "B-Roll",
                    "content": f"Concluding visual for {theme}",
                    "duration": 3.0,
                    "is_outro": True,
                    "related_aroll": total_aroll_segments - 1
                }
                b_roll_segments.append(outro_broll)
    
    return b_roll_segments

# Function to save both A-Roll and B-Roll segments
def save_segments(a_roll_segments, b_roll_segments, theme, broll_percentage=None):
    """Save both A-Roll and B-Roll segments to script.json"""
    script_file = project_path / "script.json"
    
    # Use the session state percentage if not explicitly provided
    if broll_percentage is None and "broll_percentage" in st.session_state:
        broll_percentage = st.session_state.broll_percentage
    
    # Check if script.json already exists and load it
    existing_data = {}
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading existing script: {str(e)}")
    
    # Add debug info
    print(f"Saving script with {len(a_roll_segments)} A-Roll segments and {len(b_roll_segments)} B-Roll segments")
    print(f"B-Roll percentage: {broll_percentage}%")
    
    # Combine segments in the correct order
    all_segments = []
    
    # Always start with intro B-Roll if available
    if b_roll_segments and len(b_roll_segments) > 0:
        all_segments.append(b_roll_segments[0])
    
    # Interleave A-Roll segments with remaining B-Roll segments
    a_roll_idx = 0
    b_roll_idx = 1  # Skip the intro B-Roll we already added
    
    while a_roll_idx < len(a_roll_segments):
        # Add an A-Roll segment
        all_segments.append(a_roll_segments[a_roll_idx])
        a_roll_idx += 1
        
        # Add a B-Roll segment if available
        if b_roll_idx < len(b_roll_segments):
            all_segments.append(b_roll_segments[b_roll_idx])
            b_roll_idx += 1
    
    # Create full script text from segments
    full_script = " ".join([segment["content"] for segment in all_segments if "content" in segment])
    
    # Create B-Roll to A-Roll mapping for reference
    broll_aroll_mapping = {}
    for i, segment in enumerate(b_roll_segments):
        if "related_aroll" in segment:
            broll_aroll_mapping[f"broll_{i}"] = f"aroll_{segment['related_aroll']}"
    
    # Add a clear indication of how many B-roll segments were created
    broll_segment_count = len(b_roll_segments)
    aroll_segment_count = len(a_roll_segments)
    
    # Prepare data to save with version information
    data = {
        "full_script": full_script,
        "segments": all_segments,
        "theme": theme,
        "source": "transcription",
        "timestamp": time.time(),
        "broll_percentage": broll_percentage,
        "broll_aroll_mapping": broll_aroll_mapping,
        "broll_segment_count": broll_segment_count,
        "aroll_segment_count": aroll_segment_count,
        "version": "2.0",  # Add version to track changes in structure
        "generated_with": "percentage_based_allocation"
    }
    
    # Preserve any other fields from existing data
    for key, value in existing_data.items():
        if key not in data and key not in ["segments", "broll_aroll_mapping", "broll_segment_count"]:
            data[key] = value
    
    # Save to file
    try:
        with open(script_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved segments to {script_file}")
        return True
    except IOError as e:
        print(f"Error saving segments: {str(e)}")
        return False

# Function to automatically segment the transcription using Ollama
def automatic_segment_transcription(transcription_data, video_path=None):
    """
    Automatically segment the transcription using Ollama for logical analysis.
    
    Args:
        transcription_data: The full transcription data with word timestamps
        video_path: Optional path to the video file to get duration
        
    Returns:
        List of segments with content, start_time, and end_time
    """
    if not isinstance(transcription_data, dict) or "text" not in transcription_data:
        st.error("Transcription data is missing or invalid")
        return []
    
    full_text = transcription_data["text"]
    
    # Get video duration if possible
    video_duration = None
    if video_path:
        try:
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            video_duration = video.duration
            video.close()
            st.info(f"Video duration for segmentation: {format_time(video_duration)}")
        except Exception as e:
            st.warning(f"Could not determine video duration: {str(e)}")
    
    # Check if Ollama is available
    if not st.session_state.ollama_client.is_available:
        st.warning("Ollama is not available. Falling back to basic segmentation.")
        return segment_transcription(transcription_data)
    
    with st.spinner("Analyzing transcript for logical segments using Ollama..."):
        # Get logical segments from Ollama
        segments = st.session_state.ollama_client.segment_text_logically(
            full_text,
            min_segment_length=5,  # Minimum words per segment
            max_segment_length=30  # Maximum words per segment
        )
        
        # Map segments to timestamps
        segments_with_timestamps = get_segment_timestamps(
            transcription_data,
            segments,
            video_duration
        )
        
        # Add type field to each segment
        for segment in segments_with_timestamps:
            segment["type"] = "A-Roll"
            
        return segments_with_timestamps

def cut_video_into_segments(video_path, segments):
    """
    Cut the video into segments based on timestamps.
    
    Args:
        video_path: Path to the A-Roll video
        segments: List of segments with start_time and end_time
        
    Returns:
        Updated segments with file paths
    """
    if not os.path.exists(video_path):
        st.error(f"Video file not found: {video_path}")
        return segments
    
    # Create output directory for segments
    project_path = get_project_path()
    output_dir = os.path.join(project_path, "media", "a-roll", "segments")
    os.makedirs(output_dir, exist_ok=True)
    
    with st.spinner("Cutting video into segments..."):
        try:
            # Process the segments
            updated_segments = cut_video_segments(
                video_path,
                segments,
                output_dir
            )
            
            # Save the segment files for future reference
            st.session_state.segment_files = [
                segment.get("file_path", "") for segment in updated_segments
                if "file_path" in segment
            ]
            
            # Save segment metadata
            metadata_path = os.path.join(project_path, "segments_metadata.json")
            save_segment_metadata(updated_segments, metadata_path)
            
            return updated_segments
            
        except Exception as e:
            st.error(f"Error cutting video segments: {str(e)}")
            return segments

def generate_broll_prompts_with_ollama(a_roll_segments, theme):
    """
    Generate B-Roll prompts for each A-Roll segment using Ollama.
    
    Args:
        a_roll_segments: List of A-Roll segments
        theme: Theme for the B-Roll content
        
    Returns:
        List of B-Roll segments with prompts
    """
    if not st.session_state.ollama_client.is_available:
        st.warning("Ollama is not available. Falling back to basic B-Roll prompt generation.")
        return generate_broll_segments(a_roll_segments, theme)
    
    b_roll_segments = []
    
    with st.spinner("Generating B-Roll prompts with Ollama..."):
        progress_bar = st.progress(0)
        
        for i, segment in enumerate(a_roll_segments):
            # Update progress
            progress = (i + 1) / len(a_roll_segments)
            progress_bar.progress(progress)
            
            content = segment.get("content", "")
            
            # Skip empty segments
            if not content:
                continue
                
            # Generate B-Roll prompt with Ollama
            success, prompt = st.session_state.ollama_client.generate_broll_prompt(
                content,
                theme=theme,
                style="photorealistic"  # Default style
            )
            
            if not success:
                st.warning(f"Failed to generate B-Roll prompt for segment {i+1}. Using default.")
                prompt = f"Visual representation of: {content[:50]}..."
            
            # Create B-Roll segment
            b_roll_segment = {
                "type": "B-Roll",
                "content": prompt,
                "a_roll_reference": i,
                "start_time": segment.get("start_time", 0),
                "end_time": segment.get("end_time", 0)
            }
            
            b_roll_segments.append(b_roll_segment)
        
        progress_bar.empty()
    
    return b_roll_segments

# Function to clean up existing B-roll data to prevent conflicts
def cleanup_broll_data():
    """
    Clean up existing B-roll data to prevent conflicts with newly generated B-roll segments.
    This ensures that old B-roll data doesn't interfere with the new percentage-based allocation.
    """
    # Clean up broll_prompts.json if it exists
    project_path = get_project_path()
    if not project_path:
        return
    
    broll_prompts_path = os.path.join(project_path, "broll_prompts.json")
    if os.path.exists(broll_prompts_path):
        try:
            os.remove(broll_prompts_path)
            print(f"Removed old B-roll prompts file: {broll_prompts_path}")
        except Exception as e:
            print(f"Error removing old B-roll prompts file: {str(e)}")
    
    # Alternative location in config directory
    config_broll_prompts_path = os.path.join(project_path, "config", "user_data", project_path.name, "broll_prompts.json")
    if os.path.exists(config_broll_prompts_path):
        try:
            os.remove(config_broll_prompts_path)
            print(f"Removed old B-roll prompts file: {config_broll_prompts_path}")
        except Exception as e:
            print(f"Error removing old B-roll prompts file: {str(e)}")
    
    return True

# Main function
def main():
    # Header and instructions
    st.title("A-Roll Transcription")
    render_step_header(1, "A-Roll Transcription", 6)
    
    st.write("Upload your A-Roll video to generate a transcript and split it into segments.")
    
    # Check for video from the previous step
    aroll_video_path = None
    project_path = get_project_path()
    if project_path:
        potential_path = os.path.join(project_path, "media", "a-roll", "main_aroll.mp4")
        if os.path.exists(potential_path):
            aroll_video_path = potential_path
            st.success("Found existing A-Roll video from previous step.")
    
    # Upload widget for A-Roll video
    uploaded_file = st.file_uploader("Upload A-Roll Video", type=["mp4", "mov", "avi", "mkv"])
    
    if uploaded_file or aroll_video_path:
        video_path = aroll_video_path
        
        # Process uploaded file if present
        if uploaded_file:
            # Create the a-roll directory if it doesn't exist
            aroll_dir = os.path.join(project_path, "media", "a-roll")
            os.makedirs(aroll_dir, exist_ok=True)
            
            # Define the path for the main A-Roll video
            main_aroll_path = os.path.join(aroll_dir, "main_aroll.mp4")
            
            # Save the uploaded file directly to the main_aroll.mp4 location
            with open(main_aroll_path, "wb") as f:
                f.write(uploaded_file.read())
            
            # Update the video path to point to the permanent location
            video_path = main_aroll_path
            
            # Store in session state
            st.session_state.uploaded_video = video_path
            
            # Show success message for the upload
            st.success(f"Video uploaded and saved to project.")
        
        # Display the video
        st.video(video_path)
        
        # Transcription section
        st.header("Video Transcription")
        
        # Check if transcription already exists
        transcription_data = load_transcription_data()
        
        if transcription_data is not None:
            st.session_state.transcription_data = transcription_data
            st.session_state.transcription_complete = True
            st.success("Transcription loaded from previous session.")
        
        if not st.session_state.transcription_complete:
            # Transcription engine options
            engine_options = get_available_engines()
            
            if not engine_options:
                st.error("No transcription engines available. Please install whisper or vosk.")
                st.stop()
            
            selected_engine = st.selectbox("Select Transcription Engine", engine_options)
            
            if st.button("Generate Transcript"):
                with st.spinner("Generating transcript... This may take a while for longer videos."):
                    try:
                        # Extract audio from video
                        st.info("Extracting audio from video...")
                        audio_path = extract_audio(video_path)
                        
                        if audio_path:
                            # Transcribe the audio
                            st.info(f"Transcribing audio using {selected_engine}...")
                            transcription_data = transcribe_video(audio_path, engine=selected_engine)
                            
                            if transcription_data and transcription_data.get("status") == "success":
                                # Save and display the transcription
                                save_transcription_data(transcription_data)
                                st.session_state.transcription_data = transcription_data
                                st.session_state.transcription_complete = True
                                
                                # Display success message
                                st.success("Transcription complete!")
                            else:
                                error_msg = transcription_data.get("message", "Unknown error") if transcription_data else "Transcription failed"
                                st.error(f"Transcription failed: {error_msg}")
                        else:
                            st.error("Failed to extract audio from video. Please ensure the video file is valid and has an audio track.")
                    except Exception as e:
                        st.error(f"Error during transcription process: {str(e)}")
                        st.info("Try using a different video file or transcription engine.")
        
        # If transcription is complete, show the text and segmentation options
        if st.session_state.transcription_complete and isinstance(st.session_state.transcription_data, dict):
            transcription_text = st.session_state.transcription_data.get("text", "")
            
            # Display the transcription
            with st.expander("Full Transcription", expanded=False):
                st.write(transcription_text)
            
            # Load existing segments if available
            existing_segments = load_a_roll_segments()
            if existing_segments is not None and len(existing_segments) > 0 and not st.session_state.a_roll_segments:
                st.session_state.a_roll_segments = existing_segments
                st.session_state.segmentation_complete = True
                st.success("Segments loaded from previous session.")
            
            # New section for automatic vs manual segmentation
            st.header("Segmentation Options")
            
            segmentation_tabs = st.tabs(["Automatic Segmentation", "Manual Segmentation"])
            
            # Automatic segmentation tab
            with segmentation_tabs[0]:
                st.write("Automatically segment the transcript into logical chunks using AI.")
                
                # Check if Ollama is available
                ollama_status = "✅ Available" if st.session_state.ollama_client.is_available else "❌ Not Available"
                st.info(f"Ollama Status: {ollama_status}")
                
                if not st.session_state.ollama_client.is_available:
                    st.warning("Ollama is not running. We'll use basic segmentation instead. To use Ollama, please install and run it locally.")
                
                # Automatic segmentation button
                if st.button("Analyze and Segment Automatically"):
                    with st.spinner("Analyzing transcript..."):
                        # Use Ollama to segment the transcript
                        segments = automatic_segment_transcription(st.session_state.transcription_data, video_path)
                        
                        if segments:
                            # Get the video duration if video_path is available
                            video_duration = None
                            if video_path:
                                try:
                                    from moviepy.editor import VideoFileClip
                                    video = VideoFileClip(video_path)
                                    video_duration = video.duration
                                    video.close()
                                    st.info(f"Video duration: {format_time(video_duration)}")
                                except Exception as e:
                                    st.warning(f"Could not determine video duration: {str(e)}")
                            
                            # Ensure segments have proper timing
                            segments = ensure_segments_have_timing(segments, video_duration)
                            
                            st.session_state.a_roll_segments = segments
                            st.session_state.segmentation_complete = True
                            st.session_state.auto_segmentation_complete = True
                            
                            # Save the segments
                            save_a_roll_segments(segments)
                            
                            st.success(f"Successfully created {len(segments)} logical segments!")
                        else:
                            st.error("Automatic segmentation failed.")
                
                # Option to cut video after segmentation
                if st.session_state.auto_segmentation_complete and video_path:
                    if st.button("Cut Video into Segments"):
                        # Cut the video based on segments
                        updated_segments = cut_video_into_segments(
                            video_path, 
                            st.session_state.a_roll_segments
                        )
                        
                        if updated_segments:
                            st.session_state.a_roll_segments = updated_segments
                            save_a_roll_segments(updated_segments)
                            st.success("Video has been cut into segments!")
                        else:
                            st.error("Failed to cut video into segments.")
            
            # Manual segmentation tab
            with segmentation_tabs[1]:
                st.write("Manually segment the transcript by adjusting parameters.")
                
                # Only show manual segmentation controls if automatic segmentation hasn't been done
                if not st.session_state.segmentation_complete:
                    # Segmentation parameters
                    col1, col2 = st.columns(2)
                    with col1:
                        min_duration = st.slider("Minimum Segment Duration (seconds)", 1, 15, 5)
                    with col2:
                        max_duration = st.slider("Maximum Segment Duration (seconds)", 10, 60, 20)
                    
                    # Button to segment the transcript
                    if st.button("Segment Transcript"):
                        with st.spinner("Segmenting transcript..."):
                            # Use the existing manual segmentation function
                            segments = segment_transcription(
                                transcription_text,
                                min_segment_duration=min_duration,
                                max_segment_duration=max_duration
                            )
                            
                            # Get the video duration if video_path is available
                            video_duration = None
                            if video_path:
                                try:
                                    from moviepy.editor import VideoFileClip
                                    video = VideoFileClip(video_path)
                                    video_duration = video.duration
                                    video.close()
                                    st.info(f"Video duration: {format_time(video_duration)}")
                                except Exception as e:
                                    st.warning(f"Could not determine video duration: {str(e)}")
                            
                            # Ensure segments have timing information
                            segments = ensure_segments_have_timing(segments, video_duration)
                            
                            # Store the segments
                            st.session_state.a_roll_segments = segments
                            st.session_state.segmentation_complete = True
                            
                            # Save the segments
                            save_a_roll_segments(segments)
                            
                            st.success(f"Successfully created {len(segments)} segments!")
                else:
                    st.info("Segmentation has already been completed. You can edit segments below.")
            
            # If segmentation is complete, show the segments and allow editing
            if st.session_state.segmentation_complete and st.session_state.a_roll_segments:
                st.header("A-Roll Segments")
                
                # Generate timeline visualization
                segments = st.session_state.a_roll_segments
                
                # Get the total duration from the last segment's end time
                if segments:
                    total_duration = max([segment.get("end_time", 0) for segment in segments])
                else:
                    total_duration = 0
                
                # Display timeline
                st.subheader("Timeline Visualization")
                
                timeline_height = 80
                timeline_width = 800
                padding = 20
                
                # Create a placeholder for the timeline
                timeline_placeholder = st.empty()
                
                # Generate the timeline visualization
                from matplotlib import pyplot as plt
                import io
                import base64
                
                fig, ax = plt.subplots(figsize=(10, 2))
                
                # Draw timeline
                ax.plot([0, total_duration], [0, 0], 'k-', linewidth=2)
                
                # Add ruler marks
                for i in range(0, int(total_duration) + 1, 5):
                    ax.plot([i, i], [-0.1, 0.1], 'k-', linewidth=1)
                    ax.text(i, -0.3, f"{i}s", ha='center', fontsize=8)
                
                # Plot segments
                for i, segment in enumerate(segments):
                    start_time = segment.get("start_time", 0)
                    end_time = segment.get("end_time", 0)
                    
                    # Draw segment as a colored rectangle
                    rect = plt.Rectangle((start_time, -0.5), end_time - start_time, 1, 
                                       facecolor='blue', alpha=0.3)
                    ax.add_patch(rect)
                    
                    # Add segment number
                    ax.text((start_time + end_time) / 2, 0, str(i+1), 
                          ha='center', va='center', fontsize=8, fontweight='bold')
                
                # Set plot properties
                ax.set_ylim(-1, 1)
                ax.set_xlim(0, total_duration)
                ax.axis('off')
                ax.set_title('A-Roll Segments Timeline')
                
                # Save the figure to a bytes buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)
                
                # Display the timeline
                timeline_placeholder.image(buf, width=timeline_width)
                
                # Display and edit each segment
                for i, segment in enumerate(segments):
                    with st.expander(f"Segment {i+1}: {format_time(segment.get('start_time', 0))} - {format_time(segment.get('end_time', 0))}", expanded=False):
                        # Display the segment content
                        if st.session_state.segment_edit_index == i:
                            # Edit mode
                            new_content = st.text_area(f"Edit Segment {i+1}", segment.get("content", ""), height=100)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"Save Segment {i+1}"):
                                    update_segment_content(i, new_content)
                                    st.session_state.segment_edit_index = -1
                                    st.experimental_rerun()
                            with col2:
                                if st.button(f"Cancel Editing {i+1}"):
                                    st.session_state.segment_edit_index = -1
                                    st.experimental_rerun()
                        else:
                            # Display mode
                            st.markdown(f"""
                            <div class="segment-content">
                                {segment.get("content", "")}
                                <div class="timestamp">
                                    Duration: {format_time(segment.get("end_time", 0) - segment.get("start_time", 0))}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"Edit Segment {i+1}"):
                                    st.session_state.segment_edit_index = i
                                    st.experimental_rerun()
                            
                            # If we have the video file, add a preview button
                            if video_path and "file_path" not in segment:
                                with col2:
                                    if st.button(f"Preview Segment {i+1}"):
                                        start_time = segment.get("start_time", 0)
                                        end_time = segment.get("end_time", 0)
                                        
                                        # Create preview directory if it doesn't exist
                                        preview_dir = os.path.join(project_path, "preview")
                                        os.makedirs(preview_dir, exist_ok=True)
                                        
                                        # Generate preview
                                        preview_path = os.path.join(preview_dir, f"segment_{i}_preview.mp4")
                                        success = preview_segment(video_path, start_time, end_time, preview_path)
                                        
                                        if success:
                                            st.video(preview_path)
                                        else:
                                            st.error("Failed to generate preview.")
                            
                            # If the segment has a file path, display the video
                            if "file_path" in segment:
                                file_path = segment["file_path"]
                                if os.path.exists(file_path):
                                    st.video(file_path)
                
                # Theme selection for B-Roll generation
                st.header("B-Roll Theme Selection")
                
                with st.container():
                    st.markdown("""
                    <div class="theme-container">
                        <h3>Choose a theme for your B-Roll content</h3>
                        <p>The theme will guide the visual style and content of your B-Roll segments.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    theme = st.text_input("Enter a theme (e.g., 'business', 'technology', 'nature')", 
                                         value=st.session_state.script_theme)
                    
                    # B-Roll generation strategy
                    st.subheader("B-Roll Generation")
                    
                    generation_tabs = st.tabs(["Automatic Generation", "Manual Configuration"])
                    
                    with generation_tabs[0]:
                        st.write("Automatically generate B-Roll prompts for each segment using AI.")
                        
                        # Add percentage selector here as well for consistency
                        st.markdown("""
                        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            <h4>B-Roll Density</h4>
                            <p>Select what percentage of A-Roll segments should have corresponding B-Roll segments:</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        percentage_options = {25: "25% - Minimal", 50: "50% - Balanced", 75: "75% - Maximum"}
                        auto_selected_percentage = st.select_slider(
                            "B-Roll Percentage",
                            options=list(percentage_options.keys()),
                            value=st.session_state.broll_percentage,
                            format_func=lambda x: percentage_options[x],
                            help="Select the percentage of A-Roll segments that should have corresponding B-Roll segments.",
                            key="auto_broll_percentage_slider"
                        )
                        
                        # Update session state with selected percentage
                        st.session_state.broll_percentage = auto_selected_percentage
                        
                        # Add B-Roll type selection (Video vs Image)
                        if "broll_type" not in st.session_state:
                            st.session_state.broll_type = "video"
                            
                        broll_type = st.radio(
                            "Select B-Roll Type:",
                            ["Video", "Image"],
                            index=0 if st.session_state.broll_type.lower() == "video" else 1,
                            key="broll_type_selector"
                        )
                        
                        # Update session state with the selected B-Roll type (store in lowercase)
                        st.session_state.broll_type = broll_type.lower()
                        
                        # Add image workflow selection if image type is selected
                        if st.session_state.broll_type == "image":
                            # Initialize session state for image template if not exists
                            if "image_template" not in st.session_state:
                                st.session_state.image_template = "image_homepc"
                            
                            # Add selection for image template
                            image_templates = {"image_homepc": "Home PC", "flux_schnell": "Flux Schnell"}
                            image_template = st.selectbox(
                                "Select Image Workflow Template:",
                                options=list(image_templates.keys()),
                                index=list(image_templates.keys()).index(st.session_state.image_template) 
                                    if st.session_state.image_template in image_templates else 0,
                                format_func=lambda x: image_templates.get(x, x.replace("_", " ").title()),
                                help="Choose which workflow template to use for image generation"
                            )
                            
                            # Store selection in session state
                            st.session_state.image_template = image_template
                            
                            # Show selected template
                            st.info(f"Using template: **{image_templates.get(image_template, image_template)}**")
                        
                        if st.button("Generate B-Roll Prompts with AI"):
                            with st.spinner("Generating B-Roll prompts..."):
                                # Clean up existing B-roll data first
                                cleanup_broll_data()
                                
                                # Use Ollama to generate B-Roll prompts
                                b_roll_segments = generate_broll_prompts_with_ollama(
                                    st.session_state.a_roll_segments,
                                    theme
                                )
                                
                                if b_roll_segments:
                                    # Apply the percentage-based filtering to the AI-generated prompts
                                    total_aroll_segments = len(st.session_state.a_roll_segments)
                                    target_count = max(2, round(total_aroll_segments * (auto_selected_percentage / 100)))
                                    
                                    # Always keep the first B-Roll segment (intro)
                                    filtered_segments = [b_roll_segments[0]]
                                    
                                    # If we have more than one segment, apply percentage-based filtering
                                    if len(b_roll_segments) > 1:
                                        # For 25%, keep intro and outro
                                        if auto_selected_percentage == 25:
                                            if len(b_roll_segments) > 1:
                                                filtered_segments.append(b_roll_segments[-1])
                                        # For other percentages, select segments evenly
                                        else:
                                            remaining_count = min(target_count - 1, len(b_roll_segments) - 1)
                                            if remaining_count > 0:
                                                step = (len(b_roll_segments) - 1) / remaining_count
                                                indices = [min(int(i * step) + 1, len(b_roll_segments) - 1) for i in range(remaining_count)]
                                                for idx in indices:
                                                    filtered_segments.append(b_roll_segments[idx])
                                    
                                    st.session_state.b_roll_segments = filtered_segments
                                    
                                    # Save B-Roll type to the script.json file
                                    broll_prompts_data = {
                                        "prompts": {str(i): segment.get("content", "") for i, segment in enumerate(filtered_segments)},
                                        "broll_type": st.session_state.broll_type,
                                        "image_template": st.session_state.get("image_template", "image_homepc") if st.session_state.broll_type == "image" else None
                                    }
                                    broll_prompts_file = project_path / "broll_prompts.json"
                                    with open(broll_prompts_file, "w") as f:
                                        json.dump(broll_prompts_data, f, indent=2)
                                    
                                    # Save the segments and theme
                                    save_segments(
                                        st.session_state.a_roll_segments,
                                        filtered_segments,
                                        theme,
                                        auto_selected_percentage
                                    )
                                    
                                    st.session_state.script_theme = theme
                                    
                                    # Mark step as complete
                                    mark_step_complete("aroll_transcription")
                                    
                                    st.success("B-Roll prompts generated successfully!")
                                    
                                    # Add direct navigation to B-Roll production with a more prominent style
                                    nav_col1, nav_col2 = st.columns([2, 1])
                                    with nav_col2:
                                        if st.button("Next: B-Roll Production ➡️", key="auto_next_button", type="primary", use_container_width=True):
                                            st.switch_page("pages/5B_BRoll_Video_Production.py")
                                else:
                                    st.error("Failed to generate B-Roll prompts.")
                    
                    with generation_tabs[1]:
                        st.write("Configure B-Roll generation strategy manually.")
                        
                        # Replace strategy radio with percentage selector
                        st.markdown("""
                        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            <h4>B-Roll Density</h4>
                            <p>Select what percentage of A-Roll segments should have corresponding B-Roll segments:</p>
                            <ul>
                                <li><strong>25%</strong>: Minimal B-Roll, placed after the intro and before the outro</li>
                                <li><strong>50%</strong>: Balanced B-Roll distribution across the video</li>
                                <li><strong>75%</strong>: Dense B-Roll coverage for a more visual experience</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add percentage selector with options 25%, 50%, 75%
                        percentage_options = {25: "25% - Minimal", 50: "50% - Balanced", 75: "75% - Maximum"}
                        selected_percentage = st.select_slider(
                            "B-Roll Percentage",
                            options=list(percentage_options.keys()),
                            value=st.session_state.broll_percentage,
                            format_func=lambda x: percentage_options[x],
                            help="Select the percentage of A-Roll segments that should have corresponding B-Roll segments.",
                            key="manual_broll_percentage_slider"
                        )
                        
                        # Update session state with selected percentage
                        st.session_state.broll_percentage = selected_percentage
                        
                        # Add B-Roll type selection (Video vs Image)
                        if "broll_type" not in st.session_state:
                            st.session_state.broll_type = "video"
                            
                        manual_broll_type = st.radio(
                            "Select B-Roll Type:",
                            ["Video", "Image"],
                            index=0 if st.session_state.broll_type.lower() == "video" else 1,
                            key="manual_broll_type_selector"
                        )
                        
                        # Update session state with the selected B-Roll type (store in lowercase)
                        st.session_state.broll_type = manual_broll_type.lower()
                        
                        # Add image workflow selection if image type is selected
                        if st.session_state.broll_type == "image":
                            # Initialize session state for image template if not exists
                            if "image_template" not in st.session_state:
                                st.session_state.image_template = "image_homepc"
                            
                            # Add selection for image template
                            image_templates = {"image_homepc": "Home PC", "flux_schnell": "Flux Schnell"}
                            manual_image_template = st.selectbox(
                                "Select Image Workflow Template:",
                                options=list(image_templates.keys()),
                                index=list(image_templates.keys()).index(st.session_state.image_template) 
                                    if st.session_state.image_template in image_templates else 0,
                                format_func=lambda x: image_templates.get(x, x.replace("_", " ").title()),
                                help="Choose which workflow template to use for image generation",
                                key="manual_image_template"
                            )
                            
                            # Store selection in session state
                            st.session_state.image_template = manual_image_template
                            
                            # Show selected template
                            st.info(f"Using template: **{image_templates.get(manual_image_template, manual_image_template)}**")
                        
                        if st.button("Generate B-Roll Segments"):
                            with st.spinner("Generating B-Roll segments..."):
                                # Clean up existing B-roll data first
                                cleanup_broll_data()
                                
                                # Use the updated function with percentage parameter
                                b_roll_segments = generate_broll_segments(
                                    st.session_state.a_roll_segments,
                                    theme,
                                    percentage=selected_percentage
                                )
                                
                                st.session_state.b_roll_segments = b_roll_segments
                                
                                # Save B-Roll type to the broll_prompts.json file
                                broll_prompts_data = {
                                    "prompts": {str(i): segment.get("content", "") for i, segment in enumerate(b_roll_segments)},
                                    "broll_type": st.session_state.broll_type,
                                    "image_template": st.session_state.get("image_template", "image_homepc") if st.session_state.broll_type == "image" else None
                                }
                                broll_prompts_file = project_path / "broll_prompts.json"
                                with open(broll_prompts_file, "w") as f:
                                    json.dump(broll_prompts_data, f, indent=2)
                                
                                # Save the segments and theme
                                save_segments(
                                    st.session_state.a_roll_segments,
                                    b_roll_segments,
                                    theme,
                                    selected_percentage
                                )
                                
                                st.session_state.script_theme = theme
                                
                                # Mark step as complete
                                mark_step_complete("aroll_transcription")
                                
                                st.success("B-Roll segments generated successfully!")
                                
                                # Add direct navigation to B-Roll production with a more prominent style
                                nav_col1, nav_col2 = st.columns([2, 1])
                                with nav_col2:
                                    if st.button("Next: B-Roll Production ➡️", key="manual_next_button", type="primary", use_container_width=True):
                                        st.switch_page("pages/5B_BRoll_Video_Production.py")
                
                # If B-Roll segments have been generated, display them
                if st.session_state.b_roll_segments:
                    st.header("B-Roll Segments Preview")
                    
                    b_roll_segments = st.session_state.b_roll_segments
                    
                    for i, segment in enumerate(b_roll_segments):
                        with st.expander(f"B-Roll {i+1}", expanded=False):
                            a_roll_ref = segment.get("a_roll_reference", 0)
                            a_roll_segment = st.session_state.a_roll_segments[a_roll_ref] if a_roll_ref < len(st.session_state.a_roll_segments) else None
                            
                            st.markdown("**A-Roll Context:**")
                            if a_roll_segment:
                                st.write(a_roll_segment.get("content", ""))
                            
                            st.markdown("**B-Roll Prompt:**")
                            st.markdown(f"""
                            <div class="broll-segment-content">
                                {segment.get("content", "")}
                            </div>
                            """, unsafe_allow_html=True)

# Helper function to format time in MM:SS format
def format_time(seconds):
    try:
        # Convert to float first in case it's a string or other type
        seconds_float = float(seconds)
        minutes = int(seconds_float // 60)
        seconds = int(seconds_float % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        # Return a default value if conversion fails
        return "00:00"

# Git helper for saving progress
def git_commit_changes():
    """Helper function to commit changes to Git"""
    try:
        import subprocess
        import datetime
        
        # Get current timestamp for commit message
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Git add all changes
        subprocess.run(["git", "add", "."], check=True)
        
        # Git commit with timestamp
        commit_message = f"A-Roll Transcription completed - {timestamp}"
        result = subprocess.run(["git", "commit", "-m", commit_message], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Changes committed successfully!"
        else:
            return False, f"Commit failed: {result.stderr}"
    except Exception as e:
        return False, f"Error committing changes: {str(e)}"

if __name__ == "__main__":
    main()
    
    # Add Git commit helper at the bottom
    with st.expander("💾 Save Progress to Git", expanded=False):
        st.markdown("""
        ### Commit your changes to Git
        
        This will save your current progress to your Git repository.
        """)
        
        if st.button("Commit Changes", key="git_commit_button", type="primary"):
            with st.spinner("Committing changes..."):
                success, message = git_commit_changes()
                if success:
                    st.success(message)
                else:
                    st.error(message) 