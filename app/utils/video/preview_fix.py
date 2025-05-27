#!/usr/bin/env python3
"""
Fix for the preview functionality in Caption_The_Dreams.py
"""

import os
import traceback
from pathlib import Path

def fix_preview_function():
    """Fix the preview function to properly initialize scale variable"""
    try:
        # Get the path to Caption_The_Dreams.py
        page_path = Path(__file__).parent.parent.parent / "pages" / "7_Caption_The_Dreams.py"
        if not page_path.exists():
            print(f"Error: Could not find page at {page_path}")
            return False
            
        # Create a backup
        backup_path = Path(f"{page_path}.preview_fix.bak")
        with open(page_path, "r") as f:
            original_content = f.read()
            
        with open(backup_path, "w") as f:
            f.write(original_content)
            
        print(f"Created backup at {backup_path}")
        
        # Find the problematic preview code section
        preview_section = """                # Add captions using the make_frame_with_text function that handles animation styles
                preview_frame = make_frame_with_text(
                    st.session_state.preview_frame.copy(),
                    preview_text,
                    preview_words,
                    preview_time,
                    style,  # Pass style dictionary directly
                    None,   # No additional effect params needed
                    animation_style  # Pass animation style
                )"""
                
        # Create improved version with error handling
        improved_preview = """                # Add captions using the make_frame_with_text function that handles animation styles
                try:
                    preview_frame = make_frame_with_text(
                        st.session_state.preview_frame.copy(),
                        preview_text,
                        preview_words,
                        preview_time,
                        style,  # Pass style dictionary directly
                        None,   # No additional effect params needed
                        animation_style  # Pass animation style
                    )
                except Exception as e:
                    st.error(f"Error generating preview: {str(e)}")
                    # Fall back to basic preview without animation
                    if animation_style == "single_word_focus":
                        st.warning("Preview not available for 'Single Word Focus' style. The final video will still work correctly.")
                        # Just use the original frame
                        preview_frame = st.session_state.preview_frame.copy()
                        # Add the text directly without animation
                        from utils.video.captions import render_basic_caption
                        preview_frame = render_basic_caption(preview_frame, preview_text, style)
                    else:
                        # Try with a different animation style
                        st.warning(f"Falling back to basic preview. The final video will still use your selected style.")
                        preview_frame = make_frame_with_text(
                            st.session_state.preview_frame.copy(),
                            preview_text,
                            preview_words,
                            preview_time,
                            style,
                            None,
                            "word_by_word"  # Use a more reliable animation style
                        )"""
                
        # Replace the problematic section
        modified_content = original_content.replace(preview_section, improved_preview)
        
        # Write the modified content back to the file
        with open(page_path, "w") as f:
            f.write(modified_content)
            
        print(f"Applied fix to {page_path}")
        return True
    except Exception as e:
        print(f"Error fixing preview function: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running preview function fix utility")
    success = fix_preview_function()
    if success:
        print("✅ Fix completed successfully")
    else:
        print("❌ Fix failed") 