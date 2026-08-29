#!/bin/bash
# ============================================
# inbox_watcher.sh (v2 — with summarization)
# 監控 Google Drive Audio 資料夾，偵測新音訊/影片
# 自動轉錄 → 自動摘要 → 回寫 Drive + Telegram 通知
#
# 用法：
#   ./inbox_watcher.sh              # 前景執行（看 log）
#   ./inbox_watcher.sh --daemon     # 背景執行
#   ./inbox_watcher.sh --once       # 只掃一次就結束
#   ./inbox_watcher.sh --stop       # 停止背景執行
#   ./inbox_watcher.sh --status     # 查看運行狀態
#   ./inbox_watcher.sh --reset      # 清除處理記錄
# ============================================

# ===== 監控來源：Google Drive Audio 資料夾 =====
GDRIVE_AUDIO="${GDRIVE_AUDIO:-$HOME/Library/CloudStorage/GoogleDrive-<你的帳號>/我的雲端硬碟/audio}"

# ===== 本機工作目錄 =====
WORK_DIR="$HOME/inbox"
DONE_DIR="$HOME/inbox/done"
PROCESSING_DIR="$HOME/inbox/processing"
LOG_FILE="$HOME/inbox/watcher.log"
PID_FILE="$HOME/inbox/.watcher.pid"
PROCESSED_LIST="$HOME/inbox/.processed_files"
POLL_INTERVAL=30

# ===== Skill 路徑 =====
SKILL_DIR="$HOME/.openclaw/workspace/skills/audio-transcribe/scripts"
PYTHON="$SKILL_DIR/venv/bin/python3"
TRANSCRIBER="$SKILL_DIR/gpt4o_transcribe_clawbot.py"
SUMMARIZER="$SKILL_DIR/summarize_transcript.py"
GMAIL_PROCESSOR="$SKILL_DIR/gmail_audio_processor.py"

# ===== 摘要設定 =====
SUMMARIZE_ENABLED=true           # 是否啟用自動摘要
SUMMARIZE_PROVIDER="openai"      # openai 或 gemini（實際模型見 model_config.py）
SUMMARIZE_STYLE="medical"        # medical / meeting / lecture / general

# ===== Gmail 發送設定（使用 gws CLI）=====
EMAIL_ENABLED=true               # 是否啟用 Email 發送
EMAIL_TO="${EMAIL_TO:-}"  # 收件人（請用環境變數設定）
GWS_CMD="$(command -v gws 2>/dev/null || echo "$HOME/.npm-global/bin/gws")"

# ===== 載入 API Keys =====
if [ -f "$SKILL_DIR/.env" ]; then
    source "$SKILL_DIR/.env"
fi
if [ -z "$OPENAI_API_KEY" ]; then
    OPENAI_API_KEY=$(python3 -c "
import json
with open('$HOME/.openclaw/openclaw.json') as f:
    d = json.load(f)
print(d.get('env',{}).get('OPENAI_API_KEY',''))
" 2>/dev/null)
    export OPENAI_API_KEY
fi

# ===== Telegram 通知設定 =====
TG_BOT_TOKEN="${TG_BOT_TOKEN:-}"
TG_CHAT_ID="${TG_CHAT_ID:-}"

# 支援的音訊/影片格式
AUDIO_EXTS="mp3 m4a wav ogg opus flac aac wma"
VIDEO_EXTS="mp4 mov mkv avi webm"

# 顏色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg" >> "$LOG_FILE"
    if [ "$DAEMON_MODE" != "true" ]; then
        echo -e "$msg"
    fi
}

send_telegram() {
    local message="$1"
    if [ -n "$TG_BOT_TOKEN" ] && [ -n "$TG_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            -d chat_id="$TG_CHAT_ID" \
            -d text="$message" \
            -d parse_mode="Markdown" \
            > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            log "  📨 Telegram 通知已發送"
        else
            log "  ⚠️ Telegram 通知發送失敗"
        fi
    fi
}

send_email() {
    local subject="$1"
    local body_file="$2"
    local stem="$3"

    if [ "$EMAIL_ENABLED" != "true" ]; then
        return 0
    fi

    if [ ! -x "$GWS_CMD" ] && ! command -v gws &>/dev/null; then
        log "  ⚠️ gws CLI 未安裝，跳過 Email 發送"
        return 1
    fi

    # 取得可用的 gws 指令
    local gws_bin
    if command -v gws &>/dev/null; then
        gws_bin="gws"
    else
        gws_bin="$GWS_CMD"
    fi

    # 讀取筆記內容（截取前 50000 字避免超長）
    local body
    if [ -f "$body_file" ]; then
        body=$(head -c 50000 "$body_file")
    else
        body="筆記檔案未找到: $body_file"
    fi

    log "  📧 發送 Email: ${subject}"

    "$gws_bin" gmail +send \
        --to "$EMAIL_TO" \
        --subject "$subject" \
        --body "$body" \
        2>&1 | while IFS= read -r line; do
            log "    $line"
        done

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "  📧 Email 已發送到 ${EMAIL_TO}"
        return 0
    else
        log "  ⚠️ Email 發送失敗"
        return 1
    fi
}

get_gdrive_search_url() {
    local filename="$1"
    local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$filename'))" 2>/dev/null)
    echo "https://drive.google.com/drive/search?q=${encoded}"
}

is_media_file() {
    local ext="${1##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    for e in $AUDIO_EXTS $VIDEO_EXTS; do
        if [ "$ext" = "$e" ]; then
            return 0
        fi
    done
    return 1
}

is_file_stable() {
    local file="$1"
    local size1=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    sleep 3
    local size2=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    [ "$size1" = "$size2" ] && [ "$size1" -gt 0 ]
}

is_already_processed() {
    local file="$1"
    local filename=$(basename "$file")
    local filesize=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    local key="${filename}|${filesize}"
    if [ -f "$PROCESSED_LIST" ]; then
        grep -qF "$key" "$PROCESSED_LIST"
        return $?
    fi
    return 1
}

mark_as_processed() {
    local file="$1"
    local filename=$(basename "$file")
    local filesize=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    local key="${filename}|${filesize}"
    echo "$key" >> "$PROCESSED_LIST"
}

# ============================================
# 摘要函式
# ============================================
summarize_transcript() {
    local transcript_file="$1"
    local stem="$2"
    local output_dir="$3"

    if [ "$SUMMARIZE_ENABLED" != "true" ]; then
        log "  ⏭️ 摘要功能已停用，跳過"
        return 0
    fi

    if [ ! -f "$SUMMARIZER" ]; then
        log "  ⚠️ 找不到摘要程式 $SUMMARIZER，跳過摘要"
        return 1
    fi

    local summary_file="${output_dir}/${stem}_detailed_notes.md"

    log "${CYAN}📝 開始摘要: ${stem}.txt → ${stem}_detailed_notes.md${NC}"

    cd "$SKILL_DIR" && source venv/bin/activate

    "$PYTHON" "$SUMMARIZER" \
        "$transcript_file" \
        --provider "$SUMMARIZE_PROVIDER" \
        --style "$SUMMARIZE_STYLE" \
        --output "$summary_file" \
        2>&1 | while IFS= read -r line; do
            log "  $line"
        done

    local exit_code=${PIPESTATUS[0]}

    if [ $exit_code -eq 0 ] && [ -f "$summary_file" ]; then
        log "${GREEN}✓ 摘要完成: ${stem}_detailed_notes.md${NC}"
        return 0
    else
        log "${RED}✗ 摘要失敗 (exit code: $exit_code)${NC}"
        return 1
    fi
}

# ============================================
# 轉錄 + 摘要 完整 pipeline
# ============================================
transcribe_file() {
    local file="$1"
    local filename=$(basename "$file")
    local stem="${filename%.*}"

    log "${CYAN}🎙️ 開始轉錄: ${filename}${NC}"

    # 從 Google Drive 複製到 processing
    cp "$file" "$PROCESSING_DIR/$filename"
    local process_file="$PROCESSING_DIR/$filename"

    if [ ! -f "$process_file" ]; then
        log "${RED}✗ 複製失敗: ${filename}${NC}"
        return 1
    fi

    # 輸出到 Google Drive Audio 資料夾
    local output_file="${GDRIVE_AUDIO}/${stem}.txt"

    # === Step 1: 轉錄 ===
    cd "$SKILL_DIR" && source venv/bin/activate

    "$PYTHON" "$TRANSCRIBER" \
        "$process_file" \
        --language zh \
        --format text \
        --output "$output_file" \
        2>&1 | while IFS= read -r line; do
            log "  $line"
        done

    local exit_code=${PIPESTATUS[0]}

    if [ $exit_code -eq 0 ] && [ -f "$output_file" ]; then
        log "${GREEN}✓ 轉錄完成: ${filename} → ${stem}.txt${NC}"
        mark_as_processed "$file"
        mv "$process_file" "$DONE_DIR/$filename"
        cp "$output_file" "$DONE_DIR/${stem}.txt"

        local char_count=$(wc -m < "$output_file" | tr -d ' ')
        local gdrive_link=$(get_gdrive_search_url "${stem}.txt")

        # 發轉錄完成通知
        send_telegram "✅ *轉錄完成*
🎙️ ${filename}
📝 ${stem}.txt (${char_count} 字)
📂 [Google Drive](${gdrive_link})"

        # === Step 2: 摘要 ===
        summarize_transcript "$output_file" "$stem" "$GDRIVE_AUDIO"
        local sum_exit=$?

        if [ $sum_exit -eq 0 ]; then
            local summary_file="${GDRIVE_AUDIO}/${stem}_detailed_notes.md"
            if [ -f "$summary_file" ]; then
                cp "$summary_file" "$DONE_DIR/${stem}_detailed_notes.md"
                local sum_chars=$(wc -m < "$summary_file" | tr -d ' ')
                local sum_link=$(get_gdrive_search_url "${stem}_detailed_notes.md")

                send_telegram "📋 *筆記完成*
📝 ${stem}\_detailed_notes.md (${sum_chars} 字)
🏷️ 風格: ${SUMMARIZE_STYLE}
📂 [Google Drive](${sum_link})"

                # === Step 3: Email 發送 ===
                send_email "📋 ${stem} - 整理筆記" "$summary_file" "$stem"
            fi
        fi
    else
        log "${RED}✗ 轉錄失敗: ${filename} (exit code: $exit_code)${NC}"
        rm -f "$process_file"

        send_telegram "❌ *轉錄失敗*
🎙️ ${filename}
請檢查 ~/inbox/watcher.log"
    fi
}

scan_gdrive() {
    if [ ! -d "$GDRIVE_AUDIO" ]; then
        log "${RED}✗ Google Drive Audio 資料夾不存在: $GDRIVE_AUDIO${NC}"
        return 0
    fi

    for file in "$GDRIVE_AUDIO"/*; do
        [ -f "$file" ] || continue
        local filename=$(basename "$file")

        [[ "$filename" == .* ]] && continue
        [[ "$filename" == *.txt ]] && continue
        [[ "$filename" == *.md ]] && continue
        [[ "$filename" == *.srt ]] && continue
        [[ "$filename" == *.json ]] && continue
        [[ "$filename" == *Icon* ]] && continue

        if is_media_file "$filename"; then
            is_already_processed "$file" && continue

            if is_file_stable "$file"; then
                transcribe_file "$file"
            else
                log "${YELLOW}⏳ 檔案同步中，稍後處理: ${filename}${NC}"
            fi
        fi
    done
}

scan_inbox() {
    for file in "$WORK_DIR"/*; do
        [ -f "$file" ] || continue
        local filename=$(basename "$file")

        [[ "$filename" == .* ]] && continue
        [[ "$filename" == *.log ]] && continue
        [[ "$filename" == *.txt ]] && continue
        [[ "$filename" == *.md ]] && continue
        [[ "$filename" == *.srt ]] && continue

        if is_media_file "$filename"; then
            if is_file_stable "$file"; then
                log "${CYAN}🎙️ 開始轉錄 (inbox): ${filename}${NC}"
                local stem="${filename%.*}"
                mv "$file" "$PROCESSING_DIR/$filename"
                local process_file="$PROCESSING_DIR/$filename"
                local output_file="$WORK_DIR/${stem}.txt"

                cd "$SKILL_DIR" && source venv/bin/activate

                "$PYTHON" "$TRANSCRIBER" \
                    "$process_file" \
                    --language zh \
                    --format text \
                    --output "$output_file" \
                    2>&1 | while IFS= read -r line; do
                        log "  $line"
                    done

                if [ ${PIPESTATUS[0]} -eq 0 ] && [ -f "$output_file" ]; then
                    log "${GREEN}✓ 轉錄完成: ${filename} → ${stem}.txt${NC}"
                    mv "$process_file" "$DONE_DIR/$filename"
                    cp "$output_file" "$DONE_DIR/${stem}.txt"

                    local char_count=$(wc -m < "$output_file" | tr -d ' ')
                    send_telegram "✅ *轉錄完成* (inbox)
🎙️ ${filename}
📝 ${stem}.txt (${char_count} 字)
📁 結果在 ~/inbox/${stem}.txt"

                    # === 摘要 (inbox) ===
                    summarize_transcript "$output_file" "$stem" "$WORK_DIR"
                    if [ $? -eq 0 ]; then
                        local summary_file="$WORK_DIR/${stem}_detailed_notes.md"
                        if [ -f "$summary_file" ]; then
                            cp "$summary_file" "$DONE_DIR/${stem}_detailed_notes.md"
                            local sum_chars=$(wc -m < "$summary_file" | tr -d ' ')
                            send_telegram "📋 *筆記完成* (inbox)
📝 ${stem}\_detailed_notes.md (${sum_chars} 字)
🏷️ 風格: ${SUMMARIZE_STYLE}"

                            # === Email 發送 (inbox) ===
                            send_email "📋 ${stem} - 整理筆記" "$summary_file" "$stem"
                        fi
                    fi
                else
                    log "${RED}✗ 轉錄失敗: ${filename}${NC}"
                    mv "$process_file" "$WORK_DIR/$filename"

                    send_telegram "❌ *轉錄失敗*
🎙️ ${filename}
請檢查 ~/inbox/watcher.log"
                fi
            fi
        fi
    done
}

setup_dirs() {
    mkdir -p "$WORK_DIR" "$DONE_DIR" "$PROCESSING_DIR"
    touch "$PROCESSED_LIST"
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            rm -f "$PID_FILE"
            echo "Watcher stopped (PID: $pid)"
        else
            rm -f "$PID_FILE"
            echo "Watcher was not running"
        fi
    else
        echo "No PID file found"
    fi
    exit 0
}

show_status() {
    echo "===== Inbox Watcher v2 (with Summarization) ====="
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "狀態: 🟢 運行中 (PID: $(cat "$PID_FILE"))"
    else
        echo "狀態: 🔴 未運行"
    fi
    if [ -f "$PROCESSED_LIST" ]; then
        echo "已處理: $(wc -l < "$PROCESSED_LIST" | tr -d ' ') 個檔案"
    fi
    if [ -d "$GDRIVE_AUDIO" ]; then
        pending=0
        for f in "$GDRIVE_AUDIO"/*; do
            [ -f "$f" ] || continue
            fname=$(basename "$f")
            is_media_file "$fname" && ! is_already_processed "$f" && ((pending++))
        done 2>/dev/null
        echo "待處理 (Google Drive): $pending 個檔案"
    fi
    echo ""
    echo "摘要: $([ "$SUMMARIZE_ENABLED" = "true" ] && echo "✅ 啟用" || echo "⏭️ 停用")"
    echo "摘要模型: $SUMMARIZE_PROVIDER"
    echo "摘要風格: $SUMMARIZE_STYLE"
    echo ""
    echo "Email: $([ "$EMAIL_ENABLED" = "true" ] && echo "✅ 啟用 → ${EMAIL_TO}" || echo "⏭️ 停用")"
    if command -v gws &>/dev/null || [ -x "$GWS_CMD" ]; then
        echo "gws CLI: ✅ 已安裝"
    else
        echo "gws CLI: ⚠️ 未安裝（npm install -g @googleworkspace/cli）"
    fi
    echo ""
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "OpenAI Key: ✅ 已設定"
    else
        echo "OpenAI Key: ⚠️ 未設定"
    fi
    if [ -n "$GEMINI_API_KEY" ]; then
        echo "Gemini Key: ✅ 已設定"
    else
        echo "Gemini Key: ⚠️ 未設定（摘要需要）"
    fi
    exit 0
}

# ============================================
# 主程式
# ============================================

DAEMON_MODE="false"
ONCE_MODE="false"

case "${1:-}" in
    --daemon)
        DAEMON_MODE="true"
        ;;
    --once)
        ONCE_MODE="true"
        ;;
    --stop)
        stop_daemon
        ;;
    --status)
        show_status
        ;;
    --reset)
        rm -f "$PROCESSED_LIST"
        echo "已清除處理記錄，下次掃描會重新處理所有檔案"
        exit 0
        ;;
    --no-summary)
        SUMMARIZE_ENABLED=false
        ;;
    --help|-h)
        echo "用法: $0 [選項]"
        echo ""
        echo "  (無參數)      前景執行，持續監控"
        echo "  --daemon      背景執行"
        echo "  --once        掃描一次就結束"
        echo "  --stop        停止背景程序"
        echo "  --status      查看運行狀態"
        echo "  --reset       清除處理記錄"
        echo "  --no-summary  不執行摘要"
        echo ""
        echo "監控來源："
        echo "  1. Google Drive: $GDRIVE_AUDIO"
        echo "  2. SCP Inbox:    $WORK_DIR"
        echo ""
        echo "摘要設定："
        echo "  Provider: $SUMMARIZE_PROVIDER"
        echo "  Style:    $SUMMARIZE_STYLE"
        exit 0
        ;;
esac

# 檢查 API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "錯誤: 未設定 OPENAI_API_KEY"
    exit 1
fi

if [ ! -f "$TRANSCRIBER" ]; then
    echo "錯誤: 找不到轉錄程式 $TRANSCRIBER"
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo "錯誤: 找不到 Python 虛擬環境 $PYTHON"
    exit 1
fi

setup_dirs

if [ "$DAEMON_MODE" = "true" ]; then
    nohup "$0" > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    echo "Watcher v2 started in background (PID: $!)"
    echo "Log: $LOG_FILE"
    echo ""
    echo "監控來源："
    echo "  1. Google Drive: $GDRIVE_AUDIO"
    echo "  2. SCP Inbox:    $WORK_DIR"
    echo ""
    echo "摘要: ✅ ${SUMMARIZE_PROVIDER} / ${SUMMARIZE_STYLE}"
    echo "Email: $([ "$EMAIL_ENABLED" = "true" ] && echo "✅ → ${EMAIL_TO}" || echo "⏭️ 停用")"
    exit 0
fi

log "========================================="
log "📥 Inbox Watcher v2 啟動（含自動摘要）"
log "  Google Drive: $GDRIVE_AUDIO"
log "  SCP Inbox:    $WORK_DIR"
log "  完成目錄:     $DONE_DIR"
log "  輪詢間隔:     ${POLL_INTERVAL}s"
log "  摘要:         $([ "$SUMMARIZE_ENABLED" = "true" ] && echo "✅ ${SUMMARIZE_PROVIDER}/${SUMMARIZE_STYLE}" || echo "⏭️ 停用")"
log "  Email:        $([ "$EMAIL_ENABLED" = "true" ] && echo "✅ → ${EMAIL_TO}" || echo "⏭️ 停用")"
log "========================================="

scan_gmail() {
    if [ "$EMAIL_ENABLED" != "true" ]; then
        return 0
    fi
    if [ ! -f "$GMAIL_PROCESSOR" ]; then
        return 0
    fi
    if ! command -v gws &>/dev/null && [ ! -x "$GWS_CMD" ]; then
        return 0
    fi
    log "📬 掃描 Gmail 收件匣..."
    cd "$SKILL_DIR" && source venv/bin/activate
    "$PYTHON" "$GMAIL_PROCESSOR" 2>&1 | while IFS= read -r line; do
        log "  $line"
    done
}

if [ "$ONCE_MODE" = "true" ]; then
    scan_gdrive
    scan_inbox
    scan_gmail
    exit 0
fi

while true; do
    scan_gdrive
    scan_inbox
    scan_gmail
    sleep "$POLL_INTERVAL"
done
