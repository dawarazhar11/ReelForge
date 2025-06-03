#!/usr/bin/env python3
"""
Create a properly timed assembly sequence and assemble the video.

This script creates an assembly sequence with precise timing information for each segment
and uses the fixed image-to-video conversion logic to ensure the final video duration matches
the A-Roll content.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add the parent directory to the Python path
app_root = Path(__file__).parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

try:
    from utils.video.simple_assembly import simple_assemble_video
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)

def create_fixed_sequence(project_path):
    """Create a properly timed assembly sequence"""
    
    # Find and analyze A-Roll content
    main_aroll_path = os.path.join(project_path, "media", "a-roll", "main_aroll.mp4")
    if not os.path.exists(main_aroll_path):
        print(f"Error: Main A-Roll not found at {main_aroll_path}")
        return None
    
    # Get main A-Roll duration using ffprobe
    import subprocess
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
    
    # Find the most recent B-Roll images for each segment
    for i in range(10):  # Look for up to 10 segments
        segment_pattern = f"broll_segment_{i}_"
        
        matching_files = []
        if os.path.exists(broll_dir):
            for filename in os.listdir(broll_dir):
                if segment_pattern in filename and filename.endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(broll_dir, filename)
                    matching_files.append((file_path, os.path.getmtime(file_path)))
        
        # Sort by modification time (newest first)
        matching_files.sort(key=lambda x: x[1], reverse=True)
        
        if matching_files:
            newest_file = matching_files[0][0]
            broll_paths.append(newest_file)
            print(f"Found B-Roll image for segment {i}: {os.path.basename(newest_file)}")
    
    # If no B-Roll found in the project path, try the app directory
    if not broll_paths:
        alt_broll_dir = os.path.join("media", "broll")
        if os.path.exists(alt_broll_dir):
            for i in range(10):  # Look for up to 10 segments
                segment_pattern = f"broll_segment_{i}_"
                
                matching_files = []
                for filename in os.listdir(alt_broll_dir):
                    if segment_pattern in filename and filename.endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(alt_broll_dir, filename)
                        matching_files.append((file_path, os.path.getmtime(file_path)))
                
                # Sort by modification time (newest first)
                matching_files.sort(key=lambda x: x[1], reverse=True)
                
                if matching_files:
                    newest_file = matching_files[0][0]
                    broll_paths.append(newest_file)
                    print(f"Found B-Roll image for segment {i}: {os.path.basename(newest_file)}")
    
    print(f"Found {len(broll_paths)} B-Roll images")
    
    # Calculate segment durations
    num_segments = max(8, len(broll_paths) + 2)  # Ensure at least 8 segments
    segment_duration = total_duration / num_segments
    print(f"Dividing {total_duration}s into {num_segments} segments of {segment_duration:.2f}s each")
    
    # Create sequence
    sequence = []
    
    # First segment is A-Roll only
    sequence.append({
        "type": "aroll_full",
        "aroll_path": main_aroll_path,
        "broll_path": None,
        "segment_id": "segment_0",
        "start_time": 0,
        "end_time": segment_duration,
        "duration": segment_duration
    })
    
    # Middle segments use B-Roll with A-Roll audio
    for i in range(1, num_segments - 1):
        # Get B-Roll image (cycling through available ones if needed)
        broll_idx = (i - 1) % len(broll_paths) if broll_paths else 0
        broll_path = broll_paths[broll_idx] if broll_paths else None
        
        if broll_path:
            sequence.append({
                "type": "broll_with_aroll_audio",
                "aroll_path": main_aroll_path,
                "broll_path": broll_path,
                "segment_id": f"segment_{i}",
                "broll_id": f"segment_{broll_idx}",
                "start_time": i * segment_duration,
                "end_time": (i + 1) * segment_duration,
                "duration": segment_duration
            })
        else:
            # Fallback to A-Roll if no B-Roll available
            sequence.append({
                "type": "aroll_full",
                "aroll_path": main_aroll_path,
                "broll_path": None,
                "segment_id": f"segment_{i}",
                "start_time": i * segment_duration,
                "end_time": (i + 1) * segment_duration,
                "duration": segment_duration
            })
    
    # Last segment is A-Roll only
    sequence.append({
        "type": "aroll_full",
        "aroll_path": main_aroll_path,
        "broll_path": None,
        "segment_id": f"segment_{num_segments - 1}",
        "start_time": (num_segments - 1) * segment_duration,
        "end_time": total_duration,
        "duration": total_duration - ((num_segments - 1) * segment_duration)
    })
    
    return sequence

def main():
    """Main function"""
    print("=== Fixed Assembly Sequence Generator ===")
    
    # Get project path
    project_path = os.path.join("config", "user_data", "my_short_video")
    if not os.path.exists(project_path):
        print(f"Project path not found: {project_path}")
        return 1
    
    # Create fixed sequence
    sequence = create_fixed_sequence(project_path)
    if not sequence:
        print("Failed to create fixed sequence")
        return 1
    
    # Print sequence details
    print("\nGenerated Fixed Sequence:")
    total_duration = 0
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        item_type = item.get("type", "unknown")
        duration = item.get("duration", 0)
        start_time = item.get("start_time", 0)
        end_time = item.get("end_time", 0)
        total_duration += duration
        
        print(f"Segment {i+1}: {item_type}, ID={segment_id}, Start={start_time:.2f}s, End={end_time:.2f}s, Duration={duration:.2f}s")
    
    print(f"\nTotal expected duration: {total_duration:.2f}s")
    
    # Save sequence to file
    sequence_file = os.path.join(project_path, "fixed_exact_segments.json")
    try:
        with open(sequence_file, "w") as f:
            json.dump({"sequence": sequence}, f, indent=2)
        print(f"Saved sequence to {sequence_file}")
    except Exception as e:
        print(f"Error saving sequence: {str(e)}")
    
    # Ask user if they want to assemble the video
    assemble = input("\nAssemble video now? (y/n): ").lower() == 'y'
    if assemble:
        print("\nAssembling video...")
        
        try:
            # Define progress callback
            def progress_callback(progress, message):
                print(f"Progress: {progress}% - {message}")
            
            # Assemble the video
            result = simple_assemble_video(
                sequence=sequence,
                output_path=None,  # Use default path
                target_resolution=(1080, 1920),
                progress_callback=progress_callback
            )
            
            if result["status"] == "success":
                output_path = result["output_path"]
                print(f"\nVideo assembled successfully: {output_path}")
                
                # Copy to a more recognizable name
                new_path = os.path.join(os.path.dirname(output_path), "fixed_exact_segments_video.mp4")
                shutil.copy2(output_path, new_path)
                print(f"Copied to: {new_path}")
                
                # Check final duration
                try:
                    cmd = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", new_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    final_duration = float(result.stdout.strip())
                    print(f"\nFinal video duration: {final_duration:.2f}s (expected: {total_duration:.2f}s)")
                    
                    if abs(final_duration - total_duration) > 1.0:
                        print(f"WARNING: Final duration differs from expected by {abs(final_duration - total_duration):.2f}s")
                    else:
                        print("SUCCESS: Duration matches expected value!")
                except Exception as e:
                    print(f"Error checking final duration: {str(e)}")
                
                return 0
            else:
                print(f"\nError assembling video: {result['message']}")
                return 1
        except Exception as e:
            print(f"\nError during assembly: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 