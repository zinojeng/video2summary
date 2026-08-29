#!/bin/bash

# Video2Summary GUI launcher menu
# 提供簡易選單，以啟動 GUI 或改進模式批次幻燈片捕獲

set -euo pipefail

# 顏色設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    # 若已在虛擬環境中，直接返回
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        return
    fi

    # 偵測既有 venv
    local activate=""
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        activate="$VENV_DIR/bin/activate"
    elif [[ -f ".venv/bin/activate" ]]; then
        activate=".venv/bin/activate"
    fi

    # 若找不到，自動建立
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

    # 啟動既有虛擬環境
    # shellcheck disable=SC1090
    source "$activate"
}

ensure_venv

# ============================================================
# 選單主迴圈
# ============================================================
while true; do
    clear
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}        Video2Summary GUI 啟動選單         ${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
    echo -e "  ${YELLOW}1.${NC} 啟動 GUI 主程式 (video_audio_processor.py)"
    echo -e "  ${YELLOW}2.${NC} 改進模式批次截圖 (capture_slides_improved)"
    echo -e "  ${RED}0.${NC} 離開"
    echo
    read -rp "請輸入選項 (0-2): " choice

    case "$choice" in
        1)
            echo
            echo -e "${GREEN}啟動 GUI 主程式...${NC}"
            python "video_audio_processor.py"
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        2)
            echo
            read -rp "請輸入影片檔或資料夾路徑: " target_path
            if [[ -z "${target_path:-}" ]]; then
                echo "未輸入路徑，返回選單。"
                read -rp $'\n按 Enter 返回選單...' _
                continue
            fi

            read -rp "是否遞迴搜尋子資料夾？ (y/N): " recursive_ans
            read -rp "是否自動挑選代表幻燈片？ (y/N): " auto_select_ans
            read -rp "是否強制重新處理 (忽略既有輸出/轉錄)？ (y/N): " force_ans
            read -rp "是否僅列出將處理的影片？ (y/N): " list_only_ans
            read -rp "是否輸出 PowerPoint？ (Y/n): " ppt_ans
            read -rp "相似度閾值 [0.85]: " threshold_input

            threshold_value="0.85"
            if [[ -n "${threshold_input// }" ]]; then
                threshold_value="$threshold_input"
            fi

            cmd=("python" "batch_processing/slides_analysis/batch_slide_capture_improved.py" "$target_path" "--threshold" "$threshold_value")

            [[ "$recursive_ans" =~ ^[Yy]$ ]]    && cmd+=("--recursive")
            [[ "$auto_select_ans" =~ ^[Yy]$ ]]   && cmd+=("--auto-select")
            [[ "$force_ans" =~ ^[Yy]$ ]]          && cmd+=("--force")
            [[ "$list_only_ans" =~ ^[Yy]$ ]]      && cmd+=("--list-only")
            [[ "$ppt_ans" =~ ^[Nn]$ ]]            && cmd+=("--no-ppt")

            echo
            echo -e "執行指令: ${cmd[*]}"
            echo "--------------------------------------------"
            "${cmd[@]}"
            echo "--------------------------------------------"
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        0)
            echo
            echo -e "${GREEN}再見！${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}無效的選項，請重新輸入。${NC}"
            sleep 1.5
            ;;
    esac
done
