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
        
        # Timeout
        timeout = st.slider("Generation Timeout (seconds)", min_value=60, max_value=1200, value=600, step=30)
        
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
            "seed": seed
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
    
    # Submit each prompt
    for i, prompt_data in enumerate(prompts):
        progress_value = i / len(prompts)
        progress_bar.progress(progress_value)
        
        status_text.info(f"Generating B-Roll segment {i+1} of {len(prompts)}...")
        
        # Log the prompt
        st.text(f"Prompt {i+1}: {prompt_data['prompt'][:80]}...")
        
        try:
            # Generate the content
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
            if result["status"] == "complete" and "downloaded_files" in result and result["downloaded_files"]:
                st.success(f"✅ Generated B-Roll segment {i+1}")
                
                # Display the files
                for file_info in result["downloaded_files"]:
                    file_path = file_info["path"]
                    file_type = file_info["type"]
                    
                    if file_type == "image":
                        st.image(file_path, caption=f"Generated image {os.path.basename(file_path)}")
                    elif file_type == "video":
                        st.video(file_path)
            
            elif result["status"] == "timeout":
                st.warning(f"⚠️ Generation timed out after {settings['timeout']} seconds")
                
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

if __name__ == "__main__":
    main() 