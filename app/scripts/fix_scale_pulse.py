#!/usr/bin/env python3
"""
Script to fix the scale_pulse animation style
"""
import os
import sys
import shutil
import re

def fix_scale_pulse_animation():
    """Fix the scale_pulse animation style"""
    captions_path = "utils/video/captions.py"
    
    # Create a backup
    backup_path = f"{captions_path}.scale_pulse.bak"
    shutil.copy2(captions_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Read the file
    with open(captions_path, "r") as f:
        content = f.read()
    
    # Find the scale_pulse animation style section
    pattern = r'(elif animation_style == "scale_pulse":[^}]+?)# Scale up when the word is first spoken\s*if current_time < word_start \+ 0\.3:'
    
    # Add more robust scale handling
    replacement = r'\1# Scale up when the word is first spoken\n                # Add safety check to avoid division by zero or negative scale\n                min_scale = 0.01  # Prevent zero or negative scale\n                if current_time < word_start + 0.3:'
    
    # Apply the replacement
    updated_content = re.sub(pattern, replacement, content)
    
    # Update the scale calculation to have min/max bounds
    pattern = r'(progress = \(current_time - word_start\) / 0\.3\s*)scale = 1\.0 \+ \(0\.5 \* \(1\.0 - progress\)\)'
    replacement = r'\1# Ensure scale is within reasonable bounds\n                    scale = max(min_scale, 1.0 + (0.5 * (1.0 - progress)))'
    
    # Apply the replacement
    updated_content = re.sub(pattern, replacement, updated_content)
    
    # Also fix the scale down calculation
    pattern = r'(progress = 1\.0 - min\(1\.0, \(current_time - word_end\) / 0\.5\)\s*)scale = 1\.0 \* progress'
    replacement = r'\1# Ensure scale is at least the minimum value\n                    scale = max(min_scale, 1.0 * progress)'
    
    # Apply the replacement
    updated_content = re.sub(pattern, replacement, updated_content)
    
    # Write the updated content
    with open(captions_path, "w") as f:
        f.write(updated_content)
    
    print(f"Applied scale_pulse animation style fix to {captions_path}")
    return True

if __name__ == "__main__":
    print("Fixing scale_pulse animation style")
    success = fix_scale_pulse_animation()
    print("Done!" if success else "Failed to apply fix")
    sys.exit(0 if success else 1) 