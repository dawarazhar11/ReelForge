import streamlit as st
from pathlib import Path
import json

def get_progress_percentage():
    """Calculate the percentage of workflow steps completed"""
    progress_file = Path("config/user_data/progress.json")
    total_steps = 6  # Total number of steps in the workflow
    
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

def render_step_header(step_number, step_name, total_steps=6):
    """
    Render a header for the current step with progress information
    
    Args:
        step_number: Current step number (1-indexed)
        step_name: Name of the current step
        total_steps: Total number of steps in the workflow
    """
    # Create a progress bar
    progress = (step_number - 1) / (total_steps - 1)
    st.progress(progress)
    
    # Display step information
    st.markdown(f"**Step {step_number} of {total_steps}: {step_name}**")
    
    # Add a spacer
    st.markdown("") 