#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
第二批运镜拼片（S2）
用户核心批评：**最后一个镜头与倒数第二个镜头的切换，声音很突兀**
根因：我给每镜都是独立生成的音轨 + 硬切 → 每切一次就换一个空间。

本版声音设计的三层：
  1. **连续雨声底**：一条素材循环铺满全片（-30dB），从头到尾不断 → 听觉上始终"在同一个地方"
  2. **事件层**：每镜自己的音轨按绝对时间铺开，但首尾各 0.35s 淡入淡出、互相压住
     → **画面硬切，声音重叠**（这是消除切割感的关键，专业里叫 L-cut / J-cut）
  3. **强调层**：怒吼前一记低频升起（J-cut），穿水时一记重击
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S2 = os.path.join(ROOT, "work", "clips", "s2")
BED = os.path.join(ROOT, "work", "clips", "mov", "m01.mp4")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

TARGET_Y = 30.0
CONTRAST = 1.10
SCURVE = "curves=all='0/0 0.14/0.10 0.45/0.45 0.78/0.85 1/1'"
FADE = 0.35      # 每镜音频头尾淡入淡出，制造重叠

PLAN = [
    ("俯瞰降下", "p01.mp4", 0.5, 10.0, -24.0),
    ("横移过村民", "p02.mp4", 0.5, 9.0, -22.0),
    ("环绕她", "p03.mp4", 0.5, 9.0, -24.0),
    ("斜升露全貌", "p04.mp4", 0.5, 9.0, -21.0),
    ("怒吼特写", "p05.mp4", 0.3, 8.0, -13.0),
    ("撞出水面", "p06.mp4", 0.4, 10.0, -14.0),
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


def audio_rms(p, ss=None, t=None, sr=16000):
    cmd = [FF, "-v", "error"]
    if ss is not None:
        cmd += ["-ss", str(ss), "-t", str(t)]
    cmd += ["-i", p, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def gamma_for(y, target=TARGET_Y):
    if y <= 1:
        return 1.0
    return float(np.clip(np.log(y / 255.0) / np.log(target / 255.0), 0.55, 2.20))


def measure_chain(p, a, b, chain):
    W, H = 320, 176
    cmd = [FF, "-v", "error", "-ss", str(a), "-t", str(max(0.4, b - a)), "-i", p,
           "-vf", f"{chain},scale={W}:{H}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if not raw:
        return TARGET_Y
    x = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W, 3).astype(np.float32)
    m = x.mean(axis=(0, 1, 2))
    return 0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]


def main():
    segs = []
    for label, fn, a, b, tgt in PLAN:
        p = os.path.join(S2, fn)
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        b = min(b, dur(p) - 0.05)
        y = mean_y(p)
        g1 = gamma_for(y)
        base = f"eq=gamma={g1:.3f}:contrast={CONTRAST}:saturation=1.16,{SCURVE}"
        m2 = measure_chain(p, a, b, base)
        g2 = gamma_for(m2) if m2 > 1 else 1.0
        r = audio_rms(p, a, b - a)
        gain = float(np.clip(10 ** ((tgt - 20 * np.log10(r + 1e-9)) / 20.0), 0.02, 40.0))
        segs.append((label, p, a, b, b - a, base, g2, gain))
        print(f"  {label}: {b-a:.2f}s  γ{g1:.2f}→实测{m2:4.1f}→γ{g2:.2f}  "
              f"{20*np.log10(r+1e-9):6.1f}→{tgt:6.1f}dB(×{gain:.2f})")

    starts, t = [], 0.0
    for _, _, _, _, d, _, _, _ in segs:
        starts.append(t); t += d
    total = t

    inputs = []
    for _, p, *_ in segs:
        inputs += ["-i", p]
    inputs += ["-i", BED]
    bed_idx = len(segs)

    fc = []
    for k, (label, p, a, b, d, base, g2, gain) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale=1280:704,fps=24,setsar=1,"
                  f"{base},eq=gamma={g2:.3f}[v{k}]")

    # ---- 画面：硬切 ----
    vcat = "".join(f"[v{k}]" for k in range(len(segs)))
    fc.append(f"{vcat}concat=n={len(segs)}:v=1:a=0[vout]")

    # ---- 声音第 2 层：事件音按绝对时间铺开，首尾淡入淡出互相压住 ----
    aops = []
    for k, (label, p, a, b, d, base, g2, gain) in enumerate(segs):
        fd = min(FADE, d / 3)
        fc.append(f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,volume={gain:.3f},"
                  f"afade=t=in:st=0:d={fd:.2f},afade=t=out:st={d-fd:.2f}:d={fd:.2f},"
                  f"adelay={int(starts[k]*1000)}|{int(starts[k]*1000)}[ea{k}]")
        aops.append(f"[ea{k}]")
    fc.append(f"{''.join(aops)}amix=inputs={len(segs)}:duration=longest:normalize=0[events]")

    # ---- 声音第 1 层：连续雨声底，铺满全片不断 ----
    fc.append(f"[{bed_idx}:a]aloop=loop=-1:size=2000000000,atrim=0:{total:.3f},"
              f"volume=0.10,afade=t=in:st=0:d=1.5,"
              f"afade=t=out:st={total-2.0:.3f}:d=2.0[bed]")

    # ---- 声音第 3 层：怒吼 J-cut + 穿水重击 ----
    roar = starts[4]       # 怒吼镜头起点
    crash = starts[5]      # 撞出水面起点
    fc.append(f"sine=frequency=48:sample_rate=48000:duration=2.2,"
              f"afade=t=in:st=0:d=0.45,afade=t=out:st=0.9:d=1.3,volume=0.85[r1]")
    fc.append("anoisesrc=color=brown:sample_rate=48000:duration=1.6:amplitude=0.55,"
              "bandpass=f=160:width_type=h:w=230,"
              "afade=t=in:st=0:d=0.40,afade=t=out:st=0.35:d=1.2,volume=1.3[r2]")
    fc.append("[r1][r2]amix=inputs=2:duration=longest:normalize=0,"
              f"adelay={int((roar-0.5)*1000)}|{int((roar-0.5)*1000)}[roar]")
    fc.append(f"sine=frequency=52:sample_rate=48000:duration=3.0,"
              f"afade=t=in:st=0:d=0.03,afade=t=out:st=1.2:d=1.7,volume=0.95[c1]")
    fc.append("anoisesrc=color=brown:sample_rate=48000:duration=2.0:amplitude=0.65,"
              "bandpass=f=180:width_type=h:w=250,"
              "afade=t=in:st=0:d=0.02,afade=t=out:st=0.5:d=1.4,volume=1.9[c2]")
    fc.append("anoisesrc=color=white:sample_rate=48000:duration=0.10:amplitude=0.40,"
              "highpass=f=1300,afade=t=out:st=0.015:d=0.08,volume=1.2[c3]")
    fc.append("[c2][c3]amix=inputs=2:duration=longest:normalize=0[ch]")
    fc.append("[c1][ch]amix=inputs=2:duration=longest:normalize=0,"
              f"adelay={int(crash*1000)}|{int(crash*1000)}[crash]")

    fc.append("[events][bed][roar][crash]amix=inputs=4:duration=first:normalize=0,"
              "alimiter=limit=0.92,"
              f"afade=t=in:st=0:d=1.0,afade=t=out:st={total-2.2:.3f}:d=2.2[aout]")

    out = os.path.join(OUT, "走蛟-运镜版2.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print(f"总长 {total:.2f}s  怒吼 {roar:.2f}s  重击 {crash:.2f}s  渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
