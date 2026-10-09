#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竖屏 (1080x1920, 9:16) 背景 PNG 生成 (Mac/Win 双平台)"""

import platform
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920

def load_font(size, bold=False):
    if platform.system() == "Darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\simhei.ttf",
        ]
        if bold:
            candidates = [
                r"C:\Windows\Fonts\msyhbd.ttc",
                r"C:\Windows\Fonts\msyhbd.ttf",
            ] + candidates
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()

def gradient_bg(w, h, top="#0f172a", bottom="#1e1b4b"):
    img = Image.new("RGB", (w, h))
    top_c = tuple(int(top.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    bot_c = tuple(int(bottom.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    for y in range(h):
        r = int(top_c[0] + (bot_c[0] - top_c[0]) * y / h)
        g = int(top_c[1] + (bot_c[1] - top_c[1]) * y / h)
        b = int(top_c[2] + (bot_c[2] - top_c[2]) * y / h)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img

def draw_grid(draw, w, h, spacing=40, color="#1e293b"):
    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(0, h, spacing):
        draw.line([(0, y), (w, y)], fill=color, width=1)

def rounded(draw, xy, r, fill, outline=None, width=3):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def tc(draw, text, y, font, fill, cx=None):
    if cx is None:
        cx = W // 2
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text((cx - tw // 2, y), text, font=font, fill=fill)

def tl(draw, text, x, y, font, fill):
    draw.text((x, y), text, font=font, fill=fill)


def make_cover():
    img = gradient_bg(W, H)
    draw = ImageDraw.Draw(img)
    draw_grid(draw, W, H)

    fb = load_font(40, bold=True)
    fbig = load_font(120, bold=True)
    fmid = load_font(80, bold=True)
    fsub = load_font(44, bold=True)
    ftag = load_font(32, bold=True)

    # 第1期 tag
    rounded(draw, (W//2 - 120, 100, W//2 + 120, 170), 12, "#fb7185")
    tc(draw, "第 1 期", 115, fb, "white")

    # 主标题 竖屏分段
    tc(draw, "AI 说", 240, fbig, "white")
    tc(draw, '"接好了"', 390, fbig, "#fb7185")
    tc(draw, "你信吗?", 560, fbig, "white")

    # 副标题框
    bw, bh = 860, 100
    rounded(draw, ((W-bw)//2, 720, (W+bw)//2, 720+bh), 20,
            "#881337", outline="#fb7185", width=4)
    tc(draw, "其实一半还是假的", 748, fsub, "#fb7185")

    # 产品 tag
    rounded(draw, (W - 280, H - 160, W - 40, H - 90), 12, "#0ea5e9")
    tc(draw, "立规 APT", H - 140, ftag, "white", cx=W - 160)

    img.save(OUT / "bg_cover.png")
    print("OK: bg_cover.png 1080x1920")


def make_pits():
    img = gradient_bg(W, H, top="#0f172a", bottom="#4c1d95")
    draw = ImageDraw.Draw(img)
    draw_grid(draw, W, H)

    ft = load_font(68, bold=True)
    fct = load_font(38, bold=True)
    fcd = load_font(26)
    fnum = load_font(46, bold=True)

    tc(draw, "踩过的三个坑", 120, ft, "white")
    tc(draw, "AI 说接好了, 其实根本没通", 220, fcd, "#94a3b8")

    cards = [
        ("坑 1", "#ef4444", "Mock 残留",
         "页面看着正常\n请求根本没发到后端"),
        ("坑 2", "#f59e0b", "下拉写死",
         "选项硬编码在页面\n不走字典接口"),
        ("坑 3", "#8b5cf6", "菜单写死",
         "菜单直接写代码里\n不按后端权限展示"),
    ]

    card_w = 860
    card_h = 320
    gap = 30
    total_h = card_h * 3 + gap * 2
    start_y = 360 + (H - 360 - 80 - total_h) // 2
    card_x = (W - card_w) // 2

    for i, (label, color, title, desc) in enumerate(cards):
        cy = start_y + i * (card_h + gap)

        rounded(draw, (card_x, cy, card_x + card_w, cy + card_h),
                24, "#1e293b", outline=color, width=4)

        rounded(draw, (card_x + 24, cy + 24, card_x + 140, cy + 78),
                12, color)
        tl(draw, label, card_x + 42, cy + 30, fnum, "white")

        tl(draw, title, card_x + 24, cy + 100, fct, "white")

        lines = desc.split("\n")
        for li, ln in enumerate(lines):
            tl(draw, ln, card_x + 24, cy + 160 + li * 42, fcd, "#cbd5e1")

        draw.rectangle([card_x + 24, cy + card_h - 12,
                        card_x + card_w - 24, cy + card_h - 8], fill=color)

    img.save(OUT / "bg_pits.png")
    print("OK: bg_pits.png 1080x1920")


def make_flow():
    img = gradient_bg(W, H, top="#0f172a", bottom="#134e4a")
    draw = ImageDraw.Draw(img)
    draw_grid(draw, W, H)

    ft = load_font(64, bold=True)
    fr = load_font(42, bold=True)
    fs = load_font(28)
    fc = load_font(34, bold=True)

    tc(draw, "两轮验收, 只看证据", 100, ft, "white")

    # === 第一轮 ===
    r1_x = 80
    r1_y = 220
    r1_w = W - 160
    r1_h = 580

    rounded(draw, (r1_x, r1_y, r1_x + r1_w, r1_y + r1_h),
            28, "#1e293b", outline="#0ea5e9", width=5)

    rounded(draw, (r1_x + 20, r1_y + 20, r1_x + 220, r1_y + 70),
            14, "#0ea5e9")
    tc(draw, "第一轮", r1_y + 26, fr, "white", cx=r1_x + 120)
    tl(draw, "出效果", r1_x + 240, r1_y + 22, fr, "#0ea5e9")

    steps_r1 = [
        "① 扫描源码中的 mock 痕迹",
        "② 真的打开页面、点开下拉框",
        "③ 抓它发出的请求",
        "④ 检查是否打到正确后端接口",
    ]
    for i, s in enumerate(steps_r1):
        sy = r1_y + 110 + i * 92
        rounded(draw, (r1_x + 30, sy, r1_x + r1_w - 30, sy + 72),
                12, "#0f172a", outline="#334155", width=2)
        tl(draw, s, r1_x + 50, sy + 18, fs, "white")

    # 中间箭头
    arr_cy = r1_y + r1_h + 40
    draw.polygon([
        (W//2 - 40, arr_cy),
        (W//2 + 40, arr_cy),
        (W//2, arr_cy + 50),
    ], fill="#64748b")
    tc(draw, "放行", arr_cy + 60, fc, "#94a3b8")

    # === 第二轮 ===
    r2_x = 80
    r2_y = arr_cy + 140
    r2_w = W - 160
    r2_h = H - r2_y - 140

    rounded(draw, (r2_x, r2_y, r2_x + r2_w, r2_y + r2_h),
            28, "#1e293b", outline="#10b981", width=5)

    rounded(draw, (r2_x + 20, r2_y + 20, r2_x + 220, r2_y + 70),
            14, "#10b981")
    tc(draw, "第二轮", r2_y + 26, fr, "white", cx=r2_x + 120)
    tl(draw, "查权限", r2_x + 240, r2_y + 22, fr, "#10b981")

    steps_r2 = [
        "① 人工确认第一轮效果",
        "② 放行后才进入第二轮",
        "③ 检查需要权限的页面",
        "④ 菜单必须来自后端权限接口",
        "⑤ 代码里另写菜单 → 直接打回",
    ]
    for i, s in enumerate(steps_r2):
        sy = r2_y + 110 + i * 88
        color = "#86efac" if i == 4 else "white"
        bg = "#450a0a" if i == 4 else "#0f172a"
        ol = "#dc2626" if i == 4 else "#334155"
        rounded(draw, (r2_x + 30, sy, r2_x + r2_w - 30, sy + 68),
                12, bg, outline=ol, width=2)
        tl(draw, s, r2_x + 50, sy + 16, fs, color)

    img.save(OUT / "bg_flow.png")
    print("OK: bg_flow.png 1080x1920")


def main():
    print(f"竖屏背景 {W}x{H} ...")
    make_cover()
    make_pits()
    make_flow()
    print(f"\n输出目录: {OUT}")

if __name__ == "__main__":
    main()
