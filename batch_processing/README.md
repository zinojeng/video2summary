# Batch Processing Tools 批次處理工具

This directory contains all batch processing tools for handling large-scale video, audio, and slide processing tasks.

## Directory Structure 目錄結構

```
batch_processing/
├── slides_analysis/          # 投影片分析工具
│   ├── batch_slide_capture.py       # 批次捕獲投影片
│   ├── batch_slides_analysis.py     # 批次分析投影片 (OpenAI)
│   ├── batch_slides_analysis_gemini.py  # 批次分析投影片 (Gemini)
│   └── batch_process_full_slides.py # 處理完整投影片資料夾
│
├── transcription_notes/      # 轉錄筆記工具
│   ├── batch_transcription_notes_v2.py  # 批次處理轉錄文件 (v2)
│   ├── batch_transcription_notes.py     # 批次處理轉錄文件 (v1)
│   └── continue_transcription_notes.py  # 繼續處理剩餘文件
│
├── merge_tools/             # 合併工具
│   └── merge_notes_slides.py    # 合併演講筆記與投影片分析
│
├── reports/                 # 報告工具
│   ├── transcription_notes_final_report.py  # 轉錄筆記處理報告
│   └── merge_notes_final_report.py          # 合併筆記最終報告
│
├── batch_process_resume.py          # 恢復中斷的處理 (Gemini)
└── batch_process_resume_openai.py   # 恢復中斷的處理 (OpenAI)
```

## Workflow 工作流程

### Complete Processing Pipeline 完整處理流程

1. **Extract Slides from Videos 從影片提取投影片**
   ```bash
   python batch_processing/slides_analysis/batch_slide_capture.py <video_path> [--recursive] [--auto-select]
   ```

2. **Transcribe Audio 轉錄音頻**
   ```bash
   python gpt4o_transcribe_improved.py <audio_file> --output transcript.txt
   ```

3. **Generate Speaker Notes 生成演講筆記**
   ```bash
   python batch_processing/transcription_notes/batch_transcription_notes_v2.py <base_path> <gemini_api_key>
   ```

4. **Analyze Slides 分析投影片**
   ```bash
   python batch_processing/slides_analysis/batch_slides_analysis.py <base_path> <openai_api_key>
   ```

5. **Merge Notes and Slides 合併筆記與投影片**
   ```bash
   python batch_processing/merge_tools/merge_notes_slides.py <base_path> <gemini_api_key>
   ```

6. **Generate Reports 生成報告**
   ```bash
   python batch_processing/reports/merge_notes_final_report.py
   ```

## Usage 使用方法

### Using the Menu System 使用選單系統

The easiest way to use these tools is through the menu system:

```bash
# Main launcher (includes all tools)
./run_gui.sh

# Or directly access batch processing menu
python batch_processing_menu.py
```

### Direct Usage 直接使用

Each tool can also be run directly with appropriate arguments:

```bash
# Example: Batch capture slides from a folder
python batch_processing/slides_analysis/batch_slide_capture.py /path/to/videos --recursive --auto-select

# Example: Process transcriptions
python batch_processing/transcription_notes/batch_transcription_notes_v2.py /path/to/ADA2025 $GEMINI_API_KEY
```

## API Keys Required 需要的 API 金鑰

- **OpenAI API Key**: For slide analysis and GPT-4o transcription
- **Gemini API Key**: For transcription notes and merging tools

Set environment variables:
```bash
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"
```

## Progress Tracking 進度追蹤

All batch tools create progress JSON files:
- `slides_analysis_progress.json`
- `transcription_notes_progress_v2.json`
- `merge_notes_progress.json`

These files allow resuming interrupted processes.

## Output Files 輸出檔案

- **Slide Analysis**: `*_slides/selected_slides_analysis.md`
- **Speaker Notes**: `transcription-*_detailed_notes.md`
- **Merged Notes**: `transcription-*_merged_notes.md`