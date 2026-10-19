#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
《走蛟》剧情小样拼片
- 6 镜，trim + xfade 0.4s，音频用 acrossfade 同参数对齐（避免音画错位）
- 字幕按实测语音区间落位（解码音频算 RMS，找高于阈值的连续区间）
- 统一调色
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "story")
OUT = os.path.join(ROOT, "release")
os.makedirs(OUT, exist_ok=True)
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

ORDER = [1, 2, 3, 4, 5, 6]
XF = 0.4
# 亮度基线：原始片段 Y=11~31（太暗，手机上看是黑屏）。
# 目标是夜戏安全区 Y≈36~59（均值 45）。F 档实测：亮度 +0.035 / gamma 1.20 / 饱和 1.10
GRADE = "eq=brightness=0.035:contrast=1.00:gamma=1.20:saturation=1.10"

LINES = {4: "好大一条……", 5: "……龙。"}


def dur(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def speech_window(path, sr=16000):
    """按能量检测语音区间。
    注意：不能用基频周期性做判据——"咬着牙说话"会让周期性掉到 0.3 以下，但语音确实存在。
    判据改为：RMS 显著高于背景（>median*4 且 >max*0.35），且持续 ≥0.4s。"""
    raw = subprocess.run([FF, "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if x.size < sr:
        return None
    hop = int(sr * 0.05)
    n = x.size // hop
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    s = np.convolve(rms, np.ones(3) / 3, mode="same")
    med = float(np.median(s))
    thr = max(med * 3.0, float(s.max()) * 0.25)
    mask = s > thr
    # 容错：允许 0.3s 以内的空隙（句中换气/辅音造成的能量凹陷）
    gap = 6
    idx = np.where(mask)[0]
    if idx.size == 0:
        return None
    groups, cur = [], [idx[0]]
    for i in idx[1:]:
        if i - cur[-1] <= gap:
            cur.append(i)
        else:
            groups.append(cur); cur = [i]
    groups.append(cur)
    g = max(groups, key=len)
    start, end = g[0] * 0.05, (g[-1] + 1) * 0.05
    if end - start < 0.25:
        return None
    return start, end


def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(clips, durs, path):
    """clips: [(sid, path, sdur)]; 返回每条对白的绝对时间"""
    starts, t = {}, 0.0
    for k, (sid, _, d) in enumerate(clips):
        starts[sid] = t
        t += d - XF
    ev = []
    for sid, text in LINES.items():
        if sid not in starts:
            continue
        p = dict((s, pp) for s, pp, _ in clips)[sid]
        w = speech_window(p)
        sdur = durs[ORDER.index(sid)]
        if w is None:
            a, b = 0.8, sdur - 0.8
            print(f"  镜{sid}: 未检出语音，退化为 {a:.2f}-{b:.2f}")
        else:
            a, b = max(0.0, w[0] - 0.20), min(sdur, w[1] + 0.55)
            print(f"  镜{sid}: 语音 {w[0]:.2f}-{w[1]:.2f}s → 字幕 {a:.2f}-{b:.2f}s")
        # 字幕至少挂 1.2s，避免一闪而过
        if b - a < 1.2:
            b = min(sdur, a + 1.2)
        g0, g1 = starts[sid] + a, starts[sid] + b
        ev.append((g0, g1, text))
    hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 704
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,SimHei,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,3,1,2,60,60,56,134

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Main,,0,0,0,,{t}\n" for a, b, t in ev)
    open(path, "w", encoding="utf-8").write(hdr + body)
    return ev


def main():
    clips = []
    for i in ORDER:
        p = os.path.join(SRC, f"s{i:02d}.mp4")
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        clips.append((i, p, dur(p)))
    print("分段:", [(i, round(d, 2)) for i, _, d in clips])

    ass = os.path.join(SRC, "subs.ass")
    ev = build_ass(clips, [d for _, _, d in clips], ass)
    print("字幕事件:", [(round(a, 2), round(b, 2), t) for a, b, t in ev])

    inputs = []
    for _, p, _ in clips:
        inputs += ["-i", p]

    fc = []
    for k, (i, p, d) in enumerate(clips):
        fc.append(f"[{k}:v]scale=1280:704,fps=24,setsar=1,{GRADE}[v{k}]")
    cur = "v0"
    off = clips[0][2] - XF
    for k in range(1, len(clips)):
        nxt = f"x{k}"
        fc.append(f"[{cur}][v{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[{nxt}]")
        cur = nxt
        off += clips[k][2] - XF

    # 音频 acrossfade，参数与 xfade 一致 → 时长严格对齐，且保留对白
    acur = "0:a"
    for k in range(1, len(clips)):
        nxt = f"a{k}"
        fc.append(f"[{acur}][{k}:a]acrossfade=d={XF}:c1=tri:c2=tri[{nxt}]")
        acur = nxt

    fc.append(f"[{cur}]ass=subs.ass[vout]")

    out = os.path.join(OUT, "走蛟-剧情小样.mp4")
    # 必须 cd 到 SRC，ass 用相对路径（Windows 中文路径 + 盘符冒号会崩）
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", f"[{acur}]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print("渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore", cwd=SRC)
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
