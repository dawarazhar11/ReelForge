#!/usr/bin/env python3
"""
Fix Assembly Sequence - Prevent First Segment Repetition

This script fixes the issue where the first segment is incorrectly repeated at the end
of the assembled video. It modifies the assembly sequence data to ensure proper ordering.
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

def fix_assembly_sequence():
    """Fix the assembly sequence to prevent first segment repetition"""
    project_path = Path("config/user_data/my_short_video")
    
    # Assembly sequence files that might contain the issue
    assembly_files = [
        project_path / "no_overlap_assembly.json",
        project_path / "assembly_data.json",
        project_path / "fixed_no_overlap_assembly.json",
        project_path / "fixed_exact_segments.json"
    ]
    
    found_files = False
    
    # Process each assembly file if it exists
    for file_path in assembly_files:
        if file_path.exists():
            found_files = True
            print(f"Processing assembly file: {file_path}")
            
            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f".{timestamp}.bak")
            try:
                shutil.copy2(file_path, backup_path)
                print(f"Created backup: {backup_path}")
                
                # Load assembly data
                with open(file_path, "r") as f:
                    assembly_data = json.load(f)
                
                # Check if this is a list (sequence of segments)
                if isinstance(assembly_data, list):
                    # Check if first segment is repeated at the end
                    if len(assembly_data) > 1 and assembly_data[0].get("segment_id") == assembly_data[-1].get("segment_id"):
                        print(f"Found repeated first segment at the end! Removing duplicate.")
                        # Remove the last element (duplicate of first segment)
                        assembly_data.pop()
                        
                        # Save fixed assembly data
                        with open(file_path, "w") as f:
                            json.dump(assembly_data, f, indent=2)
                        print(f"Fixed assembly sequence saved to {file_path}")
                    else:
                        print(f"No segment repetition found in {file_path}")
                else:
                    print(f"File {file_path} doesn't contain a sequence list. Checking for nested sequences...")
                    
                    # Check for nested sequences (some files might have different structure)
                    fixed = False
                    for key, value in assembly_data.items():
                        if isinstance(value, list) and len(value) > 1:
                            if len(value) > 1 and value[0].get("segment_id") == value[-1].get("segment_id"):
                                print(f"Found repeated first segment at the end in '{key}'! Removing duplicate.")
                                # Remove the last element (duplicate of first segment)
                                value.pop()
                                fixed = True
                    
                    if fixed:
                        # Save fixed assembly data
                        with open(file_path, "w") as f:
                            json.dump(assembly_data, f, indent=2)
                        print(f"Fixed assembly sequence saved to {file_path}")
                    else:
                        print(f"No segment repetition found in {file_path}")
                
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
    
    if not found_files:
        print("No assembly sequence files found. Try running the Video Assembly step first.")
        return False
    
    # Also check content_status.json for any sequence information
    content_status_path = project_path / "content_status.json"
    if content_status_path.exists():
        try:
            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = content_status_path.with_suffix(f".{timestamp}.bak")
            shutil.copy2(content_status_path, backup_path)
            print(f"Created backup of content status: {backup_path}")
            
            # Load content status
            with open(content_status_path, "r") as f:
                content_status = json.load(f)
            
            # Check for assembly_sequence key
            if "assembly_sequence" in content_status:
                sequence = content_status["assembly_sequence"]
                if isinstance(sequence, list) and len(sequence) > 1:
                    if sequence[0] == sequence[-1]:
                        print(f"Found repeated first segment in content_status assembly_sequence! Removing duplicate.")
                        # Remove the last element (duplicate of first segment)
                        sequence.pop()
                        content_status["assembly_sequence"] = sequence
                        
                        # Save fixed content status
                        with open(content_status_path, "w") as f:
                            json.dump(content_status, f, indent=2)
                        print(f"Fixed assembly sequence saved to {content_status_path}")
            
        except Exception as e:
            print(f"Error processing content_status.json: {str(e)}")
    
    print("\n✅ Assembly sequence fix complete!")
    print("You can now run the Video Assembly step to generate a new video")
    print("without the repeated first segment at the end.")
    return True

def clear_assembly_cache():
    """Clear assembly cache files to force regeneration"""
    project_path = Path("config/user_data/my_short_video")
    
    # Files to remove if they exist
    cache_files = [
        project_path / "no_overlap_assembly.json",
        project_path / "assembly_data.json",
        project_path / "fixed_no_overlap_assembly.json",
        project_path / "fixed_exact_segments.json"
    ]
    
    # Make backups before removing
    for file_path in cache_files:
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f".{timestamp}.bak")
            try:
                shutil.copy2(file_path, backup_path)
                print(f"Created backup: {backup_path}")
                os.remove(file_path)
                print(f"Removed cache file: {file_path}")
            except Exception as e:
                print(f"Error backing up/removing {file_path}: {str(e)}")
    
    print("\n✅ Assembly cache cleared!")
    print("You can now run the Video Assembly step to generate a new video")
    print("with the correct segment sequence.")
    return True

if __name__ == "__main__":
    print("=== Assembly Sequence Fix Tool ===")
    print("This script fixes the issue where the first segment is incorrectly repeated at the end of the video.")
    print("A backup of all modified files will be created before making changes.")
    print()
    
    print("Choose an option:")
    print("1. Fix assembly sequence (try to fix existing sequence files)")
    print("2. Clear assembly cache (force regeneration)")
    print("3. Do both (recommended)")
    print()
    
    response = input("Enter your choice (1-3): ")
    
    if response == "1":
        fix_assembly_sequence()
    elif response == "2":
        clear_assembly_cache()
    elif response == "3":
        fix_assembly_sequence()
        print("\n---\n")
        clear_assembly_cache()
    else:
        print("Invalid choice. Exiting.") 