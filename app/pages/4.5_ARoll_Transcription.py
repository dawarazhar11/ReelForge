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
if "uploaded_video" not in st.session_state:
    st.session_state.uploaded_video = None
if "transcription_complete" not in st.session_state:
    st.session_state.transcription_complete = False
if "segmentation_complete" not in st.session_state:
    st.session_state.segmentation_complete = False
if "segment_edit_index" not in st.session_state:
    st.session_state.segment_edit_index = -1

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
        "theme": existing_data.get("theme", ""),
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
                        st.session_state.a_roll_segments = segments
                        st.session_state.segmentation_complete = True
                        return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading A-roll segments: {str(e)}")
            return False
    return False

# Function to segment the transcription into A-roll segments
def segment_transcription(transcription, min_segment_duration=5, max_segment_duration=20):
    segments = transcription.get("segments", [])
    words = transcription.get("words", [])
    
    if not segments:
        return []
    
    # Calculate total duration
    total_duration = segments[-1]["end"]
    
    # Determine optimal number of segments based on total duration
    # Aim for segments between min_segment_duration and max_segment_duration seconds
    target_segments = max(3, int(total_duration / ((min_segment_duration + max_segment_duration) / 2)))
    
    # Try to find natural breaks in speech (pauses)
    pauses = []
    for i in range(1, len(segments)):
        pause_duration = segments[i]["start"] - segments[i-1]["end"]
        if pause_duration > 0.5:  # Consider pauses longer than 0.5 seconds
            pauses.append({
                "time": segments[i-1]["end"],
                "duration": pause_duration
            })
    
    # Sort pauses by duration (longest first)
    pauses.sort(key=lambda x: x["duration"], reverse=True)
    
    # Take the top N-1 pauses as segment boundaries (where N is target_segments)
    boundaries = []
    if len(pauses) >= target_segments - 1:
        for i in range(target_segments - 1):
            boundaries.append(pauses[i]["time"])
    else:
        # Not enough natural pauses, divide evenly
        segment_length = total_duration / target_segments
        for i in range(1, target_segments):
            boundaries.append(i * segment_length)
    
    # Sort boundaries by time
    boundaries.sort()
    
    # Create segments based on boundaries
    a_roll_segments = []
    start_time = 0
    
    for i, end_time in enumerate(boundaries):
        # Find all words in this time range
        segment_words = [w for w in words if w["start"] >= start_time and w["end"] <= end_time]
        
        # Create segment text from words
        segment_text = " ".join([w["word"] for w in segment_words])
        
        # Clean up the text
        segment_text = re.sub(r'\s+', ' ', segment_text).strip()
        
        a_roll_segments.append({
            "type": "A-Roll",
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "content": segment_text
        })
        
        start_time = end_time
    
    # Add the final segment
    final_words = [w for w in words if w["start"] >= start_time]
    final_text = " ".join([w["word"] for w in final_words])
    final_text = re.sub(r'\s+', ' ', final_text).strip()
    
    a_roll_segments.append({
        "type": "A-Roll",
        "start_time": start_time,
        "end_time": total_duration,
        "duration": total_duration - start_time,
        "content": final_text
    })
    
    return a_roll_segments

# Function to update segment content
def update_segment_content(index, new_content):
    if 0 <= index < len(st.session_state.a_roll_segments):
        st.session_state.a_roll_segments[index]["content"] = new_content
        return True
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
        
        # Display each segment with edit options
        for i, segment in enumerate(st.session_state.a_roll_segments):
            with st.container():
                st.markdown(f"""
                <div class="segment-container">
                    <div class="segment-header">
                        <h3>Segment {i+1}</h3>
                        <span class="timestamp">{format_time(segment['start_time'])} - {format_time(segment['end_time'])} ({segment['duration']:.1f}s)</span>
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
        
        # Save and continue button
        if st.button("Save and Continue to B-Roll Prompts"):
            # Mark this step as complete
            mark_step_complete("a_roll_transcription")
            
            # Save the segments one more time
            save_a_roll_segments(st.session_state.a_roll_segments)
            
            # Redirect to the B-Roll Prompts page
            st.success("A-Roll segments saved! Redirecting to B-Roll Prompts...")
            time.sleep(2)
            st.switch_page("4_BRoll_Prompts")

# Helper function to format time in MM:SS format
def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

if __name__ == "__main__":
    main() 