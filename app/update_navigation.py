import os
from pathlib import Path
import re

def update_navigation_in_files():
    """Update all page files to include horizontal navigation"""
    
    # Define the directory containing page files
    pages_dir = Path("pages")
    
    # Get all Python files in the pages directory
    page_files = [f for f in pages_dir.glob("*.py") if f.is_file()]
    
    # CSS style for horizontal navigation
    nav_style = """
# Style for horizontal navigation
st.markdown(\"\"\"
<style>
    .horizontal-nav {
        margin-bottom: 20px;
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    
    .horizontal-nav button {
        background-color: transparent;
        border: none;
        font-size: 1.2rem;
        margin: 0 5px;
        transition: all 0.3s;
    }
    
    .horizontal-nav button:hover {
        transform: scale(1.2);
    }
</style>
\"\"\", unsafe_allow_html=True)

# Add horizontal navigation
st.markdown("<div class='horizontal-nav'>", unsafe_allow_html=True)
render_horizontal_navigation()
st.markdown("</div>", unsafe_allow_html=True)
"""
    
    # Import statement for horizontal navigation
    import_statement = "from components.navigation import render_workflow_navigation, render_step_navigation, render_horizontal_navigation"
    
    # Process each file
    for file_path in page_files:
        print(f"Processing: {file_path}")
        
        # Read file content
        with open(file_path, "r") as f:
            content = f.read()
        
        # Check if file already has horizontal navigation
        if "render_horizontal_navigation" in content:
            print(f"  - Already has horizontal navigation, skipping")
            continue
        
        # Replace import statement (if exists)
        content = re.sub(
            r"from components\.navigation import render_workflow_navigation, render_step_navigation",
            import_statement,
            content
        )
        
        # If import wasn't replaced (different format), check for other patterns
        if "render_horizontal_navigation" not in content:
            # Try another common pattern
            content = re.sub(
                r"from components\.navigation import render_workflow_navigation",
                import_statement,
                content
            )
            
            # If still not replaced, we need to add it
            if "render_horizontal_navigation" not in content:
                print(f"  - Could not replace import statement, manual check needed")
                continue
        
        # Find position to insert navigation (after CSS loading or after imports)
        css_load_pos = content.find("load_css()")
        if css_load_pos > -1:
            # Find the end of the line
            insert_pos = content.find("\n", css_load_pos) + 1
            
            # Insert navigation code
            updated_content = content[:insert_pos] + "\n" + nav_style + content[insert_pos:]
        else:
            print(f"  - Could not find load_css(), manual check needed")
            continue
        
        # Write updated content back to file
        with open(file_path, "w") as f:
            f.write(updated_content)
            
        print(f"  - Updated successfully")
    
    print("Navigation update complete")

if __name__ == "__main__":
    update_navigation_in_files() 