#!/usr/bin/env python3

import os
import sys
import json

# Add app directory to path
sys.path.insert(0, os.path.abspath(os.getcwd()))

# Import modules
import utils.direct_workflow as direct_workflow

# Function from 5B_BRoll_Video_Production.py (modified for standalone use)
def load_workflow_5b(workflow_type="video"):
    """Load a workflow template file based on the type of content to generate"""
    try:
        # Special handling for wan workflow - directly use wan.json for everything
        wan_path = os.path.join(os.getcwd(), "wan.json")
        if os.path.exists(wan_path):
            print(f"Found WAN workflow file at: {wan_path}")
            try:
                with open(wan_path, "r") as f:
                    workflow = json.load(f)
                    
                if workflow and len(workflow) > 0:
                    print(f"✅ Loaded workflow from {wan_path} with {len(workflow)} nodes")
                    return workflow
            except Exception as e:
                print(f"Error loading WAN workflow: {str(e)}")
        
        # Add fallback paths
        possible_paths = []
            
        if workflow_type == "image":
            # For image type, prefer flux_schnell.json
            possible_paths.append(os.path.join(os.getcwd(), "flux_schnell.json"))
        else:
            possible_paths.append(os.path.join(os.getcwd(), "wan.json"))
            
        # Try each path
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found workflow file at: {path}")
                try:
                    with open(path, "r") as f:
                        workflow = json.load(f)
                    
                    if workflow and len(workflow) > 0:
                        print(f"✅ Loaded workflow from {path} with {len(workflow)} nodes")
                        return workflow
                except Exception as e:
                    print(f"Error loading workflow from {path}: {str(e)}")
                    continue
        
        print("❌ No valid workflow file found")
        return None
            
    except Exception as e:
        print(f"Error in load_workflow: {str(e)}")
        return None

def test_direct_workflow_loading():
    """Test loading using direct_workflow module"""
    print("\n=== Testing utils/direct_workflow.py loading ===")
    # Test with flux_schnell.json
    print("\nTesting flux_schnell.json:")
    flux_path = os.path.join(os.getcwd(), "flux_schnell.json")
    flux_workflow = direct_workflow.load_raw_workflow(flux_path)
    if flux_workflow:
        print(f"✅ Successfully loaded flux_schnell.json with {len(flux_workflow)} nodes")
    else:
        print("❌ Failed to load flux_schnell.json")
        
    # Test with wan.json
    print("\nTesting wan.json:")
    wan_path = os.path.join(os.getcwd(), "wan.json")
    wan_workflow = direct_workflow.load_raw_workflow(wan_path)
    if wan_workflow:
        print(f"✅ Successfully loaded wan.json with {len(wan_workflow)} nodes")
    else:
        print("❌ Failed to load wan.json")

def test_5b_workflow_loading():
    """Test loading using 5B_BRoll_Video_Production.py function"""
    print("\n=== Testing 5B_BRoll_Video_Production.py loading ===")
    
    # Test with video type (should use wan.json)
    print("\nTesting with workflow_type='video':")
    video_workflow = load_workflow_5b(workflow_type="video")
    
    # Test with image type (should use flux_schnell.json)
    print("\nTesting with workflow_type='image':")
    image_workflow = load_workflow_5b(workflow_type="image")

def compare_workflows():
    """Check if both JSON files exist and compare their structure"""
    print("\n=== Comparing workflow files ===")
    
    # Check if files exist
    flux_path = os.path.join(os.getcwd(), "flux_schnell.json")
    wan_path = os.path.join(os.getcwd(), "wan.json")
    
    flux_exists = os.path.exists(flux_path)
    wan_exists = os.path.exists(wan_path)
    
    print(f"flux_schnell.json exists: {flux_exists}")
    print(f"wan.json exists: {wan_exists}")
    
    # If both exist, compare node counts and types
    if flux_exists and wan_exists:
        try:
            with open(flux_path, "r") as f:
                flux_workflow = json.load(f)
                
            with open(wan_path, "r") as f:
                wan_workflow = json.load(f)
                
            print(f"\nflux_schnell.json has {len(flux_workflow)} nodes")
            print(f"wan.json has {len(wan_workflow)} nodes")
            
            # Check for class_type in nodes
            flux_classes = {}
            wan_classes = {}
            
            for node_id, node in flux_workflow.items():
                if "class_type" in node:
                    class_type = node["class_type"]
                    flux_classes[class_type] = flux_classes.get(class_type, 0) + 1
            
            for node_id, node in wan_workflow.items():
                if "class_type" in node:
                    class_type = node["class_type"]
                    wan_classes[class_type] = wan_classes.get(class_type, 0) + 1
            
            print("\nflux_schnell.json node types:")
            for class_type, count in flux_classes.items():
                print(f"  - {class_type}: {count}")
                
            print("\nwan.json node types:")
            for class_type, count in wan_classes.items():
                print(f"  - {class_type}: {count}")
            
        except Exception as e:
            print(f"Error comparing workflows: {str(e)}")

if __name__ == "__main__":
    # Run tests
    test_direct_workflow_loading()
    test_5b_workflow_loading()
    compare_workflows() 