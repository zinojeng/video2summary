#!/bin/bash
# 啟動 Folder Processor daemon
# 監控 ~/audio/
#   - 音訊檔案 → 轉錄+筆記
#   - 子資料夾（音訊+投影片）→ 轉錄+分析+合併筆記

cd ~/.openclaw/workspace/skills/audio-transcribe/scripts

# 載入環境變數
if [ -f .env ]; then
    source .env
fi

export PATH="/opt/homebrew/bin:$PATH"

# 確認 venv 存在
if [ ! -f ./venv/bin/python3 ]; then
    echo "❌ venv not found. Please create it first."
    exit 1
fi

# 如果已經在跑，先停掉
pkill -f "folder_processor.py --daemon" 2>/dev/null

# 建立目錄
mkdir -p ~/audio/done

LOG=~/audio/folder_processor.log

nohup ./venv/bin/python3 folder_processor.py --daemon >> "$LOG" 2>&1 </dev/null &
disown

echo "✅ Folder Processor daemon started (PID: $!)"
echo "📂 監控: ~/audio/"
echo "📋 Log: $LOG"
echo ""
echo "使用方式："
echo "  純音訊轉錄:    直接丟音訊檔到 ~/audio/"
echo "  音訊+投影片:   建立 ~/audio/講題名稱/ 然後丟音訊+投影片進去"
echo ""
echo "範例："
echo "  ~/audio/Pit-1.m4a                    → 轉錄+筆記"
echo "  ~/audio/HAE_黃教授/HAE.m4a           → 轉錄"
echo "  ~/audio/HAE_黃教授/slide_01.jpg      → +投影片分析+合併筆記"
