#!/bin/bash
# ============================================================
# 一次性环境安装: Homebrew + ffmpeg + Python 依赖
# 用法:  chmod +x setup.sh && ./setup.sh
# ============================================================
set -e
cd "$(dirname "$0")"

if [[ $(uname -m) != "arm64" ]]; then
    echo "警告: 非 Apple Silicon Mac, 脚本未在 Intel 上验证过, 继续执行..."
fi

# ---------- 1. Homebrew ----------
if ! command -v brew &>/dev/null; then
    echo "[1/3] 安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "[1/3] Homebrew 已安装"
fi

# ---------- 2. ffmpeg ----------
if ! command -v ffmpeg &>/dev/null; then
    echo "[2/3] 安装 ffmpeg..."
    brew install ffmpeg
else
    echo "[2/3] ffmpeg: $(ffmpeg -version | head -1)"
fi

# ---------- 3. Python 依赖 ----------
echo "[3/3] 安装 Python 依赖 (edge-tts / pillow)..."
python3 -m pip install --quiet edge-tts pillow

python3 - <<'EOF'
import edge_tts, PIL
print("依赖检查 OK: edge-tts / pillow")
EOF

echo ""
echo "============================================"
echo " 环境就绪! 生成视频:"
echo "   ./run.sh"
echo "============================================"
