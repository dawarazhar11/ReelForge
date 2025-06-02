# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Video Assembly feature now supports transcription-based A-Roll videos
  - B-Roll segments are now overlaid on the full A-Roll video based on timestamps
  - Improved handling of segment timing information
  - Added UI to display transcription-based A-Roll information
- A-Roll Transcription feature with:
  - Video upload and automatic transcription using Whisper
  - Automatic segmentation of transcription
  - Editing capability for transcribed segments
  - B-Roll generation for each A-Roll segment
  - Theme selection for B-Roll generation (minimal, balanced, maximum)
  - Custom theme creation
  - Distinct styling for B-Roll segments

### Fixed
- Fixed navigation issues throughout the app
  - Updated references to the old "5A A-Roll Video Production" page
  - Replaced them with references to the new "A-Roll Transcription" page
  - Fixed navigation paths in multiple files
- Fixed KeyError in A-Roll Transcription page
  - Added robust handling for timing information in segments
  - Implemented default values for missing timing data
  - Enhanced format_time function to handle errors

## [0.1.0] - 2023-05-01

### Added
- Initial release
- Basic video editing capabilities
- Script generation
- B-Roll generation
- Video assembly 