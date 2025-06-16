#!/usr/bin/env python3
"""
Fix script for moviepy dependency issues in AI Money Printer
"""

import os
import sys
import subprocess
import platform
import site
import importlib.util

def print_color(text, color="green"):
    """Print colored text"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "end": "\033[0m"
    }
    print(f"{colors.get(color, colors['green'])}{text}{colors['end']}")

def run_command(cmd, verbose=True):
    """Run a shell command and return the output"""
    if verbose:
        print_color(f"Running: {cmd}", "blue")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        if verbose and result.stdout:
            print(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        if verbose:
            print_color(f"Error: {e}", "red")
            if e.stderr:
                print_color(f"Error details: {e.stderr}", "red")
        return False, e.stderr

def check_module_installed(module_name):
    """Check if a Python module is installed"""
    spec = importlib.util.find_spec(module_name)
    return spec is not None

def install_module(module_name, version=None):
    """Install a Python module using pip"""
    module_spec = f"{module_name}=={version}" if version else module_name
    print_color(f"Installing {module_spec}...", "yellow")
    success, _ = run_command(f"{sys.executable} -m pip install {module_spec}")
    return success

def check_ffmpeg():
    """Check if FFmpeg is installed and install it if needed"""
    print_color("Checking for FFmpeg...", "yellow")
    success, _ = run_command("ffmpeg -version", verbose=False)
    
    if success:
        print_color("FFmpeg is installed!", "green")
        return True
    
    print_color("FFmpeg not found. Attempting to install...", "yellow")
    
    # Try to install FFmpeg based on platform
    if platform.system() == "Darwin":  # macOS
        success, _ = run_command("brew install ffmpeg")
        if not success:
            print_color("Failed to install FFmpeg with Homebrew. Trying pip...", "yellow")
            install_module("ffmpeg-python")
    elif platform.system() == "Linux":
        success, _ = run_command("sudo apt-get update && sudo apt-get install -y ffmpeg")
        if not success:
            print_color("Failed to install FFmpeg with apt. Trying pip...", "yellow")
            install_module("ffmpeg-python")
    else:
        print_color("Unsupported platform for automatic FFmpeg installation.", "red")
        print_color("Please install FFmpeg manually: https://ffmpeg.org/download.html", "yellow")
        install_module("ffmpeg-python")
    
    # Check again
    success, _ = run_command("ffmpeg -version", verbose=False)
    if success:
        print_color("FFmpeg is now installed!", "green")
        return True
    else:
        print_color("FFmpeg installation failed. Please install manually.", "red")
        return False

def fix_moviepy():
    """Fix moviepy installation issues"""
    print_color("Checking moviepy installation...", "yellow")
    
    # Try to import moviepy
    try:
        import moviepy.editor
        print_color(f"moviepy is already installed (version {moviepy.editor.__version__})", "green")
        return True
    except ImportError as e:
        print_color(f"Error importing moviepy: {e}", "red")
    
    # Install dependencies
    print_color("Installing moviepy and dependencies...", "yellow")
    
    # First, make sure pip is up to date
    run_command(f"{sys.executable} -m pip install --upgrade pip")
    
    # Install moviepy with specific version
    success = install_module("moviepy", "1.0.3")
    if not success:
        print_color("Failed to install moviepy with version 1.0.3. Trying without version...", "yellow")
        success = install_module("moviepy")
    
    # Install related dependencies
    dependencies = [
        ("numpy", "1.24.0"),
        ("decorator", "4.4.2"),
        ("imageio", "2.25.1"),
        ("imageio-ffmpeg", "0.4.8"),
        ("proglog", "0.1.10"),
        ("tqdm", "4.66.1")
    ]
    
    for dep, ver in dependencies:
        install_module(dep, ver)
    
    # Try to import moviepy again
    try:
        import moviepy.editor
        print_color(f"moviepy is now installed (version {moviepy.editor.__version__})", "green")
        return True
    except ImportError as e:
        print_color(f"Still having issues importing moviepy: {e}", "red")
        
        # Last resort: try without cache
        print_color("Trying alternative installation method...", "yellow")
        run_command(f"{sys.executable} -m pip uninstall -y moviepy")
        run_command(f"{sys.executable} -m pip install moviepy --no-cache-dir")
        
        try:
            import moviepy.editor
            print_color(f"moviepy is now installed (version {moviepy.editor.__version__})", "green")
            return True
        except ImportError as e:
            print_color(f"Failed to install moviepy: {e}", "red")
            return False

def check_python_path():
    """Check Python path and print information"""
    print_color("\nPython Environment Information:", "blue")
    print_color(f"Python executable: {sys.executable}", "yellow")
    print_color(f"Python version: {platform.python_version()}", "yellow")
    print_color(f"Platform: {platform.platform()}", "yellow")
    
    print_color("\nPython Path:", "blue")
    for path in sys.path:
        print_color(f"  {path}", "yellow")
    
    print_color("\nSite Packages:", "blue")
    for path in site.getsitepackages():
        print_color(f"  {path}", "yellow")

def main():
    """Main function"""
    print_color("\n=== AI Money Printer - MoviePy Fix Tool ===\n", "blue")
    
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        print_color("Running in a virtual environment", "green")
    else:
        print_color("Not running in a virtual environment", "yellow")
        print_color("It's recommended to use a virtual environment", "yellow")
        
        # Ask if user wants to create one
        response = input("Create a virtual environment? (y/n): ").lower()
        if response == 'y':
            run_command(f"{sys.executable} -m pip install virtualenv")
            run_command(f"{sys.executable} -m virtualenv venv")
            
            # Provide instructions to activate
            print_color("\nVirtual environment created!", "green")
            print_color("Please activate it and run this script again:", "yellow")
            if platform.system() == "Windows":
                print_color("  venv\\Scripts\\activate", "blue")
            else:
                print_color("  source venv/bin/activate", "blue")
            return
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    
    # Fix moviepy
    moviepy_ok = fix_moviepy()
    
    # Check other critical dependencies
    print_color("\nChecking other critical dependencies...", "yellow")
    other_deps = [
        ("pydub", "0.25.1"),
        ("opencv-python", "4.7.0"),
        ("matplotlib", "3.7.0"),
        ("pandas", "2.0.0"),
        ("python-dotenv", "1.0.0"),
        ("streamlit", "1.30.0")
    ]
    
    for dep, ver in other_deps:
        if not check_module_installed(dep.split("-")[0]):
            install_module(dep, ver)
    
    # Print Python path information
    check_python_path()
    
    # Final status
    print_color("\n=== Fix Summary ===", "blue")
    print_color(f"FFmpeg: {'✓ Installed' if ffmpeg_ok else '✗ Not installed'}", 
               "green" if ffmpeg_ok else "red")
    print_color(f"MoviePy: {'✓ Installed' if moviepy_ok else '✗ Not installed'}", 
               "green" if moviepy_ok else "red")
    
    if moviepy_ok and ffmpeg_ok:
        print_color("\nAll fixes applied successfully! You can now run the app.", "green")
        print_color("Run: ./run_app.sh", "blue")
    else:
        print_color("\nSome issues could not be fixed automatically.", "red")
        print_color("Please see the error messages above for manual steps.", "yellow")

if __name__ == "__main__":
    main() 