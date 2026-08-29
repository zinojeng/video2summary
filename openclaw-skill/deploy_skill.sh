#!/bin/bash
# ============================================
# deploy_skill.sh
# 一鍵部署 audio-transcribe skill 到 Mac Mini OpenClaw
#
# 從 MacBook 執行：
#   ./deploy_skill.sh
#
# 或指定 Mac Mini IP：
#   ./deploy_skill.sh 100.114.129.67
# ============================================

MAC_MINI="${1:-100.114.129.67}"
USER="ander"
REMOTE_SKILL_DIR="~/.openclaw/workspace/skills/audio-transcribe"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "====================================="
echo "🦞 OpenClaw Skill 部署工具"
echo "  目標: ${USER}@${MAC_MINI}"
echo "  Skill: audio-transcribe"
echo "====================================="

# 1. 確認連線
echo ""
echo "[1/5] 測試 SSH 連線..."
ssh -o ConnectTimeout=5 "${USER}@${MAC_MINI}" "echo '✅ SSH 連線成功'" || {
    echo "❌ 無法連線到 ${USER}@${MAC_MINI}"
    echo "請確認："
    echo "  - Mac Mini 已開機"
    echo "  - Tailscale 已連線"
    echo "  - SSH 已啟用"
    exit 1
}

# 2. 建立目錄
echo ""
echo "[2/5] 建立遠端目錄..."
ssh "${USER}@${MAC_MINI}" "mkdir -p ${REMOTE_SKILL_DIR}/scripts"

# 3. 部署 SKILL.md
echo ""
echo "[3/5] 部署 SKILL.md..."
scp "${SCRIPT_DIR}/SKILL.md" "${USER}@${MAC_MINI}:${REMOTE_SKILL_DIR}/SKILL.md"

# 4. 部署 scripts
echo ""
echo "[4/5] 部署 scripts..."
scp "${SCRIPT_DIR}/scripts/summarize_transcript.py" \
    "${USER}@${MAC_MINI}:${REMOTE_SKILL_DIR}/scripts/summarize_transcript.py"
scp "${SCRIPT_DIR}/scripts/inbox_watcher.sh" \
    "${USER}@${MAC_MINI}:${REMOTE_SKILL_DIR}/scripts/inbox_watcher.sh"

# 設定執行權限
ssh "${USER}@${MAC_MINI}" "chmod +x ${REMOTE_SKILL_DIR}/scripts/inbox_watcher.sh"

# 5. 安裝 Python 依賴（在 venv 中）
echo ""
echo "[5/5] 安裝 Python 依賴..."
ssh "${USER}@${MAC_MINI}" "
    cd ${REMOTE_SKILL_DIR}/scripts
    if [ -d venv ]; then
        source venv/bin/activate
        pip install -q openai \
            'llm-provider-kit @ https://github.com/zinojeng/llm-provider-kit/archive/refs/heads/main.tar.gz' \
            2>&1 | tail -3
        echo '✅ Python 依賴已安裝'
    else
        echo '⚠️ 找不到 venv，請先建立：'
        echo '  cd ${REMOTE_SKILL_DIR}/scripts'
        echo '  python3 -m venv venv'
        echo '  source venv/bin/activate'
        echo '  pip install openai llm-provider-kit@https://github.com/zinojeng/llm-provider-kit/archive/refs/heads/main.tar.gz'
    fi
"

# 驗證
echo ""
echo "====================================="
echo "✅ 部署完成！"
echo ""
echo "驗證指令（在 Mac Mini 上執行）："
echo "  ls -la ${REMOTE_SKILL_DIR}/"
echo "  ls -la ${REMOTE_SKILL_DIR}/scripts/"
echo ""
echo "啟動 inbox watcher："
echo "  ${REMOTE_SKILL_DIR}/scripts/inbox_watcher.sh --status"
echo "  ${REMOTE_SKILL_DIR}/scripts/inbox_watcher.sh --daemon"
echo ""
echo "或透過 OpenClaw 下指令："
echo '  「啟動 audio inbox 監控」'
echo '  「幫我轉錄 ~/inbox/recording.m4a」'
echo "====================================="
