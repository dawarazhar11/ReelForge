"""
Video segmentation utilities to automatically split A-Roll videos into logical segments.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_segment_timestamps(
    transcript_data: Dict[str, Any],
    segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Map logical segments to actual timestamps in the transcript.
    
    Args:
        transcript_data: Complete transcript with word-level timestamps
        segments: Logical segments without timestamps
        
    Returns:
        Segments with start and end timestamps added
    """
    if not transcript_data or "segments" not in transcript_data:
        logger.error("Invalid transcript data format")
        return segments
    
    # Extract all words with their timestamps
    all_words = []
    for segment in transcript_data["segments"]:
        if "words" not in segment:
            continue
            
        for word in segment["words"]:
            if "start" in word and "end" in word and "word" in word:
                all_words.append({
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"]
                })
    
    if not all_words:
        logger.error("No word timestamps found in transcript")
        return segments
    
    # Reassemble the full text with indices for each word
    full_text = " ".join([w["word"] for w in all_words])
    
    # Map each segment to timestamps
    result_segments = []
    
    for segment in segments:
        content = segment["content"]
        # Find this content in the full text (approximate matching)
        start_idx = find_best_match(content, full_text)
        
        if start_idx == -1:
            # Couldn't find a good match, skip this segment
            logger.warning(f"Could not find timestamp match for segment: {content[:30]}...")
            segment["start_time"] = 0
            segment["end_time"] = 0
            result_segments.append(segment)
            continue
            
        # Count words to determine the approximate word boundaries
        segment_word_count = len(content.split())
        words_before = len(full_text[:start_idx].split())
        
        if words_before >= len(all_words):
            words_before = len(all_words) - 1
            
        # Find the word indices in our all_words list
        start_word_idx = words_before
        end_word_idx = min(start_word_idx + segment_word_count, len(all_words) - 1)
        
        # Get the timestamps
        segment["start_time"] = all_words[start_word_idx]["start"]
        segment["end_time"] = all_words[end_word_idx]["end"]
        
        result_segments.append(segment)
    
    # Ensure segments don't overlap
    for i in range(1, len(result_segments)):
        if result_segments[i]["start_time"] < result_segments[i-1]["end_time"]:
            # Use the midpoint between segments
            midpoint = (result_segments[i-1]["end_time"] + result_segments[i]["start_time"]) / 2
            result_segments[i-1]["end_time"] = midpoint
            result_segments[i]["start_time"] = midpoint
    
    return result_segments

def find_best_match(segment: str, full_text: str) -> int:
    """
    Find the best match for a segment within the full text.
    Uses a simple approach to find the segment's position.
    
    Args:
        segment: The segment text to locate
        full_text: The full transcript text
        
    Returns:
        Starting index of the best match, or -1 if no good match found
    """
    # First try exact matching
    start_idx = full_text.find(segment)
    if start_idx != -1:
        return start_idx
    
    # Try simplified matching (lowercase, no punctuation)
    import re
    segment_simple = re.sub(r'[^\w\s]', '', segment.lower())
    full_text_simple = re.sub(r'[^\w\s]', '', full_text.lower())
    
    start_idx = full_text_simple.find(segment_simple)
    if start_idx != -1:
        return start_idx
    
    # Try fuzzy matching with the first few words
    segment_words = segment_simple.split()
    if len(segment_words) >= 3:
        first_words = " ".join(segment_words[:3])
        start_idx = full_text_simple.find(first_words)
        if start_idx != -1:
            return start_idx
    
    # If all else fails, return -1
    return -1

def cut_video_segments(
    video_path: str,
    segments: List[Dict[str, Any]],
    output_dir: str
) -> List[Dict[str, Any]]:
    """
    Cut a video into segments based on timestamps.
    
    Args:
        video_path: Path to the input video file
        segments: List of segments with start_time and end_time
        output_dir: Directory to save the output segments
        
    Returns:
        Updated segments with file paths added
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Load the video
    try:
        video = VideoFileClip(video_path)
    except Exception as e:
        print(f"Error loading video: {str(e)}")
        return []
    
    # Process each segment
    updated_segments = []
    for i, segment in enumerate(segments):
        try:
            # Extract start and end times
            start_time = segment.get("start_time", 0)
            end_time = segment.get("end_time", 0)
            
            # Skip if invalid timing
            if end_time <= start_time:
                print(f"Invalid timing for segment {i}: start={start_time}, end={end_time}")
                # Still ensure it has a segment_id and update it
                segment["segment_id"] = f"segment_{i}"
                updated_segments.append(segment)
                continue
            
            # Cut the segment
            segment_clip = video.subclip(start_time, end_time)
            
            # Generate the output filename
            segment_id = f"segment_{i}"
            # Ensure segment has an ID property
            segment["segment_id"] = segment_id
            
            output_filename = f"{base_name}_segment_{i}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            # Use absolute path for file_path to ensure it can be found from anywhere
            absolute_output_path = os.path.abspath(output_path)
            
            # Save the segment
            print(f"Writing segment {i} to {output_path}")
            segment_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                preset="ultrafast",
                fps=video.fps
            )
            
            # Update the segment with the file path
            segment["file_path"] = absolute_output_path
            segment["segment_id"] = segment_id
            updated_segments.append(segment)
            
            # Close the segment clip
            segment_clip.close()
            
            # Log success
            print(f"✅ Successfully created segment {i}: {absolute_output_path}")
            
        except Exception as e:
            print(f"Error processing segment {i}: {str(e)}")
            # Still ensure it has a segment_id even if there was an error
            segment["segment_id"] = f"segment_{i}"
            updated_segments.append(segment)
    
    # Close the main video
    video.close()
    
    # Log the number of segments created
    print(f"Created {len(updated_segments)} segments, with {sum(1 for s in updated_segments if 'file_path' in s)} having valid file paths")
    
    return updated_segments

def save_segment_metadata(segments: List[Dict[str, Any]], output_path: str) -> bool:
    """
    Save segment metadata to a JSON file.
    
    Args:
        segments: List of segment data
        output_path: Path to save the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_path, 'w') as f:
            json.dump({"segments": segments}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save segment metadata: {str(e)}")
        return False

def load_segment_metadata(input_path: str) -> List[Dict[str, Any]]:
    """
    Load segment metadata from a JSON file.
    
    Args:
        input_path: Path to the JSON file
        
    Returns:
        List of segment data, or empty list if file not found
    """
    try:
        with open(input_path, 'r') as f:
            data = json.load(f)
        return data.get("segments", [])
    except Exception as e:
        logger.error(f"Failed to load segment metadata: {str(e)}")
        return []

def preview_segment(video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
    """
    Create a preview of a video segment.
    
    Args:
        video_path: Path to the input video
        start_time: Start time in seconds
        end_time: End time in seconds
        output_path: Path to save the preview
        
    Returns:
        True if successful, False otherwise
    """
    try:
        video = VideoFileClip(video_path)
        segment = video.subclip(start_time, end_time)
        segment.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(os.path.dirname(output_path), "temp_preview.m4a"),
            remove_temp=True,
            threads=4,
            verbose=False,
            logger=None
        )
        video.close()
        return True
    except Exception as e:
        logger.error(f"Failed to create segment preview: {str(e)}")
        return False 