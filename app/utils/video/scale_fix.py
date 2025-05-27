#!/usr/bin/env python3
"""
Diagnostic and fix script for the 'scale' variable error in captions.py
"""

import os
import re
import traceback
from pathlib import Path

def fix_scale_variable_error():
    """Find and fix all instances of the variable 'scale' in captions.py"""
    try:
        # Get the path to captions.py
        captions_path = Path(__file__).parent / "captions.py"
        if not captions_path.exists():
            print(f"Error: Could not find captions.py at {captions_path}")
            return False
            
        # Create a backup
        backup_path = Path(f"{captions_path}.scale_fix.bak")
        with open(captions_path, "r") as f:
            original_content = f.read()
            
        with open(backup_path, "w") as f:
            f.write(original_content)
            
        print(f"Created backup at {backup_path}")
        
        # Find all occurrences of 'scale' variable
        scale_references = re.findall(r'\bscale\b', original_content)
        print(f"Found {len(scale_references)} references to 'scale' variable")
        
        # Replace the error-prone pattern in render_animated_caption function
        modified_content = original_content
        
        # Fix 1: Replace any direct access to 'scale' with 'scale_factor'
        modified_content = re.sub(
            r'(\W)scale(\W)', 
            r'\1scale_factor\2', 
            modified_content
        )
        
        # Fix 2: Add scale_factor initialization before it's used
        pattern = r'def render_animated_caption\([^)]*\):[^}]+?# If we found a current word'
        replacement = """def render_animated_caption(frame_img, text, words_with_times, current_time, style_params, animation_style, effect_params=None):
    \"\"\"
    Render an animated caption on a frame based on the animation style
    All rendering is done directly in this function to avoid recursion
    \"\"\"
    try:
        # Initialize scale_factor variable to prevent "cannot access local variable" errors
        scale_factor = 1.5  # Default scale factor
        
        if not words_with_times:
            # No word timing info available, fall back to basic caption
            return render_basic_caption(frame_img, text, style_params)
"""
        modified_content = re.sub(pattern, replacement, modified_content)
        
        # Write the modified content back to the file
        with open(captions_path, "w") as f:
            f.write(modified_content)
            
        print(f"Applied fixes to {captions_path}")
        print("Modified scale variable references to prevent 'cannot access local variable' errors")
        
        return True
    except Exception as e:
        print(f"Error fixing scale variable: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running scale variable fix utility")
    success = fix_scale_variable_error()
    if success:
        print("✅ Fix completed successfully")
    else:
        print("❌ Fix failed") 