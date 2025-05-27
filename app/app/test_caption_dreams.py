#!/usr/bin/env python3
"""
Test script for the Caption The Dreams page functionality
"""
import os
import sys
import traceback
from pathlib import Path

# No need for additional path manipulation since we're already in the correct directory
# Import the required modules
try:
    from utils.video.captions import (
        add_captions_to_video,
        DREAM_ANIMATION_STYLES
    )
    from utils.audio.transcription import transcribe_video
    print("Successfully imported required modules")
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_caption_dreams_functionality():
    """Test the Caption The Dreams functionality"""
    # Check if a test video exists
    test_video = Path("sample_video.mp4")
    if not test_video.exists():
        print(f"Test video not found: {test_video}")
        print("Please provide a test video as sample_video.mp4 in the project root")
        return False
    
    print(f"Found test video: {test_video}")
    
    # Test the transcription function
    print("\nTesting transcription...")
    try:
        result = transcribe_video(str(test_video), model_size="tiny", engine="whisper")
        if result.get("status") == "success":
            print("✅ Transcription successful")
            word_count = len(result.get("words", []))
            print(f"Found {word_count} words in the transcript")
        else:
            print(f"❌ Transcription failed: {result.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error during transcription: {str(e)}")
        traceback.print_exc()
        return False
    
    # Test each animation style
    print("\nTesting animation styles:")
    for style_name, style_info in DREAM_ANIMATION_STYLES.items():
        print(f"\nTesting '{style_name}' animation style ({style_info['name']})...")
        
        output_path = f"test_outputs/captioned_{style_name}_{test_video.name}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # Use the transcription result directly from the previous step
            words_with_times = []
            for word in result.get("words", []):
                words_with_times.append({
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"]
                })
            
            if not words_with_times:
                print("❌ No words available from transcription, skipping animation test")
                continue
                
            # Fixed model_size and engine parameters
            result = add_captions_to_video(
                str(test_video),
                output_path=output_path,
                style_name="tiktok",  # Use TikTok style as base
                model_size="tiny",    # Use tiny model for faster testing
                engine="whisper",     # Explicitly use whisper 
                animation_style=style_name
            )
            
            if result.get("status") == "success":
                print(f"✅ Successfully generated captions with '{style_name}' style")
                print(f"Output saved to: {result.get('output_path')}")
            else:
                print(f"❌ Failed to generate captions: {result.get('message', 'Unknown error')}")
                if "traceback" in result:
                    print(f"Traceback: {result['traceback']}")
        except Exception as e:
            print(f"❌ Error generating captions: {str(e)}")
            traceback.print_exc()
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    print("Testing Caption The Dreams functionality")
    success = test_caption_dreams_functionality()
    sys.exit(0 if success else 1) 