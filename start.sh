#!/bin/bash

# 視頻和音頻處理工具啟動腳本
# Video and Audio Processor Startup Script

# 設定顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 獲取腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 切換到腳本目錄
cd "$SCRIPT_DIR"

# 虛擬環境目錄名稱
VENV_DIR="venv"

# 顯示歡迎訊息
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   視頻和音頻處理工具啟動腳本${NC}"
echo -e "${BLUE}   Video Audio Processor Launcher${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 檢查 Python3 是否安裝
echo -e "${YELLOW}檢查系統環境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}錯誤：未找到 Python3，請先安裝 Python3${NC}"
    echo -e "${RED}Error: Python3 not found, please install Python3 first${NC}"
    exit 1
fi

# 顯示 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "Python 版本: ${GREEN}$PYTHON_VERSION${NC}"

# 檢查 Python 版本是否符合要求 (>=3.8)
PYTHON_VERSION_NUM=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION_NUM" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}錯誤：Python 版本必須為 3.8 或更高版本${NC}"
    echo -e "${RED}Error: Python version must be 3.8 or higher${NC}"
    exit 1
fi

# 檢查虛擬環境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo -e "${YELLOW}虛擬環境不存在，準備建立...${NC}"
    echo -e "${YELLOW}Virtual environment not found, creating...${NC}"
    
    # 建立虛擬環境
    echo -e "${BLUE}正在建立虛擬環境...${NC}"
    python3 -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}錯誤：無法建立虛擬環境${NC}"
        echo -e "${RED}Error: Failed to create virtual environment${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 虛擬環境建立完成${NC}"
    echo -e "${GREEN}✓ Virtual environment created successfully${NC}"
    FIRST_RUN=true
else
    echo -e "${GREEN}✓ 找到現有虛擬環境${NC}"
    echo -e "${GREEN}✓ Found existing virtual environment${NC}"
    FIRST_RUN=false
fi

# 啟動虛擬環境
echo ""
echo -e "${YELLOW}啟動虛擬環境...${NC}"
echo -e "${YELLOW}Activating virtual environment...${NC}"

# 根據作業系統選擇啟動腳本
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source "$VENV_DIR/Scripts/activate"
else
    # macOS/Linux
    source "$VENV_DIR/bin/activate"
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}錯誤：無法啟動虛擬環境${NC}"
    echo -e "${RED}Error: Failed to activate virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 虛擬環境已啟動${NC}"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# 升級 pip
if [ "$FIRST_RUN" = true ]; then
    echo ""
    echo -e "${YELLOW}升級 pip 到最新版本...${NC}"
    echo -e "${YELLOW}Upgrading pip to latest version...${NC}"
    python -m pip install --upgrade pip --quiet
    echo -e "${GREEN}✓ pip 已升級${NC}"
    echo -e "${GREEN}✓ pip upgraded${NC}"
fi

# 檢查 requirements.txt 是否存在
if [ -f "requirements.txt" ]; then
    echo ""
    echo -e "${YELLOW}檢查並安裝依賴套件...${NC}"
    echo -e "${YELLOW}Checking and installing dependencies...${NC}"
    
    # 檢查是否需要安裝/更新依賴
    if [ "$FIRST_RUN" = true ]; then
        NEED_INSTALL=true
    else
        # 檢查是否有新的依賴需要安裝
        echo -e "${BLUE}檢查依賴更新...${NC}"
        pip install --dry-run -r requirements.txt 2>&1 | grep -q "Would install"
        if [ $? -eq 0 ]; then
            NEED_INSTALL=true
        else
            NEED_INSTALL=false
        fi
    fi
    
    if [ "$NEED_INSTALL" = true ]; then
        echo -e "${BLUE}安裝必要依賴套件...${NC}"
        echo -e "${BLUE}Installing required packages...${NC}"
        
        # 顯示將要安裝的套件
        echo ""
        echo -e "${BLUE}必要套件 (Required packages):${NC}"
        echo "  - moviepy (視頻/音頻處理)"
        echo "  - opencv-python (視頻幀分析)"
        echo "  - numpy (數值計算)"
        echo "  - pillow (圖像處理)"
        echo "  - python-pptx (PowerPoint生成)"
        echo "  - scikit-image (圖像相似度計算)"
        
        echo ""
        echo -e "${BLUE}可選套件 (Optional packages):${NC}"
        echo "  - markitdown (增強型Markdown生成)"
        echo "  - openai (AI輔助功能)"
        echo ""
        
        # 安裝依賴
        pip install -r requirements.txt
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}警告：部分依賴套件安裝失敗${NC}"
            echo -e "${RED}Warning: Some dependencies failed to install${NC}"
            echo -e "${YELLOW}程式可能無法正常運行所有功能${NC}"
            echo -e "${YELLOW}Some features may not work properly${NC}"
        else
            echo -e "${GREEN}✓ 所有依賴套件安裝完成${NC}"
            echo -e "${GREEN}✓ All dependencies installed successfully${NC}"
        fi
    else
        echo -e "${GREEN}✓ 所有依賴套件已是最新版本${NC}"
        echo -e "${GREEN}✓ All dependencies are up to date${NC}"
    fi
else
    echo -e "${RED}警告：找不到 requirements.txt 文件${NC}"
    echo -e "${RED}Warning: requirements.txt not found${NC}"
    echo -e "${YELLOW}將嘗試直接運行程式，但可能缺少必要的依賴${NC}"
    echo -e "${YELLOW}Will try to run the program, but dependencies may be missing${NC}"
fi

# 檢查主程式文件
MAIN_FILE="video_audio_processor.py"
if [ ! -f "$MAIN_FILE" ]; then
    echo ""
    echo -e "${RED}錯誤：找不到主程式文件 $MAIN_FILE${NC}"
    echo -e "${RED}Error: Main program file $MAIN_FILE not found${NC}"
    exit 1
fi

# 檢查 CLAUDE.md 文件
if [ ! -f "CLAUDE.md" ]; then
    echo ""
    echo -e "${YELLOW}提示：CLAUDE.md 文件不存在${NC}"
    echo -e "${YELLOW}Note: CLAUDE.md file not found${NC}"
    echo -e "${BLUE}這個文件包含項目的開發指南，對使用 Claude Code 很有幫助${NC}"
    echo -e "${BLUE}This file contains development guidelines helpful for Claude Code${NC}"
fi

# 顯示啟動訊息
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}環境準備完成，正在啟動應用程式...${NC}"
echo -e "${GREEN}Environment ready, launching application...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}工作目錄 (Working Directory): ${NC}$SCRIPT_DIR"
echo -e "${BLUE}虛擬環境 (Virtual Environment): ${NC}$VIRTUAL_ENV"
echo ""

echo -e "${BLUE}========================================${NC}"
echo ""

# 執行主程式
python "$MAIN_FILE"

# 儲存執行結果
EXIT_CODE=$?

# 檢查執行結果
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "${RED}程式執行失敗，錯誤代碼: $EXIT_CODE${NC}"
    echo -e "${RED}Program execution failed with error code: $EXIT_CODE${NC}"
    echo ""
    echo -e "${YELLOW}可能的解決方案:${NC}"
    echo -e "${YELLOW}Possible solutions:${NC}"
    echo "  1. 檢查是否所有依賴都已正確安裝"
    echo "     Check if all dependencies are installed correctly"
    echo "  2. 確認 Python 版本為 3.8 或以上"
    echo "     Ensure Python version is 3.8 or higher"
    echo "  3. 查看上方的錯誤訊息"
    echo "     Check the error message above"
    echo ""
    
    # 在錯誤時保持終端開啟
    echo -e "${YELLOW}按任意鍵退出... (Press any key to exit...)${NC}"
    read -n 1 -s
else
    echo ""
    echo -e "${GREEN}✓ 程式執行完成${NC}"
    echo -e "${GREEN}✓ Program execution completed${NC}"
fi

# 退出虛擬環境
deactivate 2>/dev/null

exit $EXIT_CODE