#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动作段拼片：验证"动作僵不僵 / 有没有交互感"
- 逐镜做亮度归一化（原始 Y=28~76，跨度太大），统一到 48
- 快切：xfade 0.25s（动作段要比剧情段更快）
- 音频 acrossfade 同步，保留水声与冲击
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "act")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

# (镜号, 入点, 出点, 目标亮度增益 gamma)
PLAN = [
    (3, 0.3, 2.0, 0.72),   # 水面被从下顶开（冲击起手，短）
    (1, 0.2, 5.2, 1.00),   # 蛟迎面冲来，水被犁开
    (4, 0.3, 5.2, 1.07),   # 浪把阿月掀退（反应）
    (2, 0.3, 4.3, 0.88),   # 头部甩向镜头（力量）
    (5, 0.4, 4.2, 1.33),   # 她的脸，喘（余韵）
]
XF = 0.25


def dur(p):
    out = subprocess.run([FF, "-i", p], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main():
    segs = []
    for i, a, b, g in PLAN:
        p = os.path.join(SRC, f"a{i:02d}.mp4")
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        segs.append((i, p, a, min(b, dur(p)), g))
    print("分段:", [(i, round(b - a, 2)) for i, _, a, b, _ in segs])

    inputs = []
    for _, p, _, _, _ in segs:
        inputs += ["-i", p]

    fc = []
    for k, (i, p, a, b, g) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale=1280:704,fps=24,setsar=1,"
                  f"eq=gamma={g}:saturation=1.06:contrast=1.04[v{k}]")

    cur, off = "v0", (segs[0][3] - segs[0][2]) - XF
    for k in range(1, len(segs)):
        fc.append(f"[{cur}][v{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]")
        cur = f"x{k}"
        off += (segs[k][3] - segs[k][2]) - XF

    acur = "0:a"
    for k in range(1, len(segs)):
        fc.append(f"[{acur}][{k}:a]acrossfade=d={XF}:c1=tri:c2=tri[a{k}]")
        acur = f"a{k}"

    out = os.path.join(OUT, "走蛟-动作验证.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", f"[{cur}]", "-map", f"[{acur}]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print("渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-2500:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
