#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
雨层合成（Python 逐帧，绕开 ffmpeg 滤镜链的色彩坑）
问题：在 ffmpeg 里用 blend=screen 叠雨，无论 RGB 还是 YUV 空间都会把整片染成紫色
      （实测成片 RGB 均值 64/13/72）。改用 numpy 直接算 screen 混合，颜色可控。

用法: python add_rain.py <输入mp4> <输出mp4> [强度=0.42]
"""
import os, subprocess, sys
import numpy as np

FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIN = os.path.join(ROOT, "work", "fx", "rain_loop2.mp4")
W, H, FPS = 1280, 704, 24


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    op = float(sys.argv[3]) if len(sys.argv) > 3 else 0.42

    # 读取时间轴：室内镜头不叠雨（否则"屋里也下雨"是硬逻辑错误）
    tl_path = os.path.join(ROOT, "release", "_timeline.json")
    indoor = []
    if os.path.exists(tl_path):
        import json
        for s in json.load(open(tl_path, encoding="utf-8")):
            if s.get("indoor"):
                indoor.append((s["start"], s["end"]))
    print(f"室内时段（不叠雨）: {indoor}")

    dec = subprocess.Popen([FF, "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    # 雨层循环解码
    rain = subprocess.Popen([FF, "-v", "error", "-stream_loop", "-1", "-i", RAIN,
                             "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, "-y", "-v", "error",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-i", src, "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-shortest", "-movflags", "+faststart", dst],
                           stdin=subprocess.PIPE)

    fsz = W * H * 3
    rsz = W * H
    n = 0
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz:
            break
        rbuf = rain.stdout.read(rsz)
        if len(rbuf) < rsz:
            rain.stdout.close(); rain.wait()
            rain = subprocess.Popen([FF, "-v", "error", "-stream_loop", "-1", "-i", RAIN,
                                     "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
            rbuf = rain.stdout.read(rsz)
        a = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3).astype(np.uint16)
        r = np.frombuffer(rbuf, dtype=np.uint8).reshape(H, W).astype(np.uint16)

        # 室内镜头完全不叠雨（否则"屋里也下雨"是硬逻辑错误）
        t = n / FPS
        op_f = 0.0 if any(s <= t < e for s, e in indoor) else op
        if op_f <= 0.0:
            enc.stdin.write(a.astype(np.uint8).tobytes())
            n += 1
            continue

        # 按亮度调制：雨在暗处看得见，在亮处（人脸、灯笼）几乎看不见。
        # 这一条是让"雨不再糊在人脸上"的关键——之前是把雨平均铺满，所以出戏。
        luma = (a[:, :, 0] * 77 + a[:, :, 1] * 150 + a[:, :, 2] * 29) >> 8
        mask = (255 - luma).astype(np.float32) / 255.0
        mask = (mask ** 1.5)[:, :, None]        # 越暗越明显，亮部迅速衰减
        r_eff = (r[:, :, None].astype(np.float32) * op_f * mask).astype(np.uint16)

        # screen: 255 - (255-a)(255-r)/255
        out = 255 - ((255 - a) * (255 - r_eff)) // 255
        enc.stdin.write(out.astype(np.uint8).tobytes())
        n += 1

    enc.stdin.close()
    dec.stdout.close()
    enc.wait(); dec.wait()
    print(f"✓ {dst}  合成 {n} 帧  {os.path.getsize(dst)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
