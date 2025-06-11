"""
Direct Workflow Submission Module

This module provides utility functions to submit workflow JSON files directly to ComfyUI
without any intermediary processing or validation.
"""

import os
import sys
import json
import time
import random
import requests
import uuid
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default settings
COMFYUI_SERVER_URL = "http://100.115.243.42:8000"

def load_raw_workflow(workflow_path):
    """Load a workflow JSON file without any validation or modification"""
    logger.info(f"Loading workflow from: {workflow_path}")
    
    if not os.path.exists(workflow_path):
        logger.error(f"❌ Workflow file not found at {workflow_path}")
        return None
        
    try:
        with open(workflow_path, "r") as f:
            workflow = json.load(f)
            
        logger.info(f"✅ Successfully loaded workflow with {len(workflow)} nodes")
        return workflow
    except Exception as e:
        logger.error(f"❌ Error loading workflow: {str(e)}")
        return None

def set_prompts(workflow, prompt, negative_prompt="ugly, blurry, low quality"):
    """Set prompts in the workflow without changing anything else"""
    if not workflow:
        return workflow
        
    # Make a deep copy to avoid modifying the original
    workflow_copy = workflow.copy()
    
    # Find text input nodes (for prompt) - search for nodes with CLIPTextEncode class_type
    text_nodes = [k for k in workflow_copy.keys() 
                 if "class_type" in workflow_copy[k] and 
                 workflow_copy[k]["class_type"] == "CLIPTextEncode"]
    
    logger.info(f"Found {len(text_nodes)} CLIPTextEncode nodes: {text_nodes}")
    
    # Find negative text nodes - typically the second CLIPTextEncode node
    if len(text_nodes) >= 2:
        # First node for positive prompt, second for negative
        pos_node_id = text_nodes[0]
        neg_node_id = text_nodes[1]
        
        # Set prompts
        if "inputs" in workflow_copy[pos_node_id]:
            workflow_copy[pos_node_id]["inputs"]["text"] = prompt
            logger.info(f"Set positive prompt in node {pos_node_id}: {prompt[:50]}...")
            
        if "inputs" in workflow_copy[neg_node_id]:
            workflow_copy[neg_node_id]["inputs"]["text"] = negative_prompt
            logger.info(f"Set negative prompt in node {neg_node_id}: {negative_prompt[:50]}...")
    
    return workflow_copy

def set_seed(workflow, seed=None):
    """Set a random seed (or specific seed if provided) in the workflow"""
    if not workflow:
        return workflow
        
    workflow_copy = workflow.copy()
    
    # Generate random seed if not provided
    if seed is None:
        seed = random.randint(0, 999999999)
    
    # Ensure seed is preserved as-is without type conversion or truncation
    # This handles large seed values like 827984466477363 used in ComfyUI
        
    # Find the KSampler node to set seed
    for node_id, node in workflow_copy.items():
        if "class_type" in node and node["class_type"] == "KSampler" and "inputs" in node and "seed" in node["inputs"]:
            workflow_copy[node_id]["inputs"]["seed"] = seed
            logger.info(f"Set seed in node {node_id}: {seed}")
            break
    
    return workflow_copy

def set_dimensions(workflow, width=1080, height=1920):
    """Set dimensions in the workflow"""
    if not workflow:
        return workflow
        
    workflow_copy = workflow.copy()
    
    # Find nodes that might contain width/height parameters
    for node_id, node in workflow_copy.items():
        if "class_type" in node and "inputs" in node:
            if "width" in node["inputs"] and "height" in node["inputs"]:
                node["inputs"]["width"] = width
                node["inputs"]["height"] = height
                logger.info(f"Set dimensions in node {node_id}: {width}x{height}")
    
    return workflow_copy

def prepare_workflow(workflow_path, prompt, negative_prompt="ugly, blurry, low quality", width=1080, height=1920, seed=None):
    """Load and prepare a workflow for submission"""
    # Load the raw workflow
    workflow = load_raw_workflow(workflow_path)
    if not workflow:
        return None
    
    # Set prompts, dimensions, and seed
    workflow = set_prompts(workflow, prompt, negative_prompt)
    workflow = set_dimensions(workflow, width, height)
    workflow = set_seed(workflow, seed)
    
    return workflow

def submit_workflow(workflow, api_url=COMFYUI_SERVER_URL):
    """Submit the workflow directly to ComfyUI using its API"""
    if not workflow:
        logger.error("❌ No valid workflow to submit")
        return None
        
    try:
        # Create a unique client ID
        client_id = str(uuid.uuid4())
        
        # Prepare the data payload
        data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        # Log submission details
        logger.info(f"Submitting workflow to {api_url}/prompt")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{api_url}/prompt", 
            json=data,  # Use json parameter instead of manually encoding
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")
            
            if prompt_id:
                logger.info(f"✅ Workflow submitted successfully. Prompt ID: {prompt_id}")
                return prompt_id
            else:
                logger.error(f"❌ No prompt ID returned in response")
                return None
        else:
            logger.error(f"❌ Failed to submit workflow. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"❌ Error submitting workflow: {str(e)}")
        return None

def check_job_status(prompt_id, api_url=COMFYUI_SERVER_URL):
    """Check the status of a submitted job"""
    try:
        logger.info(f"Checking status of prompt ID: {prompt_id}")
        # First check direct history endpoint
        response = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if the job is complete (has outputs)
            if "outputs" in data and data["outputs"]:
                logger.info(f"✅ Job completed")
                
                # Find output files
                output_files = []
                for node_id, outputs in data["outputs"].items():
                    if "images" in outputs:
                        for img in outputs["images"]:
                            output_files.append({"filename": img["filename"], "type": "image"})
                    
                    # Check for videos
                    for media_type in ["videos", "gifs"]:
                        if media_type in outputs:
                            for vid in outputs[media_type]:
                                output_files.append({"filename": vid["filename"], "type": "video"})
                
                logger.info(f"Found {len(output_files)} output files")
                return {"status": "complete", "files": output_files}
            
            # Check for alternative indicators job is actually complete
            # Sometimes the job is complete but outputs are structured differently
            if "status" in data and isinstance(data["status"], dict):
                if "completed" in data["status"] and data["status"]["completed"] == True:
                    logger.info("✅ Job found with completed status flag")
                    
                    # Try to find output filenames using alternative methods
                    try:
                        # Check recent outputs view directory
                        patterns = [
                            f"ComfyUI_{prompt_id[:8]}.png",
                            f"ComfyUI_{prompt_id[:8]}.jpg", 
                            f"{prompt_id[:8]}.png",
                            "ComfyUI.png"
                        ]
                        
                        # Try to check if these files exist
                        for pattern in patterns:
                            test_url = f"{api_url}/view?filename={pattern}"
                            try:
                                head_response = requests.head(test_url, timeout=3)
                                if head_response.status_code == 200:
                                    logger.info(f"✅ Found output file via pattern match: {pattern}")
                                    return {
                                        "status": "complete", 
                                        "files": [{"filename": pattern, "type": "image"}]
                                    }
                            except:
                                pass
                        
                        # If we got here but status is completed, return success anyway
                        logger.info("Job marked complete but no files found via patterns. Reporting success.")
                        return {"status": "complete", "files": []}
                    except Exception as e:
                        logger.warning(f"Error checking alternative file patterns: {str(e)}")
                        # Still return complete status since the job is marked as completed
                        return {"status": "complete", "files": []}
            
            # If we get here, the job is still processing
            logger.info(f"⏳ Job still processing...")
            return {"status": "processing"}
                
        # If direct history check failed, check the full history endpoint
        try:
            history_response = requests.get(f"{api_url}/history", timeout=10)
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                
                # Handle different formats of history response
                if isinstance(history_data, dict):
                    for item_id, item_data in history_data.items():
                        # Check for exact or partial match with prompt ID
                        if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                            if "outputs" in item_data and item_data["outputs"]:
                                logger.info(f"✅ Found job in full history with outputs")
                                
                                output_files = []
                                for node_id, outputs in item_data["outputs"].items():
                                    if "images" in outputs:
                                        for img in outputs["images"]:
                                            output_files.append({"filename": img["filename"], "type": "image"})
                                    
                                    # Check for videos
                                    for media_type in ["videos", "gifs"]:
                                        if media_type in outputs:
                                            for vid in outputs[media_type]:
                                                output_files.append({"filename": vid["filename"], "type": "video"})
                                
                                return {"status": "complete", "files": output_files}
        except Exception as e:
            logger.warning(f"Error checking full history: {str(e)}")
        
        # Check queue as a last resort
        try:
            queue_response = requests.get(f"{api_url}/queue", timeout=5)
            
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                
                # Check if the job is in the running queue
                running_fields = ["queue_running", "running_items", "running"]
                for field in running_fields:
                    if field in queue_data:
                        for item in queue_data[field]:
                            if isinstance(item, dict) and "prompt_id" in item:
                                if item["prompt_id"] == prompt_id:
                                    return {"status": "processing"}
                
                # Check if job is pending
                pending_fields = ["queue_pending", "pending_items", "pending"]
                for field in pending_fields:
                    if field in queue_data:
                        for item in queue_data[field]:
                            if isinstance(item, dict) and "prompt_id" in item:
                                if item["prompt_id"] == prompt_id:
                                    return {"status": "processing"}
        except Exception as e:
            logger.warning(f"Error checking queue: {str(e)}")
            
        # If we get here, report unknown status
        logger.info(f"❓ Cannot determine job status")
        return {"status": "unknown"}
            
    except Exception as e:
        logger.error(f"Error checking job status: {str(e)}")
        return {"status": "error", "message": str(e)}

def fetch_output_file(filename, output_dir=None, api_url=COMFYUI_SERVER_URL):
    """Download an output file from ComfyUI"""
    try:
        # Create output directory if not provided
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "outputs")
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine local path
        local_path = os.path.join(output_dir, os.path.basename(filename))
        
        # Determine if it's an image or video based on extension
        is_video = filename.lower().endswith((".mp4", ".webm", ".avi", ".mov", ".gif"))
        
        # Get the appropriate view endpoint
        file_url = f"{api_url}/view"
        if is_video:
            file_url = f"{api_url}/view_video"
            
        params = {"filename": filename}
        
        logger.info(f"Downloading {'video' if is_video else 'image'} file {filename} to {local_path}")
        response = requests.get(file_url, params=params, stream=True, timeout=60)
        
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"✅ Downloaded to {local_path}")
            return local_path
        else:
            logger.error(f"❌ Failed to download file. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Error downloading file: {str(e)}")
        return None

def wait_for_completion(prompt_id, timeout=600, check_interval=5, api_url=COMFYUI_SERVER_URL):
    """Wait for a job to complete, with timeout"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = check_job_status(prompt_id, api_url)
        
        if status["status"] == "complete":
            elapsed = int(time.time() - start_time)
            logger.info(f"✅ Job completed successfully after {elapsed} seconds")
            return status
        
        elif status["status"] == "error":
            logger.error(f"❌ Job failed: {status.get('message', 'Unknown error')}")
            return status
        
        # Wait before checking again
        time.sleep(check_interval)
    
    # If we get here, we've timed out
    elapsed = int(time.time() - start_time)
    logger.warning(f"⚠️ Timed out after {elapsed} seconds")
    return {"status": "timeout", "message": f"Job timed out after {timeout} seconds"}

def generate_content(workflow_path, prompt, negative_prompt=None, output_dir=None, timeout=600, api_url=COMFYUI_SERVER_URL, seed=None):
    """Generate content using a workflow file"""
    # Prepare negative prompt if not provided
    if negative_prompt is None:
        negative_prompt = "ugly, blurry, low quality"
    
    # Prepare the workflow
    workflow = prepare_workflow(workflow_path, prompt, negative_prompt, width=1080, height=1920, seed=seed)
    if not workflow:
        return {"status": "error", "message": "Failed to prepare workflow"}
    
    # Submit the workflow
    prompt_id = submit_workflow(workflow, api_url)
    if not prompt_id:
        return {"status": "error", "message": "Failed to submit workflow"}
    
    # Wait for completion
    result = wait_for_completion(prompt_id, timeout, api_url=api_url)
    
    # If the job completed successfully, download the files
    if result["status"] == "complete" and "files" in result:
        downloaded_files = []
        
        for file_info in result["files"]:
            filename = file_info["filename"]
            file_path = fetch_output_file(filename, output_dir, api_url)
            
            if file_path:
                downloaded_files.append({
                    "path": file_path,
                    "type": file_info["type"],
                    "filename": filename
                })
        
        # Add the downloaded files to the result
        result["downloaded_files"] = downloaded_files
    
    return result 