#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
《走蛟》v1.5 —— 在 v1 基础上的确定性修复（不重拍）
修复项：
  1. 色彩统一：按场景组把亮度/色温/饱和度拉到规范区间（v1 实测亮度差 97、色温差 50）
  2. 音画对齐：字幕按【实测语音区间】放置，不再靠猜
  3. 大跳变处加 0.5s 溶解转场缓冲
输出: release/走蛟-ep01-v15.mp4
"""
import json, os, shutil, subprocess
import numpy as np
from PIL import Image

FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
FONT_SRC = r"C:/Windows/Fonts/simhei.ttf"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(ROOT, "work", "clips", "ep01")
WORK = os.path.join(ROOT, "work", "build15")
REL = os.path.join(ROOT, "release")
FONTDIR = os.path.join(WORK, "fonts")
for d in (WORK, REL, FONTDIR):
    os.makedirs(d, exist_ok=True)

W, H, FPS, INTRO = 1280, 704, 24, 3.5
DUR = {1:6.58, 2:7.30, 3:7.30, 4:7.30, 5:8.00, 6:7.30, 7:7.30,
       8:8.00, 9:7.30, 10:8.00, 11:8.00, 12:8.00}

# 场景组 → (目标亮度, 目标R-B, 目标饱和度%)
GROUPS = {
    1:(65,-24,50), 2:(65,-24,50), 3:(65,-24,50), 4:(65,-24,50),
    5:(42,-20,50), 6:(42,-20,50), 9:(42,-20,50),
    7:(65,-24,50), 8:(65,-24,50), 10:(65,-24,50),
    11:(78,-6,50),
    12:(105,4,35),
}
# 需要溶解转场的切点（前镜号→后镜号）
XFADE_AT = {4:0.5, 11:0.5}
XFADE_D = 0.5

# 实测语音区间（相对镜头起点，秒）→ 字幕显示区间（提前 0.3s 出现，语音结束后保留 1.6s 供阅读）
SPEECH = {8:(1.78,2.94), 10:(3.58,3.90)}


def run(cmd, desc="", cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd)
    if r.returncode != 0:
        print(f"✗ {desc}\n{(r.stderr or '')[-2000:]}")
        raise SystemExit(1)
    if desc: print(f"» {desc}")


def measure(src):
    """抽中间帧测亮度/色温/饱和度"""
    tmp = os.path.join(WORK, "_m.png")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", "3", "-i", src,
         "-frames:v", "1", tmp])
    a = np.asarray(Image.open(tmp).convert("RGB")).astype(np.float32)
    Y = (0.299*a[:,:,0] + 0.587*a[:,:,1] + 0.114*a[:,:,2]).mean()
    rb = a[:,:,0].mean() - a[:,:,2].mean()
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = ((mx-mn)/(mx+1e-6)).mean()*100
    return Y, rb, sat


def grade_and_norm(sid, src, dst):
    """两轮迭代把色彩拉到目标区间"""
    tY, tRB, tSAT = GROUPS[sid]
    b_add, rm, sat_mul = 0.0, 0.0, 1.0
    for it in range(2):
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
              f"eq=brightness={b_add:.4f}:saturation={sat_mul:.3f}:contrast=1.02,"
              f"colorbalance=rm={rm:.4f}:bm={-rm*0.5:.4f}")
        run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
             "-vf", vf + ",format=yuv420p",
             "-af", "aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:st=0:d=0.06",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", dst])
        Y, rb, sat = measure(dst)
        dY, dRB = tY - Y, tRB - rb
        print(f"  镜{sid:02d} 迭代{it+1}: Y={Y:.0f}(目标{tY}) R-B={rb:.0f}(目标{tRB}) SAT={sat:.0f}%"
              + ("  ✓" if abs(dY) <= 8 and abs(dRB) <= 8 else ""))
        if abs(dY) <= 8 and abs(dRB) <= 8:
            break
        b_add += dY / 255.0
        rm += dRB / 255.0 * 1.2
        if it == 0:
            sat_mul = max(0.5, min(1.6, tSAT / max(sat, 1)))


def make_intro(dst):
    run([FF, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d={INTRO}:r={FPS}",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", str(INTRO), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "128k", "-shortest", dst], "片头")


def ass_time(s):
    return f"{int(s//3600)}:{int((s%3600)//60):02d}:{s%60:05.2f}"


def build_ass(starts, total):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,SimHei,86,&H00D6E2E8,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,6,0,1,0,3,5,60,60,0,1
Style: Sub,SimHei,36,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,2,0,1,3,1,2,60,60,56,1
Style: SubSmall,SimHei,30,&H008A8578,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,4,0,1,0,2,5,60,60,0,1
Style: End,SimHei,42,&H00E8E2D6,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,3,0,1,2,2,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    ev.append(f"Dialogue: 0,{ass_time(0.40)},{ass_time(3.10)},Title,,0,0,0,,{{\\fad(500,500)}}走  蛟")
    ev.append(f"Dialogue: 1,{ass_time(1.10)},{ass_time(3.10)},SubSmall,,0,0,0,,{{\\fad(400,400)}}民间志异 · 第一集")
    # 旁白（镜6，无配音，纯字幕，给足阅读时间）
    s6 = starts[6] + 0.40
    ev.append(f"Dialogue: 0,{ass_time(s6)},{ass_time(starts[6]+DUR[6]-0.25)},Sub,,0,0,0,,"
              f"{{\\fad(250,250)}}老辈人说，走蛟那夜若被人撞见，是要讨一句封正的。\\N"
              f"说它是龙，它就活了；说它是蛇……它就散了。")
    # 对白：严格对齐实测语音
    for sid, (a, b) in SPEECH.items():
        st = starts[sid] + max(0.0, a - 0.30)
        en = starts[sid] + b + 1.60
        txt = "好大一条……" if sid == 8 else "……龙。"
        ev.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Sub,,0,0,0,,"
                  f"{{\\fad(150,250)}}{txt}")
    # 片尾
    ev.append(f"Dialogue: 0,{ass_time(starts[12]+2.60)},{ass_time(total-0.40)},End,,0,0,0,,"
              f"{{\\fad(700,500)}}那一夜，她放走了一条龙。\\N也放走了自己的恨。")
    return head + "\n".join(ev) + "\n"


def main():
    fpath = os.path.join(FONTDIR, "simhei.ttf")
    if not os.path.exists(fpath): shutil.copy(FONT_SRC, fpath)

    print("=== 第一步：逐镜调色 ===")
    parts = []
    intro = os.path.join(WORK, "00_intro.mp4")
    make_intro(intro)
    parts.append((intro, INTRO))
    for sid in sorted(DUR):
        src = os.path.join(CLIPS, f"shot_{sid:02d}.mp4")
        if not os.path.exists(src): continue
        dst = os.path.join(WORK, f"g_{sid:02d}.mp4")
        grade_and_norm(sid, src, dst)
        parts.append((dst, DUR[sid]))

    print("\n=== 第二步：拼接（全部切点用 xfade 交叉溶解） ===")
    # 用 xfade 处理所有切点，避免硬切造成的突兀感
    XF = 0.30  # 每处溶解时长
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error"]
    for p, _ in parts:
        cmd += ["-i", p]

    n = len(parts)
    fc = []
    # 视频链
    prev = "[0:v]"
    cum = parts[0][1]
    for i in range(1, n):
        off = cum - XF
        out = f"[v{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{out}")
        prev = out
        cum += parts[i][1] - XF
    # 音频链
    aprev = "[0:a]"
    for i in range(1, n):
        out = f"[a{i}]"
        fc.append(f"{aprev}[{i}:a]acrossfade=d={XF}:c1=tri:c2=tri{out}")
        aprev = out
    fc.append(f"{prev}copy[vfinal]")
    fc.append(f"{aprev}anull[afinal]")

    joined = os.path.join(WORK, "joined.mp4")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vfinal]", "-map", "[afinal]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", joined]
    run(cmd, "xfade 拼接")

    # 时间轴随转场前移
    starts, t = {}, 0.0
    for idx, sid in enumerate(sorted(DUR)):
        start = parts[0][1] + sum(DUR[s] for s in sorted(DUR)[:idx]) - idx * XF
        starts[sid] = start
    total = parts[0][1] + sum(DUR.values()) - (len(DUR) - 1) * XF
    print(f"  转场后总时长 {total:.2f}s（原 93.9s）")

    ass_path = os.path.join(WORK, "subs.ass")
    open(ass_path, "w", encoding="utf-8").write(build_ass(starts, total))

    out = os.path.join(REL, "走蛟-ep01-v15.mp4")
    run([FF, "-y", "-hide_banner", "-loglevel", "error",
         "-i", "joined.mp4", "-vf", "ass=subs.ass:fontsdir=fonts",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-c:a", "copy", "-movflags", "+faststart", out.replace("\\", "/")],
        "烧录字幕", cwd=WORK)

    print(f"\n✓ {out}")
    print(f"  {total:.1f}s  {os.path.getsize(out)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
