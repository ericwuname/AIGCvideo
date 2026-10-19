#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
叙事重剪（8 镜 / 约 27 秒）
本轮改的三件事，全部来自 docs/19 的诊断：
  1. **硬切，不用溶解**——之前每处 0.3s 溶解把冲击力磨掉了。动作段必须硬切。
  2. **J-cut**——冲击点的水声提前 0.5s 起来（先听到，后看到），进入下一镜的前一镜末尾。
  3. **时长有长短**——建立 4.6s / 反应 1.8s / 冲击 1.5s，不再等长。
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAR = os.path.join(ROOT, "work", "clips", "nar")
IMM = os.path.join(ROOT, "work", "clips", "imm")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

TARGET_Y = 48.0
# (标签, 文件, 入点, 出点, 目标音量dBFS)
PLAN = [
    ("建立",  NAR, "n01.mp4", 0.4, 5.0, -24.0),   # 她在左，江面在右
    ("视线",  NAR, "n02.mp4", 0.3, 3.2, -27.0),   # 她转头看右
    ("所见",  NAR, "n03.mp4", 0.4, 4.4, -23.0),   # 远处水线推进
    ("僵住",  NAR, "n04.mp4", 0.4, 2.2, -28.0),   # Kuleshov：脸
    ("顶开",  IMM, "i03.mp4", 0.2, 3.6, -13.5),   # 冲击（最响）
    ("水扑",  NAR, "n05.mp4", 0.2, 1.7, -15.0),   # 水花打在她身上
    ("逼近",  IMM, "i04.mp4", 0.3, 5.5, -17.0),   # 蛟冲来
    ("余波",  IMM, "i01.mp4", 0.6, 4.2, -27.0),   # 回到水面（呼应开场）
]


def dur(p):
    o = subprocess.run([FF, "-i", p], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", o)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def mean_y(p):
    W, H = 320, 176
    raw = subprocess.run([FF, "-v", "error", "-i", p, "-vf", f"scale={W}:{H}",
                          "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W, 3).astype(np.float32)
    m = x.mean(axis=(0, 1, 2))
    return 0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]


def audio_rms(p, sr=16000):
    raw = subprocess.run([FF, "-v", "error", "-i", p, "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def gamma_for(y, target=TARGET_Y):
    if y <= 1:
        return 1.0
    return float(np.clip(np.log(y / 255.0) / np.log(target / 255.0), 0.55, 2.20))


def main():
    segs = []
    for label, d_, fn, a, b, tgt in PLAN:
        p = os.path.join(d_, fn)
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        b = min(b, dur(p) - 0.05)
        y, r = mean_y(p), audio_rms(p)
        gain = float(np.clip(10 ** ((tgt - 20 * np.log10(r + 1e-9)) / 20.0), 0.02, 40.0))
        segs.append((label, p, a, b, b - a, gamma_for(y), gain))
        print(f"  {label}: {b-a:.2f}s  Y={y:5.1f}→γ{gamma_for(y):.3f}  "
              f"{20*np.log10(r+1e-9):6.1f}→{tgt:6.1f}dB(×{gain:.2f})")

    inputs = []
    for _, p, *_ in segs:
        inputs += ["-i", p]

    fc = []
    for k, (label, p, a, b, d, g, gain) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale=1280:704,fps=24,setsar=1,"
                  f"eq=gamma={g:.3f}:saturation=1.06:contrast=1.05[v{k}]")
        fc.append(f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,volume={gain:.3f}[a{k}]")

    # 硬切：直接 concat，不加任何溶解
    vcat = "".join(f"[v{k}]" for k in range(len(segs)))
    acat = "".join(f"[a{k}]" for k in range(len(segs)))
    fc.append(f"{vcat}concat=n={len(segs)}:v=1:a=0[vout]")
    fc.append(f"{acat}concat=n={len(segs)}:v=0:a=1[amb0]")

    starts, t = [], 0.0
    for _, _, _, _, d, _, _ in segs:
        starts.append(t); t += d
    total = t
    hit = starts[4]           # 第 5 段（水面顶开）= 冲击点

    # ---- 声音：J-cut（水声提前 0.5s 起）+ 冲击前 duck + 低频三段 ----
    jcut = max(0.0, hit - 0.50)
    duck0 = max(0.0, hit - 0.70)
    fc.append(f"[amb0]volume='if(between(t,{duck0:.3f},{hit:.3f}),0.25,1)':eval=frame[amb]")
    # J-cut：低频轰鸣提前 0.5s 缓慢升起（先听到后看到）
    fc.append(f"sine=frequency=52:sample_rate=48000:duration=3.2,"
              f"afade=t=in:st=0:d=0.55,afade=t=out:st=1.6:d=1.6,volume=0.9[lo]")
    fc.append("anoisesrc=color=brown:sample_rate=48000:duration=2.0:amplitude=0.60,"
              "bandpass=f=170:width_type=h:w=240,"
              "afade=t=in:st=0:d=0.45,afade=t=out:st=0.5:d=1.5,volume=1.7[mid]")
    fc.append("anoisesrc=color=white:sample_rate=48000:duration=0.12:amplitude=0.35,"
              "highpass=f=1200,afade=t=out:st=0.02:d=0.10,volume=1.1[hi]")
    fc.append("[mid][hi]amix=inputs=2:duration=longest:normalize=0[hi2]")
    fc.append(f"[hi2]adelay={int(hit*1000)}|{int(hit*1000)}[hid]")
    fc.append(f"[lo][hid]amix=inputs=2:duration=longest:normalize=0,"
              f"adelay={int(jcut*1000)}|{int(jcut*1000)}[hitmix]")
    fc.append("[amb][hitmix]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.92,"
              f"afade=t=in:st=0:d=0.8,afade=t=out:st={total-1.6:.3f}:d=1.6[aout]")

    out = os.path.join(OUT, "走蛟-叙事版.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print(f"总长 {total:.2f}s，冲击点 {hit:.2f}s，J-cut 起于 {jcut:.2f}s，渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
