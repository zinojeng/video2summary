# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a video and audio processing tool (視頻音頻處理工具) with a GUI interface built using Python and Tkinter. The main functionality includes:

1. **Audio Extraction**: Extract audio from video files in various formats (MP3/WAV/AAC)
2. **Slide Capture**: Automatically detect slide changes in videos and save as images
3. **Slide Processing**: Convert captured slides to PowerPoint or Markdown files

## Common Commands

### Running the Application
```bash
python video_audio_processor.py
```

### Installing Dependencies
```bash
# Required dependencies
pip install moviepy opencv-python numpy pillow python-pptx scikit-image

# Optional dependencies
pip install markitdown>=0.1.1  # Enhanced Markdown generation
pip install openai>=1.0.0      # AI-assisted features
```

### Testing
```bash
# Test slide processing functionality
python test_slides.py
```

## Code Architecture

### Main Components

1. **video_audio_processor.py** (40KB)
   - Main GUI application using Tkinter with three tabs
   - Dynamically imports modules as needed to reduce startup time
   - Key classes:
     - `VideoAudioProcessor`: Main application class managing the GUI
   - Threading used for background processing to keep UI responsive

2. **markitdown_helper.py** (10KB)
   - Helper module for image-to-document conversion
   - Two main functions:
     - `convert_images_to_markdown()`: Converts images to Markdown with optional LLM analysis
     - `process_images_to_ppt()`: Converts images to PowerPoint presentations
   - Supports OpenAI Vision API for AI-powered image analysis when API key is provided

3. **test_slides.py**
   - Testing script for slide processing functionality
   - Creates test images and validates conversion pipelines

4. **improved_slide_capture.py** (New)
   - Enhanced slide capture module with multiple detection strategies
   - Three-pass detection: fast scan → precise detection → supplementary check
   - Key features:
     - Multi-strategy detection (histogram, edge detection, text region analysis)
     - Adaptive step size based on video length
     - Parallel processing capabilities
     - Deduplication using image hashing
   - Significantly faster while reducing missed slides

5. **slide_capture_advanced.py** (New)
   - Advanced slide capture with intelligent grouping
   - Uses perceptual hashing (pHash and dHash) for similarity detection
   - Groups similar slides automatically
   - File naming: `slide_g01-02_t10.5s_h1a2b3c.jpg`
     - g01-02: Group 1, slide 2
     - t10.5s: Timestamp
     - h1a2b3c: Content hash
   - Generates metadata JSON with detailed information
   
6. **slide_post_processor.py** (New)
   - Post-processing tool for managing captured slides
   - Features:
     - Show summary of captured slides and groups
     - Remove duplicates within groups
     - Select best slide from each group
     - Generate HTML preview page
   - Usage: `python slide_post_processor.py <slides_folder> --action <action>`

7. **batch_slide_capture.py** (New)
   - Batch processing tool for multiple videos
   - Features:
     - Process single video or entire folders
     - Recursive directory search option
     - Saves slides in same path as video (video_name_slides/)
     - Progress tracking and statistics
     - Auto-select best slides option
     - HTML preview generation for each video
   - Usage: `python batch_slide_capture.py <path> [--recursive] [--auto-select]`

### Key Technical Details

- **Video Processing**: Uses OpenCV (`cv2`) for frame extraction and scikit-image for SSIM calculations
- **Audio Processing**: Uses moviepy for audio extraction from videos
- **Slide Detection**: Compares frames using Structural Similarity Index (SSIM) with adjustable threshold
- **Document Generation**: 
  - PowerPoint: Uses python-pptx library
  - Markdown: Basic image embedding or AI-enhanced content extraction via OpenAI Vision API
- **GUI Threading**: Background operations run in separate threads to prevent UI freezing

### Dependencies Management

The application checks for required dependencies on startup and offers to install missing packages automatically. Optional packages (markitdown, openai) are checked separately and only suggested if the user wants to use those features.

### File Organization

- Captured slides are saved in folders named `video_slides_{video_name}`
- Audio files are saved with the original video name plus the audio format extension
- Generated documents keep the source folder name with appropriate extensions (.pptx, .md)

## Important Notes

- The GUI has three tabs corresponding to the three main functions
- Default similarity threshold for slide capture is 0.85 (adjustable via slider)
- Slide capture offers four modes:
  - Standard mode: Traditional frame-by-frame comparison
  - Improved mode: Three-pass detection with multiple strategies (faster and more accurate)
  - Ultra mode: Advanced animation detection (if available)
  - Advanced mode: Intelligent grouping with perceptual hashing
- When processing completes successfully, the app offers to switch to the next logical tab
- The application supports both basic and AI-enhanced processing modes for generating documents from captured slides

## Batch Processing Tools (批次處理工具)

### Slides Analysis (投影片分析)

1. **batch_slides_analysis.py**
   - Batch process slide folders for AI analysis using OpenAI GPT-4
   - Analyzes images in selected_slides folders to reduce API costs
   - Creates slides_analysis.md files with detailed content analysis
   - Supports GPT-4o-mini and GPT-4o models

2. **batch_process_full_slides.py**
   - Process folders without selected_slides subdirectories
   - Analyzes complete slides folders (limited to 30 images)
   - Handles special cases like CGM speaker presentations

### Transcription Notes (轉錄筆記)

1. **batch_transcription_notes_v2.py**
   - Process audio transcription files (*.txt, *.srt) with Gemini 2.5 Pro
   - Generates detailed speaker notes, NOT summaries
   - Features:
     - Preserves all speaker content and important details
     - Professional editing and error correction
     - Hierarchical structure organization
     - Bold, italic, and underline emphasis
     - Automatic agenda matching (RTF/RTFD/DOCX files)
   - Output: transcription-*_detailed_notes.md

2. **merge_notes_slides.py**
   - Merges speaker notes with slide analysis
   - Creates comprehensive two-in-one notes
   - Features:
     - Speaker content as main axis
     - Slide references: **(參見 Slide X)**
     - Extended interpretations with __underline__
     - Avoids duplication, only adds new information
     - Clear content correspondence
   - Output: transcription-*_merged_notes

### Progress Tracking

All batch tools support:
- Resume capability from interruptions
- Progress tracking in JSON files
- Detailed statistics and cost estimation
- Error handling and retry logic

## ADA2025 Processing Results

Successfully processed materials from ADA2025 conference:

### Slide Analysis
- **28** total slide folders
- **22** folders with selected_slides analyzed
- **100%** OpenAI coverage for available folders
- **31** total analyses including special cases

### Transcription Notes
- **21** transcription files processed (12 TXT + 9 SRT)
- **20** detailed speaker notes generated
- Used **1,265,808** Gemini tokens (~$9.49 USD)

### Merged Notes
- **14** comprehensive merged notes created
- Combined speaker content with slide analysis
- Used **537,109** Gemini tokens (~$4.03 USD)

### File Locations
- Slide analyses: `*_slides/selected_slides_analysis.md`
- Speaker notes: `transcription-*_detailed_notes.md`
- Merged notes: `transcription-*_merged_notes`