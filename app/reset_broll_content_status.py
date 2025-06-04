#!/usr/bin/env python3
"""
Reset B-Roll Content Status

This utility script forcefully resets the B-roll segment data in content_status.json
to match the B-roll segments in script.json. This is useful when the content_status.json
file gets out of sync with script.json after changing B-roll percentage settings.

Usage:
    python reset_broll_content_status.py [project_name]

If project_name is not provided, it will process all projects in the user_data directory.
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path

def reset_broll_content_status(project_dir):
    """
    Reset B-roll content status for a specific project directory.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        bool: True if changes were made, False otherwise
    """
    print(f"Processing project: {project_dir.name}")
    
    # Check if script.json and content_status.json exist
    script_path = project_dir / "script.json"
    content_status_path = project_dir / "content_status.json"
    
    if not script_path.exists():
        print(f"  Script file not found: {script_path}")
        return False
    
    try:
        # Load script.json
        with open(script_path, "r") as f:
            script_data = json.load(f)
        
        # Extract B-roll segments from script.json
        broll_segments = [s for s in script_data.get("segments", []) if s.get("type") == "B-Roll"]
        broll_segment_count = len(broll_segments)
        
        print(f"  Found {broll_segment_count} B-Roll segments in script.json")
        
        # Check if percentage-based B-roll generation is used
        if "broll_percentage" in script_data:
            percentage = script_data["broll_percentage"]
            print(f"  Using percentage-based B-roll generation: {percentage}%")
        
        # Create content_status.json if it doesn't exist
        if not content_status_path.exists():
            print(f"  Content status file not found, creating new one")
            content_status = {
                "broll": {},
                "broll_segment_count": broll_segment_count,
                "created_from_script": True,
                "timestamp": time.time()
            }
        else:
            # Load existing content_status.json
            with open(content_status_path, "r") as f:
                content_status = json.load(f)
            
            # Create backup of existing file
            backup_path = content_status_path.with_suffix(f".json.bak.{int(time.time())}")
            shutil.copy(content_status_path, backup_path)
            print(f"  Created backup at {backup_path.name}")
        
        # Reset B-roll data in content_status
        new_broll_status = {}
        for i in range(broll_segment_count):
            segment_id = f"segment_{i}"
            
            # Copy existing segment data if available
            if "broll" in content_status and segment_id in content_status["broll"]:
                # Preserve certain fields, but reset status
                broll_data = content_status["broll"][segment_id]
                new_broll_status[segment_id] = {
                    "status": "not_started",
                    "asset_paths": broll_data.get("asset_paths", []),
                    "selected_asset": broll_data.get("selected_asset", None),
                    "prompt_id": broll_data.get("prompt_id", "")
                }
            else:
                # Create new segment data
                new_broll_status[segment_id] = {
                    "status": "not_started",
                    "asset_paths": [],
                    "selected_asset": None
                }
        
        # Update content_status
        content_status["broll"] = new_broll_status
        content_status["broll_segment_count"] = broll_segment_count
        content_status["synced_with_script"] = True
        content_status["reset_timestamp"] = time.time()
        
        # Save updated content_status.json
        with open(content_status_path, "w") as f:
            json.dump(content_status, f, indent=2)
        
        print(f"  Successfully reset content_status.json with {broll_segment_count} B-Roll segments")
        return True
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def main():
    # Check if project name is provided
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        user_data_path = Path("config/user_data")
        project_dir = user_data_path / project_name
        
        if not project_dir.exists():
            print(f"Project directory not found: {project_dir}")
            return
        
        reset_broll_content_status(project_dir)
    else:
        # Process all projects
        user_data_path = Path("config/user_data")
        if not user_data_path.exists():
            print(f"User data directory not found: {user_data_path}")
            return
        
        projects = [d for d in user_data_path.iterdir() if d.is_dir()]
        processed_count = 0
        
        for project_dir in projects:
            if reset_broll_content_status(project_dir):
                processed_count += 1
        
        print(f"\nProcessed {processed_count} out of {len(projects)} projects")

if __name__ == "__main__":
    main() 