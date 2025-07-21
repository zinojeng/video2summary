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
# Use the main launcher menu:
./run_gui.sh

# Or run directly:
python video_audio_processor.py
```

### Audio Transcription (Improved)
```bash
# Use improved transcription tool
python gpt4o_transcribe_improved.py <audio_file>

# Or use the shortcut script:
./transcribe_audio.sh <audio_file> [options]

# Debug audio issues
python debug_transcription.py <audio_file>

# Test transcription
python test_improved_transcription.py <audio_file>
```

### Installing Dependencies
```bash
# Required dependencies
pip install moviepy opencv-python numpy pillow python-pptx scikit-image

# Optional dependencies
pip install markitdown>=0.1.1  # Enhanced Markdown generation
pip install openai>=1.0.0      # AI-assisted features

# For improved audio transcription
pip install ffmpeg-python      # Optional: for programmatic ffmpeg usage
brew install ffmpeg            # macOS: for audio format conversion
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

### Audio Transcription Improvements (2025-07-20)

**New features to handle "Audio file might be corrupted or unsupported" errors:**

1. **gpt4o_transcribe_improved.py** - Standalone improved transcription tool
   - Auto-converts audio to compatible MP3 format (16kHz, mono, 64kbps CBR)
   - Handles large files (>25MB) with automatic segmentation
   - Proper filename and MIME type handling
   - Detailed error messages with solutions

2. **Automatic Format Conversion**
   - Converts any audio format to high-compatibility MP3
   - Uses ffmpeg with optimal parameters for OpenAI API
   - Preserves original files

3. **Large File Support**
   - Automatically splits files larger than 25MB into 10-minute segments
   - Processes segments and combines results
   - Maintains transcription continuity
   - Shows progress for each segment

4. **Enhanced Error Handling**
   - Detailed diagnostics for format issues
   - Uses GPT-4o models (gpt-4o-transcribe, gpt-4o-mini-transcribe)
   - Clear error messages with suggested fixes

5. **Output Format Support**
   - **Text format (.txt)**: Plain text transcription
   - **Markdown format (.md)**: Adds header "# 語音轉錄結果"
   - **SRT format (.srt)**: Subtitle format with timestamps
   - Auto-adds file extensions if not specified
   - Format-specific processing for better readability

6. **Integration**
   - video_audio_processor.py now uses improved transcription
   - Backward compatible with existing code
   - Falls back to original method if improved module unavailable

### Common Audio Transcription Issues and Solutions

1. **"Audio file might be corrupted or unsupported"**
   - **Cause**: OpenAI API strict format requirements
   - **Solution**: gpt4o_transcribe_improved.py auto-converts to compatible MP3 format

2. **"File size exceeds 25MB limit"**
   - **Cause**: OpenAI API file size limitation
   - **Solution**: Automatic splitting into 10-minute segments

3. **"response_format 'srt' is not compatible with model"**
   - **Cause**: GPT-4o models only support 'text' and 'json' formats
   - **Solution**: Gets text format and converts to SRT with timestamps

4. **"'str' object has no attribute 'text'"**
   - **Cause**: GPT-4o models return string directly, not object
   - **Solution**: Checks response type and handles accordingly

5. **Incomplete transcription appearance**
   - **Cause**: Long paragraphs make content seem shorter
   - **Solution**: Added double line breaks between segments for better readability

### Usage Examples

```bash
# Basic transcription
python gpt4o_transcribe_improved.py audio.mp3

# Specify output format
python gpt4o_transcribe_improved.py audio.mp3 --format text --output transcript.txt
python gpt4o_transcribe_improved.py audio.mp3 --format markdown --output transcript.md
python gpt4o_transcribe_improved.py audio.mp3 --format srt --output subtitles.srt

# Choose model
python gpt4o_transcribe_improved.py audio.mp3 --model gpt-4o-transcribe    # Higher quality
python gpt4o_transcribe_improved.py audio.mp3 --model gpt-4o-mini-transcribe  # Faster

# Specify language
python gpt4o_transcribe_improved.py audio.mp3 --language zh  # Chinese
python gpt4o_transcribe_improved.py audio.mp3 --language en  # English

# Disable auto-conversion (not recommended)
python gpt4o_transcribe_improved.py audio.mp3 --no-convert
```

## Batch Processing Tools (批次處理工具)

The batch processing tools are now organized in the `batch_processing/` directory with a user-friendly menu system.

### Quick Start (快速開始)

```bash
# Launch the main tool menu (includes all tools)
./run_gui.sh

# Or directly launch batch processing menu
python batch_processing_menu.py
```

### Directory Structure (目錄結構)

```
batch_processing/
├── slides_analysis/          # 投影片分析工具
├── transcription_notes/      # 轉錄筆記工具  
├── merge_tools/             # 合併工具
├── reports/                 # 報告工具
└── README.md               # 詳細文檔
```

### Slides Analysis (投影片分析)

1. **batch_slide_capture.py**
   - Batch capture slides from videos
   - Supports recursive directory search
   - Auto-select best slides option
   - HTML preview generation

2. **batch_slides_analysis.py**
   - Batch process slide folders for AI analysis using OpenAI GPT-4
   - Analyzes images in selected_slides folders to reduce API costs
   - Creates slides_analysis.md files with detailed content analysis
   - Supports GPT-4o-mini and GPT-4o models

3. **batch_process_full_slides.py**
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

2. **continue_transcription_notes.py**
   - Continue processing remaining transcription files
   - Checks progress and resumes from interruption

### Merge Tools (合併工具)

1. **merge_notes_slides.py**
   - Merges speaker notes with slide analysis
   - Creates comprehensive two-in-one notes
   - Features:
     - Speaker content as main axis
     - Slide references: **(參見 Slide X)**
     - Extended interpretations with __underline__
     - Avoids duplication, only adds new information
     - Clear content correspondence
   - Output: transcription-*_merged_notes.md

### Reports (報告工具)

1. **transcription_notes_final_report.py**
   - Generate final report for transcription processing
   - Shows statistics and cost estimation

2. **merge_notes_final_report.py**
   - Generate final report for merged notes
   - Lists all successfully merged conferences

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