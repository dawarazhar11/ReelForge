#!/usr/bin/env python3
"""
Restore captions.py from backup to fix indentation errors
"""

import os
import shutil
from pathlib import Path

def restore_from_backup():
    """Restore captions.py from a backup file"""
    # Get the path to the current directory
    current_dir = Path(__file__).parent
    
    # Find all backup files
    backup_files = list(current_dir.glob("captions.py.*.bak"))
    
    if not backup_files:
        print("No backup files found.")
        return False
    
    # Sort by modification time (newest first)
    backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    # Get the newest backup
    newest_backup = backup_files[0]
    print(f"Found backup file: {newest_backup}")
    
    # Original file
    original_file = current_dir / "captions.py"
    
    # Create a new backup of the current (broken) file
    broken_backup = current_dir / "captions.py.broken.bak"
    shutil.copy2(original_file, broken_backup)
    print(f"Created backup of broken file at: {broken_backup}")
    
    # Restore from backup
    shutil.copy2(newest_backup, original_file)
    print(f"Restored from backup: {newest_backup}")
    
    # Verify the file works
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("captions", original_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print("✅ Successfully imported the restored captions.py file")
        return True
    except Exception as e:
        print(f"❌ Error importing restored file: {e}")
        return False

if __name__ == "__main__":
    print("Restoring captions.py from backup...")
    if restore_from_backup():
        print("✅ Restore completed successfully")
    else:
        print("❌ Restore failed") 