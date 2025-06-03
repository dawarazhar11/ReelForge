#!/usr/bin/env python3
"""
Video Assembly Streamlit Fix

This script creates a fixed version of the Video Assembly functionality
that can be used directly in the Streamlit app to generate properly timed videos.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Add the parent directory to the Python path
app_root = Path(__file__).parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

def is_image_file(file_path):
    """Check if a file is an image (PNG, JPG, JPEG)"""
    if not file_path or not os.path.exists(file_path):
        return False
        
    # Check file extension
    _, ext = os.path.splitext(file_path.lower())
    return ext in ['.png', '.jpg', '.jpeg']

def image_to_video(image_path, output_path, duration=5.0, target_resolution=(1080, 1920)):
    """
    Convert an image to a video using ffmpeg with exact duration
    
    Args:
        image_path: Path to the image
        output_path: Path to save the output video
        duration: Duration of the video in seconds
        target_resolution: Target resolution (width, height)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a video from the image with the specified duration
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-t", str(duration),
            "-vf", f"scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease,pad={target_resolution[0]}:{target_resolution[1]}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]
        
        print(f"Creating video from image with exact duration: {duration}s")
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Error converting image to video: {str(e)}")
        return False

def direct_assembly(project_path, output_name=None):
    """
    Directly assemble a video with proper B-Roll image durations
    
    Args:
        project_path: Path to the project directory
        output_name: Name of the output file (without extension)
        
    Returns:
        str: Path to the assembled video or None if failed
    """
    # Find main A-Roll file
    main_aroll_path = os.path.join(project_path, "media", "a-roll", "main_aroll.mp4")
    if not os.path.exists(main_aroll_path):
        print(f"Error: Main A-Roll file not found at {main_aroll_path}")
        return None
    
    # Get main A-Roll duration
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", main_aroll_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        total_duration = float(result.stdout.strip())
        print(f"Main A-Roll duration: {total_duration}s")
    except Exception as e:
        print(f"Error getting A-Roll duration: {str(e)}")
        return None
    
    # Find B-Roll images
    broll_dir = os.path.join(project_path, "media", "broll")
    broll_paths = []
    
    # Search in multiple potential locations to find the most recent B-Roll images
    potential_broll_dirs = [
        os.path.join(project_path, "media", "broll"),
        os.path.join("media", "broll"),
        os.path.join(app_root, "media", "broll"),
        os.path.join("config", "user_data", "my_short_video", "media", "broll")
    ]
    
    # Find the most recent B-Roll images for each segment across all potential directories
    for i in range(10):  # Look for up to 10 segments
        segment_pattern = f"broll_segment_{i}_"
        
        all_matching_files = []
        
        # Search across all potential directories
        for broll_dir in potential_broll_dirs:
            if os.path.exists(broll_dir):
                for filename in os.listdir(broll_dir):
                    if segment_pattern in filename and filename.endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(broll_dir, filename)
                        # Get modification time for sorting
                        mod_time = os.path.getmtime(file_path)
                        all_matching_files.append((file_path, mod_time))
        
        # Sort all matching files by modification time (newest first)
        all_matching_files.sort(key=lambda x: x[1], reverse=True)
        
        if all_matching_files:
            newest_file = all_matching_files[0][0]
            broll_paths.append(newest_file)
            print(f"Found B-Roll image for segment {i}: {os.path.basename(newest_file)} (modified: {datetime.fromtimestamp(all_matching_files[0][1]).strftime('%Y-%m-%d %H:%M:%S')})")
    
    if not broll_paths:
        print("No B-Roll images found in any of the potential directories.")
        return None
    
    # Calculate segment durations - ensure segments are around 4 seconds
    # For A-Roll of 32 seconds, aim for 8 segments of 4 seconds each
    num_segments = max(8, len(broll_paths) + 2)  # Ensure at least 8 segments
    segment_duration = total_duration / num_segments
    print(f"Dividing {total_duration}s into {num_segments} segments of {segment_duration:.2f}s each")
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Process segments
        segment_files = []
        
        # First segment is A-Roll only
        first_segment_path = os.path.join(temp_dir, "segment_0.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-i", main_aroll_path,
            "-ss", "0",
            "-t", str(segment_duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            first_segment_path
        ], check=True, capture_output=True)
        segment_files.append(first_segment_path)
        
        # Middle segments use B-Roll with A-Roll audio
        for i in range(1, num_segments - 1):
            segment_start = i * segment_duration
            segment_end = (i + 1) * segment_duration
            current_duration = segment_end - segment_start
            
            # Get B-Roll image (cycling through available ones if needed)
            broll_idx = (i - 1) % len(broll_paths)
            broll_path = broll_paths[broll_idx]
            
            # Extract audio segment from A-Roll
            audio_path = os.path.join(temp_dir, f"audio_{i}.aac")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", main_aroll_path,
                "-ss", str(segment_start),
                "-t", str(current_duration),
                "-vn", "-c:a", "aac", "-b:a", "128k",
                audio_path
            ], check=True, capture_output=True)
            
            # Convert B-Roll image to video with exact segment duration
            broll_video_path = os.path.join(temp_dir, f"broll_{i}.mp4")
            image_to_video(broll_path, broll_video_path, duration=current_duration)
            
            # Combine B-Roll video with A-Roll audio
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", broll_video_path,
                "-i", audio_path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                segment_path
            ], check=True, capture_output=True)
            
            segment_files.append(segment_path)
        
        # Last segment is A-Roll only
        last_idx = num_segments - 1
        last_segment_path = os.path.join(temp_dir, f"segment_{last_idx}.mp4")
        last_segment_start = last_idx * segment_duration
        last_segment_duration = total_duration - last_segment_start
        
        subprocess.run([
            "ffmpeg", "-y",
            "-i", main_aroll_path,
            "-ss", str(last_segment_start),
            "-t", str(last_segment_duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            last_segment_path
        ], check=True, capture_output=True)
        segment_files.append(last_segment_path)
        
        # Create concat file
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for file_path in segment_files:
                escaped_path = file_path.replace("\\", "\\\\").replace("'", "\\'")
                f.write(f"file '{escaped_path}'\n")
        
        # Create output directory if needed
        output_dir = os.path.join(app_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Set output path
        if output_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"fixed_duration_video_{timestamp}"
        
        output_path = os.path.join(output_dir, f"{output_name}.mp4")
        
        # Concatenate all segments
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ], check=True, capture_output=True)
        
        # Check final duration
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            final_duration = float(result.stdout.strip())
            print(f"Final video duration: {final_duration:.2f}s (expected: {total_duration:.2f}s)")
            
            if abs(final_duration - total_duration) > 1.0:
                print(f"WARNING: Final duration differs from expected by {abs(final_duration - total_duration):.2f}s")
            else:
                print("SUCCESS: Duration matches expected value!")
        except Exception as e:
            print(f"Error checking final duration: {str(e)}")
        
        print(f"Video successfully assembled: {output_path}")
        return output_path

if __name__ == "__main__":
    print("=== Direct Video Assembly with Fixed B-Roll Durations ===")
    
    # Get project path
    project_path = os.path.join("config", "user_data", "my_short_video")
    if not os.path.exists(project_path):
        print(f"Project path not found: {project_path}")
        sys.exit(1)
    
    # Run the direct assembly
    output_path = direct_assembly(project_path)
    
    if output_path:
        print(f"\n✅ Video assembly completed successfully!")
        print(f"Output: {output_path}")
        sys.exit(0)
    else:
        print("\n⚠️ Video assembly failed.")
        sys.exit(1) 