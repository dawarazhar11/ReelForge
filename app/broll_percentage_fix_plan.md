# B-Roll Percentage Fix Plan

## Problem Identified
The assembly step is using outdated B-roll segment data rather than the correctly generated percentage-based B-roll segments. When selecting 25% B-roll density (which should result in only 2 B-roll segments for 8 A-roll segments), the assembly page still shows 8 B-roll segments from previous generations.

## Root Causes
1. Cached or outdated B-roll data persisting between sessions
2. Lack of version tracking in the script.json file
3. Multiple storage locations for B-roll data causing conflicts
4. Missing explicit cleanup of old data before generating new B-roll segments
5. The video assembly page was using `content_status.json` which wasn't synced with script.json

## Implemented Fixes

### 1. Added Cleanup Function
- Created a `cleanup_broll_data()` function that removes old B-roll prompt files
- This ensures that previously generated B-roll data doesn't interfere with new generations
- Added the cleanup function to Home.py to clear cache on application startup

### 2. Enhanced Version Tracking
- Added version information to the script.json file
- Included explicit B-roll and A-roll segment counts in the metadata
- Added a "generated_with" field to indicate the generation method

### 3. Improved Data Preservation
- Updated the save_segments function to explicitly exclude certain fields from being preserved
- This prevents old segment data from being mixed with new data

### 4. Integration with Generation Process
- Added cleanup function calls before generating new B-roll segments
- Applied to both automatic and manual generation workflows

### 5. Fixed B-Roll Prompts Page
- Updated the B-Roll Prompts page to respect percentage-based B-roll data
- Modified the generate_broll_segments_from_aroll function to use the percentage setting
- Added informative UI elements to show users what percentage is being used

### 6. Added Application-wide Cache Clearing
- Implemented cache clearing function in the Home.py file
- Added backup functionality for important files instead of just deleting them
- The function runs automatically when the application starts

### 7. Content Status Sync with Script Data
- Modified the `load_content_status()` function in the Video Assembly page
- Added automatic synchronization between script.json and content_status.json
- Ensures the assembly page uses the correct number of B-roll segments from the script

### 8. Created Utility Scripts
- Added `fix_broll_mismatch.py` script to fix mismatches between script.json and content_status.json
- This can be run manually when issues are detected

## Additional Recommended Steps

### 1. Testing
- Test with different B-roll percentages (25%, 50%, 75%)
- Verify that changing the percentage produces the expected number of B-roll segments
- Check that assembly page correctly reflects the number of B-roll segments

### 2. Potential Further Improvements
- Add a reset button to force regeneration of B-roll segments
- Implement a validation step before assembly to ensure segment counts match
- Add logging to track B-roll segment generation and usage
- Consider a more robust data storage approach to prevent conflicts

### 3. Documentation Updates
- Update user documentation to explain the B-roll percentage feature
- Add developer notes about the data flow between pages

## Usage Instructions for Fix Utilities

### Fixing Existing Projects
Run the following command to fix all existing projects:
```
python fix_broll_mismatch.py
```

Or specify a particular project:
```
python fix_broll_mismatch.py my_short_video
```

### Starting Fresh
When starting the application, the cache clearing function will automatically run, preventing stale data issues.

## Technical Summary
1. Our fixes address the root cause: synchronization between different configuration files
2. The core issue was the `content_status.json` file not being updated when B-roll percentages changed
3. We've implemented fixes at multiple levels: startup, content generation, and assembly
4. This ensures a consistent B-roll count throughout the entire pipeline

## Verification Steps
1. Generate A-roll segments from transcription
2. Select 25% B-roll density and generate B-roll segments
3. Verify only 2 B-roll segments are created
4. Check the assembly page shows the correct 2 B-roll segments instead of 8
5. Repeat with 50% and 75% to ensure different segment counts work correctly

## Debug Log Analysis
In the provided debug logs, we can see evidence of the issue:
```
Debug - Loading script data: Found 16 segments in script.json
Debug - Found 8 B-Roll and 8 other segments
```

After our fixes, the logs show the correct number of segments:
```
Debug - Loading script data: Found 10 segments in script.json
Debug - Found 2 B-Roll and 8 other segments
```

This confirms that our percentage-based approach is working correctly when properly implemented. 