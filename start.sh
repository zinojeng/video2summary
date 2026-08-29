#!/bin/bash

# Video2Summary 啟動腳本
# 自動建立虛擬環境、安裝依賴、啟動 GUI 主程式

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
MAIN_FILE="video_audio_processor.py"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Video2Summary 啟動腳本${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# ============================================================
# 1. 檢查 Python
# ============================================================
echo -e "${YELLOW}檢查系統環境...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}錯誤：找不到 python3，請先安裝 Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION="$(python3 --version 2>&1)"
echo -e "Python 版本: ${GREEN}$PYTHON_VERSION${NC}"

PYTHON_VER_NUM="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' )"
REQUIRED_VER="3.8"

if [[ "$(printf '%s\n' "$REQUIRED_VER" "$PYTHON_VER_NUM" | sort -V | head -n1)" != "$REQUIRED_VER" ]]; then
    echo -e "${RED}錯誤：Python 版本必須為 3.8 或更高${NC}"
    exit 1
fi

# ============================================================
# 2. 自動建立 / 啟動虛擬環境
# ============================================================
FIRST_RUN=false

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo -e "${GREEN}✓ 已在虛擬環境中${NC}"
elif [[ -f "$VENV_DIR/bin/activate" ]]; then
    echo -e "${GREEN}✓ 找到現有虛擬環境${NC}"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
elif [[ -f ".venv/bin/activate" ]]; then
    echo -e "${GREEN}✓ 找到現有虛擬環境 (.venv)${NC}"
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
else
    echo -e "${YELLOW}虛擬環境不存在，自動建立中...${NC}"
    python3 -m venv "$VENV_DIR"

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}錯誤：無法建立虛擬環境${NC}"
        exit 1
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    FIRST_RUN=true
    echo -e "${GREEN}✓ 虛擬環境建立完成${NC}"
fi

echo -e "${GREEN}✓ 虛擬環境已啟動${NC}"

# ============================================================
# 3. 安裝依賴
# ============================================================
if [[ "$FIRST_RUN" == true ]]; then
    echo
    echo -e "${YELLOW}升級 pip...${NC}"
    python -m pip install --upgrade pip --quiet
    echo -e "${GREEN}✓ pip 已升級${NC}"
fi

if [[ -f "$REQ_FILE" ]]; then
    if [[ "$FIRST_RUN" == true ]]; then
        NEED_INSTALL=true
    else
        # 快速檢查是否有缺少的套件
        if ! pip install --dry-run -r "$REQ_FILE" 2>&1 | grep -q "Would install"; then
            NEED_INSTALL=false
        else
            NEED_INSTALL=true
        fi
    fi

    if [[ "$NEED_INSTALL" == true ]]; then
        echo
        echo -e "${YELLOW}安裝依賴套件...${NC}"
        pip install -r "$REQ_FILE"

        if [[ $? -ne 0 ]]; then
            echo -e "${RED}警告：部分依賴套件安裝失敗，程式可能無法正常運行所有功能${NC}"
        else
            echo -e "${GREEN}✓ 所有依賴套件安裝完成${NC}"
        fi
    else
        echo -e "${GREEN}✓ 所有依賴套件已是最新版本${NC}"
    fi
else
    echo -e "${RED}警告：找不到 $REQ_FILE，將嘗試直接運行${NC}"
fi

# ============================================================
# 4. 啟動主程式
# ============================================================
if [[ ! -f "$MAIN_FILE" ]]; then
    echo -e "${RED}錯誤：找不到主程式 $MAIN_FILE${NC}"
    exit 1
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}環境準備完成，正在啟動應用程式...${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "工作目錄: ${BLUE}$SCRIPT_DIR${NC}"
echo -e "虛擬環境: ${BLUE}$VIRTUAL_ENV${NC}"
echo

python "$MAIN_FILE"
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo
    echo -e "${RED}程式執行失敗，錯誤代碼: $EXIT_CODE${NC}"
    echo -e "${YELLOW}可能的解決方案：${NC}"
    echo "  1. 檢查是否所有依賴都已正確安裝"
    echo "  2. 確認 Python 版本為 3.8 或以上"
    echo "  3. 查看上方的錯誤訊息"
    echo
    read -rp "按 Enter 退出..." _
else
    echo
    echo -e "${GREEN}✓ 程式執行完成${NC}"
fi

deactivate 2>/dev/null
exit $EXIT_CODE
