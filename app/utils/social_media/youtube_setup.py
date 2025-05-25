#!/usr/bin/env python3
"""
YouTube API setup utility for AI Money Printer Shorts
"""
import os
import sys
import json
from pathlib import Path

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.parent.parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

def create_client_secrets_template():
    """
    Create a template client_secrets.json file with instructions
    
    Returns:
        str: Path to the created template file
    """
    template = {
        "installed": {
            "client_id": "YOUR_CLIENT_ID_HERE",
            "project_id": "YOUR_PROJECT_ID_HERE",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET_HERE",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    # Create the output directory
    os.makedirs("config/credentials", exist_ok=True)
    
    # Write the template to a file
    output_path = "config/credentials/client_secret_template.json"
    with open(output_path, "w") as f:
        json.dump(template, f, indent=4)
    
    return output_path

def print_setup_instructions():
    """Print instructions for setting up YouTube API credentials"""
    print("\n" + "="*80)
    print("YouTube API Setup Instructions".center(80))
    print("="*80)
    
    print("""
To upload videos to YouTube, you need to set up API credentials:

1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"
4. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as the application type
   - Enter a name for your credentials (e.g., "AI Money Printer Shorts")
   - Click "Create"
5. Download the JSON credentials file
6. Rename it to "client_secret.json"
7. Place it in the app root directory

A template file has been created at:
""")
    
    template_path = create_client_secrets_template()
    print(f"{template_path}\n")
    
    print("""
Replace the placeholder values with your actual credentials from the downloaded JSON file.

Once you have the credentials file properly set up, you can run the Social Media Upload page
and authenticate with your YouTube account to upload videos.
""")
    
    print("="*80)

if __name__ == "__main__":
    print_setup_instructions() 