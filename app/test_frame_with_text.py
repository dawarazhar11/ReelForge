#!/usr/bin/env python3
"""
Test script for the frame with text functionality directly
"""
import os
import sys
import numpy as np
from PIL import Image

# Import the required modules
try:
    from utils.video.captions import (
        DREAM_ANIMATION_STYLES,
        make_frame_with_text
    )
    print("Successfully imported required modules")
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_frame_with_text():
    """Test frame with text functionality directly"""
    # Create a sample frame (black image with size 1280x720)
    width, height = 1280, 720
    sample_frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create sample words with timing
    words_with_times = [
        {"word": "I", "start": 0.0, "end": 0.34},
        {"word": "see", "start": 0.34, "end": 0.66},
        {"word": "light", "start": 0.66, "end": 0.98},
        {"word": "bouncing", "start": 0.98, "end": 1.56},
        {"word": "off", "start": 1.56, "end": 2.02},
        {"word": "particles", "start": 2.02, "end": 2.46}
    ]
    
    # Prepare text
    text = " ".join([w["word"] for w in words_with_times])
    
    # Create output directory for test images
    os.makedirs("test_outputs/frames", exist_ok=True)
    
    # Test each animation style with a few timestamps
    print("\nTesting animation styles:")
    for style_name, style_info in DREAM_ANIMATION_STYLES.items():
        print(f"\nTesting '{style_name}' animation style ({style_info['name']})...")
        
        # Test with a few different timestamps
        for t in [0.2, 0.8, 1.3, 2.2]:
            try:
                # Apply captions to the frame
                frame_with_captions = make_frame_with_text(
                    sample_frame,
                    text,
                    words_with_times, 
                    t,
                    "tiktok",  # Use style name as string
                    animation_style=style_name
                )
                
                # Save the frame as an image
                output_path = f"test_outputs/frames/{style_name}_t{t:.1f}.jpg"
                Image.fromarray(frame_with_captions).save(output_path)
                
                print(f"✅ Successfully generated frame at t={t:.1f}s")
                print(f"   Saved to: {output_path}")
                
            except Exception as e:
                print(f"❌ Error generating frame at t={t:.1f}s: {str(e)}")
                import traceback
                traceback.print_exc()
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    print("Testing frame with text functionality")
    success = test_frame_with_text()
    sys.exit(0 if success else 1) 