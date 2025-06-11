"""
Workflow Selector Module

This module provides utility functions to select the appropriate workflow file
based on content type, ensuring the right model is used for each type of content.
"""

import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define constants
DEFAULT_VIDEO_WORKFLOW = "wan.json"
DEFAULT_IMAGE_WORKFLOW = "flux_schnell.json"
DEFAULT_RESOLUTION = (1080, 1920)

def get_workflow_file(content_type):
    """Get the appropriate workflow file path based on content type
    
    Args:
        content_type: String with either "image" or "video"
        
    Returns:
        String path to the workflow file
    """
    try:
        if content_type.lower() == "image":
            workflow_path = os.path.join(os.getcwd(), DEFAULT_IMAGE_WORKFLOW)
            logger.info(f"Selected image workflow: {workflow_path}")
        else:  # Default to video
            workflow_path = os.path.join(os.getcwd(), DEFAULT_VIDEO_WORKFLOW)
            logger.info(f"Selected video workflow: {workflow_path}")
            
        # Verify file exists
        if not os.path.exists(workflow_path):
            logger.error(f"Workflow file not found: {workflow_path}")
            return None
            
        return workflow_path
    except Exception as e:
        logger.error(f"Error selecting workflow file: {str(e)}")
        return None

def load_workflow(content_type):
    """Load the appropriate workflow JSON based on content type
    
    Args:
        content_type: String with either "image" or "video"
        
    Returns:
        Dict containing the workflow JSON, or None if failed
    """
    try:
        workflow_path = get_workflow_file(content_type)
        if not workflow_path:
            return None
            
        with open(workflow_path, "r") as f:
            workflow = json.load(f)
            
        if not workflow:
            logger.error(f"Empty or invalid workflow JSON in {workflow_path}")
            return None
            
        logger.info(f"Successfully loaded {content_type} workflow with {len(workflow)} nodes")
        return workflow
    except Exception as e:
        logger.error(f"Error loading workflow: {str(e)}")
        return None
        
def get_model_info(workflow):
    """Extract model information from a workflow
    
    Args:
        workflow: Dict containing the workflow JSON
        
    Returns:
        Dict with model info, or empty dict if not found
    """
    model_info = {"model_type": "unknown", "has_specialized_nodes": False}
    
    try:
        if not workflow:
            return model_info
            
        # Check for specialized nodes
        specialized_nodes = [
            "EmptyHunyuanLatentVideo",  # WAN model
            "EmptySD3LatentImage",      # SD3/FLOW model
            "UNETLoader",               # WAN model
            "CLIPLoader"                # WAN model
        ]
        
        for node_id, node in workflow.items():
            if "class_type" in node and node["class_type"] in specialized_nodes:
                model_info["has_specialized_nodes"] = True
                
                if node["class_type"] == "EmptyHunyuanLatentVideo":
                    model_info["model_type"] = "WAN"
                elif node["class_type"] == "EmptySD3LatentImage":
                    model_info["model_type"] = "FLOW"
                    
            # Check for model loaders to determine model type
            if "class_type" in node and node["class_type"] == "CheckpointLoaderSimple":
                if "inputs" in node and "ckpt_name" in node["inputs"]:
                    model_name = node["inputs"]["ckpt_name"]
                    model_info["model_name"] = model_name
                    
                    # Try to determine model type from name
                    if any(x in model_name.lower() for x in ["sd3", "stable-diffusion-3", "flow"]):
                        model_info["model_type"] = "FLOW"
            
        return model_info
    except Exception as e:
        logger.error(f"Error analyzing workflow: {str(e)}")
        return model_info 