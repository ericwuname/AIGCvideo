#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
身临其境版拼片
修复：v1 只 trim 了画面没 trim 声音 → 每段声音更长 → 累积错位。
      本版 video 用 trim/setpts，audio 用 atrim/asetpts，参数完全一致，再用 xfade/acrossfade 同 d 串联。
新增：声音设计（压迫感来自"停顿"，不是音量）
      - 冲击点前 0.6s 把环境声压到 12%（几乎静音）
      - 冲击点砸一声 34Hz 次低频 + 低通棕噪声
      - 逐镜自动亮度归一化到 Y≈48
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "imm")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

# (镜号, 入点, 出点)
# (镜号, 入点, 出点, 目标音量 dBFS)
# 实测各镜原始音量差 21dB（i01 -36.8 / i04 -15.5），不归一化就会出现"开头死寂、突然轰一声"
PLAN = [
    (1, 0.4, 5.0, -25.0),   # 贴水面·前景芦苇（安静，留白）
    (2, 0.4, 2.1, -21.0),   # 水下黑影极近掠过（闷响渐起）
    (3, 0.2, 3.8, -13.5),   # 水面被顶开 · 水扑镜头（冲击，最响）
    (4, 0.3, 5.8, -17.5),   # 蛟迎面冲来
    (5, 0.3, 4.8, -20.0),   # 浪把阿月掀退
    (6, 0.4, 4.4, -24.0),   # 她抬头望向江面（收）
]
XF = 0.30
TARGET_Y = 48.0


def dur(p):
    out = subprocess.run([FF, "-i", p], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def mean_y(p):
    W, H = 320, 176
    raw = subprocess.run([FF, "-v", "error", "-i", p, "-vf", f"scale={W}:{H}",
                          "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W, 3).astype(np.float32)
    m = x.mean(axis=(0, 1, 2))
    return 0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]


def gamma_for(y, target=TARGET_Y):
    """ffmpeg eq 的 gamma 是 output = input^(1/gamma)，所以亮化要 gamma>1。
    由 (y/255)^(1/g) = target/255 解出 g = ln(y/255) / ln(target/255)。
    （上一版把分子分母写反了，导致暗的更暗、亮的更亮。）"""
    if y <= 1:
        return 1.0
    g = np.log(y / 255.0) / np.log(target / 255.0)
    return float(np.clip(g, 0.55, 2.20))


def audio_rms(p, sr=16000):
    raw = subprocess.run([FF, "-v", "error", "-i", p, "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def main():
    segs = []
    for i, a, b, tgt in PLAN:
        p = os.path.join(SRC, f"i{i:02d}.mp4")
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        d = dur(p)
        b = min(b, d - 0.05)
        y = mean_y(p)
        g = gamma_for(y)
        r = audio_rms(p)
        gain_db = tgt - 20 * np.log10(r + 1e-9)
        gain = float(np.clip(10 ** (gain_db / 20.0), 0.02, 40.0))
        segs.append((i, p, a, b, b - a, y, g, gain, tgt))
        print(f"  镜{i}: {b-a:.2f}s  画面Y={y:5.1f}→gamma {g:.3f}  "
              f"音频{20*np.log10(r+1e-9):6.1f}→{tgt:6.1f}dB (×{gain:.2f})")

    inputs = []
    for _, p, *_ in segs:
        inputs += ["-i", p]

    fc = []
    for k, s in enumerate(segs):
        i, p, a, b, d, y, g, gain, tgt = s
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,"
                  f"scale=1280:704,fps=24,setsar=1,"
                  f"eq=gamma={g:.3f}:saturation=1.06:contrast=1.04[v{k}]")

    cur, off = "v0", segs[0][4] - XF
    starts = [0.0]
    for k in range(1, len(segs)):
        fc.append(f"[{cur}][v{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]")
        cur = f"x{k}"
        starts.append(off)
        off += segs[k][4] - XF

    # ---- 音频：画面/声音用完全相同的入出点 + 逐镜响度归一化 ----
    for k, s in enumerate(segs):
        i, p, a, b, d, y, g, gain, tgt = s
        fc.append(f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,"
                  f"volume={gain:.3f}[a{k}]")
    acur = "a0"
    for k in range(1, len(segs)):
        fc.append(f"[{acur}][a{k}]acrossfade=d={XF}:c1=tri:c2=tri[b{k}]")
        acur = f"b{k}"
    total = starts[-1] + segs[-1][4]

    # ---- 声音设计：冲击点前压静 → 砸下来 ----
    # 注意：34Hz 手机放不出来，必须补 100~300Hz 与一记高频"裂"声
    hit = starts[2]
    duck0 = max(0.0, hit - 0.60)
    fc.append(f"[{acur}]volume='if(between(t,{duck0:.3f},{hit:.3f}),0.10,1)':eval=frame[amb]")
    # 低频胸腔感（音箱能听到）
    fc.append("sine=frequency=52:sample_rate=48000:duration=2.6,"
              "afade=t=in:st=0:d=0.02,afade=t=out:st=1.05:d=1.50,volume=1.0[lo]")
    # 中低频轰鸣（手机外放能听到）
    fc.append("anoisesrc=color=brown:sample_rate=48000:duration=1.6:amplitude=0.60,"
              "bandpass=f=170:width_type=h:w=240,"
              "afade=t=in:st=0:d=0.01,afade=t=out:st=0.30:d=1.20,volume=1.6[mid]")
    # 高频裂声（一记短促的"啪"，给手机）
    fc.append("anoisesrc=color=white:sample_rate=48000:duration=0.12:amplitude=0.35,"
              "highpass=f=1200,afade=t=out:st=0.02:d=0.10,volume=1.1[hi]")
    fc.append(f"[mid][hi]amix=inputs=2:duration=longest:normalize=0[hi2]")
    fc.append(f"[hi2]adelay=40|40[hid]")
    fc.append(f"[lo][hid]amix=inputs=2:duration=longest:normalize=0,"
              f"adelay={int(hit*1000)}|{int(hit*1000)}[hitmix]")
    fc.append("[amb][hitmix]amix=inputs=2:duration=first:normalize=0,"
              f"alimiter=limit=0.92,"
              f"afade=t=in:st=0:d=0.8,afade=t=out:st={total-1.4:.3f}:d=1.4[aout]")

    out = os.path.join(OUT, "走蛟-身临其境.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", f"[{cur}]", "-map", "[aout]",
           "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print(f"总长 {total:.2f}s，冲击点 {hit:.2f}s，渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
