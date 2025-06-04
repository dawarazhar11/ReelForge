#!/usr/bin/env python3
"""
Fix B-Roll Mismatch Utility

This script fixes mismatches between script.json and content_status.json for B-roll segments.
It ensures that the content_status.json file has exactly the same number of B-roll segments
as defined in script.json, which is especially important when using percentage-based B-roll generation.

Usage:
    python fix_broll_mismatch.py [project_name]

    If project_name is not provided, it will fix all projects in the user_data directory.
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path

def fix_broll_mismatch(project_dir):
    """Fix B-roll mismatch for a specific project directory."""
    print(f"Checking project: {project_dir.name}")
    
    # Check if script.json exists
    script_path = project_dir / "script.json"
    content_status_path = project_dir / "content_status.json"
    
    if not script_path.exists():
        print(f"  Script file not found: {script_path}")
        return False
    
    if not content_status_path.exists():
        print(f"  Content status file not found: {content_status_path}")
        return False
    
    try:
        # Load script.json
        with open(script_path, "r") as f:
            script_data = json.load(f)
        
        # Load content_status.json
        with open(content_status_path, "r") as f:
            content_status = json.load(f)
        
        # Count B-roll segments in script.json
        broll_segments = [s for s in script_data.get("segments", []) if s.get("type") == "B-Roll"]
        broll_segment_count = len(broll_segments)
        aroll_segments = [s for s in script_data.get("segments", []) if s.get("type") == "A-Roll"]
        aroll_segment_count = len(aroll_segments)
        
        # Count B-roll segments in content_status.json
        content_broll_count = len(content_status.get("broll", {}))
        
        print(f"  Script has {broll_segment_count} B-Roll segments and {aroll_segment_count} A-Roll segments")
        print(f"  Content status has {content_broll_count} B-Roll segments")
        
        # Check if percentage-based B-roll generation is used
        if "broll_percentage" in script_data:
            percentage = script_data["broll_percentage"]
            print(f"  Using percentage-based B-roll generation: {percentage}%")
        
        # Check if counts match
        if content_broll_count != broll_segment_count:
            print(f"  MISMATCH DETECTED: Script has {broll_segment_count} B-Roll segments, but content status has {content_broll_count}")
            
            # Back up content status file
            backup_path = content_status_path.with_suffix(f".json.bak.{int(time.time())}")
            shutil.copy(content_status_path, backup_path)
            print(f"  Backed up content_status.json to {backup_path.name}")
            
            # Create new content status with the correct number of B-roll segments
            new_broll_status = {}
            for i in range(broll_segment_count):
                segment_id = f"segment_{i}"
                # Copy existing data if available, otherwise create empty entry
                if "broll" in content_status and segment_id in content_status["broll"]:
                    new_broll_status[segment_id] = content_status["broll"][segment_id]
                else:
                    new_broll_status[segment_id] = {
                        "status": "not_started",
                        "asset_paths": [],
                        "selected_asset": None
                    }
            
            # Update content status with new B-roll data
            content_status["broll"] = new_broll_status
            content_status["broll_segment_count"] = broll_segment_count
            content_status["synced_with_script"] = True
            content_status["last_updated"] = time.time()
            
            # Write updated content status
            with open(content_status_path, "w") as f:
                json.dump(content_status, f, indent=2)
            
            print(f"  FIXED: Updated content_status.json to match script.json: {broll_segment_count} B-Roll segments")
            return True
        else:
            print(f"  OK: B-Roll segment counts already match")
            return False
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
        
        fix_broll_mismatch(project_dir)
    else:
        # Fix all projects
        user_data_path = Path("config/user_data")
        if not user_data_path.exists():
            print(f"User data directory not found: {user_data_path}")
            return
        
        projects = [d for d in user_data_path.iterdir() if d.is_dir()]
        fixed_count = 0
        
        for project_dir in projects:
            if fix_broll_mismatch(project_dir):
                fixed_count += 1
        
        print(f"\nFixed {fixed_count} out of {len(projects)} projects")

if __name__ == "__main__":
    main() 