#!/usr/bin/env python3
"""
Script to fix syntax error in captions.py
"""
import os
import sys

def fix_syntax_error():
    """Fix the syntax error in captions.py"""
    file_path = "utils/video/captions.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Fix the syntax error around line 836
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for the line with the issue
        if "try:" in line and i + 1 < len(lines) and "scaled_font = ImageFont.truetype" in lines[i+1]:
            # Check if there's a closing parenthesis issue
            if ")\\n" in lines[i+1] or ")\n" not in lines[i+1]:
                # Fix the line by ensuring proper closing parenthesis
                fixed_line = lines[i+1].rstrip().rstrip('\\').rstrip() + ")\n"
                fixed_lines.append(line)
                fixed_lines.append(fixed_line)
                i += 2
                continue
        
        fixed_lines.append(line)
        i += 1
    
    # Write the fixed content back to the file
    with open(file_path, 'w') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed syntax error in {file_path}")
    return True

if __name__ == "__main__":
    success = fix_syntax_error()
    sys.exit(0 if success else 1) 