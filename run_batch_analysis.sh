#!/bin/bash

# 批量分析幻燈片內容的便捷腳本

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帶顏色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[錯誤]${NC} $1"
}

# 顯示標題
clear
echo "=============================================="
echo "       批量幻燈片內容 AI 分析工具"
echo "=============================================="
echo ""

# 設置默認路徑
DEFAULT_PATH="/Volumes/WD_BLACK/國際年會/ADA2025"

# 獲取路徑
echo "請輸入要分析的文件夾路徑"
echo "默認: $DEFAULT_PATH"
read -p "路徑 [回車使用默認]: " USER_PATH

if [ -z "$USER_PATH" ]; then
    FOLDER_PATH="$DEFAULT_PATH"
else
    FOLDER_PATH="$USER_PATH"
fi

# 檢查路徑是否存在
if [ ! -d "$FOLDER_PATH" ]; then
    print_error "路徑不存在: $FOLDER_PATH"
    exit 1
fi

print_success "使用路徑: $FOLDER_PATH"

# 獲取 API Key
echo ""
echo "請輸入您的 OpenAI API Key"
echo "（如果已設置環境變量 OPENAI_API_KEY，可直接回車）"
read -s -p "API Key: " USER_API_KEY
echo ""

if [ -z "$USER_API_KEY" ]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        print_error "未提供 API Key"
        exit 1
    else
        API_KEY="$OPENAI_API_KEY"
        print_info "使用環境變量中的 API Key"
    fi
else
    API_KEY="$USER_API_KEY"
fi

# 選擇處理模式
echo ""
echo "請選擇處理模式："
echo "1. 分析所有幻燈片（完整分析）"
echo "2. 只分析精選幻燈片（selected_slides）"
echo "3. 強制重新分析所有（覆蓋現有分析）"
read -p "選擇 (1-3) [默認: 1]: " MODE

case $MODE in
    2)
        MODE_ARGS="--selected-only"
        MODE_DESC="只分析精選幻燈片"
        ;;
    3)
        MODE_ARGS="--force"
        MODE_DESC="強制重新分析"
        ;;
    *)
        MODE_ARGS=""
        MODE_DESC="分析所有幻燈片"
        ;;
esac

# 選擇模型
echo ""
echo "請選擇 AI 模型："
echo "1. GPT-4o-mini (快速、經濟)"
echo "2. GPT-4o (高質量、較慢)"
read -p "選擇 (1-2) [默認: 1]: " MODEL

case $MODEL in
    2)
        MODEL_ARG="--model gpt-4o"
        MODEL_DESC="GPT-4o"
        ;;
    *)
        MODEL_ARG="--model gpt-4o-mini"
        MODEL_DESC="GPT-4o-mini"
        ;;
esac

# 顯示配置摘要
echo ""
echo "=============================================="
echo "配置摘要："
echo "路徑: $FOLDER_PATH"
echo "模式: $MODE_DESC"
echo "模型: $MODEL_DESC"
echo "=============================================="
echo ""

# 確認執行
read -p "確認開始分析？(y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    print_warning "已取消"
    exit 0
fi

# 執行分析
echo ""
print_info "開始批量分析..."
echo ""

# 獲取腳本所在目錄
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 執行 Python 腳本
python "$SCRIPT_DIR/batch_slides_analysis.py" \
    "$FOLDER_PATH" \
    --api-key "$API_KEY" \
    $MODEL_ARG \
    $MODE_ARGS

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo ""
    print_success "批量分析完成！"
else
    echo ""
    print_error "分析過程中出現錯誤"
fi