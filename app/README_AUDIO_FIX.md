# Audio Repetition Fix for Video Assembly

This document explains how to fix the audio repetition issue in the video assembly process.

## The Problem

When assembling videos, you may encounter an issue where the same A-Roll audio segments are used multiple times, causing audio repetition in the final video. This can happen when:

1. Using certain sequence patterns that don't properly track which A-Roll audio segments have been used
2. Having more A-Roll segments than B-Roll segments, causing the system to reuse A-Roll audio
3. Using a transcription-based A-Roll where segments need to be extracted at specific timestamps

## The Solution

The `fix_audio_repetition.py` script creates a custom assembly sequence that ensures each A-Roll audio segment is used exactly once, preventing audio repetition in the final video.

## How to Use

1. Run the script with your project directory:
   ```
   python fix_audio_repetition.py path/to/your/project
   ```
   
   If you don't specify a project directory, the script will try to find one automatically.

2. The script will create a file called `no_overlap_assembly.json` in your project directory.

3. To use this sequence:
   - Go to the Video Assembly page
   - Select "Custom (Manual Arrangement)" in the Sequence Pattern dropdown
   - In the Custom Sequence section, click "Import Sequence"
   - Select the `no_overlap_assembly.json` file
   - Click "Assemble Video"

## How It Works

The script:

1. Loads your project's script segments and content status
2. Identifies all available A-Roll segments
3. Creates a sequence that ensures each A-Roll segment is used exactly once
4. Includes timestamp information for transcription-based A-Roll segments
5. Saves the sequence to a JSON file that can be imported in the Video Assembly page

## Additional Tips

- For transcription-based A-Roll videos, make sure the script includes proper timestamp information
- If you're still experiencing audio repetition, try using the "B-Roll Full" sequence pattern
- Check for any audio overlaps in the Video Assembly page before assembling the video
- Use the "Use simple assembly (FFmpeg direct)" option if you continue to experience issues

## Troubleshooting

If you encounter any issues:

1. Make sure your project has valid A-Roll and B-Roll segments
2. Check that the A-Roll video file exists and is accessible
3. Verify that the timestamp information in your script is correct
4. Try running the script with the `--debug` flag for more detailed output
5. Check the console for any error messages

## Technical Details

The script creates a sequence with the following structure:
- First segment: A-Roll visuals with A-Roll audio
- Middle segments: B-Roll visuals with A-Roll audio
- Last segment: A-Roll visuals with A-Roll audio

Each segment includes:
- Type: "aroll_full" or "broll_with_aroll_audio"
- A-Roll path: Path to the A-Roll video file
- B-Roll path: Path to the B-Roll video/image file (if applicable)
- Segment ID: Identifier for the segment
- Start time, end time, and duration: Timestamp information for transcription-based A-Roll 