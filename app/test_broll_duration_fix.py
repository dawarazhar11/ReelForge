#!/usr/bin/env python3
"""
Test B-Roll Image Duration Fix

This script tests that B-Roll images are correctly converted to videos with durations
that match their corresponding A-Roll audio segments.
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

# Import the necessary functions
try:
    from utils.video.assembly import image_to_video, is_image_file
    from utils.video.simple_assembly import image_to_video as simple_image_to_video
    
    # Check if MoviePy is available
    try:
        import moviepy.editor as mp
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False
        print("MoviePy not available, will test only simple_assembly")
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)

def get_video_duration(video_path):
    """Get the duration of a video file using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"Error getting video duration: {str(e)}")
        return None

def create_test_image(output_path):
    """Create a simple test image"""
    try:
        # Check if PIL is available
        from PIL import Image, ImageDraw
        
        # Create a 640x480 image with some text
        img = Image.new('RGB', (640, 480), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Test B-Roll Image", fill=(255, 255, 0))
        
        # Save the image
        img.save(output_path)
        return True
    except ImportError:
        print("PIL not available, cannot create test image")
        return False

def test_assembly_image_to_video():
    """Test the assembly.py image_to_video function"""
    if not MOVIEPY_AVAILABLE:
        print("MoviePy not available, skipping assembly.py test")
        return False
    
    print("\n=== Testing assembly.py image_to_video ===")
    
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test image
        image_path = os.path.join(temp_dir, "test_image.png")
        if not create_test_image(image_path):
            # Try to use an existing image if we can't create one
            test_images = [
                "media/b-roll/image_0.png",
                "media/images/broll_0.png",
                "config/user_data/my_short_video/media/b-roll/image_0.png"
            ]
            for img in test_images:
                if os.path.exists(img):
                    image_path = img
                    break
            else:
                print("No test image available, skipping test")
                return False
        
        print(f"Using test image: {image_path}")
        
        # Test with different durations
        test_durations = [3.0, 4.5, 6.0]
        success = True
        
        for duration in test_durations:
            print(f"\nTesting with duration: {duration}s")
            
            # Convert image to video
            clip = image_to_video(image_path, duration=duration)
            
            if clip is None:
                print(f"Failed to convert image to video with duration {duration}s")
                success = False
                continue
            
            # Check the clip duration
            clip_duration = clip.duration
            print(f"Resulting clip duration: {clip_duration}s")
            
            # Verify the duration is correct
            if abs(clip_duration - duration) > 0.1:
                print(f"ERROR: Duration mismatch! Expected {duration}s, got {clip_duration}s")
                success = False
            else:
                print(f"SUCCESS: Duration matches expected value")
                
            # Clean up
            clip.close()
        
        return success

def test_simple_assembly_image_to_video():
    """Test the simple_assembly.py image_to_video function"""
    print("\n=== Testing simple_assembly.py image_to_video ===")
    
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test image
        image_path = os.path.join(temp_dir, "test_image.png")
        if not create_test_image(image_path):
            # Try to use an existing image if we can't create one
            test_images = [
                "media/b-roll/image_0.png",
                "media/images/broll_0.png",
                "config/user_data/my_short_video/media/b-roll/image_0.png"
            ]
            for img in test_images:
                if os.path.exists(img):
                    image_path = img
                    break
            else:
                print("No test image available, skipping test")
                return False
        
        print(f"Using test image: {image_path}")
        
        # Test with different durations
        test_durations = [3.0, 4.5, 6.0]
        success = True
        
        for duration in test_durations:
            print(f"\nTesting with duration: {duration}s")
            
            # Output path for the video
            output_path = os.path.join(temp_dir, f"test_video_{duration}.mp4")
            
            # Convert image to video
            result = simple_image_to_video(image_path, output_path, duration=duration)
            
            if not result:
                print(f"Failed to convert image to video with duration {duration}s")
                success = False
                continue
            
            # Check if the output file exists
            if not os.path.exists(output_path):
                print(f"ERROR: Output file not created: {output_path}")
                success = False
                continue
            
            # Get the video duration
            video_duration = get_video_duration(output_path)
            print(f"Resulting video duration: {video_duration}s")
            
            # Verify the duration is correct
            if video_duration is None:
                print("ERROR: Could not determine video duration")
                success = False
            elif abs(video_duration - duration) > 0.1:
                print(f"ERROR: Duration mismatch! Expected {duration}s, got {video_duration}s")
                success = False
            else:
                print(f"SUCCESS: Duration matches expected value")
        
        return success

def main():
    """Main function"""
    print("Testing B-Roll Image Duration Fix")
    
    # Test assembly.py image_to_video
    assembly_success = test_assembly_image_to_video()
    
    # Test simple_assembly.py image_to_video
    simple_assembly_success = test_simple_assembly_image_to_video()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"assembly.py image_to_video: {'PASS' if assembly_success else 'FAIL'}")
    print(f"simple_assembly.py image_to_video: {'PASS' if simple_assembly_success else 'FAIL'}")
    
    # Return success if both tests pass
    return 0 if assembly_success and simple_assembly_success else 1

if __name__ == "__main__":
    sys.exit(main()) 