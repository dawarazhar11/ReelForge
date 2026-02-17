#!/usr/bin/env python3
"""
Rename problematic files so they can't be loaded by Streamlit.
"""
import os
from pathlib import Path

def disable_problem_files():
    # Files to disable
    problem_files = [
        "pages/4.5_ARoll_Production.py",
        "pages/5_Content_Production.py"
    ]
    
    for file_path in problem_files:
        path = Path(file_path)
        if path.exists():
            # Rename to .disabled extension
            new_path = path.with_suffix(".py.disabled")
            path.rename(new_path)
            print(f"Disabled: {path} -> {new_path}")
        else:
            print(f"File not found: {path}")

if __name__ == "__main__":
    disable_problem_files()
    print("Problem files disabled successfully.") 