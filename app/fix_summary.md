# B-Roll Percentage Fixes Summary

## Problem Description
When selecting a B-roll percentage (25%, 50%, or 75%) during A-Roll transcription, the assembly step was still showing the original number of B-roll segments rather than the reduced number based on the percentage. For example, selecting 25% B-roll density (which should result in only 2 B-roll segments for 8 A-roll segments) still showed 8 B-roll segments in the assembly page.

## Root Cause Analysis
We identified multiple synchronization issues between configuration files:

1. When generating B-roll segments with a percentage setting, the `script.json` file was correctly updated with the new segments, but:
   - The `content_status.json` file wasn't being updated to match
   - Cached B-roll prompts were not being properly cleared

2. The Video Assembly page was loading B-roll data from `content_status.json` without checking if it matched the current `script.json` data.

3. **NEW ROOT CAUSE**: Default B-roll IDs in `broll_defaults.py` were being applied even when percentage-based B-roll segments were already set up, overriding the correct number of segments.

## Implemented Fixes

### 1. Enhanced Home.py Cache Clearing
Added comprehensive cache clearing to the application startup:
- Now properly checks for content_status.json and synchronizes it with script.json
- Backs up files instead of simply deleting them
- Adds version information to script.json
- Explicitly tracks B-roll segment counts

### 2. Created Utility Scripts
Added two utility scripts:
- `fix_broll_mismatch.py` to fix mismatches between script.json and content_status.json
- `reset_broll_content_status.py` to forcefully reset B-roll segments in content_status.json based on script.json

### 3. Fixed Video Assembly Page
Modified `load_content_status()` in 6_Video_Assembly.py:
- Now loads script.json first to determine the correct number of B-roll segments
- Automatically fixes mismatches between script.json and content_status.json
- Creates appropriate data structures when files are missing
- Adds detailed logging for troubleshooting
- Updates session state to ensure consistency

### 4. Modified Default B-Roll Logic
Updated the default B-roll ID application logic:
- Modified `apply_default_broll_ids()` to respect existing B-roll segments
- Only applies defaults when no B-roll segments are present
- Added checks to preserve percentage-based B-roll settings

### 5. Enhanced Debugging
Added detailed debug logging throughout the application:
- Shows B-roll segment counts from both script.json and content_status.json
- Warns about mismatches between these files
- Displays percentage-based B-roll settings when present

## How to Verify the Fix

1. Start with a fresh project or reset the existing data:
   ```
   python reset_broll_content_status.py my_short_video
   ```

2. Complete the A-Roll transcription with a specific percentage (e.g., 25%)

3. Check the logs to confirm the correct number of B-roll segments are created:
   ```
   Debug - Loading script data: Found 10 segments in script.json
   Debug - Found 2 B-Roll and 8 other segments
   ```

4. Proceed to the B-Roll Prompts page and verify it shows only 2 B-roll segments

5. Go to the Video Assembly page and confirm it shows only 2 B-roll segments

## Technical Improvements Made

1. **Version Tracking**: Added version information to script.json to track data format changes
2. **Backup Mechanism**: Now creates timestamped backups instead of overwriting files
3. **Data Validation**: Added validation to ensure segment counts match between files
4. **Improved Logging**: Enhanced debug output to help diagnose future issues
5. **Sync Logic**: Implemented robust synchronization between different data files
6. **Default Overrides**: Prevented default settings from overriding percentage-based settings

## Future Improvements

1. Consider a more unified data storage approach to prevent these types of inconsistencies
2. Add a user-facing reset button for when inconsistencies are detected
3. Implement additional validation checks throughout the workflow
4. Add automated tests to verify data consistency

## Manual Fixes for Existing Projects

If you encounter B-roll mismatch issues, you can run the following utilities:

1. To check and fix mismatches between script.json and content_status.json:
   ```
   python fix_broll_mismatch.py my_short_video
   ```

2. To forcefully reset B-roll segments in content_status.json:
   ```
   python reset_broll_content_status.py my_short_video
   ```

3. If issues persist, restart the application after running these fixes. 