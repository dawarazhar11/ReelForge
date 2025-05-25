import streamlit as st
from pathlib import Path
import json

def get_progress_percentage():
    """Calculate the percentage of workflow steps completed"""
    progress_file = Path("config/user_data/progress.json")
    total_steps = 8  # Total number of steps in the workflow
    
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
            completed_steps = len(progress.keys())
            # Return value between 0.0 and 1.0, clamped to valid range
            return min(1.0, max(0.0, completed_steps / total_steps))
    
    return 0.0

def render_progress_bar():
    """Render a progress bar showing workflow completion"""
    progress = get_progress_percentage()
    
    st.sidebar.subheader("Workflow Progress")
    st.sidebar.progress(progress)
    st.sidebar.caption(f"{int(progress * 100)}% complete")

def render_step_header(step_number_or_name, step_name_or_description=None, total_steps=8):
    """
    Render a header with step information
    
    Supports two calling patterns:
    1. render_step_header(step_number, step_name, total_steps)
    2. render_step_header(step_name, description)
    """
    # Determine which calling pattern is being used
    if step_name_or_description is None or isinstance(step_number_or_name, int):
        # First pattern: step_number, step_name, total_steps
        step_number = step_number_or_name
        step_name = step_name_or_description if step_name_or_description else "Step"
        
        # Convert step_number to int if it's a string
        if isinstance(step_number, str):
            try:
                step_number = int(step_number)
            except ValueError:
                # Default to 1 if conversion fails
                step_number = 1
        
        st.subheader(f"Step {step_number} of {total_steps}: {step_name}")
        
        # Calculate normalized progress value (0-1 range)
        if step_number <= 1:
            progress = 0.0
        elif step_number >= total_steps:
            progress = 1.0
        else:
            # Normalize to range [0,1]
            progress = (step_number - 1) / (total_steps - 1)
    else:
        # Second pattern: step_name, description
        step_name = step_number_or_name
        description = step_name_or_description
        
        st.subheader(step_name)
        if description:
            st.markdown(f"*{description}*")
        
        # No progress calculation for this pattern
        progress = None
    
    # Show progress bar if we have a progress value
    if progress is not None:
        # Double-check that progress is within valid range [0,1]
        progress = min(1.0, max(0.0, progress))
        st.progress(progress)
    
    st.markdown("---") 