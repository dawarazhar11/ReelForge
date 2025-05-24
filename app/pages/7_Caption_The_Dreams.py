#!/usr/bin/env python3
"""
Page for adding animated word-by-word captions to videos
"""
import os
import sys
import time
import json
import traceback
from pathlib import Path
import streamlit as st

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    from components.progress import render_step_header
    from utils.session_state import mark_step_complete
    from components.navigation import render_workflow_navigation, render_step_navigation
    from utils.video.captions import (
        check_dependencies, 
        add_captions_to_video, 
        get_available_caption_styles,
        CAPTION_STYLES
    )
    from utils.audio.transcription import (
        transcribe_video,
        get_available_engines
    )
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Please make sure you're running this from the project root directory.")
    st.stop()

# Set page config
st.set_page_config(
    page_title="Caption The Dreams - AI Money Printer Shorts",
    page_icon="✨",
    layout="wide"
)

# Initialize session state for this page
if "caption_dreams" not in st.session_state:
    st.session_state.caption_dreams = {
        "status": "not_started",
        "source_video": None,
        "output_path": None,
        "selected_style": "tiktok",
        "model_size": "base",
        "transcription_engine": "whisper",
        "animation_style": "word_by_word",
        "error": None
    }

# Define dream animation styles
DREAM_ANIMATION_STYLES = {
    "word_by_word": {
        "name": "Word by Word",
        "description": "Words appear one by one as they are spoken"
    },
    "fade_in_out": {
        "name": "Fade In/Out",
        "description": "Words fade in as they are spoken and fade out after"
    },
    "scale_pulse": {
        "name": "Scale Pulse",
        "description": "Words scale up when spoken for emphasis"
    },
    "color_highlight": {
        "name": "Color Highlight",
        "description": "Current words are highlighted with a different color"
    }
}

# Main function
def main():
    # Header and navigation
    render_step_header("Caption The Dreams", "Add animated word-by-word captions to your video")
    render_workflow_navigation()
    
    # Introduction
    st.markdown("""
    # ✨ Caption The Dreams
    
    Add beautiful animated captions that map each word precisely to the spoken audio.
    The captions will animate word-by-word to create an engaging viewer experience!
    """)
    
    # Check dependencies
    dep_check = check_dependencies()
    if not dep_check["all_available"]:
        st.error(f"Missing dependencies: {', '.join(dep_check['missing'])}")
        st.info("Please install the required dependencies to use this feature.")
        
        if st.button("Install Dependencies"):
            # Import and run the dependency installer
            try:
                from utils.video.dependencies import install_dependencies
                with st.spinner("Installing dependencies..."):
                    result = install_dependencies()
                    if result["success"]:
                        st.success("Dependencies installed successfully! Please refresh the page.")
                    else:
                        st.error(f"Failed to install dependencies: {result['message']}")
            except Exception as e:
                st.error(f"Error running dependency installer: {str(e)}")
        return
    
    # Display the video selection panel
    st.markdown("## Step 1: Select the Video")
    
    # Option to use the previously assembled video or upload a custom one
    video_source = st.radio(
        "Video Source:",
        ["Use Assembled Video", "Upload Custom Video"],
        key="video_source"
    )
    
    if video_source == "Use Assembled Video":
        # Check for assembled video from previous step
        if "video_assembly" in st.session_state and st.session_state.video_assembly.get("output_path"):
            assembled_video_path = st.session_state.video_assembly["output_path"]
            if os.path.exists(assembled_video_path):
                st.session_state.caption_dreams["source_video"] = assembled_video_path
                st.success(f"Using assembled video: {os.path.basename(assembled_video_path)}")
                
                # Display the video
                st.video(assembled_video_path)
            else:
                st.error("The assembled video file no longer exists. Please choose another option.")
                st.session_state.caption_dreams["source_video"] = None
        else:
            st.warning("No assembled video found. Please go to the Video Assembly page first or upload a custom video.")
            st.session_state.caption_dreams["source_video"] = None
    else:
        # Upload custom video
        uploaded_file = st.file_uploader("Upload your video file:", type=["mp4", "mov", "avi", "mkv"])
        if uploaded_file:
            # Save the uploaded file to a temporary location
            os.makedirs("output", exist_ok=True)
            temp_path = os.path.join("output", f"uploaded_{int(time.time())}.mp4")
            
            try:
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Verify the file was written successfully
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    st.session_state.caption_dreams["source_video"] = temp_path
                    st.success(f"Video uploaded successfully: {os.path.basename(temp_path)}")
                    
                    # Display the video
                    st.video(temp_path)
                else:
                    st.error("Failed to save uploaded video. The file may be empty or corrupted.")
            except Exception as e:
                st.error(f"Error saving uploaded video: {str(e)}")
                st.session_state.caption_dreams["source_video"] = None
    
    # Display the caption style selection
    if st.session_state.caption_dreams["source_video"]:
        st.markdown("## Step 2: Configure Caption Settings")
        
        # Create columns for settings
        col1, col2 = st.columns(2)
        
        with col1:
            # Caption style selection
            st.subheader("Caption Base Style")
            # Get available caption styles
            styles = get_available_caption_styles()
            
            selected_style = st.selectbox(
                "Base Style:",
                list(styles.keys()),
                index=list(styles.keys()).index(st.session_state.caption_dreams.get("selected_style", "tiktok")),
                format_func=lambda x: styles[x] if x in styles else x.replace("_", " ").title(),
                key="style_select"
            )
            st.session_state.caption_dreams["selected_style"] = selected_style
            
            # Animation style selection
            st.subheader("Word Animation Style")
            # Filter out the problematic scale_pulse style
            available_animation_styles = {k: v for k, v in DREAM_ANIMATION_STYLES.items() if k != "scale_pulse"}
            selected_animation = st.selectbox(
                "Animation Type:",
                list(available_animation_styles.keys()),
                index=list(available_animation_styles.keys()).index(
                    st.session_state.caption_dreams.get("animation_style", "word_by_word")
                ),
                format_func=lambda x: available_animation_styles[x]["name"],
                key="animation_select"
            )
            st.session_state.caption_dreams["animation_style"] = selected_animation
            
            # Display description
            st.info(available_animation_styles[selected_animation]["description"])
        
        with col2:
            # Transcription engine selection
            st.subheader("Speech Recognition Engine")
            
            # Get available engines
            available_engines = ["auto"] + get_available_engines()
            
            engine = st.selectbox(
                "Transcription Engine:",
                available_engines,
                index=available_engines.index(
                    st.session_state.caption_dreams.get("transcription_engine", "auto")
                ),
                key="engine_select"
            )
            st.session_state.caption_dreams["transcription_engine"] = engine
            
            if engine == "auto":
                st.info("Auto will choose the best available engine (Whisper preferred if available).")
            elif engine == "whisper":
                # For Whisper, allow model size selection
                model_sizes = ["tiny", "base", "small", "medium", "large"]
                model_size = st.selectbox(
                    "Whisper Model Size:",
                    model_sizes,
                    index=model_sizes.index(
                        st.session_state.caption_dreams.get("model_size", "base")
                    ),
                    key="model_size_select"
                )
                st.session_state.caption_dreams["model_size"] = model_size
                
                st.info("Larger models are more accurate but require more processing time and memory.")
            elif engine == "faster_whisper":
                # For Faster Whisper, allow model size selection
                model_sizes = ["tiny", "base", "small", "medium", "large"]
                model_size = st.selectbox(
                    "Faster Whisper Model Size:",
                    model_sizes,
                    index=model_sizes.index(
                        st.session_state.caption_dreams.get("model_size", "base")
                    ),
                    key="model_size_select"
                )
                st.session_state.caption_dreams["model_size"] = model_size
                
                st.info("Faster-Whisper provides similar accuracy to Whisper with improved processing speed.")
            elif engine == "vosk":
                st.info("Vosk is a lightweight speech recognition engine that works offline.")
        
        # Display the caption generation section
        st.markdown("## Step 3: Generate Animated Captions")
        
        # Output file path
        output_filename = f"captioned_{os.path.basename(st.session_state.caption_dreams['source_video'])}"
        output_path = os.path.join("output", output_filename)
        st.session_state.caption_dreams["output_path"] = output_path
        
        # Create a column layout for buttons
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Generate captions button
            if st.button("✨ Generate Animated Captions", key="generate_btn", use_container_width=True):
                try:
                    # Start the caption generation process
                    st.session_state.caption_dreams["status"] = "processing"
                    
                    # Create a progress bar
                    progress = st.progress(0)
                    status_text = st.empty()
                    
                    # Define a callback for progress updates
                    def update_progress(progress_value, message):
                        progress.progress(progress_value)
                        status_text.text(message)
                    
                    # Update initial status
                    update_progress(0.1, "Preparing to process video...")
                    
                    # Call the captioning function
                    result = add_captions_to_video(
                        st.session_state.caption_dreams["source_video"],
                        output_path=output_path,
                        style_name=selected_style,
                        model_size=st.session_state.caption_dreams.get("model_size", "base"),
                        engine="whisper",  # Always use whisper explicitly
                        animation_style=st.session_state.caption_dreams.get("animation_style", "word_by_word"),
                        progress_callback=update_progress
                    )
                    
                    # Check result
                    if result.get("status") == "success":
                        st.session_state.caption_dreams["status"] = "completed"
                        mark_step_complete("caption_dreams")
                        
                        # Clear progress indicators
                        progress.empty()
                        status_text.empty()
                        
                        st.success("✅ Captions generated successfully!")
                    else:
                        st.session_state.caption_dreams["status"] = "error"
                        st.session_state.caption_dreams["error"] = result.get("message", "Unknown error")
                        
                        # Clear progress indicators
                        progress.empty()
                        status_text.empty()
                        
                        st.error(f"❌ Error generating captions: {result.get('message', 'Unknown error')}")
                        
                        # If there's a detailed traceback, show it in an expander
                        if "traceback" in result:
                            with st.expander("View Error Details"):
                                st.code(result["traceback"], language="python")
                except Exception as e:
                    st.session_state.caption_dreams["status"] = "error"
                    st.session_state.caption_dreams["error"] = str(e)
                    st.error(f"❌ Error: {str(e)}")
                    
                    # If there's a traceback, show it in an expander
                    with st.expander("View Error Details"):
                        st.code(traceback.format_exc(), language="python")
        
        # Display the output video if available
        if st.session_state.caption_dreams["status"] == "completed" and os.path.exists(output_path):
            st.markdown("## Output Video with Animated Captions")
            st.video(output_path)
            
            # Provide download link
            with open(output_path, "rb") as file:
                st.download_button(
                    label="Download Captioned Video",
                    data=file,
                    file_name=output_filename,
                    mime="video/mp4",
                    key="download_btn"
                )
            
            # Mark this step as complete in the workflow
            mark_step_complete("caption_dreams")

# Run the main function
if __name__ == "__main__":
    main() 