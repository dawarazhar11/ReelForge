#!/usr/bin/env python3
"""
Update Progress

This utility script updates the progress.json file to match the new workflow steps
after disabling the Settings, Blueprint, and Script Segmentation pages.

Usage:
    python update_progress.py
"""

import os
import json
from pathlib import Path

def update_progress():
    """Update progress.json file to match the new workflow steps"""
    
    progress_file = Path("config/user_data/progress.json")
    
    if not progress_file.exists():
        print("No progress.json file found")
        return
    
    print(f"Updating progress file: {progress_file}")
    
    # Load existing progress
    with open(progress_file, "r") as f:
        progress = json.load(f)
    
    # Create backup
    backup_path = progress_file.with_suffix(".json.bak")
    with open(backup_path, "w") as f:
        json.dump(progress, f, indent=2)
    
    print(f"Created backup at {backup_path}")
    
    # New mapping from old step numbers to new step numbers
    step_mapping = {
        # Old steps 0-2 (Settings, Blueprint, Script Segmentation) are removed
        "step_0": None,
        "step_1": None,
        "step_2": None,
        # A-Roll Transcription becomes step 0
        "step_4.5": "step_0",
        # B-Roll Prompts becomes step 1
        "step_3": "step_1",
        # B-Roll Video Production becomes step 2
        "step_5B": "step_2",
        # Video Assembly becomes step 3
        "step_5": "step_3",
        # Captioning becomes step 4
        "step_6": "step_4",
        # Social Media Upload becomes step 5
        "step_7": "step_5"
    }
    
    # Create new progress dictionary
    new_progress = {}
    
    for old_step, value in progress.items():
        if old_step in step_mapping and step_mapping[old_step] is not None:
            new_progress[step_mapping[old_step]] = value
    
    # Save updated progress
    with open(progress_file, "w") as f:
        json.dump(new_progress, f, indent=2)
    
    print(f"Updated progress file with new step mappings")
    print(f"Old progress: {progress}")
    print(f"New progress: {new_progress}")

if __name__ == "__main__":
    update_progress() 