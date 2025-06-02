import os
import sys
import json
import requests
import time
import traceback
from pathlib import Path

# Constants
OLLAMA_API_URL = "http://100.115.243.42:11434/api"
DEFAULT_MODEL = "mistral:7b-instruct-v0.3-q4_K_M"

def check_ollama_availability():
    """
    Check if Ollama is available
    
    Returns:
        bool: True if Ollama is available, False otherwise
    """
    try:
        response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error connecting to Ollama API: {str(e)}")
        return False

def get_available_models():
    """
    Get available Ollama models
    
    Returns:
        list: List of available Ollama models
    """
    try:
        response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=5)
        if response.status_code == 200:
            models = [model['name'] for model in response.json().get('models', [])]
            return models
        return []
    except Exception as e:
        print(f"Error connecting to Ollama API: {str(e)}")
        return []

def generate_broll_prompt(segment_text, theme, model=DEFAULT_MODEL, is_video=True):
    """
    Generate a B-Roll prompt for a given text segment using Ollama
    
    Args:
        segment_text: Text from the A-Roll segment
        theme: Theme of the video
        model: Ollama model to use
        is_video: Whether to generate a video or image prompt
        
    Returns:
        str: Generated B-Roll prompt
    """
    try:
        print(f"Generating B-Roll prompt using model: {model}")
        
        # Create a thoughtful prompt for the LLM
        video_or_image = "video" if is_video else "image"
        resolution = "1080x1920"  # Default to 9:16 ratio for shorts
        
        # Add video-specific instructions for motion if generating video
        video_specific_instructions = "" if not is_video else """
        For video, you MUST:
        - Describe specific motion and animation (e.g., slow motion, panning, tracking shots)
        - Include how elements move or change over the duration of the clip
        - Describe dynamic camera movements if applicable
        - Add temporal elements like "as the camera moves..." or "gradually revealing..."
        - Think cinematically about how the scene unfolds over time
        """
        
        # Select example based on video or image
        example_prompt = """
        "A large orange octopus is seen resting on the bottom of the ocean floor, blending in with the sandy and rocky terrain. Its tentacles are spread out around its body, and its eyes are closed. The octopus is unaware of a king crab that is crawling towards it from behind a rock, its claws raised and ready to attack. The scene is captured from a wide angle, showing the vastness and depth of the ocean. The water is clear and blue, with rays of sunlight filtering through."
        """
        
        if is_video:
            example_prompt = """
            "A large orange octopus rests on the sandy ocean floor as the camera slowly pans from left to right. Its tentacles gently sway with the current, creating hypnotic motion. As the shot progresses, a king crab emerges from behind a rock, moving deliberately toward the unaware octopus with raised claws. The camera track continues revealing more of the scene, with rays of sunlight dancing through the clear blue water, creating shifting patterns of light on the ocean floor. Small fish dart across the frame, adding dynamism to this underwater tableau."
            """
        
        prompt_instructions = f"""
        Create a detailed, cinematic, and visually rich {video_or_image} generation prompt based on this text: "{segment_text}"
        
        The theme is: {theme}
        Target resolution: {resolution} (9:16 ratio)
        {video_specific_instructions}
        
        Your prompt should:
        1. Create a vivid, detailed scene with a clear subject/focus
        2. Include rich details about:
           - Setting and environment
           - Lighting, mood, and atmosphere
           - Color palette and visual tone
           - Camera angle, framing, and composition
           - Subject positioning and activity
           - Background elements and context
        3. Tell a mini-story within the scene that ACCURATELY depicts what's being spoken about in the text
        4. Avoid generic terms like "4K" or "HD" (resolution is already defined)
        5. Be 2-4 sentences maximum with descriptive, evocative language
        
        Here's an excellent example of the level of detail and storytelling I want:
        {example_prompt}
        
        Return ONLY the prompt text, nothing else. No explanations, no "Prompt:" prefix, just the prompt itself.
        """
        
        # Increase timeout and add retry logic
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Increase timeout to 60 seconds
                response = requests.post(
                    f"{OLLAMA_API_URL}/generate",
                    json={
                        "model": model,
                        "prompt": prompt_instructions,
                        "stream": False
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    generated_prompt = response.json().get('response', '').strip()
                    # Clean up any quotation marks from the response
                    generated_prompt = generated_prompt.replace('"', '').replace('"', '').replace('"', '')
                    return generated_prompt
                else:
                    print(f"Error from Ollama API: {response.status_code} - {response.text}")
                    current_retry += 1
                    time.sleep(1)  # Wait before retrying
            except requests.exceptions.Timeout:
                current_retry += 1
                print(f"Timeout connecting to Ollama API (attempt {current_retry}/{max_retries})")
                time.sleep(2)  # Wait longer before retrying
            except Exception as e:
                current_retry += 1
                print(f"Error connecting to Ollama API: {str(e)}")
                print(traceback.format_exc())
                time.sleep(1)  # Wait before retrying
                
        # If we've exhausted retries, return a fallback prompt
        if is_video:
            return f"A detailed {video_or_image} showing {segment_text}, set in a {theme} environment with atmospheric lighting and rich visual elements. The camera slowly pans across the scene with subtle motion elements creating visual interest."
        else:
            return f"A detailed {video_or_image} showing {segment_text}, set in a {theme} environment with atmospheric lighting and rich visual elements."
    except Exception as e:
        print(f"Error generating prompt: {str(e)}")
        print(traceback.format_exc())
        if is_video:
            return f"A detailed {video_or_image} showing {segment_text}, set in a {theme} environment with atmospheric lighting and rich visual elements. The camera slowly pans across the scene with subtle motion elements creating visual interest."
        else:
            return f"A detailed {video_or_image} showing {segment_text}, set in a {theme} environment with atmospheric lighting and rich visual elements."

def generate_negative_prompt(segment_text, model=DEFAULT_MODEL):
    """
    Generate a negative prompt for a given text segment using Ollama
    
    Args:
        segment_text: Text from the A-Roll segment
        model: Ollama model to use
        
    Returns:
        str: Generated negative prompt
    """
    try:
        # Default negative prompt to use if API call fails
        default_negative = "poor quality, blurry, distorted faces, bad anatomy, ugly, unrealistic, deformed, low resolution, amateur, poorly composed, out of frame, pixelated, watermark, signature, text"
        
        negative_instructions = f"""
        Based on this prompt: "{segment_text}"
        
        Generate a negative prompt for image/video generation that will help avoid common issues.
        Include terms to avoid: poor quality, blurry, distorted faces, bad anatomy, ugly, unrealistic, 
        deformed, low resolution, amateur, poorly composed, and any other elements that would lower quality.
        
        Return ONLY the negative prompt text - no explanations or additional context.
        """
        
        # Increase timeout and add retry logic
        max_retries = 2  # Fewer retries for negative prompt since we have a good default
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Increase timeout to 45 seconds
                response = requests.post(
                    f"{OLLAMA_API_URL}/generate",
                    json={
                        "model": model,
                        "prompt": negative_instructions,
                        "stream": False
                    },
                    timeout=45
                )
                
                if response.status_code == 200:
                    negative_prompt = response.json().get('response', '').strip()
                    # Clean up any quotation marks from the response
                    negative_prompt = negative_prompt.replace('"', '').replace('"', '').replace('"', '')
                    return negative_prompt
                else:
                    current_retry += 1
                    time.sleep(1)  # Wait before retrying
            except Exception as e:
                current_retry += 1
                time.sleep(1)  # Wait before retrying
                
        # If we've exhausted retries, return the default negative prompt
        return default_negative
    except Exception as e:
        # Return a default negative prompt if there's an exception
        return default_negative

def generate_all_broll_prompts(segments, theme, model=DEFAULT_MODEL, is_video=True):
    """
    Generate B-Roll prompts for all segments
    
    Args:
        segments: List of segments
        theme: Theme of the video
        model: Ollama model to use
        is_video: Whether to generate video or image prompts
        
    Returns:
        dict: Dictionary of prompts
    """
    prompts = {}
    
    # Track B-Roll segment IDs
    broll_counter = 0
    
    print(f"Generating B-Roll prompts using model: {model}")
    
    for i, segment in enumerate(segments):
        if segment["type"] == "B-Roll":
            # Create a segment identifier
            segment_id = f"segment_{broll_counter}"
            
            # Check if this segment has multiple visuals
            visuals = segment.get("visuals", [])
            
            if visuals:
                # Create a prompt for each visual with its own ID
                for j, visual in enumerate(visuals):
                    visual_id = f"{segment_id}_visual_{j}"
                    visual_text = visual.get("content", segment.get("content", ""))
                    
                    # Generate the prompt
                    print(f"Generating prompt for {visual_id}: {visual_text[:50]}...")
                    
                    # Get timestamp information if available
                    timestamp_info = ""
                    if "timestamp" in segment and "duration" in visual:
                        visual_timestamp = segment["timestamp"] + (visual.get("position", 0) * segment.get("duration", 0))
                        timestamp_info = f" at timestamp {visual_timestamp:.2f}s"
                    
                    # Generate the prompt with timestamp context
                    prompt = generate_broll_prompt(
                        f"{visual_text}{timestamp_info}",
                        theme,
                        model,
                        is_video
                    )
                    
                    # Generate negative prompt if needed
                    negative_prompt = generate_negative_prompt(visual_text, model)
                    
                    prompts[visual_id] = {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "is_video": is_video,
                        "segment_text": visual_text,
                        "timestamp": visual_timestamp if "timestamp" in segment else None,
                        "duration": visual.get("duration")
                    }
            else:
                # No visuals specified, create a single prompt for the whole segment
                segment_text = segment.get("content", "")
                
                # Generate the prompt
                print(f"Generating prompt for {segment_id}: {segment_text[:50]}...")
                
                # Include timestamp information if available
                timestamp_info = ""
                if "timestamp" in segment:
                    timestamp_info = f" at timestamp {segment['timestamp']:.2f}s"
                
                prompt = generate_broll_prompt(
                    f"{segment_text}{timestamp_info}",
                    theme,
                    model,
                    is_video
                )
                
                # Generate negative prompt if needed
                negative_prompt = generate_negative_prompt(segment_text, model)
                
                prompts[segment_id] = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "is_video": is_video,
                    "segment_text": segment_text,
                    "timestamp": segment.get("timestamp"),
                    "duration": segment.get("duration", 3.0)
                }
                
            # Increment the counter for B-Roll segments
            broll_counter += 1
    
    return {"prompts": prompts}

def save_broll_prompts(prompts, project_path, broll_type="video"):
    """
    Save B-Roll prompts to a JSON file
    
    Args:
        prompts: Dictionary of prompts
        project_path: Path to the project directory
        broll_type: Type of B-Roll (image, video)
        
    Returns:
        bool: True if saved successfully
    """
    try:
        # Create the path to broll_prompts.json
        if isinstance(project_path, str):
            project_path = Path(project_path)
            
        prompts_file = project_path / "broll_prompts.json"
        
        # Load existing file if it exists
        existing_data = {}
        if prompts_file.exists():
            try:
                with open(prompts_file, "r") as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading existing prompts: {str(e)}")
        
        # Update with new prompts
        data = {
            "prompts": prompts.get("prompts", {}),
            "broll_type": broll_type,
            "exclude_negative_prompts": False,
            "image_template": "flux_schnell",  # Default template
            "map_broll_to_aroll": True,
            "broll_aroll_mapping": existing_data.get("broll_aroll_mapping", {})
        }
        
        # Preserve any additional fields from existing data
        for key, value in existing_data.items():
            if key not in data and key != "prompts":
                data[key] = value
        
        # Save to file
        with open(prompts_file, "w") as f:
            json.dump(data, f, indent=4)
            
        print(f"Saved {len(data['prompts'])} B-Roll prompts to {prompts_file}")
        return True
    except Exception as e:
        print(f"Error saving B-Roll prompts: {str(e)}")
        print(traceback.format_exc())
        return False 