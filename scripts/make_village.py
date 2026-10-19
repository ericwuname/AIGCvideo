#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
村庄夜惊拼片
用户要求：
  - 龙的威压感来自"看不清"：黑暗为主，闪电瞬间才照亮局部
  - 水要一直在动
  - 运镜要服务于表达，不为运镜而运镜
  - 人物要有 psych/反应，不是道具

本版新增：**后期人工打闪电**
  每次闪电只有 2–3 帧爆亮（eq brightness 时间轴开窗），雷声延迟 0.6~1.6s 才到
  —— 光速快于声速，观众说不出，但身体感觉得到。
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "vil")
BED = os.path.join(ROOT, "work", "clips", "mov", "m01.mp4")
ROAR = os.path.join(ROOT, "work", "clips", "s2", "p05.mp4")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

TARGET_Y = 28.0
CONTRAST = 1.12
SCURVE = "curves=all='0/0 0.12/0.08 0.45/0.45 0.78/0.86 1/1'"
FADE = 0.35

# (标签, 文件, 入点, 出点, 目标音量dBFS)
PLAN = [
    ("村庄俯瞰", "v01.mp4", 0.5, 7.0, -24.0),
    ("老妇添柴", "v02.mp4", 0.5, 7.0, -26.0),
    ("门缝偷看", "v03.mp4", 0.4, 5.0, -28.0),
    ("渔夫回头", "v04.mp4", 0.4, 6.0, -25.0),
    ("她在河边", "v05.mp4", 0.5, 7.0, -24.0),
    ("水线推进", "v06.mp4", 0.4, 5.0, -22.0),
    ("黑暗巨物", "v07.mp4", 0.5, 9.0, -20.0),
    ("鳞片粘液", "v08.mp4", 0.3, 5.0, -19.0),
    ("压过来", "v09.mp4", 0.4, 7.0, -14.0),
]
# 闪电：(镜序号从0起, 镜内时间, 持续帧数/24, 亮度增益)
FLASH = [
    (0, 4.2, 0.10, 0.40), (0, 4.55, 0.05, 0.22),
    (3, 3.6, 0.08, 0.30),
    (5, 2.2, 0.10, 0.36), (5, 2.5, 0.05, 0.18),
    (6, 3.0, 0.12, 0.45), (6, 4.6, 0.08, 0.30),
    (7, 1.6, 0.14, 0.50), (7, 2.0, 0.06, 0.25),
    (8, 1.4, 0.16, 0.55), (8, 6.4, 0.12, 0.34),
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


def audio_rms(p, ss, t, sr=16000):
    raw = subprocess.run([FF, "-v", "error", "-ss", str(ss), "-t", str(t), "-i", p,
                          "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
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
    segs, starts, t = [], [], 0.0
    for k, (label, fn, a, b, tgt) in enumerate(PLAN):
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        b = min(b, dur(p) - 0.05)
        y = mean_y(p)
        g1 = gamma_for(y)
        base = f"eq=gamma={g1:.3f}:contrast={CONTRAST}:saturation=1.14,{SCURVE}"
        m2 = measure_chain(p, a, b, base)
        g2 = gamma_for(m2) if m2 > 1 else 1.0
        r = audio_rms(p, a, b - a)
        gain = float(np.clip(10 ** ((tgt - 20 * np.log10(r + 1e-9)) / 20.0), 0.02, 40.0))
        segs.append((label, p, a, b, b - a, base, g2, gain))
        starts.append(t); t += b - a
        print(f"  {label}: {b-a:.2f}s  γ{g1:.2f}→实测{m2:4.1f}→γ{g2:.2f}")
    total = t

    inputs = []
    for _, p, *_ in segs:
        inputs += ["-i", p]
    inputs += ["-i", BED]
    bed_i = len(segs)

    fc = []
    for k, (label, p, a, b, d, base, g2, gain) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale=1280:704,fps=24,setsar=1,"
                  f"{base},eq=gamma={g2:.3f}[v{k}]")

    vcat = "".join(f"[v{k}]" for k in range(len(segs)))
    fc.append(f"{vcat}concat=n={len(segs)}:v=1:a=0[vc]")

    # ---- 闪电：时间轴开窗，每次 2~4 帧爆亮 ----
    fl = []
    for idx, (si, ts, dd, bg) in enumerate(FLASH):
        t0 = starts[si] + ts
        fl.append((t0, t0 + dd, bg))
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b, _ in fl)
    # 分档亮度：用两个 eq 叠出强弱两级
    strong = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b, g in fl if g >= 0.40)
    weak = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b, g in fl if 0.25 <= g < 0.40)
    slight = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b, g in fl if g < 0.25)
    chain = "[vc]"
    if strong:
        fc.append(f"[vc]eq=brightness=0.34:enable='{strong}'[f1]"); chain = "[f1]"
    if weak:
        fc.append(f"{chain}eq=brightness=0.20:enable='{weak}'[f2]"); chain = "[f2]"
    if slight:
        fc.append(f"{chain}eq=brightness=0.10:enable='{slight}'[f3]"); chain = "[f3]"
    fc.append(f"{chain}null[vout]")

    # ---- 声音 ----
    aops = []
    for k, (label, p, a, b, d, base, g2, gain) in enumerate(segs):
        fd = min(FADE, d / 3)
        fc.append(f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,volume={gain:.3f},"
                  f"afade=t=in:st=0:d={fd:.2f},afade=t=out:st={d-fd:.2f}:d={fd:.2f},"
                  f"adelay={int(starts[k]*1000)}|{int(starts[k]*1000)}[ea{k}]")
        aops.append(f"[ea{k}]")
    fc.append(f"{''.join(aops)}amix=inputs={len(segs)}:duration=longest:normalize=0[events]")

    fc.append(f"[{bed_i}:a]aloop=loop=-1:size=2000000000,atrim=0:{total:.3f},volume=0.11,"
              f"afade=t=in:st=0:d=1.5,afade=t=out:st={total-2.0:.3f}:d=2.0[bed]")

    # 雷声：每个闪电之后 0.6~1.6s 才到（光比声快）
    th = []
    for i, (a, b, g) in enumerate(fl):
        th.append((a + 0.55 + 0.25 * (i % 3), 0.55 + 0.35 * g))
    labels = []
    for i, (t0, amp) in enumerate(th):
        fc.append(f"anoisesrc=color=brown:sample_rate=48000:duration=2.6:amplitude={amp:.2f},"
                  f"lowpass=f=190,afade=t=in:st=0:d=0.15,afade=t=out:st=0.8:d=1.8,"
                  f"volume=1.9,adelay={int(t0*1000)}|{int(t0*1000)}[th{i}]")
        labels.append(f"[th{i}]")

    # 结尾一声龙吟（低沉、闷、听得见但听不清）
    cl = starts[-1] + 1.2
    fc.append(f"sine=frequency=62:sample_rate=48000:duration=2.8,"
              f"afade=t=in:st=0:d=0.5,afade=t=out:st=1.2:d=1.6,volume=0.9[g1]")
    fc.append(f"sine=frequency=93:sample_rate=48000:duration=2.8,"
              f"afade=t=in:st=0:d=0.5,afade=t=out:st=1.2:d=1.6,volume=0.45[g2]")
    fc.append("anoisesrc=color=brown:sample_rate=48000:duration=2.4:amplitude=0.5,"
              "bandpass=f=200:width_type=h:w=260,"
              f"afade=t=in:st=0:d=0.4,afade=t=out:st=1.0:d=1.4,volume=1.2[g3]")
    fc.append(f"[g1][g2][g3]amix=inputs=3:duration=longest:normalize=0,"
              f"adelay={int(cl*1000)}|{int(cl*1000)}[growl]")

    mixin = "[events][bed]" + "".join(labels) + "[growl]"
    n_mix = 2 + len(labels) + 1
    fc.append(f"{mixin}amix=inputs={n_mix}:duration=first:normalize=0,alimiter=limit=0.92,"
              f"afade=t=in:st=0:d=1.0,afade=t=out:st={total-2.4:.3f}:d=2.4[aout]")

    out = os.path.join(OUT, "走蛟-村庄夜惊.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print(f"总长 {total:.2f}s  闪电 {len(fl)} 次  龙吟 {cl:.2f}s  渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
