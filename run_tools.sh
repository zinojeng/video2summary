#!/bin/bash

# 工具啟動器 - 提供選擇不同工具的選單
# Tool Launcher - Menu for selecting different tools

set -euo pipefail

# 顏色設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 切換到腳本所在的專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

VENV_DIR="venv"
REQ_FILE="requirements.txt"

# ============================================================
# 自動建立 / 啟動虛擬環境
# ============================================================
ensure_venv() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        return
    fi

    local activate=""
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        activate="$VENV_DIR/bin/activate"
    elif [[ -f ".venv/bin/activate" ]]; then
        activate=".venv/bin/activate"
    fi

    if [[ -z "$activate" ]]; then
        echo -e "${YELLOW}虛擬環境不存在，自動建立中...${NC}"

        if ! command -v python3 &>/dev/null; then
            echo -e "${RED}錯誤：找不到 python3，請先安裝 Python 3.8+${NC}"
            exit 1
        fi

        python3 -m venv "$VENV_DIR"
        activate="$VENV_DIR/bin/activate"

        # shellcheck disable=SC1090
        source "$activate"

        echo -e "${YELLOW}升級 pip...${NC}"
        python -m pip install --upgrade pip --quiet

        if [[ -f "$REQ_FILE" ]]; then
            echo -e "${YELLOW}安裝依賴套件 ($REQ_FILE)...${NC}"
            pip install -r "$REQ_FILE"
        fi

        echo -e "${GREEN}✓ 虛擬環境建立完成並已安裝依賴${NC}"
        echo
        return
    fi

    # shellcheck disable=SC1090
    source "$activate"
}

ensure_venv

# ============================================================
# 選單主迴圈
# ============================================================
while true; do
    clear
    echo -e "${PURPLE}============================================${NC}"
    echo -e "${PURPLE}     Video2Summary 工具選單 Tool Menu${NC}"
    echo -e "${PURPLE}============================================${NC}"
    echo
    echo -e "  ${YELLOW}1.${NC} GUI 主程式 - 視頻音頻處理器"
    echo -e "     Main GUI - Video/Audio Processor"
    echo
    echo -e "  ${YELLOW}2.${NC} 批次處理工具選單"
    echo -e "     Batch Processing Tools Menu"
    echo
    echo -e "  ${YELLOW}3.${NC} 音頻轉錄工具 (命令行)"
    echo -e "     Audio Transcription Tool (CLI)"
    echo
    echo -e "  ${YELLOW}4.${NC} 投影片捕獲工具 (命令行)"
    echo -e "     Slide Capture Tool (CLI)"
    echo
    echo -e "  ${RED}0.${NC} 退出 Exit"
    echo
    read -rp "請輸入選項 Enter option (0-4): " choice

    case "$choice" in
        1)
            echo -e "\n${GREEN}啟動 GUI 主程式...${NC}"
            python video_audio_processor.py
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        2)
            echo -e "\n${GREEN}啟動批次處理工具選單...${NC}"
            python batch_processing_menu.py
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        3)
            echo
            echo -e "${GREEN}音頻轉錄工具使用說明：${NC}"
            echo
            echo "python gpt4o_transcribe_improved.py <audio_file> [options]"
            echo
            echo "Options:"
            echo "  --format {text,markdown,srt}  輸出格式"
            echo "  --model {gpt-transcribe,gemini-3.5-transcribe}  模型選擇"
            echo "  --language <code>  語言代碼 (如 zh, en)"
            echo "  --output <file>  輸出檔案路徑"
            echo
            echo -e "${YELLOW}範例：${NC}"
            echo "python gpt4o_transcribe_improved.py audio.mp3 --format srt --output subtitles.srt"
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        4)
            echo
            echo -e "${GREEN}投影片捕獲工具使用說明：${NC}"
            echo
            echo "python batch_processing/slides_analysis/batch_slide_capture.py <path> [options]"
            echo
            echo "Options:"
            echo "  --recursive    遞迴搜尋子資料夾"
            echo "  --auto-select  自動選擇最佳投影片"
            echo
            echo -e "${YELLOW}範例：${NC}"
            echo "python batch_processing/slides_analysis/batch_slide_capture.py /path/to/videos --recursive"
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        0)
            echo -e "\n${CYAN}再見！Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}無效的選項！Invalid option!${NC}"
            sleep 1.5
            ;;
    esac
done
