import os
import tempfile
import time
from pathlib import Path
import replicate
from utils.video_stitcher import download_video
import requests
import json
import base64
import re
import math
import random

# Models available on Replicate
AVAILABLE_MODELS = {
    "zeroscope_v2": {
        "id": "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351",
        "description": "Zeroscope V2 XL - High quality text-to-video model"
    },
    "svd_xt": {
        "id": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        "description": "Stable Diffusion XL - High quality image generation model (fallback)"
    },
    "wan_2_1_1_3b": {
        "id": "wan-video/wan-2.1-1.3b:121bbb762bf449889f090d36e3598c72c50c7a8cc2ce250433bc521a562aae61",
        "description": "WAN 2.1 (1.3B) - Wave Animation Network model"
    },
    "wan_2_1_t2v_480p": {
        "id": "wavespeedai/wan-2.1-t2v-480p:067897beabcf7ff30fe6b10dc9f99eeebd2b4d6fdab52eb08d3b47d7116dfa19",
        "description": "WAN 2.1 T2V - Text to video generation at 480p"
    },
    "kling_v2": {
        "id": "kwaivgi/kling-v2.0:5b15e6bf879ebd2fbb4510f78eb6dd00e666e06716915d0c31533651a744748f",
        "description": "Kling V2.0 - High quality text-to-video model"
    },
    "hunyuan_video": {
        "id": "tencent/hunyuan-video:6c9132aee14409cd6568d030453f1ba50f5f3412b844fe67f78a9eb62d55664f",
        "description": "Hunyuan Video - Tencent's high-fidelity text-to-video generation model"
    }
}

def get_available_models():
    """Return available Replicate models for the UI"""
    return list(AVAILABLE_MODELS.keys())

def parse_resolution_and_aspect_ratio(resolution, aspect_ratio):
    """
    Parse resolution and aspect ratio settings to determine width and height.
    
    Args:
        resolution (str): Resolution setting like "480p", "720p", "1080p"
        aspect_ratio (str): Aspect ratio like "16:9", "9:16", "1:1"
        
    Returns:
        tuple: Width and height in pixels
    """
    # Parse resolution for base height
    if resolution == "480p":
        base_height = 480
    elif resolution == "720p":
        base_height = 720
    elif resolution == "1080p":
        base_height = 1080
    elif resolution == "360p":
        base_height = 360
    else:
        # Default to 720p if not recognized
        base_height = 720
    
    # Parse aspect ratio
    try:
        aspect_parts = aspect_ratio.split(":")
        width_ratio = int(aspect_parts[0])
        height_ratio = int(aspect_parts[1])
    except (ValueError, IndexError):
        # Default to 16:9 if invalid format
        width_ratio, height_ratio = 16, 9
    
    # Calculate width and height based on orientation
    if width_ratio >= height_ratio:  # Landscape or square
        width = (base_height * width_ratio) // height_ratio
        height = base_height
    else:  # Portrait
        width = base_height
        height = (base_height * height_ratio) // width_ratio
    
    # Ensure width is even (required by some encoders)
    width = width + (width % 2)
    # Ensure height is even
    height = height + (height % 2)
    
    return width, height

def get_client(api_key):
    """Get a configured Replicate client"""
    # The replicate package will use REPLICATE_API_TOKEN env var if not provided
    os.environ["REPLICATE_API_TOKEN"] = api_key
    return replicate

def list_predictions(api_key, limit=20):
    """
    List recent predictions made with the Replicate API.
    
    Args:
        api_key (str): Replicate API key
        limit (int): Maximum number of predictions to return (default: 20)
        
    Returns:
        list: List of prediction objects or None if failed
    """
    if not api_key:
        raise ValueError("Replicate API key is required")
    
    # Set up headers for API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Get predictions from Replicate
    print(f"Listing up to {limit} recent predictions")
    api_url = f"https://api.replicate.com/v1/predictions"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        predictions = data.get("results", [])
        
        # Filter to only include completed predictions with video output
        completed_predictions = [
            p for p in predictions 
            if p.get("status") == "succeeded" and p.get("output") is not None
        ]
        
        return completed_predictions[:limit]
    
    except Exception as e:
        print(f"Error listing predictions: {str(e)}")
        return None

def cancel_prediction(api_key, prediction_id):
    """
    Cancel a running prediction on Replicate.
    
    Args:
        api_key (str): Replicate API key
        prediction_id (str): ID of the prediction to cancel
        
    Returns:
        dict: Response containing success status and message
    """
    if not api_key:
        return {"success": False, "message": "Replicate API key is required"}
    
    if not prediction_id:
        return {"success": False, "message": "Prediction ID is required"}
    
    # Set up headers for API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make the cancel request
        api_url = f"https://api.replicate.com/v1/predictions/{prediction_id}/cancel"
        response = requests.post(api_url, headers=headers)
        
        # Check if the request was successful
        response.raise_for_status()
        
        print(f"Successfully canceled prediction: {prediction_id}")
        return {
            "success": True, 
            "message": f"Successfully canceled prediction: {prediction_id}",
            "status_code": response.status_code
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else None
        error_message = f"HTTP Error: {e}"
        
        # Handle specific HTTP errors
        if status_code == 404:
            error_message = f"Prediction {prediction_id} not found"
        elif status_code == 401:
            error_message = "Unauthorized: Invalid API key"
        elif status_code == 403:
            error_message = "Forbidden: You don't have permission to cancel this prediction"
        
        print(error_message)
        return {"success": False, "message": error_message, "status_code": status_code}
    
    except Exception as e:
        print(f"Error canceling prediction: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def generate_broll(prompt, api_key, model_name="zeroscope_v2", duration_seconds=4, progress_tracker=None, segment_index=0, resolution="720p", aspect_ratio="16:9", force_portrait=False):
    """
    Generate B-roll video using Replicate API.
    
    Args:
        prompt (str): The prompt describing the desired B-roll content
        api_key (str): Replicate API key
        model_name (str): The model to use for generation
        duration_seconds (int): Duration in seconds (1-10)
        progress_tracker: Optional progress tracker object
        segment_index (int): Index of the segment being generated
        resolution (str): Video resolution (e.g., "480p", "720p", "1080p")
        aspect_ratio (str): Video aspect ratio (e.g., "16:9", "9:16", "1:1")
        force_portrait (bool): Force portrait mode (9:16) regardless of aspect_ratio setting
        
    Returns:
        tuple: Path to the generated video file and path to local downloaded copy
    """
    if not api_key:
        raise ValueError("Replicate API key is required")
    
    # Ensure we have a valid model
    if model_name not in AVAILABLE_MODELS:
        print(f"⚠️ WARNING: Model '{model_name}' not found in AVAILABLE_MODELS dictionary")
        print(f"Available models: {list(AVAILABLE_MODELS.keys())}")
        print(f"Falling back to default model: zeroscope_v2")
        model_name = "zeroscope_v2"  # Default fallback
    
    model_id = AVAILABLE_MODELS[model_name]["id"]
    print(f"🚀 Using model: {model_name} with ID: {model_id}")
    
    # Ensure duration is within limits
    duration_seconds = max(1, min(10, duration_seconds))
    
    # Create temporary directory for storing the video
    temp_dir = Path(tempfile.mkdtemp())
    output_path = temp_dir / f"broll_{int(time.time())}.mp4"
    
    # Update progress tracker if provided
    if progress_tracker:
        progress_tracker.update_segment_progress(
            segment_index, 
            0.1,  # Initial progress
            "b-roll", 
            "replicate"
        )
    
    # Apply portrait mode if forced or if using WAN models (they work better with short-form)
    use_portrait = force_portrait or ("wan" in model_name.lower() and aspect_ratio != "1:1")
    
    # If using portrait mode, override the aspect ratio
    if use_portrait:
        aspect_ratio = "9:16"
        print(f"Using portrait mode (9:16) for {model_name}")
    
    # Parse resolution to width and height
    width, height = parse_resolution_and_aspect_ratio(resolution, aspect_ratio)
    
    # Ensure dimensions are optimal for the model
    if use_portrait and model_name in ["wan_2_1_1_3b", "wan_2_1_t2v_480p"]:
        # For WAN models, ensure dimensions are optimal for portrait mode
        if resolution == "480p":
            width, height = 480, 848  # 9:16 at 480p
        elif resolution == "720p":
            width, height = 720, 1280  # 9:16 at 720p 
        else:
            width, height = 576, 1024  # Default optimal size for WAN models in portrait
    
    print(f"Generating video with dimensions: {width}x{height} ({aspect_ratio})")
    
    # Set API token
    os.environ["REPLICATE_API_TOKEN"] = api_key
    
    # Model-specific parameters
    if model_name == "zeroscope_v2":
        input_params = {
            "prompt": prompt,
            "fps": 24,
            "num_frames": 24 * duration_seconds,  # Duration in frames at 24 fps
            "guidance_scale": 12.5,
            "width": width,
            "height": height
        }
    elif model_name == "svd_xt":
        # SDXL is an image model, not video, so we'll adapt parameters
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height
        }
    elif model_name == "wan_2_1_1_3b":
        # WAN 2.1 parameters - optimized for vertical video
        input_params = {
            "prompt": prompt,
            "negative_prompt": "low quality, bad quality, blurry, low resolution, distorted, watermark, text, cropped",
            "num_frames": 16,  # WAN typically uses 16 frames
            "num_steps": 50,
            "width": width,
            "height": height,
            "guidance_scale": 15.0,  # Higher guidance scale for better prompt adherence
            "seed": random.randint(1, 2147483647)  # Random seed for variety
        }
    elif model_name == "wan_2_1_t2v_480p":
        # WAN T2V parameters - optimized for vertical video
        input_params = {
            "prompt": prompt,
            "negative_prompt": "low quality, bad quality, blurry, low resolution, distorted, watermark, text, cropped",
            "num_frames": 16,
            "fps": 8,
            "guidance_scale": 17.5,  # Higher guidance for short-form video clarity
            "width": width,
            "height": height,
            "seed": random.randint(1, 2147483647)  # Random seed for variety
        }
    elif model_name == "kling_v2":
        # Kling parameters
        input_params = {
            "prompt": prompt, 
            "negative_prompt": "low quality, bad quality, blurry, watermark",
            "num_inference_steps": 50,
            "guidance_scale": 12.5,
            "width": width,
            "height": height,
            "num_frames": 24 * duration_seconds
        }
    elif model_name == "hunyuan_video":
        # Hunyuan parameters
        input_params = {
            "prompt": prompt,
            "negative_prompt": "Low quality, blurry, distorted, unnatural movements, watermark, text",
            "num_frames": 24 * duration_seconds,
            "fps": 24,
            "width": width,
            "height": height
        }
    else:
        # Generic parameters
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height
        }
    
    try:
        # Update progress
        if progress_tracker:
            progress_tracker.update_segment_progress(
                segment_index, 
                0.3,  # API call started
                "b-roll", 
                "replicate"
            )
        
        # Use the simpler replicate.run() approach from the documentation
        output = replicate.run(
            model_id,
            input=input_params
        )
        
        # Handle different output formats
        if isinstance(output, list):
            # Handle list output (common for image/video models)
            download_url = output[0]
        elif hasattr(output, 'read'):
            # Handle FileOutput objects
            with open(output_path, "wb") as f:
                f.write(output.read())
            download_url = None
        else:
            # Handle string URL
            download_url = output
        
        # If we have a download URL, process it
        if download_url:
            # Download the video
            from requests import get
            video_response = get(download_url)
            video_response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(video_response.content)
            
            # Use download_video function for local storage
            local_path = download_video(download_url, {
                "type": "b-roll", 
                "id": f"broll_{int(time.time())}",
                "width": width,
                "height": height
            }, "replicate")
            
            # Update progress to complete
            if progress_tracker:
                progress_tracker.update_segment_progress(
                    segment_index, 
                    1.0,  # Complete
                    "b-roll", 
                    "replicate"
                )
            
            return str(output_path), local_path
        else:
            # If we wrote the file directly from output.read()
            local_path = str(output_path)
            # Use download_video function for local storage
            local_path = download_video(local_path, {
                "type": "b-roll", 
                "id": f"broll_{int(time.time())}",
                "width": width,
                "height": height
            }, "replicate")
            
            # Update progress to complete
            if progress_tracker:
                progress_tracker.update_segment_progress(
                    segment_index, 
                    1.0,  # Complete
                    "b-roll", 
                    "replicate"
                )
            
            return str(output_path), local_path
    except Exception as e:
        raise ValueError(f"Error generating video with Replicate: {str(e)}")

def generate_broll_segments(segments, api_key, model_name="zeroscope_v2", progress_tracker=None, resolution="720p", aspect_ratio="16:9", force_portrait=False):
    """
    Generate multiple B-roll video segments using Replicate API.
    
    Args:
        segments (list): List of segment dictionaries with 'content', 'description', and 'prompt' keys
        api_key (str): Replicate API key
        model_name (str): The model to use for generation
        progress_tracker: Optional progress tracker object
        resolution (str): Video resolution (e.g., "480p", "720p", "1080p")
        aspect_ratio (str): Video aspect ratio (e.g., "16:9", "9:16", "1:1")
        force_portrait (bool): Force portrait mode (9:16) regardless of aspect_ratio setting
        
    Returns:
        list: List of dictionaries with segment info and paths to generated videos
    """
    if not api_key:
        raise ValueError("Replicate API key is required")
    
    results = []
    
    # Process each segment
    for i, segment in enumerate(segments):
        if segment.get("type") != "b-roll":
            continue
            
        content = segment.get("content", "")
        description = segment.get("description", "visual footage")
        
        if not content.strip():
            continue
        
        # Get or create prompt
        prompt = segment.get("prompt")
        if not prompt:
            prompt = f"Create visual footage of {description} that represents: {content}"
        
        # Calculate duration - Replicate models typically handle 2-6 seconds well
        word_count = len(content.split())
        duration = min(6, max(2, word_count / 15))
        
        try:
            # Generate the B-roll segment
            output_path, local_path = generate_broll(
                prompt=prompt,
                api_key=api_key,
                model_name=model_name,
                duration_seconds=duration,
                progress_tracker=progress_tracker,
                segment_index=i,
                resolution=resolution,
                aspect_ratio=aspect_ratio,
                force_portrait=force_portrait
            )
            
            # Add the result to our list
            results.append({
                "index": i,
                "type": "b-roll",
                "content": content,
                "description": description,
                "path": output_path,
                "local_path": local_path,
                "duration": duration,
                "api": "replicate",
                "model": model_name,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio if not force_portrait else "9:16"
            })
            
        except Exception as e:
            # Log the error but continue with other segments
            print(f"Error generating B-roll segment {i}: {str(e)}")
    
    return results

def check_model_accessibility(api_key, model_name=None):
    """
    Check if a specific model or all models are accessible through the Replicate API.
    
    Args:
        api_key (str): Replicate API key
        model_name (str, optional): Specific model name to check. If None, checks all models.
        
    Returns:
        dict: Dictionary with model names as keys and boolean accessibility status as values
    """
    if not api_key:
        raise ValueError("Replicate API key is required")
    
    # Set the API token as an environment variable
    os.environ["REPLICATE_API_TOKEN"] = api_key
    
    if model_name:
        print(f"🔍 Checking accessibility for model: {model_name}")
    else:
        print(f"🔍 Checking accessibility for all models: {list(AVAILABLE_MODELS.keys())}")
    
    results = {}
    models_to_check = [model_name] if model_name else list(AVAILABLE_MODELS.keys())
    
    for model in models_to_check:
        if model not in AVAILABLE_MODELS:
            results[model] = {"accessible": False, "error": "Model not defined in available models"}
            continue
        
        model_id = AVAILABLE_MODELS[model]["id"]
        
        try:
            # For models that don't need specific inputs (like SDXL), we'll use a minimal input
            min_input = {"prompt": "test accessibility"}
            
            # Try to create a minimal prediction to check accessibility
            # We'll set a very short timeout to avoid waiting for actual generation
            try:
                # Just check if the model is accessible by using run() with a timeout
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(replicate.run, model_id, input=min_input)
                    try:
                        # Just try to start the prediction, don't wait for completion
                        future.result(timeout=2.0)  # Short timeout, we don't need the result
                        is_accessible = True
                    except concurrent.futures.TimeoutError:
                        # This is actually good - means we were able to start the prediction
                        is_accessible = True
                    except Exception as run_error:
                        error_str = str(run_error)
                        # If the error is about inputs, that means the model exists but needs specific inputs
                        if "input" in error_str.lower() and "not found" not in error_str.lower():
                            is_accessible = True
                        else:
                            is_accessible = False
                            error_msg = error_str
                
                if is_accessible:
                    results[model] = {
                        "accessible": True,
                        "model_id": model_id
                    }
                else:
                    results[model] = {
                        "accessible": False,
                        "error": error_msg if 'error_msg' in locals() else "Unknown error"
                    }
            
            except Exception as e:
                # If there's a general exception, the model is probably not accessible
                results[model] = {"accessible": False, "error": str(e)}
                
        except Exception as e:
            results[model] = {"accessible": False, "error": str(e)}
    
    return results

def check_all_models_accessibility(api_key):
    """
    Check accessibility for all defined models and return a report.
    
    Args:
        api_key (str): Replicate API key
        
    Returns:
        dict: Detailed report on model accessibility
    """
    results = check_model_accessibility(api_key)
    
    # Summary statistics
    summary = {
        "total_models": len(results),
        "accessible_models": sum(1 for r in results.values() if r.get("accessible", False)),
        "inaccessible_models": sum(1 for r in results.values() if not r.get("accessible", False))
    }
    
    return {
        "summary": summary,
        "model_details": results
    }

def fetch_prediction_by_id(prediction_id, api_key):
    """
    Fetch a prediction and its output from Replicate using its ID.
    
    Args:
        prediction_id (str): Replicate prediction ID to fetch
        api_key (str): Replicate API key
        
    Returns:
        tuple: (video path, prediction data) or (None, None) if failed
    """
    if not api_key:
        raise ValueError("Replicate API key is required")
    
    if not prediction_id:
        raise ValueError("Prediction ID is required")
    
    # Create temporary directory for output if it doesn't exist
    output_dir = Path("temp/videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up headers for API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Check the status of the prediction
    print(f"Fetching prediction with ID: {prediction_id}")
    api_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        prediction_data = response.json()
        
        # Check if the prediction is completed
        status = prediction_data.get("status", "")
        if status != "succeeded":
            raise ValueError(f"Prediction is not completed. Current status: {status}")
        
        # Handle different output types (single URL string or list of URLs)
        output = prediction_data.get("output", None)
        if not output:
            raise ValueError("No output available for this prediction")
        
        # Store paths of downloaded videos
        video_paths = []
        
        # Handle single output (string) or multiple outputs (list)
        outputs_to_process = [output] if isinstance(output, str) else output
        
        for i, video_url in enumerate(outputs_to_process):
            if not isinstance(video_url, str):
                continue
                
            # Skip non-video outputs
            if not (video_url.startswith("http") and (video_url.endswith(".mp4") or 
                                                     video_url.endswith(".webm") or
                                                     video_url.endswith(".gif") or
                                                     "video" in video_url)):
                continue
                
            # Download the video
            try:
                download_resp = requests.get(video_url, headers={"Authorization": f"Bearer {api_key}"})
                download_resp.raise_for_status()
                
                # Save to a temporary file
                temp_file = output_dir / f"replicate_fetched_{prediction_id}_{i}.mp4"
                with open(temp_file, "wb") as f:
                    f.write(download_resp.content)
                
                print(f"Downloaded video to: {temp_file}")
                video_paths.append(str(temp_file))
                
                # Use our download function to maintain consistency with the video storage system
                local_path = download_video(video_url, {"type": "b-roll", "id": f"{prediction_id}_{i}"}, "replicate")
            
            except Exception as e:
                print(f"Error downloading video output {i}: {str(e)}")
        
        if video_paths:
            return video_paths, prediction_data
        else:
            print("No video outputs found in the prediction")
            return None, prediction_data
            
    except Exception as e:
        print(f"Error fetching prediction: {str(e)}")
        return None, None 