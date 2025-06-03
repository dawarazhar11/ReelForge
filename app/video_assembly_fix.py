#!/usr/bin/env python3
"""
Video Assembly Fix

This script patches the Video Assembly code to fix the B-Roll image duration issue.
When run, it will apply the fix to the relevant files in the application.
"""

import os
import sys
import re
import shutil
from pathlib import Path
import subprocess
import datetime

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def patch_simple_assembly(file_path):
    """Patch the simple_assembly.py file to fix B-Roll image duration issue"""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return False
    
    # Create backup
    backup_path = backup_file(file_path)
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Define the pattern to match in the code
    pattern = re.compile(r'# Extract audio from A-Roll.*?temp_audio = os\.path\.join\(temp_dir, f"audio_{i}\.aac"\).*?cmd_audio = \[\s*"ffmpeg", "-y", "-i", aroll_path,\s*"-vn", "-c:a", "aac", "-b:a", "128k",\s*temp_audio\s*\]', re.DOTALL)
    
    # Define the replacement with the fixed code
    replacement = """# Get segment duration from the item - this is critical for correct timing
                segment_duration = item.get("duration", 0)
                segment_start = item.get("start_time", 0)
                segment_end = item.get("end_time", 0)
                
                # If we have a valid duration in the sequence item, use it
                if segment_duration > 0:
                    print(f"Using segment duration from sequence: {segment_duration}s")
                    extract_duration = segment_duration
                # If we have start and end times, calculate duration
                elif segment_end > segment_start:
                    extract_duration = segment_end - segment_start
                    print(f"Calculated duration from start/end times: {extract_duration}s")
                else:
                    # Fallback to a reasonable default (not the entire video)
                    extract_duration = 5.0
                    print(f"Using default duration: {extract_duration}s")
                
                # Extract segment-specific audio from A-Roll
                temp_audio = os.path.join(temp_dir, f"audio_{i}.aac")
                
                # If we have start_time, extract just the segment audio
                if segment_start > 0 or segment_end > 0:
                    cmd_audio = [
                        "ffmpeg", "-y", "-i", aroll_path,
                        "-ss", str(segment_start),  # Start time
                        "-t", str(extract_duration),  # Duration to extract
                        "-vn", "-c:a", "aac", "-b:a", "128k",
                        temp_audio
                    ]
                else:
                    # No timing info, extract the whole audio (fallback)
                    cmd_audio = [
                        "ffmpeg", "-y", "-i", aroll_path,
                        "-t", str(extract_duration),  # Extract only the specified duration
                        "-vn", "-c:a", "aac", "-b:a", "128k",
                        temp_audio
                    ]"""
    
    # Replace the pattern in the content
    if pattern.search(content):
        patched_content = pattern.sub(replacement, content)
        
        # Fix the "Use the exact A-Roll audio duration for the image video" part
        patched_content = patched_content.replace(
            "# Use the exact A-Roll audio duration for the image video",
            "# Use the segment duration for the image video"
        )
        
        patched_content = patched_content.replace(
            "print(f\"Creating image video with exact A-Roll audio duration: {audio_duration}s\")",
            "print(f\"Creating image video with segment duration: {extract_duration}s\")"
        )
        
        patched_content = patched_content.replace(
            "if image_to_video(broll_path, temp_video, duration=audio_duration,",
            "if image_to_video(broll_path, temp_video, duration=extract_duration,"
        )
        
        patched_content = patched_content.replace(
            "print(f\"Adding A-Roll audio to image video with exact duration: {audio_duration}s\")",
            "print(f\"Adding segment audio to image video\")"
        )
        
        # Write the patched content back to the file
        with open(file_path, 'w') as f:
            f.write(patched_content)
        
        print(f"Successfully patched {file_path}")
        return True
    else:
        print(f"Pattern not found in {file_path}, no changes made")
        return False

def patch_assembly_py(file_path):
    """Patch the assembly.py file to fix B-Roll image duration issue"""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return False
    
    # Create backup
    backup_path = backup_file(file_path)
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Define the pattern to match in the code
    pattern = re.compile(r'# Check if B-Roll is an image file.*?if is_image_file\(broll_path\):.*?# Get A-Roll audio duration to use for the image.*?aroll_audio_duration = audio_durations\.get\(segment_id, 0\)', re.DOTALL)
    
    # Define the replacement with the fixed code
    replacement = """# Check if B-Roll is an image file
                    if is_image_file(broll_path):
                        # Get segment-specific duration to use for the image
                        segment_duration = item.get("duration", 0)
                        
                        if segment_duration <= 0:
                            # If duration is not in the item, calculate from start/end time
                            segment_start = item.get("start_time", 0)
                            segment_end = item.get("end_time", 0)
                            if segment_end > segment_start:
                                segment_duration = segment_end - segment_start
                                print(f"Calculated segment duration from timestamps: {segment_duration}s")
                        
                        # If still no valid duration, fall back to audio duration
                        if segment_duration <= 0:
                            # Get A-Roll audio duration to use for the image
                            segment_duration = audio_durations.get(segment_id, 0)"""
    
    # Replace the pattern in the content
    if pattern.search(content):
        patched_content = pattern.sub(replacement, content)
        
        # Also replace uses of aroll_audio_duration with segment_duration
        patched_content = patched_content.replace(
            "if aroll_audio_duration <= 0:",
            "if segment_duration <= 0:"
        )
        
        patched_content = patched_content.replace(
            "if \"duration\" in item and item[\"duration\"] > 0:\n                                aroll_audio_duration = item[\"duration\"]\n                                print(f\"Using duration from sequence data: {aroll_audio_duration}s\")",
            "if \"duration\" in item and item[\"duration\"] > 0:\n                                segment_duration = item[\"duration\"]\n                                print(f\"Using duration from sequence data: {segment_duration}s\")"
        )
        
        patched_content = patched_content.replace(
            "aroll_audio_duration = 5.0\n                                print(f\"No valid duration found, using default: {aroll_audio_duration}s\")",
            "segment_duration = 5.0\n                                print(f\"No valid duration found, using default: {segment_duration}s\")"
        )
        
        patched_content = patched_content.replace(
            "print(f\"Creating B-Roll image video with exact A-Roll audio duration: {aroll_audio_duration}s\")",
            "print(f\"Creating B-Roll image video with exact segment duration: {segment_duration}s\")"
        )
        
        patched_content = patched_content.replace(
            "broll_clip = image_to_video(broll_path, duration=aroll_audio_duration,",
            "broll_clip = image_to_video(broll_path, duration=segment_duration,"
        )
        
        # Write the patched content back to the file
        with open(file_path, 'w') as f:
            f.write(patched_content)
        
        print(f"Successfully patched {file_path}")
        return True
    else:
        print(f"Pattern not found in {file_path}, no changes made")
        return False

def apply_patches():
    """Apply patches to fix the B-Roll image duration issue"""
    # Find the main application directory
    app_dir = Path.cwd()
    
    # Find the files to patch
    simple_assembly_path = app_dir / "utils" / "video" / "simple_assembly.py"
    assembly_path = app_dir / "utils" / "video" / "assembly.py"
    
    # Apply patches
    success = True
    if not patch_simple_assembly(simple_assembly_path):
        success = False
    
    if not patch_assembly_py(assembly_path):
        success = False
    
    if success:
        print("\n✅ Successfully applied all patches!")
        print("\nTo verify the fix:")
        print("1. Go to the Video Assembly page in the app")
        print("2. Select any sequence pattern")
        print("3. Click 'Assemble Video'")
        print("4. The assembled video should now have the correct duration matching the A-Roll content")
    else:
        print("\n⚠️ Some patches could not be applied. Please check the logs above.")

if __name__ == "__main__":
    print("Applying Video Assembly Fix...")
    apply_patches() 