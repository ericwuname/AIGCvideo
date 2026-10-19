#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
走蛟 teaser 拼片 v2
v1 问题：结尾落在眼部微距 → 全片最像鳄鱼的一帧放在最后一秒，把片子定性成"鳄鱼片"。
v2 结构：眼部特写降为插入镜头（2.2s），结尾收在"整条龙"上（最能确立"这是中国龙"）。
另外各段做入点/出点裁切，节奏更紧。
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "teaser")
OUT = os.path.join(ROOT, "release")
os.makedirs(OUT, exist_ok=True)
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

# (镜号, 入点, 出点)   —— 顺序即最终剪辑顺序
PLAN = [
    (1, 0.0, 3.6),   # 雨夜水乡空镜（定场）
    (2, 0.2, 4.8),   # 水下：长躯滑过
    (3, 0.2, 4.4),   # 水面：腹甲与爪，威胁不明
    (4, 0.4, 5.1),   # 头部浮出黑水（第一次揭示）
    (7, 0.6, 2.8),   # 插入：竖瞳特写（短，只作点睛）
    (5, 0.4, 4.4),   # 低角度逼近（压迫）
    (6, 0.6, 6.5),   # 收尾：整条龙立于雨夜江岸
]
XF = 0.4

GRADE = ("eq=contrast=1.09:brightness=-0.035:saturation=0.80,"
         "colorbalance=rs=-0.03:gs=0.01:bs=0.05,"
         "curves=all='0/0 0.25/0.20 0.75/0.79 1/1'")


def dur(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main():
    missing = [i for i, _, _ in PLAN if not os.path.exists(os.path.join(SRC, f"t{i:02d}.mp4"))]
    if missing:
        print("缺少片段:", missing); sys.exit(1)

    segs = []
    for i, a, b in PLAN:
        p = os.path.join(SRC, f"t{i:02d}.mp4")
        b = min(b, dur(p))
        segs.append((i, p, a, b - a))

    print("分段:", [f"t{i:02d} {d:.2f}s" for i, _, _, d in segs])
    total = sum(d for *_, d in segs) - XF * (len(segs) - 1)
    print(f"成片预计 {total:.2f}s")

    inputs = []
    for _, p, _, _ in segs:
        inputs += ["-i", p]

    fc = []
    for k, (i, p, a, d) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={a+d},setpts=PTS-STARTPTS,"
                  f"scale=1280:704,fps=24,setsar=1,{GRADE}[v{k}]")

    cur = "v0"
    offset = segs[0][3] - XF
    for k in range(1, len(segs)):
        nxt = f"x{k}"
        fc.append(f"[{cur}][v{k}]xfade=transition=fade:duration={XF}:offset={offset:.3f}[{nxt}]")
        cur = nxt
        offset += segs[k][3] - XF

    # 音频：第 1 段雨声循环铺满（各段音轨与 xfade 后长度不等，直接 concat 会音画错位）
    fc.append(f"[0:a]aloop=loop=-1:size=2000000000,atrim=0:{total:.3f},"
              f"afade=t=in:st=0:d=1.2,afade=t=out:st={total-1.8:.3f}:d=1.8,"
              f"volume=0.9[aout]")

    out = os.path.join(OUT, "走蛟-teaser-v2.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
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
