#!/bin/bash
# 啟動 Telegram Bot daemon
cd ~/.openclaw/workspace/skills/audio-transcribe/scripts

# 載入環境變數
if [ -f .env ]; then
    source .env
fi
export PATH="/opt/homebrew/bin:$PATH"

# 停止舊的 bot
pkill -f "tg_bot.py" 2>/dev/null
sleep 1

# 建立目錄
mkdir -p ~/audio/done

LOG=~/audio/tg_bot.log

# 啟動
nohup ./venv/bin/python3 tg_bot.py --daemon >> "$LOG" 2>&1 </dev/null &
disown

PID=$!
echo "✅ Telegram Bot 啟動 (PID: $PID)"
echo "📋 Log: $LOG"
echo ""
echo "指令："
echo "  /status  — 查詢處理狀態"
echo "  /list    — 最近處理的檔案"
echo "  /rerun   — 重新處理檔案"
echo "  /pending — 待處理的檔案"
echo "  /help    — 說明"
echo ""
echo "傳送音訊檔到 bot → 自動轉錄 + 筆記"
