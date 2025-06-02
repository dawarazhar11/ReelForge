# A-Roll/B-Roll Enhancement Project Implementation Checklist

## Overview
This document tracks implementation progress for the new A-Roll/B-Roll functionality that improves how videos are assembled using a single A-Roll file with B-Roll visuals mapped to specific timestamps.

## 1. Data Structure Revisions

- [ ] Update segment data structure to accurately represent single A-Roll file with timestamps
- [ ] Revise B-Roll segment structure to include:
  - [ ] Link to timestamp in A-Roll
  - [ ] Support for multiple visuals per B-Roll segment
  - [ ] Duration controls for each visual
- [ ] Create new sequence format that follows the pattern:
  - A1 → (B1+A2) → (B2+A3) → (B3+A4)

## 2. A-Roll Transcription Page Updates

- [ ] Implement timeline visualization showing A-Roll with timestamp markers
- [ ] Add visual indicators for B-Roll placement along the A-Roll timeline
- [ ] Create UI for mapping B-Roll visuals to specific timestamp ranges in A-Roll
- [ ] Add controls for B-Roll sub-segmentation (multiple visuals per segment)
- [ ] Update B-Roll generation logic to work with timestamps rather than segments
- [ ] Implement preview of sequence flow with proper B-Roll/A-Roll mapping

## 3. B-Roll Management Enhancements

- [ ] Create interface for managing multiple visuals within single B-Roll segment
- [ ] Add duration controls for each B-Roll visual
- [ ] Implement visual transition options between sub-segments
- [ ] Add controls to adjust B-Roll placement on the timeline
- [ ] Implement B-Roll preview functionality

## 4. Video Assembly Logic Overhaul

- [ ] Remove existing segment stitching approach
- [ ] Implement new assembly algorithm based on A-Roll timestamps and B-Roll mappings
- [ ] Create logic for:
  - [ ] Starting with first A-Roll section (full video and audio)
  - [ ] Overlaying B-Roll visuals with next A-Roll section audio
  - [ ] Handling transitions between segments
- [ ] Update progress tracking and error handling for new assembly process

## 5. Ollama Integration for B-Roll Prompts

- [ ] Ensure Ollama-generated prompts align with timestamp-specific content
- [ ] Modify prompt generation to reference specific A-Roll content at timestamps
- [ ] Update storage format for B-Roll prompts to include timestamp references

## 6. UI/UX Improvements

- [ ] Create visual sequence preview showing the full assembly flow
- [ ] Add clear visual differentiation between A-Roll and B-Roll sections
- [ ] Implement drag-and-drop interface for adjusting B-Roll placement
- [ ] Add visual indicators showing the 60/40 split between A-Roll and B-Roll when applicable
- [ ] Create comprehensive help system explaining the new workflow

## 7. Testing and Validation

- [ ] Test with various A-Roll lengths and B-Roll configurations
- [ ] Validate correct audio mapping between segments
- [ ] Test B-Roll sub-segment handling
- [ ] Verify smooth transitions between segments
- [ ] Test with different visual types (images, videos)
- [ ] Validate Ollama integration functionality

## 8. Documentation and Refinement

- [ ] Update user documentation to explain new workflow
- [ ] Create visual guides for timeline and segment mapping
- [ ] Document the new assembly sequence with examples
- [ ] Add tooltips and in-app guidance for new features
- [ ] Implement any refinements based on initial testing

## 9. Final Deployment

- [ ] Package all changes into a cohesive update
- [ ] Ensure backward compatibility with existing projects where possible
- [ ] Create migration path for projects using the old format
- [ ] Deploy final version with comprehensive release notes

## Progress Tracking

| Phase | Started | Completed | Notes |
|-------|---------|-----------|-------|
| Data Structure Revisions | ❌ | ❌ | |
| A-Roll Transcription Updates | ❌ | ❌ | |
| B-Roll Management | ❌ | ❌ | |
| Video Assembly Logic | ❌ | ❌ | |
| Ollama Integration | ✅ | ❌ | Basic implementation complete |
| UI/UX Improvements | ❌ | ❌ | |
| Testing | ❌ | ❌ | |
| Documentation | ❌ | ❌ | |
| Deployment | ❌ | ❌ | |

## Implementation Notes

### Current Implementation Status
- Basic Ollama integration for generating B-Roll prompts has been implemented
- Initial 60/40 split for A-Roll/B-Roll overlay has been added but needs revision
- Session state variables have been updated to support new functionality

### Next Steps
1. Update the data structures to support timestamp-based mapping
2. Implement the timeline visualization in the A-Roll transcription page
3. Revise the assembly logic to follow the new sequence pattern

### Questions/Decisions Needed
- Decision on how to handle transitions between segments
- Format for storing multiple B-Roll visuals per segment
- UI approach for timeline visualization 