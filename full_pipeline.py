#!/usr/bin/env python3
"""完整流程: 切段 → 每段阿里云 → 拼接 → 叠背景字幕 (Mac 版)"""
import os, sys, time, subprocess, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aliyun_client import generate_talking_head

KEY = os.environ.get("ALIYUN_API_KEY", "sk-ed15527a249e44918a80b3da22c4ded2")
ROOT = Path(__file__).parent
OUT = ROOT / "output"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(OUT / "pipeline.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def probe_dur(p):
    r = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(p)],
        capture_output=True, text=True)
    return float(r.stdout.strip()) if r.stdout.strip() else 0

# === Step 1: 切段 ===
audio = OUT / "narration.mp3"
chunks_dir = OUT / "audio_chunks"
chunks_dir.mkdir(exist_ok=True)

log(f"=== Step 1: 切段 {probe_dur(audio):.1f}s ===")
chunk_files = []
t = 0
idx = 0
max_chunk = 19
total_dur = probe_dur(audio)

# 清旧切段
for f in chunks_dir.glob("*.mp3"):
    f.unlink()

while t < total_dur:
    end = min(t + max_chunk, total_dur)
    chunk_path = chunks_dir / f"chunk_{idx:02d}.mp3"
    subprocess.run([
        "ffmpeg","-y","-i",str(audio),
        "-ss",str(t),"-t",str(end-t),"-c","copy",str(chunk_path)
    ], capture_output=True)
    dur = probe_dur(chunk_path)
    log(f"  段{idx}: {t:.1f}s - {end:.1f}s ({dur:.1f}s)")
    chunk_files.append((idx, chunk_path))
    t = end
    idx += 1

log(f"共 {len(chunk_files)} 段")

# === Step 2: 逐段阿里云 ===
log(f"=== Step 2: 阿里云 wan2.2-s2v 生成 ===")
parts = []
for ci, chunk_path in chunk_files:
    part_out = OUT / f"aliyun_part_{ci:02d}.mp4"
    if part_out.exists() and part_out.stat().st_size > 100000:
        log(f"[段{ci}] 已存在, 跳过")
        parts.append(part_out)
        continue

    t0 = time.time()
    log(f"[段{ci}] 开始生成 ({chunk_path.name}, {probe_dur(chunk_path):.1f}s) ...")
    try:
        generate_talking_head(KEY, None, ROOT / "assets" / "avatar.jpg",
                              chunk_path, part_out, "480P")
        elapsed = int(time.time() - t0)
        log(f"[段{ci}] OK 完成 ({elapsed}s, {part_out.stat().st_size//1024}KB)")
        parts.append(part_out)
    except Exception as e:
        elapsed = int(time.time() - t0)
        log(f"[段{ci}] FAIL 失败 ({elapsed}s): {e}")

# === Step 3: 拼接 ===
if len(parts) >= 2:
    log(f"=== Step 3: 拼接 {len(parts)} 段 ===")
    final_avatar = OUT / "did_talking_head.mp4"
    concat_list = OUT / "aliyun_concat.txt"
    with open(concat_list, "w") as f:
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0",
        "-i",str(concat_list),"-c","copy",str(final_avatar)
    ], capture_output=True)
    if final_avatar.exists() and final_avatar.stat().st_size > 100000:
        dur = probe_dur(final_avatar)
        log(f"OK 拼接完成: {dur:.1f}s, {final_avatar.stat().st_size//1024}KB")
    else:
        log("拼接失败!")
        sys.exit(1)
elif len(parts) == 1:
    final_avatar = OUT / "did_talking_head.mp4"
    shutil.copy(parts[0], final_avatar)
    log(f"只有一段, 直接复制: {final_avatar.stat().st_size//1024}KB")
else:
    log("没有成功的片段! (若为 Arrearage 欠费, 请先给阿里云百炼充值)")
    sys.exit(1)

# === Step 4: quick_video 叠背景字幕 ===
log(f"=== Step 4: 叠背景+字幕 ===")
import subprocess as sp
result = sp.run(
    [sys.executable, str(ROOT / "quick_video.py"), "--skip-did"],
    capture_output=True, text=True, cwd=str(ROOT))
log(f"quick_video 退出码: {result.returncode}")
if result.stdout:
    for line in result.stdout.splitlines()[-10:]:
        log(f"  {line}")

final = OUT / "final_output.mp4"
if final.exists():
    log(f"\nDONE 全部完成! final_output.mp4: {probe_dur(final):.1f}s, {final.stat().st_size//1024}KB")
else:
    log("final_output.mp4 未找到, 可能 quick_video 失败")
