#!/usr/bin/env python3
"""
Manual fix for the scale variable error in captions.py
"""

import os
from pathlib import Path

def fix_scale_issue():
    """Manually fix the scale variable issue in render_animated_caption function"""
    # Get the path to captions.py
    captions_path = Path(__file__).parent / "captions.py"
    if not captions_path.exists():
        print(f"Error: Could not find captions.py at {captions_path}")
        return False
        
    # Create a backup
    backup_path = Path(f"{captions_path}.manual_fix.bak")
    with open(captions_path, "r") as f:
        original_content = f.read()
        
    with open(backup_path, "w") as f:
        f.write(original_content)
        
    print(f"Created backup at {backup_path}")
    
    # Find the start of the render_animated_caption function
    function_start = "def render_animated_caption("
    try:
        function_start_pos = original_content.index(function_start)
    except ValueError:
        print("Could not find render_animated_caption function in the file")
        return False
    
    # Carefully construct the target function with fixes
    # This inserts just the new initialization of scale_factor without changing indentation
    fixed_function_start = """def render_animated_caption(frame_img, text, words_with_times, current_time, style_params, animation_style, effect_params=None):
    \"\"\"
    Render an animated caption on a frame based on the animation style
    All rendering is done directly in this function to avoid recursion
    \"\"\"
    try:
        # Initialize scale_factor variable to prevent "cannot access local variable" errors
        scale_factor = 1.5  # Default scale factor
        
        if not words_with_times:
            # No word timing info available, fall back to basic caption"""
    
    # Apply the fix
    new_content = original_content[:function_start_pos] + fixed_function_start + original_content[function_start_pos+len(function_start):]
    
    # Insert more robust error handling
    error_handler = """    except Exception as e:
        print(f"Error in render_animated_caption: {e}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        
        # Try to provide more specific error context
        if "cannot access local variable" in str(e):
            var_name = str(e).split("'")[1] if "'" in str(e) else "unknown"
            print(f"Variable access error: '{var_name}' is not defined before use.")
            
            # For specific known issues, attempt recovery
            if var_name == "scale" or var_name == "scale_factor":
                print("Attempting to recover from scale variable error...")
                # Return original frame as fallback
        
        return frame_img"""
    
    # Find existing error handler
    existing_error_handler = "    except Exception as e:\n        print(f\"Error in render_animated_caption: {e}\")\n        return frame_img"
    
    # Replace it
    new_content = new_content.replace(existing_error_handler, error_handler)
    
    # Replace 'scale' with 'scale_factor' but only in the render_animated_caption function
    function_end = "def add_caption_to_frame("
    function_end_pos = new_content.find(function_end)
    
    function_body = new_content[function_start_pos:function_end_pos]
    fixed_function_body = function_body.replace(" scale ", " scale_factor ")
    
    new_content = new_content[:function_start_pos] + fixed_function_body + new_content[function_end_pos:]
    
    # Write the modified content back to the file
    with open(captions_path, "w") as f:
        f.write(new_content)
        
    print(f"Applied manual fix to {captions_path}")
    return True

if __name__ == "__main__":
    print("Running manual scale variable fix utility")
    success = fix_scale_issue()
    if success:
        print("✅ Fix completed successfully")
    else:
        print("❌ Fix failed") 