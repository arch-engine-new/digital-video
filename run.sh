#!/bin/bash
# ============================================================
# 纯内容口播视频: 语音 + 背景卡片 + 字幕
# 全本地生成, 无需任何云端 API / 头像
# ============================================================
set -e
cd "$(dirname "$0")"

if ! command -v ffmpeg &>/dev/null; then
    echo "ffmpeg 未安装, 请先运行: ./setup.sh"
    exit 1
fi

mkdir -p output
python3 quick_video.py --no-avatar

FINAL="output/final_output.mp4"
if [ -f "$FINAL" ]; then
    echo ""
    echo "============================================"
    echo " 完成! 成片: $FINAL"
    echo "============================================"
else
    echo ""
    echo "final_output.mp4 未生成, 请查看上方日志"
    exit 1
fi
