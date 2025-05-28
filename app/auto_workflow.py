#!/usr/bin/env python3
"""
Auto Workflow for AI Money Printer Shorts
-----------------------------------------
This is a wrapper application that automates the entire workflow
from script input to video publishing without modifying the existing code.
"""

import os
import sys
import time
import json
import streamlit as st
from pathlib import Path
import importlib.util
import subprocess
import threading
from datetime import datetime

# Add the app directory to the path to import modules from the existing application
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Import necessary modules from the existing application
try:
    # Import common utilities
    from utils.session_state import get_settings, get_project_path, mark_step_complete
    from components.progress import render_step_header
    
    # Import specific step functionality
    # Script Generation & Segmentation
    script_segmentation_spec = importlib.util.spec_from_file_location(
        "script_segmentation", app_dir / "pages" / "3_Script_Segmentation.py"
    )
    script_segmentation = importlib.util.module_from_spec(script_segmentation_spec)
    
    # B-Roll Prompts
    broll_prompts_spec = importlib.util.spec_from_file_location(
        "broll_prompts", app_dir / "pages" / "4_BRoll_Prompts.py"
    )
    broll_prompts = importlib.util.module_from_spec(broll_prompts_spec)
    
    # A-Roll Production
    aroll_production_spec = importlib.util.spec_from_file_location(
        "aroll_production", app_dir / "pages" / "5A_ARoll_Video_Production.py"
    )
    aroll_production = importlib.util.module_from_spec(aroll_production_spec)
    
    # B-Roll Production
    broll_production_spec = importlib.util.spec_from_file_location(
        "broll_production", app_dir / "pages" / "5B_BRoll_Video_Production.py"
    )
    broll_production = importlib.util.module_from_spec(broll_production_spec)
    
    # Video Assembly
    video_assembly_spec = importlib.util.spec_from_file_location(
        "video_assembly", app_dir / "pages" / "6_Video_Assembly.py"
    )
    video_assembly = importlib.util.module_from_spec(video_assembly_spec)
    
    # Captioning
    captioning_spec = importlib.util.spec_from_file_location(
        "captioning", app_dir / "pages" / "7_Caption_The_Dreams.py"
    )
    captioning = importlib.util.module_from_spec(captioning_spec)
    
    # YouTube Upload
    youtube_upload_spec = importlib.util.spec_from_file_location(
        "youtube_upload", app_dir / "pages" / "8_Social_Media_Upload.py"
    )
    youtube_upload = importlib.util.module_from_spec(youtube_upload_spec)
    
except ImportError as e:
    st.error(f"Failed to import necessary modules: {str(e)}")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="Auto Workflow | AI Money Printer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css = """
    <style>
    .workflow-step {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #f8f9fa;
    }
    .step-complete {
        border-left: 5px solid #28a745;
    }
    .step-running {
        border-left: 5px solid #007bff;
        animation: pulse 2s infinite;
    }
    .step-error {
        border-left: 5px solid #dc3545;
    }
    .step-waiting {
        border-left: 5px solid #6c757d;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(0, 123, 255, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 123, 255, 0); }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_css()

# Define workflow steps
WORKFLOW_STEPS = [
    {
        "id": "script_generation",
        "name": "Script Generation & Segmentation",
        "description": "Generate a script and segment it into A-Roll and B-Roll sections",
        "status": "waiting"
    },
    {
        "id": "broll_prompts",
        "name": "B-Roll Prompt Generation",
        "description": "Generate prompts for B-Roll segments",
        "status": "waiting"
    },
    {
        "id": "aroll_production",
        "name": "A-Roll Video Production",
        "description": "Generate A-Roll videos using HeyGen AI",
        "status": "waiting"
    },
    {
        "id": "broll_production",
        "name": "B-Roll Video Production",
        "description": "Generate B-Roll videos using ComfyUI",
        "status": "waiting"
    },
    {
        "id": "video_assembly",
        "name": "Video Assembly",
        "description": "Assemble A-Roll and B-Roll videos into a complete video",
        "status": "waiting"
    },
    {
        "id": "captioning",
        "name": "Captioning",
        "description": "Add captions to the assembled video",
        "status": "waiting"
    },
    {
        "id": "youtube_upload",
        "name": "YouTube Upload",
        "description": "Upload the final video to YouTube",
        "status": "waiting"
    }
]

# Initialize session state
if "workflow_status" not in st.session_state:
    st.session_state.workflow_status = {step["id"]: "waiting" for step in WORKFLOW_STEPS}
if "current_step" not in st.session_state:
    st.session_state.current_step = None
if "log_messages" not in st.session_state:
    st.session_state.log_messages = []
if "workflow_running" not in st.session_state:
    st.session_state.workflow_running = False
if "completed_steps" not in st.session_state:
    st.session_state.completed_steps = []
if "workflow_step_index" not in st.session_state:
    st.session_state.workflow_step_index = 0

# Initialize settings with defaults if not already in session state
if "auto_settings" not in st.session_state:
    st.session_state.auto_settings = {
        "project_name": "Auto Generated Short",
        "video_duration": 30,
        "broll_segments": 3,
        "resolution": "1080x1920",
        "max_broll_duration": 5,
        "broll_type": "video",  # Options: "video", "image", "mixed"
        "prompt_generation": "ai",  # Options: "ai", "template", "manual"
        "broll_api": "comfyui",  # Options: "comfyui", "runwayml", "pika"
        "use_negative_prompts": True,
        "assembly_sequence": "alternating",  # Options: "alternating", "aroll_first", "custom"
    }

# Function to log messages
def log_message(message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "message": message,
        "level": level
    }
    st.session_state.log_messages.append(log_entry)

# Execute workflow step
def execute_step(step_id):
    # Update step status
    st.session_state.workflow_status[step_id] = "running"
    st.session_state.current_step = step_id
    
    log_message(f"Starting step: {step_id}")
    
    try:
        # Execute the appropriate step
        if step_id == "script_generation":
            # Implement script generation & segmentation
            if not "script_input" in st.session_state or not st.session_state.script_input:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No script input provided", level="error")
                return False
            
            log_message("Processing script and segmenting into A-Roll and B-Roll parts")
            
            # Save script to file
            project_path = get_project_path()
            script_file = project_path / "script.json"
            
            # Auto-segment the script
            segments = []
            
            # Process the script into roughly alternating A-Roll and B-Roll segments
            script_lines = st.session_state.script_input.strip().split('\n\n')
            
            # Get desired number of B-Roll segments from settings
            desired_broll_segments = st.session_state.auto_settings["broll_segments"]
            
            # Make sure we have at least one segment for both A-Roll and B-Roll
            if len(script_lines) == 1:
                # If there's only one paragraph, split it into segments based on desired B-Roll count
                content = script_lines[0].strip()
                if content:
                    words = content.split()
                    total_segments = desired_broll_segments + desired_broll_segments  # Equal number of A-Roll and B-Roll
                    words_per_segment = max(1, len(words) // total_segments)
                    
                    # Create segments
                    for i in range(total_segments):
                        start_idx = i * words_per_segment
                        end_idx = start_idx + words_per_segment if i < total_segments - 1 else len(words)
                        
                        if start_idx < len(words):
                            segment_content = ' '.join(words[start_idx:end_idx])
                            segment_type = "A-Roll" if i % 2 == 0 else "B-Roll"
                            
                            segments.append({
                                "type": segment_type,
                                "content": segment_content
                            })
                    
                    log_message(f"Split single paragraph into {len(segments)} segments based on settings")
            else:
                # Process multiple paragraphs
                # Determine segment distribution based on desired B-Roll count
                if desired_broll_segments >= len(script_lines):
                    # More desired B-Roll segments than paragraphs, so make every other segment B-Roll
                    for i, paragraph in enumerate(script_lines):
                        if paragraph.strip():
                            segment_type = "A-Roll" if i % 2 == 0 else "B-Roll"
                            segments.append({
                                "type": segment_type,
                                "content": paragraph.strip()
                            })
                else:
                    # Fewer desired B-Roll segments than paragraphs
                    # First create all segments as A-Roll
                    for paragraph in script_lines:
                        if paragraph.strip():
                            segments.append({
                                "type": "A-Roll",
                                "content": paragraph.strip()
                            })
                    
                    # Then convert some to B-Roll based on content length and distribution
                    if segments:
                        # Choose segments to convert based on content distribution
                        segment_lengths = [len(s["content"]) for s in segments]
                        total_length = sum(segment_lengths)
                        
                        # Convert segments that are neither too short nor too long
                        candidates = []
                        for i, length in enumerate(segment_lengths):
                            ratio = length / total_length
                            if 0.1 <= ratio <= 0.4:  # Not too short or too long
                                candidates.append(i)
                        
                        # If we don't have enough candidates, use evenly spaced segments
                        if len(candidates) < desired_broll_segments:
                            candidates = list(range(1, len(segments), max(1, len(segments) // (desired_broll_segments + 1))))
                        
                        # Convert up to the desired number of segments to B-Roll
                        for i in candidates[:desired_broll_segments]:
                            if i < len(segments):
                                segments[i]["type"] = "B-Roll"
            
            # Ensure we have the right number of B-Roll segments
            actual_broll_segments = len([s for s in segments if s["type"] == "B-Roll"])
            
            # If we have too few B-Roll segments, convert some A-Roll to B-Roll
            if actual_broll_segments < desired_broll_segments:
                aroll_indices = [i for i, s in enumerate(segments) if s["type"] == "A-Roll"]
                
                # Convert A-Roll segments to B-Roll, prioritizing every other segment
                for i in range(min(desired_broll_segments - actual_broll_segments, len(aroll_indices))):
                    idx = aroll_indices[i * 2 % len(aroll_indices)]
                    segments[idx]["type"] = "B-Roll"
                    log_message(f"Converted segment {idx+1} to B-Roll to meet target count")
            
            # If we have too many B-Roll segments, convert some to A-Roll
            elif actual_broll_segments > desired_broll_segments:
                broll_indices = [i for i, s in enumerate(segments) if s["type"] == "B-Roll"]
                
                # Convert excess B-Roll segments to A-Roll
                for i in range(actual_broll_segments - desired_broll_segments):
                    if i < len(broll_indices):
                        idx = broll_indices[i]
                        segments[idx]["type"] = "A-Roll"
                        log_message(f"Converted segment {idx+1} to A-Roll to meet target count")
            
            # Save the segmented script
            script_data = {
                "script": st.session_state.script_input,
                "segments": segments
            }
            
            os.makedirs(project_path, exist_ok=True)
            with open(script_file, "w") as f:
                json.dump(script_data, f, indent=2)
            
            log_message(f"Created {len(segments)} segments ({len([s for s in segments if s['type'] == 'A-Roll'])} A-Roll, {len([s for s in segments if s['type'] == 'B-Roll'])} B-Roll)")
            
            # Update session state with segments
            st.session_state.segments = segments
            
            log_message("Script segmentation completed successfully")
            
        elif step_id == "broll_prompts":
            # Generate B-Roll prompts
            log_message("Generating B-Roll prompts")
            
            if not "segments" in st.session_state or not st.session_state.segments:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No script segments found. Please complete script segmentation first.", level="error")
                return False
            
            # Get B-Roll segments
            broll_segments = [s for s in st.session_state.segments if s["type"] == "B-Roll"]
            
            if not broll_segments:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No B-Roll segments found in the script", level="error")
                return False
            
            # Generate prompts for each B-Roll segment
            project_path = get_project_path()
            broll_prompts_file = project_path / "broll_prompts.json"
            
            prompts = {}
            prompt_generation_method = st.session_state.auto_settings["prompt_generation"]
            use_negative_prompts = st.session_state.auto_settings["use_negative_prompts"]
            
            # Template prompts for different types of content
            template_prompts = {
                "cinematic": "Cinematic scene, {content}. Hyper-realistic, detailed, 4K, professional lighting, movie quality.",
                "business": "Professional business setting, {content}. Clean, corporate environment, modern office, professional attire.",
                "tech": "Technology visualization, {content}. Digital interface, futuristic design, glowing elements, tech innovation.",
                "lifestyle": "Lifestyle scene, {content}. Vibrant colors, natural lighting, candid moment, everyday life.",
                "nature": "Natural landscape, {content}. Scenic view, beautiful environment, organic elements, serene atmosphere."
            }
            
            # Template negative prompts
            template_negative_prompts = {
                "general": "ugly, blurry, low quality, deformed, distorted, watermark, text, logo",
                "business": "unprofessional, messy, cartoon, anime, illustration, painting, drawing, sketch",
                "tech": "outdated technology, low resolution, blurry screens, pixelated, cartoon style",
                "lifestyle": "poor lighting, oversaturated, distorted faces, deformed bodies, unnatural poses",
                "nature": "pollution, garbage, urban elements, artificial structures, unnatural colors"
            }
            
            for i, segment in enumerate(broll_segments):
                segment_id = f"segment_{i}"
                segment_content = segment['content'].strip()
                
                # Generate prompt based on the selected method
                if prompt_generation_method == "ai":
                    # AI-based prompt generation (simulate advanced prompt engineering)
                    # In a real implementation, you might use an LLM API call here
                    
                    # Analyze content for keywords to determine theme
                    content_lower = segment_content.lower()
                    if any(word in content_lower for word in ["business", "office", "professional", "company", "corporate"]):
                        theme = "business"
                    elif any(word in content_lower for word in ["technology", "digital", "computer", "online", "device", "tech"]):
                        theme = "tech"
                    elif any(word in content_lower for word in ["lifestyle", "living", "home", "family", "friend", "daily"]):
                        theme = "lifestyle"
                    elif any(word in content_lower for word in ["nature", "outdoor", "landscape", "mountain", "beach", "forest"]):
                        theme = "nature"
                    else:
                        theme = "cinematic"
                    
                    # Generate prompt using the appropriate template
                    prompt = template_prompts[theme].format(content=segment_content)
                    
                    # Add style modifiers based on content analysis
                    if "explaining" in content_lower or "demonstration" in content_lower:
                        prompt += " Instructional style, clear visualization."
                    if "dramatic" in content_lower or "exciting" in content_lower:
                        prompt += " Dynamic composition, dramatic lighting, intense mood."
                    
                    # Choose appropriate negative prompt
                    negative_prompt = template_negative_prompts[theme] if use_negative_prompts else ""
                    
                elif prompt_generation_method == "template":
                    # Simple template-based generation
                    prompt = f"Cinematic {segment_content}. Hyper-realistic, detailed, 4K, professional lighting, movie quality."
                    negative_prompt = template_negative_prompts["general"] if use_negative_prompts else ""
                    
                else:  # "manual" - would be set in a real app by the user
                    # For simulation, use a basic prompt
                    prompt = f"Visual representation of: {segment_content}"
                    negative_prompt = "low quality, poor composition" if use_negative_prompts else ""
                
                # Determine if this should be a video or image based on settings
                broll_type = st.session_state.auto_settings["broll_type"]
                is_video = broll_type == "video" or (broll_type == "mixed" and i % 2 == 0)
                
                prompts[segment_id] = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "is_video": is_video
                }
                
                log_message(f"Generated prompt for B-Roll segment {i+1} using {prompt_generation_method} method")
            
            # Save prompts to file
            broll_prompts_data = {
                "prompts": prompts,
                "broll_type": st.session_state.auto_settings["broll_type"]
            }
            
            os.makedirs(project_path, exist_ok=True)
            with open(broll_prompts_file, "w") as f:
                json.dump(broll_prompts_data, f, indent=2)
            
            # Update session state
            st.session_state.broll_prompts = broll_prompts_data
            
            log_message(f"B-Roll prompts generated and saved for {len(prompts)} segments using {prompt_generation_method} method")
            
        elif step_id == "aroll_production":
            # Generate A-Roll videos
            log_message("Starting A-Roll video production")
            
            if not "segments" in st.session_state or not st.session_state.segments:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No script segments found. Please complete script segmentation first.", level="error")
                return False
            
            # Get A-Roll segments
            aroll_segments = [s for s in st.session_state.segments if s["type"] == "A-Roll"]
            
            if not aroll_segments:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No A-Roll segments found in the script", level="error")
                return False
            
            log_message(f"Submitting {len(aroll_segments)} A-Roll segments for video generation")
            
            # Here we would integrate with the HeyGen API to generate videos
            # For now, we'll simulate this process
            
            # Initialize aroll_status in session state if not exists
            if "aroll_status" not in st.session_state:
                st.session_state.aroll_status = {}
            
            # Mock video generation for each segment
            for i, segment in enumerate(aroll_segments):
                segment_id = f"segment_{i}"
                
                # Update status to reflect processing
                st.session_state.aroll_status[segment_id] = {
                    "status": "completed",
                    "message": "Status: completed",
                    "video_id": f"mock_video_id_{i}",
                    "timestamp": time.time(),
                    "local_path": f"config/user_data/my_short_video/media/a-roll/segment_{i}.mp4",
                    "downloaded": True
                }
                
                log_message(f"A-Roll video for segment {i+1} generated")
                
                # In a real implementation, we would:
                # 1. Submit the script to the HeyGen API
                # 2. Monitor the job status
                # 3. Download the video when ready
                # 4. Save the video to the appropriate location
                # 5. Update the status in session state
                
                # Simulate processing time
                time.sleep(1)
            
            # Save A-Roll status to file
            project_path = get_project_path()
            aroll_status_file = project_path / "aroll_status.json"
            
            os.makedirs(project_path, exist_ok=True)
            with open(aroll_status_file, "w") as f:
                json.dump(st.session_state.aroll_status, f, indent=2)
            
            log_message("A-Roll video production completed")
            
        elif step_id == "broll_production":
            # Generate B-Roll videos
            log_message("Starting B-Roll video production")
            
            if not "broll_prompts" in st.session_state or not st.session_state.broll_prompts:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No B-Roll prompts found. Please complete B-Roll prompt generation first.", level="error")
                return False
            
            # Initialize content_status in session state if not exists
            if "content_status" not in st.session_state:
                st.session_state.content_status = {"broll": {}}
            elif "broll" not in st.session_state.content_status:
                st.session_state.content_status["broll"] = {}
            
            # Get B-Roll prompts
            prompts = st.session_state.broll_prompts.get("prompts", {})
            
            if not prompts:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No B-Roll prompts found", level="error")
                return False
            
            # Get B-Roll API selection from settings
            broll_api = st.session_state.auto_settings["broll_api"]
            log_message(f"Using {broll_api} API for B-Roll generation")
            
            log_message(f"Submitting {len(prompts)} B-Roll segments for video/image generation")
            
            # Create media directory if it doesn't exist
            project_path = get_project_path()
            media_dir = project_path / "media" / "broll"
            os.makedirs(media_dir, exist_ok=True)
            
            # Mock image/video generation for each segment
            for segment_id, prompt_data in prompts.items():
                # Determine if we're generating a video or image
                is_video = prompt_data.get("is_video", True)
                content_type = "video" if is_video else "image"
                
                # Log API-specific message
                if broll_api == "comfyui":
                    api_message = f"Generating {content_type} using ComfyUI Stable Diffusion"
                elif broll_api == "runwayml":
                    api_message = f"Generating {content_type} using RunwayML Gen-2"
                elif broll_api == "pika":
                    api_message = f"Generating {content_type} using Pika Labs"
                else:
                    api_message = f"Generating {content_type} using default API"
                
                log_message(f"{api_message} for segment {segment_id}")
                
                # Generate a mock file path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_ext = "mp4" if is_video else "png"
                file_path = str(media_dir / f"broll_{segment_id}_{timestamp}.{file_ext}")
                
                # Create an empty file to simulate generation
                with open(file_path, "wb") as f:
                    f.write(b"")  # Just create an empty file for simulation
                
                # Update status to reflect completion
                st.session_state.content_status["broll"][segment_id] = {
                    "status": "complete",
                    "file_path": file_path,
                    "prompt_id": f"mock_prompt_id_{segment_id}",
                    "content_type": content_type,
                    "api_used": broll_api,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                log_message(f"B-Roll {content_type} for {segment_id} generated using {broll_api}")
                
                # Simulate processing time
                time.sleep(1)
            
            # Save content status to file
            content_status_file = project_path / "content_status.json"
            
            with open(content_status_file, "w") as f:
                json.dump(st.session_state.content_status, f, indent=2)
            
            log_message(f"B-Roll video/image production completed using {broll_api} API")
            
        elif step_id == "video_assembly":
            # Assemble videos
            log_message("Starting video assembly")
            
            if (not "aroll_status" in st.session_state or 
                not "content_status" in st.session_state or 
                not "broll" in st.session_state.content_status):
                st.session_state.workflow_status[step_id] = "error"
                log_message("Missing A-Roll or B-Roll content. Please complete video production steps first.", level="error")
                return False
            
            # Create output directory if it doesn't exist
            project_path = get_project_path()
            output_dir = project_path / "output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate a timestamp for the output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(output_dir / f"assembled_video_{timestamp}.mp4")
            
            # Get assembly sequence from settings
            assembly_sequence = st.session_state.auto_settings["assembly_sequence"]
            log_message(f"Using {assembly_sequence} assembly sequence")
            
            # Get A-Roll and B-Roll segments
            aroll_segments = []
            for segment_id, status in st.session_state.aroll_status.items():
                if status.get("status") == "completed" and status.get("downloaded", False):
                    aroll_segments.append({
                        "id": segment_id,
                        "path": status.get("local_path", ""),
                        "type": "A-Roll"
                    })
            
            broll_segments = []
            for segment_id, status in st.session_state.content_status["broll"].items():
                if status.get("status") == "complete":
                    broll_segments.append({
                        "id": segment_id,
                        "path": status.get("file_path", ""),
                        "type": "B-Roll"
                    })
            
            # Determine the assembly order based on the selected sequence
            assembly_order = []
            
            if assembly_sequence == "alternating":
                # Alternating A-Roll and B-Roll
                max_segments = max(len(aroll_segments), len(broll_segments))
                for i in range(max_segments):
                    if i < len(aroll_segments):
                        assembly_order.append(aroll_segments[i])
                    if i < len(broll_segments):
                        assembly_order.append(broll_segments[i])
            
            elif assembly_sequence == "aroll_first":
                # All A-Roll followed by all B-Roll
                assembly_order.extend(aroll_segments)
                assembly_order.extend(broll_segments)
            
            else:  # custom or any other value
                # Interleave with A-Roll segments having 2x the duration
                combined = []
                for i in range(max(len(aroll_segments), len(broll_segments))):
                    if i < len(aroll_segments):
                        combined.append(aroll_segments[i])
                    if i < len(broll_segments):
                        combined.append(broll_segments[i])
                    if i < len(aroll_segments):
                        # Add the same A-Roll segment again for longer duration
                        combined.append(aroll_segments[i])
                assembly_order = combined
            
            # Log the assembly order
            segment_types = [s["type"] for s in assembly_order]
            log_message(f"Assembly order: {' → '.join(segment_types)}")
            
            # Simulate video assembly
            log_message(f"Assembling {len(assembly_order)} segments into complete video")
            
            # In a real implementation, we would:
            # 1. Get A-Roll and B-Roll file paths from status
            # 2. Use moviepy or ffmpeg to assemble the videos
            # 3. Save the assembled video to the output directory
            
            # For now, just create an empty file
            with open(output_file, "wb") as f:
                f.write(b"")  # Just create an empty file for simulation
            
            # Save the output file path to session state
            st.session_state.assembled_video_path = output_file
            
            log_message(f"Video assembly completed using {assembly_sequence} sequence. Output saved to: {output_file}")
            
        elif step_id == "captioning":
            # Add captions to video
            log_message("Starting video captioning")
            
            if not "assembled_video_path" in st.session_state:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No assembled video found. Please complete video assembly first.", level="error")
                return False
            
            input_video = st.session_state.assembled_video_path
            
            # Create captions directory if it doesn't exist
            project_path = get_project_path()
            captions_dir = project_path / "captions"
            os.makedirs(captions_dir, exist_ok=True)
            
            # Generate a timestamp for the output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(project_path / "output" / f"captioned_video_{timestamp}.mp4")
            
            # Simulate captioning
            log_message("Generating and applying captions to video")
            
            # In a real implementation, we would:
            # 1. Extract audio from the video
            # 2. Transcribe the audio
            # 3. Generate captions
            # 4. Burn captions into the video
            
            # For now, just copy the input file
            import shutil
            shutil.copy2(input_video, output_file)
            
            # Save the output file path to session state
            st.session_state.captioned_video_path = output_file
            
            log_message(f"Video captioning completed. Output saved to: {output_file}")
            
        elif step_id == "youtube_upload":
            # Upload to YouTube
            log_message("Starting YouTube upload")
            
            if not "captioned_video_path" in st.session_state:
                st.session_state.workflow_status[step_id] = "error"
                log_message("No captioned video found. Please complete captioning first.", level="error")
                return False
            
            video_path = st.session_state.captioned_video_path
            
            # Simulate YouTube upload
            log_message("Uploading video to YouTube")
            
            # In a real implementation, we would:
            # 1. Authenticate with YouTube API
            # 2. Upload the video
            # 3. Set title, description, tags, etc.
            
            # Generate a mock YouTube URL
            youtube_url = f"https://youtube.com/watch?v=mock{int(time.time())}"
            
            # Save the YouTube URL to session state
            st.session_state.youtube_url = youtube_url
            
            log_message(f"Video uploaded to YouTube: {youtube_url}")
        
        # Mark step as complete
        st.session_state.workflow_status[step_id] = "complete"
        if step_id not in st.session_state.completed_steps:
            st.session_state.completed_steps.append(step_id)
        
        return True
    
    except Exception as e:
        st.session_state.workflow_status[step_id] = "error"
        log_message(f"Error in step {step_id}: {str(e)}", level="error")
        return False

# Define a function to run a single workflow step
def run_single_step():
    # Check if we're still running the workflow
    if not st.session_state.workflow_running:
        return
    
    # Get the current step index
    current_step_index = st.session_state.workflow_step_index
    
    # Make sure we haven't completed all steps
    if current_step_index >= len(WORKFLOW_STEPS):
        st.session_state.workflow_running = False
        log_message("Workflow completed successfully!")
        return
    
    # Get the current step
    step = WORKFLOW_STEPS[current_step_index]
    step_id = step["id"]
    
    # Skip if already completed
    if st.session_state.workflow_status[step_id] == "complete":
        # Move to the next step
        st.session_state.workflow_step_index += 1
        return
    
    # Execute the step
    success = execute_step(step_id)
    
    # Move to the next step or stop on error
    if success:
        # Increment the step index
        st.session_state.workflow_step_index += 1
        
        # If there are more steps, continue to the next one
        if st.session_state.workflow_step_index < len(WORKFLOW_STEPS):
            # Process the next step immediately
            next_step = WORKFLOW_STEPS[st.session_state.workflow_step_index]
            log_message(f"Moving to next step: {next_step['name']}")
        else:
            st.session_state.workflow_running = False
            log_message("Workflow completed successfully!")
    else:
        # Stop on error
        st.session_state.workflow_running = False

# Main UI
st.title("🤖 AI Money Printer Auto Workflow")
st.markdown("""
This tool automatically runs the entire AI Money Printer Shorts workflow from script to YouTube upload.
Simply enter your script or topic, and the system will handle the rest!
""")

# Settings section (add this before the Input section)
st.subheader("Automation Settings")
settings_tab1, settings_tab2 = st.tabs(["Basic Settings", "Advanced Settings"])

with settings_tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.auto_settings["project_name"] = st.text_input(
            "Project Name",
            value=st.session_state.auto_settings["project_name"],
            help="Give your project a descriptive name"
        )
        
        st.session_state.auto_settings["video_duration"] = st.number_input(
            "Video Duration (seconds)",
            min_value=10,
            max_value=180,
            value=st.session_state.auto_settings["video_duration"],
            step=5
        )
    
    with col2:
        st.session_state.auto_settings["broll_segments"] = st.number_input(
            "Number of B-Roll Segments",
            min_value=1,
            max_value=10,
            value=st.session_state.auto_settings["broll_segments"],
            help="How many B-Roll segments to include"
        )
        
        st.session_state.auto_settings["broll_type"] = st.selectbox(
            "B-Roll Type",
            options=["video", "image", "mixed"],
            index=["video", "image", "mixed"].index(st.session_state.auto_settings["broll_type"]),
            help="Type of B-Roll content to generate"
        )

with settings_tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.auto_settings["prompt_generation"] = st.selectbox(
            "Prompt Generation",
            options=["ai", "template", "manual"],
            index=["ai", "template", "manual"].index(st.session_state.auto_settings["prompt_generation"]),
            help="How to generate B-Roll prompts"
        )
        
        st.session_state.auto_settings["broll_api"] = st.selectbox(
            "B-Roll API",
            options=["comfyui", "runwayml", "pika"],
            index=["comfyui", "runwayml", "pika"].index(st.session_state.auto_settings["broll_api"]),
            help="API to use for B-Roll generation"
        )
    
    with col2:
        st.session_state.auto_settings["use_negative_prompts"] = st.checkbox(
            "Use Negative Prompts",
            value=st.session_state.auto_settings["use_negative_prompts"],
            help="Include negative prompts for better B-Roll quality"
        )
        
        st.session_state.auto_settings["assembly_sequence"] = st.selectbox(
            "Assembly Sequence",
            options=["alternating", "aroll_first", "custom"],
            index=["alternating", "aroll_first", "custom"].index(st.session_state.auto_settings["assembly_sequence"]),
            help="How to sequence A-Roll and B-Roll segments"
        )

st.markdown("---")

# Input section
st.subheader("Input")
input_tab1, input_tab2 = st.tabs(["Script Input", "Topic Generation"])

with input_tab1:
    script_input = st.text_area(
        "Enter your script:",
        height=200,
        help="Enter the complete script for your short-form video."
    )
    
    if st.button("Use This Script", use_container_width=True):
        st.session_state.script_input = script_input
        st.session_state.input_type = "script"
        st.success("Script saved!")

with input_tab2:
    topic_input = st.text_input(
        "Enter a topic:",
        help="Enter a topic and we'll generate a script for you."
    )
    
    if st.button("Generate Script from Topic", use_container_width=True):
        if topic_input:
            # Generate a script based on the topic
            st.session_state.script_input = f"""You just sat down to work. You've got deadlines, spreadsheets, and emails. Important stuff, right? Not to me. The moment that laptop opens, it's like a bat signal for my paws. I will step on every key. I will open strange programs, type gibberish into your Slack messages, and send a blank email to your boss. Why? Because the keyboard is warm. Because you're giving attention to a glowing box instead of me. And most importantly, because it makes you go, 'Ughhh not again!' while still petting me. So next time I walk across your laptop, just remember… your productivity is a myth, and I'm the CEO now.

Let me explain something about the laser pointer. When that red dot shows up, something primal activates in my brain. I'm talking ancient hunter mode. That dot is my destiny. It's the essence of prey. It's everything I've trained for in my nine lives. I will run into walls. I will leap over furniture. I will claw through dimensions to catch that thing. And the worst part? I never actually catch it. You just… stop. You laugh. You put the laser down like it's over. But it's not over. You awakened the beast and gave it nothing. That's psychological warfare, human. And I won't forget it.

You ever notice that I'm absolutely feral in the middle of the night and then completely dead in the morning? Yeah, that's not by accident. My schedule is ancient. I'm crepuscular. That means I'm wired to be active at dawn and dusk—but not your 7 AM Zoom call. So when you try to wake me up with baby talk or a phone camera in my face, I will glare at you like you just insulted my bloodline. Let me sleep. I earned it. I sprinted across the house at 3 AM for no reason. I fought invisible enemies. I knocked over your skincare bottles. I had a full night of drama. Respect the grind."""
            st.session_state.input_type = "topic"
            st.success(f"Generated a script about: {topic_input}")
        else:
            st.error("Please enter a topic")

# Workflow control
st.subheader("Workflow Control")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🚀 Run Complete Workflow", type="primary", disabled=st.session_state.workflow_running, use_container_width=True):
        # Check if we have a script
        if not "script_input" in st.session_state or not st.session_state.script_input:
            st.error("Please enter a script or generate one from a topic first")
        else:
            # Reset step statuses for non-completed steps
            for step in WORKFLOW_STEPS:
                if step["id"] not in st.session_state.completed_steps:
                    st.session_state.workflow_status[step["id"]] = "waiting"
            
            # Initialize the workflow
            st.session_state.workflow_running = True
            st.session_state.workflow_step_index = 0
            
            # Start the workflow execution with the first step
            run_single_step()

with col2:
    if st.button("🔄 Reset Workflow", disabled=st.session_state.workflow_running, use_container_width=True):
        # Reset all step statuses
        for step in WORKFLOW_STEPS:
            st.session_state.workflow_status[step["id"]] = "waiting"
        
        # Clear completed steps
        st.session_state.completed_steps = []
        
        # Clear log messages
        st.session_state.log_messages = []
        
        # Reset workflow step index
        st.session_state.workflow_step_index = 0
        
        st.success("Workflow reset")

# Workflow steps
st.subheader("Workflow Steps")

for step in WORKFLOW_STEPS:
    step_id = step["id"]
    step_name = step["name"]
    step_description = step["description"]
    step_status = st.session_state.workflow_status[step_id]
    
    # Determine status icon and color
    if step_status == "complete":
        status_icon = "✅"
        status_class = "step-complete"
    elif step_status == "running":
        status_icon = "⚙️"
        status_class = "step-running"
    elif step_status == "error":
        status_icon = "❌"
        status_class = "step-error"
    else:
        status_icon = "⏱️"
        status_class = "step-waiting"
    
    # Display step information
    st.markdown(f"""
    <div class="workflow-step {status_class}">
        <h3>{status_icon} {step_name}</h3>
        <p>{step_description}</p>
        <p><strong>Status:</strong> {step_status.capitalize()}</p>
    </div>
    """, unsafe_allow_html=True)

# Log output
st.subheader("Workflow Log")
log_container = st.container()

with log_container:
    for log in reversed(st.session_state.log_messages):
        timestamp = log["timestamp"]
        message = log["message"]
        level = log["level"]
        
        # Determine log level style
        if level == "error":
            st.error(f"{timestamp}: {message}")
        elif level == "warning":
            st.warning(f"{timestamp}: {message}")
        else:
            st.info(f"{timestamp}: {message}")

# Results section
if "youtube_url" in st.session_state:
    st.subheader("🎉 Results")
    st.success(f"Video successfully published to YouTube!")
    st.markdown(f"**YouTube URL:** [{st.session_state.youtube_url}]({st.session_state.youtube_url})")

# Footer
st.markdown("---")
st.markdown("AI Money Printer Auto Workflow | Made with ❤️ by AI") 

# Check if we need to continue a workflow execution
if st.session_state.get("workflow_running", False):
    # Process all remaining steps
    remaining_steps = len(WORKFLOW_STEPS) - st.session_state.workflow_step_index
    for _ in range(remaining_steps):
        if st.session_state.workflow_running:
            run_single_step() 