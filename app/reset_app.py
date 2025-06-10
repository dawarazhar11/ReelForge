import os
import json
import shutil
from pathlib import Path
import time

def reset_app_state():
    """
    Completely reset the application state to ensure a clean start.
    This script can be run before starting the app to fix workflow issues.
    """
    print("Starting app reset process...")
    
    # Clear user data progress
    user_data_path = Path("config/user_data")
    if user_data_path.exists():
        # Reset progress tracking
        progress_path = user_data_path / "progress.json"
        if progress_path.exists():
            try:
                # Create a backup before modifying
                backup_path = progress_path.with_suffix(f".json.bak.{int(time.time())}")
                shutil.copy2(progress_path, backup_path)
                # Create fresh progress file with all steps marked incomplete
                progress_data = {}
                with open(progress_path, "w") as f:
                    json.dump(progress_data, f, indent=4)
                print(f"Reset progress tracking file: {progress_path}")
            except Exception as e:
                print(f"Error resetting progress file: {e}")
        
        # Process all project directories
        projects = [d for d in user_data_path.iterdir() if d.is_dir()]
        for project_dir in projects:
            print(f"Processing project directory: {project_dir}")
            
            # Remove transcription data
            transcription_path = project_dir / "transcription.json"
            if transcription_path.exists():
                try:
                    backup_path = project_dir / f"transcription.json.bak.{int(time.time())}"
                    shutil.copy2(transcription_path, backup_path)
                    os.remove(transcription_path)
                    print(f"Removed transcription.json file")
                except Exception as e:
                    print(f"Error removing transcription.json: {e}")
            
            # Remove A-Roll video if exists
            media_aroll_dir = project_dir / "media" / "a-roll"
            if media_aroll_dir.exists():
                for video_file in media_aroll_dir.glob("main_aroll*.mp4"):
                    try:
                        os.remove(video_file)
                        print(f"Removed A-Roll video: {video_file}")
                    except Exception as e:
                        print(f"Error removing A-Roll video: {e}")
            
            # Reset script.json if exists
            script_path = project_dir / "script.json"
            if script_path.exists():
                try:
                    backup_path = project_dir / f"script.json.bak.{int(time.time())}"
                    shutil.copy2(script_path, backup_path)
                    os.remove(script_path)
                    print(f"Removed script.json file")
                except Exception as e:
                    print(f"Error removing script.json: {e}")
                    
            # Reset content_status.json if exists
            content_status_path = project_dir / "content_status.json"
            if content_status_path.exists():
                try:
                    backup_path = project_dir / f"content_status.json.bak.{int(time.time())}"
                    shutil.copy2(content_status_path, backup_path)
                    os.remove(content_status_path)
                    print(f"Removed content_status.json file")
                except Exception as e:
                    print(f"Error removing content_status.json: {e}")
            
            # Remove B-roll prompts
            broll_prompts_path = project_dir / "broll_prompts.json"
            if broll_prompts_path.exists():
                try:
                    backup_path = project_dir / f"broll_prompts.json.bak.{int(time.time())}"
                    shutil.copy2(broll_prompts_path, backup_path)
                    os.remove(broll_prompts_path)
                    print(f"Removed broll_prompts.json file")
                except Exception as e:
                    print(f"Error removing broll_prompts.json: {e}")
    
    # Clear Streamlit cache
    cache_dir = Path(".streamlit/cache")
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            print("Cleared Streamlit cache directory")
        except Exception as e:
            print(f"Error clearing Streamlit cache: {e}")
    
    # Clear temporary preview files
    preview_dir = Path("preview")
    if preview_dir.exists() and preview_dir.is_dir():
        try:
            for file in preview_dir.glob("*_preview.*"):
                os.remove(file)
                print(f"Removed temporary preview file: {file}")
        except Exception as e:
            print(f"Error clearing preview files: {e}")
    
    print("App reset process complete. The app should now start with a clean state.")
    print("Please restart the app now.")

if __name__ == "__main__":
    reset_app_state() 