#!/usr/bin/env python3
"""
Caption generator for AI Money Printer Shorts videos
Provides automatic caption generation and stylish overlay options
"""

import os
import sys
import tempfile
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import shutil
import math

# Add parent directory to path
app_root = Path(__file__).parent.parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path from captions module")

# Try to import required packages
try:
    import moviepy.editor as mp
    from moviepy.video.tools.subtitles import SubtitlesClip
    import numpy as np
    # Check if any transcription engine is available
    try:
        from utils.audio.transcription import transcribe_video as transcription_func
        TRANSCRIPTION_AVAILABLE = True
        print("✅ Successfully imported transcription module")
    except ImportError:
        # Try to import whisper directly as fallback
        try:
            import whisper
            TRANSCRIPTION_AVAILABLE = True
            print("✅ Successfully imported whisper module")
        except ImportError:
            TRANSCRIPTION_AVAILABLE = False
            print("❌ No transcription module available")

    from PIL import Image, ImageDraw, ImageFont
    DEPENDENCIES_AVAILABLE = True
    print("✅ Successfully imported caption dependencies")
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    TRANSCRIPTION_AVAILABLE = False
    print(f"❌ Error importing caption dependencies: {str(e)}")
    print("Please run the dependencies installation to use caption features")

# Check if required dependencies are available
DEPENDENCIES_AVAILABLE = True
try:
    import numpy as np
    import moviepy.editor as mp
    from PIL import Image, ImageDraw, ImageFont
    # Import typography effects module
    try:
        from utils.video.typography_effects_pillow import make_frame_with_typography_effects
        TYPOGRAPHY_EFFECTS_AVAILABLE = True
    except ImportError:
        TYPOGRAPHY_EFFECTS_AVAILABLE = False
        
    # Import advanced typography effects module
    try:
        from utils.video.advanced_typography import make_frame_with_advanced_typography
        ADVANCED_TYPOGRAPHY_AVAILABLE = True
    except ImportError:
        ADVANCED_TYPOGRAPHY_AVAILABLE = False
except ImportError:
    DEPENDENCIES_AVAILABLE = False

# Helper function to get text size compatible with all Pillow versions
def get_text_size(draw, text, font):
    """
    Get text size in a way that works with older and newer versions of Pillow
    
    Args:
        draw: ImageDraw object
        text: Text string
        font: Font to use
        
    Returns:
        tuple: (width, height) of text
    """
    try:
        # Try newer Pillow 10.0+ method first
        return draw.textbbox((0, 0), text, font=font)[2:]
    except (AttributeError, TypeError):
        try:
            # Fall back to older method
            return draw.textsize(text, font=font)
        except (AttributeError, TypeError):
            # Last resort fallback - estimate based on font size
            return (len(text) * font.size * 0.6, font.size * 1.2)

def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    
    try:
        import moviepy.editor as mp
    except ImportError:
        missing.append("moviepy")
    
    # Check if any transcription engine is available
    transcription_available = False
    try:
        from utils.audio.transcription import check_module_availability
        # Check whisper
        if check_module_availability("whisper"):
            transcription_available = True
        # Check vosk
        elif check_module_availability("vosk"):
            transcription_available = True
    except ImportError:
        # Fallback check for whisper directly
        try:
            import whisper
            transcription_available = True
        except ImportError:
            pass
    
    if not transcription_available:
        missing.append("transcription (whisper or vosk)")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")
    
    # Check ffmpeg installation
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode != 0:
            missing.append("ffmpeg")
    except:
        missing.append("ffmpeg")
    
    return {
        "all_available": len(missing) == 0,
        "missing": missing
    }

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

@error_handler
def transcribe_video(video_path, model_size="base", engine="auto"):
    """
    Transcribe video audio to text with timestamps
    
    Args:
        video_path: Path to the video file
        model_size: Model size for Whisper (tiny, base, small, medium, large)
        engine: Transcription engine to use ("whisper", "vosk", or "auto")
        
    Returns:
        dict: Results containing transcript with word-level timing
    """
    if not DEPENDENCIES_AVAILABLE or not TRANSCRIPTION_AVAILABLE:
        return {"status": "error", "message": "Required dependencies not available"}
    
    try:
        # Validate the video path
        if not video_path:
            return {"status": "error", "message": "No video path provided"}
            
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video file not found: {video_path}"}
            
        # Check if the new transcription API is available
        try:
            from utils.audio.transcription import transcribe_video as transcription_func
            print(f"Using transcription API with engine={engine}, model_size={model_size}")
            
            # Call the transcription API
            result = transcription_func(
                video_path, 
                engine=engine, 
                model_size=model_size if engine == "whisper" else None
            )
            
            # Format the result to match the expected output
            if "error" in result:
                return {"status": "error", "message": result["error"]}
            
            # Create a standard response format regardless of engine
            if engine == "vosk" or result.get("engine") == "vosk":
                # Format Vosk results to match the expected whisper format
                segments = result.get("segments", [])
                words = []
                
                for segment in segments:
                    segment_words = segment.get("words", [])
                    for word_info in segment_words:
                        words.append({
                            "word": word_info.get("word", ""),
                            "start": word_info.get("start", 0),
                            "end": word_info.get("end", 0)
                        })
                
                return {
                    "status": "success",
                    "transcript": result.get("text", ""),
                    "segments": segments,
                    "words": words,
                    "engine": "vosk"
                }
            else:
                # Already in Whisper format or compatible
                return {
                    "status": "success",
                    "transcript": result.get("text", ""),
                    "segments": result.get("segments", []),
                    "words": [
                        {
                            "word": word.get("word", ""),
                            "start": word.get("start", 0),
                            "end": word.get("end", 0)
                        }
                        for word in result.get("words", [])
                    ],
                    "engine": "whisper"
                }
                
        except ImportError:
            # Fall back to direct whisper usage
            print(f"Using direct Whisper API with model_size={model_size}")
            import whisper
            
            print(f"Loading Whisper model: {model_size}")
            model = whisper.load_model(model_size)
            
            # Extract audio from video if needed
            temp_dir = tempfile.mkdtemp()
            audio_path = os.path.join(temp_dir, "audio.wav")
            
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                audio_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Transcribe with word-level timestamps
            print(f"Transcribing audio with Whisper...")
            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=True
            )
            
            shutil.rmtree(temp_dir)
            
            return {
                "status": "success",
                "transcript": result["text"],
                "segments": result["segments"],
                "words": [
                    {
                        "word": segment["words"][i]["word"], 
                        "start": segment["words"][i]["start"], 
                        "end": segment["words"][i]["end"]
                    }
                    for segment in result["segments"]
                    for i in range(len(segment["words"]))
                ],
                "engine": "whisper"
            }
            
    except Exception as e:
        return {"status": "error", "message": f"Transcription failed: {str(e)}"}

# Caption style presets
CAPTION_STYLES = {
    "tiktok": {
        "font": "Arial-Bold.ttf",
        "font_size": 40,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 180),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True
    },
    "modern_bold": {
        "font": "Impact.ttf",
        "font_size": 45,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (255, 0, 0, 200),  # Semi-transparent red
        "highlight_padding": 12,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True
    },
    "minimal": {
        "font": "Arial.ttf",
        "font_size": 35,
        "text_color": (255, 255, 255),  # White
        "highlight_color": None,  # No background
        "highlight_padding": 0,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": False,
        "word_by_word": False
    },
    "news": {
        "font": "Georgia.ttf",
        "font_size": 38,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 139, 230),  # Dark blue
        "highlight_padding": 10,
        "position": "bottom",
        "align": "center",
        "shadow": False,
        "animate": False,
        "word_by_word": False
    },
    "social": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (50, 50, 50, 200),  # Dark gray
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True
    },
}

# Add new typography effects constants
TYPOGRAPHY_EFFECTS = {
    "fade": {
        "description": "Fade in/out effect for each word",
        "params": {
            "fade_in_duration": 0.2,  # seconds
            "fade_out_duration": 0.1  # seconds
        }
    },
    "scale": {
        "description": "Scale words up/down for emphasis",
        "params": {
            "min_scale": 0.8,
            "max_scale": 1.5,
            "scale_duration": 0.3  # seconds
        }
    },
    "color_shift": {
        "description": "Shift colors based on word importance",
        "params": {
            "regular_color": (255, 255, 255),  # White
            "emphasis_color": (255, 255, 0),   # Yellow
            "strong_emphasis_color": (255, 150, 0)  # Orange
        }
    },
    "wave": {
        "description": "Words move in a wave pattern",
        "params": {
            "amplitude": 10,  # pixels
            "frequency": 2.0  # cycles per second
        }
    },
    "typewriter": {
        "description": "Words appear one character at a time",
        "params": {
            "chars_per_second": 15
        }
    }
}

# Add advanced typography effects
ADVANCED_TYPOGRAPHY_EFFECTS = {
    "kinetic_typography": {"description": "Words move independently with unique animations"},
    "audio_reactive": {"description": "Text reacts to audio levels in the video"},
    "character_animation": {"description": "Characters animate individually with effects like drop-in, fade-in, and spin-in"}
}

# Update typography effects dictionary with advanced effects
TYPOGRAPHY_EFFECTS.update(ADVANCED_TYPOGRAPHY_EFFECTS)

# Update the caption styles to include typography effects
CAPTION_STYLES.update({
    "dynamic": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 180),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["fade", "scale"]  # List of effects to apply
    },
    "impactful": {
        "font": "Impact.ttf",
        "font_size": 45,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 200),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "center",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["scale", "color_shift"]  # List of effects to apply
    },
    "wave_text": {
        "font": "Arial-Bold.ttf",
        "font_size": 40,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 100, 180),  # Semi-transparent blue
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["wave"]  # List of effects to apply
    },
    "typewriter": {
        "font": "Courier New.ttf",
        "font_size": 38,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 200),  # Semi-transparent black
        "highlight_padding": 12,
        "position": "bottom",
        "align": "center",
        "shadow": False,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["typewriter"]  # List of effects to apply
    }
})

# Add new advanced caption styles
CAPTION_STYLES.update({
    "kinetic": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": None,  # No background
        "highlight_padding": 15,
        "position": "center",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["kinetic_typography"]  # Use kinetic typography effect
    },
    "audio_pulse": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 150),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["audio_reactive"]  # Use audio-reactive effect
    },
    "drop_in": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 180),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["character_animation"],  # Use character animation effect
        "character_effect": "drop_in"  # Specify the character animation type
    },
    "fade_in": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 180),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["character_animation"],  # Use character animation effect
        "character_effect": "fade_in"  # Specify the character animation type
    },
    "spin_in": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": None,  # No background
        "highlight_padding": 15,
        "position": "center",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["character_animation"],  # Use character animation effect
        "character_effect": "spin_in"  # Specify the character animation type
    }
})

# Also add typography effects to some existing styles
CAPTION_STYLES["tiktok"]["typography_effects"] = ["fade"]
CAPTION_STYLES["modern_bold"]["typography_effects"] = ["scale"]
CAPTION_STYLES["social"]["typography_effects"] = ["fade", "color_shift"]

def get_system_font(font_name):
    """Get a system font or default to Arial"""
    import os
    import sys
    
    # Use more reliable system fonts for macOS
    if sys.platform == "darwin":  # macOS
        # Try user-provided font name first
        if font_name and os.path.exists(font_name):
            return font_name
            
        # macOS system fonts that are more reliable
        if font_name in ["Arial-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
            font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if os.path.exists(font_path):
                return font_path
        elif font_name in ["Arial.ttf", "arial.ttf"]:
            font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
            if os.path.exists(font_path):
                return font_path
        elif font_name in ["Impact.ttf", "impact.ttf"]:
            font_path = "/System/Library/Fonts/Supplemental/Impact.ttf"
            if os.path.exists(font_path):
                return font_path
    
        # Fallback system fonts on macOS
        fallbacks = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Geneva.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/Library/Fonts/Arial.ttf"
        ]
        for fallback in fallbacks:
            if os.path.exists(fallback):
                return fallback
        return "/System/Library/Fonts/Helvetica.ttc"
        
    # Windows paths
    elif sys.platform == "win32":  # Windows
        font_dir = "C:\\Windows\\Fonts"
        if font_name in ["Arial-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
            return os.path.join(font_dir, "arialbd.ttf")
        elif font_name in ["Arial.ttf", "arial.ttf"]:
            return os.path.join(font_dir, "arial.ttf")
        elif font_name in ["Impact.ttf", "impact.ttf"]:
            return os.path.join(font_dir, "impact.ttf")
        else:
            # Fallback to Arial
            return os.path.join(font_dir, "arial.ttf")
    
    # Linux and others
    else:
        # Try to use DejaVu fonts which are commonly available
        if font_name in ["Arial-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        elif font_name in ["Arial.ttf", "arial.ttf"]:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        elif font_name in ["Impact.ttf", "impact.ttf"]:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        else:
            # Fallback
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Define dream animation styles for word-by-word captioning
DREAM_ANIMATION_STYLES = {
    "word_by_word": {
        "name": "Word by Word",
        "description": "Words appear one by one as they are spoken"
    },
    "fade_in_out": {
        "name": "Fade In/Out", 
        "description": "Words fade in as they are spoken and fade out after"
    },
    "scale_pulse": {
        "name": "Scale Pulse",
        "description": "Words scale up when spoken for emphasis"
    },
    "color_highlight": {
        "name": "Color Highlight",
        "description": "Current words are highlighted with a different color"
    }
}

# Modified function to support animation styles
def make_frame_with_text(frame_img, text, words_with_times, current_time, style, effect_params=None, animation_style=None):
    """
    Create a frame with text overlay using the specified style
    
    Args:
        frame_img: The frame image as a numpy array
        text: The text to display
        words_with_times: List of word timing info
        current_time: Current time in the video
        style: The caption style to use
        effect_params: Optional parameters for effects
        animation_style: Animation style for word-by-word effects
        
    Returns:
        numpy array: The frame with text overlay
    """
    # If no animation style specified, use traditional caption rendering without recursion
    if not animation_style or animation_style not in DREAM_ANIMATION_STYLES:
        # Don't call add_caption_to_frame as it would create an infinite recursion
        # Instead implement the basic caption logic here
        if not DEPENDENCIES_AVAILABLE:
            return frame_img
        
        try:
            # Create a PIL image from the frame
            frame_pil = Image.fromarray(frame_img)
            
            # Create a transparent overlay for text
            overlay = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Get style parameters
            if isinstance(style, dict):
                style_params = style
            else:
                style_params = get_caption_style(style)
            
            # Get font information
            font_path = style_params.get("font_path", get_system_font("Arial"))
            font_size = style_params.get("font_size", 36)
            font_color = style_params.get("font_color", "#FFFFFF")
            stroke_width = style_params.get("stroke_width", 2)
            stroke_color = style_params.get("stroke_color", "#000000")
            
            # Load font
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                print(f"Warning: Error loading font: {e}")
                font = ImageFont.load_default()
            
            # Get text dimensions
            text_width, text_height = get_text_size(draw, text, font)
            
            # Calculate position
            text_x = (frame_pil.width - text_width) // 2
            text_y = frame_pil.height - text_height - style_params.get("bottom_margin", 50)
            
            # Draw text
            draw.text((text_x, text_y), text, font=font, fill=font_color, 
                    stroke_width=stroke_width, stroke_fill=stroke_color)
            
            # Composite the overlay on the frame
            frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
            return np.array(frame_pil.convert('RGB'))
        except Exception as e:
            print(f"Error in make_frame_with_text: {e}")
            return frame_img
    
    # Process with dream animation style
    return add_animated_caption_to_frame(frame_img, text, words_with_times, current_time, style, animation_style, effect_params)

# New function to handle dream animation styles
def add_animated_caption_to_frame(frame_img, text, words_with_times, current_time, style, animation_style, effect_params=None):
    """
    Add animated captions to the frame using dream animation styles
    
    Args:
        frame_img: The frame image as a numpy array
        text: The text to display
        words_with_times: List of word timing info
        current_time: Current time in the video
        style: The caption style to use (string name or dictionary of style parameters)
        animation_style: The animation style to use
        effect_params: Optional parameters for effects, can include custom style parameters
        
    Returns:
        numpy array: The frame with animated captions
    """
    if not DEPENDENCIES_AVAILABLE:
        return frame_img
    
    # Get style parameters
    if isinstance(style, dict):
        # If style is already a dictionary, use it directly
        style_params = style
    else:
        # Otherwise get the style by name
        style_params = get_caption_style(style)
    
    # If we have custom parameters in effect_params, apply them
    if effect_params and isinstance(effect_params, dict):
        # Create a copy of style_params to avoid modifying the original
        if style_params:
            style_params = style_params.copy()
        else:
            style_params = {}
        
        # Update with custom parameters
        style_params.update(effect_params)
    
    if not style_params:
        return frame_img
    
    # Create a copy of the frame
    frame_pil = Image.fromarray(frame_img)
    
    # Create a transparent overlay for text
    overlay = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Get font information
    font_path = style_params.get("font_path", get_system_font("Arial"))
    font_size = style_params.get("font_size", 36)
    font_color = style_params.get("font_color", "#FFFFFF")
    stroke_width = style_params.get("stroke_width", 2)
    stroke_color = style_params.get("stroke_color", "#000000")
    
    # Load font
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"Warning: Error loading font: {e}")
        font = ImageFont.load_default()
    
    # If no words with timing info, just show the text centered
    if not words_with_times:
        # Get text dimensions and position
        text_width, text_height = get_text_size(draw, text, font)
        text_x = (frame_pil.width - text_width) // 2
        text_y = frame_pil.height - text_height - style_params.get("bottom_margin", 50)
        
        # Draw text
        draw.text((text_x, text_y), text, font=font, fill=font_color, 
                  stroke_width=stroke_width, stroke_fill=stroke_color)
        
        # Composite the overlay on the frame
        frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
        return np.array(frame_pil.convert('RGB'))
    
    # Process words with timing
    active_words = []
    pending_words = []
    
    # Calculate total width and height for positioning
    total_text = " ".join([w["word"] for w in words_with_times])
    total_width, total_height = get_text_size(draw, total_text, font)
    
    # Calculate the starting position for the text block
    start_x = (frame_pil.width - total_width) // 2
    start_y = frame_pil.height - total_height - style_params.get("bottom_margin", 50)
    
    # Get position information from style_params
    position = style_params.get("position", "bottom")
    if position == "custom":
        # Get custom position as fractions of the frame dimensions
        h_pos = style_params.get("horizontal_pos", 0.5)  # Default to center
        v_pos = style_params.get("vertical_pos", 0.8)    # Default to near bottom
        
        # Calculate starting position in pixels
        start_x = int(frame_pil.width * h_pos - (total_width / 2))
        start_y = int(frame_pil.height * v_pos - (total_height / 2))
        
        # Update x_pos with new starting position
        x_pos = start_x
    else:
        # Use the default bottom positioning (already calculated above)
        pass

    # Check if we should draw a text box background
    show_textbox = style_params.get("show_textbox", False)
    if show_textbox:
        # Get textbox opacity
        opacity = int(255 * style_params.get("textbox_opacity", 0.7))
        
        # Get textbox color with opacity
        bg_color = style_params.get("highlight_color", (0, 0, 0))
        
        # If bg_color is a tuple, ensure it has alpha
        if isinstance(bg_color, tuple):
            if len(bg_color) == 3:
                bg_color = bg_color + (opacity,)
            elif len(bg_color) == 4:
                # Replace alpha with our calculated opacity
                bg_color = bg_color[:3] + (opacity,)
        else:
            # Default to semi-transparent black
            bg_color = (0, 0, 0, opacity)
        
        padding = 15
        
        # Draw rounded rectangle background for the entire text
        draw.rounded_rectangle(
            [start_x - padding, start_y - padding, 
            start_x + total_width + padding, start_y + total_height + padding],
            radius=10,
            fill=bg_color
        )

    # Process each word
    x_pos = start_x
    
    # Handle single word focus animation separately
    if animation_style == "single_word_focus":
        # Find the current word being spoken
        current_word = None
        current_word_text = ""
        
        for word_info in words_with_times:
            word = word_info["word"]
            word_start = word_info["start"] 
            word_end = word_info["end"]
            
            # Check if this is the current word
            if word_start <= current_time <= word_end:
                current_word = word_info
                current_word_text = word
                break
        
        # If we found a current word, display only that word
        if current_word:
            # Calculate the position for the centered single word
            word_width, word_height = get_text_size(draw, current_word_text, font)
            
            # Get position from style parameters
            position = style_params.get("position", "bottom")
            
            if position == "custom":
                # Get custom position from style parameters (as fractions of frame dimensions)
                h_pos = style_params.get("horizontal_pos", 0.5)  # Default to center
                v_pos = style_params.get("vertical_pos", 0.8)    # Default to near bottom
                
                # Calculate pixel coordinates
                word_x = int(frame_pil.width * h_pos - (word_width / 2))
                word_y = int(frame_pil.height * v_pos - (word_height / 2))
            else:
                # Default bottom positioning
                word_x = (frame_pil.width - word_width) // 2
                word_y = frame_pil.height - word_height - style_params.get("bottom_margin", 50)
            
            # Make the word larger for emphasis
            large_font_size = int(font_size * 1.5)  # 50% larger
            try:
                large_font = ImageFont.truetype(font_path, large_font_size)
            except Exception as e:
                print(f"Warning: Error loading font: {e}")
                large_font = font
                
            # Get new dimensions with the larger font
            word_width, word_height = get_text_size(draw, current_word_text, large_font)
            
            # Recalculate position with new dimensions
            if position == "custom":
                word_x = int(frame_pil.width * h_pos - (word_width / 2))
                word_y = int(frame_pil.height * v_pos - (word_height / 2))
            else:
                word_x = (frame_pil.width - word_width) // 2
                word_y = frame_pil.height - word_height - style_params.get("bottom_margin", 50)
            
            # Draw text with a highlight background if requested
            show_textbox = style_params.get("show_textbox", False)
            if show_textbox:
                # Get textbox opacity
                opacity = int(255 * style_params.get("textbox_opacity", 0.7))
                
                # Get textbox color with opacity
                highlight_color = style_params.get("highlight_color", (0, 0, 0))
                
                # If highlight_color is a tuple, ensure it has alpha
                if isinstance(highlight_color, tuple):
                    if len(highlight_color) == 3:
                        highlight_color = highlight_color + (opacity,)
                    elif len(highlight_color) == 4:
                        # Replace alpha with our calculated opacity
                        highlight_color = highlight_color[:3] + (opacity,)
                else:
                    # Default to semi-transparent black
                    highlight_color = (0, 0, 0, opacity)
                
                padding = 20
                
                # Draw rounded rectangle background
                draw.rounded_rectangle(
                    [word_x - padding, word_y - padding, 
                    word_x + word_width + padding, word_y + word_height + padding],
                    radius=12,
                    fill=highlight_color
                )
            
            # Draw the word with the larger font
            draw.text(
                (word_x, word_y), 
                current_word_text, 
                font=large_font, 
                fill=font_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
            
            # Composite the overlay on the frame
            frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
            return np.array(frame_pil.convert('RGB'))
            
        # If no current word, return the original frame
        return frame_img
    
    # For other animation styles, continue with the existing code
    for word_info in words_with_times:
        word = word_info["word"]
        word_start = word_info["start"] 
        word_end = word_info["end"]
        
        # Check if this word should be visible
        is_active = word_start <= current_time and (
            animation_style == "word_by_word" or current_time <= word_end + 0.5
        )
        
        # Get word dimensions
        word_width, word_height = get_text_size(draw, word + " ", font)
        
        if is_active:
            # Apply animation style
            if animation_style == "word_by_word":
                # Simply display the word
                alpha = 255
                scale = 1.0
                color = font_color
                
            elif animation_style == "fade_in_out":
                # Calculate fade in/out
                if current_time < word_start + 0.3:
                    # Fade in
                    progress = (current_time - word_start) / 0.3
                    alpha = int(255 * progress)
                elif current_time > word_end:
                    # Fade out
                    progress = 1.0 - min(1.0, (current_time - word_end) / 0.5)
                    alpha = int(255 * progress)
                else:
                    # Fully visible
                    alpha = 255
                
                scale = 1.0
                color = font_color
                
            elif animation_style == "scale_pulse":
                # Scale up when the word is first spoken
                # Add safety check to avoid division by zero or negative scale
                min_scale = 0.01  # Prevent zero or negative scale
                if current_time < word_start + 0.3:
                    # Scale up
                    progress = (current_time - word_start) / 0.3
                    # Ensure scale is within reasonable bounds
                    scale = max(min_scale, 1.0 + (0.5 * (1.0 - progress)))
                elif current_time > word_end:
                    # Scale down when word is done
                    progress = 1.0 - min(1.0, (current_time - word_end) / 0.5)
                    # Ensure scale is at least the minimum value
                    scale = max(min_scale, 1.0 * progress)
                else:
                    # Normal size
                    scale = 1.0
                
                alpha = 255
                color = font_color
                
            elif animation_style == "color_highlight":
                # Change color for the current word
                alpha = 255
                scale = 1.0
                
                # Determine if this is the current word being spoken
                is_current = (word_start <= current_time <= word_end)
                
                if is_current:
                    # Use highlight color
                    highlight_color = style_params.get("highlight_color", "#FFFF00")  # Yellow highlight by default
                    
                    # Handle different color formats
                    if isinstance(highlight_color, str) and highlight_color.startswith("#"):
                        # Convert hex to RGB
                        if len(highlight_color) == 7:  # #RRGGBB
                            r = int(highlight_color[1:3], 16)
                            g = int(highlight_color[3:5], 16)
                            b = int(highlight_color[5:7], 16)
                            color = (r, g, b, alpha)
                        else:
                            # Default to yellow if invalid format
                            color = (255, 255, 0, alpha)
                    elif isinstance(highlight_color, tuple):
                        # Use the tuple directly
                        if len(highlight_color) == 3:
                            color = highlight_color + (alpha,)
                        else:
                            color = highlight_color
                    else:
                        # Default to yellow
                        color = (255, 255, 0, alpha)
                else:
                    # Use normal color
                    if isinstance(font_color, str) and font_color.startswith("#"):
                        # Convert hex to RGB
                        if len(font_color) == 7:  # #RRGGBB
                            r = int(font_color[1:3], 16)
                            g = int(font_color[3:5], 16)
                            b = int(font_color[5:7], 16)
                            color = (r, g, b, alpha)
                        else:
                            # Default to white if invalid format
                            color = (255, 255, 255, alpha)
                    elif isinstance(font_color, tuple):
                        # Use the tuple directly
                        if len(font_color) == 3:
                            color = font_color + (alpha,)
                        else:
                            color = font_color
                    else:
                        # Default to white
                        color = (255, 255, 255, alpha)
            
            # Apply the effects
            if scale != 1.0:
                # Scale the font for this word
                scaled_font_size = int(font_size * scale)
                try:
                    scaled_font = ImageFont.truetype(font_path, scaled_font_size)
                except Exception as e:
                    print(f"Warning: Error loading font: {e}")
                    scaled_font = font
                
                # Get new dimensions
                try:
                    new_width, new_height = get_text_size(draw, word + " ", scaled_font)
                except Exception as e:
                    # Fallback if text size calculation fails
                    print(f"Warning: Error calculating text size: {e}")
                    new_width, new_height = word_width, word_height
                
                # Adjust position to keep text baseline aligned
                y_offset = (word_height - new_height) // 2
                
                # Draw the scaled word
                draw.text(
                    (x_pos, start_y + y_offset), 
                    word + " ", 
                    font=scaled_font, 
                    fill=color, 
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color
                )
                
                # Update position
                x_pos += new_width
            else:
                # Draw the word with the specified alpha
                draw.text(
                    (x_pos, start_y), 
                    word + " ", 
                    font=font, 
                    fill=color, 
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color
                )
                
                # Update position
                x_pos += word_width
        else:
            # Skip this word but update position
            x_pos += word_width
    
    # Composite the overlay on the frame
    frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
    return np.array(frame_pil.convert('RGB'))

def add_caption_to_frame(frame, text, word_info, current_time, style, effect_params=None):
    """Add caption to a single video frame with current word timing"""
    try:
        # Skip if no text or empty text
        if not text or not text.strip():
            return frame
        
        # Handle case where word_info is directly a list of words with timing
        words_with_times = []
        if isinstance(word_info, list):
            # If word_info is already a list of word timings, use it directly
            words_with_times = word_info
        elif isinstance(word_info, dict) and "words_with_times" in word_info:
            # If word_info is a dict with words_with_times key, extract it
            words_with_times = word_info.get("words_with_times", [])
        
        # Instead of calling make_frame_with_text (which would create recursion),
        # implement the basic caption logic directly here
        if not DEPENDENCIES_AVAILABLE:
            return frame
        
        # Create a PIL image from the frame
        frame_pil = Image.fromarray(frame)
        
        # Create a transparent overlay for text
        overlay = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Get style parameters
        if isinstance(style, dict):
            style_params = style
        else:
            style_params = get_caption_style(style)
        
        # Get font information
        font_path = style_params.get("font_path", get_system_font("Arial"))
        font_size = style_params.get("font_size", 36)
        font_color = style_params.get("font_color", "#FFFFFF")
        stroke_width = style_params.get("stroke_width", 2)
        stroke_color = style_params.get("stroke_color", "#000000")
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            print(f"Warning: Error loading font: {e}")
            font = ImageFont.load_default()
        
        # Get text dimensions
        text_width, text_height = get_text_size(draw, text, font)
        
        # Calculate position
        text_x = (frame_pil.width - text_width) // 2
        text_y = frame_pil.height - text_height - style_params.get("bottom_margin", 50)
        
        # Draw text
        draw.text((text_x, text_y), text, font=font, fill=font_color, 
                 stroke_width=stroke_width, stroke_fill=stroke_color)
        
        # Composite the overlay on the frame
        frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
        return np.array(frame_pil.convert('RGB'))
    except Exception as e:
        print(f"Error in add_caption_to_frame: {e}")
        return frame

@error_handler
def add_captions_to_video(video_path, output_path=None, style_name="tiktok", model_size="base", 
                          engine="auto", max_duration=None, custom_style=None, animation_style=None,
                          progress_callback=None):
    """
    Add captions to a video
    
    Args:
        video_path: Path to the video file
        output_path: Path to save the captioned video
        style_name: Name of the caption style to use
        model_size: Model size for Whisper (tiny, base, small, medium, large)
        engine: Transcription engine to use ("whisper", "vosk", or "auto")
        max_duration: Maximum duration to process (None for full video)
        custom_style: Custom style parameters (optional)
        animation_style: Animation style for word-by-word effects (optional)
        progress_callback: Function to call with progress updates
        
    Returns:
        dict: Results with status and output path
    """
    if not DEPENDENCIES_AVAILABLE:
        return {"status": "error", "message": "Required dependencies not available"}
    
    try:
        # Update progress if callback provided
        def update_progress(progress, message):
            if progress_callback:
                progress_callback(progress, message)
            else:
                print(f"Progress: {progress:.1%} - {message}")
        
        # Validate the video path
        if not video_path:
            return {"status": "error", "message": "No video path provided"}
            
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video file not found: {video_path}"}
        
        # Set default output path if not provided
        if not output_path:
            output_dir = os.path.join(os.path.dirname(video_path), "captioned")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"captioned_{os.path.basename(video_path)}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        update_progress(0.1, "Loading video...")
        
        # Load the video
        video = mp.VideoFileClip(video_path)
        
        # Apply max duration limit if specified
        if max_duration is not None and max_duration > 0:
            video = video.subclip(0, min(video.duration, max_duration))
        
        update_progress(0.2, "Transcribing audio...")
        
        # Transcribe the video
        transcription = transcribe_video(video_path, model_size=model_size, engine=engine)
        
        if "error" in transcription:
            return {"status": "error", "message": transcription["error"]}
        
        update_progress(0.3, "Processing transcript...")
        
        # Get the words with timing
        words_with_times = []
        
        for word in transcription.get("words", []):
            words_with_times.append({
                "word": word["word"],
                "start": word["start"],
                "end": word["end"]
            })
        
        # If no words were found, try to use segments instead
        if not words_with_times and "segments" in transcription:
            for segment in transcription["segments"]:
                words_with_times.append({
                    "word": segment["text"],
                    "start": segment["start"],
                    "end": segment["end"]
                })
        
        # If still no words, return an error
        if not words_with_times:
            return {"status": "error", "message": "No speech detected in the video"}
        
        update_progress(0.4, "Generating captions...")
        
        # Get the caption style
        style = get_caption_style(style_name, custom_style)
        
        # Group words into caption segments for display
        caption_segments = []
        current_segment = {
            "words": [],
            "start": words_with_times[0]["start"],
            "end": words_with_times[0]["end"],
            "text": ""
        }
        
        max_words_per_segment = style.get("max_words_per_segment", 7)
        min_segment_duration = style.get("min_segment_duration", 1.0)
        
        for word_info in words_with_times:
            # Check if we should start a new segment
            if (len(current_segment["words"]) >= max_words_per_segment or
                (current_segment["words"] and 
                 word_info["start"] - current_segment["end"] > style.get("segment_break_threshold", 1.0))):
                
                # Finalize the current segment
                if current_segment["words"]:
                    current_segment["text"] = " ".join([w["word"] for w in current_segment["words"]])
                    caption_segments.append(current_segment)
                
                # Start a new segment
                current_segment = {
                    "words": [],
                    "start": word_info["start"],
                    "end": word_info["end"],
                    "text": ""
                }
            
            # Add the word to the current segment
            current_segment["words"].append(word_info)
            current_segment["end"] = word_info["end"]
        
        # Add the last segment if it has words
        if current_segment["words"]:
            current_segment["text"] = " ".join([w["word"] for w in current_segment["words"]])
            caption_segments.append(current_segment)
        
        update_progress(0.5, "Applying captions to video...")
        
        # Define function to create caption for a frame
        def create_caption_frame(get_frame_func_or_img, t):
            # Handle both frame functions and direct numpy arrays
            if callable(get_frame_func_or_img):
                frame_img = get_frame_func_or_img(t)
            else:
                frame_img = get_frame_func_or_img
            # Find the currently active caption segment
            active_segment = None
            for segment in caption_segments:
                if segment["start"] <= t <= segment["end"] + style.get("segment_end_offset", 0.5):
                    active_segment = segment
                    break
            
            # If no active segment, return the frame as is
            if not active_segment:
                return frame_img
            
            # Add captions to the frame
            if animation_style:
                # Use word-by-word animation
                return make_frame_with_text(
                    frame_img, 
                    active_segment["text"],
                    active_segment["words"], 
                    t, 
                    style_name,
                    animation_style=animation_style
                )
            else:
                # Use standard captions
                return make_frame_with_text(
                    frame_img, 
                    active_segment["text"],
                    active_segment["words"], 
                    t,
                    style
                )
        
        # Apply captions to the video
        captioned_video = video.fl(create_caption_frame)
        
        update_progress(0.8, "Writing output video...")
        
        # Write the output video
        captioned_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=tempfile.NamedTemporaryFile(suffix='.m4a', delete=False).name,
            remove_temp=True,
            threads=2,
            logger=None
        )
        
        # Clean up
        video.close()
        captioned_video.close()
        
        update_progress(1.0, "Caption generation complete!")
        
        return {
            "status": "success",
            "output_path": output_path
        }
    except Exception as e:
        print(f"Error adding captions: {str(e)}")
        print(traceback.format_exc())
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

def get_available_caption_styles():
    """Return a list of available caption styles with details"""
    return {name: {k: v for k, v in style.items() 
        if k not in ['font']}  # Exclude font path for cleaner output
            for name, style in CAPTION_STYLES.items()}

def get_caption_style(style_name=None, custom_style=None):
    """
    Get caption style by name or custom parameters
    
    Args:
        style_name: Name of caption style
        custom_style: Custom style parameters
        
    Returns:
        dict: Caption style parameters
    """
    # Use custom style if provided
    if custom_style is not None:
        return custom_style
    
    # Use default style if no style name provided
    if style_name is None or style_name not in CAPTION_STYLES:
        return CAPTION_STYLES["tiktok"]
    
    # Return the style
    return CAPTION_STYLES[style_name]

if __name__ == "__main__":
    # Simple command-line interface for testing
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
        # Optional style parameter
        style = "tiktok"
        if len(sys.argv) > 2:
            style = sys.argv[2]
        
        # Check for help flag
        if video_path in ["-h", "--help"]:
            print("Usage: python captions.py [video_path] [style]")
            print(f"Available styles: {', '.join(CAPTION_STYLES.keys())}")
            sys.exit(0)
        
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            sys.exit(1)
        
        # Check dependencies
        deps = check_dependencies()
        if not deps["all_available"]:
            print(f"Missing dependencies: {', '.join(deps['missing'])}")
            print("Please install required packages first.")
            sys.exit(1)
        
        # Add captions
        result = add_captions_to_video(video_path, style_name=style)
        
        if result["status"] == "success":
            print(f"Captions added successfully!")
            print(f"Output: {result['output_path']}")
        else:
            print(f"Error adding captions: {result['message']}")
    else:
        print("Please provide a video file path.")
        print("Usage: python captions.py [video_path] [style]") 