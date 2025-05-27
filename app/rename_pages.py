#!/usr/bin/env python3
"""
Renaming script for page files to ensure correct ordering
"""
import os
import shutil
from pathlib import Path

def rename_pages():
    """
    Rename the page files to ensure they appear in the correct order
    """
    pages_dir = Path("pages")
    
    # Define the mapping of current names to desired names
    rename_map = {
        "5_Content_Production.py": "5B_BRoll_Video_Production.py",
        "4.5_ARoll_Production.py": "5A_ARoll_Video_Production.py",
    }
    
    # Check if files exist before attempting rename
    for old_name, new_name in rename_map.items():
        old_path = pages_dir / old_name
        new_path = pages_dir / new_name
        
        if old_path.exists() and not new_path.exists():
            print(f"Renaming {old_path} to {new_path}")
            shutil.copy2(old_path, new_path)
            print(f"Created copy as {new_path}")
        elif old_path.exists() and new_path.exists():
            print(f"WARNING: Both {old_path} and {new_path} exist. No action taken.")
        else:
            print(f"WARNING: Source file {old_path} does not exist.")
    
    print("Rename operation completed.")

if __name__ == "__main__":
    rename_pages() 