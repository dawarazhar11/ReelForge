#!/usr/bin/env python3
"""
Fix Duration Issues in Assembly Sequences

This script analyzes assembly sequences and ensures that B-Roll images have
the correct duration information matching their corresponding A-Roll audio segments.

Usage:
    python fix_duration_issues.py [path_to_project]
"""

import os
import sys
import json
from pathlib import Path
import subprocess
import argparse

# Check if we're running in Streamlit
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = False  # Force non-Streamlit mode for command line usage
except ImportError:
    STREAMLIT_AVAILABLE = False

def print_or_st(message):
    """Print to console or Streamlit depending on environment"""
    if STREAMLIT_AVAILABLE and 'st' in globals():
        st.write(message)
    else:
        print(message)

def is_image_file(file_path):
    """Check if a file is an image (PNG, JPG, JPEG)"""
    if not file_path or not os.path.exists(file_path):
        return False
        
    # Check file extension
    _, ext = os.path.splitext(file_path.lower())
    return ext in ['.png', '.jpg', '.jpeg']

def get_video_duration(video_path):
    """Get the duration of a video file using ffprobe"""
    if not os.path.exists(video_path):
        return None
        
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.SubprocessError, ValueError) as e:
        print_or_st(f"Error getting video duration: {str(e)}")
        return None

def get_aroll_filepath(segment_id, project_path):
    """Find A-Roll filepath for a given segment ID"""
    # Check multiple potential paths
    potential_paths = [
        os.path.join(project_path, "media", "a-roll", f"{segment_id}.mp4"),
        os.path.join(project_path, "media", "aroll", f"{segment_id}.mp4"),
        os.path.join(project_path, "config/user_data/my_short_video/media/a-roll", f"{segment_id}.mp4")
    ]
    
    # Extract segment number for alternative naming patterns
    segment_num = segment_id.split('_')[-1] if '_' in segment_id else segment_id
    
    # Add alternative naming patterns
    alt_patterns = [
        os.path.join(project_path, "media", "a-roll", f"segment_{segment_num}.mp4"),
        os.path.join(project_path, "media", "a-roll", f"aroll_segment_{segment_num}_*.mp4"),
        os.path.join(project_path, "media", "a-roll", f"fetched_aroll_segment_{segment_num}_*.mp4"),
    ]
    
    # Check direct paths first
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Check alternative patterns using glob
    import glob
    for pattern in alt_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    
    return None

def analyze_sequence(sequence):
    """
    Analyze an assembly sequence for duration issues
    
    Args:
        sequence: List of video segments to assemble
        
    Returns:
        dict: Analysis results
    """
    results = {
        "total_segments": len(sequence),
        "aroll_segments": 0,
        "broll_segments": 0,
        "broll_images": 0,
        "aroll_duration": 0,
        "broll_duration": 0,
        "total_duration": 0,
        "duration_issues": []
    }
    
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        item_type = item.get("type", "unknown")
        aroll_path = item.get("aroll_path", "")
        broll_path = item.get("broll_path", "")
        item_duration = item.get("duration", 0)
        
        # Get A-Roll duration
        aroll_duration = None
        if aroll_path and os.path.exists(aroll_path):
            aroll_duration = get_video_duration(aroll_path)
            
        if item_type == "aroll_full":
            results["aroll_segments"] += 1
            
            if aroll_duration:
                results["aroll_duration"] += aroll_duration
                results["total_duration"] += aroll_duration
                
                # Check if the item has correct duration info
                if item_duration == 0 or abs(item_duration - aroll_duration) > 0.5:
                    results["duration_issues"].append({
                        "segment": i,
                        "segment_id": segment_id,
                        "type": "aroll_full",
                        "issue": "Missing or incorrect duration",
                        "item_duration": item_duration,
                        "actual_duration": aroll_duration
                    })
        
        elif item_type == "broll_with_aroll_audio":
            results["broll_segments"] += 1
            
            # Check if B-Roll is an image
            if broll_path and is_image_file(broll_path):
                results["broll_images"] += 1
                
                # For images, we should use the A-Roll audio duration
                if aroll_duration and item_duration > 0 and abs(item_duration - aroll_duration) > 0.5:
                    results["duration_issues"].append({
                        "segment": i,
                        "segment_id": segment_id,
                        "type": "broll_image",
                        "issue": "Image duration doesn't match A-Roll audio",
                        "item_duration": item_duration,
                        "aroll_duration": aroll_duration
                    })
            else:
                # For B-Roll videos, check if they match A-Roll audio duration
                broll_duration = get_video_duration(broll_path) if broll_path and os.path.exists(broll_path) else None
                
                if broll_duration:
                    results["broll_duration"] += broll_duration
                    results["total_duration"] += broll_duration
                    
                    # Check if B-Roll video is longer than A-Roll audio
                    if aroll_duration and broll_duration > aroll_duration:
                        results["duration_issues"].append({
                            "segment": i,
                            "segment_id": segment_id,
                            "type": "broll_video",
                            "issue": "B-Roll video longer than A-Roll audio",
                            "broll_duration": broll_duration,
                            "aroll_duration": aroll_duration
                        })
    
    return results

def fix_sequence_durations(sequence, project_path):
    """
    Fix duration issues in an assembly sequence
    
    Args:
        sequence: List of video segments to assemble
        project_path: Path to the project directory
        
    Returns:
        tuple: (fixed_sequence, changes_made)
    """
    fixed_sequence = []
    changes_made = 0
    
    for i, item in enumerate(sequence):
        fixed_item = item.copy()
        segment_id = item.get("segment_id", f"segment_{i}")
        item_type = item.get("type", "unknown")
        aroll_path = item.get("aroll_path", "")
        broll_path = item.get("broll_path", "")
        
        # Get A-Roll duration
        aroll_duration = None
        if aroll_path and os.path.exists(aroll_path):
            aroll_duration = get_video_duration(aroll_path)
        
        # If we couldn't get the duration from the file, try to find the file by segment ID
        if aroll_duration is None and segment_id:
            alt_aroll_path = get_aroll_filepath(segment_id, project_path)
            if alt_aroll_path:
                aroll_duration = get_video_duration(alt_aroll_path)
                print_or_st(f"Found alternative A-Roll path for {segment_id}: {alt_aroll_path}")
        
        if aroll_duration:
            # Update duration information
            if "duration" not in fixed_item or fixed_item["duration"] == 0 or abs(fixed_item["duration"] - aroll_duration) > 0.5:
                fixed_item["duration"] = aroll_duration
                changes_made += 1
                print_or_st(f"Updated duration for segment {i} ({segment_id}): {aroll_duration:.2f}s")
            
            # Also update start/end times if missing
            if "start_time" not in fixed_item or fixed_item["start_time"] == 0:
                fixed_item["start_time"] = 0
                changes_made += 1
            
            if "end_time" not in fixed_item or fixed_item["end_time"] == 0:
                fixed_item["end_time"] = aroll_duration
                changes_made += 1
        
        fixed_sequence.append(fixed_item)
    
    return fixed_sequence, changes_made

def load_assembly_sequence(project_path):
    """Load assembly sequence from the project directory"""
    # Check multiple potential paths
    potential_paths = [
        os.path.join(project_path, "assembly_sequence.json"),
        os.path.join(project_path, "output", "assembly_sequence.json"),
        os.path.join(project_path, "config", "user_data", "assembly_sequence.json"),
        os.path.join(project_path, "config", "user_data", "my_short_video", "assembly_sequence.json")
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    sequence = json.load(f)
                print_or_st(f"Loaded assembly sequence from {path}")
                return sequence, path
            except json.JSONDecodeError:
                print_or_st(f"Error: {path} is not a valid JSON file")
    
    print_or_st("No assembly sequence found in the project directory")
    return None, None

def save_assembly_sequence(sequence, output_path):
    """Save assembly sequence to a file"""
    try:
        with open(output_path, "w") as f:
            json.dump(sequence, f, indent=2)
        print_or_st(f"Saved fixed assembly sequence to {output_path}")
        return True
    except Exception as e:
        print_or_st(f"Error saving assembly sequence: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Fix duration issues in assembly sequences")
    parser.add_argument("project_path", nargs="?", default=os.getcwd(), help="Path to the project directory")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze, don't fix")
    parser.add_argument("--output", help="Output path for fixed sequence")
    
    args = parser.parse_args()
    
    # Get project path
    project_path = args.project_path
    if not os.path.isdir(project_path):
        print_or_st(f"Error: {project_path} is not a valid directory")
        return 1
    
    # Load assembly sequence
    sequence, sequence_path = load_assembly_sequence(project_path)
    if not sequence:
        return 1
    
    # Analyze sequence
    print_or_st("\n=== Analyzing Assembly Sequence ===")
    analysis = analyze_sequence(sequence)
    
    print_or_st(f"Total segments: {analysis['total_segments']}")
    print_or_st(f"A-Roll segments: {analysis['aroll_segments']}")
    print_or_st(f"B-Roll segments: {analysis['broll_segments']} (including {analysis['broll_images']} images)")
    print_or_st(f"Total A-Roll duration: {analysis['aroll_duration']:.2f}s")
    print_or_st(f"Total B-Roll duration: {analysis['broll_duration']:.2f}s")
    print_or_st(f"Estimated total duration: {analysis['total_duration']:.2f}s")
    
    # Report issues
    if analysis["duration_issues"]:
        print_or_st(f"\nFound {len(analysis['duration_issues'])} duration issues:")
        for issue in analysis["duration_issues"]:
            print_or_st(f"  - Segment {issue['segment']} ({issue['segment_id']}): {issue['issue']}")
            if "item_duration" in issue:
                print_or_st(f"    Current duration: {issue['item_duration']:.2f}s")
            if "actual_duration" in issue:
                print_or_st(f"    Actual duration: {issue['actual_duration']:.2f}s")
            if "aroll_duration" in issue:
                print_or_st(f"    A-Roll duration: {issue['aroll_duration']:.2f}s")
            if "broll_duration" in issue:
                print_or_st(f"    B-Roll duration: {issue['broll_duration']:.2f}s")
    else:
        print_or_st("\nNo duration issues found!")
        return 0
    
    # Fix issues if not in analyze-only mode
    if not args.analyze_only:
        print_or_st("\n=== Fixing Duration Issues ===")
        fixed_sequence, changes_made = fix_sequence_durations(sequence, project_path)
        
        if changes_made > 0:
            print_or_st(f"Made {changes_made} changes to fix duration issues")
            
            # Determine output path
            if args.output:
                output_path = args.output
            else:
                # Create a new filename based on the original
                if sequence_path:
                    base_path, ext = os.path.splitext(sequence_path)
                    output_path = f"{base_path}_fixed{ext}"
                else:
                    output_path = os.path.join(project_path, "assembly_sequence_fixed.json")
            
            # Save fixed sequence
            save_assembly_sequence(fixed_sequence, output_path)
        else:
            print_or_st("No changes needed to fix duration issues")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 