#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播视频生成器 - FFmpeg + Edge-TTS + Pillow 背景
"""

import argparse
import asyncio
import platform
import subprocess
import sys
from pathlib import Path

def find_chinese_font():
    candidates = []
    system = platform.system()
    if system == "Windows":
        candidates = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyh.ttf",
                     r"C:\Windows\Fonts\simhei.ttf"]
    elif system == "Darwin":
        candidates = ["/System/Library/Fonts/PingFang.ttc",
                     "/System/Library/Fonts/STHeiti Medium.ttc"]
    else:
        candidates = ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]
    for c in candidates:
        if Path(c).exists():
            return c
    return None

CHINESE_FONT = find_chinese_font()
if CHINESE_FONT:
    FONT_ESCAPED = CHINESE_FONT.replace("\\", "/").replace(":", "\\:")
else:
    FONT_ESCAPED = None

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

AVATAR = ASSETS / "avatar.jpg"
DID_AVATAR = OUTPUT / "did_talking_head.mp4"
AUDIO = OUTPUT / "narration.mp3"
FINAL = OUTPUT / "final_output.mp4"

BG_KEYS = {
    "cover": OUTPUT / "bg_cover.png",
    "pits": OUTPUT / "bg_pits.png",
    "flow": OUTPUT / "bg_flow.png",
}

# end=None 表示自动取音频总时长
SEGMENTS_TMPL = [
    (0,  5,   "cover", "AI 说接口全接好了? 一上线还是假数据"),
    (5,  18,  "pits",  "三个坑: mock残留 / 下拉写死 / 菜单写死"),
    (18, 40,  "flow",  "两轮验收: 扫描源码 + 抓真实请求 + 检查权限"),
    (40, 58,  "cover", "两轮都过才算接完 - AI 快, 验收不能省"),
    (58, None, "cover", "关注我, 每天讲一个 AI 开发落地的工程细节"),
]

SCRIPT = """大家好,

用 AI 写前端的朋友, 你有没有遇到过:
AI 说接口全接好了, 一上线才发现, 还是假数据?

我们实测踩过三个坑:
第一, mock 没清干净, 页面看着正常, 其实请求根本没发到后端;
第二, 下拉框选项是写死的, 没走字典接口;
第三, 菜单直接写在代码里, 没按后端权限来展示.

所以立规 APT 给前端接线加了两轮验收,
不看 AI 怎么说, 只看证据.

第一轮先出效果:
扫描源码里的 mock 痕迹, 再真的打开页面、点开下拉框,
抓它发出的请求, 检查是不是打到了正确的后端接口.

你确认效果没问题、明确放行之后, 才进入第二轮:
检查需要权限的页面, 菜单是不是来自后端权限接口;
代码里另写一套菜单, 直接打回.

两轮都过, 才算真正接完.
AI 写代码可以快, 但验收必须独立.

关注我, 每天讲一个让 AI 开发真正落地的工程细节."""


def ensure_backgrounds():
    need_gen = any(not p.exists() for p in BG_KEYS.values())
    if need_gen:
        print("[背景] 生成 PNG...")
        from gen_bg import main as gen_bg_main
        gen_bg_main()

ensure_backgrounds()


def probe_duration(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def ffmpeg_escape(text):
    return (text.replace("\\", "\\\\")
                .replace(":", "\\:")
                .replace("'", "'\\''")
                .replace("%", "%%")
                .replace("/", "\\/"))


async def ensure_audio():
    if AUDIO.exists() and AUDIO.stat().st_size > 10000:
        print(f"[音频] 已存在: {AUDIO}")
        return AUDIO
    import edge_tts
    print("[音频] Edge-TTS 生成中...")
    comm = edge_tts.Communicate(SCRIPT, "zh-CN-YunjianNeural", rate="+0%")
    await comm.save(str(AUDIO))
    print(f"  OK: {AUDIO}")
    return AUDIO


def build_segment_video(seg_idx, seg, avatar_media):
    start, end, bg_key, subtitle = seg
    dur = end - start
    seg_file = OUTPUT / f"seg_{seg_idx:02d}.mp4"
    safe_sub = ffmpeg_escape(subtitle)

    bg_src = BG_KEYS.get(bg_key)
    if bg_src and bg_src.exists():
        bg_input = ["-loop", "1", "-i", str(bg_src)]
    else:
        bg_input = ["-f", "lavfi", "-i", f"color=c=0f172a:s=1080x1920:d={dur}"]

    font_arg = f"fontfile='{FONT_ESCAPED}':" if FONT_ESCAPED else ""

    is_did_video = (avatar_media is not None and avatar_media.exists()
                    and avatar_media.suffix.lower() == ".mp4")
    is_static_img = (avatar_media is not None and avatar_media.exists()
                     and avatar_media.suffix.lower() in (".jpg", ".jpeg", ".png"))

    if not avatar_media or not avatar_media.exists():
        print(f"  片段 {seg_idx}: 无头像")
        cmd = ["ffmpeg", "-y"] + bg_input + [
            "-t", str(dur),
            "-vf", f"drawtext={font_arg}"
                   f"text='{safe_sub}':"
                   f"x=(W-tw)/2:y=H-160:fontsize=44:fontcolor=white:"
                   f"box=1:boxcolor=black@0.6:boxborderw=16",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(seg_file)
        ]
    elif is_did_video:
        print(f"  片段 {seg_idx}: 数字人视频 + 背景")
        cmd = ["ffmpeg", "-y"] + bg_input + [
            "-i", str(avatar_media),
            "-t", str(dur),
            "-filter_complex",
            f"[1:v]scale=520:-1,crop=520:780:0:200[avatar];"
            f"[0:v][avatar]overlay=(W-w)/2:H-h-180:format=auto[base];"
            f"[base]drawtext={font_arg}"
            f"text='{safe_sub}':"
            f"x=(W-tw)/2:y=H-100:fontsize=44:fontcolor=white:"
            f"box=1:boxcolor=black@0.6:boxborderw=16[out]",
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(seg_file)
        ]
    else:
        print(f"  片段 {seg_idx}: 静态头像 + 背景")
        cmd = ["ffmpeg", "-y"] + bg_input + [
            "-loop", "1", "-i", str(avatar_media),
            "-t", str(dur),
            "-filter_complex",
            f"[1:v]scale=420:-1,crop=420:630:0:110[avatar];"
            f"[0:v][avatar]overlay=(W-w)/2:H-h-200:format=auto[base];"
            f"[base]drawtext={font_arg}"
            f"text='{safe_sub}':"
            f"x=(W-tw)/2:y=H-100:fontsize=44:fontcolor=white:"
            f"box=1:boxcolor=black@0.6:boxborderw=16[out]",
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(seg_file)
        ]

    result = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"  片段 {seg_idx} 失败: {(result.stderr or '')[-200:]}")
        return None
    return seg_file


def concat_and_mix(segment_files, audio_path):
    list_file = OUTPUT / "concat_list.txt"
    with open(list_file, "w") as f:
        for sf in segment_files:
            if sf:
                f.write(f"file '{sf.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-i", str(audio_path),
        "-c", "copy",
        "-map", "0:v", "-map", "1:a",
        "-shortest",
        str(FINAL)
    ]

    print("[合成] 拼接 + 音频...")
    result = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"  失败: {(result.stderr or '')[-300:]}")
        return None
    print(f"[合成] OK: {FINAL}")
    return FINAL


async def main():
    parser = argparse.ArgumentParser(description="口播视频生成器")
    parser.add_argument("--did-key", type=str, default=None,
                        help="D-ID API key")
    parser.add_argument("--aliyun-key", type=str, default=None,
                        help="阿里云百炼 API key (sk-xxx)")
    parser.add_argument("--workspace-id", type=str, default=None,
                        help="阿里云百炼 workspace ID (推荐提供)")
    parser.add_argument("--resolution", type=str, default="480P",
                        help="阿里云输出分辨率 480P/720P")
    parser.add_argument("--skip-did", action="store_true",
                        help="跳过云端数字人, 用静态头像")
    parser.add_argument("--no-avatar", action="store_true",
                        help="纯内容模式: 不用头像, 只有背景+字幕")
    args = parser.parse_args()

    print("=" * 60)
    print("口播视频生成器")
    print("=" * 60)

    audio = await ensure_audio()
    if not audio:
        return

    total_dur = probe_duration(audio)
    segments = [
        (s, e if e is not None else total_dur, bg, sub)
        for (s, e, bg, sub) in SEGMENTS_TMPL
    ]

    avatar_media = None

    def _chunk_audio(audio_path: Path, max_chunk: int = 19) -> list[tuple[float, float, Path]]:
        """把长音频切成 < max_chunk 秒的段, 返回 [(start, end, path), ...]"""
        chunks = []
        out_dir = audio_path.parent / "audio_chunks"
        out_dir.mkdir(exist_ok=True)

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True)
        total = float(probe.stdout.strip())

        t = 0
        idx = 0
        while t < total:
            end = min(t + max_chunk, total)
            chunk_path = out_dir / f"chunk_{idx:02d}.mp3"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(audio_path),
                 "-ss", str(t), "-t", str(end - t),
                 "-c", "copy", str(chunk_path)],
                capture_output=True)
            chunks.append((t, end, chunk_path))
            t = end
            idx += 1
        return chunks

    if args.aliyun_key and not args.skip_did:
        if DID_AVATAR.exists() and DID_AVATAR.stat().st_size > 100000:
            print(f"\n[阿里云] 已存在数字人视频: {DID_AVATAR}")
            avatar_media = DID_AVATAR
        elif AVATAR.exists():
            print(f"\n[阿里云] wan2.2-s2v 生成数字人视频 ...")
            from aliyun_client import generate_talking_head
            chunks = _chunk_audio(audio, 19)
            print(f"  音频切段: {len(chunks)} 段 (阿里云限 20s)")
            did_parts = []
            for ci, (start, end, chunk_path) in enumerate(chunks):
                seg_out = OUTPUT / f"aliyun_part_{ci:02d}.mp4"
                print(f"\n  段 {ci+1}/{len(chunks)}: {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")
                try:
                    generate_talking_head(
                        api_key=args.aliyun_key,
                        workspace_id=args.workspace_id,
                        avatar_path=AVATAR,
                        audio_path=chunk_path,
                        out_path=seg_out,
                        resolution=args.resolution,
                    )
                    did_parts.append(seg_out)
                except Exception as e:
                    print(f"    [阿里云] 段 {ci} 失败: {e}")

            if did_parts:
                concat_list = OUTPUT / "aliyun_concat.txt"
                with open(concat_list, "w") as f:
                    for p in did_parts:
                        f.write(f"file '{p.resolve()}'\n")
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                     "-i", str(concat_list), "-c", "copy",
                     str(DID_AVATAR)],
                    capture_output=True)
                if DID_AVATAR.exists() and DID_AVATAR.stat().st_size > 100000:
                    avatar_media = DID_AVATAR
                    print(f"\n[阿里云] 拼接完成: {DID_AVATAR} ({DID_AVATAR.stat().st_size // 1024}KB)")
                else:
                    print("  拼接失败, 降级静态头像")
                    avatar_media = AVATAR
            else:
                print("  阿里云全部失败, 降级静态头像")
                avatar_media = AVATAR

    elif args.did_key and not args.skip_did:
        if DID_AVATAR.exists() and DID_AVATAR.stat().st_size > 100000:
            print(f"\n[D-ID] 已存在数字人视频: {DID_AVATAR}")
            avatar_media = DID_AVATAR
        elif AVATAR.exists():
            print(f"\n[D-ID] 调用 API 生成数字人视频 ...")
            print(f"  头像: {AVATAR}")
            print(f"  音频: {audio}")
            try:
                from did_client import generate_talking_head
                avatar_media = generate_talking_head(
                    api_key=args.did_key,
                    avatar_path=AVATAR,
                    audio_path=audio,
                    out_path=DID_AVATAR,
                )
            except Exception as e:
                print(f"  [D-ID] 失败: {e}")
                print(f"  降级为静态头像")
                avatar_media = AVATAR
        else:
            print("[D-ID] 无头像图, 跳过")
    if not args.no_avatar and not avatar_media and DID_AVATAR.exists() and DID_AVATAR.stat().st_size > 100000:
        print(f"[数字人] 检测到已有视频: {DID_AVATAR}")
        avatar_media = DID_AVATAR
    if not args.no_avatar and not avatar_media and AVATAR.exists():
        print(f"[头像] 静态模式: {AVATAR}")
        avatar_media = AVATAR
    elif not avatar_media:
        print("[头像] 未找到, 无头像模式")

    segment_files = []
    print(f"\n[片段] 共 {len(segments)} 段, 音频 {total_dur:.1f}s ...")
    for i, seg in enumerate(segments):
        print(f"  [{i+1}/{len(segments)}] {seg[1]-seg[0]}s key={seg[2]}")
        sf = build_segment_video(i, seg, avatar_media)
        segment_files.append(sf)

    segments_ok = [s for s in segment_files if s]
    if len(segments_ok) != len(segment_files):
        print(f"\n警告: {len(segments_ok)}/{len(segment_files)} 段成功")

    if segments_ok:
        final = concat_and_mix(segments_ok, audio)
        if final:
            print(f"\n{'='*60}")
            print(f"完成! {final}")
            print(f"{'='*60}")
    else:
        print("\n所有片段失败")


if __name__ == "__main__":
    asyncio.run(main())
