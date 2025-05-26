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
import numpy as np
from PIL import Image
from datetime import datetime
import base64

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
    },
    "single_word_focus": {
        "name": "Single Word Focus",
        "description": "Only shows the current word being spoken with emphasis"
    }
}

# Add helper function to get a video data URL for embedding
def get_video_data_url(file_path):
    """Create a data URL for a video to embed it directly in the page"""
    try:
        with open(file_path, 'rb') as f:
            video_bytes = f.read()
        b64_video = base64.b64encode(video_bytes).decode()
        return f"data:video/mp4;base64,{b64_video}"
    except Exception as e:
        print(f"Error creating data URL: {e}")
        return None

# Add helper function to create a temporary HTML file with the video
def create_html_video_player(file_path):
    """Create a temporary HTML file with the video and return the path"""
    try:
        temp_html_path = os.path.join(os.path.dirname(file_path), "temp_video_player.html")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Video Player</title>
            <style>
                body {{ margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }}
                video {{ max-width: 100%; max-height: 90vh; }}
            </style>
        </head>
        <body>
            <video controls autoplay>
                <source src="file://{file_path}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </body>
        </html>
        """
        
        with open(temp_html_path, "w") as f:
            f.write(html_content)
            
        return temp_html_path
    except Exception as e:
        print(f"Error creating HTML player: {e}")
        return None

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
            
            # Add Caption Customization Options in an expander
            with st.expander("Caption Customization", expanded=True):
                # Font size customization
                font_size = st.slider(
                    "Font Size:", 
                    min_value=20, 
                    max_value=80, 
                    value=st.session_state.caption_dreams.get("font_size", 40),
                    step=2,
                    help="Adjust the size of the caption text"
                )
                st.session_state.caption_dreams["font_size"] = font_size
                
                # Add an option to force captions even if no speech is detected
                force_captions = st.checkbox(
                    "Force captions if no speech detected",
                    value=st.session_state.caption_dreams.get("force_captions", False),
                    help="Generate captions even if no speech is detected in the video"
                )
                st.session_state.caption_dreams["force_captions"] = force_captions
                
                # Show default caption input if force captions is enabled
                if force_captions:
                    default_caption = st.text_input(
                        "Default Caption:",
                        value=st.session_state.caption_dreams.get("default_caption", "No speech detected"),
                        help="Text to display if no speech is detected"
                    )
                    st.session_state.caption_dreams["default_caption"] = default_caption
                
                # Position type selection
                position_type = st.radio(
                    "Caption Position:",
                    ["Bottom", "Custom Position"],
                    index=0 if st.session_state.caption_dreams.get("position_type", "bottom") == "bottom" else 1,
                    help="Choose where to place captions"
                )
                st.session_state.caption_dreams["position_type"] = position_type.lower().replace(" ", "_")
                
                # Show custom position controls if custom position is selected
                if position_type == "Custom Position":
                    # Vertical position (top to bottom)
                    vertical_pos = st.slider(
                        "Vertical Position:", 
                        min_value=0, 
                        max_value=100, 
                        value=st.session_state.caption_dreams.get("vertical_pos", 80),
                        help="Position from top (0) to bottom (100)"
                    )
                    st.session_state.caption_dreams["vertical_pos"] = vertical_pos
                    
                    # Horizontal position (left to right)
                    horizontal_pos = st.slider(
                        "Horizontal Position:", 
                        min_value=0, 
                        max_value=100, 
                        value=st.session_state.caption_dreams.get("horizontal_pos", 50),
                        help="Position from left (0) to right (100)"
                    )
                    st.session_state.caption_dreams["horizontal_pos"] = horizontal_pos
                
                # Text alignment options
                text_align = st.radio(
                    "Text Alignment:",
                    ["Left", "Center", "Right"],
                    index=["left", "center", "right"].index(
                        st.session_state.caption_dreams.get("text_align", "center")
                    ),
                    help="Set how the text is aligned"
                )
                st.session_state.caption_dreams["text_align"] = text_align.lower()
                
                # Option to show textbox background
                show_textbox = st.checkbox(
                    "Show Text Box Background", 
                    value=st.session_state.caption_dreams.get("show_textbox", False),
                    help="Add a background box behind the text for better visibility"
                )
                st.session_state.caption_dreams["show_textbox"] = show_textbox
                
                # Textbox background opacity if showing textbox
                if show_textbox:
                    bg_opacity = st.slider(
                        "Background Opacity:", 
                        min_value=0, 
                        max_value=100, 
                        value=st.session_state.caption_dreams.get("bg_opacity", 70),
                        help="Control the opacity of the background box"
                    )
                    st.session_state.caption_dreams["bg_opacity"] = bg_opacity
        
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
                
                st.info("Model size comparison (Mac performance):")
                st.markdown("""
                - **tiny**: Fastest (1-2x realtime on M1/M2), less accurate
                - **base**: Good balance (1-1.5x realtime on M1/M2)
                - **small**: More accurate, slower (0.5x realtime)
                - **medium**: High accuracy, much slower
                - **large**: Best accuracy, very slow (not recommended on most Macs)
                """)
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
                
                st.info("Faster-Whisper provides similar accuracy to Whisper with improved processing speed on Mac.")
                st.markdown("""
                ℹ️ Recommended for M1/M2 Mac users. Uses GPU acceleration when available.
                - **tiny/base**: 2-3x faster than standard Whisper
                - **small/medium**: Good balance for Mac users
                """)
            elif engine == "vosk":
                st.info("Vosk is a lightweight offline speech recognition engine.")
                st.markdown("""
                ℹ️ Advantages for Mac users:
                - Much faster than Whisper (5-10x realtime)
                - Lower memory usage
                - Works entirely offline
                - Good for longer videos
                
                Note: May be less accurate than Whisper for some accents or noisy audio.
                """)
            
            # Add information about other options for Mac users
            with st.expander("Additional Options for Mac Users"):
                st.markdown("""
                ### Other Transcription Options for Mac Users
                
                If you're experiencing issues with word timing or accuracy:
                
                1. **Apple Speech Framework** (via a Python wrapper)
                   - Natively optimized for Mac
                   - Very fast on M1/M2 chips
                   - Requires additional setup
                
                2. **Assembly AI** or **Deepgram** APIs
                   - Cloud-based, high accuracy
                   - Requires API key (paid service)
                   - Often provides superior word-level timing
                
                3. **Improving Whisper Performance on Mac**:
                   - Use "tiny" or "base" models for faster processing
                   - Close other applications to free up memory
                   - Run on Apple Silicon Macs (M1/M2) when possible
                   - Consider using faster-whisper with appropriate compute type
                """)
        
        # Display the caption generation section
        st.markdown("## Step 3: Generate Animated Captions")
        
        # Add Live Preview section
        st.markdown("### 🔍 Live Caption Preview")
        st.info("See how your captions will look before generating the final video. This preview shows captions in a 9:16 ratio format.")
        
        # Create tabs for preview and generation
        preview_tab, generate_tab = st.tabs(["Preview Captions", "Generate Final Video"])
        
        with preview_tab:
            # Create a preview frame (black background with 9:16 ratio)
            if "preview_frame" not in st.session_state:
                # Create a blank 9:16 frame
                preview_width, preview_height = 540, 960  # 9:16 ratio, half resolution for performance
                preview_frame = np.zeros((preview_height, preview_width, 3), dtype=np.uint8)
                
                # Try to extract an actual frame from the video if possible
                try:
                    import moviepy.editor as mp
                    video = mp.VideoFileClip(st.session_state.caption_dreams["source_video"])
                    if video.duration > 1.0:
                        # Get a frame from 1 second in
                        frame = video.get_frame(1.0)
                        # Resize to 9:16 with pillow for better quality
                        pil_frame = Image.fromarray(frame)
                        # Resize while maintaining aspect ratio and adding black bars if needed
                        target_ratio = preview_width / preview_height
                        img_ratio = pil_frame.width / pil_frame.height
                        
                        if img_ratio > target_ratio:
                            # Image is wider than target, resize based on height
                            new_height = preview_height
                            new_width = int(new_height * img_ratio)
                            resized = pil_frame.resize((new_width, new_height), Image.LANCZOS)
                            # Crop to target width
                            crop_x = (new_width - preview_width) // 2
                            preview_frame = np.array(resized.crop((crop_x, 0, crop_x + preview_width, preview_height)))
                        else:
                            # Image is taller than target, resize based on width
                            new_width = preview_width
                            new_height = int(new_width / img_ratio)
                            resized = pil_frame.resize((new_width, new_height), Image.LANCZOS)
                            # Crop to target height
                            crop_y = (new_height - preview_height) // 2
                            preview_frame = np.array(resized.crop((0, crop_y, preview_width, crop_y + preview_height)))
                    
                    video.close()
                except Exception as e:
                    st.warning(f"Could not extract preview frame: {str(e)}")
                    preview_frame = np.zeros((preview_height, preview_width, 3), dtype=np.uint8)
                
                st.session_state.preview_frame = preview_frame
            
            # Sample text for preview
            preview_text = st.text_input(
                "Preview Text",
                value="This is a sample caption text to preview your style settings.",
                help="Enter text to preview with your caption settings"
            )
            
            # Generate sample word timings
            words = preview_text.split()
            preview_words = []
            for i, word in enumerate(words):
                # Create evenly spaced words
                start_time = i * 0.5
                end_time = start_time + 0.4
                preview_words.append({
                    "word": word,
                    "start": start_time,
                    "end": end_time
                })
            
            # Add a slider to control which word is "currently spoken"
            max_time = len(words) * 0.5 if words else 0.5
            preview_time = st.slider(
                "Time Position",
                min_value=0.0,
                max_value=max_time,
                value=min(1.0, max_time / 2),
                step=0.1,
                help="Move the slider to see different words highlighted based on time"
            )
            
            # Generate the preview with current settings
            try:
                # Create a custom style dictionary with current settings
                custom_style = {
                    "font_size": st.session_state.caption_dreams.get("font_size", 40),
                    "position": "custom" if st.session_state.caption_dreams.get("position_type") == "custom_position" else "bottom",
                    "vertical_pos": st.session_state.caption_dreams.get("vertical_pos", 80) / 100.0,
                    "horizontal_pos": st.session_state.caption_dreams.get("horizontal_pos", 50) / 100.0,
                    "align": st.session_state.caption_dreams.get("text_align", "center"),
                    "show_textbox": st.session_state.caption_dreams.get("show_textbox", False),
                    "textbox_opacity": st.session_state.caption_dreams.get("bg_opacity", 70) / 100.0,
                    "font_color": (255, 255, 255),  # White text
                    "stroke_width": 2,
                    "stroke_color": (0, 0, 0),  # Black outline
                    "bottom_margin": 50,
                    "force_captions_if_no_speech": st.session_state.caption_dreams.get("force_captions", False),
                    "default_caption": st.session_state.caption_dreams.get("default_caption", "No speech detected")
                }
                
                # Import the functions from the captions module
                from utils.video.captions import make_frame_with_text, get_caption_style
                
                # Merge the selected style with custom settings
                style = get_caption_style(st.session_state.caption_dreams.get("selected_style", "tiktok"))
                if style:
                    # Update style with custom settings
                    for key, value in custom_style.items():
                        style[key] = value
                else:
                    style = custom_style
                
                # Get the animation style
                animation_style = st.session_state.caption_dreams.get("animation_style", "word_by_word")
                
                # Print debug information
                print(f"Preview settings: Animation style: {animation_style}")
                print(f"Preview text: {preview_text}")
                print(f"Word count: {len(preview_words)}")
                print(f"Preview time: {preview_time}")
                
                # Add captions using the make_frame_with_text function that handles animation styles
                preview_frame = make_frame_with_text(
                    st.session_state.preview_frame.copy(),
                    preview_text,
                    preview_words,
                    preview_time,
                    style,  # Pass style dictionary directly
                    None,   # No additional effect params needed
                    animation_style  # Pass animation style
                )
                
                # Display the preview
                st.image(
                    preview_frame,
                    caption="Caption Preview (9:16 Ratio)",
                    use_column_width=True
                )
                
                # Add a note about the preview
                st.info("This is a simulation of how your captions will appear in the final video. The actual results may vary slightly based on your video content and resolution.")
                
            except Exception as e:
                st.error(f"Error generating preview: {str(e)}")
                st.code(traceback.format_exc())
        
        with generate_tab:
            # Output file path
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            output_filename = f"captioned_{os.path.basename(st.session_state.caption_dreams['source_video'])}"
            output_path = os.path.join(output_dir, output_filename)
            st.session_state.caption_dreams["output_path"] = output_path
            
            # Put debug information in collapsible expander
            with st.expander("🔍 File Path Information", expanded=False):
                st.info(f"Output directory: {output_dir}")
                st.info(f"Directory exists: {os.path.exists(output_dir)}")
                st.info(f"Directory writable: {os.access(output_dir, os.W_OK)}")
            
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
                        
                        # Ensure output directory exists
                        output_dir = os.path.join(os.getcwd(), "output")
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Create output filename using the exact same timestamp as the uploaded file
                        output_filename = f"captioned_{os.path.basename(st.session_state.caption_dreams['source_video'])}"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        # Log important path information
                        print(f"Source video: {st.session_state.caption_dreams['source_video']}")
                        print(f"Generated output path: {output_path}")
                        print(f"Current working directory: {os.getcwd()}")
                        
                        # Update session state with the absolute path
                        output_path = os.path.abspath(output_path)
                        st.session_state.caption_dreams["output_path"] = output_path
                        print(f"Final absolute output path: {output_path}")
                        
                        # Create custom style with the user's customization options
                        custom_style = {
                            "font_size": st.session_state.caption_dreams.get("font_size", 40),
                            "position": "custom" if st.session_state.caption_dreams.get("position_type") == "custom_position" else "bottom",
                            "vertical_pos": st.session_state.caption_dreams.get("vertical_pos", 80) / 100.0,  # Convert to fraction
                            "horizontal_pos": st.session_state.caption_dreams.get("horizontal_pos", 50) / 100.0,  # Convert to fraction
                            "align": st.session_state.caption_dreams.get("text_align", "center"),
                            "show_textbox": st.session_state.caption_dreams.get("show_textbox", False),
                            "textbox_opacity": st.session_state.caption_dreams.get("bg_opacity", 70) / 100.0,  # Convert to fraction
                            "force_captions_if_no_speech": st.session_state.caption_dreams.get("force_captions", False),
                            "default_caption": st.session_state.caption_dreams.get("default_caption", "No speech detected")
                        }
                        
                        # Call the captioning function with customization options
                        result = add_captions_to_video(
                            st.session_state.caption_dreams["source_video"],
                            output_path=output_path,
                            style_name=st.session_state.caption_dreams.get("selected_style", "tiktok"),
                            model_size=st.session_state.caption_dreams.get("model_size", "base"),
                            engine=st.session_state.caption_dreams.get("transcription_engine", "auto"),
                            animation_style=st.session_state.caption_dreams.get("animation_style", "word_by_word"),
                            custom_style=custom_style,
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
                            
                            # Debug info
                            output_file = result.get("output_path", output_path)
                            
                            # Put technical details in a collapsible expander
                            with st.expander("🔧 Technical Details", expanded=False):
                                st.info(f"Output file path from result: {output_file}")
                                st.info(f"File exists: {os.path.exists(output_file)}")
                                st.info(f"File size: {os.path.getsize(output_file) if os.path.exists(output_file) else 'N/A'}")
                                st.info(f"Updated session state output path: {st.session_state.caption_dreams['output_path']}")
                                st.info(f"Session state status: {st.session_state.caption_dreams['status']}")
                            
                            # IMPORTANT: Update session state with the path returned from the function
                            # This is critical in case the backend used an alternative path
                            st.session_state.caption_dreams["output_path"] = output_file
                            
                            st.rerun()  # Rerun to show the video output
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
            if st.session_state.caption_dreams["status"] == "completed":
                output_path = st.session_state.caption_dreams.get("output_path")
                
                # Put debug info in a collapsible expander
                with st.expander("🔍 Debug Information (click to expand)", expanded=False):
                    st.info(f"Output video status: {'Completed' if st.session_state.caption_dreams['status'] == 'completed' else 'Not completed'}")
                    st.info(f"Output path: {output_path}")
                    st.info(f"Current working directory: {os.getcwd()}")
                    
                    # Make sure path is absolute
                    if output_path and not os.path.isabs(output_path):
                        absolute_path = os.path.abspath(output_path)
                        st.info(f"Absolute path: {absolute_path}")
                        output_path = absolute_path
                    
                    # Check if path exists, if not try to find a similar file
                    if output_path and not os.path.exists(output_path):
                        # Move this warning into the debug expander instead of showing in main UI
                        st.warning(f"Path does not exist: {output_path}")
                        
                        # Try to find files with similar names
                        try:
                            output_dir = os.path.dirname(output_path)
                            base_name = os.path.basename(output_path)
                            
                            if os.path.exists(output_dir):
                                files = os.listdir(output_dir)
                                # Don't use a nested expander - just show the file list directly
                                st.text("Files in output directory:")
                                st.code("\n".join(files), language=None)
                                
                                # Look for files with similar names (captioned_*)
                                similar_files = [f for f in files if f.startswith("captioned_")]
                                if similar_files:
                                    # Sort by creation time (newest first)
                                    similar_files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)), reverse=True)
                                    newest_file = similar_files[0]
                                    st.info(f"Found similar file: {newest_file}")
                                    
                                    # Use the newest similar file
                                    output_path = os.path.join(output_dir, newest_file)
                                    st.info(f"Using alternative file: {output_path}")
                        except Exception as e:
                            st.error(f"Error finding similar files: {e}")
                    
                    # Final check before display
                    st.info(f"Final path exists: {os.path.exists(output_path) if output_path else 'No path'}")
                    if output_path and os.path.exists(output_path):
                        st.info(f"File size: {os.path.getsize(output_path)} bytes")
                
                # Continue with normal display code
                if output_path and os.path.exists(output_path):
                    try:
                        # Get file size
                        file_size = os.path.getsize(output_path)
                        st.info(f"File size: {file_size} bytes")
                        
                        # Verify it's a valid video file
                        if file_size > 0:
                            st.markdown("## Output Video with Animated Captions")
                            
                            # Try multiple approaches to display the video
                            video_displayed = False
                            
                            # Approach 1: Default Streamlit video player
                            try:
                                st.video(output_path)
                                video_displayed = True
                            except Exception as e1:
                                st.warning(f"Default video player failed: {str(e1)}")
                                
                                # Approach 2: Use bytes
                                try:
                                    with open(output_path, "rb") as video_file:
                                        video_bytes = video_file.read()
                                        st.video(video_bytes)
                                        video_displayed = True
                                except Exception as e2:
                                    st.warning(f"Bytes-based video player failed: {str(e2)}")
                                    
                                    # Approach 3: Use data URL
                                    try:
                                        data_url = get_video_data_url(output_path)
                                        if data_url:
                                            st.markdown(f"""
                                            <video width="100%" controls>
                                              <source src="{data_url}" type="video/mp4">
                                              Your browser does not support the video tag.
                                            </video>
                                            """, unsafe_allow_html=True)
                                            video_displayed = True
                                    except Exception as e3:
                                        st.warning(f"Data URL video player failed: {str(e3)}")
                                        
                                        # Approach 4: Create HTML player file
                                        try:
                                            html_path = create_html_video_player(output_path)
                                            if html_path:
                                                st.markdown(f"📹 [Open Video in Browser](file://{html_path})")
                                                video_displayed = True
                                        except Exception as e4:
                                            st.warning(f"HTML player failed: {str(e4)}")
                        
                            # Provide download link regardless of display success
                            with open(output_path, "rb") as file:
                                st.download_button(
                                    label="⬇️ Download Captioned Video",
                                    data=file,
                                    file_name=os.path.basename(output_path),
                                    mime="video/mp4",
                                    key="download_btn"
                                )
                            
                            # If all display methods failed, show a message
                            if not video_displayed:
                                st.error("Could not display the video in the UI, but you can download it using the button above.")
                                st.info(f"Video file path: {output_path}")
                                
                                # Additional option - open directly
                                if st.button("🎬 Open Video in Default Video Player"):
                                    import subprocess
                                    import platform
                                    
                                    system = platform.system()
                                    try:
                                        if system == "Darwin":  # macOS
                                            subprocess.call(["open", output_path])
                                        elif system == "Windows":
                                            subprocess.call(["start", output_path], shell=True)
                                        else:  # Linux
                                            subprocess.call(["xdg-open", output_path])
                                        st.success("Video opened in external player")
                                    except Exception as e:
                                        st.error(f"Failed to open video: {e}")
                        
                            # Mark this step as complete in the workflow
                            mark_step_complete("caption_dreams")
                        else:
                            st.error("Output file exists but has zero size.")
                    except Exception as e:
                        st.error(f"Error displaying video: {str(e)}")
                        st.code(traceback.format_exc())
                else:
                    # Major fallback - scan the whole output directory for recent videos
                    st.warning(f"Output video file not found at: {output_path}")
                    
                    # Add a more user-friendly message
                    st.info("🔍 Looking for your recently generated videos...")
                    
                    # Try to list files in output directory to help debugging
                    try:
                        output_dir = os.path.dirname(output_path) if output_path else os.path.join(os.getcwd(), "output")
                        if os.path.exists(output_dir):
                            files = os.listdir(output_dir)
                            # Show files directly instead of using an expander
                            st.text("Files in output directory:")
                            st.code("\n".join(files), language=None)
                            
                            # Show most recent file info
                            if files:
                                files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)), reverse=True)
                                recent_file = files[0]
                                recent_path = os.path.join(output_dir, recent_file)
                                st.info(f"Most recent file: {recent_file}")
                                st.info(f"Created: {datetime.fromtimestamp(os.path.getctime(recent_path))}")
                                st.info(f"Size: {os.path.getsize(recent_path)} bytes")
                        else:
                            st.info(f"Output directory does not exist: {output_dir}")
                    except Exception as e:
                        st.error(f"Error listing output directory: {str(e)}")
                    
                    st.info("Try generating the video again.")

# Run the main function
if __name__ == "__main__":
    main() 