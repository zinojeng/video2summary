#!/bin/bash

# 音頻轉錄快捷腳本

# 檢查參數
if [ $# -eq 0 ]; then
    echo "使用方法: ./transcribe_audio.sh <音頻檔案> [選項]"
    echo ""
    echo "選項:"
    echo "  --model <model>      模型選擇 (gpt-4o-transcribe, gpt-4o-mini-transcribe, whisper-1)"
    echo "  --format <format>    輸出格式 (text, markdown, srt)"
    echo "  --output <file>      輸出檔案路徑"
    echo "  --no-convert         不自動轉換音頻格式"
    echo ""
    echo "範例:"
    echo "  ./transcribe_audio.sh audio.mp3"
    echo "  ./transcribe_audio.sh audio.m4a --format srt --output audio.srt"
    exit 1
fi

# 啟動虛擬環境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 執行改進的轉錄程式
python gpt4o_transcribe_improved.py "$@"