#!/usr/bin/env python3
"""
Update all pages to use the custom navigation.
"""
import os
import re
from pathlib import Path

def update_page_files():
    """Update all page files to use the custom navigation components."""
    pages_dir = Path("pages")
    
    # Process each Python file in the pages directory
    for page_file in pages_dir.glob("*.py"):
        print(f"Processing file: {page_file}")
        
        # Read the file content
        with open(page_file, "r") as f:
            content = f.read()
        
        # Replace import statements
        content = re.sub(
            r'from components\.navigation import render_workflow_navigation', 
            'from components.custom_navigation import render_custom_sidebar', 
            content
        )
        
        # Also handle horizontal navigation import
        if 'render_horizontal_navigation' in content:
            content = re.sub(
                r'from components\.navigation import (.*?)render_horizontal_navigation(.*?)', 
                r'from components.navigation import \1\2\nfrom components.custom_navigation import render_horizontal_navigation, render_custom_sidebar', 
                content
            )
        else:
            # If horizontal navigation is not imported, add it
            content = re.sub(
                r'from components\.navigation import (.*?)\n', 
                r'from components.navigation import \1\nfrom components.custom_navigation import render_horizontal_navigation, render_custom_sidebar\n', 
                content
            )
        
        # Replace function call to render_workflow_navigation
        content = re.sub(
            r'render_workflow_navigation\(\)', 
            'render_custom_sidebar()', 
            content
        )
        
        # Write the updated content back to the file
        with open(page_file, "w") as f:
            f.write(content)
        
        print(f"Updated file: {page_file}")

if __name__ == "__main__":
    update_page_files()
    print("All page files updated successfully!") 