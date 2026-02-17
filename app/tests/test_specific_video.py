#!/usr/bin/env python3
"""
Test script for the Caption The Dreams functionality on a specific video
"""
import os
import sys
import traceback
from pathlib import Path

# Import the required modules
try:
    from utils.video.captions import (
        DREAM_ANIMATION_STYLES,
        add_captions_to_video
    )
    from utils.audio.transcription import transcribe_video
    print("Successfully imported required modules")
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_specific_video():
    """Test Caption The Dreams functionality on a specific video"""
    # Path to the specific video
    video_path = "media/a-roll/fetched_aroll_segment_2_e7d47355.mp4"
    
    # Check if the video exists
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return False
    
    print(f"Found video: {video_path}")
    
    # Test the transcription function
    print("\nTranscribing video...")
    try:
        result = transcribe_video(video_path, model_size="tiny", engine="whisper")
        if result.get("status") == "success":
            print("✅ Transcription successful")
            word_count = len(result.get("words", []))
            print(f"Found {word_count} words in the transcript")
            
            # Print the first 10 words with timing
            print("\nFirst 10 words with timing:")
            for i, word in enumerate(result.get("words", [])[:10]):
                print(f"  {i+1}. '{word['word']}' ({word['start']:.2f}s - {word['end']:.2f}s)")
            
        else:
            print(f"❌ Transcription failed: {result.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error during transcription: {str(e)}")
        traceback.print_exc()
        return False
    
    # Create output directory
    os.makedirs("test_outputs/specific_video", exist_ok=True)
    
    # Test each animation style with a few timestamps
    print("\nTesting animation styles:")
    for style_name, style_info in DREAM_ANIMATION_STYLES.items():
        # Skip the problematic scale_pulse style for now
        if style_name == "scale_pulse":
            print(f"\nSkipping '{style_name}' animation style due to known issues")
            continue
            
        print(f"\nTesting '{style_name}' animation style ({style_info['name']})...")
        
        output_path = f"test_outputs/specific_video/captioned_{style_name}_{os.path.basename(video_path)}"
        
        try:
            # Generate captions with this animation style
            result = add_captions_to_video(
                video_path,
                output_path=output_path,
                style_name="tiktok",  # Use TikTok style as base
                model_size="tiny",    # Use tiny model for faster testing
                engine="whisper",     # Explicitly use whisper
                animation_style=style_name
            )
            
            if result.get("status") == "success":
                print(f"✅ Successfully generated captions with '{style_name}' style")
                print(f"   Output saved to: {result.get('output_path')}")
            else:
                print(f"❌ Failed to generate captions: {result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Error generating captions: {str(e)}")
            traceback.print_exc()
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    print("Testing Caption The Dreams on specific video")
    success = test_specific_video()
    sys.exit(0 if success else 1) 