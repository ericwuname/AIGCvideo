#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
重剪（FIX 版）
修四件事：
  1. **删掉鳞片慢滴那一镜**（用户："水慢慢滴在鳞片上是啥情况，看的很无语"）—— 物料空镜，不该在剪辑里
  2. **龙吟提到最前面**：它必须在第一次有人转头之前响，否则观众不知道他们在看什么
     —— 龙吟是本地合成的 39~75Hz，不是视频模型给的噪声
  3. **转场改 3 帧（0.12s）微溶解**：硬切在大黑大白之间太割裂，3 帧溶解肉眼几乎看不见，但把"跳"磨掉了
  4. 闪电保留，雷声仍延迟到达
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIL = os.path.join(ROOT, "work", "clips", "vil")
FIX = os.path.join(ROOT, "work", "clips", "fix")
BED = os.path.join(ROOT, "work", "clips", "mov", "m01.mp4")
ROAR = os.path.join(ROOT, "assets", "audio", "dragon_roar.wav")
RAIN = os.path.join(ROOT, "work", "fx", "rain_loop.mp4")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

# 每镜叠雨的强度（None = 不叠，屋内那镜不叠）
RAIN_OP = [0.55, None, 0.32, 0.55, 0.50, 0.45, 0.45, 0.45]

TARGET_Y = 28.0
CONTRAST = 1.12
SCURVE = "curves=all='0/0 0.12/0.08 0.45/0.45 0.78/0.86 1/1'"
XF = 0.12          # 3 帧微溶解

# (标签, 目录, 文件, 入点, 出点, 目标音量dBFS)
PLAN = [
    ("村庄俯瞰",   VIL, "v01.mp4", 0.5, 7.0, -25.0, False),
    ("老妇手停",   VIL, "v02.mp4", 0.4, 6.6, -27.0, True),    # 室内：不叠雨
    ("门缝偷看",   FIX, "F3.mp4",  0.4, 5.0, -27.0, True),    # 室内（门开）：不叠雨
    ("渔夫回头",   FIX, "F4.mp4",  0.4, 6.0, -25.0, False),
    ("她在河边",   VIL, "v05.mp4", 0.5, 7.0, -25.0, False),
    ("水线推进",   VIL, "v06.mp4", 0.4, 5.0, -23.0, False),
    ("黑暗巨物",   FIX, "F1.mp4",  0.5, 9.0, -21.0, False),
]
FLASH = [(0, 4.0, 0.10, 0.42), (0, 4.4, 0.05, 0.20),
         (6, 3.2, 0.12, 0.46), (6, 4.8, 0.07, 0.28),
         (6, 6.2, 0.16, 0.55), (6, 7.6, 0.12, 0.34)]


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
    segs = []
    for label, d_, fn, a, b, tgt, indoor in PLAN:
        p = os.path.join(d_, fn)
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
        segs.append((label, p, a, b, b - a, base, g2, gain, indoor))
        print(f"  {label}: {b-a:.2f}s  γ{g1:.2f}→实测{m2:4.1f}→γ{g2:.2f}")

    starts, t = [0.0], 0.0
    for _, _, _, _, d, _, _, _, _ in segs:
        t += d - XF
    total = t + XF
    for k in range(1, len(segs)):
        starts.append(starts[k - 1] + segs[k - 1][4] - XF)

    # 把"哪些时段是室内"写出来，供 add_rain.py 关掉该时段的雨
    tl = [{"label": s[0], "start": round(starts[i], 3), "end": round(starts[i] + s[4], 3),
           "indoor": bool(s[8])} for i, s in enumerate(segs)]
    json.dump(tl, open(os.path.join(OUT, "_timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("  室内镜头（不叠雨）:", [x["label"] for x in tl if x["indoor"]])

    inputs = []
    for _, p, *_ in segs:
        inputs += ["-i", p]
    bed_i = len(segs)
    inputs += ["-i", BED]
    roar_i = len(segs) + 1
    inputs += ["-i", ROAR]

    fc = []
    for k, (label, p, a, b, d, base, g2, gain, indoor) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale=1280:704,fps=24,setsar=1,"
                  f"{base},eq=gamma={g2:.3f},format=yuv420p[v{k}]")

    cur, off = "v0", segs[0][4] - XF
    for k in range(1, len(segs)):
        fc.append(f"[{cur}][v{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]")
        cur = f"x{k}"
        off += segs[k][4] - XF

    # 雨层不在 ffmpeg 里叠（滤镜链会把画面染紫，实测 RGB 均值 64/13/72）
    # 改为渲染无雨版，再用 scripts/add_rain.py 逐帧合成
    cur = cur

    # 闪电
    fl = [(starts[si] + ts, starts[si] + ts + dd, bg) for si, ts, dd, bg in FLASH]
    strong = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b, g in fl if g >= 0.40)
    weak = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b, g in fl if 0.25 <= g < 0.40)
    chain = f"[{cur}]"
    if strong:
        fc.append(f"[{cur}]eq=brightness=0.36:enable='{strong}'[f1]"); chain = "[f1]"
    if weak:
        fc.append(f"{chain}eq=brightness=0.20:enable='{weak}'[f2]"); chain = "[f2]"
    fc.append(f"{chain}null[vout]")

    # 声音事件层
    aops = []
    for k, (label, p, a, b, d, base, g2, gain, indoor) in enumerate(segs):
        fd = min(0.35, d / 3)
        fc.append(f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,volume={gain:.3f},"
                  f"afade=t=in:st=0:d={fd:.2f},afade=t=out:st={d-fd:.2f}:d={fd:.2f},"
                  f"adelay={int(starts[k]*1000)}|{int(starts[k]*1000)}[ea{k}]")
        aops.append(f"[ea{k}]")
    fc.append(f"{''.join(aops)}amix=inputs={len(segs)}:duration=longest:normalize=0[events]")

    fc.append(f"[{bed_i}:a]aloop=loop=-1:size=2000000000,atrim=0:{total:.3f},volume=0.11,"
              f"afade=t=in:st=0:d=1.5,afade=t=out:st={total-2.0:.3f}:d=2.0[bed]")

    # ★ 龙吟：第一次有人转头之前就响（放在第 1 镜尾部，压到第 2 镜）
    roar1 = 4.6
    roar2 = max(0.0, total - 3.6)
    fc.append(f"[{roar_i}:a]asplit=2[r1][r2]")
    fc.append(f"[r1]afade=t=out:st=3.6:d=1.0,volume=1.0,"
              f"adelay={int(roar1*1000)}|{int(roar1*1000)}[roarA]")
    fc.append(f"[r2]volume=0.85,adelay={int(roar2*1000)}|{int(roar2*1000)}[roarB]")

    # 雷声：每个闪电后 0.55~1.1s 才到
    labels = []
    for i, (a, b, g) in enumerate(fl):
        t0 = a + 0.55 + 0.2 * (i % 3)
        amp = 0.55 + 0.35 * g
        fc.append(f"anoisesrc=color=brown:sample_rate=48000:duration=2.6:amplitude={amp:.2f},"
                  f"lowpass=f=190,afade=t=in:st=0:d=0.15,afade=t=out:st=0.8:d=1.8,volume=1.9,"
                  f"adelay={int(t0*1000)}|{int(t0*1000)}[th{i}]")
        labels.append(f"[th{i}]")

    mixin = "[events][bed][roarA][roarB]" + "".join(labels)
    n_mix = 4 + len(labels)
    fc.append(f"{mixin}amix=inputs={n_mix}:duration=first:normalize=0,"
              f"alimiter=limit=0.95,afade=t=in:st=0:d=1.0,"
              f"afade=t=out:st={total-2.4:.3f}:d=2.4[aout]")

    out = os.path.join(OUT, "_tmp_norain.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print(f"总长 {total:.2f}s  龙吟@{roar1:.1f}s 与 @{roar2:.1f}s  渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
