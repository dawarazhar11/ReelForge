import streamlit as st
import os
import json
import shutil
from pathlib import Path
import time

# Function to clear cache and reset session state
def clear_app_cache():
    """
    Clear the application cache and reset any leftover data from previous sessions.
    This ensures a clean state when starting the application.
    """
    # Get list of all projects in user_data directory
    user_data_path = Path("config/user_data")
    if not user_data_path.exists():
        return
    
    projects = [d for d in user_data_path.iterdir() if d.is_dir()]
    
    for project_dir in projects:
        # Clear B-roll prompts files which might be cached
        broll_prompts_path = project_dir / "broll_prompts.json"
        if broll_prompts_path.exists():
            try:
                # Instead of deleting, back it up with timestamp
                backup_path = project_dir / f"broll_prompts.json.bak.{int(time.time())}"
                shutil.copy2(broll_prompts_path, backup_path)
                os.remove(broll_prompts_path)
                print(f"Cleared cached B-roll prompts file: {broll_prompts_path}")
            except Exception as e:
                print(f"Error clearing cached file: {e}")
        
        # Check script.json file and add version information if missing
        script_path = project_dir / "script.json"
        if script_path.exists():
            try:
                with open(script_path, "r") as f:
                    script_data = json.load(f)
                
                # Check if version info is missing, add it if needed
                if "version" not in script_data:
                    script_data["version"] = "2.0"
                    script_data["last_cleaned"] = time.time()
                    
                    # Count B-roll and A-roll segments if available
                    if "segments" in script_data:
                        broll_segments = [s for s in script_data["segments"] if s.get("type") == "B-Roll"]
                        aroll_segments = [s for s in script_data["segments"] if s.get("type") == "A-Roll"]
                        
                        script_data["broll_segment_count"] = len(broll_segments)
                        script_data["aroll_segment_count"] = len(aroll_segments)
                        
                        print(f"Updated script.json with version info: {len(broll_segments)} B-Roll, {len(aroll_segments)} A-Roll segments")
                    
                    with open(script_path, "w") as f:
                        json.dump(script_data, f, indent=2)
                        
                # Now check for content_status.json and sync it with script.json if needed
                content_status_path = project_dir / "content_status.json"
                if content_status_path.exists() and "segments" in script_data:
                    try:
                        with open(content_status_path, "r") as f:
                            content_status = json.load(f)
                            
                        # Check if B-roll segments in content_status match script.json
                        broll_segments = [s for s in script_data["segments"] if s.get("type") == "B-Roll"]
                        broll_segment_count = len(broll_segments)
                        
                        if "broll" in content_status:
                            content_broll_count = len(content_status["broll"])
                            # If counts don't match, we need to update content_status.json
                            if content_broll_count != broll_segment_count:
                                # Back up content status file
                                backup_path = project_dir / f"content_status.json.bak.{int(time.time())}"
                                shutil.copy2(content_status_path, backup_path)
                                
                                # Create new content status with the correct number of B-roll segments
                                new_broll_status = {}
                                for i in range(broll_segment_count):
                                    segment_id = f"segment_{i}"
                                    # Copy existing data if available, otherwise create empty entry
                                    if "broll" in content_status and segment_id in content_status["broll"]:
                                        new_broll_status[segment_id] = content_status["broll"][segment_id]
                                    else:
                                        new_broll_status[segment_id] = {
                                            "status": "not_started",
                                            "asset_paths": [],
                                            "selected_asset": None
                                        }
                                
                                # Update content status with new B-roll data
                                content_status["broll"] = new_broll_status
                                content_status["broll_segment_count"] = broll_segment_count
                                content_status["synced_with_script"] = True
                                content_status["last_updated"] = time.time()
                                
                                with open(content_status_path, "w") as f:
                                    json.dump(content_status, f, indent=2)
                                    
                                print(f"Updated content_status.json to match script.json: {broll_segment_count} B-Roll segments")
                    except Exception as e:
                        print(f"Error updating content_status.json: {str(e)}")
            except Exception as e:
                print(f"Error updating script.json: {str(e)}")
        
        # Also clean up main_aroll.mp4 file to prevent "Found existing A-Roll video" message
        # when there's no active transcription process
        aroll_path = project_dir / "media" / "a-roll" / "main_aroll.mp4"
        if aroll_path.exists():
            # Only remove if we don't have a corresponding transcription file
            transcription_path = project_dir / "transcription.json"
            if not transcription_path.exists():
                try:
                    os.remove(aroll_path)
                    print(f"Cleared main_aroll.mp4 file as no active transcription exists")
                except Exception as e:
                    print(f"Error clearing main_aroll.mp4 file: {e}")
    
    # Clear Streamlit cache files if any exist
    cache_dir = Path(".streamlit/cache")
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            print("Cleared Streamlit cache directory")
        except Exception as e:
            print(f"Error clearing Streamlit cache: {str(e)}")
    
    # Clear temporary preview files if any exist
    preview_dir = Path("preview")
    if preview_dir.exists() and preview_dir.is_dir():
        try:
            for file in preview_dir.glob("*_preview.*"):
                os.remove(file)
                print(f"Removed temporary preview file: {file}")
        except Exception as e:
            print(f"Error clearing preview files: {str(e)}")
    
    # Clear session state
    if st.session_state:
        for key in list(st.session_state.keys()):
            if key not in ['user_settings', 'project_path', 'current_page']:
                try:
                    del st.session_state[key]
                except Exception:
                    pass
    
    print("Cache clearing complete. App is starting with a clean state.")

# Run cache clearing on startup
clear_app_cache()

# Set page configuration
st.set_page_config(
    page_title="AI Money Printer - Video Shorts Generator",
    page_icon="💰",
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

# Create user_data directory if it doesn't exist
Path("config/user_data").mkdir(parents=True, exist_ok=True)

# App header
st.title("💰 AI Money Printer Shorts")
st.subheader("Automate your short-form video production pipeline")

# App description
st.markdown("""
### Turn your ideas into engaging short-form videos

This app guides you through creating professional short-form videos by automating the most time-consuming parts of the process.

**Complete the following steps to create your video:**

1. **⚙️ Settings** - Configure your project settings
2. **📝 Video Blueprint Setup** - Visualize video structure and segments
3. **✂️ Script Segmentation** - Organize your script into A-Roll and B-Roll sections
4. **🔍 B-Roll Prompt Generation** - Create optimized prompts for AI-generated visuals
5. **⚡ Parallel Content Production** - Generate both A-Roll and B-Roll simultaneously
6. **🎬 Seamless Video Assembly** - Stitch all segments together with perfect timing
7. **💬 Captioning Enhancement** - Add stylized captions synced with your voice
8. **🚀 Multi-Platform Publishing** - Export for YouTube, TikTok, and Instagram
""")

# Get started button
st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("Get Started 🚀", use_container_width=True, type="primary"):
        st.switch_page("pages/4.5_ARoll_Transcription.py")

# Footer
st.markdown("---")
st.caption("AI Money Printer Shorts Generator | v1.0.0")
