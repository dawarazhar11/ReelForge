#!/usr/bin/env python3
"""
Test script for ComfyUI WebSocket client.
This script tests the WebSocket client with the ComfyUI server.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(parent_dir))

# Import the WebSocket client
try:
    from utils.ai.comfyui_websocket import (
        load_workflow_file,
        modify_workflow,
        submit_workflow,
        get_output_images,
        wait_for_prompt_completion,
        check_prompt_status
    )
except ImportError as e:
    logger.error(f"Failed to import WebSocket client: {str(e)}")
    sys.exit(1)

# Constants
COMFYUI_SERVER_URL = "http://100.115.243.42:8000"
WORKFLOW_FILE = parent_dir / "wan.json"
OUTPUT_DIR = parent_dir / "test_outputs" / "comfyui_websocket_test"

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def check_existing_job(prompt_id):
    """
    Check the status of an existing job.
    
    Args:
        prompt_id: The prompt ID to check
        
    Returns:
        True if job is complete, False otherwise
    """
    print(f"\n=== Checking existing job: {prompt_id} ===")
    
    # First, try to directly get the history
    try:
        print("Fetching history directly...")
        history_url = f"{COMFYUI_SERVER_URL}/history"
        history_response = requests.get(history_url)
        
        if history_response.status_code == 200:
            print(f"Response status: {history_response.status_code}")
            
            # Print raw response text (first 1000 chars)
            raw_text = history_response.text
            print(f"Raw response (first 1000 chars):\n{raw_text[:1000]}")
            
            try:
                history_data = history_response.json()
                print(f"\nFound {len(history_data)} items in history")
                
                # Print the type of history_data
                print(f"History data type: {type(history_data)}")
                
                # Try to find our prompt ID
                found = False
                for item_id, item_data in history_data.items():
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        print(f"Found matching prompt ID: {item_id}")
                        found = True
                        
                        # Check if it has outputs
                        if "outputs" in item_data:
                            outputs = item_data["outputs"]
                            print(f"Job has outputs: {bool(outputs)}")
                            print(f"Outputs type: {type(outputs)}")
                            print(f"Outputs keys: {list(outputs.keys())}")
                            
                            # Print details of each output node
                            for node_id, node_output in outputs.items():
                                print(f"\nNode ID: {node_id}")
                                print(f"Node output type: {type(node_output)}")
                                print(f"Node output keys: {list(node_output.keys())}")
                                
                                # Check for images or gifs
                                for output_type in ['images', 'gifs']:
                                    if output_type in node_output:
                                        items = node_output[output_type]
                                        print(f"{output_type.capitalize()} count: {len(items)}")
                                        
                                        # Print details of first item
                                        if items:
                                            first_item = items[0]
                                            print(f"First {output_type[:-1]} type: {type(first_item)}")
                                            print(f"First {output_type[:-1]} keys: {list(first_item.keys())}")
                                            print(f"First {output_type[:-1]} filename: {first_item.get('filename', 'N/A')}")
                                            print(f"First {output_type[:-1]} subfolder: {first_item.get('subfolder', 'N/A')}")
                                            
                                            # Try to get the image
                                            filename = first_item.get('filename')
                                            subfolder = first_item.get('subfolder', '')
                                            if filename:
                                                print(f"Trying to get {output_type[:-1]}: {filename}")
                                                image_url = f"{COMFYUI_SERVER_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
                                                print(f"URL: {image_url}")
                                                
                                                # Try to get the file directly
                                                try:
                                                    response = requests.get(image_url)
                                                    print(f"Response status: {response.status_code}")
                                                    if response.status_code == 200:
                                                        print(f"File size: {len(response.content)} bytes")
                                                        
                                                        # Save the file
                                                        output_path = OUTPUT_DIR / filename
                                                        with open(output_path, "wb") as f:
                                                            f.write(response.content)
                                                        print(f"Saved file to: {output_path}")
                                                        return True
                                                except Exception as e:
                                                    print(f"Error getting file: {str(e)}")
                                
                        else:
                            print("Job has no outputs")
                
                if not found:
                    print(f"No matching prompt ID found for {prompt_id}")
                    
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {str(e)}")
    except Exception as e:
        print(f"Error fetching history: {str(e)}")
    
    # Check status using our function
    print("\nChecking status using check_prompt_status...")
    status_info = check_prompt_status(prompt_id, COMFYUI_SERVER_URL)
    
    print(f"Status: {status_info['status']}")
    print(f"Full prompt ID: {status_info.get('prompt_id', 'unknown')}")
    
    if status_info["status"] == "complete":
        print("✅ Job is complete!")
        
        # Get output images
        output_paths = get_output_images(
            status_info.get("prompt_id", prompt_id),
            server_url=COMFYUI_SERVER_URL,
            output_dir=OUTPUT_DIR
        )
        
        if output_paths:
            print(f"✅ Found {len(output_paths)} output files:")
            for path in output_paths:
                print(f"  - {path}")
            return True
        else:
            print("❌ No output files found")
            return False
    else:
        print(f"❌ Job is not complete. Status: {status_info['status']}")
        return False

def test_websocket_client():
    """
    Test the WebSocket client with the ComfyUI server.
    """
    print("Testing ComfyUI WebSocket client...")
    
    # Step 1: Load workflow
    print("\n=== Step 1: Loading workflow ===")
    workflow = load_workflow_file(WORKFLOW_FILE)
    if not workflow:
        print("❌ Failed to load workflow")
        return False
    
    print(f"✅ Successfully loaded workflow with {len(workflow)} nodes")
    
    # Step 2: Modify workflow
    print("\n=== Step 2: Modifying workflow ===")
    modified_workflow = modify_workflow(
        workflow,
        prompt="A beautiful mountain landscape with snow and trees, photorealistic",
        negative_prompt="ugly, blurry, distorted",
        resolution="512x512"
    )
    
    if not modified_workflow:
        print("❌ Failed to modify workflow")
        return False
    
    print("✅ Successfully modified workflow")
    
    # Step 3: Submit workflow
    print("\n=== Step 3: Submitting workflow ===")
    
    # Status tracking variables
    status_updates = []
    is_complete = False
    is_error = False
    error_message = ""
    
    # Callback functions
    def on_update(data):
        status = data.get("status", "unknown")
        status_updates.append(status)
        print(f"Status update: {status}")
        
        if status == "progress":
            percentage = data.get("percentage", 0)
            print(f"Progress: {percentage:.2f}%")
    
    def on_complete(data):
        nonlocal is_complete
        is_complete = True
        print(f"✅ Workflow execution complete!")
        print(f"Complete data: {json.dumps(data, indent=2)}")
    
    def on_error(message):
        nonlocal is_error, error_message
        is_error = True
        error_message = message
        print(f"❌ Error: {message}")
    
    # Submit workflow
    prompt_id = submit_workflow(
        modified_workflow,
        server_url=COMFYUI_SERVER_URL,
        on_update=on_update,
        on_complete=on_complete,
        on_error=on_error
    )
    
    if not prompt_id:
        print("❌ Failed to submit workflow")
        return False
    
    print(f"✅ Successfully submitted workflow with prompt ID: {prompt_id}")
    
    # Step 4: Wait for completion
    print("\n=== Step 4: Waiting for completion ===")
    
    # Wait for completion with fallback mechanism
    status_info = wait_for_prompt_completion(
        prompt_id,
        server_url=COMFYUI_SERVER_URL,
        max_wait_time=300,  # 5 minutes timeout
        check_interval=5,    # Check every 5 seconds
        on_update=on_update,
        on_complete=on_complete,
        on_error=on_error
    )
    
    if status_info["status"] != "complete":
        if status_info["status"] == "error":
            print(f"❌ Workflow execution failed: {status_info.get('error_message', 'Unknown error')}")
        else:
            print(f"❌ Workflow execution did not complete. Status: {status_info['status']}")
        return False
    
    print("✅ Workflow execution completed successfully")
    
    # Step 5: Get output images
    print("\n=== Step 5: Getting output images ===")
    output_paths = get_output_images(
        status_info.get("prompt_id", prompt_id),  # Use the full prompt ID if available
        server_url=COMFYUI_SERVER_URL,
        output_dir=OUTPUT_DIR
    )
    
    if not output_paths:
        print("❌ No output images found")
        return False
    
    print(f"✅ Successfully retrieved {len(output_paths)} output files:")
    for path in output_paths:
        print(f"  - {path}")
    
    return True

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test ComfyUI WebSocket client')
    parser.add_argument('--check-job', type=str, help='Check an existing job ID')
    args = parser.parse_args()
    
    # If a job ID is provided, check its status
    if args.check_job:
        if check_existing_job(args.check_job):
            sys.exit(0)
        else:
            sys.exit(1)
    # Otherwise run the full test
    else:
        if test_websocket_client():
            print("\n✅ All tests passed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed")
            sys.exit(1) 