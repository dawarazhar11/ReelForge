import streamlit as st
from pathlib import Path
import json
from .progress import render_progress_bar

def get_step_progress():
    """Get the progress status of each step"""
    progress = {}
    progress_file = Path("config/user_data/progress.json")
    
    if progress_file.exists():
        try:
            with open(progress_file, "r") as f:
                progress = json.load(f)
        except Exception as e:
            print(f"Error loading progress data: {e}")
    
    return progress

def render_custom_sidebar():
    """Render a custom sidebar navigation with manually specified items"""
    # Render logo and app name
    st.sidebar.title("💰 AI Money Printer")
    st.sidebar.caption("Short Video Generator")
    
    # Render progress bar
    render_progress_bar()
    
    # Navigation steps
    st.sidebar.divider()
    st.sidebar.subheader("Workflow Steps")
    
    # Define the navigation items we want to show
    sidebar_items = [
        # Removed disabled pages (Settings, Blueprint, Script Segmentation)
        {
            "name": "A-Roll Transcription",
            "icon": "🎤",
            "path": "pages/4.5_ARoll_Transcription.py",
            "step": 1
        },
        {
            "name": "Video Assembly",
            "icon": "🎞️",
            "path": "pages/6_Video_Assembly.py",
            "step": 2  # Updated step number
        },
        {
            "name": "Captioning",
            "icon": "💬",
            "path": "pages/7_Caption_The_Dreams.py",
            "step": 3  # Updated step number
        },
        {
            "name": "Publishing",
            "icon": "🚀",
            "path": "pages/8_Social_Media_Upload.py",
            "step": 4  # Updated step number
        }
    ]

    # Get progress data
    progress = get_step_progress()
    
    # Display each navigation item
    for i, item in enumerate(sidebar_items):
        step_id = f"step_{item['step']}"
        is_complete = progress.get(step_id, False)
        
        # Show checkmark if step is complete
        if is_complete:
            label = f"{item['icon']} {item['name']} ✅"
        else:
            label = f"{item['icon']} {item['name']}"
        
        # Create a button with a unique key
        if st.sidebar.button(label, key=f"custom_nav_{i}"):
            st.switch_page(item["path"])
    
    st.sidebar.divider()
    
    # Home button
    if st.sidebar.button("🏠 Back to Home"):
        st.switch_page("Home.py")

def render_horizontal_navigation():
    """Render the workflow navigation horizontally in the header"""
    # Create a container for the horizontal navigation
    with st.container():
        # Define the navigation items we want to show
        horizontal_items = [
            # Removed disabled pages (Settings, Blueprint, Script Segmentation)
            {
                "name": "A-Roll Transcription",
                "icon": "🎤",
                "path": "pages/4.5_ARoll_Transcription.py",
                "step": 1
            },
            {
                "name": "Video Assembly",
                "icon": "🎞️",
                "path": "pages/6_Video_Assembly.py",
                "step": 2  # Updated step number
            },
            {
                "name": "Captioning",
                "icon": "💬",
                "path": "pages/7_Caption_The_Dreams.py",
                "step": 3  # Updated step number
            },
            {
                "name": "Publishing",
                "icon": "🚀",
                "path": "pages/8_Social_Media_Upload.py",
                "step": 4  # Updated step number
            }
        ]
        
        # Get progress data
        progress = get_step_progress()
        
        # Create columns for all items
        cols = st.columns(len(horizontal_items))
        
        # Display each item
        for i, (item, col) in enumerate(zip(horizontal_items, cols)):
            step_id = f"step_{item['step']}"
            is_complete = progress.get(step_id, False)
            
            # Show checkmark if step is complete
            if is_complete:
                label = f"{item['icon']} ✅"
            else:
                label = f"{item['icon']}"
            
            # Add tooltip with step name
            with col:
                if st.button(label, key=f"custom_horizontal_{i}", help=item['name']):
                    st.switch_page(item["path"])

def render_step_navigation(current_step, prev_step_path=None, next_step_path=None):
    """Render step navigation with previous and next buttons
    
    Args:
        current_step: Current step number
        prev_step_path: Path to the previous step
        next_step_path: Path to the next step
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # Previous step button
    with col1:
        if prev_step_path:
            # Ensure the path has the pages/ prefix if it's a page
            if prev_step_path != "Home.py" and not prev_step_path.startswith("pages/"):
                prev_step_path = f"pages/{prev_step_path}"
                
            if st.button("⬅️ Previous Step", use_container_width=True):
                st.switch_page(prev_step_path)
    
    # Current step indicator
    with col2:
        steps = [
            # Updated step names to match the new order (without B-Roll Video Production)
            "A-Roll Transcription",
            "Video Assembly",
            "Captioning",
            "Publishing"
        ]
        
        if 1 <= current_step <= len(steps):
            st.markdown(f"**Current Step: {current_step}/{len(steps)} - {steps[current_step-1]}**", 
                      help="Navigate between workflow steps using the buttons")
        else:
            st.markdown(f"**Current Step: {current_step}**")
    
    # Next step button
    with col3:
        if next_step_path:
            # Ensure the path has the pages/ prefix if it's a page
            if next_step_path != "Home.py" and not next_step_path.startswith("pages/"):
                next_step_path = f"pages/{next_step_path}"
                
            if st.button("Next Step ➡️", use_container_width=True):
                st.switch_page(next_step_path) 