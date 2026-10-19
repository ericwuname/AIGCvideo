#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
《走蛟》成片合成 v2
改用 ASS 字幕烧录（drawtext 在 Windows 中文路径下转义会崩）
1. 归一化 1280x704 / 24fps / 48k stereo
2. 片头黑场 + 12 镜 拼接
3. 一次性烧录 ASS 字幕 → release/走蛟-ep01.mp4
"""
import json, os, shutil, subprocess

FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
FONT_SRC = r"C:/Windows/Fonts/simhei.ttf"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(ROOT, "work", "clips", "ep01")
WORK = os.path.join(ROOT, "work", "build")
REL = os.path.join(ROOT, "release")
FONTDIR = os.path.join(WORK, "fonts")
for d in (WORK, REL, FONTDIR):
    os.makedirs(d, exist_ok=True)

W, H, FPS = 1280, 704, 24
INTRO = 3.5

# 实测时长（ffprobe）
DUR = {1:6.58, 2:7.30, 3:7.30, 4:7.30, 5:8.00, 6:7.30, 7:7.30,
       8:8.00, 9:7.30, 10:8.00, 11:8.00, 12:8.00}


def run(cmd, desc="", cwd=None):
    print(f"» {desc}")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd)
    if r.returncode != 0:
        print("FFMPEG ERROR:\n", (r.stderr or "")[-2500:])
        raise SystemExit(1)


def ass_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def norm(src, dst):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
         "-af", "aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:st=0:d=0.08",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
         dst], f"归一化 {os.path.basename(dst)}")


def make_intro(dst):
    run([FF, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d={INTRO}:r={FPS}",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", str(INTRO), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "128k", "-shortest", dst], "片头黑场")


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
    # 片名
    ev.append(f"Dialogue: 0,{ass_time(0.40)},{ass_time(3.10)},Title,,0,0,0,,{{\\fad(500,500)}}走  蛟")
    ev.append(f"Dialogue: 1,{ass_time(1.10)},{ass_time(3.10)},SubSmall,,0,0,0,,{{\\fad(400,400)}}民间志异 · 第一集")
    # 镜6 旁白
    s6 = starts[6] + 0.30
    ev.append(f"Dialogue: 0,{ass_time(s6)},{ass_time(starts[6]+DUR[6]-0.30)},Sub,,0,0,0,,"
              f"{{\\fad(280,280)}}老辈人说，走蛟那夜若被人撞见，是要讨一句封正的。\\N"
              f"说它是龙，它就活了；说它是蛇……它就散了。")
    # 镜8 对白
    s8 = starts[8] + 0.80
    ev.append(f"Dialogue: 0,{ass_time(s8)},{ass_time(starts[8]+DUR[8]-0.40)},Sub,,0,0,0,,"
              f"{{\\fad(200,200)}}好大一条……")
    # 镜10 对白
    s10 = starts[10] + 0.80
    ev.append(f"Dialogue: 0,{ass_time(s10)},{ass_time(starts[10]+DUR[10]-0.40)},Sub,,0,0,0,,"
              f"{{\\fad(200,200)}}……龙。")
    # 片尾
    s12 = starts[12] + 2.60
    ev.append(f"Dialogue: 0,{ass_time(s12)},{ass_time(total-0.40)},End,,0,0,0,,"
              f"{{\\fad(700,500)}}那一夜，她放走了一条龙。\\N也放走了自己的恨。")
    return head + "\n".join(ev) + "\n"


def main():
    urls_file = os.path.join(CLIPS, "video_urls.json")
    have = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}
    missing = [i for i in DUR if str(i) not in have]
    if missing:
        print("⚠ 缺片:", missing)
        if len(missing) > 4:
            return

    # 字体
    fpath = os.path.join(FONTDIR, "simhei.ttf")
    if not os.path.exists(fpath):
        shutil.copy(FONT_SRC, fpath)

    # 1. 归一化 + 拼接
    parts = []
    intro = os.path.join(WORK, "00_intro.mp4")
    make_intro(intro)
    parts.append(intro)
    for sid in sorted(DUR):
        src = os.path.join(CLIPS, f"shot_{sid:02d}.mp4")
        if not os.path.exists(src):
            continue
        dst = os.path.join(WORK, f"n_{sid:02d}.mp4")
        norm(src, dst)
        parts.append(dst)

    lst = os.path.join(WORK, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write("file '" + p.replace("\\", "/") + "'\n")
    joined = os.path.join(WORK, "joined.mp4")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", joined], "拼接")

    # 2. 时间轴
    starts, t = {}, INTRO
    for sid in sorted(DUR):
        starts[sid] = t
        t += DUR[sid]
    total = t

    # 3. ASS
    ass = build_ass(starts, total)
    ass_path = os.path.join(WORK, "subs.ass")
    open(ass_path, "w", encoding="utf-8").write(ass)

    # 4. 烧录（在 WORK 目录下执行，全部相对路径，避开中文与盘符冒号）
    out = os.path.join(REL, "走蛟-ep01.mp4")
    run([FF, "-y", "-hide_banner", "-loglevel", "error",
         "-i", "joined.mp4", "-vf", "ass=subs.ass:fontsdir=fonts",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-c:a", "copy", "-movflags", "+faststart", out.replace("\\", "/")],
        "烧录字幕", cwd=WORK)

    print(f"\n✓ 成片: {out}")
    print(f"  时长 {total:.1f}s   分辨率 {W}x{H}   {os.path.getsize(out)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
