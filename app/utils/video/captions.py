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
    },
    "single_word_focus": {
        "name": "Single Word Focus",
        "description": "Only the current word being spoken is displayed, with emphasis"
    }
}

# Modified function to support animation styles but avoid recursion
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
    if not DEPENDENCIES_AVAILABLE:
        return frame_img
    
    try:
        # Get style parameters
        if isinstance(style, dict):
            style_params = style
        else:
            style_params = get_caption_style(style)
        
        # Process animation style
        if animation_style and animation_style in DREAM_ANIMATION_STYLES:
            # Handle animated caption styles directly here instead of calling another function
            return render_animated_caption(frame_img, text, words_with_times, current_time, style_params, animation_style, effect_params)
        
        # Basic non-animated caption
        return render_basic_caption(frame_img, text, style_params)
    except Exception as e:
        print(f"Error in make_frame_with_text: {e}")
        return frame_img

def render_basic_caption(frame_img, text, style_params):
    """Render a basic caption on a frame without animation"""
    try:
        print(f"render_basic_caption called with text: {text[:30]}...")
        
        # Create a PIL image from the frame
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
        
        print(f"Using font: {font_path}, size: {font_size}")
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            print(f"Warning: Error loading font: {e}")
            font = ImageFont.load_default()
        
        # Get text dimensions
        text_width, text_height = get_text_size(draw, text, font)
        print(f"Text dimensions: {text_width}x{text_height}")
        
        # Get position information
        position = style_params.get("position", "bottom")
        print(f"Position: {position}")
        
        if position == "custom":
            # Get custom position as fractions of the frame dimensions
            h_pos = style_params.get("horizontal_pos", 0.5)  # Default to center
            v_pos = style_params.get("vertical_pos", 0.8)    # Default to near bottom
            
            # Calculate position in pixels
            text_x = int(frame_pil.width * h_pos - (text_width / 2))
            text_y = int(frame_pil.height * v_pos - (text_height / 2))
            print(f"Custom position: {text_x}, {text_y}")
        else:
            # Default positioning at bottom
            text_x = (frame_pil.width - text_width) // 2
            text_y = frame_pil.height - text_height - style_params.get("bottom_margin", 50)
            print(f"Default position: {text_x}, {text_y}")
        
        # Check if we should draw a text box background
        show_textbox = style_params.get("show_textbox", False)
        if show_textbox:
            print("Drawing text box background")
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
            
            # Draw rounded rectangle background
            draw.rounded_rectangle(
                [text_x - padding, text_y - padding, 
                text_x + text_width + padding, text_y + text_height + padding],
                radius=10,
                fill=bg_color
            )
        
        # Draw text
        print(f"Drawing text: {text[:30]}...")
        draw.text(
            (text_x, text_y), 
            text, 
            font=font, 
            fill=font_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color
        )
        
        # Composite the overlay on the frame
        frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
        result = np.array(frame_pil.convert('RGB'))
        print("Basic caption rendering completed successfully")
        return result
    except Exception as e:
        print(f"Error in render_basic_caption: {e}")
        traceback.print_exc()
        return frame_img

def render_animated_caption(frame_img, text, words_with_times, current_time, style_params, animation_style, effect_params=None):
    """
    Render an animated caption on a frame based on the animation style
    All rendering is done directly in this function to avoid recursion
    """
    try:
        if not words_with_times:
            # No word timing info available, fall back to basic caption
            return render_basic_caption(frame_img, text, style_params)
        
        # Create a PIL image from the frame
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
        
        # Calculate total width and height for positioning
        total_text = " ".join([w["word"] for w in words_with_times if isinstance(w, dict) and "word" in w])
        total_width, total_height = get_text_size(draw, total_text, font)
        
        # Calculate the starting position for the text block
        position = style_params.get("position", "bottom")
        
        if position == "custom":
            # Get custom position as fractions of the frame dimensions
            h_pos = style_params.get("horizontal_pos", 0.5)  # Default to center
            v_pos = style_params.get("vertical_pos", 0.8)    # Default to near bottom
            
            # Calculate starting position in pixels
            start_x = int(frame_pil.width * h_pos - (total_width / 2))
            start_y = int(frame_pil.height * v_pos - (total_height / 2))
        else:
            # Default bottom positioning
            start_x = (frame_pil.width - total_width) // 2
            start_y = frame_pil.height - total_height - style_params.get("bottom_margin", 50)
        
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
        
        # Initialize current_word variables before conditionals to avoid reference errors
        current_word = None
        current_word_text = ""
        current_word_index = -1
        
        # Handle single word focus animation separately
        if animation_style == "single_word_focus":
            # Initialize storage for word persistence
            if not hasattr(render_animated_caption, "prev_word"):
                render_animated_caption.prev_word = None
                render_animated_caption.prev_time = 0
                render_animated_caption.min_display_time = 0.3  # Minimum time to display a word
            
            # First pass: try to find the exact current word
            for i, word_info in enumerate(words_with_times):
                if not isinstance(word_info, dict) or "word" not in word_info or "start" not in word_info or "end" not in word_info:
                    continue
                    
                word = word_info["word"]
                word_start = word_info["start"] 
                word_end = word_info["end"]
                
                # Add a larger buffer to the end time to avoid gaps
                buffer_time = 0.3  # Increased buffer
                
                # Check if this is the current word
                if word_start <= current_time <= (word_end + buffer_time):
                    current_word = word_info
                    current_word_text = word
                    current_word_index = i
                    
                    # Store for persistence
                    render_animated_caption.prev_word = word_info
                    render_animated_caption.prev_time = current_time
                    break
            
            # Second pass: if no word is active, try persistence or find closest
            if not current_word:
                # Check if we can use the previous word (for minimum display time)
                if (render_animated_caption.prev_word and 
                    current_time - render_animated_caption.prev_time < render_animated_caption.min_display_time):
                    current_word = render_animated_caption.prev_word
                    current_word_text = current_word["word"]
                    print(f"Using persisted word '{current_word_text}' at time {current_time:.2f}s")
                else:
                    # Find the closest word in time
                    closest_word = None
                    min_distance = float('inf')
                    
                    for i, word_info in enumerate(words_with_times):
                        if not isinstance(word_info, dict) or "word" not in word_info or "start" not in word_info or "end" not in word_info:
                            continue
                            
                        word_start = word_info["start"]
                        word_end = word_info["end"]
                        
                        # Distance to start and end times
                        start_distance = abs(current_time - word_start)
                        end_distance = abs(current_time - word_end)
                        
                        # Take the minimum distance
                        distance = min(start_distance, end_distance)
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_word = word_info
                            current_word_index = i
                    
                    # Use the closest word if it's within a reasonable time range (0.7 seconds)
                    if closest_word and min_distance < 0.7:
                        current_word = closest_word
                        current_word_text = closest_word["word"]
                        render_animated_caption.prev_word = closest_word
                        render_animated_caption.prev_time = current_time
                        print(f"Using closest word '{current_word_text}' at time {current_time:.2f}s (distance: {min_distance:.2f}s)")
        
            # If we found a current word, display only that word
            if current_word:
                # Determine the font size based on word length
                scale_factor = 1.5  # Default scale factor
                if len(current_word_text) > 10:
                    # Reduce scale for longer words
                    scale_factor = 1.3
                elif len(current_word_text) > 5:
                    scale_factor = 1.4
                
                large_font_size = int(font_size * scale_factor)
                try:
                    large_font = ImageFont.truetype(font_path, large_font_size)
                except Exception as e:
                    print(f"Warning: Error loading font: {e}")
                    large_font = font
                    
                # Get new dimensions with the larger font
                word_width, word_height = get_text_size(draw, current_word_text, large_font)
                
                # Calculate position for the centered single word
                if position == "custom":
                    word_x = int(frame_pil.width * h_pos - (word_width / 2))
                    word_y = int(frame_pil.height * v_pos - (word_height / 2))
                else:
                    word_x = (frame_pil.width - word_width) // 2
                    word_y = frame_pil.height - word_height - style_params.get("bottom_margin", 50)
                
                # Draw text with a highlight background if requested
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
                    
                    # Ensure padding is appropriate for the word size
                    padding = min(30, max(20, int(word_width * 0.1)))  # Between 20-30px based on word width
                    
                    # Draw rounded rectangle background with enough padding
                    try:
                        draw.rounded_rectangle(
                            [word_x - padding, word_y - padding, 
                            word_x + word_width + padding, word_y + word_height + padding],
                            radius=12,
                            fill=highlight_color
                        )
                    except AttributeError:
                        # Fallback for older PIL versions without rounded_rectangle
                        draw.rectangle(
                            [word_x - padding, word_y - padding, 
                            word_x + word_width + padding, word_y + word_height + padding],
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
            else:
                # If no current word and we're at the beginning, show the first word
                if current_time < 1.0 and words_with_times and len(words_with_times) > 0:
                    first_word = words_with_times[0].get("word", "")
                    if first_word:
                        print(f"Showing first word '{first_word}' before official start time")
                        # Create a temporary overlay for the first word
                        temp_overlay = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
                        temp_draw = ImageDraw.Draw(temp_overlay)
                        
                        # Use the same font and rendering logic as above
                        large_font_size = int(font_size * 1.4)
                        try:
                            large_font = ImageFont.truetype(font_path, large_font_size)
                        except Exception:
                            large_font = font
                            
                        word_width, word_height = get_text_size(temp_draw, first_word, large_font)
                        word_x = (frame_pil.width - word_width) // 2
                        word_y = frame_pil.height - word_height - style_params.get("bottom_margin", 50)
                        
                        # Draw text
                        temp_draw.text(
                            (word_x, word_y), 
                            first_word, 
                            font=large_font, 
                            fill=font_color,
                            stroke_width=stroke_width,
                            stroke_fill=stroke_color
                        )
                        
                        # Composite and return
                        frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), temp_overlay)
                        return np.array(frame_pil.convert('RGB'))
                # If no word to display in single_word_focus mode, return the original frame
                return frame_img
        
        # For all other animation styles, show all words with appropriate animation
        else:  # word_by_word, fade_in_out, color_highlight, etc.
            # Default to word-by-word animation (highlight current word)
            current_word_index = -1
            active_words = []
            
            # Find the active word(s) at the current time
            for i, word_info in enumerate(words_with_times):
                if not isinstance(word_info, dict) or "word" not in word_info or "start" not in word_info or "end" not in word_info:
                    continue
                
                word = word_info["word"]
                word_start = word_info["start"]
                word_end = word_info["end"]
                buffer_time = 0.2  # Buffer time to extend word visibility
                
                # For word_by_word, words remain visible after being spoken
                if animation_style == "word_by_word":
                    if word_start <= current_time:
                        active_words.append(word_info)
                        if word_start <= current_time <= (word_end + buffer_time):
                            current_word_index = i
                            current_word = word_info
                # For fade_in_out, only show words around their time window
                elif animation_style == "fade_in_out":
                    # Add fade in/out buffer
                    fade_buffer = 0.5
                    if (word_start - fade_buffer) <= current_time <= (word_end + fade_buffer):
                        active_words.append(word_info)
                        if word_start <= current_time <= word_end:
                            current_word_index = i
                            current_word = word_info
                # For color_highlight, show all words but highlight current one
                elif animation_style == "color_highlight":
                    active_words.append(word_info)
                    if word_start <= current_time <= (word_end + buffer_time):
                        current_word_index = i
                        current_word = word_info
                # Default behavior for other animation styles
                else:
                    if word_start <= current_time:
                        active_words.append(word_info)
                        if word_start <= current_time <= (word_end + buffer_time):
                            current_word_index = i
                            current_word = word_info
            
            # If no words are active and we're at the beginning, show the first word
            if not active_words and current_time < 1.0 and words_with_times:
                active_words.append(words_with_times[0])
            
            # If we have active words, display them
            if active_words:
                # Get text alignment
                align = style_params.get("align", "center")
                
                # Get total text of active words
                active_text = " ".join([w["word"] for w in active_words])
                text_width, text_height = get_text_size(draw, active_text, font)
                
                # Calculate position based on alignment
                if align == "left":
                    text_x = start_x
                elif align == "right":
                    text_x = start_x + (total_width - text_width)
                else:  # center
                    text_x = start_x + ((total_width - text_width) // 2)
                
                text_y = start_y
                
                # Draw background if needed
                if show_textbox:
                    opacity = int(255 * style_params.get("textbox_opacity", 0.7))
                    bg_color = style_params.get("highlight_color", (0, 0, 0))
                    
                    if isinstance(bg_color, tuple):
                        if len(bg_color) == 3:
                            bg_color = bg_color + (opacity,)
                        elif len(bg_color) == 4:
                            bg_color = bg_color[:3] + (opacity,)
                    else:
                        bg_color = (0, 0, 0, opacity)
                    
                    padding = 15
                    
                    try:
                        draw.rounded_rectangle(
                            [text_x - padding, text_y - padding, 
                            text_x + text_width + padding, text_y + text_height + padding],
                            radius=10,
                            fill=bg_color
                        )
                    except AttributeError:
                        draw.rectangle(
                            [text_x - padding, text_y - padding, 
                            text_x + text_width + padding, text_y + text_height + padding],
                            fill=bg_color
                        )
                
                # Draw each word with appropriate styling
                current_x = text_x
                for i, word_info in enumerate(active_words):
                    word = word_info["word"]
                    word_width, word_height = get_text_size(draw, word, font)
                    
                    # Apply special styling for the current word
                    is_current = (i == len(active_words) - 1) if current_word_index == -1 else (word_info == current_word)
                    
                    # Use regular or highlighted color
                    current_font_color = style_params.get("highlight_font_color", (255, 255, 0)) if is_current and animation_style == "color_highlight" else font_color
                    
                    # Draw the word
                    draw.text(
                        (current_x, text_y),
                        word,
                        font=font,
                        fill=current_font_color,
                        stroke_width=stroke_width,
                        stroke_fill=stroke_color
                    )
                    
                    # Add space after word
                    space_width, _ = get_text_size(draw, " ", font)
                    current_x += word_width + space_width
                
                # Composite and return
                frame_pil = Image.alpha_composite(frame_pil.convert('RGBA'), overlay)
                return np.array(frame_pil.convert('RGB'))
    
        # If no words to display, return the original frame
        return frame_img
    except Exception as e:
        print(f"Error in render_animated_caption: {e}")
        traceback.print_exc()
        return frame_img

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
        
        # Get animation style from effect_params if available
        animation_style = None
        if effect_params and isinstance(effect_params, dict):
            animation_style = effect_params.get("animation_style")
        
        # Use make_frame_with_text to handle the rendering (without recursion)
        return make_frame_with_text(
            frame, 
            text, 
            words_with_times, 
            current_time, 
            style, 
            effect_params, 
            animation_style
        )
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
    print(f"\n\n===== Starting add_captions_to_video =====")
    print(f"Input video: {video_path}")
    print(f"Output path: {output_path}")
    print(f"Style: {style_name}")
    print(f"Animation style: {animation_style}")
    
    if not DEPENDENCIES_AVAILABLE:
        print("Required dependencies not available")
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
        
        # Make sure the output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # Check if the output directory is writable
        if not os.access(output_dir, os.W_OK):
            print(f"Warning: Output directory {output_dir} is not writable")
            # Try to make it writable
            try:
                os.chmod(output_dir, 0o755)
                print(f"Changed permissions on {output_dir}")
            except Exception as e:
                print(f"Failed to change permissions: {e}")
                # Try an alternative output path
                alt_output_dir = os.path.join(os.getcwd(), "output")
                os.makedirs(alt_output_dir, exist_ok=True)
                output_path = os.path.join(alt_output_dir, f"captioned_{os.path.basename(video_path)}")
                print(f"Using alternative output path: {output_path}")
        
        print(f"Final output path: {output_path}")
        print(f"Output directory exists: {os.path.exists(os.path.dirname(output_path))}")
        print(f"Output directory is writable: {os.access(os.path.dirname(output_path), os.W_OK)}")
        
        update_progress(0.1, "Loading video...")
        
        # Load the video
        video = mp.VideoFileClip(video_path)
        print(f"Video loaded. Duration: {video.duration:.2f}s, Size: {video.size}")
        
        # Apply max duration limit if specified
        if max_duration is not None and max_duration > 0:
            video = video.subclip(0, min(video.duration, max_duration))
            print(f"Video clipped to {min(video.duration, max_duration):.2f}s")
        
        update_progress(0.2, "Transcribing audio...")
        
        # Transcribe the video
        transcription = transcribe_video(video_path, model_size=model_size, engine=engine)
        
        if "status" in transcription and transcription["status"] == "error":
            return {"status": "error", "message": transcription.get("message", "Unknown transcription error")}
        
        update_progress(0.3, "Processing transcript...")
        
        # Get the words with timing
        words_with_times = []
        
        if "words" in transcription and isinstance(transcription["words"], list):
            for word in transcription["words"]:
                if isinstance(word, dict) and "word" in word and "start" in word and "end" in word:
                    words_with_times.append({
                        "word": word["word"],
                        "start": word["start"],
                        "end": word["end"]
                    })
        
        # If no words were found, try to use segments instead
        if not words_with_times and "segments" in transcription and isinstance(transcription["segments"], list):
            for segment in transcription["segments"]:
                if isinstance(segment, dict) and "text" in segment and "start" in segment and "end" in segment:
                    words_with_times.append({
                        "word": segment["text"],
                        "start": segment["start"],
                        "end": segment["end"]
                    })
        
        # If still no words, return an error
        if not words_with_times:
            return {"status": "error", "message": "No speech detected in the video"}
        
        print(f"Found {len(words_with_times)} words in transcription")
        
        update_progress(0.4, "Generating captions...")
        
        # Get the caption style
        if isinstance(style_name, str):
            style = get_caption_style(style_name)
        else:
            style = style_name  # Assume it's already a style dict
            
        # Apply custom style if provided
        if custom_style:
            if not style:
                style = {}
            for key, value in custom_style.items():
                style[key] = value
        
        print(f"Using style: {style.get('position', 'unknown')}, font_size: {style.get('font_size', 'unknown')}")
        
        # Group words into caption segments for display
        caption_segments = []
        
        if words_with_times:
            current_segment = {
                "words": [],
                "start": words_with_times[0]["start"],
                "end": words_with_times[0]["end"],
                "text": ""
            }
            
            max_words_per_segment = 7
            if isinstance(style, dict):
                max_words_per_segment = style.get("max_words_per_segment", 7)
            
            segment_break_threshold = 1.0
            if isinstance(style, dict):
                segment_break_threshold = style.get("segment_break_threshold", 1.0)
            
            for word_info in words_with_times:
                # Check if we should start a new segment
                if (len(current_segment["words"]) >= max_words_per_segment or
                    (current_segment["words"] and 
                     word_info["start"] - current_segment["end"] > segment_break_threshold)):
                    
                    # Finalize the current segment
                    if current_segment["words"]:
                        current_segment["text"] = " ".join([w["word"] for w in current_segment["words"] 
                                                          if isinstance(w, dict) and "word" in w])
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
                current_segment["text"] = " ".join([w["word"] for w in current_segment["words"] 
                                                  if isinstance(w, dict) and "word" in w])
                caption_segments.append(current_segment)
        
        print(f"Created {len(caption_segments)} caption segments")
        if caption_segments:
            print(f"First segment: {caption_segments[0].get('text', '')[:30]}...")
        
        update_progress(0.5, "Applying captions to video...")
        
        # Define a simpler, more reliable caption frame function
        def caption_frame_maker(get_frame, t):
            try:
                # Get the frame image using the provided function or directly use it if it's already a frame
                if callable(get_frame):
                    frame_img = get_frame(t)
                else:
                    frame_img = get_frame
                    
                # Find active segment
                active_segment = None
                segment_end_offset = 0.5
                if isinstance(style, dict):
                    segment_end_offset = style.get("segment_end_offset", 0.5)
                
                for segment in caption_segments:
                    if segment["start"] <= t <= segment["end"] + segment_end_offset:
                        active_segment = segment
                        break
                
                # If no active segment, return frame as is
                if not active_segment:
                    return frame_img
                
                # Get segment info
                segment_text = active_segment.get("text", "")
                segment_words = active_segment.get("words", [])
                
                # If empty text, return frame as is
                if not segment_text:
                    return frame_img
                
                # Add caption based on animation style
                if animation_style and animation_style in DREAM_ANIMATION_STYLES:
                    # Use direct rendering without function calls
                    return render_animated_caption(
                        frame_img,
                        segment_text,
                        segment_words,
                        t,
                        style,
                        animation_style,
                        None
                    )
                else:
                    # Use basic caption
                    return render_basic_caption(frame_img, segment_text, style)
            except Exception as e:
                print(f"Error in caption_frame_maker at t={t}: {e}")
                traceback.print_exc()
                return frame_img
        
        # Apply the function to each frame
        try:
            print("Starting to apply captions to frames...")
            # Use a more compatible approach by modifying the existing video
            # This is more reliable than creating a new VideoClip
            captioned_video = video.fl(caption_frame_maker)
            
            update_progress(0.8, "Writing output video...")
            print(f"Writing output video to {output_path}")
            
            # Create the final video with captions
            try:
                update_progress(0.9, "Saving video with captions...")
                captioned_video.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=tempfile.NamedTemporaryFile(suffix='.m4a', delete=False).name,
                    remove_temp=True,
                    threads=4,
                    preset="medium",
                    ffmpeg_params=["-crf", "23"],
                    logger=None
                )
                
                # Verify the output file was created
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"Output file successfully created at: {output_path}")
                    print(f"File size: {file_size} bytes")
                    
                    # Additional verification that file is a valid video
                    try:
                        # Import inside this block to ensure it's available
                        from moviepy.editor import VideoFileClip
                        
                        # Just open and get duration to verify it's a valid video
                        verify_clip = VideoFileClip(output_path)
                        duration = verify_clip.duration
                        print(f"Verified video file. Duration: {duration} seconds")
                        verify_clip.close()
                    except Exception as e:
                        print(f"Warning: File was created but may not be a valid video: {e}")
                        # Continue anyway since the file exists
                else:
                    print(f"Error: Output file was not created at: {output_path}")
                    # Try an alternative approach - use absolute path
                    alt_path = os.path.abspath(output_path)
                    print(f"Trying alternative output path: {alt_path}")
                    captioned_video.write_videofile(
                        alt_path,
                        codec="libx264",
                        audio_codec="aac",
                        temp_audiofile=tempfile.NamedTemporaryFile(suffix='.m4a', delete=False).name,
                        remove_temp=True,
                        threads=4,
                        preset="medium",
                        ffmpeg_params=["-crf", "23"],
                        logger=None
                    )
                    
                    if os.path.exists(alt_path):
                        print(f"Success with alternative path. File created at: {alt_path}")
                        output_path = alt_path
                    else:
                        print(f"Failed to create output file even with alternative path.")
                    
            except Exception as e:
                print(f"Error saving video: {e}")
                traceback.print_exc()
                return {
                    "status": "error",
                    "message": f"Error saving video: {str(e)}",
                    "traceback": traceback.format_exc()
                }
            
            update_progress(1.0, "Caption generation complete!")
            print("Caption generation complete!")
            
            return {
                "status": "success",
                "message": "Captions added successfully",
                "output_path": output_path
            }
        except Exception as e:
            print(f"Error in video processing: {str(e)}")
            traceback.print_exc()
            # Make sure to close video objects
            try:
                video.close()
            except Exception:
                pass
            try:
                if 'captioned_video' in locals():
                    captioned_video.close()
            except Exception:
                pass
            
            raise
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