# Ollama Setup Guide

This guide will help you set up Ollama on your system to enable the automatic A-Roll segmentation and B-Roll prompt generation features.

## What is Ollama?

Ollama is a tool that lets you run large language models (LLMs) locally on your machine. Our app uses the `mistral:7b-instruct-v0.3-q4_K_M` model for intelligent video segmentation and B-Roll prompt generation.

## Installation

### macOS

1. Download the latest Ollama app from the official website: [https://ollama.com/download](https://ollama.com/download)
2. Open the downloaded file and drag Ollama to your Applications folder
3. Launch Ollama from your Applications folder
4. You should see the Ollama icon in your menu bar

### Windows

1. Download the latest Ollama installer from the official website: [https://ollama.com/download](https://ollama.com/download)
2. Run the installer and follow the prompts
3. After installation, Ollama should start automatically

### Linux

1. Install Ollama using the command:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. Start the Ollama service:
   ```bash
   ollama serve
   ```

## Downloading the Required Model

Once Ollama is installed and running, you need to download the Mistral model we use for segmentation:

1. Open a terminal/command prompt
2. Run the following command:
   ```bash
   ollama pull mistral:7b-instruct-v0.3-q4_K_M
   ```
3. Wait for the download to complete (this may take a few minutes depending on your internet connection)

## Verifying the Installation

To verify that Ollama is running correctly:

1. Open a terminal/command prompt
2. Run the following command:
   ```bash
   curl http://localhost:11434/api/tags
   ```
3. You should see a JSON response listing the available models

## Using Ollama with the App

Once Ollama is installed and running:

1. Launch the AI Money Printer Shorts application
2. Navigate to the A-Roll Transcription page
3. Upload your video and generate a transcript
4. Choose "Automatic Segmentation" and click "Analyze and Segment Automatically"
5. The app will use Ollama to intelligently segment your transcript based on logical content boundaries

## Troubleshooting

If you encounter issues with Ollama:

- Make sure the Ollama application is running
- Check if the service is accessible by running `curl http://localhost:11434/api/tags`
- Restart Ollama if it's not responding
- Check Ollama's system requirements (8GB RAM minimum, 16GB recommended)

If Ollama is not available, the app will fall back to basic segmentation, but you'll miss out on the intelligent segmentation capabilities. 