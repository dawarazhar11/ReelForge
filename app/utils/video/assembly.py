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
    """
    Check if a clip has valid audio
    
    Args:
        clip: MoviePy video clip
        
    Returns:
        bool: True if the clip has valid audio, False otherwise
    """
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
                
            # Check if audio has valid fps
            if clip.audio.fps is None or clip.audio.fps <= 0:
                print("Audio track has invalid fps")
                return False
                
            # Check if audio has valid nchannels
            if not hasattr(clip.audio, 'nchannels') or clip.audio.nchannels <= 0:
                print("Audio track has invalid number of channels")
                return False
                
            # All checks passed
            print(f"Audio validation successful: duration={clip.audio.duration:.2f}s, fps={clip.audio.fps}, channels={clip.audio.nchannels}")
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

@error_handler
def render_video(input_path, output_path=None, target_resolution=(1080, 1920), fps=30, bitrate="8000k", progress_callback=None):
    """
    Render a video file with specified parameters
    
    Args:
        input_path: Path to the input video file
        output_path: Path to save the output video file (optional)
        target_resolution: Target resolution (width, height)
        fps: Frames per second
        bitrate: Video bitrate
        progress_callback: Function to call with progress updates
        
    Returns:
        dict: Result containing status and output path
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy not available"}
    
    # Check input file
    check_result = check_file(input_path, "video")
    if check_result["status"] == "error":
        return check_result
    
    # Generate output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rendered_{timestamp}.mp4"
        output_path = os.path.join(os.path.dirname(input_path), filename)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Define progress callback function
        def progress_print(progress, message=None):
            if progress_callback:
                progress_callback(progress, message)
            else:
                print(f"Rendering progress: {progress:.1f}%")
        
        # Load the video clip
        clip = mp.VideoFileClip(input_path)
        
        # Resize to target resolution
        if clip.size != target_resolution:
            clip = resize_video(clip, target_resolution)
        
        # Write the output file
        clip.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            bitrate=bitrate,
            threads=4,
            preset="medium",
            ffmpeg_params=["-crf", "22"],
            progress_bar=False,
            logger=None,
            verbose=False,
            callback=progress_print
        )
        
        # Close the clip to release resources
        clip.close()
        
        # Return success result
        return {
            "status": "success",
            "input_path": input_path,
            "output_path": output_path,
            "resolution": target_resolution,
            "fps": fps,
            "bitrate": bitrate
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error rendering video: {str(e)}",
            "traceback": traceback.format_exc()
        }

@error_handler
def extract_audio_track(video_path, output_dir=None, start_time=None, end_time=None):
    """
    Extract audio from a video file
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save the extracted audio (optional)
        start_time: Start time in seconds for the segment (optional)
        end_time: End time in seconds for the segment (optional)
        
    Returns:
        dict: Result containing status and output path
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy not available"}
    
    # Check input file
    check_result = check_file(video_path, "video")
    if check_result["status"] == "error":
        return check_result
    
    # Generate output path if not provided
    if not output_dir:
        output_dir = os.path.dirname(video_path)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    basename = os.path.basename(video_path)
    filename, _ = os.path.splitext(basename)
    
    # Add segment info to filename if using timestamps
    if start_time is not None and end_time is not None and end_time > start_time:
        segment_info = f"_segment_{start_time:.2f}_{end_time:.2f}"
        output_path = os.path.join(output_dir, f"{filename}{segment_info}_audio.wav")
    else:
        output_path = os.path.join(output_dir, f"{filename}_audio.wav")
    
    try:
        # Load the video clip
        video_clip = mp.VideoFileClip(video_path)
        
        # Check if video has audio
        if video_clip.audio is None:
            video_clip.close()
            return {"status": "error", "message": "Video has no audio track"}
        
        # Extract audio
        audio_clip = video_clip.audio
        
        # If start and end times are provided, extract just that segment
        if start_time is not None and end_time is not None and end_time > start_time:
            print(f"Extracting audio segment from {start_time:.2f}s to {end_time:.2f}s")
            audio_clip = audio_clip.subclip(start_time, end_time)
        
        # Write audio file
        audio_clip.write_audiofile(
            output_path,
            codec="pcm_s16le",  # WAV format
            ffmpeg_params=["-ac", "1", "-ar", "44100"],  # Mono, 44.1kHz
            logger=None,
            verbose=False
        )
        
        # Close clips to release resources
        audio_clip.close()
        video_clip.close()
        
        # Return success result
        return {
            "status": "success",
            "input_path": video_path,
            "output_path": output_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time if start_time is not None and end_time is not None else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error extracting audio: {str(e)}",
            "traceback": traceback.format_exc()
        }

@error_handler
def download_video(url, output_path=None, timeout=60):
    """
    Download a video from a URL
    
    Args:
        url: URL of the video to download
        output_path: Path to save the downloaded video (optional)
        timeout: Timeout in seconds for the download request
        
    Returns:
        dict: Result containing status and output path
    """
    try:
        # Check if requests module is available
        import requests
    except ImportError:
        return {"status": "error", "message": "Requests module not available. Please install it with: pip install requests"}
    
    # Generate output path if not provided
    if not output_path:
        # Create a temporary directory for downloads
        download_dir = os.path.join(tempfile.gettempdir(), "video_downloads")
        os.makedirs(download_dir, exist_ok=True)
        
        # Generate a filename based on the URL
        from hashlib import md5
        url_hash = md5(url.encode()).hexdigest()[:10]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(download_dir, f"download_{url_hash}_{timestamp}.mp4")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        print(f"Downloading video from {url} to {output_path}")
        
        # Download the video
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Get content length if available
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress tracking
        downloaded_size = 0
        chunk_size = 8192
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Print progress
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"Download progress: {progress:.1f}%", end="\r")
        
        print("\nDownload complete!")
        
        # Verify the downloaded file
        check_result = check_file(output_path, "video")
        if check_result["status"] == "error":
            return check_result
        
        # Return success result
        return {
            "status": "success",
            "url": url,
            "output_path": output_path,
            "size": os.path.getsize(output_path)
        }
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Error downloading video: {str(e)}",
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error processing download: {str(e)}",
            "traceback": traceback.format_exc(),
            "url": url
        }

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
        # Load image as clip with exact specified duration
        print(f"Converting image to video with exact duration: {duration}s - {image_path}")
        clip = mp.ImageClip(image_path, duration=duration)
        
        # Resize to target resolution
        if target_resolution:
            clip = resize_video(clip, target_resolution)
            
        # Ensure clip has the correct duration
        if clip.duration != duration:
            clip = clip.set_duration(duration)
            
        return clip
    except Exception as e:
        print(f"❌ Error converting image to video: {str(e)}")
        print(traceback.format_exc())
        return None

@error_handler
def assemble_video(sequence, target_resolution=(1080, 1920), output_dir=None, progress_callback=None):
    """
    Assemble a final video from A-Roll and B-Roll segments
    
    Args:
        sequence: List of video segments to assemble
        target_resolution: Target resolution (width, height)
        output_dir: Directory to save output video
        progress_callback: Callback function to update progress
        
    Returns:
        dict: Result dictionary with status, message, and output_path if successful
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy is not available. Please install required packages."}
    
    if progress_callback is None:
        def progress_print(progress, message):
            print(f"Progress: {progress}% - {message}")
        progress_callback = progress_print
    
    # Validate sequence
    if not sequence or not isinstance(sequence, list):
        return {"status": "error", "message": "Invalid sequence format"}
    
    # Check for audio overlaps
    overlaps = check_audio_overlaps(sequence)
    if overlaps["has_overlaps"]:
        print("⚠️ Warning: Potential audio overlaps detected:")
        for warning in overlaps["warnings"]:
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
        # Extract audio from all A-Roll segments first
        audio_temp_dir = tempfile.mkdtemp()
        extracted_audio_paths = {}
        audio_durations = {}
        
        progress_callback(10, "Extracting audio from A-Roll segments")
        
        # Process all A-Roll segments to extract audio first
        for i, item in enumerate(sequence):
            segment_id = item.get("segment_id", f"segment_{i}")
            if "aroll_path" in item:
                # Get start and end times if available
                start_time = item.get("start_time", None)
                end_time = item.get("end_time", None)
                
                # Extract full audio first, then subclip it
                try:
                    # First extract the full audio file
                    audio_result = extract_audio_track(
                        item["aroll_path"], 
                        audio_temp_dir
                    )
                    
                    if audio_result and audio_result["status"] == "success":
                        full_audio_path = audio_result["output_path"]
                        
                        # Load the full audio
                        full_audio_clip = mp.AudioFileClip(full_audio_path)
                        
                        # Now create subclip with proper timestamps
                        if start_time is not None and end_time is not None and end_time > start_time:
                            # Ensure timestamps are within the audio duration
                            if start_time < full_audio_clip.duration and end_time <= full_audio_clip.duration:
                                print(f"Extracting audio segment from {start_time:.2f}s to {end_time:.2f}s")
                                segment_audio = full_audio_clip.subclip(start_time, end_time)
                                
                                # Generate a filename for this segment
                                segment_filename = f"segment_{segment_id}_audio.wav"
                                segment_path = os.path.join(audio_temp_dir, segment_filename)
                                
                                # Write the subclip to file
                                segment_audio.write_audiofile(
                                    segment_path,
                                    codec="pcm_s16le",  # WAV format
                                    ffmpeg_params=["-ac", "1", "-ar", "44100"],  # Mono, 44.1kHz
                                    logger=None,
                                    verbose=False
                                )
                                
                                # Store the path to the segment audio file
                                extracted_audio_paths[segment_id] = segment_path
                                
                                # Get audio duration and store it
                                audio_durations[segment_id] = segment_audio.duration
                                print(f"Audio segment {segment_id} duration: {audio_durations[segment_id]:.2f}s")
                                
                                # Close the audio clips to free resources
                                segment_audio.close()
                            else:
                                print(f"Warning: Timestamps ({start_time:.2f}s-{end_time:.2f}s) exceed audio duration ({full_audio_clip.duration:.2f}s)")
                                # Create silent audio as fallback
                                segment_duration = end_time - start_time
                                print(f"Creating silent audio with duration: {segment_duration:.2f}s")
                                
                                # Generate a filename for this segment
                                segment_filename = f"segment_{segment_id}_silent_audio.wav"
                                segment_path = os.path.join(audio_temp_dir, segment_filename)
                                
                                # Create a silent audio clip and write it to file
                                silent_audio = mp.AudioClip(lambda t: 0, duration=segment_duration)
                                silent_audio.write_audiofile(
                                    segment_path,
                                    codec="pcm_s16le",
                                    ffmpeg_params=["-ac", "1", "-ar", "44100"],
                                    logger=None,
                                    verbose=False
                                )
                                
                                # Store the path to the segment audio file
                                extracted_audio_paths[segment_id] = segment_path
                                
                                # Store the duration
                                audio_durations[segment_id] = segment_duration
                                print(f"Silent audio segment {segment_id} duration: {audio_durations[segment_id]:.2f}s")
                                
                                # Close the audio clip to free resources
                                silent_audio.close()
                        else:
                            # If no valid timestamps, use the full audio
                            extracted_audio_paths[segment_id] = full_audio_path
                            audio_durations[segment_id] = full_audio_clip.duration
                            print(f"Using full audio for segment {segment_id}, duration: {full_audio_clip.duration:.2f}s")
                        
                        # Close the full audio clip
                        full_audio_clip.close()
                    else:
                        print(f"Failed to extract audio for segment {segment_id}: {audio_result.get('message', 'Unknown error')}")
                except Exception as e:
                    print(f"Error processing audio for segment {segment_id}: {str(e)}")
        
        # Load and assemble video clips
        progress_callback(20, "Loading video segments")
        clips = []
        
        # Track current audio position to ensure sequential placement
        current_audio_position = 0
        used_audio_segments = set()
        
        for i, item in enumerate(sequence):
            progress_callback(20 + (i / len(sequence) * 40), f"Processing segment {i+1}/{len(sequence)}")
            segment_id = item.get("segment_id", f"segment_{i}")
            
            # Skip if this A-Roll audio was already used (should be prevented by sequence creation)
            if segment_id in used_audio_segments:
                print(f"⚠️ WARNING: Segment {segment_id} audio was already used - skipping duplicate")
                continue
            
            if item["type"] == "aroll_full":
                # Load A-Roll video
                aroll_path = item["aroll_path"]
                
                try:
                    print(f"Loading A-Roll video: {aroll_path}")
                    full_clip = mp.VideoFileClip(aroll_path)
                    
                    # Extract just the segment using start_time and end_time
                    start_time = item.get("start_time", 0)
                    end_time = item.get("end_time", 0)
                    
                    # Ensure we have valid start and end times
                    if end_time > start_time:
                        print(f"Extracting segment from {start_time:.2f}s to {end_time:.2f}s (duration: {end_time-start_time:.2f}s)")
                        # Ensure timestamps are within the clip duration
                        if start_time < full_clip.duration and end_time <= full_clip.duration:
                            clip = full_clip.subclip(start_time, end_time)
                            print(f"Successfully extracted video segment with duration: {clip.duration:.2f}s")
                        else:
                            print(f"Warning: Timestamps ({start_time:.2f}s-{end_time:.2f}s) exceed video duration ({full_clip.duration:.2f}s)")
                            # Use a segment from the beginning for the specified duration if possible
                            segment_duration = end_time - start_time
                            if segment_duration > 0 and segment_duration <= full_clip.duration:
                                clip = full_clip.subclip(0, segment_duration)
                                print(f"Using first {segment_duration:.2f}s of clip as fallback")
                            else:
                                # No valid timestamps, use the full clip
                                clip = full_clip
                                print(f"Using full clip with duration: {clip.duration:.2f}s")
                    else:
                        # If no valid timestamps, use the full clip
                        print(f"No valid timestamps for segment {segment_id}, using full clip")
                        clip = full_clip
                    
                    # Check if clip has valid audio, if not, try to use extracted audio
                    if not has_valid_audio(clip) and segment_id in extracted_audio_paths:
                        audio_path = extracted_audio_paths[segment_id]
                        try:
                            print(f"Loading extracted A-Roll audio: {audio_path}")
                            # Ensure audio_path is a string, not a dictionary
                            if isinstance(audio_path, dict) and 'output_path' in audio_path:
                                audio_path = audio_path['output_path']
                                print(f"Corrected audio path to: {audio_path}")
                            
                            # Verify the audio file exists
                            if not os.path.exists(audio_path):
                                raise FileNotFoundError(f"Audio file not found: {audio_path}")
                                
                            # Try to load the audio with error handling
                            try:
                                audio_clip = mp.AudioFileClip(audio_path)
                                print(f"Successfully loaded audio with duration: {audio_clip.duration:.2f}s")
                            except Exception as audio_error:
                                print(f"Error loading audio file: {str(audio_error)}")
                                print("Creating silent audio as fallback")
                                # Create silent audio with the same duration as the clip
                                audio_clip = mp.AudioClip(lambda t: 0, duration=clip.duration)
                            
                            # First, ensure the clip has no audio of its own
                            clip = clip.without_audio()
                            
                            # Ensure the clip duration exactly matches the audio duration
                            exact_duration = min(clip.duration, audio_clip.duration)
                            clip = clip.subclip(0, exact_duration)
                            audio_clip = audio_clip.subclip(0, exact_duration)
                            
                            # Apply audio to clip
                            try:
                                clip = clip.set_audio(audio_clip)
                                print(f"Successfully applied extracted audio to A-Roll clip, duration: {clip.duration:.2f}s")
                                
                                # Mark this segment as used
                                used_audio_segments.add(segment_id)
                                
                                # Update current audio position
                                current_audio_position += clip.duration
                            except Exception as e:
                                print(f"Error applying extracted audio: {str(e)}")
                                # Create silent audio as fallback
                                silent_audio = mp.AudioClip(lambda t: 0, duration=clip.duration)
                                clip = clip.set_audio(silent_audio)
                        except Exception as e:
                            print(f"Error applying extracted audio: {str(e)}")
                            # Create silent audio as fallback
                            silent_audio = mp.AudioClip(lambda t: 0, duration=clip.duration)
                            clip = clip.set_audio(silent_audio)
                        elif not has_valid_audio(clip):
                            print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                            # Create silent audio for the full duration
                            silent_audio = mp.AudioClip(lambda t: 0, duration=clip.duration)
                            clip = clip.set_audio(silent_audio)
                        else:
                            # Clip has valid audio
                            # Mark this segment as used
                            used_audio_segments.add(segment_id)
                            
                            # Update current audio position
                            current_audio_position += clip.duration
                            
                            print(f"Using original A-Roll audio with duration: {clip.duration:.2f}s")
                        
                        # Resize to target resolution
                        clip = resize_video(clip, target_resolution)
                        clips.append(clip)
                        
                        # Close the full clip if we created a subclip from it
                        if clip != full_clip:
                            full_clip.close()
                except Exception as e:
                    print(f"Error loading A-Roll clip: {str(e)}")
                    return {"status": "error", "message": f"Error loading A-Roll clip: {str(e)}"}
            
            elif item["type"] == "broll_with_aroll_audio":
                # Load B-Roll video with A-Roll audio
                broll_path = item["broll_path"]
                aroll_path = item["aroll_path"]
                
                try:
                    # Load B-Roll video
                    print(f"Loading B-Roll video: {broll_path}")
                    
                    # Check if B-Roll is an image file
                    if is_image_file(broll_path):
                        # Get segment-specific duration to use for the image
                        segment_duration = item.get("duration", 0)
                        
                        if segment_duration <= 0:
                            # If duration is not in the item, calculate from start/end time
                            segment_start = item.get("start_time", 0)
                            segment_end = item.get("end_time", 0)
                            if segment_end > segment_start:
                                segment_duration = segment_end - segment_start
                                print(f"Calculated segment duration from timestamps: {segment_duration}s")
                        
                        # If still no valid duration, fall back to audio duration
                        if segment_duration <= 0:
                            # Get A-Roll audio duration to use for the image
                            segment_duration = audio_durations.get(segment_id, 0)
                        
                        if segment_duration <= 0:
                            # If we don't have the audio duration yet, try to get it from the item
                            if "duration" in item and item["duration"] > 0:
                                segment_duration = item["duration"]
                                print(f"Using duration from sequence data: {segment_duration}s")
                            else:
                                # Default fallback duration
                                segment_duration = 5.0
                                print(f"No valid duration found, using default: {segment_duration}s")
                        
                        print(f"Creating B-Roll image video with exact segment duration: {segment_duration}s")
                        
                        # Convert image to video with matching duration
                        broll_clip = image_to_video(broll_path, duration=segment_duration, target_resolution=target_resolution)
                        
                        if broll_clip is None:
                            print(f"❌ Failed to convert image to video: {broll_path}")
                            continue
                            
                        print(f"✅ Successfully converted image to video with duration: {broll_clip.duration}s")
                    else:
                        # Regular video file
                        broll_clip = mp.VideoFileClip(broll_path)
                    
                    # Load A-Roll audio if available in extracted paths
                    if segment_id in extracted_audio_paths:
                        audio_path = extracted_audio_paths[segment_id]
                        try:
                            print(f"Loading extracted A-Roll audio: {audio_path}")
                            # Ensure audio_path is a string, not a dictionary
                            if isinstance(audio_path, dict) and 'output_path' in audio_path:
                                audio_path = audio_path['output_path']
                                print(f"Corrected audio path to: {audio_path}")
                            
                            # Verify the audio file exists
                            if not os.path.exists(audio_path):
                                raise FileNotFoundError(f"Audio file not found: {audio_path}")
                                
                            # Try to load the audio with error handling
                            try:
                                aroll_audio = mp.AudioFileClip(audio_path)
                                print(f"Successfully loaded audio with duration: {aroll_audio.duration:.2f}s")
                            except Exception as audio_error:
                                print(f"Error loading audio file: {str(audio_error)}")
                                print("Creating silent audio as fallback")
                                # Create silent audio with the same duration as the B-roll clip
                                aroll_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                            
                            # No need to extract segment with timestamps here since we've already
                            # extracted the specific segment audio file in the first phase
                            
                            # First, ensure the B-Roll clip has no audio of its own
                            broll_clip = broll_clip.without_audio()
                            
                            # Apply A-Roll audio to B-Roll video with error handling
                            try:
                                # Ensure the clip duration exactly matches the audio duration
                                exact_duration = min(broll_clip.duration, aroll_audio.duration)
                                broll_clip = broll_clip.subclip(0, exact_duration)
                                aroll_audio = aroll_audio.subclip(0, exact_duration)
                                
                                # Apply the precisely trimmed audio to the clip
                                broll_clip = broll_clip.set_audio(aroll_audio)
                                print("Successfully applied A-Roll audio to B-Roll clip")
                                
                                # Mark this segment as used
                                used_audio_segments.add(segment_id)
                                
                                # Update current audio position
                                current_audio_position += aroll_audio.duration
                            except Exception as e:
                                print(f"Error setting audio on B-Roll clip: {str(e)}")
                                # Create silent audio as fallback
                                print("Creating silent audio as fallback")
                                silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                broll_clip = broll_clip.set_audio(silent_audio)
                        except Exception as e:
                            print(f"Error applying A-Roll audio to B-Roll: {str(e)}")
                            # Fallback: Try loading A-Roll directly to extract audio
                            try:
                                print(f"Fallback: Loading A-Roll directly: {aroll_path}")
                                aroll_full_clip = mp.VideoFileClip(aroll_path)
                                
                                # Extract just the segment using start_time and end_time
                                start_time = item.get("start_time", 0)
                                end_time = item.get("end_time", 0)
                                
                                # If we have valid timestamps, extract just that portion of the video/audio
                                if end_time > start_time:
                                    print(f"Extracting A-Roll segment from {start_time:.2f}s to {end_time:.2f}s")
                                    try:
                                        # Ensure timestamps are within the clip duration
                                        if start_time < aroll_full_clip.duration and end_time <= aroll_full_clip.duration:
                                            aroll_clip = aroll_full_clip.subclip(start_time, end_time)
                                            print(f"Successfully extracted video segment with duration: {aroll_clip.duration:.2f}s")
                                        else:
                                            print(f"Warning: Timestamps ({start_time:.2f}s-{end_time:.2f}s) exceed video duration ({aroll_full_clip.duration:.2f}s)")
                                            # Use the full clip but create silent audio
                                            aroll_clip = aroll_full_clip
                                            if has_valid_audio(aroll_clip):
                                                # Set the audio to None so we'll create silent audio below
                                                aroll_clip = aroll_clip.without_audio()
                                    except Exception as subclip_error:
                                        print(f"Error extracting video subclip: {str(subclip_error)}")
                                        # Use the full clip but create silent audio
                                        aroll_clip = aroll_full_clip
                                        if has_valid_audio(aroll_clip):
                                            # Set the audio to None so we'll create silent audio below
                                            aroll_clip = aroll_clip.without_audio()
                                else:
                                    # No valid timestamps, use the full clip
                                    aroll_clip = aroll_full_clip
                                
                                segment_duration = end_time - start_time
                                
                                if has_valid_audio(aroll_clip):
                                    try:
                                        # First, ensure the B-Roll clip has no audio of its own
                                        broll_clip = broll_clip.without_audio()
                                        
                                        # Ensure the clip duration exactly matches the audio duration
                                        exact_duration = min(broll_clip.duration, aroll_clip.duration)
                                        broll_clip = broll_clip.subclip(0, exact_duration)
                                        
                                        # Set audio on B-roll clip
                                        broll_clip = broll_clip.set_audio(aroll_clip.audio)
                                        print(f"Successfully applied A-Roll audio to B-Roll clip, duration: {broll_clip.duration:.2f}s")
                                        
                                        # Mark this segment as used
                                        used_audio_segments.add(segment_id)
                                        
                                        # Update current audio position
                                        current_audio_position += aroll_clip.duration
                                    except Exception as e:
                                        print(f"Error setting audio on B-Roll clip: {str(e)}")
                                        # Create silent audio as fallback
                                        silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                        broll_clip = broll_clip.set_audio(silent_audio)
                                else:
                                    print(f"Fallback failed: A-Roll has no valid audio")
                                    # Create silent audio with the calculated segment duration
                                    silent_audio = mp.AudioClip(lambda t: 0, duration=segment_duration if segment_duration > 0 else broll_clip.duration)
                                    broll_clip = broll_clip.set_audio(silent_audio)
                                    print(f"Created silent audio with duration: {silent_audio.duration:.2f}s")
                                
                                # Close the clips to free resources
                                aroll_full_clip.close()
                                if 'aroll_clip' in locals() and aroll_clip != aroll_full_clip:
                                    aroll_clip.close()
                            except Exception as e2:
                                print(f"Fallback failed: {str(e2)}")
                                print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                                # Create silent audio
                                silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                broll_clip = broll_clip.set_audio(silent_audio)
                    else:
                        print(f"No extracted audio found for segment {segment_id}, trying direct audio extraction")
                        # Fallback: Try loading A-Roll directly to extract audio
                        try:
                            print(f"Fallback: Loading A-Roll directly: {aroll_path}")
                            aroll_full_clip = mp.VideoFileClip(aroll_path)
                            
                            # Extract just the segment using start_time and end_time
                            start_time = item.get("start_time", 0)
                            end_time = item.get("end_time", 0)
                            
                            # If we have valid timestamps, extract just that portion of the video/audio
                            if end_time > start_time:
                                print(f"Extracting A-Roll segment from {start_time:.2f}s to {end_time:.2f}s")
                                try:
                                    # Ensure timestamps are within the clip duration
                                    if start_time < aroll_full_clip.duration and end_time <= aroll_full_clip.duration:
                                        aroll_clip = aroll_full_clip.subclip(start_time, end_time)
                                        print(f"Successfully extracted video segment with duration: {aroll_clip.duration:.2f}s")
                                    else:
                                        print(f"Warning: Timestamps ({start_time:.2f}s-{end_time:.2f}s) exceed video duration ({aroll_full_clip.duration:.2f}s)")
                                        # Use the full clip but create silent audio
                                        aroll_clip = aroll_full_clip
                                        if has_valid_audio(aroll_clip):
                                            # Set the audio to None so we'll create silent audio below
                                            aroll_clip = aroll_clip.without_audio()
                                except Exception as subclip_error:
                                    print(f"Error extracting video subclip: {str(subclip_error)}")
                                    # Use the full clip but create silent audio
                                    aroll_clip = aroll_full_clip
                                    if has_valid_audio(aroll_clip):
                                        # Set the audio to None so we'll create silent audio below
                                        aroll_clip = aroll_clip.without_audio()
                            else:
                                # No valid timestamps, use the full clip
                                aroll_clip = aroll_full_clip
                            
                            segment_duration = end_time - start_time
                            
                            if has_valid_audio(aroll_clip):
                                try:
                                    # First, ensure the B-Roll clip has no audio of its own
                                    broll_clip = broll_clip.without_audio()
                                    
                                    # Ensure the clip duration exactly matches the audio duration
                                    exact_duration = min(broll_clip.duration, aroll_clip.duration)
                                    broll_clip = broll_clip.subclip(0, exact_duration)
                                    aroll_clip = aroll_clip.subclip(0, exact_duration)
                                    
                                    # Set audio on B-roll clip
                                    broll_clip = broll_clip.set_audio(aroll_clip.audio)
                                    print(f"Successfully applied A-Roll audio to B-Roll clip, duration: {broll_clip.duration:.2f}s")
                                    
                                    # Mark this segment as used
                                    used_audio_segments.add(segment_id)
                                    
                                    # Update current audio position
                                    current_audio_position += aroll_clip.duration
                                except Exception as e:
                                    print(f"Error setting audio on B-Roll clip: {str(e)}")
                                    # Create silent audio as fallback
                                    silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                    broll_clip = broll_clip.set_audio(silent_audio)
                            else:
                                print(f"A-Roll has no valid audio")
                                # Create silent audio with the calculated segment duration
                                silent_audio = mp.AudioClip(lambda t: 0, duration=segment_duration if segment_duration > 0 else broll_clip.duration)
                                broll_clip = broll_clip.set_audio(silent_audio)
                                print(f"Created silent audio with duration: {silent_audio.duration:.2f}s")
                            
                            # Close the clips to free resources
                            aroll_full_clip.close()
                            if 'aroll_clip' in locals() and aroll_clip != aroll_full_clip:
                                aroll_clip.close()
                        except Exception as e:
                            print(f"Error extracting audio from A-Roll: {str(e)}")
                            print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                            # Create silent audio
                            silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                            broll_clip = broll_clip.set_audio(silent_audio)
                    
                    # Resize to target resolution
                    broll_clip = resize_video(broll_clip, target_resolution)
                    clips.append(broll_clip)
                except Exception as e:
                    print(f"Error processing B-Roll with A-Roll audio: {str(e)}")
                    return {"status": "error", "message": f"Error processing B-Roll with A-Roll audio: {str(e)}"}
        
        if not clips:
            return {"status": "error", "message": "No valid clips to assemble"}
        
        # Concatenate clips
        progress_callback(60, "Concatenating video segments")
        
        # Ensure all clips have valid audio
        for i, clip in enumerate(clips):
            try:
                # Check if clip has audio
                if clip.audio is None or not has_valid_audio(clip):
                    print(f"Clip {i+1} has no valid audio, adding silent audio")
                    silent_audio = mp.AudioClip(lambda t: 0, duration=clip.duration)
                    clip = clip.set_audio(silent_audio)
                    clips[i] = clip
            except Exception as e:
                print(f"Error checking audio for clip {i+1}: {str(e)}")
                # Create silent audio
                silent_audio = mp.AudioClip(lambda t: 0, duration=clip.duration)
                clip = clip.set_audio(silent_audio)
                clips[i] = clip
        
        # Use method='compose' to ensure proper audio concatenation without overlaps
        try:
            final_clip = mp.concatenate_videoclips(clips, method='compose', padding=0)
        except Exception as concat_error:
            print(f"Error concatenating clips: {str(concat_error)}")
            print("Trying alternate concatenation method...")
            try:
                # Try with method='chain' as fallback
                final_clip = mp.concatenate_videoclips(clips, method='chain', padding=0)
            except Exception as e:
                return {"status": "error", "message": f"Failed to concatenate video clips: {str(e)}"}
        
        # Set output path
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"assembled_video_{timestamp}.mp4")
        
        # Write final video with error handling
        progress_callback(80, "Writing final video")
        try:
            # Check if final clip has valid audio
            if final_clip.audio is None or not has_valid_audio(final_clip):
                print("Final clip has no valid audio, adding silent audio")
                silent_audio = mp.AudioClip(lambda t: 0, duration=final_clip.duration)
                final_clip = final_clip.set_audio(silent_audio)
            
            # Write video with explicit audio settings
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                fps=30,
                audio_fps=44100,  # Explicitly set audio sample rate
                audio_nbytes=2,   # 16-bit audio
                verbose=False,
                logger=None
            )
        except Exception as write_error:
            print(f"Error writing video file: {str(write_error)}")
            print("Attempting to write without audio...")
            try:
                # Try writing without audio as fallback
                final_clip_no_audio = final_clip.without_audio()
                final_clip_no_audio.write_videofile(
                    output_path,
                    codec="libx264",
                    audio=False,
                    fps=30,
                    verbose=False,
                    logger=None
                )
                print("Video written successfully without audio")
            except Exception as e:
                return {"status": "error", "message": f"Failed to write video file: {str(e)}"}
        
        # Clean up
        progress_callback(95, "Cleaning up")
        for clip in clips:
            clip.close()
        final_clip.close()
        
        # Clean up extracted audio files
        try:
            shutil.rmtree(audio_temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary audio files: {str(e)}")
        
        progress_callback(100, "Video assembly complete")
        
        return {
            "status": "success",
            "message": "Video assembled successfully",
            "output_path": output_path
        }
    except Exception as e:
        print(f"Error in video assembly: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        # Ensure temp directories are cleaned up
        try:
            if 'audio_temp_dir' in locals():
                shutil.rmtree(audio_temp_dir)
        except Exception:
            pass

@error_handler
def extract_audio(video_path, output_path=None):
    """
    Extract audio from a video file (simplified version for compatibility)
    
    Args:
        video_path: Path to the video file
        output_path: Path to save the extracted audio (optional)
        
    Returns:
        str: Path to the extracted audio file or None if extraction failed
    """
    # Call the more comprehensive extract_audio_track function
    result = extract_audio_track(video_path, os.path.dirname(output_path) if output_path else None)
    
    # For compatibility, return just the path or None
    if result["status"] == "success":
        return result["output_path"]
    else:
        print(f"Error extracting audio: {result.get('message', 'Unknown error')}")
        return None

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