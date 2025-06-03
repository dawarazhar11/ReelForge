#!/usr/bin/env python3
"""
Check B-Roll Videos

This script helps verify that B-Roll videos are properly detected and prioritized over images.
It will list all B-Roll content found, clear the cache, and update the content status to use videos.
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

def check_broll_content():
    """Check all B-Roll content and identify videos vs images"""
    print("=== B-Roll Content Checker ===")
    project_path = Path("config/user_data/my_short_video")
    
    # Potential B-Roll directories to check
    potential_dirs = [
        project_path / "media" / "broll",
        Path("media") / "broll",
        app_root / "media" / "broll",
        Path("config/user_data/my_short_video/media/broll")
    ]
    
    # File extensions to look for
    video_extensions = ['.mp4', '.mov', '.avi', '.webm']
    image_extensions = ['.png', '.jpg', '.jpeg']
    
    videos_found = []
    images_found = []
    
    for directory in potential_dirs:
        if directory.exists():
            print(f"\nChecking directory: {directory}")
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(filename)[1].lower()
                    mod_time = os.path.getmtime(file_path)
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                    
                    if file_ext in video_extensions:
                        print(f"  VIDEO: {filename} (modified: {mod_time_str})")
                        videos_found.append((file_path, mod_time, filename))
                    elif file_ext in image_extensions:
                        print(f"  IMAGE: {filename} (modified: {mod_time_str})")
                        images_found.append((file_path, mod_time, filename))
    
    # Summarize findings
    print("\n=== Summary ===")
    print(f"Found {len(videos_found)} B-Roll video files")
    print(f"Found {len(images_found)} B-Roll image files")
    
    # Group by segment
    segment_groups = {}
    
    for file_path, mod_time, filename in videos_found + images_found:
        # Try to extract segment number
        segment_id = None
        for segment_num in range(10):  # Check for up to 10 segments
            if f"segment_{segment_num}" in filename:
                segment_id = f"segment_{segment_num}"
                break
        
        if segment_id:
            if segment_id not in segment_groups:
                segment_groups[segment_id] = {"videos": [], "images": []}
            
            if os.path.splitext(filename)[1].lower() in video_extensions:
                segment_groups[segment_id]["videos"].append((file_path, mod_time, filename))
            else:
                segment_groups[segment_id]["images"].append((file_path, mod_time, filename))
    
    # Show content by segment
    print("\n=== Content by Segment ===")
    for segment_id, content in segment_groups.items():
        print(f"\n{segment_id}:")
        if content["videos"]:
            print(f"  Videos ({len(content['videos'])}):")
            for file_path, mod_time, filename in sorted(content["videos"], key=lambda x: x[1], reverse=True):
                mod_time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                print(f"    - {filename} (modified: {mod_time_str})")
        
        if content["images"]:
            print(f"  Images ({len(content['images'])}):")
            for file_path, mod_time, filename in sorted(content["images"], key=lambda x: x[1], reverse=True):
                mod_time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                print(f"    - {filename} (modified: {mod_time_str})")
    
    return videos_found, images_found, segment_groups

def update_content_status():
    """Update content_status.json to prioritize videos"""
    project_path = Path("config/user_data/my_short_video")
    content_status_path = project_path / "content_status.json"
    
    if not content_status_path.exists():
        print(f"Content status file not found at {content_status_path}")
        return False
    
    try:
        # Load current content status
        with open(content_status_path, "r") as f:
            content_status = json.load(f)
        
        # Create backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = content_status_path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(content_status_path, backup_path)
        print(f"Created backup of content status: {backup_path}")
        
        # Check if "broll" section exists
        if "broll" not in content_status:
            print("No 'broll' section found in content status")
            return False
        
        # Import get_broll_filepath function
        sys.path.insert(0, str(app_root / "pages"))
        try:
            # Create a dummy module with only the necessary imports
            import types
            dummy_module = types.ModuleType("dummy_module")
            dummy_module.__dict__["os"] = os
            dummy_module.__dict__["Path"] = Path
            dummy_module.__dict__["datetime"] = datetime
            dummy_module.__dict__["project_path"] = project_path
            dummy_module.__dict__["app_root"] = app_root
            
            # Define a simplified version of get_broll_filepath that just prioritizes videos
            def find_best_broll_file(segment_id):
                """Find the best B-Roll file for a segment, prioritizing videos over images"""
                video_extensions = ['.mp4', '.mov', '.avi', '.webm']
                image_extensions = ['.png', '.jpg', '.jpeg']
                potential_dirs = [
                    project_path / "media" / "broll",
                    Path("media") / "broll",
                    app_root / "media" / "broll"
                ]
                
                segment_num = segment_id.split('_')[-1]
                base_patterns = [
                    f"broll_segment_{segment_num}",
                    f"fetched_broll_segment_{segment_num}",
                    f"broll_video_segment_{segment_num}",
                    f"image_{segment_num}",
                    f"broll_{segment_num}",
                    f"video_{segment_num}"
                ]
                
                # Find matching videos and images
                matching_videos = []
                matching_images = []
                
                for directory in potential_dirs:
                    if directory.exists():
                        for filename in os.listdir(directory):
                            if any(pattern in filename for pattern in base_patterns):
                                file_path = os.path.join(directory, filename)
                                file_ext = os.path.splitext(filename)[1].lower()
                                mod_time = os.path.getmtime(file_path)
                                
                                if file_ext in video_extensions:
                                    matching_videos.append((file_path, mod_time))
                                elif file_ext in image_extensions:
                                    matching_images.append((file_path, mod_time))
                
                # Sort by modification time (newest first)
                matching_videos.sort(key=lambda x: x[1], reverse=True)
                matching_images.sort(key=lambda x: x[1], reverse=True)
                
                # Return the newest video if available, otherwise the newest image
                if matching_videos:
                    return matching_videos[0][0], "video"
                elif matching_images:
                    return matching_images[0][0], "image"
                
                return None, None
            
            # Update each B-Roll segment
            updated_count = 0
            for segment_id, segment_data in content_status["broll"].items():
                best_file, content_type = find_best_broll_file(segment_id)
                
                if best_file:
                    old_file = segment_data.get("file_path", None)
                    old_type = segment_data.get("content_type", "unknown")
                    
                    # Update only if needed
                    if best_file != old_file or content_type != old_type:
                        segment_data["file_path"] = best_file
                        segment_data["content_type"] = content_type
                        segment_data["timestamp"] = os.path.getmtime(best_file)
                        print(f"Updated {segment_id} to use {content_type}: {os.path.basename(best_file)}")
                        updated_count += 1
            
            # Save updated content status
            with open(content_status_path, "w") as f:
                json.dump(content_status, f, indent=2)
            
            print(f"\nUpdated {updated_count} B-Roll segments in content status")
            return True
            
        except Exception as e:
            print(f"Error updating content status: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
            
    except Exception as e:
        print(f"Error loading content status: {str(e)}")
        return False

def clear_assembly_cache():
    """Clear any cached assembly data"""
    project_path = Path("config/user_data/my_short_video")
    
    # Files to remove if they exist
    cache_files = [
        project_path / "no_overlap_assembly.json",
        project_path / "assembly_data.json",
        project_path / "fixed_no_overlap_assembly.json",
        project_path / "fixed_exact_segments.json"
    ]
    
    removed_count = 0
    for file_path in cache_files:
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f".{timestamp}.bak")
            try:
                shutil.copy2(file_path, backup_path)
                print(f"Created backup: {backup_path}")
                os.remove(file_path)
                print(f"Removed cache file: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"Error backing up/removing {file_path}: {str(e)}")
    
    print(f"\nRemoved {removed_count} cache files")
    return removed_count > 0

def run_video_assembly():
    """Run the fixed video assembly process"""
    try:
        # Import the direct assembly function
        from video_assembly_streamlit_fix import direct_assembly
        
        print("\nRunning video assembly with latest B-Roll content...")
        project_path = "config/user_data/my_short_video"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"broll_video_assembly_{timestamp}"
        
        output_path = direct_assembly(project_path, output_name)
        
        if output_path:
            print(f"\n✅ Assembly complete! New video saved to: {output_path}")
            return True
        else:
            print("\n⚠️ Failed to generate new assembly.")
            return False
    except Exception as e:
        print(f"\n⚠️ Error running video assembly: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=== B-Roll Video Checker and Updater ===")
    print("This script will check for B-Roll videos, update content status, and clear the cache.")
    
    # Check B-Roll content
    videos, images, segments = check_broll_content()
    
    # Update content status
    if update_content_status():
        print("\n✅ Content status updated to prioritize videos!")
    
    # Clear assembly cache
    if clear_assembly_cache():
        print("\n✅ Assembly cache cleared!")
    
    # Ask if user wants to run video assembly
    run_assembly = input("\nDo you want to run video assembly now with the updated settings? (y/n): ").lower() == 'y'
    if run_assembly:
        run_video_assembly()
    else:
        print("\nSkipping video assembly. You can run the Video Assembly page in Streamlit")
        print("to generate a new video with the latest B-Roll videos.") 