#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
程序化雨层生成器
视频模型画不出可读的雨（实测多镜都是"看不见雨"），所以在后期合成一层真雨。

做法：
  - 远近两层雨丝：远层细、密、亮；近层粗、疏、虚（模拟贴镜头的雨）
  - 每帧根据速度向下移动，出画后回到上方 → 真实的下落连续性
  - 输出黑底白丝的无损视频，剪辑时用 blend=screen 叠到画面上
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "work", "fx")
os.makedirs(TMP, exist_ok=True)
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

W, H, FPS, SEC = 1280, 704, 24, 2.0
N = int(FPS * SEC)
rng = np.random.default_rng(3)


def make_streaks(n, ang_rng, len_rng, spd_rng, bright_rng, width=1):
    out = []
    for _ in range(n):
        out.append(dict(
            x=rng.uniform(-100, W + 100),
            y=rng.uniform(-H, H),
            ang=np.deg2rad(rng.uniform(*ang_rng)),
            ln=rng.uniform(*len_rng),
            spd=rng.uniform(*spd_rng),
            br=int(rng.uniform(*bright_rng)),
            w=width,
        ))
    return out


FAR = make_streaks(420, (12, 19), (50, 130), (26, 40), (70, 190), 1)
NEAR = make_streaks(55, (11, 20), (150, 300), (55, 85), (45, 110), 4)


def draw_layer(streaks, blur=0):
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for s in streaks:
        dx, dy = np.sin(s["ang"]) * s["ln"], np.cos(s["ang"]) * s["ln"]
        d.line([(s["x"], s["y"]), (s["x"] + dx, s["y"] + dy)], fill=s["br"], width=s["w"])
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(img, dtype=np.uint16)


frames = []
for f in range(N):
    far = draw_layer(FAR, blur=0)
    near = draw_layer(NEAR, blur=2.2)
    a = np.clip(far * 0.55 + near * 0.85, 0, 255).astype(np.uint8)
    frames.append(a)
    for s in FAR:
        s["y"] += s["spd"]
        if s["y"] > H + 40:
            s["y"] = rng.uniform(-180, -20); s["x"] = rng.uniform(-100, W + 100)
    for s in NEAR:
        s["y"] += s["spd"]
        if s["y"] > H + 60:
            s["y"] = rng.uniform(-260, -30); s["x"] = rng.uniform(-100, W + 100)

# 写成 PNG 序列再编码（避免管道编码的色彩问题）
seq = os.path.join(TMP, "rain")
os.makedirs(seq, exist_ok=True)
for i, a in enumerate(frames):
    Image.fromarray(a, mode="L").save(os.path.join(seq, f"r{i:04d}.png"))

out = os.path.join(TMP, "rain_loop.mp4")
cmd = [FF, "-y", "-framerate", str(FPS), "-i", os.path.join(seq, "r%04d.png"),
       "-vf", "format=gray", "-c:v", "libx264", "-crf", "0", "-preset", "ultrafast",
       "-pix_fmt", "gray", out]
r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
if r.returncode != 0:
    print(r.stderr[-1500:]); raise SystemExit(1)
print(f"✓ {out}  {os.path.getsize(out)/1024:.0f} KB  {N}帧 @{FPS}fps")

# 抽一帧看效果
prev = os.path.join(TMP, "rain_preview.png")
Image.fromarray(frames[12], mode="L").save(prev)
print("预览:", prev)
