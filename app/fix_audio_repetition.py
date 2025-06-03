#!/usr/bin/env python3
"""
Fix Audio Repetition in Video Assembly

This script provides a solution to fix audio repetition issues in the video assembly process.
It creates a new assembly sequence that ensures each A-Roll audio segment is used exactly once.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

try:
    import streamlit as st
except ImportError:
    print("Streamlit not available, running in non-streamlit mode")
    st = None

def print_or_st(message):
    """Print message to console and streamlit if available"""
    print(message)
    if st:
        st.write(message)

def load_segments(project_path):
    """Load segments from script.json"""
    script_file = project_path / "script.json"
    if not script_file.exists():
        print_or_st(f"Script file not found: {script_file}")
        return []
    
    try:
        with open(script_file, "r") as f:
            data = json.load(f)
            return data.get("segments", [])
    except Exception as e:
        print_or_st(f"Error loading script: {str(e)}")
        return []

def load_content_status(project_path):
    """Load content status from content_status.json"""
    status_file = project_path / "content_status.json"
    if not status_file.exists():
        print_or_st(f"Content status file not found: {status_file}")
        return {}
    
    try:
        with open(status_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print_or_st(f"Error loading content status: {str(e)}")
        return {}

def get_aroll_filepath(segment_id, segment_data, project_path):
    """Get A-Roll filepath for a segment"""
    # First check if there's a direct file_path in the segment data
    if "file_path" in segment_data and os.path.exists(segment_data["file_path"]):
        return segment_data["file_path"], True, None
    
    # Check if this is a transcription-based A-Roll
    if "transcription" in segment_data or "start_time" in segment_data:
        # Look for the full A-Roll video
        full_aroll_paths = [
            project_path / "aroll_video.mp4",
            project_path / "media" / "a-roll" / "main_aroll.mp4",
            project_path / "media" / "aroll" / "main_aroll.mp4"
        ]
        for path in full_aroll_paths:
            if path.exists():
                return str(path), True, None
    
    # Check for segment-specific A-Roll in various locations
    possible_paths = [
        project_path / "aroll" / f"{segment_id}.mp4",
        project_path / "media" / "aroll" / f"{segment_id}.mp4",
        project_path / "media" / "a-roll" / f"{segment_id}.mp4",
        project_path / "media" / "a-roll" / "segments" / f"main_aroll_{segment_id}.mp4"
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path), True, None
    
    # Check for other video formats
    for ext in [".mov", ".avi", ".webm"]:
        alt_paths = [
            project_path / "aroll" / f"{segment_id}{ext}",
            project_path / "media" / "aroll" / f"{segment_id}{ext}",
            project_path / "media" / "a-roll" / f"{segment_id}{ext}"
        ]
        for path in alt_paths:
            if path.exists():
                return str(path), True, None
    
    # Check content_status for A-Roll paths
    content_status = load_content_status(project_path)
    aroll_segments = content_status.get("aroll", {})
    
    if segment_id in aroll_segments:
        aroll_data = aroll_segments[segment_id]
        file_path = aroll_data.get("file_path")
        
        if file_path:
            # Check if it's a relative path
            if not os.path.isabs(file_path):
                file_path = os.path.join(project_path, file_path)
            
            if os.path.exists(file_path):
                return file_path, True, None
            
            # Check if it's in the media directory
            media_paths = [
                os.path.join(project_path, "media", "aroll", os.path.basename(file_path)),
                os.path.join(project_path, "media", "a-roll", os.path.basename(file_path))
            ]
            for path in media_paths:
                if os.path.exists(path):
                    return path, True, None
    
    # A-Roll not found
    return None, False, f"A-Roll file not found for {segment_id}"

def get_broll_filepath(segment_id, segment_data, project_path):
    """Get B-Roll filepath for a segment"""
    # First check if there's a direct file_path in the segment data
    if "file_path" in segment_data and os.path.exists(segment_data["file_path"]):
        return segment_data["file_path"]
    
    # Check for segment-specific B-Roll in the standard location
    broll_dir = project_path / "broll"
    if broll_dir.exists():
        # Check for MP4 file
        mp4_path = broll_dir / f"{segment_id}.mp4"
        if mp4_path.exists():
            return str(mp4_path)
        
        # Check for image files
        for ext in [".png", ".jpg", ".jpeg"]:
            img_path = broll_dir / f"{segment_id}{ext}"
            if img_path.exists():
                return str(img_path)
        
        # Check for other video formats
        for ext in [".mov", ".avi", ".webm"]:
            alt_path = broll_dir / f"{segment_id}{ext}"
            if alt_path.exists():
                return str(alt_path)
    
    # B-Roll not found
    return None

def create_no_overlap_sequence(project_path):
    """
    Create a sequence that ensures no audio repetition
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        list: Assembly sequence with no audio repetition
    """
    # Load content status and segments
    content_status = load_content_status(project_path)
    script_segments = load_segments(project_path)
    
    aroll_segments = content_status.get("aroll", {})
    broll_segments = content_status.get("broll", {})
    
    # Get A-Roll script segments
    aroll_script_segments = [s for s in script_segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    
    print_or_st(f"Found {len(aroll_script_segments)} A-Roll segments and {len(broll_segments)} B-Roll segments")
    
    # Track which A-Roll segments have been used to prevent duplicates
    used_aroll_segments = set()
    assembly_sequence = []
    
    # First, identify all available A-Roll segments
    available_aroll_segments = []
    for i, segment in enumerate(aroll_script_segments):
        # Assign segment_id based on index if not present
        segment_id = segment.get("segment_id", f"segment_{i}")
        
        # If segment_id is not in the format "segment_X", create it based on index
        if not segment_id.startswith("segment_"):
            segment_id = f"segment_{i}"
            
        print_or_st(f"Processing A-Roll segment {i}: {segment_id}")
        
        aroll_path, aroll_success, aroll_error = get_aroll_filepath(segment_id, segment, project_path)
        if aroll_path:
            print_or_st(f"Found A-Roll path: {aroll_path}")
            
            # Extract timestamp information if available
            start_time = segment.get("start_time", 0)
            end_time = segment.get("end_time", 0)
            duration = segment.get("duration", end_time - start_time if end_time > start_time else 0)
            
            # If we don't have duration but have start and end times, calculate it
            if duration == 0 and end_time > start_time:
                duration = end_time - start_time
                print_or_st(f"Calculated duration: {duration}s from start_time: {start_time}s to end_time: {end_time}s")
            
            available_aroll_segments.append({
                "segment_id": segment_id,
                "segment_data": segment,
                "aroll_path": aroll_path,
                "index": i,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration
            })
        else:
            print_or_st(f"Error: {aroll_error}")
    
    print_or_st(f"Found {len(available_aroll_segments)} available A-Roll segments")
    
    # First segment is A-Roll only (if we have enough segments)
    if len(available_aroll_segments) > 0:
        first_segment = available_aroll_segments[0]
        segment_id = first_segment["segment_id"]
        aroll_path = first_segment["aroll_path"]
        
        print_or_st(f"Adding A-Roll segment 0 (ID: {segment_id}) with path: {aroll_path}")
        assembly_sequence.append({
            "type": "aroll_full",
            "aroll_path": aroll_path,
            "broll_path": None,
            "segment_id": segment_id,
            "start_time": first_segment.get("start_time", 0),
            "end_time": first_segment.get("end_time", 0),
            "duration": first_segment.get("duration", 0)
        })
        # Mark as used
        used_aroll_segments.add(segment_id)
        
        # Remove from available segments
        available_aroll_segments = available_aroll_segments[1:]
    
    # Last segment is A-Roll only (if we have enough segments)
    last_segment = None
    if len(available_aroll_segments) > 1:
        last_segment = available_aroll_segments[-1]
        available_aroll_segments = available_aroll_segments[:-1]
    
    # Middle segments use B-Roll visuals with A-Roll audio
    total_broll_segments = len(broll_segments)
    for i, aroll_segment in enumerate(available_aroll_segments):
        segment_id = aroll_segment["segment_id"]
        aroll_path = aroll_segment["aroll_path"]
        
        # Get the A-Roll duration - important for matching B-Roll image durations
        aroll_duration = aroll_segment.get("duration", 0)
        if aroll_duration == 0:
            # If we have start and end times but no duration, calculate it
            start_time = aroll_segment.get("start_time", 0)
            end_time = aroll_segment.get("end_time", 0)
            if end_time > start_time:
                aroll_duration = end_time - start_time
                print_or_st(f"Calculated A-Roll duration: {aroll_duration}s")
        
        # Use the appropriate B-Roll segment or cycle through available ones
        broll_index = i % total_broll_segments
        broll_segment_id = f"segment_{broll_index}"
        
        if broll_segment_id in broll_segments:
            broll_data = broll_segments[broll_segment_id]
            broll_path = get_broll_filepath(broll_segment_id, broll_data, project_path)
            
            if broll_path:
                # Check if B-Roll is an image - if so, we need to ensure duration matches A-Roll
                is_image = broll_path.lower().endswith(('.png', '.jpg', '.jpeg'))
                if is_image:
                    print_or_st(f"Adding B-Roll image {broll_index} with A-Roll segment {segment_id} (duration: {aroll_duration}s)")
                else:
                    print_or_st(f"Adding B-Roll segment {broll_index} with A-Roll segment {segment_id}")
                
                assembly_sequence.append({
                    "type": "broll_with_aroll_audio",
                    "aroll_path": aroll_path,
                    "broll_path": broll_path,
                    "segment_id": segment_id,
                    "broll_id": broll_segment_id,
                    "start_time": aroll_segment.get("start_time", 0),
                    "end_time": aroll_segment.get("end_time", 0),
                    "duration": aroll_duration  # Ensure duration is passed for B-Roll images
                })
                # Mark as used
                used_aroll_segments.add(segment_id)
            else:
                print_or_st(f"B-Roll file not found for {broll_segment_id}, using A-Roll visuals")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": segment_id,
                    "start_time": aroll_segment.get("start_time", 0),
                    "end_time": aroll_segment.get("end_time", 0),
                    "duration": aroll_duration
                })
                # Mark as used
                used_aroll_segments.add(segment_id)
        else:
            # If no matching B-Roll, use A-Roll visuals
            print_or_st(f"No B-Roll segment available for {segment_id}, using A-Roll visuals")
            assembly_sequence.append({
                "type": "aroll_full",
                "aroll_path": aroll_path,
                "broll_path": None,
                "segment_id": segment_id,
                "start_time": aroll_segment.get("start_time", 0),
                "end_time": aroll_segment.get("end_time", 0),
                "duration": aroll_segment.get("duration", 0)
            })
            # Mark as used
            used_aroll_segments.add(segment_id)
    
    # Add the last segment if we saved one
    if last_segment:
        segment_id = last_segment["segment_id"]
        aroll_path = last_segment["aroll_path"]
        
        print_or_st(f"Adding final A-Roll segment (ID: {segment_id}) with path: {aroll_path}")
        assembly_sequence.append({
            "type": "aroll_full",
            "aroll_path": aroll_path,
            "broll_path": None,
            "segment_id": segment_id,
            "start_time": last_segment.get("start_time", 0),
            "end_time": last_segment.get("end_time", 0),
            "duration": last_segment.get("duration", 0)
        })
        # Mark as used
        used_aroll_segments.add(segment_id)
    
    # Check for audio overlaps
    used_audio_segments = {}
    overlaps = []
    
    for i, item in enumerate(assembly_sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        
        # Track which A-Roll audio segments are being used
        if segment_id in used_audio_segments:
            overlaps.append({
                "segment": i+1, 
                "audio_id": segment_id,
                "previous_use": used_audio_segments[segment_id]["index"]+1,
                "previous_type": used_audio_segments[segment_id]["type"]
            })
        else:
            used_audio_segments[segment_id] = {
                "index": i,
                "type": item["type"]
            }
    
    if overlaps:
        print_or_st("⚠️ WARNING: Audio overlaps detected despite prevention measures!")
        for overlap in overlaps:
            print_or_st(f"  - Segment {overlap['segment']} uses the same audio ({overlap['audio_id']}) as segment {overlap['previous_use']}")
    else:
        print_or_st("✅ No audio overlaps detected in the sequence!")
    
    return assembly_sequence

def save_assembly_sequence(sequence, project_path):
    """Save the assembly sequence to a file"""
    output_file = project_path / "no_overlap_assembly.json"
    try:
        with open(output_file, "w") as f:
            json.dump({"sequence": sequence}, f, indent=2)
        print_or_st(f"✅ Assembly sequence saved to {output_file}")
        return True
    except Exception as e:
        print_or_st(f"❌ Error saving assembly sequence: {str(e)}")
        return False

def main():
    """Main function"""
    # Get project path from command line or use current directory
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        # Try to find the project directory
        current_dir = Path.cwd()
        if (current_dir / "script.json").exists() or (current_dir / "content_status.json").exists():
            project_path = current_dir
        else:
            # Check if we're in the app directory
            if (current_dir / "pages").exists() and (current_dir.name == "app"):
                # Look for user_data directories
                user_data_dir = current_dir / "config" / "user_data"
                if user_data_dir.exists():
                    # List all directories in user_data
                    projects = [d for d in user_data_dir.iterdir() if d.is_dir()]
                    if projects:
                        # Use the first project
                        project_path = projects[0]
                        print_or_st(f"Using project: {project_path}")
                    else:
                        print_or_st("No projects found in user_data directory")
                        return
                else:
                    print_or_st("User data directory not found")
                    return
            else:
                print_or_st("Project directory not found")
                return
    
    print_or_st(f"Using project path: {project_path}")
    
    # Create a sequence with no audio overlaps
    sequence = create_no_overlap_sequence(project_path)
    
    # Save the sequence
    if sequence:
        save_assembly_sequence(sequence, project_path)
        print_or_st("\nTo use this sequence:")
        print_or_st("1. Go to the Video Assembly page")
        print_or_st("2. Select 'Custom (Manual Arrangement)' in the Sequence Pattern dropdown")
        print_or_st("3. In the Custom Sequence section, click 'Import Sequence'")
        print_or_st("4. Select the 'no_overlap_assembly.json' file")
        print_or_st("5. Click 'Assemble Video'")
    else:
        print_or_st("Failed to create assembly sequence")

if __name__ == "__main__":
    main() 