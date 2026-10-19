#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
走蛟 teaser 拼片：统一调色 + 0.4s 溶解 + H.264/AAC
读 work/clips/teaser/tNN.mp4，输出 release/走蛟-teaser.mp4
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "teaser")
OUT = os.path.join(ROOT, "release")
os.makedirs(OUT, exist_ok=True)
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

ORDER = [1, 2, 3, 4, 5, 6, 7]
XF = 0.4  # 溶解时长

# 统一调色：压暗、降饱和、压冷（AST-STYLE-001 的 B 组区间）
GRADE = ("eq=contrast=1.07:brightness=-0.025:saturation=0.85,"
         "colorbalance=rs=-0.02:gs=0.01:bs=0.04,"
         "curves=all='0/0 0.25/0.21 0.75/0.80 1/1'")


def dur(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    h, mnt, s = m.group(1), m.group(2), m.group(3)
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def main():
    clips = []
    for i in ORDER:
        p = os.path.join(SRC, f"t{i:02d}.mp4")
        if not os.path.exists(p):
            print(f"缺少 {p}"); sys.exit(1)
        clips.append((i, p))

    durs = [dur(p) for _, p in clips]
    print("片段时长:", [f"{d:.2f}" for d in durs], f"合计 {sum(durs):.2f}s")
    print(f"溶解后预计 {sum(durs) - XF * (len(clips) - 1):.2f}s")

    inputs = []
    for _, p in clips:
        inputs += ["-i", p]

    fc = []
    for k in range(len(clips)):
        fc.append(f"[{k}:v]scale=1280:704,fps=24,setsar=1,{GRADE}[v{k}]")

    # xfade 串联
    cur = "v0"
    offset = durs[0] - XF
    for k in range(1, len(clips)):
        nxt = f"x{k}"
        fc.append(f"[{cur}][v{k}]xfade=transition=fade:duration={XF}:offset={offset:.3f}[{nxt}]")
        cur = nxt
        offset += durs[k] - XF

    # 音频：各片段音轨长度与 xfade 后的视频不等长，直接 concat 会音画错位。
    # 改用第 1 段的雨声环境音循环铺满全片（雨声近似噪声，接缝不明显），首尾淡入淡出。
    total = sum(durs) - XF * (len(clips) - 1)
    fc.append(f"[0:a]aloop=loop=-1:size=2000000000,atrim=0:{total:.3f},"
              f"afade=t=in:st=0:d=1.2,afade=t=out:st={total-1.6:.3f}:d=1.6,"
              f"volume=0.9[aout]")

    out = os.path.join(OUT, "走蛟-teaser.mp4")
    cmd = [FF, "-y", *inputs,
           "-filter_complex", ";".join(fc),
           "-map", f"[{cur}]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print("渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print("ffmpeg 失败:\n", r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out}  {os.path.getsize(out)/1024/1024:.1f} MB  {dur(out):.2f}s")


if __name__ == "__main__":
    main()
