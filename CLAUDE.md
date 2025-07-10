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
- Slide capture offers two modes:
  - Standard mode: Traditional frame-by-frame comparison
  - Improved mode: Three-pass detection with multiple strategies (faster and more accurate)
- When processing completes successfully, the app offers to switch to the next logical tab
- The application supports both basic and AI-enhanced processing modes for generating documents from captured slides