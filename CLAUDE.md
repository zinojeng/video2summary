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
# Or use the shortcut:
./run_gui.sh
```

### Audio Transcription
```bash
python gpt4o_transcribe_improved.py <audio_file> [options]

# Interactive menu (model / language / format / batch)
./transcribe_audio_v2.sh

# Debug helpers live under tests/
python tests/debug_transcription.py <audio_file>
```

See **Audio Transcription** below for model choice and the full flag list.

### Installing Dependencies
```bash
pip install -r requirements.txt
brew install ffmpeg   # macOS: required for conversion, splitting and duration
```

API keys are read from the environment (or a local `.env`, which is gitignored):

```bash
export OPENAI_API_KEY=...    # gpt-transcribe, whisper-1, GPT vision/notes
export GEMINI_API_KEY=...    # gemini-3.5-transcribe and all Gemini models
```

### Testing
```bash
python tests/test_slides.py   # slide processing
```

## Code Architecture

### Main Components

0. **model_config.py**
   - Single source of truth for every model ID, organised by role
   - `upgrade_legacy_model()` maps retired IDs to current ones
   - Change models here; tools import role constants instead of literals

0b. **gemini_transcribe.py**
   - `gemini-3.5-transcribe` backend via the new `google-genai` SDK
     (`client.interactions`, not `GenerativeModel.generate_content`)
   - Groups word annotations into segments on speaker change, length and duration
   - Returns the same `{'text', 'segments'}` shape as the OpenAI path, so the
     SRT / translation / merge pipelines are shared
   - `generate_text()` provides Gemini text generation for translation

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

## AI Models (模型設定)

**All model IDs live in `model_config.py`. Change models there, not in individual
tools.** Each tool imports a role constant (`OPENAI_VISION`, `GEMINI_NOTES`, …)
rather than hardcoding a string, so bumping a model is a one-file edit.

Models are retired quickly. Verify against the live API rather than trusting
docs or this file:

```bash
python -c "from openai import OpenAI; print([m.id for m in OpenAI().models.list()])"
python -c "from google import genai; print([m.name for m in genai.Client().models.list()])"
```

References: [OpenAI models](https://developers.openai.com/api/docs/models) ·
[Gemini models](https://ai.google.dev/gemini-api/docs/models)

### Roles and current defaults

| Role | OpenAI | Gemini | Used by |
|---|---|---|---|
| Transcription | `gpt-transcribe` | `gemini-3.5-transcribe` | transcription pipeline |
| Timestamped transcription | `whisper-1` | (Gemini covers this) | SRT with real timings |
| Notes / summary | `gpt-5.6-terra` | `gemini-3.7-flash` | speaker notes, merged notes |
| Heavy reasoning | `gpt-5.6-sol` | `gemini-3.1-pro-preview` | reserved, more expensive |
| Slide vision (bulk) | `gpt-5.6-luna` | `gemini-3.5-flash-lite` | batch slide analysis |
| Slide vision (dense) | `gpt-5.6-terra` | `gemini-3.7-flash` | tables, charts |
| Translation | `gpt-5.6-terra` | `gemini-3.5-flash-lite` | subtitle/text translation |

`upgrade_legacy_model()` maps retired IDs to current ones, so old configs and
saved commands keep working.

### Model gotchas

- **`gemini-2.0-flash-exp` is shut down.** Any code still naming it fails outright.
- **Gemini 3.x rejects `temperature` / `top_p` / `top_k`** and returns 400. Old
  `GenerationConfig(temperature=...)` calls must drop those fields.
- **Transcription models cannot generate text.** Passing `gpt-transcribe` or
  `gemini-3.5-transcribe` to a chat/translate call fails or silently misroutes.
  `resolve_translation_model()` maps a transcription model to a text model from
  the same provider.
- **Two different Google SDKs are in play, and one is dead.**
  `gemini-3.5-transcribe` needs the new `google-genai` (`client.interactions`).
  The `batch_processing/` notes and merge tools plus `markitdown_helper_gemini.py`
  still import `google.generativeai`, which now prints *"All support for the
  `google.generativeai` package has ended"* on import. Their bump to
  `gemini-3.7-flash` is **untested** — an unmaintained SDK may not be able to
  address current models at all. Migrating these to `google-genai` is the next
  piece of work; until then, run one file end to end before trusting a batch.

## Audio Transcription

### Choosing a model

| | Text accuracy | Timestamps | Speaker labels |
|---|---|---|---|
| `gpt-transcribe` | best | estimated only | no |
| `whisper-1` | worst | real | no |
| `gemini-3.5-transcribe` | middle | real | yes (up to 8) |

Neither `gpt-transcribe` nor the legacy `gpt-4o-transcribe` returns segment
timestamps, so their SRT timings are estimated from character counts and scaled
to the real audio duration. **For accurate subtitles use
`gemini-3.5-transcribe`; for speaker-labelled conference notes it is the only
option.**

### gemini-3.5-transcribe constraints

Discovered by live testing; **not in Google's documentation**:

- `custom_vocabulary` is incompatible with diarization **and** with word
  timestamps. The three are mutually exclusive — the API returns 400. `keywords`
  are dropped automatically when annotations are on; pass
  `--no-diarization --no-word-timestamps` to prefer the vocabulary instead.
- Requesting diarization without word timestamps returns **zero** annotations,
  so no speaker labels appear. Speaker identity rides on the word records, so
  the code enables word timestamps whenever diarization is requested.
- Speaker ids come back as `spk:0`, `spk:1`, not `spk_1`.
- Limits: 1 hour per request, **30 minutes** once diarization or timestamps are
  on. Segment length defaults to 1800s for Gemini and 600s for OpenAI's 25MB cap.
- Mandarin must be sent as `cmn-Hans-CN`; Google's supported-language table has
  no `zh-TW`. Output script varies run to run — add `--translate zh-tw` if you
  need reliable Traditional Chinese.

### Usage

```bash
# Default: gpt-transcribe
python gpt4o_transcribe_improved.py audio.mp3

# Speaker labels + real timestamps (conference recordings)
python gpt4o_transcribe_improved.py audio.mp3 --model gemini-3.5-transcribe --format srt

# Domain terms instead of speaker labels
python gpt4o_transcribe_improved.py audio.mp3 --model gemini-3.5-transcribe \
    --keywords "HbA1c,GLP-1,dapagliflozin" --no-diarization --no-word-timestamps

# OpenAI with term hints
python gpt4o_transcribe_improved.py audio.mp3 --keywords "HbA1c,GLP-1"

# Output formats
python gpt4o_transcribe_improved.py audio.mp3 --format markdown --output notes.md
python gpt4o_transcribe_improved.py audio.mp3 --format srt --output subs.srt

# Translation (routed to a text model of the same provider automatically)
python gpt4o_transcribe_improved.py audio.mp3 --format srt --translate en,zh-tw

# Keep a legacy model instead of auto-upgrading
python gpt4o_transcribe_improved.py audio.mp3 --model gpt-4o-transcribe --allow-legacy-model
```

### How the pipeline works

1. Video input has its audio extracted first.
2. Format conversion to 16kHz mono MP3, skipped for already-compatible formats
   (`.mp3/.m4a/.wav`, plus `.flac/.ogg/.aac` on the Gemini path).
3. Splitting by duration; ffmpeg's trailing remainder is dropped when under a
   second, since Gemini rejects such fragments and OpenAI wastes a request.
4. Per-segment transcription with resume: results are cached in
   `<audio>_parts/segments/` keyed by a `run_signature` covering model, language,
   keywords, diarization, timestamps and segment length. Changing any of them
   re-transcribes rather than returning a stale result.
5. Merge — segment timestamps are relative and get their offset added once.
6. Optional translation, then output as text / markdown / SRT.

### Known API behaviours

- OpenAI **silently ignores unknown body parameters** on the transcription
  endpoint, so a request succeeding does not prove a parameter took effect.
- GPT-transcribe-family models accept only `json` and `text` response formats;
  `srt`/`vtt` and `timestamp_granularities` require `whisper-1`, which needs
  `verbose_json` to return segments at all.
- Files over 25MB must be split for OpenAI. Gemini uploads via the Files API
  and is bounded by duration instead.

## Batch Processing Tools (批次處理工具)

The batch processing tools are now organized in the `batch_processing/` directory with a user-friendly menu system.

### Quick Start (快速開始)

```bash
# Launch the main tool menu
./run_tools.sh

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
   - Batch process slide folders for AI vision analysis (OpenAI)
   - Analyzes images in selected_slides folders to reduce API costs
   - Creates slides_analysis.md files with detailed content analysis
   - Model comes from `model_config.OPENAI_VISION`; override with `--model`

3. **batch_process_full_slides.py**
   - Process folders without selected_slides subdirectories
   - Analyzes complete slides folders (limited to 30 images)
   - Handles special cases like CGM speaker presentations

### Transcription Notes (轉錄筆記)

1. **batch_transcription_notes_v2.py**
   - Process audio transcription files (*.txt, *.srt) with `model_config.GEMINI_NOTES`
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

Historical record of one completed run. The token counts and costs below reflect
the models in use at the time (`gemini-2.5-pro`, `gpt-4o-mini`), not the current
defaults in `model_config.py`.

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