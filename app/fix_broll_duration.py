#!/usr/bin/env python3
"""
Fix B-Roll Duration Issues

This script forces the video assembly to use the fixed sequence with proper durations.
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

try:
    from utils.video.assembly import assemble_video
    from utils.video.simple_assembly import simple_assemble_video
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)

def main():
    """Main function"""
    print("=== B-Roll Duration Fix ===")
    
    # Load the fixed sequence
    sequence_path = "config/user_data/my_short_video/fixed_no_overlap_assembly.json"
    if not os.path.exists(sequence_path):
        print(f"Error: Fixed sequence file not found at {sequence_path}")
        return 1
    
    try:
        with open(sequence_path, "r") as f:
            data = json.load(f)
            sequence = data.get("sequence", [])
        
        if not sequence:
            print("Error: No sequence found in the fixed assembly file")
            return 1
        
        print(f"Loaded sequence with {len(sequence)} segments")
        
        # Print sequence details
        total_duration = 0
        for i, item in enumerate(sequence):
            segment_id = item.get("segment_id", f"segment_{i}")
            item_type = item.get("type", "unknown")
            duration = item.get("duration", 0)
            total_duration += duration
            
            print(f"Segment {i+1}: {item_type}, ID={segment_id}, Duration={duration:.2f}s")
        
        print(f"Total expected duration: {total_duration:.2f}s")
        
        # Ask which assembly method to use
        use_simple = input("Use simple assembly (y/n)? ").lower() == 'y'
        
        # Assemble the video
        print("Assembling video...")
        
        if use_simple:
            result = simple_assemble_video(sequence)
        else:
            result = assemble_video(sequence)
        
        if result["status"] == "success":
            output_path = result["output_path"]
            print(f"Video assembled successfully: {output_path}")
            
            # Copy to a more recognizable name
            new_path = os.path.join(os.path.dirname(output_path), "fixed_duration_video.mp4")
            shutil.copy2(output_path, new_path)
            print(f"Copied to: {new_path}")
            
            return 0
        else:
            print(f"Error: {result['message']}")
            return 1
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 