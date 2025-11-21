#!/bin/bash

# Video2Summary GUI launcher menu
# 提供簡易選單，以啟動 GUI 或改進模式批次幻燈片捕獲

set -euo pipefail

# 切換到腳本所在的專案根目錄，確保 Python 模組可被找到
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

# 嘗試啟動虛擬環境
activate_venv() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        return
    fi
    if [[ -f "venv/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source "venv/bin/activate"
    elif [[ -f ".venv/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source ".venv/bin/activate"
    else
        echo "找不到虛擬環境！請先建立 venv 或 .venv" >&2
        exit 1
    fi
}

activate_venv

# 選單主迴圈
while true; do
    clear
    echo "============================================"
    echo "        Video2Summary GUI 啟動選單         "
    echo "============================================"
    echo
    echo "1. 啟動 GUI 主程式 (video_audio_processor.py)"
    echo "2. 改進模式批次截圖 (capture_slides_improved)"
    echo "0. 離開"
    echo
    read -rp "請輸入選項 (0-2): " choice

    case "$choice" in
        1)
            echo
            echo "啟動 GUI 主程式..."
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

            if [[ "$recursive_ans" =~ ^[Yy]$ ]]; then
                cmd+=("--recursive")
            fi
            if [[ "$auto_select_ans" =~ ^[Yy]$ ]]; then
                cmd+=("--auto-select")
            fi
            if [[ "$force_ans" =~ ^[Yy]$ ]]; then
                cmd+=("--force")
            fi
            if [[ "$list_only_ans" =~ ^[Yy]$ ]]; then
                cmd+=("--list-only")
            fi
            if [[ "$ppt_ans" =~ ^[Nn]$ ]]; then
                cmd+=("--no-ppt")
            fi

            echo
            echo "執行指令: ${cmd[*]}"
            echo "--------------------------------------------"
            "${cmd[@]}"
            echo "--------------------------------------------"
            read -rp $'\n按 Enter 返回選單...' _
            ;;
        0)
            echo
            echo "再見！"
            exit 0
            ;;
        *)
            echo "\n無效的選項，請重新輸入。"
            sleep 1.5
            ;;
    esac
done
