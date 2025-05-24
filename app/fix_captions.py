#!/usr/bin/env python3
"""
Script to apply fixes to the captions module
"""
import os
import sys
import shutil
import re

def apply_fix_to_captions_module():
    """Apply fixes to the captions module"""
    captions_path = "utils/video/captions.py"
    
    # Create a backup
    backup_path = f"{captions_path}.bak"
    shutil.copy2(captions_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Read the file
    with open(captions_path, "r") as f:
        content = f.read()
    
    # Fix 1: Update the create_caption_frame function in add_captions_to_video
    # to pass the style_name instead of the style object
    pattern = r'(return make_frame_with_text\(\s*frame_img,\s*active_segment\["text"\],\s*active_segment\["words"\],\s*t,\s*)style(,\s*animation_style=animation_style\s*\))'
    replacement = r'\1style_name\2'
    content = re.sub(pattern, replacement, content)
    
    # Fix 2: Add a try-except around the scale calculation in add_animated_caption_to_frame
    # to prevent division by zero
    pattern = r'(# Scale the font for this word\s*scaled_font_size = int\(font_size \* scale\)\s*try:\s*scaled_font = ImageFont\.truetype\(font_path, scaled_font_size\)\s*except:\s*scaled_font = font\s*\s*# Get new dimensions\s*)new_width, new_height = get_text_size\(draw, word \+ " ", scaled_font\)'
    replacement = r'\1try:\n                    new_width, new_height = get_text_size(draw, word + " ", scaled_font)\n                except Exception as e:\n                    # Fallback if text size calculation fails\n                    print(f"Warning: Error calculating text size: {e}")\n                    new_width, new_height = word_width, word_height'
    content = re.sub(pattern, replacement, content)
    
    # Fix 3: Update the create_caption_frame function to handle the frame function properly
    pattern = r'# Define function to create caption for a frame\s*def create_caption_frame\(frame_img, t\):'
    replacement = r'# Define function to create caption for a frame\n        def create_caption_frame(get_frame_func_or_img, t):\n            # Handle both frame functions and direct numpy arrays\n            if callable(get_frame_func_or_img):\n                frame_img = get_frame_func_or_img(t)\n            else:\n                frame_img = get_frame_func_or_img'
    content = re.sub(pattern, replacement, content)
    
    # Write the updated content
    with open(captions_path, "w") as f:
        f.write(content)
    
    print(f"Applied fixes to {captions_path}")
    return True

if __name__ == "__main__":
    print("Applying fixes to captions module")
    success = apply_fix_to_captions_module()
    print("Done!" if success else "Failed to apply fixes")
    sys.exit(0 if success else 1) 