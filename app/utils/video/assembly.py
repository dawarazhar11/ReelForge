#!/usr/bin/env python3
import os
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
import json
import tempfile
import subprocess
import shutil

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path from assembly module")

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
    from moviepy.video.fx import resize, speedx
    import numpy as np
    MOVIEPY_AVAILABLE = True
    print("✅ Successfully imported moviepy in assembly module")
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    print(f"❌ Error importing moviepy in assembly module: {str(e)}")
    print("Please run: python utils/video/dependencies.py to install required packages")

@error_handler
def check_file(file_path, file_type="video"):
    """
    Check if a file exists and is valid
    
    Args:
        file_path: Path to the file
        file_type: Type of file (video, image, audio)
        
    Returns:
        dict: Result containing status and additional info
    """
    if not file_path:
        return {"status": "error", "message": f"No {file_type} path provided"}
        
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"{file_type.capitalize()} file not found: {file_path}"}
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return {"status": "error", "message": f"{file_type.capitalize()} file is empty: {file_path}"}
    
    # For video/audio files, validate they're proper media files
    if file_type in ["video", "audio"] and MOVIEPY_AVAILABLE:
        try:
            if file_type == "video":
                clip = mp.VideoFileClip(file_path)
                duration = clip.duration
                width, height = clip.size
                clip.close()
                return {
                    "status": "success", 
                    "path": file_path,
                    "size": file_size,
                    "duration": duration,
                    "width": width,
                    "height": height
                }
            elif file_type == "audio":
                clip = mp.AudioFileClip(file_path)
                duration = clip.duration
                clip.close()
                return {
                    "status": "success", 
                    "path": file_path,
                    "size": file_size,
                    "duration": duration
                }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Invalid {file_type} file: {file_path}", 
                "error": str(e)
            }
    
    # For image files or if MoviePy is not available
    return {"status": "success", "path": file_path, "size": file_size}

@error_handler
def resize_video(clip, target_resolution=(1080, 1920)):
    """
    Resize video clip to target resolution maintaining aspect ratio with padding
    
    Args:
        clip: MoviePy video clip
        target_resolution: Target resolution (width, height)
        
    Returns:
        Resized video clip
    """
    if not MOVIEPY_AVAILABLE:
        return None
    
    # Get original dimensions
    w, h = clip.size
    
    # Calculate target aspect ratio
    target_aspect = target_resolution[0] / target_resolution[1]  # width/height
    current_aspect = w / h
    
    try:
        if current_aspect > target_aspect:
            # Video is wider than target aspect ratio - fit to width
            new_width = target_resolution[0]
            new_height = int(new_width / current_aspect)
            resized_clip = clip.resize(width=new_width, height=new_height)
            
            # Add padding to top and bottom
            padding_top = (target_resolution[1] - new_height) // 2
            
            # Create black background
            bg = mp.ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
            
            # Position resized clip on background
            final_clip = mp.CompositeVideoClip([
                bg,
                resized_clip.set_position(("center", padding_top))
            ])
        else:
            # Video is taller than target aspect ratio - fit to height
            new_height = target_resolution[1]
            new_width = int(new_height * current_aspect)
            resized_clip = clip.resize(height=new_height, width=new_width)
            
            # Add padding to left and right
            padding_left = (target_resolution[0] - new_width) // 2
            
            # Create black background
            bg = mp.ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
            
            # Position resized clip on background
            final_clip = mp.CompositeVideoClip([
                bg,
                resized_clip.set_position((padding_left, 0))
            ])
            
        return final_clip.set_duration(clip.duration)
    except Exception as e:
        print(f"❌ Error resizing video: {str(e)}")
        print(traceback.format_exc())
        # Return original clip if resize fails
        return clip

# Add this new function to validate audio
def has_valid_audio(clip):
    """Check if a clip has valid audio"""
    try:
        if clip.audio is None:
            print("Clip has no audio track")
            return False
            
        # Additional validation
        try:
            # Try to access a frame to check if audio is valid
            _ = clip.audio.get_frame(0)
            # Check if the audio has a duration
            if clip.audio.duration <= 0:
                print("Audio track has zero or negative duration")
                return False
            return True
        except (AttributeError, IOError, ValueError) as e:
            print(f"Audio validation error: {str(e)}")
            return False
    except Exception as e:
        print(f"Unexpected audio validation error: {str(e)}")
        return False

# Add this function after has_valid_audio and before extract_audio_track
def check_audio_overlaps(sequence):
    """
    Check for potential audio overlaps in the sequence
    
    Args:
        sequence: List of video segments to assemble
        
    Returns:
        dict: Result containing status and any overlap warnings
    """
    warnings = []
    used_audio_segments = {}
    segment_details = []
    
    # First pass: gather all audio segment information
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        
        # Track which A-Roll audio segments are being used
        if segment_id in used_audio_segments:
            warning_msg = f"Segment {i+1}: Using same A-Roll audio ({segment_id}) that was already used in segment {used_audio_segments[segment_id]['index']+1}"
            warnings.append(warning_msg)
            # Print warning in a visible format
            print(f"⚠️ AUDIO OVERLAP DETECTED: {warning_msg}")
            
            # Add this segment to the details with overlap flag
            segment_details.append({
                "index": i,
                "segment_id": segment_id,
                "type": item["type"],
                "has_overlap": True,
                "original_index": used_audio_segments[segment_id]["index"]
            })
        else:
            used_audio_segments[segment_id] = {
                "index": i,
                "type": item["type"]
            }
            
            # Add to details without overlap flag
            segment_details.append({
                "index": i,
                "segment_id": segment_id,
                "type": item["type"],
                "has_overlap": False
            })
    
    # Generate enhanced diagnostic details
    if warnings:
        print("\n=== Audio Track Sequence Analysis ===")
        print(f"Total segments: {len(sequence)}")
        print(f"Unique audio tracks: {len(used_audio_segments)}")
        print(f"Duplicated audio tracks: {len(warnings)}")
        print("\nAudio track sequence (⚠️ = overlap):")
        
        for segment in segment_details:
            overlap_indicator = "⚠️" if segment["has_overlap"] else "  "
            overlap_info = f" (duplicate of segment {segment['original_index']+1})" if segment["has_overlap"] else ""
            print(f"{overlap_indicator} Segment {segment['index']+1}: {segment['segment_id']}{overlap_info}")
    
    return {
        "has_overlaps": len(warnings) > 0,
        "warnings": warnings,
        "used_segments": used_audio_segments,
        "segment_details": segment_details
    }

# Add this function to extract audio from video file to separate audio file
def extract_audio_track(video_path, output_dir=None):
    """
    Extract audio from a video file to a separate audio file
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save the audio file (uses temp dir if None)
        
    Returns:
        str: Path to extracted audio file or None if extraction failed
    """
    try:
        # Create temp directory if not provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        # Generate output path for audio file
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        audio_path = os.path.join(output_dir, f"{video_name}.m4a")
        
        print(f"Extracting audio from: {video_path}")
        print(f"Video path for extraction: {os.path.abspath(video_path)}")
        print(f"Audio output path: {audio_path}")
        
        # Use ffmpeg to extract audio
        cmd = [
            "ffmpeg", "-y", "-i", os.path.abspath(video_path),
            "-vn", "-acodec", "aac", "-b:a", "192k", "-f", "mp4",
            audio_path
        ]
        
        print(f"Running ffmpeg command: {' '.join(cmd)}")
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            print(f"Successfully extracted audio to: {audio_path}")
            return audio_path
        else:
            print(f"Error extracting audio: {process.stderr}")
            return None
    except Exception as e:
        print(f"Exception extracting audio: {str(e)}")
        return None

# Add this function to detect if a file is an image
def is_image_file(file_path):
    """
    Check if a file is an image (PNG, JPG, JPEG)
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if the file is an image, False otherwise
    """
    if not file_path or not os.path.exists(file_path):
        return False
        
    # Check file extension
    _, ext = os.path.splitext(file_path.lower())
    return ext in ['.png', '.jpg', '.jpeg']

# Add this function to convert an image to a video clip
@error_handler
def image_to_video(image_path, duration=5.0, target_resolution=(1080, 1920)):
    """
    Convert an image to a video clip
    
    Args:
        image_path: Path to the image file
        duration: Duration of the video clip in seconds
        target_resolution: Target resolution (width, height)
        
    Returns:
        MoviePy clip or None if conversion fails
    """
    if not MOVIEPY_AVAILABLE:
        print("❌ MoviePy is not available, cannot convert image to video")
        return None
        
    if not is_image_file(image_path):
        print(f"❌ File is not a recognized image format: {image_path}")
        return None
        
    try:
        # Load image as clip
        print(f"Converting image to video: {image_path} (duration: {duration}s)")
        image_clip = mp.ImageClip(image_path, duration=duration)
        
        # Resize to target resolution
        image_clip = resize_video(image_clip, target_resolution)
        
        return image_clip
    except Exception as e:
        print(f"❌ Error converting image to video: {str(e)}")
        print(traceback.format_exc())
        return None

@error_handler
def create_partial_broll_overlay(aroll_clip, broll_clip, aroll_percentage=0.6):
    """
    Creates a video clip with A-Roll at the beginning and B-Roll overlay for the remainder
    
    Args:
        aroll_clip: The A-Roll clip
        broll_clip: The B-Roll clip 
        aroll_percentage: Percentage of time to show only A-Roll (0.6 = 60%)
        
    Returns:
        MoviePy clip with A-Roll followed by B-Roll with A-Roll audio
    """
    if not MOVIEPY_AVAILABLE:
        print("❌ MoviePy is not available, cannot create partial B-Roll overlay")
        return None
        
    try:
        # Get the full duration and calculate split time
        total_duration = aroll_clip.duration
        aroll_only_duration = total_duration * aroll_percentage
        broll_duration = total_duration - aroll_only_duration
        
        print(f"Creating partial B-Roll overlay with {aroll_percentage*100}% A-Roll")
        print(f"Total duration: {total_duration}s, A-Roll only: {aroll_only_duration}s, B-Roll: {broll_duration}s")
        
        # Create A-Roll only segment (first part)
        aroll_only_segment = aroll_clip.subclip(0, aroll_only_duration)
        
        # Create B-Roll segment with A-Roll audio (second part)
        aroll_audio_segment = aroll_clip.subclip(aroll_only_duration, total_duration).audio
        
        # If B-Roll is shorter than the required duration, loop it
        if broll_clip.duration < broll_duration:
            repeat_count = int(np.ceil(broll_duration / broll_clip.duration))
            broll_clip = mp.concatenate_videoclips([broll_clip] * repeat_count)
        
        # Cut B-Roll to exact duration needed
        broll_segment = broll_clip.subclip(0, broll_duration)
        
        # Apply A-Roll audio to B-Roll segment
        broll_segment = broll_segment.set_audio(aroll_audio_segment)
        
        # Concatenate A-Roll and B-Roll segments
        final_clip = mp.concatenate_videoclips([aroll_only_segment, broll_segment])
        
        return final_clip
    except Exception as e:
        print(f"❌ Error creating partial B-Roll overlay: {str(e)}")
        print(traceback.format_exc())
        return None

@error_handler
def assemble_video(sequence, target_resolution=(1080, 1920), output_dir=None, progress_callback=None, is_transcription=False, segment_timestamps=None, aroll_percentage=0.6):
    """
    Assemble a final video from A-Roll and B-Roll segments
    
    Args:
        sequence: List of video segments to assemble or full A-Roll path and B-Roll mapping
        target_resolution: Target resolution (width, height)
        output_dir: Directory to save output video
        progress_callback: Callback function to update progress
        is_transcription: Whether the A-Roll is from transcription
        segment_timestamps: Dictionary of segment timestamps for transcription-based A-Roll
        aroll_percentage: Percentage of time to show only A-Roll (0.6 = 60%)
        
    Returns:
        dict: Result dictionary with status, message, and output_path if successful
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy is not available. Please install required packages."}
    
    if progress_callback is None:
        def progress_print(progress, message):
            print(f"Progress: {progress}% - {message}")
        progress_callback = progress_print
    
    # Check if sequence is a dictionary with aroll_path and broll_mapping (new format)
    if isinstance(sequence, dict) and "aroll_path" in sequence:
        return assemble_video_timestamp_based(
            sequence["aroll_path"],
            sequence.get("broll_mapping", {}),
            target_resolution=target_resolution,
            output_dir=output_dir,
            progress_callback=progress_callback,
            aroll_percentage=aroll_percentage
        )
    
    # If sequence is a list, use the older segment-based assembly logic
    if not sequence or not isinstance(sequence, list):
        return {"status": "error", "message": "Invalid sequence format"}
    
    # Check for audio overlaps
    overlaps = check_audio_overlaps(sequence)
    if overlaps.get("has_overlaps", False):
        print("⚠️ Warning: Potential audio overlaps detected:")
        for warning in overlaps.get("warnings", []):
            print(f"  - {warning}")
        
        # Print a more informative message with suggestions
        print("\n⚠️ IMPORTANT: Audio overlap issues detected in your sequence!")
        print("This can cause audio from the same segment to be heard multiple times in your video.")
        print("To fix this:")
        print("1. Try using a different sequence pattern (B-Roll Full, Standard, etc.)")
        print("2. Use the Custom arrangement to manually control which audio segments are used")
        print("3. Ensure each A-Roll audio segment is used exactly once\n")
    
    # Check all input files
    missing_files = []
    
    for item in sequence:
        if item["type"] == "aroll_full":
            aroll_path = item.get("aroll_path")
            if not aroll_path or not os.path.exists(aroll_path):
                missing_files.append(f"A-Roll file not found: {aroll_path}")
        elif item["type"] == "broll_with_aroll_audio":
            broll_path = item.get("broll_path")
            aroll_path = item.get("aroll_path")
            
            if not broll_path or not os.path.exists(broll_path):
                missing_files.append(f"B-Roll file not found: {broll_path}")
            
            if not aroll_path or not os.path.exists(aroll_path):
                missing_files.append(f"A-Roll file not found: {aroll_path}")
    
    if missing_files:
        return {
            "status": "error",
            "message": "Missing files required for assembly",
            "missing_files": missing_files
        }
    
    # Generate a timestamp for the output file - defined here so it's available for all code paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Special handling for transcription-based A-Roll
        if is_transcription and segment_timestamps:
            print("Using transcription-based A-Roll assembly mode")
            progress_callback(5, "Preparing for transcription-based assembly")
            
            # Load the full A-Roll video once
            full_aroll_path = None
            for item in sequence:
                if "aroll_path" in item:
                    full_aroll_path = item["aroll_path"]
                    break
                    
            if not full_aroll_path or not os.path.exists(full_aroll_path):
                return {"status": "error", "message": "Full A-Roll video not found"}
            
            progress_callback(10, "Loading full A-Roll video")
            try:
                full_aroll_clip = mp.VideoFileClip(full_aroll_path)
            except Exception as e:
                return {"status": "error", "message": f"Failed to load full A-Roll video: {str(e)}"}
            
            # Process each segment in the sequence
            clips = []
            progress_callback(15, "Processing segments")
            
            for i, item in enumerate(sequence):
                segment_progress = 15 + (i / len(sequence) * 50)
                progress_callback(segment_progress, f"Processing segment {i+1}/{len(sequence)}")
                
                segment_id = item.get("segment_id")
                timestamp_data = item.get("timestamp_data", {})
                
                if not timestamp_data and segment_id in segment_timestamps:
                    timestamp_data = segment_timestamps[segment_id]
                
                if not timestamp_data:
                    print(f"Warning: No timestamp data for segment {segment_id}")
                    continue
                
                start_time = timestamp_data.get("start_time", 0)
                end_time = timestamp_data.get("end_time", 0)
                
                if start_time >= end_time:
                    print(f"Warning: Invalid timestamps for segment {segment_id}: start={start_time}, end={end_time}")
                    continue
                
                try:
                    if item["type"] == "aroll_full":
                        # Extract the segment from the full A-Roll video
                        print(f"Extracting A-Roll segment {segment_id} from {start_time}s to {end_time}s")
                        segment_clip = full_aroll_clip.subclip(start_time, end_time)
                        segment_clip = resize_video(segment_clip, target_resolution)
                        clips.append(segment_clip)
                        
                    elif item["type"] == "broll_with_aroll_audio":
                        broll_path = item.get("broll_path")
                        if not broll_path or not os.path.exists(broll_path):
                            print(f"Warning: B-Roll file not found for segment {segment_id}")
                            continue
                        
                        # Extract the A-Roll segment clip
                        print(f"Extracting A-Roll segment for partial overlay from {start_time}s to {end_time}s")
                        aroll_segment = full_aroll_clip.subclip(start_time, end_time)
                        segment_duration = end_time - start_time
                        
                        # Load B-Roll video or image
                        if is_image_file(broll_path):
                            print(f"Converting image to video: {broll_path} with duration {segment_duration}s")
                            broll_clip = image_to_video(broll_path, duration=segment_duration, target_resolution=target_resolution)
                        else:
                            print(f"Loading B-Roll video: {broll_path}")
                            broll_clip = mp.VideoFileClip(broll_path)
                            
                            # Adjust B-Roll duration to match the A-Roll segment
                            if broll_clip.duration < segment_duration:
                                print(f"B-Roll duration ({broll_clip.duration}s) is shorter than A-Roll segment ({segment_duration}s)")
                                # Loop B-Roll clip to match A-Roll duration
                                repeat_count = int(np.ceil(segment_duration / broll_clip.duration))
                                print(f"Looping B-Roll clip {repeat_count} times")
                                broll_clip = mp.concatenate_videoclips([broll_clip] * repeat_count).subclip(0, segment_duration)
                            elif broll_clip.duration > segment_duration:
                                print(f"Trimming B-Roll clip from {broll_clip.duration}s to {segment_duration}s")
                                broll_clip = broll_clip.subclip(0, segment_duration)
                        
                        # Resize B-Roll
                        broll_clip = resize_video(broll_clip, target_resolution)
                        
                        # Create partial overlay with 60/40 split
                        overlay_clip = create_partial_broll_overlay(aroll_segment, broll_clip, aroll_percentage)
                        
                        if overlay_clip:
                            clips.append(overlay_clip)
                        else:
                            print(f"Warning: Failed to create partial overlay for segment {segment_id}")
                            # Fall back to A-Roll only if overlay fails
                            clips.append(aroll_segment)
                except Exception as e:
                    print(f"Error processing segment {segment_id}: {str(e)}")
                    print(traceback.format_exc())
            
            # Create final video by concatenating all clips
            if not clips:
                return {"status": "error", "message": "No valid clips to assemble"}
            
            progress_callback(70, "Concatenating clips")
            
            try:
                final_clip = mp.concatenate_videoclips(clips)
            except Exception as e:
                return {"status": "error", "message": f"Failed to concatenate clips: {str(e)}"}
            
            # Define output path
            if output_dir:
                output_dir = Path(output_dir)
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_dir = Path.cwd()
            
            output_path = output_dir / f"assembled_video_{timestamp}.mp4"
            
            # Write final video
            progress_callback(80, f"Writing final video to {output_path}")
            
            try:
                final_clip.write_videofile(
                    str(output_path),
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                    remove_temp=True,
                    threads=4,
                    preset="medium",
                    fps=30
                )
            except Exception as e:
                return {"status": "error", "message": f"Failed to write final video: {str(e)}"}
            
            # Clean up clips
            progress_callback(95, "Cleaning up")
            
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            
            try:
                full_aroll_clip.close()
            except:
                pass
            
            progress_callback(100, "Video assembly complete")
            
            return {
                "status": "success",
                "message": "Video assembly complete",
                "output_path": str(output_path)
            }
        
        # Standard segment-based assembly logic (older approach)
        else:
            # Process each segment in the sequence
            clips = []
            progress_callback(10, "Processing segments")
            
            for i, item in enumerate(sequence):
                segment_progress = 10 + (i / len(sequence) * 60)
                progress_callback(segment_progress, f"Processing segment {i+1}/{len(sequence)}")
                
                try:
                    if item["type"] == "aroll_full":
                        aroll_path = item["aroll_path"]
                        aroll_clip = mp.VideoFileClip(aroll_path)
                        
                        # Resize to target resolution
                        aroll_clip = resize_video(aroll_clip, target_resolution)
                        
                        clips.append(aroll_clip)
                    
                    elif item["type"] == "broll_with_aroll_audio":
                        broll_path = item["broll_path"]
                        aroll_path = item["aroll_path"]
                        
                        # Load A-Roll for audio
                        aroll_clip = mp.VideoFileClip(aroll_path)
                        
                        # Load B-Roll based on file type
                        if is_image_file(broll_path):
                            # Convert image to video with A-Roll duration
                            broll_clip = image_to_video(broll_path, duration=aroll_clip.duration, target_resolution=target_resolution)
                        else:
                            # Load B-Roll video
                            broll_clip = mp.VideoFileClip(broll_path)
                            
                            # Loop B-Roll if it's shorter than A-Roll
                            if broll_clip.duration < aroll_clip.duration:
                                repeat_count = int(np.ceil(aroll_clip.duration / broll_clip.duration))
                                broll_clip = mp.concatenate_videoclips([broll_clip] * repeat_count).subclip(0, aroll_clip.duration)
                            elif broll_clip.duration > aroll_clip.duration:
                                broll_clip = broll_clip.subclip(0, aroll_clip.duration)
                            
                            # Resize to target resolution
                            broll_clip = resize_video(broll_clip, target_resolution)
                        
                        # Create partial overlay with 60/40 split
                        overlay_clip = create_partial_broll_overlay(aroll_clip, broll_clip, aroll_percentage)
                        
                        if overlay_clip:
                            clips.append(overlay_clip)
                        else:
                            # Fall back to B-Roll with A-Roll audio if overlay fails
                            broll_clip = broll_clip.set_audio(aroll_clip.audio)
                            clips.append(broll_clip)
                            
                except Exception as e:
                    print(f"Error processing segment {i+1}: {str(e)}")
                    print(traceback.format_exc())
            
            # Create final video
            if not clips:
                return {"status": "error", "message": "No valid clips to assemble"}
            
            progress_callback(70, "Concatenating clips")
            
            try:
                final_clip = mp.concatenate_videoclips(clips)
            except Exception as e:
                return {"status": "error", "message": f"Failed to concatenate clips: {str(e)}"}
            
            # Define output path
            if output_dir:
                output_dir = Path(output_dir)
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_dir = Path.cwd()
            
            output_path = output_dir / f"assembled_video_{timestamp}.mp4"
            
            # Write final video
            progress_callback(80, "Writing final video")
            
            try:
                final_clip.write_videofile(
                    str(output_path),
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                    remove_temp=True,
                    threads=4,
                    preset="medium",
                    fps=30
                )
            except Exception as e:
                return {"status": "error", "message": f"Failed to write final video: {str(e)}"}
            
            # Clean up clips
            progress_callback(95, "Cleaning up")
            
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            
            progress_callback(100, "Video assembly complete")
            
            return {
                "status": "success",
                "message": "Video assembly complete",
                "output_path": str(output_path)
            }
    
    except Exception as e:
        print(f"Error in video assembly: {str(e)}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Error in video assembly: {str(e)}"}

@error_handler
def assemble_video_timestamp_based(aroll_path, broll_mapping, target_resolution=(1080, 1920), output_dir=None, progress_callback=None, aroll_percentage=0.6):
    """
    Assemble a video using timestamp-based B-Roll mapping to a single A-Roll file
    
    Args:
        aroll_path: Path to the full A-Roll video
        broll_mapping: Dictionary mapping B-Roll IDs to their timestamp info
        target_resolution: Target resolution (width, height)
        output_dir: Directory to save the output video
        progress_callback: Callback function to update progress
        aroll_percentage: Percentage of time to show only A-Roll (0.6 = 60%)
        
    Returns:
        dict: Result dictionary with status, message, and output_path if successful
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy is not available. Please install required packages."}
    
    if progress_callback is None:
        def progress_print(progress, message):
            print(f"Progress: {progress}% - {message}")
        progress_callback = progress_print
    
    # Check A-Roll path
    if not aroll_path or not os.path.exists(aroll_path):
        return {"status": "error", "message": f"A-Roll file not found: {aroll_path}"}
    
    # Generate a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Load the full A-Roll video
        progress_callback(5, "Loading A-Roll video")
        aroll_clip = mp.VideoFileClip(aroll_path)
        aroll_duration = aroll_clip.duration
        
        # Resize A-Roll to target resolution
        aroll_clip = resize_video(aroll_clip, target_resolution)
        
        # Sort B-Roll mapping by timestamp
        progress_callback(10, "Processing B-Roll mapping")
        sorted_broll = []
        
        for broll_id, broll_info in broll_mapping.items():
            timestamp = broll_info.get("timestamp", 0)
            sorted_broll.append((broll_id, broll_info, timestamp))
        
        sorted_broll.sort(key=lambda x: x[2])  # Sort by timestamp
        
        # Process each segment
        clips = []
        current_time = 0
        
        # If there are no B-Roll segments, just use the full A-Roll
        if not sorted_broll:
            progress_callback(20, "No B-Roll segments found, using full A-Roll")
            clips.append(aroll_clip)
        else:
            progress_callback(20, "Processing video segments")
            
            # Process each B-Roll segment and the A-Roll before it
            for i, (broll_id, broll_info, timestamp) in enumerate(sorted_broll):
                segment_progress = 20 + (i / len(sorted_broll) * 60)
                progress_callback(segment_progress, f"Processing segment {i+1}/{len(sorted_broll)}")
                
                # If this is the first B-Roll or there's a gap, add A-Roll up to this point
                if timestamp > current_time:
                    # Add A-Roll segment from current_time to timestamp
                    print(f"Adding A-Roll segment from {current_time}s to {timestamp}s")
                    aroll_segment = aroll_clip.subclip(current_time, timestamp)
                    clips.append(aroll_segment)
                
                # Get B-Roll path or determine if we need to generate it
                visuals = broll_info.get("visuals", [])
                duration = broll_info.get("duration", 0)
                
                # Skip if no duration or visuals
                if duration <= 0 or not visuals:
                    print(f"Skipping B-Roll {broll_id} - no duration or visuals")
                    continue
                
                # Extract A-Roll segment for this B-Roll period
                end_time = min(timestamp + duration, aroll_duration)
                aroll_segment = aroll_clip.subclip(timestamp, end_time)
                
                # Process B-Roll visuals
                visual_clips = []
                
                for j, visual in enumerate(visuals):
                    visual_duration = visual.get("duration", 0)
                    visual_content = visual.get("content", "")
                    
                    # Skip if no duration
                    if visual_duration <= 0:
                        continue
                    
                    # Get B-Roll path for this visual
                    visual_path = visual.get("path")
                    
                    if visual_path and os.path.exists(visual_path):
                        # Load B-Roll based on file type
                        if is_image_file(visual_path):
                            # Convert image to video
                            broll_visual = image_to_video(visual_path, duration=visual_duration, target_resolution=target_resolution)
                        else:
                            # Load video and adjust duration
                            broll_visual = mp.VideoFileClip(visual_path)
                            
                            # Adjust duration if needed
                            if broll_visual.duration < visual_duration:
                                repeat_count = int(np.ceil(visual_duration / broll_visual.duration))
                                broll_visual = mp.concatenate_videoclips([broll_visual] * repeat_count).subclip(0, visual_duration)
                            elif broll_visual.duration > visual_duration:
                                broll_visual = broll_visual.subclip(0, visual_duration)
                            
                            # Resize to target resolution
                            broll_visual = resize_video(broll_visual, target_resolution)
                        
                        visual_clips.append(broll_visual)
                
                # If we have visual clips, concatenate them and create overlay
                if visual_clips:
                    # Concatenate B-Roll visuals if multiple
                    if len(visual_clips) > 1:
                        broll_clip = mp.concatenate_videoclips(visual_clips)
                    else:
                        broll_clip = visual_clips[0]
                    
                    # Create partial overlay with 60/40 split
                    overlay_clip = create_partial_broll_overlay(aroll_segment, broll_clip, aroll_percentage)
                    
                    if overlay_clip:
                        clips.append(overlay_clip)
                    else:
                        # Fall back to B-Roll with A-Roll audio if overlay fails
                        broll_clip = broll_clip.set_audio(aroll_segment.audio)
                        clips.append(broll_clip)
                else:
                    # No valid B-Roll visuals, just use A-Roll
                    clips.append(aroll_segment)
                
                # Update current time
                current_time = end_time
            
            # If there's remaining A-Roll after the last B-Roll, add it
            if current_time < aroll_duration:
                print(f"Adding final A-Roll segment from {current_time}s to {aroll_duration}s")
                final_aroll = aroll_clip.subclip(current_time, aroll_duration)
                clips.append(final_aroll)
        
        # Create final video
        if not clips:
            return {"status": "error", "message": "No valid clips to assemble"}
        
        progress_callback(80, "Concatenating clips")
        
        try:
            final_clip = mp.concatenate_videoclips(clips)
        except Exception as e:
            return {"status": "error", "message": f"Failed to concatenate clips: {str(e)}"}
        
        # Define output path
        if output_dir:
            output_dir = Path(output_dir)
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = Path.cwd()
        
        output_path = output_dir / f"assembled_video_{timestamp}.mp4"
        
        # Write final video
        progress_callback(90, "Writing final video")
        
        try:
            final_clip.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                remove_temp=True,
                threads=4,
                preset="medium",
                fps=30
            )
        except Exception as e:
            return {"status": "error", "message": f"Failed to write final video: {str(e)}"}
        
        # Clean up
        progress_callback(95, "Cleaning up")
        
        for clip in clips:
            try:
                clip.close()
            except:
                pass
        
        try:
            aroll_clip.close()
        except:
            pass
        
        progress_callback(100, "Video assembly complete")
        
        return {
            "status": "success",
            "message": "Video assembly complete",
            "output_path": str(output_path)
        }
        
    except Exception as e:
        print(f"Error in timestamp-based video assembly: {str(e)}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Error in timestamp-based video assembly: {str(e)}"}

if __name__ == "__main__":
    # Simple test if this script is run directly
    if not MOVIEPY_AVAILABLE:
        print("MoviePy is not available. Please run check_dependencies.py first.")
        sys.exit(1)
        
    # Check for arguments
    if len(sys.argv) > 1:
        # Check if first argument is a JSON file with sequence info
        sequence_file = sys.argv[1]
        if os.path.exists(sequence_file):
            try:
                with open(sequence_file, 'r') as f:
                    sequence = json.load(f)
                    
                def progress_print(progress, message):
                    print(f"Progress: {progress}% - {message}")
                    
                result = assemble_video(
                    sequence, 
                    target_resolution=(1080, 1920), 
                    progress_callback=progress_print
                )
                
                if result["status"] == "success":
                    print(f"Video assembly completed successfully!")
                    print(f"Output: {result['output_path']}")
                else:
                    print(f"Error during video assembly: {result['message']}")
            except Exception as e:
                print(f"Error processing sequence file: {str(e)}")
        else:
            print(f"Sequence file not found: {sequence_file}")
    else:
        print("Usage: python video_assembly_helper.py [sequence_file.json]")
        print("To use this script directly, provide a JSON file with sequence information.") 