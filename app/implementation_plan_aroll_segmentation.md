# Automatic A-Roll Segmentation and B-Roll Generation Implementation Plan

## Overview
This plan outlines the implementation of automatic video segmentation for A-Roll content and the generation of matching B-Roll prompts using the Ollama mistral:7b-instruct-v0.3-q4_K_M model.

## Implementation Checklist

### Phase 1: A-Roll Video Processing and Transcription
- [x] 1.1 Enhance the video upload functionality to process videos for segmentation
- [x] 1.2 Implement transcription of the A-Roll video using existing transcription tools
- [x] 1.3 Add timestamp extraction for accurate segment timing
- [x] 1.4 Create a data structure to hold transcription with timestamps

### Phase 2: Logical Segmentation Using Ollama
- [x] 2.1 Set up Ollama integration with the mistral:7b-instruct-v0.3-q4_K_M model
- [x] 2.2 Design prompts for logical sentence segmentation analysis
- [x] 2.3 Implement function to send transcription to Ollama for segmentation
- [x] 2.4 Process Ollama's response to identify logical segment boundaries
- [x] 2.5 Create segment objects with start and end timestamps

### Phase 3: A-Roll Video Segmentation
- [x] 3.1 Create utility to cut the A-Roll video based on determined segments
- [x] 3.2 Implement preview functionality for the segmented A-Roll
- [x] 3.3 Add manual adjustment capability for segment boundaries
- [x] 3.4 Set up storage for segmented A-Roll videos

### Phase 4: B-Roll Prompt Generation Using Ollama
- [x] 4.1 Design prompt templates for B-Roll content that matches A-Roll context
- [x] 4.2 Implement function to send A-Roll segment content to Ollama
- [x] 4.3 Process Ollama responses to extract B-Roll descriptions
- [x] 4.4 Create storage for B-Roll prompts linked to A-Roll segments
- [x] 4.5 Implement manual editing capability for generated B-Roll prompts

### Phase 5: B-Roll Generation Integration
- [ ] 5.1 Modify existing B-Roll generation workflow to use the new prompts
- [ ] 5.2 Update UI to show progress of B-Roll generation for each segment
- [ ] 5.3 Implement proper error handling and retries for failed generations
- [ ] 5.4 Set up storage for generated B-Roll content linked to segments

### Phase 6: Video Assembly Integration
- [ ] 6.1 Update Video Assembly page to recognize the new segmentation format
- [ ] 6.2 Implement functions to stitch A-Roll and B-Roll segments based on logical mapping
- [ ] 6.3 Add preview capability for the assembled segments
- [ ] 6.4 Implement final video export with all segments properly stitched

### Phase 7: UI/UX Enhancements
- [x] 7.1 Design and implement progress indicators for the segmentation process
- [x] 7.2 Create visualizations for segment boundaries on a timeline
- [x] 7.3 Add drag-and-drop functionality for manual segment adjustment
- [x] 7.4 Implement segment preview in the UI

### Phase 8: Testing and Optimization
- [ ] 8.1 Test with various video types and lengths
- [ ] 8.2 Optimize Ollama prompts for better segmentation accuracy
- [ ] 8.3 Measure and optimize performance for longer videos
- [ ] 8.4 Implement caching to avoid reprocessing

## Technical Components

### Ollama Integration
- Endpoint: Local Ollama API
- Model: mistral:7b-instruct-v0.3-q4_K_M
- Expected latency: 2-5 seconds per request
- Prompting strategy: Few-shot learning with examples of good logical segments

### Video Processing
- Using existing MoviePy or similar libraries
- Maintaining audio quality during segmentation
- Handling timing alignment between transcript and video

### Data Flow
1. Video upload → Transcription → Ollama segmentation
2. Segmented transcription → A-Roll video cutting
3. Segment content → Ollama B-Roll prompt generation
4. B-Roll prompts → Existing B-Roll generation
5. A-Roll + B-Roll segments → Video assembly

## Implementation Strategy

- Start with core Ollama integration and testing
- Implement simple segmentation first, then refine with more complex logic
- Build on existing transcription and B-Roll generation pipelines
- Use progressive enhancement: get basic functionality working, then improve UX
- Maintain backward compatibility with existing manual workflows 