"""
ComfyUI WebSocket integration module for AI Money Printer.
This module provides functions to interact with ComfyUI using WebSockets.
"""

import json
import requests
import websocket
import uuid
import time
import threading
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComfyUIWebSocketClient:
    def __init__(self, server_url: str = "http://100.115.243.42:8000"):
        """
        Initialize ComfyUI WebSocket client.
        
        Args:
            server_url: Base URL of the ComfyUI server
        """
        self.server_url = server_url
        self.ws_url = f"ws{server_url[4:]}/ws" if server_url.startswith('http') else f"ws://{server_url}/ws"
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self.ws_thread = None
        self.callbacks = {}
        self.prompt_map = {}  # Maps prompt_id to client_data
        
    def connect(self) -> bool:
        """
        Connect to ComfyUI WebSocket server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.ws = websocket.create_connection(self.ws_url)
            logger.info(f"Connected to ComfyUI WebSocket server at {self.ws_url}")
            
            # Start WebSocket listener thread
            self.ws_thread = threading.Thread(target=self._ws_listener, daemon=True)
            self.ws_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {str(e)}")
            return False
    
    def disconnect(self):
        """
        Disconnect from ComfyUI WebSocket server.
        """
        if self.ws:
            try:
                self.ws.close()
                logger.info("Disconnected from ComfyUI WebSocket server")
            except Exception as e:
                logger.error(f"Error disconnecting from WebSocket: {str(e)}")
            finally:
                self.ws = None
    
    def submit_workflow(self, 
                        workflow: Dict[str, Any], 
                        extra_data: Optional[Dict[str, Any]] = None, 
                        on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
                        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
                        on_error: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        Submit a workflow to ComfyUI.
        
        Args:
            workflow: ComfyUI workflow dictionary
            extra_data: Extra data to include with the prompt
            on_update: Callback function for status updates
            on_complete: Callback function for completion
            on_error: Callback function for errors
            
        Returns:
            Prompt ID if successful, None otherwise
        """
        # Ensure we have a WebSocket connection
        if not self.ws or not self.ws_thread or not self.ws_thread.is_alive():
            logger.info("WebSocket connection not active, reconnecting...")
            success = self.connect()
            if not success:
                error_msg = "Failed to connect to WebSocket server"
                logger.error(error_msg)
                if on_error:
                    on_error(error_msg)
                return None
        
        try:
            # Prepare the data in the format ComfyUI expects
            data = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            if extra_data:
                data["extra_data"] = extra_data
            
            # Convert to JSON string and then to bytes
            json_data = json.dumps(data).encode('utf-8')
            
            # Send the request directly using requests
            response = requests.post(f"{self.server_url}/prompt", data=json_data)
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                
                if prompt_id:
                    logger.info(f"Workflow submitted with prompt ID: {prompt_id}")
                    
                    # Register callbacks
                    client_data = {
                        "workflow": workflow,
                        "extra_data": extra_data,
                        "on_update": on_update,
                        "on_complete": on_complete,
                        "on_error": on_error,
                        "start_time": time.time(),
                        "status": "queued",
                        "progress": 0,
                        "max_progress": 100,
                        "session_id": self.client_id
                    }
                    
                    self.prompt_map[prompt_id] = client_data
                    
                    return prompt_id
                else:
                    error_msg = "No prompt ID returned"
                    logger.error(error_msg)
                    if on_error:
                        on_error(error_msg)
                    return None
            else:
                error_msg = f"Error submitting workflow: Status code {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                if on_error:
                    on_error(error_msg)
                return None
        
        except Exception as e:
            error_msg = f"Error submitting workflow: {str(e)}"
            logger.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get job history from ComfyUI.
        
        Args:
            limit: Maximum number of history items to return
            
        Returns:
            List of history items
        """
        try:
            response = requests.get(f"{self.server_url}/history", params={"limit": limit})
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting history: Status code {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}")
            return []
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """
        Get image data from ComfyUI server.
        
        Args:
            filename: Image filename
            subfolder: Subfolder within the folder_type
            folder_type: Folder type (output, input, temp)
            
        Returns:
            Image data if successful, None otherwise
        """
        try:
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            response = requests.get(f"{self.server_url}/view", params=data)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Error getting image: Status code {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting image: {str(e)}")
            return None
    
    def save_image(self, 
                  image_data: bytes, 
                  filename: str, 
                  output_dir: Union[str, Path] = None) -> Optional[str]:
        """
        Save image data to file.
        
        Args:
            image_data: Image data
            filename: Filename to save as
            output_dir: Directory to save to (defaults to current directory)
            
        Returns:
            Path to saved file if successful, None otherwise
        """
        try:
            if output_dir is None:
                output_dir = Path.cwd()
            elif isinstance(output_dir, str):
                output_dir = Path(output_dir)
            
            # Create directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            output_path = output_dir / filename
            with open(output_path, "wb") as f:
                f.write(image_data)
            
            logger.info(f"Image saved to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            return None
    
    def get_output_images(self, 
                         prompt_id: str, 
                         output_dir: Union[str, Path] = None,
                         node_id: str = None) -> List[str]:
        """
        Get output images for a completed prompt.
        
        Args:
            prompt_id: Prompt ID
            output_dir: Directory to save images to
            node_id: Node ID to get images from (default is to get all)
            
        Returns:
            List of paths to saved images
        """
        try:
            # Get history for this prompt
            logger.debug(f"Getting output images for prompt ID: {prompt_id}")
            
            # Get the history data
            history_url = f"{self.server_url}/history"
            history_response = requests.get(history_url)
            
            if history_response.status_code != 200:
                logger.error(f"Error getting history: Status code {history_response.status_code}")
                return []
                
            history_data = history_response.json()
            saved_paths = []
            
            # Handle dictionary format (newer ComfyUI versions)
            if isinstance(history_data, dict):
                # Look for exact or partial match in the keys
                for item_id, item_data in history_data.items():
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        logger.info(f"Found matching prompt ID in history: {item_id}")
                        
                        # Get the outputs
                        outputs = item_data.get("outputs", {})
                        
                        # Process all nodes or specific node
                        for node_id_key, node_output in outputs.items():
                            # Skip if we're looking for a specific node and this isn't it
                            if node_id and node_id != node_id_key:
                                continue
                            
                            # Process images - check both 'images' and 'gifs' keys
                            for output_type in ['images', 'gifs']:
                                if output_type in node_output:
                                    logger.info(f"Found {output_type} in node {node_id_key}")
                                    
                                    for image_data in node_output[output_type]:
                                        filename = image_data.get("filename")
                                        subfolder = image_data.get("subfolder", "")
                                        
                                        if not filename:
                                            continue
                                        
                                        logger.info(f"Processing {output_type[:-1]} file: {filename}")
                                        
                                        # Get the image data
                                        image_bytes = self.get_image(filename, subfolder)
                                        if not image_bytes:
                                            logger.warning(f"Failed to get file data for {filename}")
                                            continue
                                        
                                        # Save the image
                                        saved_path = self.save_image(image_bytes, filename, output_dir)
                                        if saved_path:
                                            logger.info(f"Saved file to {saved_path}")
                                            saved_paths.append(saved_path)
                        
                        # Return paths for the first matching prompt ID
                        return saved_paths
            
            # Handle list format (older ComfyUI versions)
            elif isinstance(history_data, list):
                for item in history_data:
                    if not isinstance(item, dict):
                        continue
                        
                    item_prompt_id = item.get("prompt_id", "")
                    if not item_prompt_id:
                        continue
                    
                    # Check if this is the prompt we're looking for
                    if item_prompt_id == prompt_id or item_prompt_id.startswith(prompt_id) or prompt_id.startswith(item_prompt_id):
                        # Get the outputs
                        outputs = item.get("outputs", {})
                        
                        # Process all nodes or specific node
                        for node_id_key, node_output in outputs.items():
                            # Skip if we're looking for a specific node and this isn't it
                            if node_id and node_id != node_id_key:
                                continue
                            
                            # Process images - check both 'images' and 'gifs' keys
                            for output_type in ['images', 'gifs']:
                                if output_type in node_output:
                                    logger.info(f"Found {output_type} in node {node_id_key}")
                                    
                                    for image_data in node_output[output_type]:
                                        filename = image_data.get("filename")
                                        subfolder = image_data.get("subfolder", "")
                                        
                                        if not filename:
                                            continue
                                        
                                        logger.info(f"Processing {output_type[:-1]} file: {filename}")
                                        
                                        # Get the image data
                                        image_bytes = self.get_image(filename, subfolder)
                                        if not image_bytes:
                                            logger.warning(f"Failed to get file data for {filename}")
                                            continue
                                        
                                        # Save the image
                                        saved_path = self.save_image(image_bytes, filename, output_dir)
                                        if saved_path:
                                            logger.info(f"Saved file to {saved_path}")
                                            saved_paths.append(saved_path)
                        
                        # Return paths for the first matching prompt ID
                        return saved_paths
            
            if not saved_paths:
                logger.warning(f"No output files found for prompt ID {prompt_id}")
            
            return saved_paths
        
        except Exception as e:
            logger.error(f"Error getting output images: {str(e)}")
            return []
    
    def modify_workflow(self, 
                       workflow: Dict[str, Any], 
                       prompt: str, 
                       negative_prompt: str = "", 
                       resolution: str = "1080x1920",
                       seed: int = None,
                       steps: int = None) -> Dict[str, Any]:
        """
        Modify a workflow with the given parameters.
        
        Args:
            workflow: ComfyUI workflow dictionary
            prompt: Text prompt
            negative_prompt: Negative text prompt
            resolution: Resolution in format "widthxheight"
            seed: Random seed (optional)
            steps: Number of steps (optional)
            
        Returns:
            Modified workflow
        """
        try:
            # Create a deep copy of the workflow to avoid modifying the original
            import copy
            modified_workflow = copy.deepcopy(workflow)
            
            # Parse resolution
            if 'x' in resolution:
                width, height = map(int, resolution.split('x'))
            else:
                width, height = 1080, 1920  # Default to vertical video
            
            # Check if workflow is valid
            if not modified_workflow:
                logger.error("Workflow is empty")
                return {}
            
            # Find prompt nodes in the workflow
            positive_prompt_nodes = []
            negative_prompt_nodes = []
            latent_image_nodes = []
            
            for node_id, node in modified_workflow.items():
                # Look for CLIPTextEncode nodes
                if node.get("class_type") == "CLIPTextEncode":
                    node_inputs = node.get("inputs", {})
                    # Check if this is a positive or negative prompt node
                    node_text = node_inputs.get("text", "")
                    if "negative" in node_id.lower() or "negative" in node_text.lower():
                        negative_prompt_nodes.append(node_id)
                    else:
                        positive_prompt_nodes.append(node_id)
                
                # Look for latent image nodes to set resolution
                elif node.get("class_type") in ["EmptyLatentImage", "VideoLinearCFGGuidance"]:
                    latent_image_nodes.append(node_id)
                
                # Look for sampler nodes to set seed and steps
                elif node.get("class_type") in ["KSampler", "KSamplerAdvanced"]:
                    if seed is not None:
                        node["inputs"]["seed"] = seed
                    if steps is not None:
                        node["inputs"]["steps"] = steps
            
            # Set positive prompt
            for node_id in positive_prompt_nodes:
                modified_workflow[node_id]["inputs"]["text"] = prompt
            
            # Set negative prompt
            for node_id in negative_prompt_nodes:
                modified_workflow[node_id]["inputs"]["text"] = negative_prompt
            
            # Set resolution
            for node_id in latent_image_nodes:
                node = modified_workflow[node_id]
                if "width" in node["inputs"] and "height" in node["inputs"]:
                    node["inputs"]["width"] = width
                    node["inputs"]["height"] = height
            
            return modified_workflow
        
        except Exception as e:
            logger.error(f"Error modifying workflow: {str(e)}")
            return workflow  # Return original workflow on error
    
    def _queue_prompt(self, prompt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Queue a prompt to ComfyUI server.
        
        Args:
            prompt: Prompt data
            
        Returns:
            Response data if successful, None otherwise
        """
        try:
            # Validate prompt data
            if not prompt or "prompt" not in prompt:
                logger.error("Invalid prompt data: Missing 'prompt' field")
                return None
            
            # Ensure client_id is included
            client_id = prompt.get("client_id", self.client_id)
            
            # Structure the data correctly for ComfyUI API
            data = {
                "prompt": prompt["prompt"],
                "client_id": client_id
            }
            
            # Add extra_data if present
            if "extra_data" in prompt:
                data["extra_data"] = prompt["extra_data"]
            
            # Convert to JSON and send
            json_data = json.dumps(data).encode('utf-8')
            response = requests.post(f"{self.server_url}/prompt", data=json_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error queueing prompt: Status code {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error queueing prompt: {str(e)}")
            return None
    
    def _ws_listener(self):
        """
        WebSocket listener thread.
        """
        if not self.ws:
            logger.error("WebSocket not connected")
            return
        
        logger.info("WebSocket listener thread started")
        
        try:
            while self.ws:
                try:
                    # Receive message with timeout
                    self.ws.settimeout(0.5)  # Set a timeout for recv
                    try:
                        message = self.ws.recv()
                        # Reset timeout for next recv
                        self.ws.settimeout(None)
                    except websocket.WebSocketTimeoutException:
                        # No message received within timeout
                        continue
                    
                    if not message:
                        time.sleep(0.1)
                        continue
                    
                    # Parse message
                    data = json.loads(message)
                    message_type = data.get("type", "")
                    logger.debug(f"Received WebSocket message: {message_type}")
                    
                    # Handle different message types
                    if message_type == "status":
                        self._handle_status_message(data)
                    elif message_type == "execution_start":
                        self._handle_execution_start(data)
                    elif message_type == "execution_cached":
                        self._handle_execution_cached(data)
                    elif message_type == "executing":
                        self._handle_executing(data)
                    elif message_type == "progress":
                        self._handle_progress(data)
                    elif message_type == "executed":
                        self._handle_executed(data)
                    elif message_type == "execution_error":
                        self._handle_execution_error(data)
                    elif message_type == "execution_complete":
                        self._handle_execution_complete(data)
                
                except websocket.WebSocketConnectionClosedException:
                    logger.info("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error in WebSocket listener: {str(e)}")
                    time.sleep(0.5)  # Prevent busy waiting
        
        finally:
            logger.info("WebSocket listener thread stopped")
    
    def _handle_status_message(self, data: Dict[str, Any]):
        """
        Handle status message from WebSocket.
        
        Args:
            data: Message data
        """
        status_data = data.get("data", {})
        status_msg = status_data.get("status", "")
        
        logger.debug(f"Status update: {status_msg}")
        
        # Check if there's an executing prompt
        executing_data = status_data.get("executing", {})
        if executing_data:
            prompt_id = executing_data.get("prompt_id")
            if prompt_id and prompt_id in self.prompt_map:
                client_data = self.prompt_map[prompt_id]
                client_data["status"] = "executing"
                
                if client_data.get("on_update"):
                    client_data["on_update"]({
                        "prompt_id": prompt_id,
                        "status": "executing",
                        "progress": client_data.get("progress", 0),
                        "max_progress": client_data.get("max_progress", 100),
                    })
    
    def _handle_execution_start(self, data: Dict[str, Any]):
        """
        Handle execution_start message from WebSocket.
        
        Args:
            data: Message data
        """
        prompt_id = data.get("data", {}).get("prompt_id")
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["status"] = "started"
            
            if client_data.get("on_update"):
                client_data["on_update"]({
                    "prompt_id": prompt_id,
                    "status": "started",
                    "progress": 0,
                    "max_progress": 100,
                })
    
    def _handle_execution_cached(self, data: Dict[str, Any]):
        """
        Handle execution_cached message from WebSocket.
        
        Args:
            data: Message data
        """
        prompt_id = data.get("data", {}).get("prompt_id")
        cached_data = data.get("data", {})
        
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["status"] = "cached"
            
            if client_data.get("on_update"):
                client_data["on_update"]({
                    "prompt_id": prompt_id,
                    "status": "cached",
                    "progress": 100,
                    "max_progress": 100,
                    "cached_data": cached_data,
                })
    
    def _handle_executing(self, data: Dict[str, Any]):
        """
        Handle executing message from WebSocket.
        
        Args:
            data: Message data
        """
        node_id = data.get("data", {}).get("node")
        prompt_id = data.get("data", {}).get("prompt_id")
        
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["status"] = f"executing_node_{node_id}"
            
            if client_data.get("on_update"):
                client_data["on_update"]({
                    "prompt_id": prompt_id,
                    "status": "executing",
                    "node_id": node_id,
                    "progress": client_data.get("progress", 0),
                    "max_progress": client_data.get("max_progress", 100),
                })
    
    def _handle_progress(self, data: Dict[str, Any]):
        """
        Handle progress message from WebSocket.
        
        Args:
            data: Message data
        """
        progress_data = data.get("data", {})
        value = progress_data.get("value", 0)
        max_value = progress_data.get("max", 100)
        prompt_id = progress_data.get("prompt_id")
        
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["progress"] = value
            client_data["max_progress"] = max_value
            
            if client_data.get("on_update"):
                client_data["on_update"]({
                    "prompt_id": prompt_id,
                    "status": "progress",
                    "progress": value,
                    "max_progress": max_value,
                    "percentage": (value / max_value) * 100 if max_value > 0 else 0,
                })
    
    def _handle_executed(self, data: Dict[str, Any]):
        """
        Handle executed message from WebSocket.
        
        Args:
            data: Message data
        """
        node_id = data.get("data", {}).get("node")
        prompt_id = data.get("data", {}).get("prompt_id")
        output_data = data.get("data", {}).get("output", {})
        
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["status"] = f"executed_node_{node_id}"
            
            if client_data.get("on_update"):
                client_data["on_update"]({
                    "prompt_id": prompt_id,
                    "status": "node_executed",
                    "node_id": node_id,
                    "output": output_data,
                })
    
    def _handle_execution_error(self, data: Dict[str, Any]):
        """
        Handle execution_error message from WebSocket.
        
        Args:
            data: Message data
        """
        prompt_id = data.get("data", {}).get("prompt_id")
        error_data = data.get("data", {})
        error_type = error_data.get("type", "unknown")
        error_message = error_data.get("message", "Unknown error")
        exception_message = error_data.get("exception_message", "")
        
        logger.error(f"Execution error for prompt {prompt_id}: {error_type} - {error_message} - {exception_message}")
        
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["status"] = "error"
            client_data["error"] = {
                "type": error_type,
                "message": error_message,
                "exception_message": exception_message,
            }
            
            if client_data.get("on_error"):
                client_data["on_error"](f"Execution error: {error_message} - {exception_message}")
            
            # Remove from prompt map after error
            del self.prompt_map[prompt_id]
    
    def _handle_execution_complete(self, data: Dict[str, Any]):
        """
        Handle execution_complete message from WebSocket.
        
        Args:
            data: Message data
        """
        msg_data = data.get("data", {})
        prompt_id = msg_data.get("prompt_id")
        
        logger.debug(f"Execution complete for prompt ID: {prompt_id}")
        logger.debug(f"Execution complete data: {json.dumps(msg_data, indent=2)}")
        
        if prompt_id and prompt_id in self.prompt_map:
            client_data = self.prompt_map[prompt_id]
            client_data["status"] = "complete"
            client_data["complete_data"] = msg_data
            
            # Notify on_complete callback
            if client_data.get("on_complete"):
                try:
                    client_data["on_complete"]({
                        "prompt_id": prompt_id,
                        "status": "complete",
                        "data": msg_data,
                    })
                except Exception as e:
                    logger.error(f"Error in on_complete callback: {str(e)}")
            
            # Log that we're removing the prompt from tracking
            logger.info(f"Removing completed prompt {prompt_id} from tracking")
            
            # Remove from prompt map after completion
            del self.prompt_map[prompt_id]
        else:
            logger.warning(f"Received execution_complete for unknown prompt ID: {prompt_id}")

# Create a singleton instance
_comfyui_client = None

def get_client(server_url: str = "http://100.115.243.42:8000") -> ComfyUIWebSocketClient:
    """
    Get ComfyUI WebSocket client singleton instance.
    
    Args:
        server_url: Base URL of the ComfyUI server
        
    Returns:
        ComfyUIWebSocketClient instance
    """
    global _comfyui_client
    if _comfyui_client is None:
        _comfyui_client = ComfyUIWebSocketClient(server_url)
    elif _comfyui_client.server_url != server_url:
        # Update server URL if it changed
        _comfyui_client.disconnect()
        _comfyui_client = ComfyUIWebSocketClient(server_url)
    
    return _comfyui_client

# Helper functions for direct use without creating a client instance

def submit_workflow(workflow: Dict[str, Any], 
                   server_url: str = "http://100.115.243.42:8000",
                   extra_data: Optional[Dict[str, Any]] = None,
                   on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
                   on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
                   on_error: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """
    Submit a workflow to ComfyUI.
    
    Args:
        workflow: ComfyUI workflow dictionary
        server_url: Base URL of the ComfyUI server
        extra_data: Extra data to include with the prompt
        on_update: Callback function for status updates
        on_complete: Callback function for completion
        on_error: Callback function for errors
        
    Returns:
        Prompt ID if successful, None otherwise
    """
    client = get_client(server_url)
    
    try:
        # Create a unique client_id
        client_id = str(uuid.uuid4())
        
        # Prepare the data in the format ComfyUI expects
        data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        if extra_data:
            data["extra_data"] = extra_data
        
        # Convert to JSON string and then to bytes
        json_data = json.dumps(data).encode('utf-8')
        
        # Send the request directly using requests
        response = requests.post(f"{server_url}/prompt", data=json_data)
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")
            
            if prompt_id:
                logger.info(f"Workflow submitted with prompt ID: {prompt_id}")
                
                # Register callbacks for WebSocket updates
                if on_update or on_complete or on_error:
                    client_data = {
                        "workflow": workflow,
                        "extra_data": extra_data,
                        "on_update": on_update,
                        "on_complete": on_complete,
                        "on_error": on_error,
                        "start_time": time.time(),
                        "status": "queued",
                        "progress": 0,
                        "max_progress": 100,
                        "session_id": client_id
                    }
                    
                    client.prompt_map[prompt_id] = client_data
                
                return prompt_id
            else:
                error_msg = "No prompt ID returned"
                logger.error(error_msg)
                if on_error:
                    on_error(error_msg)
                return None
        else:
            error_msg = f"Error submitting workflow: Status code {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
    except Exception as e:
        error_msg = f"Error submitting workflow: {str(e)}"
        logger.error(error_msg)
        if on_error:
            on_error(error_msg)
        return None

def get_output_images(prompt_id: str, 
                     server_url: str = "http://100.115.243.42:8000",
                     output_dir: Union[str, Path] = None,
                     node_id: str = None) -> List[str]:
    """
    Get output images for a completed prompt.
    
    Args:
        prompt_id: Prompt ID (can be partial)
        server_url: Base URL of the ComfyUI server
        output_dir: Directory to save images to
        node_id: Node ID to get images from (default is to get all)
        
    Returns:
        List of paths to saved images
    """
    try:
        # Get history for this prompt
        logger.debug(f"Getting output images for prompt ID: {prompt_id}")
        
        # Get the history data
        history_url = f"{server_url}/history"
        history_response = requests.get(history_url)
        
        if history_response.status_code != 200:
            logger.error(f"Error getting history: Status code {history_response.status_code}")
            return []
            
        history_data = history_response.json()
        saved_paths = []
        
        # Handle dictionary format (newer ComfyUI versions)
        if isinstance(history_data, dict):
            # Look for exact or partial match in the keys
            for item_id, item_data in history_data.items():
                if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                    logger.info(f"Found matching prompt ID in history: {item_id}")
                    
                    # Get the outputs
                    outputs = item_data.get("outputs", {})
                    
                    # Process all nodes or specific node
                    for node_id_key, node_output in outputs.items():
                        # Skip if we're looking for a specific node and this isn't it
                        if node_id and node_id != node_id_key:
                            continue
                        
                        # Process images - check both 'images' and 'gifs' keys
                        for output_type in ['images', 'gifs']:
                            if output_type in node_output:
                                logger.info(f"Found {output_type} in node {node_id_key}")
                                
                                for image_data in node_output[output_type]:
                                    filename = image_data.get("filename")
                                    subfolder = image_data.get("subfolder", "")
                                    
                                    if not filename:
                                        continue
                                    
                                    logger.info(f"Processing {output_type[:-1]} file: {filename}")
                                    
                                    # Get the image data
                                    image_bytes = get_image(filename, subfolder, server_url=server_url)
                                    if not image_bytes:
                                        logger.warning(f"Failed to get file data for {filename}")
                                        continue
                                    
                                    # Save the image
                                    client = get_client(server_url)
                                    saved_path = client.save_image(image_bytes, filename, output_dir)
                                    if saved_path:
                                        logger.info(f"Saved file to {saved_path}")
                                        saved_paths.append(saved_path)
                    
                    # Return paths for the first matching prompt ID
                    return saved_paths
        
        # Handle list format (older ComfyUI versions)
        elif isinstance(history_data, list):
            for item in history_data:
                if not isinstance(item, dict):
                    continue
                    
                item_prompt_id = item.get("prompt_id", "")
                if not item_prompt_id:
                    continue
                
                # Check if this is the prompt we're looking for
                if item_prompt_id == prompt_id or item_prompt_id.startswith(prompt_id) or prompt_id.startswith(item_prompt_id):
                    # Get the outputs
                    outputs = item.get("outputs", {})
                    
                    # Process all nodes or specific node
                    for node_id_key, node_output in outputs.items():
                        # Skip if we're looking for a specific node and this isn't it
                        if node_id and node_id != node_id_key:
                            continue
                        
                        # Process images - check both 'images' and 'gifs' keys
                        for output_type in ['images', 'gifs']:
                            if output_type in node_output:
                                logger.info(f"Found {output_type} in node {node_id_key}")
                                
                                for image_data in node_output[output_type]:
                                    filename = image_data.get("filename")
                                    subfolder = image_data.get("subfolder", "")
                                    
                                    if not filename:
                                        continue
                                    
                                    logger.info(f"Processing {output_type[:-1]} file: {filename}")
                                    
                                    # Get the image data
                                    image_bytes = get_image(filename, subfolder, server_url=server_url)
                                    if not image_bytes:
                                        logger.warning(f"Failed to get file data for {filename}")
                                        continue
                                    
                                    # Save the image
                                    client = get_client(server_url)
                                    saved_path = client.save_image(image_bytes, filename, output_dir)
                                    if saved_path:
                                        logger.info(f"Saved file to {saved_path}")
                                        saved_paths.append(saved_path)
                    
                    # Return paths for the first matching prompt ID
                    return saved_paths
        
        if not saved_paths:
            logger.warning(f"No output files found for prompt ID {prompt_id}")
        
        return saved_paths
    
    except Exception as e:
        logger.error(f"Error getting output images: {str(e)}")
        return []

def get_image(filename: str, subfolder: str = "", folder_type: str = "output", server_url: str = "http://100.115.243.42:8000") -> Optional[bytes]:
    """
    Get image data from ComfyUI server.
    
    Args:
        filename: Image filename
        subfolder: Subfolder within the folder_type
        folder_type: Folder type (output, input, temp)
        server_url: Base URL of the ComfyUI server
        
    Returns:
        Image data if successful, None otherwise
    """
    try:
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        response = requests.get(f"{server_url}/view", params=data)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Error getting image: Status code {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting image: {str(e)}")
        return None

def modify_workflow(workflow: Dict[str, Any], 
                   prompt: str, 
                   negative_prompt: str = "", 
                   resolution: str = "1080x1920",
                   seed: int = None,
                   steps: int = None,
                   server_url: str = "http://100.115.243.42:8000") -> Dict[str, Any]:
    """
    Modify a workflow with the given parameters.
    
    Args:
        workflow: ComfyUI workflow dictionary
        prompt: Text prompt
        negative_prompt: Negative text prompt
        resolution: Resolution in format "widthxheight"
        seed: Random seed (optional)
        steps: Number of steps (optional)
        server_url: Base URL of the ComfyUI server
        
    Returns:
        Modified workflow
    """
    client = get_client(server_url)
    return client.modify_workflow(workflow, prompt, negative_prompt, resolution, seed, steps)

def load_workflow_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load workflow from JSON file.
    
    Args:
        file_path: Path to workflow JSON file
        
    Returns:
        Workflow dictionary
    """
    try:
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Workflow file not found: {file_path}")
            return {}
        
        with open(file_path, "r") as f:
            workflow = json.load(f)
        
        return workflow
    except Exception as e:
        logger.error(f"Error loading workflow file: {str(e)}")
        return {}

def check_prompt_status(prompt_id: str, server_url: str = "http://100.115.243.42:8000") -> Dict[str, Any]:
    """
    Check the status of a prompt using the HTTP API.
    
    Args:
        prompt_id: Prompt ID to check (can be partial)
        server_url: Base URL of the ComfyUI server
        
    Returns:
        Status information dictionary
    """
    try:
        # Log the prompt ID we're checking
        logger.info(f"Checking status for prompt ID: {prompt_id}")
        
        # First, try to get the prompt status from the history endpoint
        history_url = f"{server_url}/history"
        logger.debug(f"Fetching history from {history_url}")
        history_response = requests.get(history_url)
        
        if history_response.status_code == 200:
            history_data = history_response.json()
            
            # Check if history_data is a dictionary (newer ComfyUI versions)
            if isinstance(history_data, dict):
                logger.debug(f"History data is a dictionary with {len(history_data)} items")
                
                # Look for exact or partial match in the keys
                for item_id, item_data in history_data.items():
                    if item_id == prompt_id or item_id.startswith(prompt_id) or prompt_id.startswith(item_id):
                        logger.info(f"Found matching prompt ID in history: {item_id}")
                        
                        # Check if it has outputs, which means it's complete
                        if "outputs" in item_data and item_data["outputs"]:
                            logger.info(f"Prompt {item_id} found in history with outputs")
                            return {
                                "status": "complete",
                                "outputs": item_data["outputs"],
                                "prompt_id": item_id
                            }
                        else:
                            logger.info(f"Prompt {item_id} found in history but no outputs yet")
                            return {
                                "status": "running",
                                "prompt_id": item_id
                            }
            
            # Handle list format (older ComfyUI versions)
            elif isinstance(history_data, list):
                logger.debug(f"History data is a list with {len(history_data)} items")
                
                # Look for the prompt in the history - support both full and partial IDs
                for item in history_data:
                    if not isinstance(item, dict):
                        continue
                        
                    item_prompt_id = item.get("prompt_id", "")
                    if not item_prompt_id:
                        continue
                    
                    # Check if the prompt ID matches (either full or starts with)
                    if item_prompt_id == prompt_id or item_prompt_id.startswith(prompt_id) or prompt_id.startswith(item_prompt_id):
                        # Log the match
                        logger.info(f"Found matching prompt ID in history: {item_prompt_id}")
                        
                        # Check if it has outputs, which means it's complete
                        if "outputs" in item and item["outputs"]:
                            logger.info(f"Prompt {item_prompt_id} found in history with outputs")
                            return {
                                "status": "complete",
                                "outputs": item["outputs"],
                                "prompt_id": item_prompt_id
                            }
                        else:
                            logger.info(f"Prompt {item_prompt_id} found in history but no outputs yet")
                            return {
                                "status": "running",
                                "prompt_id": item_prompt_id
                            }
            else:
                logger.warning(f"Unexpected history data type: {type(history_data)}")
        
        # If not found in history, check the queue
        queue_url = f"{server_url}/queue"
        logger.debug(f"Fetching queue from {queue_url}")
        queue_response = requests.get(queue_url)
        
        if queue_response.status_code == 200:
            queue_data = queue_response.json()
            
            # Check the running queue item
            running_item = queue_data.get("running", {})
            if isinstance(running_item, dict):
                running_prompt_id = running_item.get("prompt_id", "")
                if running_prompt_id and (running_prompt_id == prompt_id or 
                                        running_prompt_id.startswith(prompt_id) or 
                                        prompt_id.startswith(running_prompt_id)):
                    logger.info(f"Prompt {running_prompt_id} is currently running")
                    return {
                        "status": "running",
                        "prompt_id": running_prompt_id
                    }
            
            # Check the pending queue items
            for item in queue_data.get("pending", []):
                if not isinstance(item, dict):
                    continue
                    
                item_prompt_id = item.get("prompt_id", "")
                if not item_prompt_id:
                    continue
                
                if item_prompt_id == prompt_id or item_prompt_id.startswith(prompt_id) or prompt_id.startswith(item_prompt_id):
                    logger.info(f"Prompt {item_prompt_id} is pending in queue")
                    return {
                        "status": "pending",
                        "prompt_id": item_prompt_id
                    }
        
        # If we get here, the prompt ID wasn't found in history or queue
        logger.warning(f"Prompt {prompt_id} not found in history or queue")
        
        return {
            "status": "unknown",
            "prompt_id": prompt_id
        }
    
    except Exception as e:
        logger.error(f"Error checking prompt status: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e),
            "prompt_id": prompt_id
        }

def wait_for_prompt_completion(prompt_id: str, 
                              server_url: str = "http://100.115.243.42:8000",
                              max_wait_time: int = 300,
                              check_interval: int = 5,
                              on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
                              on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
                              on_error: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """
    Wait for a prompt to complete using both WebSocket and HTTP API polling as fallback.
    
    Args:
        prompt_id: Prompt ID to check (can be partial)
        server_url: Base URL of the ComfyUI server
        max_wait_time: Maximum time to wait in seconds
        check_interval: Interval between HTTP API checks in seconds
        on_update: Callback for status updates
        on_complete: Callback for completion
        on_error: Callback for errors
        
    Returns:
        Status information dictionary
    """
    # Initialize the WebSocket client in case we need to use it
    client = get_client(server_url)
    
    # Variables to track status
    start_time = time.time()
    last_check_time = 0
    is_complete = False
    status_info = {"status": "pending", "prompt_id": prompt_id}
    full_prompt_id = prompt_id  # Store the full ID if we find it
    check_count = 0
    
    # Log that we're starting to wait
    logger.info(f"Starting to wait for prompt {prompt_id} to complete (timeout: {max_wait_time}s)")
    
    # Wait until complete or timeout
    while not is_complete and time.time() - start_time < max_wait_time:
        # Only check via HTTP API at intervals
        current_time = time.time()
        if current_time - last_check_time >= check_interval:
            last_check_time = current_time
            check_count += 1
            
            # Check status via HTTP API
            logger.info(f"Check #{check_count}: Checking status of prompt {prompt_id}")
            status_info = check_prompt_status(prompt_id, server_url)
            
            # If we found a full prompt ID, use that for subsequent checks
            if status_info.get("prompt_id") != prompt_id:
                full_prompt_id = status_info.get("prompt_id", prompt_id)
                logger.info(f"Found full prompt ID: {full_prompt_id}")
                prompt_id = full_prompt_id
            
            # Process status
            if status_info["status"] == "complete":
                is_complete = True
                logger.info(f"Prompt {prompt_id} is complete after {int(time.time() - start_time)}s")
                
                # Call completion callback if provided
                if on_complete:
                    try:
                        on_complete(status_info)
                    except Exception as e:
                        logger.error(f"Error in on_complete callback: {str(e)}")
                
                break
            elif status_info["status"] == "error":
                logger.error(f"Error with prompt {prompt_id}: {status_info.get('error_message', 'Unknown error')}")
                
                # Call error callback if provided
                if on_error:
                    try:
                        on_error(status_info.get("error_message", "Unknown error"))
                    except Exception as e:
                        logger.error(f"Error in error callback: {str(e)}")
                
                break
            else:
                # Still running or pending
                logger.info(f"Prompt {prompt_id} status: {status_info['status']} (elapsed: {int(time.time() - start_time)}s)")
                
                # Call update callback if provided
                if on_update:
                    try:
                        on_update(status_info)
                    except Exception as e:
                        logger.error(f"Error in update callback: {str(e)}")
        
        # Sleep for a short time before checking again
        time.sleep(1)
    
    # Check if we timed out
    if not is_complete and time.time() - start_time >= max_wait_time:
        logger.warning(f"Timed out waiting for prompt {prompt_id} to complete after {max_wait_time} seconds")
        status_info["status"] = "timeout"
        
        # Call error callback if provided
        if on_error:
            try:
                on_error(f"Timed out waiting for prompt {prompt_id} to complete")
            except Exception as e:
                logger.error(f"Error in error callback: {str(e)}")
    
    return status_info 