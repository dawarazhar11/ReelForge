#!/usr/bin/env python3
"""
Test script for the Caption The Dreams page functionality
"""
import os
import sys
import json
import traceback
from pathlib import Path

# Import the required modules
try:
    from utils.video.captions import (
        DREAM_ANIMATION_STYLES,
        make_frame_with_text,
        get_caption_style
    )
    from utils.audio.transcription import transcribe_video
    import numpy as np
    from PIL import Image
    print("Successfully imported required modules")
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_animation_functionality():
    """Test the animation functionality directly without video processing"""
    print("Testing animation styles directly by creating sample frames")
    
    # Create a sample frame (black image)
    width, height = 1280, 720
    sample_frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create sample words with timing
    words_with_times = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 0.6, "end": 1.0},
        {"word": "this", "start": 1.1, "end": 1.3},
        {"word": "is", "start": 1.4, "end": 1.5},
        {"word": "a", "start": 1.6, "end": 1.7},
        {"word": "test", "start": 1.8, "end": 2.0}
    ]
    
    # Test each animation style with a few timestamps
    print("\nTesting animation styles:")
    for style_name, style_info in DREAM_ANIMATION_STYLES.items():
        print(f"\nTesting '{style_name}' animation style ({style_info['name']})...")
        
        # Create output directory for test images
        os.makedirs("test_outputs/animation_test", exist_ok=True)
        
        # Test with a few different timestamps
        for t in [0.2, 0.7, 1.2, 1.9]:
            try:
                # Get full text
                text = " ".join([w["word"] for w in words_with_times])
                
                # Apply captions to the frame
                frame_with_captions = make_frame_with_text(
                    sample_frame, 
                    text,
                    words_with_times, 
                    t, 
                    "tiktok",  # Use style name
                    animation_style=style_name
                )
                
                # Save the frame as an image
                output_path = f"test_outputs/animation_test/{style_name}_t{t:.1f}.jpg"
                Image.fromarray(frame_with_captions).save(output_path)
                
                print(f"✅ Successfully generated frame at t={t:.1f}s")
                print(f"   Saved to: {output_path}")
                
            except Exception as e:
                print(f"❌ Error generating frame at t={t:.1f}s: {str(e)}")
                traceback.print_exc()
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    print("Testing Caption The Dreams functionality")
    success = test_animation_functionality()
    sys.exit(0 if success else 1) 