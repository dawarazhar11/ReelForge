"""
Direct B-Roll Video Generator

This page uses direct workflow submission to generate B-Roll content
without workflow validation that could cause issues with specialized nodes.
"""

import os
import sys
import json
import time
import random
import streamlit as st
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import custom modules
try:
    import utils.direct_workflow as direct_workflow
    import utils.workflow_selector as workflow_selector
    from components.custom_navigation import render_custom_sidebar
except ImportError as e:
    st.error(f"Failed to import modules: {e}")
    st.stop()

# Default settings
DEFAULT_COMFYUI_URL = "http://100.115.243.42:8000"
DEFAULT_VIDEO_WORKFLOW = "wan.json"
DEFAULT_IMAGE_WORKFLOW = "flux_schnell.json"

# Page setup
st.set_page_config(
    page_title="Direct B-Roll Generator",
    page_icon="🎬",
    layout="wide"
)

def init_session_state():
    """Initialize session state variables"""
    if "job_ids" not in st.session_state:
        st.session_state.job_ids = []
    if "generating" not in st.session_state:
        st.session_state.generating = False
    if "results" not in st.session_state:
        st.session_state.results = []

def load_prompt_templates():
    """Load B-Roll prompt templates from configuration file"""
    try:
        config_dir = os.path.join(os.getcwd(), "config", "user_data", "my_short_video")
        prompts_file = os.path.join(config_dir, "broll_prompts.json")
        
        if not os.path.exists(prompts_file):
            st.warning(f"Prompt file not found: {prompts_file}")
            return []
            
        with open(prompts_file, 'r') as f:
            data = json.load(f)
            
        # Try to extract prompts from the structure
        if "broll_prompts_full" in data:
            prompts = data["broll_prompts_full"]
            st.success(f"Loaded {len(prompts)} prompt templates from configuration file")
            return prompts
        else:
            st.warning("No prompts found in configuration file")
            return []
            
    except Exception as e:
        st.error(f"Error loading prompt templates: {str(e)}")
        return []

def render_settings_sidebar():
    """Render the settings sidebar"""
    st.sidebar.title("⚙️ Settings")
    
    with st.sidebar.expander("ComfyUI Connection", expanded=True):
        comfyui_url = st.text_input("ComfyUI Server URL", "http://100.115.243.42:8000", key="comfyui_url")
    
    with st.sidebar.expander("Workflow Settings", expanded=True):
        # Workflow type (image or video)
        workflow_type = st.radio("Content Type", ["video", "image"], index=0)
        
        # Workflow file selection
        if workflow_type == "video":
            workflow_file = st.text_input("Video Workflow File", "wan.json")
            # Extra warning for video generation
            st.warning("⚠️ Video generation can take 30+ minutes")
        else:
            workflow_file = st.text_input("Image Workflow File", "flux_schnell.json")
        
        # Add a seed input option
        seed = st.text_input("Seed Value (optional)", "827984466477363", 
                           help="Enter seed value for reproducible results. Leave empty for random seeds.")
        
        # Convert seed to integer if provided
        if seed.strip():
            try:
                seed = int(seed)
            except ValueError:
                st.warning("Invalid seed value. Using random seeds.")
                seed = None
        else:
            seed = None
        
        # Resolution
        col1, col2 = st.columns(2)
        with col1:
            width = st.number_input("Width", value=1080, step=8, min_value=320, max_value=2048)
        with col2:
            height = st.number_input("Height", value=1920, step=8, min_value=320, max_value=2048)
        
        # Timeout - different defaults based on content type
        default_timeout = 1800 if workflow_type == "video" else 600
        timeout = st.slider("Generation Timeout (seconds)", 
                          min_value=60, 
                          max_value=3600, 
                          value=default_timeout, 
                          step=60)
        
        # Detached mode option
        detached_mode = st.checkbox("Detached Mode", value=False, 
                                  help="Start generation and return immediately with prompt ID instead of waiting for completion")
        
        # Output settings
        output_dir = st.text_input("Output Directory", "outputs")
        
        return {
            "comfyui_url": comfyui_url,
            "workflow_type": workflow_type,
            "workflow_file": workflow_file,
            "width": width,
            "height": height,
            "timeout": timeout,
            "output_dir": output_dir,
            "seed": seed,
            "detached_mode": detached_mode
        }
        
def render_prompt_editor():
    """Render the prompt editor section"""
    st.subheader("✨ Prompts")
    
    # Load prompt templates
    prompt_templates = load_prompt_templates()
    if not prompt_templates:
        st.warning("No prompt templates found. Creating default templates.")
        prompt_templates = [
            {"prompt": "A beautiful cinematic scene with mountains and trees", "negative_prompt": "ugly, blurry, low quality"},
            {"prompt": "A futuristic cityscape with flying cars", "negative_prompt": "ugly, blurry, low quality"}
        ]
    
    # Create a container for prompts
    prompts_container = st.container()
    
    # Use expandable sections for each prompt
    with prompts_container:
        prompts = []
        for i, template in enumerate(prompt_templates):
            with st.expander(f"B-Roll Segment {i+1}", expanded=True):
                prompt = st.text_area(
                    "Positive Prompt", 
                    value=template.get("prompt", ""), 
                    height=100,
                    key=f"prompt_{i}"
                )
                
                negative_prompt = st.text_area(
                    "Negative Prompt", 
                    value=template.get("negative_prompt", "ugly, blurry, low quality"), 
                    height=70,
                    key=f"negative_{i}"
                )
                
                prompts.append({
                    "prompt": prompt,
                    "negative_prompt": negative_prompt
                })
    
    return prompts

def generate_content(settings, prompts):
    """Generate B-Roll content using direct workflow submission"""
    if not prompts:
        st.error("No prompts provided")
        return
        
    # Mark as generating
    st.session_state.generating = True
    st.session_state.job_ids = []
    st.session_state.results = []
    
    # Setup progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Create a placeholder for detailed status updates
    detailed_status = st.empty()
    
    # Ensure output directory exists
    output_dir = os.path.join(os.getcwd(), settings["output_dir"])
    os.makedirs(output_dir, exist_ok=True)
    
    # Get workflow path from the workflow selector - guarantees correct workflow by content type
    workflow_type = settings["workflow_type"]
    workflow_path = workflow_selector.get_workflow_file(workflow_type)
    
    if not workflow_path:
        st.error(f"Failed to find appropriate workflow file for {workflow_type} content")
        if workflow_type == "image":
            st.error("Make sure flux_schnell.json exists in the app directory")
        else:
            st.error("Make sure wan.json exists in the app directory")
        st.session_state.generating = False
        return
    
    # Display workflow info
    workflow = direct_workflow.load_raw_workflow(workflow_path)
    if workflow:
        model_info = workflow_selector.get_model_info(workflow)
        st.info(f"Using {workflow_type} workflow: {os.path.basename(workflow_path)} (Model: {model_info['model_type']})")
    else:
        st.error(f"Failed to load workflow from {workflow_path}")
        st.session_state.generating = False
        return
    
    # Create a detached job status section if in detached mode
    if settings.get("detached_mode"):
        detached_jobs = st.container()
        with detached_jobs:
            st.subheader("⏱️ Detached Jobs")
            st.info("These jobs will continue running in the background. You can check their status later.")
            detached_job_list = st.empty()
    
    # Submit each prompt
    for i, prompt_data in enumerate(prompts):
        progress_value = i / len(prompts)
        progress_bar.progress(progress_value)
        
        status_text.info(f"Generating B-Roll segment {i+1} of {len(prompts)}...")
        
        # Log the prompt
        st.text(f"Prompt {i+1}: {prompt_data['prompt'][:80]}...")
        
        try:
            # Check if we're in detached mode
            if settings.get("detached_mode"):
                # Just submit the job without waiting for completion
                workflow = direct_workflow.prepare_workflow(
                    workflow_path=workflow_path,
                    prompt=prompt_data["prompt"],
                    negative_prompt=prompt_data["negative_prompt"],
                    seed=settings.get("seed")
                )
                
                prompt_id = direct_workflow.submit_workflow(
                    workflow=workflow,
                    api_url=settings["comfyui_url"]
                )
                
                if prompt_id:
                    st.session_state.job_ids.append({
                        "prompt_id": prompt_id,
                        "prompt": prompt_data["prompt"][:80] + "...",
                        "timestamp": time.time(),
                        "status": "submitted"
                    })
                    
                    # Update the detached job list
                    job_items = []
                    for job in st.session_state.job_ids:
                        job_items.append(f"• Job ID: `{job['prompt_id']}` - {job['prompt']}")
                    
                    detached_job_list.markdown("\n".join(job_items))
                    st.success(f"✅ Submitted job for segment {i+1}. Prompt ID: {prompt_id}")
                else:
                    st.error(f"❌ Failed to submit job for segment {i+1}")
                
                continue
            
            # Generate the content with real-time progress updates
            detailed_status.info("Starting generation...")
            
            # For video workflows, add additional progress information
            if settings["workflow_type"] == "video":
                content_status = st.empty()
                progress_status = st.empty()
                time_status = st.empty()
                
                content_status.info("🎬 Video generation started")
                progress_status.info("⏳ Preparing model...")
                time_status.info("Estimating time remaining...")
                
                # Setup progress tracking variables
                start_time = time.time()
                last_update_time = start_time
                last_progress = 0
                progress_history = []
                
                # Define a progress callback
                def progress_callback(progress_data):
                    nonlocal last_update_time, last_progress, progress_history
                    
                    # Update the progress display
                    progress_status.info(f"🔄 Progress: {progress_data}")
                    
                    # Try to extract percentage and estimate time
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Extract percentage if possible
                    percent = None
                    if isinstance(progress_data, str):
                        if "%" in progress_data:
                            try:
                                percent_text = progress_data.split("%")[0].strip()
                                # Remove any non-numeric characters except decimal points
                                percent_text = ''.join(c for c in percent_text if c.isdigit() or c == '.')
                                percent = float(percent_text)
                            except:
                                pass
                        elif "Frame" in progress_data and "of" in progress_data:
                            try:
                                # Extract frame numbers from text like "Frame 3 of 30"
                                frame_parts = progress_data.split("of")
                                current_frame = int(''.join(c for c in frame_parts[0] if c.isdigit()))
                                total_frames = int(''.join(c for c in frame_parts[1] if c.isdigit()))
                                percent = (current_frame / total_frames) * 100
                            except:
                                pass
                    
                    # If we got a percentage, update time estimate
                    if percent is not None:
                        # Record the progress point
                        progress_history.append((elapsed, percent))
                        
                        # Only keep last 5 progress points to account for varying speeds
                        if len(progress_history) > 5:
                            progress_history.pop(0)
                        
                        # Calculate speed only if we have at least 2 points
                        if len(progress_history) >= 2:
                            # Calculate speed based on progress history
                            first_time, first_percent = progress_history[0]
                            percent_change = percent - first_percent
                            time_change = elapsed - first_time
                            
                            if percent_change > 0 and time_change > 0:
                                speed = percent_change / time_change  # % per second
                                remaining_percent = 100 - percent
                                
                                if speed > 0:
                                    remaining_time = remaining_percent / speed
                                    
                                    # Format the time nicely
                                    if remaining_time > 3600:
                                        time_str = f"{remaining_time/3600:.1f} hours"
                                    elif remaining_time > 60:
                                        time_str = f"{remaining_time/60:.1f} minutes"
                                    else:
                                        time_str = f"{remaining_time:.0f} seconds"
                                    
                                    time_status.info(f"⏱️ Estimated time remaining: {time_str}")
                
                # Generate content with progress tracking
                result = direct_workflow.generate_content(
                    workflow_path=workflow_path,
                    prompt=prompt_data["prompt"],
                    negative_prompt=prompt_data["negative_prompt"],
                    output_dir=output_dir,
                    timeout=settings["timeout"],
                    api_url=settings["comfyui_url"],
                    seed=settings.get("seed")
                )
                
                # Clear the progress displays
                content_status.empty()
                progress_status.empty()
                time_status.empty()
            else:
                # For images, just use the regular method
                result = direct_workflow.generate_content(
                    workflow_path=workflow_path,
                    prompt=prompt_data["prompt"],
                    negative_prompt=prompt_data["negative_prompt"],
                    output_dir=output_dir,
                    timeout=settings["timeout"],
                    api_url=settings["comfyui_url"],
                    seed=settings.get("seed")
                )
            
            # Store the result
            st.session_state.results.append(result)
            
            # Update UI with result
            if result["status"] == "complete":
                if "downloaded_files" in result and result["downloaded_files"]:
                    st.success(f"✅ Generated B-Roll segment {i+1}")
                    
                    # Display the files
                    for file_info in result["downloaded_files"]:
                        file_path = file_info["path"]
                        file_type = file_info["type"]
                        
                        if file_type == "image":
                            st.image(file_path, caption=f"Generated image {os.path.basename(file_path)}")
                        elif file_type == "video":
                            st.video(file_path)
                else:
                    # Job completed but no files were downloaded
                    st.warning(f"⚠️ Job completed for segment {i+1} but no output files were found")
                    
                    # Check if we have filenames but they weren't downloaded
                    if "files" in result and result["files"]:
                        st.info(f"Output files were detected but couldn't be downloaded: {[f['filename'] for f in result['files']]}")
                        
                        # Try to manually download them
                        manually_downloaded = []
                        for file_info in result["files"]:
                            filename = file_info["filename"]
                            file_path = direct_workflow.fetch_output_file(filename, output_dir, settings["comfyui_url"])
                            if file_path:
                                manually_downloaded.append({
                                    "path": file_path, 
                                    "type": file_info["type"],
                                    "filename": filename
                                })
                                
                        # If we managed to download any files, display them
                        if manually_downloaded:
                            st.success(f"✅ Successfully retrieved {len(manually_downloaded)} files manually")
                            for file_info in manually_downloaded:
                                file_path = file_info["path"]
                                file_type = file_info["type"]
                                
                                if file_type == "image":
                                    st.image(file_path, caption=f"Retrieved image {os.path.basename(file_path)}")
                                elif file_type == "video":
                                    st.video(file_path)
            
            elif result["status"] == "timeout":
                st.warning(f"⚠️ Generation timed out after {settings['timeout']} seconds")
                
                # Try one last time to see if there are any output files
                final_check = direct_workflow.find_output_files_by_pattern(
                    result.get("prompt_id", "unknown"),
                    settings["comfyui_url"]
                )
                
                if final_check["status"] == "complete" and "files" in final_check and final_check["files"]:
                    st.info(f"Found files after timeout: {[f['filename'] for f in final_check['files']]}")
                    
                    # Try to download them
                    manually_downloaded = []
                    for file_info in final_check["files"]:
                        filename = file_info["filename"]
                        file_path = direct_workflow.fetch_output_file(filename, output_dir, settings["comfyui_url"])
                        if file_path:
                            manually_downloaded.append({
                                "path": file_path, 
                                "type": file_info["type"],
                                "filename": filename
                            })
                            
                    # If we managed to download any files, display them
                    if manually_downloaded:
                        st.success(f"✅ Successfully retrieved {len(manually_downloaded)} files after timeout")
                        for file_info in manually_downloaded:
                            file_path = file_info["path"]
                            file_type = file_info["type"]
                            
                            if file_type == "image":
                                st.image(file_path, caption=f"Retrieved image {os.path.basename(file_path)}")
                            elif file_type == "video":
                                st.video(file_path)
                
            else:
                st.error(f"❌ Generation failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"Error generating content: {str(e)}")
            st.session_state.results.append({
                "status": "error",
                "message": str(e)
            })
    
    # Complete the progress bar
    progress_bar.progress(1.0)
    status_text.success("Generation complete!")
    detailed_status.empty()
    
    # Mark as done
    st.session_state.generating = False
    
    return st.session_state.results
    
def main():
    """Main function to run the Streamlit app"""
    # Render custom sidebar navigation (if available)
    try:
        render_custom_sidebar()
    except:
        pass
        
    # Initialize session state
    init_session_state()
    
    # Page header
    st.title("🎬 Direct B-Roll Generator")
    st.info("Generate B-Roll content with direct workflow submission, bypassing validation issues")
    
    # Render settings sidebar
    settings = render_settings_sidebar()
    
    # Render prompt editor
    prompts = render_prompt_editor()
    
    # Generate button
    generate_col, status_col = st.columns([1, 3])
    
    with generate_col:
        if st.button("🚀 Generate B-Roll", disabled=st.session_state.generating, use_container_width=True):
            generate_content(settings, prompts)
            
    with status_col:
        if st.session_state.generating:
            st.info("⏳ Generation in progress...")
    
    # Show results if available
    if "results" in st.session_state and st.session_state.results:
        st.subheader("🎞️ Generated Content")
        
        # Count successes and failures
        success_count = sum(1 for r in st.session_state.results if r.get("status") == "complete")
        st.text(f"Successfully generated {success_count} out of {len(st.session_state.results)} B-Roll segments")
        
        # List all downloaded files
        all_files = []
        for result in st.session_state.results:
            if result.get("status") == "complete" and "downloaded_files" in result:
                all_files.extend(result["downloaded_files"])
                
        # Display gallery of files
        if all_files:
            st.subheader("📁 Downloaded Files")
            
            for file_info in all_files:
                file_path = file_info["path"]
                file_type = file_info["type"]
                
                with st.expander(f"{os.path.basename(file_path)}", expanded=True):
                    if file_type == "image":
                        st.image(file_path, use_column_width=True)
                    elif file_type == "video":
                        st.video(file_path)
    
    # Job Status Checker
    with st.expander("🔎 Check Job Status", expanded=False):
        st.subheader("Check Status of Previously Submitted Jobs")
        st.info("If you've submitted jobs in detached mode or they timed out, you can check their status here.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            prompt_id = st.text_input("Enter Prompt ID")
            
        with col2:
            check_button = st.button("Check Status", use_container_width=True)
            
        if check_button and prompt_id:
            st.write("Checking job status...")
            
            try:
                # Create status placeholders
                status_info = st.empty()
                details_info = st.empty()
                files_info = st.empty()
                download_container = st.container()
                
                # Check job status
                status_info.info("⏳ Checking job status...")
                status = direct_workflow.check_job_status(prompt_id, settings["comfyui_url"])
                
                if status["status"] == "complete":
                    status_info.success("✅ Job completed successfully!")
                    
                    # Show files if available
                    if "files" in status and status["files"]:
                        files_info.write(f"Found {len(status['files'])} output files:")
                        
                        file_list = "\n".join([f"- {file_info['filename']}" for file_info in status['files']])
                        details_info.code(file_list)
                        
                        # Add download option
                        with download_container:
                            if st.button("Download Files"):
                                st.write("Downloading files...")
                                
                                output_dir = os.path.join(os.getcwd(), settings["output_dir"])
                                os.makedirs(output_dir, exist_ok=True)
                                
                                downloaded = []
                                for file_info in status["files"]:
                                    filename = file_info["filename"]
                                    file_path = direct_workflow.fetch_output_file(
                                        filename, output_dir, settings["comfyui_url"]
                                    )
                                    
                                    if file_path:
                                        downloaded.append({
                                            "path": file_path,
                                            "type": file_info["type"],
                                            "filename": filename
                                        })
                                
                                if downloaded:
                                    st.success(f"Downloaded {len(downloaded)} files")
                                    
                                    # Display files
                                    for file_info in downloaded:
                                        file_path = file_info["path"]
                                        file_type = file_info["type"]
                                        
                                        with st.expander(f"{os.path.basename(file_path)}", expanded=True):
                                            if file_type == "image":
                                                st.image(file_path, use_column_width=True)
                                            elif file_type == "video":
                                                st.video(file_path)
                                else:
                                    st.error("Failed to download any files")
                    else:
                        details_info.warning("No output files found for this job")
                
                elif status["status"] == "processing":
                    status_info.info("⏳ Job is still processing...")
                    
                    # Try to get progress information
                    progress_info = direct_workflow.check_video_progress(prompt_id, settings["comfyui_url"])
                    if progress_info:
                        details_info.info(f"Progress: {progress_info}")
                    else:
                        details_info.info("No progress information available")
                
                elif status["status"] == "error":
                    status_info.error("❌ Job failed")
                    details_info.error(f"Error: {status.get('message', 'Unknown error')}")
                
                else:
                    status_info.warning(f"❓ Job status: {status['status']}")
                    details_info.warning("Cannot determine detailed status information")
                
            except Exception as e:
                st.error(f"Error checking job status: {str(e)}")
    
    # Warning about video generation time
    if settings["workflow_type"] == "video":
        st.warning("""
        ⚠️ **Note about Video Generation:** 
        
        Video generation using the WAN model can take a very long time (30+ minutes) due to the 
        frame-by-frame processing. Each frame can take 2-3 minutes to generate. For a 30-frame video, 
        that means it could take 1-1.5 hours to complete.
        
        Consider using **Detached Mode** for video generation, which will start the job and give you a 
        Prompt ID that you can use to check status later.
        """)

if __name__ == "__main__":
    main() 