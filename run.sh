#!/bin/bash
# ============================================================
# 一键生成数字人口播视频
# 流程: 切段 → 阿里云 wan2.2-s2v 逐段生成 → 拼接 → 叠背景字幕
# 前置: 已跑过 ./setup.sh;  阿里云账户需有余额
# ============================================================
set -e
cd "$(dirname "$0")"

# API key 可用环境变量覆盖, 不设置则用内置的
export ALIYUN_API_KEY="${ALIYUN_API_KEY:-sk-ed15527a249e44918a80b3da22c4ded2}"

if ! command -v ffmpeg &>/dev/null; then
    echo "ffmpeg 未安装, 请先运行: ./setup.sh"
    exit 1
fi

if [ ! -f "assets/avatar.jpg" ]; then
    echo "没找到头像: assets/avatar.jpg"
    exit 1
fi

mkdir -p output
python3 full_pipeline.py

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
