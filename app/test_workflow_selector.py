#!/usr/bin/env python3

import os
import sys
import json

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.getcwd()))

# Import our new workflow selector module
import utils.workflow_selector as workflow_selector
import utils.direct_workflow as direct_workflow

def test_workflow_paths():
    """Test getting workflow file paths"""
    print("\n=== Testing workflow file path selection ===")
    
    # Test with image type
    print("\nTesting with content_type='image':")
    image_path = workflow_selector.get_workflow_file("image")
    if image_path:
        print(f"✅ Selected image workflow: {image_path}")
        print(f"  File exists: {os.path.exists(image_path)}")
    else:
        print("❌ Failed to get image workflow path")
    
    # Test with video type
    print("\nTesting with content_type='video':")
    video_path = workflow_selector.get_workflow_file("video")
    if video_path:
        print(f"✅ Selected video workflow: {video_path}")
        print(f"  File exists: {os.path.exists(video_path)}")
    else:
        print("❌ Failed to get video workflow path")

def test_workflow_loading():
    """Test loading workflow JSON"""
    print("\n=== Testing workflow JSON loading ===")
    
    # Test with image type
    print("\nTesting with content_type='image':")
    image_workflow = workflow_selector.load_workflow("image")
    if image_workflow:
        print(f"✅ Loaded image workflow with {len(image_workflow)} nodes")
        
        # Count node types
        node_types = {}
        for node_id, node in image_workflow.items():
            if "class_type" in node:
                node_type = node["class_type"]
                node_types[node_type] = node_types.get(node_type, 0) + 1
                
        print("  Node types:")
        for node_type, count in node_types.items():
            print(f"    - {node_type}: {count}")
    else:
        print("❌ Failed to load image workflow")
    
    # Test with video type
    print("\nTesting with content_type='video':")
    video_workflow = workflow_selector.load_workflow("video")
    if video_workflow:
        print(f"✅ Loaded video workflow with {len(video_workflow)} nodes")
        
        # Count node types
        node_types = {}
        for node_id, node in video_workflow.items():
            if "class_type" in node:
                node_type = node["class_type"]
                node_types[node_type] = node_types.get(node_type, 0) + 1
                
        print("  Node types:")
        for node_type, count in node_types.items():
            print(f"    - {node_type}: {count}")
    else:
        print("❌ Failed to load video workflow")

def test_model_info():
    """Test extracting model info from workflows"""
    print("\n=== Testing model info extraction ===")
    
    # Test with image workflow
    print("\nTesting with image workflow:")
    image_workflow = workflow_selector.load_workflow("image")
    if image_workflow:
        image_model_info = workflow_selector.get_model_info(image_workflow)
        print(f"✅ Image workflow model info:")
        for key, value in image_model_info.items():
            print(f"  - {key}: {value}")
    
    # Test with video workflow
    print("\nTesting with video workflow:")
    video_workflow = workflow_selector.load_workflow("video")
    if video_workflow:
        video_model_info = workflow_selector.get_model_info(video_workflow)
        print(f"✅ Video workflow model info:")
        for key, value in video_model_info.items():
            print(f"  - {key}: {value}")

def test_direct_workflow_with_selector():
    """Test combining workflow selector with direct workflow submission"""
    print("\n=== Testing direct workflow with selector ===")
    
    # First get the appropriate workflow path
    workflow_path = workflow_selector.get_workflow_file("image")
    if not workflow_path:
        print("❌ Failed to get workflow path")
        return
        
    # Load the workflow
    workflow = direct_workflow.load_raw_workflow(workflow_path)
    if not workflow:
        print("❌ Failed to load workflow")
        return
        
    # Get model info
    model_info = workflow_selector.get_model_info(workflow)
    print(f"✅ Loaded workflow for model type: {model_info['model_type']}")
    
    # Print number of nodes
    print(f"✅ Workflow has {len(workflow)} nodes")
    
    # Don't actually submit the workflow in this test

if __name__ == "__main__":
    # Run tests
    test_workflow_paths()
    test_workflow_loading()
    test_model_info()
    test_direct_workflow_with_selector() 