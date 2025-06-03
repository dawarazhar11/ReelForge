#!/usr/bin/env python3
"""
Clear B-Roll Cache and Regenerate Assembly Sequence

This script clears any cached B-Roll data and regenerates the assembly sequence
to ensure the most recent B-Roll images are used in the video assembly process.
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

def clear_cache():
    """Clear any cached B-Roll and assembly data"""
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
    
    # Clear B-Roll entries from content status
    content_status_path = project_path / "content_status.json"
    if content_status_path.exists():
        try:
            with open(content_status_path, "r") as f:
                content_status = json.load(f)
            
            # Make backup of content status
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = content_status_path.with_suffix(f".{timestamp}.bak")
            shutil.copy2(content_status_path, backup_path)
            print(f"Created backup of content status: {backup_path}")
            
            # Update B-Roll status to use most recent files
            if "broll" in content_status:
                # Find most recent B-Roll images
                broll_dir = project_path / "media" / "broll"
                potential_broll_dirs = [
                    project_path / "media" / "broll",
                    Path("media") / "broll",
                    app_root / "media" / "broll",
                    Path("config/user_data/my_short_video/media/broll")
                ]
                
                for segment_id, segment_data in content_status["broll"].items():
                    segment_num = segment_id.split("_")[-1]
                    segment_pattern = f"broll_segment_{segment_num}_"
                    
                    all_matching_files = []
                    for broll_dir in potential_broll_dirs:
                        if broll_dir.exists():
                            for filename in os.listdir(broll_dir):
                                if segment_pattern in filename and filename.endswith(('.png', '.jpg', '.jpeg')):
                                    file_path = os.path.join(broll_dir, filename)
                                    mod_time = os.path.getmtime(file_path)
                                    all_matching_files.append((file_path, mod_time))
                    
                    # Sort by modification time (newest first)
                    all_matching_files.sort(key=lambda x: x[1], reverse=True)
                    
                    if all_matching_files:
                        newest_file = all_matching_files[0][0]
                        segment_data["file_path"] = newest_file
                        segment_data["timestamp"] = all_matching_files[0][1]
                        print(f"Updated {segment_id} to use newest file: {newest_file}")
                
                # Save updated content status
                with open(content_status_path, "w") as f:
                    json.dump(content_status, f, indent=2)
                print("Saved updated content status with latest B-Roll image paths")
        except Exception as e:
            print(f"Error updating content status: {str(e)}")
    
    print("\n✅ Cache clearing complete!")
    print("You can now run the Video Assembly step to generate a new video")
    print("using the most recent B-Roll images.")

def regenerate_assembly():
    """Generate a new video assembly with the most recent B-Roll images"""
    try:
        # Import the direct assembly function
        from video_assembly_streamlit_fix import direct_assembly
        
        print("\nRegenerating video assembly with latest B-Roll images...")
        project_path = "config/user_data/my_short_video"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"fresh_assembly_{timestamp}"
        
        output_path = direct_assembly(project_path, output_name)
        
        if output_path:
            print(f"\n✅ Assembly complete! New video saved to: {output_path}")
            return True
        else:
            print("\n⚠️ Failed to generate new assembly.")
            return False
    except Exception as e:
        print(f"\n⚠️ Error generating new assembly: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=== B-Roll Cache Cleaner ===")
    print("This script will clear cached B-Roll data and regenerate the assembly sequence.")
    
    # Clear cache
    clear_cache()
    
    # Ask if user wants to regenerate assembly
    regenerate = input("\nDo you want to regenerate the video assembly now? (y/n): ").lower() == 'y'
    if regenerate:
        regenerate_assembly()
    else:
        print("\nSkipping regeneration. You can run the Video Assembly page in Streamlit")
        print("to generate a new video with the latest B-Roll images.") 