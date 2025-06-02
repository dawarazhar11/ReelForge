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
    from utils.ai.broll_prompt_generator import (
        check_ollama_availability,
        get_available_models,
        generate_all_broll_prompts,
        save_broll_prompts,
        DEFAULT_MODEL
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
if "use_ollama_prompts" not in st.session_state:
    st.session_state.use_ollama_prompts = True
if "ollama_available" not in st.session_state:
    st.session_state.ollama_available = False
if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = []
if "selected_ollama_model" not in st.session_state:
    st.session_state.selected_ollama_model = DEFAULT_MODEL
if "broll_generation_strategy" not in st.session_state:
    st.session_state.broll_generation_strategy = "balanced"

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
                return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading transcription: {str(e)}")
            return False
    return False

# Function to save A-roll segments
def save_a_roll_segments(segments):
    """Save A-roll segments to script.json"""
    # If we have B-Roll segments, use the new save_segments function
    if "b_roll_segments" in st.session_state and st.session_state.b_roll_segments:
        return save_segments(
            segments,
            st.session_state.b_roll_segments,
            st.session_state.script_theme
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
                        
                        return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading A-roll segments: {str(e)}")
            return False
    return False

# Function to segment the transcription
def segment_transcription(transcription, min_segment_duration=5, max_segment_duration=5):
    """
    Segment the transcription into A-Roll segments
    
    Args:
        transcription: The transcription data
        min_segment_duration: Minimum segment duration in seconds
        max_segment_duration: Maximum segment duration in seconds
        
    Returns:
        List of A-Roll segments
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
def ensure_segments_have_timing(segments):
    """Add default timing information to segments that don't have it"""
    for i, segment in enumerate(segments):
        if "start_time" not in segment:
            segment["start_time"] = i * 10  # Default 10 seconds per segment
        if "end_time" not in segment:
            segment["end_time"] = (i + 1) * 10
        if "duration" not in segment:
            segment["duration"] = segment["end_time"] - segment["start_time"]
    return segments

# Function to generate B-Roll segments based on A-Roll segments
def generate_broll_segments(a_roll_segments, theme, strategy="balanced"):
    """
    Generate B-Roll segments based on A-Roll segments and a theme
    
    Args:
        a_roll_segments: List of A-Roll segments
        theme: Theme for the B-Roll content
        strategy: Strategy for B-Roll placement ('minimal', 'balanced', 'maximum')
        
    Returns:
        List of B-Roll segments with timestamp mapping
    """
    if not a_roll_segments:
        return []
    
    b_roll_segments = []
    
    # Determine number of B-Roll segments based on strategy
    if strategy == "minimal":
        # Minimal: Just intro and outro B-Roll
        target_count = 2
    elif strategy == "maximum":
        # Maximum: B-Roll for every A-Roll segment
        target_count = len(a_roll_segments)
    else:
        # Balanced: Approximately 1 B-Roll for every 2 A-Roll segments
        target_count = max(2, len(a_roll_segments) // 2 + 1)
    
    # Always add intro B-Roll (not mapped to any A-Roll)
    intro_broll = {
        "type": "B-Roll",
        "content": f"Introductory visual for {theme}",
        "duration": 3.0,  # Default duration in seconds
        "timestamp": 0.0,  # Start at the beginning
        "is_intro": True,
        "visuals": [
            {
                "content": f"Opening shot for {theme}",
                "duration": 3.0
            }
        ]
    }
    b_roll_segments.append(intro_broll)
    
    # Create B-Roll segments for A-Roll segments based on strategy
    if strategy == "minimal":
        # Just add outro B-Roll
        if len(a_roll_segments) > 0:
            last_segment = a_roll_segments[-1]
            end_time = last_segment.get("end_time", 0)
            
            outro_broll = {
                "type": "B-Roll",
                "content": f"Concluding visual for {theme}",
                "duration": 3.0,
                "timestamp": end_time,  # Start at the end of the last A-Roll
                "is_outro": True,
                "visuals": [
                    {
                        "content": f"Closing shot for {theme}",
                        "duration": 3.0
                    }
                ]
            }
            b_roll_segments.append(outro_broll)
    elif strategy == "maximum":
        # Add B-Roll for each A-Roll segment
        for i, segment in enumerate(a_roll_segments):
            if "start_time" not in segment or "end_time" not in segment:
                print(f"Warning: A-Roll segment {i} missing timing information")
                continue
                
            content = segment["content"]
            summary = content[:50] + "..." if len(content) > 50 else content
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            duration = end_time - start_time
            
            # If segment is too short, adjust duration
            if duration < 1.0:
                duration = 1.0
            
            # For longer segments, we can have multiple visuals
            visuals = []
            if duration > 8.0:
                # Create 2-3 visuals for longer segments
                num_visuals = min(3, int(duration / 3))
                sub_duration = duration / num_visuals
                
                for j in range(num_visuals):
                    visual_summary = f"Part {j+1} of: {summary}"
                    visuals.append({
                        "content": visual_summary,
                        "duration": sub_duration,
                        "position": j / num_visuals  # Relative position (0-1) within the segment
                    })
            else:
                # Just one visual for shorter segments
                visuals.append({
                    "content": summary,
                    "duration": duration,
                    "position": 0.0
                })
            
            broll = {
                "type": "B-Roll",
                "content": f"Visual representation of: {summary}",
                "timestamp": start_time,
                "duration": duration,
                "mapped_aroll_index": i,  # Index of related A-Roll segment
                "visuals": visuals
            }
            b_roll_segments.append(broll)
            
        # Add outro B-Roll if there are A-Roll segments
        if len(a_roll_segments) > 0:
            last_segment = a_roll_segments[-1]
            end_time = last_segment.get("end_time", 0)
            
            outro_broll = {
                "type": "B-Roll",
                "content": f"Concluding visual for {theme}",
                "duration": 3.0,
                "timestamp": end_time,  # Start at the end of the last A-Roll
                "is_outro": True,
                "visuals": [
                    {
                        "content": f"Closing shot for {theme}",
                        "duration": 3.0
                    }
                ]
            }
            b_roll_segments.append(outro_broll)
    else:
        # Balanced approach: Add B-Roll at strategic points
        segments_per_broll = max(1, len(a_roll_segments) // (target_count - 1))
        
        for i in range(0, len(a_roll_segments), segments_per_broll):
            if i > 0 and len(b_roll_segments) < target_count - 1:
                # Get the current A-Roll segment
                if i < len(a_roll_segments):
                    segment = a_roll_segments[i]
                    
                    if "start_time" not in segment or "end_time" not in segment:
                        print(f"Warning: A-Roll segment {i} missing timing information")
                        continue
                        
                    content = segment["content"]
                    summary = content[:50] + "..." if len(content) > 50 else content
                    start_time = segment["start_time"]
                    end_time = segment["end_time"]
                    duration = end_time - start_time
                    
                    # If segment is too short, adjust duration
                    if duration < 1.0:
                        duration = 1.0
                    
                    # Create visuals similar to the maximum strategy
                    visuals = []
                    if duration > 8.0:
                        num_visuals = min(3, int(duration / 3))
                        sub_duration = duration / num_visuals
                        
                        for j in range(num_visuals):
                            visual_summary = f"Part {j+1} of: {summary}"
                            visuals.append({
                                "content": visual_summary,
                                "duration": sub_duration,
                                "position": j / num_visuals
                            })
                    else:
                        visuals.append({
                            "content": summary,
                            "duration": duration,
                            "position": 0.0
                        })
                    
                    broll = {
                        "type": "B-Roll",
                        "content": f"Visual representation of: {summary}",
                        "timestamp": start_time,
                        "duration": duration,
                        "mapped_aroll_index": i,
                        "visuals": visuals
                    }
                    b_roll_segments.append(broll)
        
        # Add outro B-Roll if there are A-Roll segments and we haven't reached the target count
        if len(a_roll_segments) > 0 and len(b_roll_segments) < target_count:
            last_segment = a_roll_segments[-1]
            end_time = last_segment.get("end_time", 0)
            
            outro_broll = {
                "type": "B-Roll",
                "content": f"Concluding visual for {theme}",
                "duration": 3.0,
                "timestamp": end_time,
                "is_outro": True,
                "visuals": [
                    {
                        "content": f"Closing shot for {theme}",
                        "duration": 3.0
                    }
                ]
            }
            b_roll_segments.append(outro_broll)
    
    return b_roll_segments

# Function to save both A-Roll and B-Roll segments
def save_segments(a_roll_segments, b_roll_segments, theme, aroll_percentage=0.6):
    """
    Save both A-Roll and B-Roll segments to script.json with timestamp mapping
    
    Args:
        a_roll_segments: List of A-Roll segments
        b_roll_segments: List of B-Roll segments
        theme: Theme for the video
        aroll_percentage: Percentage of time to show only A-Roll (0.6 = 60%)
    
    Returns:
        bool: True if saved successfully, False otherwise
    """
    script_file = project_path / "script.json"
    
    # Check if script.json already exists and load it
    existing_data = {}
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading existing script: {str(e)}")
    
    # Create mapping between B-Roll and A-Roll segments based on timestamps
    broll_aroll_mapping = {}
    timeline_segments = []
    
    # First, sort the B-Roll segments by timestamp
    sorted_broll = sorted(b_roll_segments, key=lambda x: x.get("timestamp", 0))
    
    # Process intro B-Roll first (if exists)
    intro_broll = next((b for b in sorted_broll if b.get("is_intro", False)), None)
    if intro_broll:
        timeline_segments.append(intro_broll)
        # Remove from the list so we don't process it again
        sorted_broll.remove(intro_broll)
    
    # Process A-Roll segments with their associated B-Roll segments
    for i, a_segment in enumerate(a_roll_segments):
        # Add the A-Roll segment
        timeline_segments.append(a_segment)
        
        # Find any B-Roll segments that map to this A-Roll segment
        matching_broll = [b for b in sorted_broll if b.get("mapped_aroll_index") == i]
        
        # If we found matching B-Roll segments, add them to the timeline and mapping
        for broll in matching_broll:
            # Add to timeline in timestamp order
            timeline_segments.append(broll)
            
            # Add to mapping
            broll_id = f"broll_{len(broll_aroll_mapping)}"
            aroll_id = f"aroll_{i}"
            
            broll_aroll_mapping[broll_id] = {
                "aroll_segment": aroll_id,
                "timestamp": broll.get("timestamp", 0),
                "duration": broll.get("duration", 3.0),
                "visuals": broll.get("visuals", [])
            }
            
            # Remove from the list so we don't process it again
            sorted_broll.remove(broll)
    
    # Process outro B-Roll last (if exists and not already processed)
    outro_broll = next((b for b in sorted_broll if b.get("is_outro", False)), None)
    if outro_broll:
        timeline_segments.append(outro_broll)
    
    # Create full script text from segments
    full_script = " ".join([segment["content"] for segment in timeline_segments if "content" in segment])
    
    # Prepare data to save
    data = {
        "full_script": full_script,
        "segments": timeline_segments,
        "theme": theme,
        "source": "transcription",
        "timestamp": time.time(),
        "broll_type": "video",  # Default to video B-Roll
        "exclude_negative_prompts": False,
        "map_broll_to_aroll": True,  # Enable B-Roll to A-Roll mapping
        "broll_aroll_mapping": broll_aroll_mapping,
        "aroll_percentage": aroll_percentage  # Save the A-Roll percentage setting
    }
    
    # Preserve any other fields from existing data
    for key, value in existing_data.items():
        if key not in data:
            data[key] = value
    
    # Save to file
    try:
        with open(script_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved segments to {script_file}")
        
        # Generate B-Roll prompts with Ollama if enabled
        if st.session_state.use_ollama_prompts and st.session_state.ollama_available:
            try:
                # Use selected model or default
                model = st.session_state.selected_ollama_model or DEFAULT_MODEL
                prompts = generate_all_broll_prompts(timeline_segments, theme, model, is_video=True)
                if prompts:
                    save_broll_prompts(prompts, project_path, broll_type="video")
                    print(f"Generated and saved B-Roll prompts using Ollama model: {model}")
            except Exception as e:
                print(f"Error generating B-Roll prompts: {str(e)}")
        
        return True
    except IOError as e:
        print(f"Error saving segments: {str(e)}")
        return False

def display_timeline_visualization(a_roll_segments, b_roll_segments=None):
    """
    Display a visual timeline of A-Roll segments with B-Roll overlays
    
    Args:
        a_roll_segments: List of A-Roll segments
        b_roll_segments: List of B-Roll segments
    """
    if not a_roll_segments:
        st.warning("No A-Roll segments to display")
        return
        
    # Add CSS for the timeline
    st.markdown("""
    <style>
        .timeline-container {
            position: relative;
            width: 100%;
            height: 200px;
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }
        .timeline-ruler {
            position: relative;
            width: 100%;
            height: 30px;
            background-color: #f7f7f7;
            border-bottom: 1px solid #ddd;
            display: flex;
            align-items: center;
        }
        .timeline-ruler-mark {
            position: absolute;
            width: 1px;
            height: 10px;
            background-color: #777;
            bottom: 0;
        }
        .timeline-ruler-text {
            position: absolute;
            font-size: 10px;
            color: #777;
            bottom: 12px;
            transform: translateX(-50%);
        }
        .timeline-segments {
            position: relative;
            width: 100%;
            height: 170px;
            background-color: #fff;
        }
        .timeline-aroll {
            position: absolute;
            height: 40px;
            background-color: #64B5F6;
            border-radius: 4px;
            top: 30px;
            color: white;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 10px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            z-index: 1;
        }
        .timeline-broll {
            position: absolute;
            height: 40px;
            background-color: #FF9800;
            border-radius: 4px;
            top: 80px;
            color: white;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 10px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            z-index: 2;
            border: 1px dashed #fff;
        }
        .timeline-sequence {
            position: absolute;
            height: 30px;
            background-color: #4CAF50;
            border-radius: 4px;
            top: 130px;
            color: white;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 10px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            z-index: 3;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Calculate total duration
    total_duration = 0
    for segment in a_roll_segments:
        if "end_time" in segment:
            total_duration = max(total_duration, segment["end_time"])
    
    if total_duration == 0:
        st.warning("No valid timing information in A-Roll segments")
        return
    
    # Create the timeline container
    st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
    
    # Create the ruler
    st.markdown('<div class="timeline-ruler">', unsafe_allow_html=True)
    
    # Add ruler marks every second
    for i in range(int(total_duration) + 1):
        left_percent = (i / total_duration) * 100
        if i % 5 == 0 or i == int(total_duration):  # Label every 5 seconds and the end
            st.markdown(f'<div class="timeline-ruler-mark" style="left: {left_percent}%;"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="timeline-ruler-text" style="left: {left_percent}%;">{i}s</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="timeline-ruler-mark" style="left: {left_percent}%; height: 5px;"></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create the segments container
    st.markdown('<div class="timeline-segments">', unsafe_allow_html=True)
    
    # Add A-Roll segments
    for i, segment in enumerate(a_roll_segments):
        if "start_time" in segment and "end_time" in segment:
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            duration = end_time - start_time
            
            left_percent = (start_time / total_duration) * 100
            width_percent = (duration / total_duration) * 100
            
            # Limit text length for display
            content = segment.get("content", "")
            if len(content) > 30:
                content = content[:27] + "..."
            
            st.markdown(
                f'<div class="timeline-aroll" style="left: {left_percent}%; width: {width_percent}%;" title="{segment.get("content", "")}">A{i}: {content}</div>',
                unsafe_allow_html=True
            )
    
    # Add B-Roll segments if provided
    if b_roll_segments:
        for i, segment in enumerate(b_roll_segments):
            if "timestamp" in segment and "duration" in segment:
                start_time = segment["timestamp"]
                duration = segment["duration"]
                
                left_percent = (start_time / total_duration) * 100
                width_percent = (duration / total_duration) * 100
                
                # Limit text length for display
                content = segment.get("content", "")
                if len(content) > 30:
                    content = content[:27] + "..."
                
                # Different styling for intro/outro B-Rolls
                extra_style = ""
                if segment.get("is_intro", False):
                    extra_style = "border: 2px solid #fff; background-color: #E65100;"
                elif segment.get("is_outro", False):
                    extra_style = "border: 2px solid #fff; background-color: #E65100;"
                
                st.markdown(
                    f'<div class="timeline-broll" style="left: {left_percent}%; width: {width_percent}%; {extra_style}" title="{segment.get("content", "")}">B{i}: {content}</div>',
                    unsafe_allow_html=True
                )
    
    # Show sequence visualization
    # This will visualize A1 → (B1+A2) → (B2+A3) → (B3+A4) pattern
    if b_roll_segments:
        # Sort by timestamp
        segments = sorted(a_roll_segments + b_roll_segments, key=lambda x: x.get("start_time", 0) if "start_time" in x else x.get("timestamp", 0))
        
        # Create sequence blocks
        current_pos = 0
        for i, segment in enumerate(segments):
            if segment["type"] == "A-Roll" and i == 0:
                # First A-Roll segment
                start_time = segment.get("start_time", 0)
                end_time = segment.get("end_time", 0)
                duration = end_time - start_time
                
                left_percent = (start_time / total_duration) * 100
                width_percent = (duration / total_duration) * 100
                
                st.markdown(
                    f'<div class="timeline-sequence" style="left: {left_percent}%; width: {width_percent}%;">A{current_pos}</div>',
                    unsafe_allow_html=True
                )
                current_pos += 1
            elif segment["type"] == "B-Roll" and i < len(segments) - 1 and segments[i+1]["type"] == "A-Roll":
                # B-Roll followed by A-Roll
                b_start = segment.get("timestamp", 0)
                a_start = segments[i+1].get("start_time", 0)
                a_end = segments[i+1].get("end_time", 0)
                
                # Use the longer of the two segments
                end_time = max(b_start + segment.get("duration", 0), a_end)
                duration = end_time - b_start
                
                left_percent = (b_start / total_duration) * 100
                width_percent = (duration / total_duration) * 100
                
                # Get the current B-Roll and A-Roll indices
                b_index = [j for j, s in enumerate(b_roll_segments) if s is segment][0]
                a_index = [j for j, s in enumerate(a_roll_segments) if s is segments[i+1]][0]
                
                st.markdown(
                    f'<div class="timeline-sequence" style="left: {left_percent}%; width: {width_percent}%;">B{b_index}+A{a_index}</div>',
                    unsafe_allow_html=True
                )
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add legend
    st.markdown("""
    <div style="display: flex; gap: 20px; margin-top: 10px;">
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #64B5F6; border-radius: 3px; margin-right: 5px;"></div>
            <span style="font-size: 14px;">A-Roll Segments</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #FF9800; border-radius: 3px; margin-right: 5px;"></div>
            <span style="font-size: 14px;">B-Roll Segments</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #4CAF50; border-radius: 3px; margin-right: 5px;"></div>
            <span style="font-size: 14px;">Sequence Flow</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Main function
def main():
    st.title("A-Roll Transcription & Segmentation")
    
    # Check if transcription data already exists
    if not st.session_state.transcription_complete:
        load_transcription_data()
    
    # Check if A-roll segments already exist
    if not st.session_state.segmentation_complete:
        load_a_roll_segments()
    
    # Check for Ollama availability
    try:
        st.session_state.ollama_available = check_ollama_availability()
        if st.session_state.ollama_available:
            st.session_state.ollama_models = get_available_models()
            # Set default model if it's available, otherwise use the first available model
            if DEFAULT_MODEL in st.session_state.ollama_models:
                st.session_state.selected_ollama_model = DEFAULT_MODEL
            elif st.session_state.ollama_models:
                st.session_state.selected_ollama_model = st.session_state.ollama_models[0]
    except Exception as e:
        print(f"Error checking Ollama availability: {str(e)}")
        st.session_state.ollama_available = False
    
    # Initialize session state variables for B-Roll generation strategy if not already set
    if "broll_generation_strategy" not in st.session_state:
        st.session_state.broll_generation_strategy = "balanced"
    
    # Step 1: Upload video
    st.header("Step 1: Upload A-Roll Video")
    
    uploaded_file = st.file_uploader("Upload your A-Roll video", type=["mp4", "mov", "avi", "mkv"])
    
    if uploaded_file is not None:
        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            video_path = tmp_file.name
            st.session_state.uploaded_video = video_path
        
        st.success(f"Video uploaded successfully: {uploaded_file.name}")
        
        # Display the uploaded video
        st.video(uploaded_file)
    
    # Step 2: Transcribe video
    st.header("Step 2: Transcribe Video")
    
    # Check available transcription engines
    available_engines = get_available_engines()
    
    if not available_engines:
        st.warning("No transcription engines available. Please install Whisper or Faster-Whisper.")
        
        if st.button("Install Whisper"):
            with st.spinner("Installing Whisper..."):
                os.system(f"{sys.executable} -m pip install openai-whisper")
                st.success("Whisper installed successfully. Please refresh the page.")
                st.experimental_rerun()
    else:
        # Transcription options
        col1, col2 = st.columns(2)
        
        with col1:
            engine = st.selectbox(
                "Transcription Engine",
                options=["auto"] + available_engines,
                index=0,
                help="Select the transcription engine to use"
            )
        
        with col2:
            model_size = st.selectbox(
                "Model Size",
                options=["tiny", "base", "small", "medium", "large"],
                index=1,  # Default to "base"
                help="Larger models are more accurate but require more processing time and resources"
            )
        
        # Transcription button
        if st.button("Transcribe Video", disabled=not st.session_state.uploaded_video and not st.session_state.transcription_complete):
            if st.session_state.uploaded_video:
                with st.spinner("Transcribing video..."):
                    # Transcribe the video
                    result = transcribe_video(
                        st.session_state.uploaded_video,
                        engine=engine,
                        model_size=model_size
                    )
                    
                    if result["status"] == "success":
                        st.session_state.transcription_data = result
                        st.session_state.transcription_complete = True
                        
                        # Save the transcription data
                        save_transcription_data(result)
                        
                        st.success("Transcription complete!")
                        st.experimental_rerun()
                    else:
                        st.error(f"Transcription failed: {result.get('message', 'Unknown error')}")
            else:
                st.warning("Please upload a video first")
    
    # Step 3: Review and edit transcription
    if st.session_state.transcription_complete and st.session_state.transcription_data:
        st.header("Step 3: Review Transcription")
        
        transcription = st.session_state.transcription_data
        full_text = transcription.get("text", "")
        
        st.subheader("Full Transcription")
        edited_text = st.text_area("Edit if needed", full_text, height=200)
        
        if edited_text != full_text:
            # Update the transcription text
            st.session_state.transcription_data["text"] = edited_text
            
            if st.button("Save Edited Transcription"):
                save_transcription_data(st.session_state.transcription_data)
                st.success("Transcription updated!")
        
        # Step 4: Segment transcription
        st.header("Step 4: Segment Transcription")
        
        # Segmentation options
        col1, col2 = st.columns(2)
        
        with col1:
            min_segment_duration = st.slider(
                "Minimum Segment Duration (seconds)",
                min_value=3.0,
                max_value=10.0,
                value=5.0,
                step=0.5,
                help="Minimum duration for each segment"
            )
        
        with col2:
            max_segment_duration = st.slider(
                "Maximum Segment Duration (seconds)",
                min_value=min_segment_duration,
                max_value=10.0,
                value=min_segment_duration,
                step=0.5,
                help="Maximum duration for each segment"
            )
        
        # Segmentation button
        if st.button("Segment Transcription"):
            with st.spinner("Segmenting transcription..."):
                # Segment the transcription
                segments = segment_transcription(
                    st.session_state.transcription_data,
                    min_segment_duration=min_segment_duration,
                    max_segment_duration=max_segment_duration
                )
                
                if segments:
                    st.session_state.a_roll_segments = segments
                    st.session_state.segmentation_complete = True
                    
                    # Save the A-Roll segments
                    save_a_roll_segments(segments)
                    
                    st.success("Segmentation complete!")
                    st.experimental_rerun()
                else:
                    st.error("Segmentation failed!")
        
        # Step 5: Adjust segmentation and B-Roll generation
        if st.session_state.segmentation_complete:
            st.header("Step 5: Review and Adjust Segments")
            
            # Display the timeline visualization
            st.subheader("A-Roll Timeline")
            display_timeline_visualization(st.session_state.a_roll_segments)
            
            # Display segments for review/editing
            st.subheader("A-Roll Segments")
            
            segments = st.session_state.a_roll_segments
            
            for i, segment in enumerate(segments):
                with st.expander(f"Segment {i+1}: {format_time(segment.get('start_time', 0))} - {format_time(segment.get('end_time', 0))}"):
                    # Display segment content
                    new_content = st.text_area(
                        f"Segment {i+1} Content",
                        value=segment.get("content", ""),
                        key=f"segment_{i}"
                    )
                    
                    # Update the segment if content has changed
                    if new_content != segment.get("content", ""):
                        if st.button(f"Update Segment {i+1}", key=f"update_{i}"):
                            update_segment_content(i, new_content)
                            st.success(f"Segment {i+1} updated!")
                            st.experimental_rerun()
            
            # Step 6: B-Roll generation
            st.header("Step 6: Generate B-Roll")
            
            with st.expander("B-Roll Generation Options", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    strategy_options = {
                        "balanced": "Balanced (recommended)",
                        "minimal": "Minimal (intro/outro only)",
                        "maximum": "Maximum (every segment)"
                    }
                    
                    selected_strategy = st.selectbox(
                        "B-Roll Placement Strategy",
                        options=list(strategy_options.keys()),
                        index=list(strategy_options.keys()).index(st.session_state.broll_generation_strategy),
                        format_func=lambda x: strategy_options[x],
                        help="Choose how B-Roll segments are placed: 'minimal' (intro/outro only), 'balanced' (approx. 1 B-Roll per 2 A-Roll), or 'maximum' (B-Roll for every A-Roll)"
                    )
                    
                    st.session_state.broll_generation_strategy = selected_strategy
                
                with col2:
                    theme = st.text_input("Video Theme", st.session_state.script_theme or "educational video")
                
                # Add A-Roll/B-Roll split ratio control
                if "aroll_percentage" not in st.session_state:
                    st.session_state.aroll_percentage = 0.6  # Default to 60/40 split
                
                st.markdown("### A-Roll/B-Roll Split Ratio")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    aroll_percentage = st.slider(
                        "A-Roll Percentage",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state.aroll_percentage,
                        step=0.1,
                        format="%d%%",
                        help="For B-Roll segments, what percentage of time should show only A-Roll before switching to B-Roll overlay (0.6 = 60% A-Roll, 40% B-Roll)"
                    )
                    st.session_state.aroll_percentage = aroll_percentage
                
                with col2:
                    st.markdown(f"<div style='margin-top: 30px;'><b>Split: {int(aroll_percentage*100)}% / {int((1-aroll_percentage)*100)}%</b></div>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
                    <b>Visual Transition:</b> Each B-Roll segment will start with {int(aroll_percentage*100)}% A-Roll only, 
                    then transition to B-Roll visuals with A-Roll audio for the remaining {int((1-aroll_percentage)*100)}% of the segment duration.
                </div>
                """, unsafe_allow_html=True)
                
                # Add Ollama integration UI if available
                if st.session_state.ollama_available:
                    st.success("✅ Ollama AI is available for enhanced B-Roll prompts")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.session_state.use_ollama_prompts = st.checkbox(
                            "Use Ollama for B-Roll Prompts", 
                            value=st.session_state.use_ollama_prompts,
                            help="Generate better B-Roll prompts using Ollama AI"
                        )
                    
                    with col2:
                        if st.session_state.use_ollama_prompts:
                            model_options = st.session_state.ollama_models
                            if model_options:
                                # Find the index of the selected model in the list
                                selected_index = 0
                                if st.session_state.selected_ollama_model in model_options:
                                    selected_index = model_options.index(st.session_state.selected_ollama_model)
                                
                                st.session_state.selected_ollama_model = st.selectbox(
                                    "Ollama Model",
                                    model_options,
                                    index=selected_index,
                                    help="Select the Ollama model to use for generating B-Roll prompts"
                                )
                
                    if st.session_state.use_ollama_prompts:
                        st.info("The selected Ollama model will be used to generate detailed B-Roll prompts that accurately represent what's being spoken in each A-Roll segment.")
                else:
                    st.warning("⚠️ Ollama AI is not available. Simple B-Roll prompts will be used.")
            
            # Generate B-Roll button
            if st.button("Generate B-Roll Segments"):
                with st.spinner("Generating B-Roll segments..."):
                    # Generate B-Roll segments
                    b_roll_segments = generate_broll_segments(
                        st.session_state.a_roll_segments,
                        theme,
                        strategy=st.session_state.broll_generation_strategy
                    )
                    
                    if b_roll_segments:
                        st.session_state.b_roll_segments = b_roll_segments
                        
                        # Save the segments
                        save_segments(
                            st.session_state.a_roll_segments,
                            b_roll_segments,
                            theme,
                            aroll_percentage=st.session_state.aroll_percentage
                        )
                        
                        st.success("B-Roll segments generated!")
                        st.experimental_rerun()
                    else:
                        st.error("B-Roll generation failed!")
            
            # Display B-Roll segments if available
            if hasattr(st.session_state, "b_roll_segments") and st.session_state.b_roll_segments:
                st.subheader("B-Roll Segments")
                
                # Display the timeline with B-Roll overlay
                display_timeline_visualization(st.session_state.a_roll_segments, st.session_state.b_roll_segments)
                
                # Display B-Roll details
                for i, segment in enumerate(st.session_state.b_roll_segments):
                    with st.expander(f"B-Roll {i+1}: {segment.get('content', '')[:50]}{'...' if len(segment.get('content', '')) > 50 else ''}"):
                        st.markdown(f"**Content:** {segment.get('content', '')}")
                        st.markdown(f"**Timestamp:** {format_time(segment.get('timestamp', 0))}")
                        st.markdown(f"**Duration:** {segment.get('duration', 3.0):.1f} seconds")
                        
                        # Display mapped A-Roll segment if available
                        mapped_index = segment.get("mapped_aroll_index")
                        if mapped_index is not None and 0 <= mapped_index < len(st.session_state.a_roll_segments):
                            mapped_segment = st.session_state.a_roll_segments[mapped_index]
                            st.markdown(f"**Mapped to A-Roll:** Segment {mapped_index + 1} ({format_time(mapped_segment.get('start_time', 0))} - {format_time(mapped_segment.get('end_time', 0))})")
                        
                        # Display visuals if available
                        visuals = segment.get("visuals", [])
                        if visuals:
                            st.markdown("**Visuals:**")
                            for j, visual in enumerate(visuals):
                                st.markdown(f"  - Visual {j+1}: {visual.get('content', '')} (Duration: {visual.get('duration', 0):.1f}s)")
                
                # Add explanation of the new sequence structure
                st.subheader("Assembly Sequence")
                
                st.markdown("""
                The video will be assembled in the following sequence:
                
                **A-1**  
                *A-Roll video*  
                *A-Roll audio*
                
                **B-1 + A-2**  
                *B-Roll video*  
                *A-Roll audio*
                
                **B-2 + A-3**  
                *B-Roll video*  
                *A-Roll audio*
                
                **B-3 + A-4**  
                *B-Roll video*  
                *A-Roll audio*
                """)
                
                st.markdown("**Detailed Sequence:**")
                
                # First sequence (A-Roll only)
                if len(st.session_state.a_roll_segments) > 0:
                    st.markdown(f"1. A-Roll Segment 1 (full video and audio)")
                
                # Subsequent sequences (B-Roll video + A-Roll audio)
                for i in range(1, len(st.session_state.a_roll_segments)):
                    if i-1 < len(st.session_state.b_roll_segments):
                        st.markdown(f"{i+1}. B-Roll Segment {i} visuals + A-Roll Segment {i+1} audio")

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

if __name__ == "__main__":
    main() 