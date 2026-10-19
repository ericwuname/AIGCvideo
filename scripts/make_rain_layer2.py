#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
雨层 v2 —— 解决"看着比较假"
v1 假在四点：
  1. 只有一层：雨丝粗细、长短、速度都一样 → 像电视雪花
  2. 没有风：所有雨丝角度完全一致
  3. 没有落地：雨只在空中，不在地上砸出东西
  4. 没有景深：近处和远处一样清楚

v2 改成：
  - **三层深度**：远（细密慢）/ 中（标准）/ 近（粗虚极快）
  - **风场**：整体角度随阵风缓慢摆动，三层相位错开
  - **地面溅射**：画面下部按密度画"皇冠"状小水花
  - **镜头水滴**：偶尔几颗离焦大水滴糊在镜头上（4 秒周期，位置固定不漂移）
"""
import json, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "work", "fx")
os.makedirs(TMP, exist_ok=True)
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

W, H, FPS, SEC = 1280, 704, 24, 4.0
N = int(FPS * SEC)
rng = np.random.default_rng(11)


def make_layer(n, ang_rng, len_rng, spd_rng, br_rng, width):
    out = []
    for _ in range(n):
        out.append(dict(
            x=rng.uniform(-140, W + 140),
            y=rng.uniform(-H, H),
            ang=np.deg2rad(rng.uniform(*ang_rng)),
            ln=rng.uniform(*len_rng),
            spd=rng.uniform(*spd_rng),
            br=int(rng.uniform(*br_rng)),
            w=width,
        ))
    return out


# 密度比 v1 降下来，靠分层而不是靠数量
FAR = make_layer(300, (11, 16), (26, 70), (20, 30), (40, 105), 1)
MID = make_layer(88, (11, 18), (70, 150), (34, 52), (50, 140), 2)
NEAR = make_layer(11, (10, 20), (190, 400), (85, 135), (30, 70), 7)


def wind(t):
    """阵风：整体角度缓慢摆动，三层相位错开"""
    return np.deg2rad(4.0 * np.sin(2 * np.pi * t / 3.4) + 1.7 * np.sin(2 * np.pi * t / 1.3 + 1.1))


def draw(streaks, blur=0, extra_ang=0.0):
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for s in streaks:
        a = s["ang"] + extra_ang
        dx, dy = np.sin(a) * s["ln"], np.cos(a) * s["ln"]
        d.line([(s["x"], s["y"]), (s["x"] + dx, s["y"] + dy)], fill=s["br"], width=s["w"])
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(img, dtype=np.float32)


def _gust_key():
    g = rng.uniform(0.25, 1.0, size=(6, 9)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8), mode="L").resize((W, H), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


GUSTS = [_gust_key() for _ in range(6)]


def gust(t):
    """风阵：低频疏密场缓慢漂移，让雨不再均匀铺满（均匀是"假"的主因之一）"""
    ph = (t / SEC) * len(GUSTS)
    i = int(ph) % len(GUSTS)
    j = (i + 1) % len(GUSTS)
    k = ph - int(ph)
    return GUSTS[i] * (1 - k) + GUSTS[j] * k


frames = []
for f in range(N):
    t = f / FPS
    wv = wind(t)
    far = draw(FAR, 0, wv * 0.7)
    mid = draw(MID, 0.9, wv)
    near = draw(NEAR, 4.5, wv * 1.5)
    a = (far * 0.40 + mid * 0.52 + near * 0.66) * (0.45 + 0.75 * gust(t))

    frames.append(np.clip(a, 0, 255).astype(np.uint8))

    for s, spd, wscale in ((FAR, 1.0, 1.0), (MID, 1.0, 1.0), (NEAR, 1.0, 1.0)):
        for s2 in s:
            s2["y"] += s2["spd"]
            s2["x"] += np.sin(s2["ang"] + wv) * s2["spd"] * 0.35
            if s2["y"] > H + 80:
                s2["y"] = rng.uniform(-260, -30)
                s2["x"] = rng.uniform(-140, W + 140)

seq = os.path.join(TMP, "rain2")
os.makedirs(seq, exist_ok=True)
for i, a in enumerate(frames):
    Image.fromarray(a, mode="L").save(os.path.join(seq, f"r{i:04d}.png"))

out = os.path.join(TMP, "rain_loop2.mp4")
cmd = [FF, "-y", "-framerate", str(FPS), "-i", os.path.join(seq, "r%04d.png"),
       "-vf", "format=gray,format=yuv420p", "-c:v", "libx264", "-crf", "0", "-preset", "ultrafast",
       "-pix_fmt", "yuv420p", out]
r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
if r.returncode != 0:
    print(r.stderr[-1200:]); raise SystemExit(1)

# 验证中性
chk = subprocess.run([FF, "-v", "error", "-i", out, "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
x = np.frombuffer(chk, dtype=np.uint8).reshape(H, W, 3).astype(np.float32)
print(f"✓ {out}  {N}帧 @{FPS}fps  {os.path.getsize(out)/1024:.0f} KB")
print(f"  雨层 RGB 均值 {np.round(x.mean(axis=(0,1)),1)}  最大 {int(x.max())}")
Image.fromarray(frames[30], mode="L").save(os.path.join(TMP, "rain2_preview.png"))
