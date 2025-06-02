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
def segment_transcription(transcription, min_segment_duration=5, max_segment_duration=20):
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
        List of B-Roll segments
    """
    if not a_roll_segments:
        return []
    
    b_roll_segments = []
    
    # Determine number of B-Roll segments based on strategy
    if strategy == "minimal":
        # Minimal: Just intro and outro B-Roll
        target_count = 2
    elif strategy == "maximum":
        # Maximum: B-Roll between every A-Roll segment
        target_count = len(a_roll_segments) + 1
    else:
        # Balanced: Approximately 1 B-Roll for every 2 A-Roll segments
        target_count = max(2, len(a_roll_segments) // 2 + 1)
    
    # Always add intro B-Roll
    intro_broll = {
        "type": "B-Roll",
        "content": f"Introductory visual for {theme}",
        "duration": 3.0  # Default duration in seconds
    }
    b_roll_segments.append(intro_broll)
    
    # Add B-Roll segments between A-Roll segments based on strategy
    if strategy == "minimal":
        # Just add outro B-Roll
        outro_broll = {
            "type": "B-Roll",
            "content": f"Concluding visual for {theme}",
            "duration": 3.0
        }
        b_roll_segments.append(outro_broll)
    elif strategy == "maximum":
        # Add B-Roll after each A-Roll segment
        for i, segment in enumerate(a_roll_segments):
            content = segment["content"]
            summary = content[:50] + "..." if len(content) > 50 else content
            
            broll = {
                "type": "B-Roll",
                "content": f"Visual representation of: {summary}",
                "duration": 3.0,
                "related_aroll": i  # Index of related A-Roll segment
            }
            b_roll_segments.append(broll)
            
        # Add outro B-Roll
        outro_broll = {
            "type": "B-Roll",
            "content": f"Concluding visual for {theme}",
            "duration": 3.0
        }
        b_roll_segments.append(outro_broll)
    else:
        # Balanced approach: Add B-Roll at strategic points
        segments_per_broll = max(1, len(a_roll_segments) // (target_count - 1))
        
        for i in range(len(a_roll_segments)):
            if i > 0 and i % segments_per_broll == 0 and len(b_roll_segments) < target_count - 1:
                # Get content from surrounding A-Roll segments for context
                prev_content = a_roll_segments[i-1]["content"]
                current_content = a_roll_segments[i]["content"]
                
                # Create a summary from both segments
                combined = prev_content + " " + current_content
                summary = combined[:50] + "..." if len(combined) > 50 else combined
                
                broll = {
                    "type": "B-Roll",
                    "content": f"Visual representation of: {summary}",
                    "duration": 3.0,
                    "related_aroll": i  # Index of related A-Roll segment
                }
                b_roll_segments.append(broll)
        
        # Add outro B-Roll if we haven't reached target count
        if len(b_roll_segments) < target_count:
            outro_broll = {
                "type": "B-Roll",
                "content": f"Concluding visual for {theme}",
                "duration": 3.0
            }
            b_roll_segments.append(outro_broll)
    
    return b_roll_segments

# Function to save both A-Roll and B-Roll segments
def save_segments(a_roll_segments, b_roll_segments, theme):
    """Save both A-Roll and B-Roll segments to script.json"""
    script_file = project_path / "script.json"
    
    # Check if script.json already exists and load it
    existing_data = {}
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading existing script: {str(e)}")
    
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
    
    # Prepare data to save
    data = {
        "full_script": full_script,
        "segments": all_segments,
        "theme": theme,
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
        print(f"Saved segments to {script_file}")
        return True
    except IOError as e:
        print(f"Error saving segments: {str(e)}")
        return False

# Main function
def main():
    st.title("A-Roll Transcription & Segmentation")
    
    # Check if transcription data already exists
    if not st.session_state.transcription_complete:
        load_transcription_data()
    
    # Check if A-roll segments already exist
    if not st.session_state.segmentation_complete:
        load_a_roll_segments()
    
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
        
        # Step 4: Segment the transcription
        st.header("Step 4: Create A-Roll Segments")
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_duration = st.slider("Minimum Segment Duration (seconds)", 3, 10, 5)
        
        with col2:
            max_duration = st.slider("Maximum Segment Duration (seconds)", 10, 30, 20)
        
        if st.button("Generate A-Roll Segments"):
            with st.spinner("Generating segments..."):
                a_roll_segments = segment_transcription(
                    st.session_state.transcription_data,
                    min_segment_duration=min_duration,
                    max_segment_duration=max_duration
                )
                
                st.session_state.a_roll_segments = a_roll_segments
                st.session_state.segmentation_complete = True
                
                # Save the segments
                save_a_roll_segments(a_roll_segments)
                
                st.success(f"Created {len(a_roll_segments)} A-Roll segments!")
                st.experimental_rerun()
    
    # Step 5: Review and edit segments
    if st.session_state.segmentation_complete and st.session_state.a_roll_segments:
        st.header("Step 5: Review and Edit A-Roll Segments")
        
        # Ensure all segments have timing information
        st.session_state.a_roll_segments = ensure_segments_have_timing(st.session_state.a_roll_segments)
        
        # Display each segment with edit options
        for i, segment in enumerate(st.session_state.a_roll_segments):
            with st.container():
                st.markdown(f"""
                <div class="segment-container">
                    <div class="segment-header">
                        <h3>Segment {i+1}</h3>
                        <span class="timestamp">{format_time(segment.get('start_time', 0))} - {format_time(segment.get('end_time', 0))} ({segment.get('duration', 0):.1f}s)</span>
                    </div>
                    <div class="segment-content">
                        {segment['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Edit button for this segment
                if st.button(f"Edit Segment {i+1}", key=f"edit_btn_{i}"):
                    st.session_state.segment_edit_index = i
        
        # Edit dialog
        if st.session_state.segment_edit_index >= 0:
            segment = st.session_state.a_roll_segments[st.session_state.segment_edit_index]
            st.subheader(f"Editing Segment {st.session_state.segment_edit_index + 1}")
            
            new_content = st.text_area("Edit segment content", segment["content"], height=150, key=f"edit_area_{st.session_state.segment_edit_index}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Changes"):
                    update_segment_content(st.session_state.segment_edit_index, new_content)
                    save_a_roll_segments(st.session_state.a_roll_segments)
                    st.session_state.segment_edit_index = -1
                    st.success("Segment updated!")
                    st.experimental_rerun()
            
            with col2:
                if st.button("Cancel"):
                    st.session_state.segment_edit_index = -1
                    st.experimental_rerun()
        
        # Step 6: Theme and B-Roll Generation
        st.header("Step 6: Theme and B-Roll Generation")
        
        # Theme selection
        st.subheader("Select Content Theme")
        
        # Get current theme or default to empty
        current_theme = st.session_state.script_theme
        
        # Theme container with styling
        st.markdown("""
        <div class="theme-container">
            <h3>Content Theme</h3>
            <p>The theme will guide B-Roll generation and provide context for visuals.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Theme input
        theme_col1, theme_col2 = st.columns([3, 1])
        
        with theme_col1:
            # Provide some theme examples
            theme_examples = ["Technology Explainer", "Product Review", "Educational Content", 
                             "Travel Vlog", "Cooking Tutorial", "Fitness Guide", 
                             "Business Tips", "Gaming Highlights", "Fashion Trends"]
            
            selected_example = st.selectbox(
                "Choose a theme template or create your own below:",
                ["Custom"] + theme_examples,
                index=0
            )
            
            if selected_example != "Custom":
                st.session_state.script_theme = selected_example
        
        with theme_col2:
            # Button to clear theme
            if st.button("Clear Theme", key="clear_theme"):
                st.session_state.script_theme = ""
                st.experimental_rerun()
        
        # Custom theme input
        custom_theme = st.text_input(
            "Enter your content theme:",
            value=current_theme,
            help="This theme will guide B-Roll generation and provide context for visuals"
        )
        
        if custom_theme != current_theme:
            st.session_state.script_theme = custom_theme
        
        # B-Roll generation options
        st.subheader("B-Roll Generation Options")
        
        # B-Roll generation strategy
        strategy_options = {
            "minimal": "Minimal (Intro/Outro only)",
            "balanced": "Balanced (Strategic placement)",
            "maximum": "Maximum (Between all A-Roll segments)"
        }
        
        strategy = st.radio(
            "B-Roll Generation Strategy:",
            list(strategy_options.keys()),
            format_func=lambda x: strategy_options[x],
            index=list(strategy_options.keys()).index(st.session_state.broll_generation_strategy),
            help="Choose how many B-Roll segments to generate and where to place them"
        )
        
        if strategy != st.session_state.broll_generation_strategy:
            st.session_state.broll_generation_strategy = strategy
        
        # Preview B-Roll generation
        if st.button("Preview B-Roll Generation", key="preview_broll"):
            if not st.session_state.script_theme:
                st.warning("Please enter a content theme first.")
            else:
                # Generate B-Roll segments
                b_roll_segments = generate_broll_segments(
                    st.session_state.a_roll_segments,
                    st.session_state.script_theme,
                    st.session_state.broll_generation_strategy
                )
                
                # Store in session state for later use
                st.session_state.b_roll_segments = b_roll_segments
                
                # Show preview
                st.subheader("B-Roll Preview")
                st.success(f"Generated {len(b_roll_segments)} B-Roll segments")
                
                for i, segment in enumerate(b_roll_segments):
                    with st.container():
                        st.markdown(f"""
                        <div class="broll-segment-container">
                            <div class="segment-header">
                                <h3>B-Roll Segment {i+1}</h3>
                            </div>
                            <div class="broll-segment-content">
                                {segment['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Show B-Roll segments if they exist
        if "b_roll_segments" in st.session_state and st.session_state.b_roll_segments:
            st.subheader("Generated B-Roll Segments")
            
            # Show count of segments
            st.info(f"Generated {len(st.session_state.b_roll_segments)} B-Roll segments based on theme: **{st.session_state.script_theme}**")
            
            # Display each B-Roll segment
            for i, segment in enumerate(st.session_state.b_roll_segments):
                with st.container():
                    st.markdown(f"""
                    <div class="broll-segment-container">
                        <div class="segment-header">
                            <h3>B-Roll Segment {i+1}</h3>
                        </div>
                        <div class="broll-segment-content">
                            {segment['content']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Save both A-Roll and B-Roll segments
            if st.button("Save All Segments", type="primary", key="save_all_segments"):
                with st.spinner("Saving segments..."):
                    if save_segments(
                        st.session_state.a_roll_segments,
                        st.session_state.b_roll_segments,
                        st.session_state.script_theme
                    ):
                        st.success("All segments saved successfully!")
                    else:
                        st.error("Failed to save segments.")
        
        # Save and continue button
        st.markdown("---")
        if st.button("Save and Continue to B-Roll Prompts", type="primary"):
            # Check if we have B-Roll segments
            if "b_roll_segments" not in st.session_state or not st.session_state.b_roll_segments:
                # Generate B-Roll segments if not already done
                if not st.session_state.script_theme:
                    st.warning("Please enter a content theme and generate B-Roll segments first.")
                    st.stop()
                
                b_roll_segments = generate_broll_segments(
                    st.session_state.a_roll_segments,
                    st.session_state.script_theme,
                    st.session_state.broll_generation_strategy
                )
                
                st.session_state.b_roll_segments = b_roll_segments
            
            # Save all segments
            save_segments(
                st.session_state.a_roll_segments,
                st.session_state.b_roll_segments,
                st.session_state.script_theme
            )
            
            # Mark this step as complete
            mark_step_complete("a_roll_transcription")
            
            # Redirect to the B-Roll Prompts page
            st.success("All segments saved! Redirecting to B-Roll Prompts...")
            time.sleep(2)
            st.switch_page("pages/4_BRoll_Prompts.py")

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