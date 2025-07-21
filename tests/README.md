# Test Files 測試檔案

This directory contains test scripts for various components of the video2summary project.

## Audio Transcription Tests 音頻轉錄測試

- **test_gpt4o_transcribe.py** - Tests GPT-4o transcription functionality
- **test_improved_transcription.py** - Tests improved transcription with error handling
- **test_fix_transcription.py** - Tests transcription fixes and workarounds
- **test_single_transcription.py** - Tests single file transcription
- **debug_transcription.py** - Debug tool for audio transcription issues

## Slide Capture Tests 投影片捕獲測試

- **test_slides.py** - Basic slide processing functionality tests
- **test_improved_capture.py** - Tests improved slide capture with multi-strategy detection
- **test_advanced_capture.py** - Tests advanced capture with intelligent grouping
- **test_phash_dedup.py** - Tests perceptual hash deduplication functionality

## Running Tests 執行測試

```bash
# Run from project root directory
python tests/test_gpt4o_transcribe.py <audio_file>
python tests/test_improved_capture.py <video_file>

# Or make them executable
chmod +x tests/test_*.py
./tests/test_improved_transcription.py <audio_file>
```

## Note 注意

Some tests require:
- OpenAI API key for transcription tests
- ffmpeg installed for audio processing
- Sample video/audio files for testing