"""
Ollama API client for integrating LLM capabilities using the mistral:7b-instruct-v0.3-q4_K_M model.
Provides functions for text analysis, logical segmentation, and B-Roll prompt generation.
"""

import json
import requests
from typing import List, Dict, Any, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default Ollama settings
DEFAULT_MODEL = "mistral:7b-instruct-v0.3-q4_K_M"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 120  # seconds

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(
        self, 
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST, 
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Initialize the Ollama client.
        
        Args:
            model: Name of the Ollama model to use
            host: Host URL for Ollama API
            temperature: Temperature for generation (0.0 to 1.0)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.host = host
        self.temperature = temperature
        self.timeout = timeout
        self.api_generate_url = f"{host}/api/generate"
        
        # Test connection on initialization
        self.is_available = self._test_connection()
        if not self.is_available:
            logger.warning(f"Ollama is not available at {host}. Some features will be limited.")
    
    def _test_connection(self) -> bool:
        """Test if Ollama API is available."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error connecting to Ollama: {str(e)}")
            return False
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[bool, str]:
        """
        Generate a response from Ollama model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            
        Returns:
            Tuple of (success, response_text)
        """
        if not self.is_available:
            return False, "Ollama service is not available."
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                self.api_generate_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return True, response.json().get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return False, f"API error: {response.status_code}"
                
        except requests.RequestException as e:
            logger.error(f"Request to Ollama failed: {str(e)}")
            return False, f"Request failed: {str(e)}"
    
    def segment_text_logically(self, transcript: str, min_segment_length: int = 5, max_segment_length: int = 30) -> List[Dict[str, Any]]:
        """
        Segment a transcript into logical chunks using the LLM.
        
        Args:
            transcript: Full transcript text
            min_segment_length: Minimum words per segment
            max_segment_length: Maximum words per segment
            
        Returns:
            List of segmented text chunks with metadata
        """
        system_prompt = """
        You are an expert video editor who specializes in breaking down transcripts into logical segments.
        Each segment should:
        1. Complete a thought or point
        2. End at a natural pause in speech
        3. Be coherent and standalone
        4. Be neither too short nor too long

        Split the transcript at the places where it makes most sense semantically.
        Don't split in the middle of a sentence unless the sentence is very long.
        Don't be influenced solely by length - focus on logical completeness.
        """
        
        user_prompt = f"""
        Please segment the following transcript into logical chunks.
        Each chunk should represent a complete thought or point and should be reasonable for a B-Roll segment.
        
        Guidelines:
        - Aim for segments between {min_segment_length} and {max_segment_length} words
        - Split at natural pauses and thought boundaries
        - Each segment should make sense on its own
        - Return the segments as a numbered list where each item is a complete segment
        
        Transcript:
        {transcript}
        
        Output the segmented transcript as a numbered list. ONLY include the segments, no additional text.
        """
        
        success, response = self.generate(user_prompt, system_prompt)
        
        if not success:
            logger.error(f"Failed to segment transcript: {response}")
            # Fallback to simple splitting
            words = transcript.split()
            avg_length = (min_segment_length + max_segment_length) // 2
            segments = []
            
            for i in range(0, len(words), avg_length):
                segment = " ".join(words[i:i+avg_length])
                segments.append({"content": segment})
            
            return segments
        
        # Parse the numbered list response
        segments = []
        
        # Handle both numbered format or plain text
        if "1." in response or "1)" in response:
            # Extract numbered segments
            import re
            pattern = r'\d+[\.\)]\s+(.*?)(?=\d+[\.\)]|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)
            
            for match in matches:
                segments.append({
                    "content": match.strip()
                })
        else:
            # Split by paragraphs as fallback
            paragraphs = [p.strip() for p in response.split('\n') if p.strip()]
            for paragraph in paragraphs:
                segments.append({
                    "content": paragraph
                })
        
        return segments
    
    def generate_broll_prompt(self, segment_text: str, theme: str = "", style: str = "photorealistic") -> Tuple[bool, str]:
        """
        Generate a B-Roll prompt that matches the A-Roll segment content.
        
        Args:
            segment_text: Text of the A-Roll segment
            theme: Optional theme to guide B-Roll content
            style: Visual style for the B-Roll
            
        Returns:
            Tuple of (success, broll_prompt)
        """
        system_prompt = """
        You are an expert visual director who creates compelling B-Roll prompts for video content.
        The B-Roll should visualize exactly what's being said in the A-Roll segment.
        Create detailed, vivid descriptions that would be perfect for image generation models.
        Focus on creating visuals that complement and enhance the spoken content.
        """
        
        theme_context = f"The overall theme of the video is: {theme}. " if theme else ""
        
        user_prompt = f"""
        Create a detailed B-Roll visual prompt that perfectly illustrates the following A-Roll segment.
        
        {theme_context}The A-Roll segment says:
        "{segment_text}"
        
        Your B-Roll prompt should:
        1. Visualize exactly what's being discussed
        2. Be highly detailed and specific
        3. Include setting, mood, lighting, and key elements
        4. Use the style: {style}
        5. Be 1-3 sentences, focus on the most important visual elements
        
        Provide ONLY the B-Roll prompt text, no explanations or additional content.
        """
        
        return self.generate(user_prompt, system_prompt) 