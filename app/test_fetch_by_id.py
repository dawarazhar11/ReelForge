#!/usr/bin/env python3
"""
Test script for testing fetch_content_by_id function.
This script tests our ability to fetch generated content by prompt ID.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
import tempfile

# Add parent directory to path for imports
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Constants
COMFYUI_SERVER_URL = "http://100.115.243.42:8000"
OUTPUT_DIR = current_dir / "test_outputs" / "fetch_test"

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_content_by_id(prompt_id, api_url):
    """Fetch content from ComfyUI using prompt ID"""
    try:
        print(f"\n=== Fetching content for prompt_id: {prompt_id} ===")
        print(f"API URL: {api_url}")
        
        # First check history
        history_url = f"{api_url}/history"
        history_response = requests.get(history_url, timeout=10)
        
        if history_response.status_code != 200:
            print(f"Error fetching history: {history_response.status_code}")
            return {
                "status": "error",
                "message": f"Error fetching history: {history_response.status_code}"
            }
        
        history_data = history_response.json()
        print(f"History data type: {type(history_data).__name__}")
        
        # Get some basic info about the history data
        if isinstance(history_data, dict):
            print(f"History contains {len(history_data)} items")
            # Print first few IDs
            print(f"First few prompt IDs: {list(history_data.keys())[:3]}")
        elif isinstance(history_data, list):
            print(f"History contains {len(history_data)} items")
            # Print first few IDs if available
            prompt_ids = [item.get("prompt_id", "unknown") for item in history_data[:3] if isinstance(item, dict)]
            print(f"First few prompt IDs: {prompt_ids}")
        
        # Handle both dictionary and list formats
        job_data = None
        found_prompt_id = None
        
        # Handle dictionary format (older ComfyUI versions)
        if isinstance(history_data, dict):
            # Look for exact or partial match in the keys
            for item_id, item_data in history_data.items():
                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                    print(f"Found matching prompt ID in history: {item_id}")
                    job_data = item_data
                    found_prompt_id = item_id
                    break
        # Handle list format (newer ComfyUI versions)
        elif isinstance(history_data, list):
            for item in history_data:
                if isinstance(item, dict) and "prompt_id" in item:
                    item_id = item["prompt_id"]
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        print(f"Found matching prompt ID in history: {item_id}")
                        job_data = item
                        found_prompt_id = item_id
                        break
        
        # Check if job exists
        if not job_data:
            print(f"Prompt ID '{prompt_id}' not found in history")
            return {
                "status": "error",
                "message": "Prompt ID not found in history"
            }
        
        # Check if job completed
        outputs = job_data.get("outputs", {})
        if not outputs:
            print(f"Job still processing - no outputs available")
            return {
                "status": "processing",
                "message": "Job still processing"
            }
        
        print(f"Found outputs for prompt ID: {found_prompt_id or prompt_id}")
        print(f"Number of output nodes: {len(outputs)}")
        
        # Find output file
        for node_id, node_data in outputs.items():
            # Check for images
            if "images" in node_data:
                for image_data in node_data["images"]:
                    filename = image_data.get("filename", "")
                    
                    if filename:
                        print(f"Found image: {filename}")
                        # Download file
                        file_url = f"{api_url}/view?filename={filename}"
                        content_response = requests.get(file_url, timeout=30)
                        
                        if content_response.status_code == 200:
                            # Save to output directory
                            output_path = OUTPUT_DIR / filename
                            with open(output_path, "wb") as f:
                                f.write(content_response.content)
                            
                            print(f"Successfully downloaded image to {output_path}")
                            
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "type": "image",
                                "saved_path": str(output_path)
                            }
            
            # Check for videos
            for media_type in ["videos", "gifs"]:
                if media_type in node_data:
                    for media_item in node_data[media_type]:
                        filename = media_item.get("filename", "")
                        
                        if filename:
                            print(f"Found {media_type}: {filename}")
                            # Download file
                            file_url = f"{api_url}/view?filename={filename}"
                            content_response = requests.get(file_url, timeout=60)
                            
                            if content_response.status_code == 200:
                                # Save to output directory
                                output_path = OUTPUT_DIR / filename
                                with open(output_path, "wb") as f:
                                    f.write(content_response.content)
                                
                                print(f"Successfully downloaded video to {output_path}")
                                
                                return {
                                    "status": "success",
                                    "content": content_response.content,
                                    "filename": filename,
                                    "type": "video",
                                    "saved_path": str(output_path)
                                }
        
        # If we get here, try looking for AnimateDiff pattern files
        print("No outputs found in standard locations, checking for AnimateDiff pattern files...")
        possible_files = [f"animation_{i:05d}.mp4" for i in range(1, 10)]
        for filename in possible_files:
            file_url = f"{api_url}/view?filename={filename}"
            try:
                response = requests.head(file_url, timeout=5)
                if response.status_code == 200:
                    print(f"Found animation file: {filename}")
                    content_response = requests.get(file_url, timeout=60)
                    if content_response.status_code == 200:
                        # Save to output directory
                        output_path = OUTPUT_DIR / filename
                        with open(output_path, "wb") as f:
                            f.write(content_response.content)
                        
                        print(f"Successfully downloaded animation to {output_path}")
                        
                        return {
                            "status": "success",
                            "content": content_response.content,
                            "filename": filename,
                            "type": "video",
                            "saved_path": str(output_path)
                        }
            except Exception as e:
                print(f"Error checking alternative file {filename}: {str(e)}")
        
        print("No output files found")
        return {
            "status": "error",
            "message": "No output file found"
        }
    
    except Exception as e:
        error_msg = f"Error fetching content: {str(e)}"
        print(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }

def get_active_prompt_ids():
    """Get a list of recent prompt IDs from the history"""
    try:
        response = requests.get(f"{COMFYUI_SERVER_URL}/history")
        if response.status_code != 200:
            print(f"Error fetching history: {response.status_code}")
            return []
        
        data = response.json()
        prompt_ids = []
        
        if isinstance(data, dict):
            # Dictionary format
            prompt_ids = list(data.keys())
        elif isinstance(data, list):
            # List format
            prompt_ids = [item.get("prompt_id") for item in data if isinstance(item, dict) and "prompt_id" in item]
        
        return prompt_ids[:5]  # Return first 5 IDs
    except Exception as e:
        print(f"Error getting prompt IDs: {str(e)}")
        return []

def main():
    print("=== ComfyUI Content Fetch Test (fetch_content_by_id) ===")
    
    # Get some recent prompt IDs
    prompt_ids = get_active_prompt_ids()
    
    if not prompt_ids:
        print("No prompt IDs found in history. Using example IDs.")
        # Use IDs from the logs
        prompt_ids = [
            "68f9fa75-4198-4089-b5b4-90a09f873636",  # From logs
            "3211a05d-fb3d-42df-9ae8-af2a82ee5c10",  # From logs
            "04b1845a-b95f-4c27-a954-a253f72aa546",  # Previous ID that failed
            "3d7f0862-1aab-472f-8528-2e0c5618a8aa"   # Previous ID that failed
        ]
    
    # Add the previously failing IDs to the test
    failing_ids = [
        "68f9fa75-4198-4089-b5b4-90a09f873636",  # From logs
        "3211a05d-fb3d-42df-9ae8-af2a82ee5c10",  # From logs
        "04b1845a-b95f-4c27-a954-a253f72aa546",  # Previous ID that failed
        "3d7f0862-1aab-472f-8528-2e0c5618a8aa"   # Previous ID that failed
    ]
    
    # Combine the lists, removing duplicates
    for id in failing_ids:
        if id not in prompt_ids:
            prompt_ids.append(id)
    
    print(f"Found {len(prompt_ids)} prompt IDs: {prompt_ids}")
    
    # Try fetching content for each prompt ID
    for i, prompt_id in enumerate(prompt_ids):
        print(f"\n\n=== Testing prompt ID {i+1}/{len(prompt_ids)}: {prompt_id} ===")
        
        result = fetch_content_by_id(prompt_id, COMFYUI_SERVER_URL)
        
        print(f"\nResult for prompt ID {prompt_id}:")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"Content type: {result.get('type', 'unknown')}")
            print(f"Filename: {result.get('filename', 'unknown')}")
            print(f"Saved to: {result.get('saved_path', 'unknown')}")
        else:
            print(f"Message: {result.get('message', 'Unknown error')}")
        
        print("=" * 50)

if __name__ == "__main__":
    main() 