#!/bin/bash

# 批量幻燈片捕獲腳本
# 自動設置環境並執行批量處理

set -e  # 遇到錯誤時停止執行

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
echo "     批量視頻幻燈片捕獲工具安裝與運行"
echo "=============================================="
echo ""

# 檢查 Python 是否安裝
print_info "檢查 Python 安裝..."
if ! command -v python3 &> /dev/null; then
    print_error "未找到 Python 3，請先安裝 Python 3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
print_success "找到 $PYTHON_VERSION"

# 獲取腳本所在目錄
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
print_info "工作目錄: $SCRIPT_DIR"

# 檢查是否已有虛擬環境
if [ -d "venv" ]; then
    print_info "發現已存在的虛擬環境"
    read -p "是否要使用現有的虛擬環境？(y/n) [默認: y]: " use_existing
    use_existing=${use_existing:-y}
    
    if [ "$use_existing" != "y" ]; then
        print_info "刪除舊的虛擬環境..."
        rm -rf venv
        CREATE_VENV=true
    else
        CREATE_VENV=false
    fi
else
    CREATE_VENV=true
fi

# 創建虛擬環境
if [ "$CREATE_VENV" = true ]; then
    print_info "創建虛擬環境..."
    python3 -m venv venv
    print_success "虛擬環境創建完成"
fi

# 激活虛擬環境
print_info "激活虛擬環境..."
source venv/bin/activate

# 更新 pip
print_info "更新 pip..."
pip install --upgrade pip

# 檢查並安裝依賴
print_info "檢查並安裝必要的依賴..."

# 創建臨時 requirements 文件
cat > temp_requirements.txt << EOF
opencv-python>=4.5.0
numpy>=1.19.0
pillow>=8.0.0
moviepy>=1.0.0
python-pptx>=0.6.0
scikit-image>=0.18.0
EOF

# 安裝依賴
pip install -r temp_requirements.txt

# 刪除臨時文件
rm temp_requirements.txt

print_success "所有依賴安裝完成"

# 主程序循環
while true; do
    echo ""
    echo "=============================================="
    echo "           批量幻燈片捕獲工具"
    echo "=============================================="
    echo ""
    
    # 獲取用戶輸入
    echo "請選擇操作模式："
    echo "1. 處理單個視頻文件"
    echo "2. 處理整個文件夾（非遞歸）"
    echo "3. 遞歸處理文件夾及子文件夾"
    echo "4. 退出"
    echo ""
    read -p "請輸入選項 (1-4): " mode
    
    case $mode in
        1)
            # 單個文件模式
            read -p "請輸入視頻文件的完整路徑: " video_path
            if [ ! -f "$video_path" ]; then
                print_error "文件不存在: $video_path"
                continue
            fi
            ;;
        2)
            # 文件夾模式（非遞歸）
            read -p "請輸入文件夾路徑: " folder_path
            if [ ! -d "$folder_path" ]; then
                print_error "文件夾不存在: $folder_path"
                continue
            fi
            video_path="$folder_path"
            ;;
        3)
            # 遞歸模式
            read -p "請輸入文件夾路徑: " folder_path
            if [ ! -d "$folder_path" ]; then
                print_error "文件夾不存在: $folder_path"
                continue
            fi
            video_path="$folder_path"
            RECURSIVE="-r"
            ;;
        4)
            print_info "退出程序"
            deactivate
            exit 0
            ;;
        *)
            print_error "無效的選項"
            continue
            ;;
    esac
    
    # 詢問處理選項
    echo ""
    echo "處理選項："
    read -p "是否自動選擇每組最佳幻燈片？(y/n) [默認: y]: " auto_select
    auto_select=${auto_select:-y}
    
    read -p "是否強制重新處理已有幻燈片的視頻？(y/n) [默認: n]: " force
    force=${force:-n}
    
    read -p "相似度閾值 (0.5-0.95) [默認: 0.80]: " threshold
    threshold=${threshold:-0.80}
    
    # 構建命令
    CMD="python batch_slide_capture.py \"$video_path\""
    
    if [ "$RECURSIVE" = "-r" ]; then
        CMD="$CMD -r"
    fi
    
    if [ "$auto_select" = "y" ]; then
        CMD="$CMD -a"
    fi
    
    if [ "$force" = "y" ]; then
        CMD="$CMD -f"
    fi
    
    CMD="$CMD -t $threshold"
    
    # 先列出將要處理的文件
    echo ""
    print_info "檢查將要處理的視頻..."
    eval "$CMD -l"
    
    echo ""
    read -p "是否開始處理？(y/n): " confirm
    
    if [ "$confirm" = "y" ]; then
        echo ""
        print_info "開始處理..."
        eval "$CMD"
    else
        print_warning "已取消處理"
    fi
    
    # 詢問是否繼續
    echo ""
    read -p "是否繼續處理其他視頻？(y/n) [默認: n]: " continue_process
    continue_process=${continue_process:-n}
    
    if [ "$continue_process" != "y" ]; then
        break
    fi
    
    # 重置變量
    RECURSIVE=""
done

print_success "程序結束"
deactivate