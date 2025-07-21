#!/bin/bash

# 工具啟動器 - 提供選擇不同工具的選單
# Tool Launcher - Menu for selecting different tools

# 設定顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 清除螢幕
clear

echo -e "${PURPLE}============================================${NC}"
echo -e "${PURPLE}     Video2Summary 工具選單 Tool Menu${NC}"
echo -e "${PURPLE}============================================${NC}"
echo

echo -e "${CYAN}請選擇要啟動的工具 Please select a tool:${NC}"
echo
echo -e "${YELLOW}1.${NC} GUI 主程式 - 視頻音頻處理器"
echo "   Main GUI - Video/Audio Processor"
echo
echo -e "${YELLOW}2.${NC} 批次處理工具選單"
echo "   Batch Processing Tools Menu"
echo
echo -e "${YELLOW}3.${NC} 音頻轉錄工具 (命令行)"
echo "   Audio Transcription Tool (CLI)"
echo
echo -e "${YELLOW}4.${NC} 投影片捕獲工具 (命令行)"
echo "   Slide Capture Tool (CLI)"
echo
echo -e "${RED}0.${NC} 退出 Exit"
echo

read -p "請輸入選項 Enter option (0-4): " choice

case $choice in
    1)
        echo -e "\n${GREEN}啟動 GUI 主程式...${NC}"
        echo "Starting Main GUI..."
        # 啟動虛擬環境並運行 GUI
        source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || {
            echo -e "${RED}找不到虛擬環境！請先創建虛擬環境。${NC}"
            echo "Virtual environment not found! Please create one first."
            exit 1
        }
        python video_audio_processor.py
        ;;
    
    2)
        echo -e "\n${GREEN}啟動批次處理工具選單...${NC}"
        echo "Starting Batch Processing Menu..."
        # 啟動虛擬環境並運行批次處理選單
        source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || {
            echo -e "${RED}找不到虛擬環境！請先創建虛擬環境。${NC}"
            echo "Virtual environment not found! Please create one first."
            exit 1
        }
        python batch_processing_menu.py
        ;;
    
    3)
        echo -e "\n${GREEN}音頻轉錄工具使用說明：${NC}"
        echo "Audio Transcription Tool Usage:"
        echo
        echo "python gpt4o_transcribe_improved.py <audio_file> [options]"
        echo
        echo "Options:"
        echo "  --format {text,markdown,srt}  輸出格式"
        echo "  --model {gpt-4o-transcribe,gpt-4o-mini-transcribe}  模型選擇"
        echo "  --language <code>  語言代碼 (如 zh, en)"
        echo "  --output <file>  輸出檔案路徑"
        echo
        echo -e "${YELLOW}範例 Example:${NC}"
        echo "python gpt4o_transcribe_improved.py audio.mp3 --format srt --output subtitles.srt"
        echo
        read -p "按 Enter 鍵返回選單 Press Enter to return to menu..."
        exec "$0"
        ;;
    
    4)
        echo -e "\n${GREEN}投影片捕獲工具使用說明：${NC}"
        echo "Slide Capture Tool Usage:"
        echo
        echo "python batch_processing/slides_analysis/batch_slide_capture.py <path> [options]"
        echo
        echo "Options:"
        echo "  --recursive  遞迴搜尋子資料夾"
        echo "  --auto-select  自動選擇最佳投影片"
        echo
        echo -e "${YELLOW}範例 Example:${NC}"
        echo "python batch_processing/slides_analysis/batch_slide_capture.py /path/to/videos --recursive"
        echo
        read -p "按 Enter 鍵返回選單 Press Enter to return to menu..."
        exec "$0"
        ;;
    
    0)
        echo -e "\n${CYAN}再見！Goodbye!${NC}"
        exit 0
        ;;
    
    *)
        echo -e "\n${RED}無效的選項！Invalid option!${NC}"
        sleep 2
        exec "$0"
        ;;
esac