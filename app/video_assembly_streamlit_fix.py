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

def is_video_file(file_path):
    """Check if a file is a video (MP4, MOV, AVI, etc.)"""
    if not file_path or not os.path.exists(file_path):
        return False
        
    # Check file extension
    _, ext = os.path.splitext(file_path.lower())
    return ext in ['.mp4', '.mov', '.avi', '.webm']

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

def resize_video(video_path, output_path, duration=None, target_resolution=(1080, 1920)):
    """
    Resize a video to the target resolution and optionally adjust its duration
    
    Args:
        video_path: Path to the input video
        output_path: Path to save the output video
        duration: Optional duration to set (or None to keep original)
        target_resolution: Target resolution (width, height)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Build the ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease,pad={target_resolution[0]}:{target_resolution[1]}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p"
        ]
        
        # Add duration parameter if specified
        if duration is not None:
            cmd.extend(["-t", str(duration)])
            print(f"Resizing video with exact duration: {duration}s")
        else:
            print(f"Resizing video keeping original duration")
        
        # Add output path
        cmd.append(output_path)
        
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Error resizing video: {str(e)}")
        return False

def prepare_broll_content(broll_path, output_path, duration, target_resolution=(1080, 1920)):
    """
    Prepare B-Roll content (image or video) for assembly
    
    Args:
        broll_path: Path to the B-Roll image or video
        output_path: Path to save the processed video
        duration: Desired duration in seconds
        target_resolution: Target resolution (width, height)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if is_image_file(broll_path):
        print(f"Processing B-Roll image: {os.path.basename(broll_path)}")
        return image_to_video(broll_path, output_path, duration, target_resolution)
    elif is_video_file(broll_path):
        print(f"Processing B-Roll video: {os.path.basename(broll_path)}")
        return resize_video(broll_path, output_path, duration, target_resolution)
    else:
        print(f"Unsupported B-Roll content type: {broll_path}")
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
    
    # Find B-Roll images and videos
    broll_dir = os.path.join(project_path, "media", "broll")
    broll_paths = []
    
    # Search in multiple potential locations to find the most recent B-Roll content
    potential_broll_dirs = [
        os.path.join(project_path, "media", "broll"),
        os.path.join("media", "broll"),
        os.path.join(app_root, "media", "broll"),
        os.path.join("config", "user_data", "my_short_video", "media", "broll")
    ]
    
    # File extensions to check
    video_extensions = ['.mp4', '.mov', '.avi', '.webm']
    image_extensions = ['.png', '.jpg', '.jpeg']
    
    # Find the most recent B-Roll content for each segment across all potential directories
    for i in range(10):  # Look for up to 10 segments
        segment_pattern = f"broll_segment_{i}_"
        
        matching_videos = []
        matching_images = []
        
        # Search across all potential directories
        for broll_dir in potential_broll_dirs:
            if os.path.exists(broll_dir):
                for filename in os.listdir(broll_dir):
                    if segment_pattern in filename:
                        file_path = os.path.join(broll_dir, filename)
                        file_ext = os.path.splitext(filename)[1].lower()
                        # Get modification time for sorting
                        mod_time = os.path.getmtime(file_path)
                        
                        if file_ext in video_extensions:
                            matching_videos.append((file_path, mod_time))
                            print(f"Found B-Roll video for segment {i}: {filename}")
                        elif file_ext in image_extensions:
                            matching_images.append((file_path, mod_time))
                            print(f"Found B-Roll image for segment {i}: {filename}")
        
        # Sort by modification time (newest first)
        matching_videos.sort(key=lambda x: x[1], reverse=True)
        matching_images.sort(key=lambda x: x[1], reverse=True)
        
        # Prioritize videos over images
        if matching_videos:
            newest_file = matching_videos[0][0]
            broll_paths.append(newest_file)
            print(f"Using B-Roll VIDEO for segment {i}: {os.path.basename(newest_file)} (modified: {datetime.fromtimestamp(matching_videos[0][1]).strftime('%Y-%m-%d %H:%M:%S')})")
        elif matching_images:
            newest_file = matching_images[0][0]
            broll_paths.append(newest_file)
            print(f"Using B-Roll IMAGE for segment {i}: {os.path.basename(newest_file)} (modified: {datetime.fromtimestamp(matching_images[0][1]).strftime('%Y-%m-%d %H:%M:%S')})")
    
    if not broll_paths:
        print("No B-Roll content found in any of the potential directories.")
        return None
    
    # Calculate segment durations - ensure segments are around 4 seconds
    # For A-Roll of 32 seconds, aim for 8 segments of 4 seconds each
    num_segments = max(8, len(broll_paths) + 2)  # Ensure at least 8 segments
    segment_duration = total_duration / num_segments
    print(f"Dividing {total_duration}s into {num_segments} segments of {segment_duration:.2f}s each")
    
    # Define audio crossfade duration (in seconds)
    crossfade_duration = 0.3  # 300ms crossfade between segments
    print(f"Using {crossfade_duration}s crossfade between audio segments to smooth transitions")
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Process segments
        segment_files = []
        audio_files = []
        
        # First extract the full audio track for smoother transitions
        full_audio_path = os.path.join(temp_dir, "full_audio.aac")
        subprocess.run([
            "ffmpeg", "-y",
            "-i", main_aroll_path,
            "-vn", "-c:a", "aac", "-b:a", "192k",
            full_audio_path
        ], check=True, capture_output=True)
        
        # First segment is A-Roll only
        first_segment_path = os.path.join(temp_dir, "segment_0.mp4")
        # Extract with slight overlap for crossfade
        segment_end = segment_duration + (crossfade_duration/2)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", main_aroll_path,
            "-ss", "0",
            "-t", str(segment_end),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            first_segment_path
        ], check=True, capture_output=True)
        segment_files.append(first_segment_path)
        
        # Middle segments use B-Roll with A-Roll audio
        for i in range(1, num_segments - 1):
            # Calculate segment times with overlap for crossfading
            segment_start = i * segment_duration - (crossfade_duration/2)
            segment_end = (i + 1) * segment_duration + (crossfade_duration/2)
            
            # Ensure we don't go below 0 or beyond total duration
            segment_start = max(0, segment_start)
            segment_end = min(total_duration, segment_end)
            
            current_duration = segment_end - segment_start
            
            # Get B-Roll image/video (cycling through available ones if needed)
            broll_idx = (i - 1) % len(broll_paths)
            broll_path = broll_paths[broll_idx]
            
            # Extract audio segment from A-Roll with overlap for crossfade
            audio_path = os.path.join(temp_dir, f"audio_{i}.aac")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", main_aroll_path,
                "-ss", str(segment_start),
                "-t", str(current_duration),
                "-vn", "-c:a", "aac", "-b:a", "192k",
                audio_path
            ], check=True, capture_output=True)
            audio_files.append(audio_path)
            
            # Process B-Roll content based on type
            broll_video_path = os.path.join(temp_dir, f"broll_{i}.mp4")
            # Use the exact A-Roll segment duration (without the crossfade overlap)
            exact_segment_duration = min((i + 1) * segment_duration, total_duration) - (i * segment_duration)
            prepare_broll_content(broll_path, broll_video_path, exact_segment_duration)
            
            # Combine B-Roll video with A-Roll audio
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", broll_video_path,
                "-i", audio_path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                segment_path
            ], check=True, capture_output=True)
            
            segment_files.append(segment_path)
        
        # Last segment is A-Roll only
        last_idx = num_segments - 1
        last_segment_path = os.path.join(temp_dir, f"segment_{last_idx}.mp4")
        # Extract with overlap for crossfade
        last_segment_start = last_idx * segment_duration - (crossfade_duration/2)
        last_segment_start = max(0, last_segment_start)
        last_segment_duration = total_duration - (last_idx * segment_duration) + (crossfade_duration/2)
        
        subprocess.run([
            "ffmpeg", "-y",
            "-i", main_aroll_path,
            "-ss", str(last_segment_start),
            "-t", str(last_segment_duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            last_segment_path
        ], check=True, capture_output=True)
        segment_files.append(last_segment_path)
        
        # Create a complex filtergraph for crossfading
        if num_segments > 1:
            print("Creating smooth audio crossfades between segments...")
            # Create a filter complex file for concatenation with crossfades
            filter_complex_file = os.path.join(temp_dir, "filter_complex.txt")
            
            # Option 1: Create improved filter complex for direct concatenation with crossfades
            filter_text = ""
            for i, segment in enumerate(segment_files):
                filter_text += f"[{i}:v]setpts=PTS-STARTPTS[v{i}];\n"
                filter_text += f"[{i}:a]asetpts=PTS-STARTPTS[a{i}];\n"
            
            # Video concatenation (simple)
            video_inputs = "".join(f"[v{i}]" for i in range(len(segment_files)))
            filter_text += f"{video_inputs}concat=n={len(segment_files)}:v=1:a=0[v_out];\n"
            
            # Audio concatenation with crossfades
            # First segment
            filter_text += f"[a0]"
            
            # Middle segments with crossfades
            for i in range(1, len(segment_files)):
                # Apply crossfade between segments
                filter_text += f"[a{i}]acrossfade=d={crossfade_duration}:c1=tri:c2=tri"
                
                # Add output label if it's not the last segment
                if i < len(segment_files) - 1:
                    filter_text += f"[a_tmp{i}];\n[a_tmp{i}]"
            
            # Final output label
            filter_text += "[a_out]"
            
            # Write filter complex to file
            with open(filter_complex_file, 'w') as f:
                f.write(filter_text)
            
            # Create output directory if needed
            output_dir = os.path.join(app_root, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Set output path
            if output_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_name = f"fixed_duration_video_{timestamp}"
            
            output_path = os.path.join(output_dir, f"{output_name}.mp4")
            
            # Build ffmpeg input arguments
            input_args = []
            for segment in segment_files:
                input_args.extend(["-i", segment])
            
            # Run ffmpeg with filter complex
            ffmpeg_command = [
                "ffmpeg", "-y",
            ] + input_args + [
                "-filter_complex_script", filter_complex_file,
                "-map", "[v_out]",
                "-map", "[a_out]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                output_path
            ]
            
            subprocess.run(ffmpeg_command, check=True, capture_output=True)
        else:
            # If only one segment, just copy it to the output
            output_dir = os.path.join(app_root, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            if output_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_name = f"fixed_duration_video_{timestamp}"
            
            output_path = os.path.join(output_dir, f"{output_name}.mp4")
            
            shutil.copy2(segment_files[0], output_path)
        
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
        
        print(f"Video successfully assembled with smooth audio transitions: {output_path}")
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