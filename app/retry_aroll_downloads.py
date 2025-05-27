#!/usr/bin/env python3
import os
import json
import sys
import time
from pathlib import Path
from utils.heygen_api import HeyGenAPI

def main():
    """
    Retry downloading failed A-Roll segments
    """
    # Set paths
    project_dir = Path(os.path.abspath("."))  # Use current directory as project dir
    aroll_status_path = project_dir / "config" / "user_data" / "my_short_video" / "aroll_status.json"
    output_dir = project_dir / "media" / "a-roll"
    
    print(f"Status file path: {aroll_status_path}")
    print(f"Output directory: {output_dir}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get API key
    api_key = os.environ.get("HEYGEN_API_KEY", "")
    if not api_key:
        print("Error: HEYGEN_API_KEY environment variable not set")
        api_key = input("Enter your HeyGen API key: ")
        if not api_key:
            print("No API key provided. Exiting.")
            sys.exit(1)
    
    # Initialize HeyGen API client
    heygen_api = HeyGenAPI(api_key)
    
    # Load status file
    if not aroll_status_path.exists():
        print(f"Status file not found at {aroll_status_path}")
        sys.exit(1)
    
    with open(aroll_status_path, "r") as f:
        aroll_status = json.load(f)
    
    # Track updates
    updated_segments = []
    
    # Process each segment
    for segment_id, status in aroll_status.items():
        # Skip segments that are already complete
        if status.get("status") == "complete" and "file_path" in status:
            print(f"Segment {segment_id} already complete: {status['file_path']}")
            continue
        
        # Check if we have a video URL to download
        if "video_url" in status:
            video_url = status["video_url"]
            print(f"\nRetrying download for segment {segment_id}")
            print(f"URL: {video_url}")
            
            # Generate output path
            timestamp = int(time.time())
            output_path = str(output_dir / f"aroll_{segment_id}_{timestamp}.mp4")
            
            # Download the video
            print(f"Downloading to {output_path}...")
            download_result = heygen_api.download_video(video_url, output_path)
            
            if download_result["status"] == "success":
                print(f"✅ Successfully downloaded to {output_path}")
                
                # Update status
                aroll_status[segment_id].update({
                    "status": "complete",
                    "file_path": output_path,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                updated_segments.append(segment_id)
            else:
                print(f"❌ Download failed: {download_result['message']}")
        
        # If we only have a prompt ID, check status first
        elif "prompt_id" in status:
            prompt_id = status["prompt_id"]
            print(f"\nChecking status for segment {segment_id} (ID: {prompt_id})")
            
            # Check video status
            status_result = heygen_api.check_video_status(prompt_id)
            
            if status_result["status"] == "success":
                data = status_result["data"]
                video_status = data.get("status", "unknown")
                video_url = data.get("video_url", "")
                
                print(f"Status: {video_status}")
                
                if video_status.lower() in ["completed", "ready", "success", "done"] and video_url:
                    print(f"Video is ready: {video_url}")
                    
                    # Generate output path
                    timestamp = int(time.time())
                    output_path = str(output_dir / f"aroll_{segment_id}_{timestamp}.mp4")
                    
                    # Download the video
                    print(f"Downloading to {output_path}...")
                    download_result = heygen_api.download_video(video_url, output_path)
                    
                    if download_result["status"] == "success":
                        print(f"✅ Successfully downloaded to {output_path}")
                        
                        # Update status
                        aroll_status[segment_id].update({
                            "status": "complete",
                            "video_url": video_url,
                            "file_path": output_path,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        updated_segments.append(segment_id)
                    else:
                        print(f"❌ Download failed: {download_result['message']}")
                else:
                    print(f"Video not ready yet: {video_status}")
            else:
                print(f"❌ Failed to check status: {status_result['message']}")
    
    # Save updated status if there were changes
    if updated_segments:
        with open(aroll_status_path, "w") as f:
            json.dump(aroll_status, f, indent=4)
        print(f"\nUpdated status for {len(updated_segments)} segments: {', '.join(updated_segments)}")
        print(f"Status file saved to {aroll_status_path}")
    else:
        print("\nNo segments were updated")

if __name__ == "__main__":
    main() 