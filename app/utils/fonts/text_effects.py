#!/usr/bin/env python3
"""
Text effects and caption utilities for videos.
"""

import os
import sys
import traceback
from pathlib import Path
import tempfile
import json
import time
from datetime import datetime

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path from text_effects module")

# Import error handler decorator to gracefully handle errors in functions
def error_handler(func):
    """Decorator to handle errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error in {func.__name__}: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
    return wrapper

# Try to import MoviePy, if it fails we'll handle it gracefully
try:
    import moviepy.editor as mp
    from moviepy.video.tools.subtitles import SubtitlesClip
    from moviepy.video.fx import resize
    import numpy as np
    MOVIEPY_AVAILABLE = True
    print("✅ Successfully imported moviepy in text_effects module")
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    print(f"❌ Error importing moviepy in text_effects module: {str(e)}")
    print("Please run: python utils/video/dependencies.py to install required packages")

@error_handler
def add_captions_to_video(video_path, captions_data=None, output_path=None, font='Arial', fontsize=40, 
                          color='white', stroke_color='black', stroke_width=2, 
                          position=('center', 'bottom'), 
                          progress_callback=None):
    """
    Add captions to a video based on provided caption data
    
    Args:
        video_path: Path to the video file
        captions_data: Dictionary or list of caption data with timing information
        output_path: Path to save the output video (optional)
        font: Font name to use for captions
        fontsize: Font size for captions
        color: Text color for captions
        stroke_color: Outline color for captions
        stroke_width: Width of text outline
        position: Position of captions on screen ('center', 'bottom')
        progress_callback: Function to call with progress updates
        
    Returns:
        dict: Result containing status and output path
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy not available"}
    
    # Check if video file exists
    if not os.path.exists(video_path):
        return {"status": "error", "message": f"Video file not found: {video_path}"}
    
    # Generate output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captioned_{timestamp}.mp4"
        output_path = os.path.join(os.path.dirname(video_path), filename)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Define progress callback function
    def progress_print(progress, message=None):
        if progress_callback:
            progress_callback(progress, message)
        else:
            print(f"Captioning progress: {progress:.1f}%")
    
    try:
        progress_print(10, "Loading video")
        video = mp.VideoFileClip(video_path)
        
        # If no captions data provided, return original video
        if not captions_data:
            progress_print(20, "No captions data provided, saving original video")
            video.write_videofile(output_path)
            video.close()
            return {
                "status": "success", 
                "message": "No captions data provided, saved original video",
                "output_path": output_path
            }
        
        # Process captions data based on format
        progress_print(30, "Processing captions data")
        subtitles = []
        
        # Handle different caption data formats
        if isinstance(captions_data, list):
            # List of caption objects with start, end, text
            for caption in captions_data:
                if "start" in caption and "end" in caption and "text" in caption:
                    subtitles.append(((caption["start"], caption["end"]), caption["text"]))
        elif isinstance(captions_data, dict):
            # Dictionary with words or segments
            if "words" in captions_data:
                # Group words into sentences/phrases
                words = captions_data["words"]
                current_text = ""
                current_start = None
                
                for word in words:
                    if "word" in word and "start" in word and "end" in word:
                        if current_start is None:
                            current_start = word["start"]
                            current_text = word["word"]
                        else:
                            # If more than 1 second gap, start a new caption
                            if word["start"] - (current_start + len(current_text) * 0.1) > 1.0:
                                subtitles.append(((current_start, word["start"]), current_text))
                                current_start = word["start"]
                                current_text = word["word"]
                            else:
                                current_text += " " + word["word"]
                
                # Add the last caption
                if current_text:
                    end_time = words[-1]["end"] if words else video.duration
                    subtitles.append(((current_start, end_time), current_text))
            
            elif "segments" in captions_data:
                # Segments with start, end, text
                segments = captions_data["segments"]
                for segment in segments:
                    if "start" in segment and "end" in segment and "text" in segment:
                        subtitles.append(((segment["start"], segment["end"]), segment["text"]))
        
        # If no subtitles were extracted, return original video
        if not subtitles:
            progress_print(40, "No valid captions found, saving original video")
            video.write_videofile(output_path)
            video.close()
            return {
                "status": "success", 
                "message": "No valid captions found, saved original video",
                "output_path": output_path
            }
        
        # Define a generator function for text positions
        def generator(txt):
            return mp.TextClip(
                txt, 
                font=font, 
                fontsize=fontsize, 
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                method='caption',
                align='center',
                size=(video.w * 0.9, None)  # Width constraint
            )
        
        # Create subtitles clip
        progress_print(50, "Creating subtitles clip")
        subtitles_clip = SubtitlesClip(subtitles, generator)
        
        # Position the subtitles
        if position == ('center', 'bottom'):
            y_position = video.h - fontsize * 2  # Position from bottom
            subtitles_clip = subtitles_clip.set_position(('center', y_position))
        else:
            subtitles_clip = subtitles_clip.set_position(position)
        
        # Overlay subtitles on video
        progress_print(70, "Compositing video with captions")
        final_clip = mp.CompositeVideoClip([video, subtitles_clip])
        
        # Write the output file
        progress_print(80, "Writing output video")
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            fps=video.fps
        )
        
        # Close clips to release resources
        progress_print(95, "Cleaning up resources")
        video.close()
        subtitles_clip.close()
        final_clip.close()
        
        progress_print(100, "Caption addition complete")
        
        return {
            "status": "success",
            "message": "Captions added successfully",
            "output_path": output_path
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error adding captions: {str(e)}",
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    # Simple test if this script is run directly
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
        # Sample captions data
        captions_data = {
            "segments": [
                {"start": 0, "end": 3, "text": "This is a test caption"},
                {"start": 4, "end": 7, "text": "Adding captions to videos"},
                {"start": 8, "end": 12, "text": "Using the text_effects module"}
            ]
        }
        
        result = add_captions_to_video(video_path, captions_data)
        
        if result["status"] == "success":
            print(f"Captions added successfully! Output: {result['output_path']}")
        else:
            print(f"Error adding captions: {result['message']}")
    else:
        print("Usage: python text_effects.py <video_path>")
        print("This will add sample captions to the specified video.") 