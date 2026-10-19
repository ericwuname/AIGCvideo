#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
运镜版拼片（MOV）
与之前最大的区别在**调色逻辑**：
  之前 = 把每镜的平均亮度强行拉到同一个值（Y≈48）→ 全片一片中灰 → 审美下降、压迫感没了
  现在 = 只做适度提亮，再叠 S 曲线（压深黑、提亮高光）→ 黑有黑的重量，高光锐利

另外：
  - 运镜镜头的头尾少裁（0.3~0.5s），保住运动本身
  - 硬切
  - 画面/声音同入出点；逐镜响度归一；冲击点 J-cut
"""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "clips", "mov")
OUT = os.path.join(ROOT, "release")
FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

# (标签, 文件, 入点, 出点, 目标音量dBFS)
PLAN = [
    ("推进", "m01.mp4", 0.3, 10.0, -24.0),
    ("涉水", "m02.mp4", 0.3, 8.0, -22.0),
    ("后拉", "m03.mp4", 0.3, 9.0, -25.0),
    ("涌来", "m04.mp4", 0.2, 7.0, -18.0),
    ("穿水", "m05.mp4", 0.4, 10.0, -15.0),
    ("逼近", "m06.mp4", 0.3, 8.0, -14.0),
]
TARGET_Y = 30.0          # 目标均值（比之前的 48 更暗，给黑场留空间）
CONTRAST = 1.10
# S 曲线：压深黑、提亮高光（先做对比，再用二次 gamma 把均值锚回来）
SCURVE = "curves=all='0/0 0.14/0.10 0.45/0.45 0.78/0.85 1/1'"


def measure_chain(p, a, b, chain):
    """把 chain 实际跑一遍，量这条链子作用后的平均亮度（保证校正不是纸上算的）"""
    W, H = 320, 176
    cmd = [FF, "-v", "error", "-ss", f"{a}", "-t", f"{max(0.4, b-a)}", "-i", p,
           "-vf", f"{chain},scale={W}:{H}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if not raw:
        return TARGET_Y
    x = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W, 3).astype(np.float32)
    m = x.mean(axis=(0, 1, 2))
    return 0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]


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
    """eq 的 gamma 是 out=in^(1/gamma)，所以亮化要 gamma>1：g = ln(y/255)/ln(target/255)"""
    if y <= 1:
        return 1.0
    return float(np.clip(np.log(y / 255.0) / np.log(target / 255.0), 0.55, 2.20))


def main():
    segs = []
    for label, fn, a, b, tgt in PLAN:
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            print("缺", p); sys.exit(1)
        b = min(b, dur(p) - 0.05)
        y, r = mean_y(p), audio_rms(p)
        g1 = gamma_for(y)
        base = f"eq=gamma={g1:.3f}:contrast={CONTRAST}:saturation=1.16,{SCURVE}"
        # 二次校正：把这条链子真跑一遍，量出残差后再补一个 gamma
        m2 = measure_chain(p, a, b, base)
        g2 = gamma_for(m2) if m2 > 1 else 1.0
        gain = float(np.clip(10 ** ((tgt - 20 * np.log10(r + 1e-9)) / 20.0), 0.02, 40.0))
        segs.append((label, p, a, b, b - a, base, g2, gain))
        print(f"  {label}: {b-a:.2f}s  Y={y:5.1f}→γ{g1:.2f}→实测{m2:4.1f}→γ{g2:.2f}  "
              f"{20*np.log10(r+1e-9):6.1f}→{tgt:6.1f}dB(×{gain:.2f})")

    inputs = []
    for _, p, *_ in segs:
        inputs += ["-i", p]

    fc = []
    for k, (label, p, a, b, d, base, g2, gain) in enumerate(segs):
        fc.append(f"[{k}:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale=1280:704,fps=24,setsar=1,"
                  f"{base},eq=gamma={g2:.3f}[v{k}]")
        fc.append(f"[{k}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,volume={gain:.3f}[a{k}]")

    vcat = "".join(f"[v{k}]" for k in range(len(segs)))
    acat = "".join(f"[a{k}]" for k in range(len(segs)))
    fc.append(f"{vcat}concat=n={len(segs)}:v=1:a=0[vout]")
    fc.append(f"{acat}concat=n={len(segs)}:v=0:a=1[amb0]")

    starts, t = [], 0.0
    for _, _, _, _, d, _, _, _ in segs:
        starts.append(t); t += d
    total = t
    hit = starts[4]                    # 第 5 段（水下穿出水面）= 冲击点
    jcut = max(0.0, hit - 0.55)
    duck0 = max(0.0, hit - 0.75)

    fc.append(f"[amb0]volume='if(between(t,{duck0:.3f},{hit:.3f}),0.22,1)':eval=frame[amb]")
    fc.append("sine=frequency=52:sample_rate=48000:duration=3.4,"
              "afade=t=in:st=0:d=0.60,afade=t=out:st=1.7:d=1.7,volume=0.95[lo]")
    fc.append("anoisesrc=color=brown:sample_rate=48000:duration=2.2:amplitude=0.62,"
              "bandpass=f=170:width_type=h:w=240,"
              "afade=t=in:st=0:d=0.50,afade=t=out:st=0.55:d=1.6,volume=1.8[mid]")
    fc.append("anoisesrc=color=white:sample_rate=48000:duration=0.12:amplitude=0.38,"
              "highpass=f=1200,afade=t=out:st=0.02:d=0.10,volume=1.2[hi]")
    fc.append("[mid][hi]amix=inputs=2:duration=longest:normalize=0[hi2]")
    fc.append(f"[hi2]adelay={int(hit*1000)}|{int(hit*1000)}[hid]")
    fc.append(f"[lo][hid]amix=inputs=2:duration=longest:normalize=0,"
              f"adelay={int(jcut*1000)}|{int(jcut*1000)}[hitmix]")
    fc.append("[amb][hitmix]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.92,"
              f"afade=t=in:st=0:d=0.8,afade=t=out:st={total-1.8:.3f}:d=1.8[aout]")

    out = os.path.join(OUT, "走蛟-运镜版.mp4")
    cmd = [FF, "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    print(f"总长 {total:.2f}s，冲击点 {hit:.2f}s，J-cut {jcut:.2f}s，渲染中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(1)
    print(f"✓ {out} {os.path.getsize(out)/1024/1024:.1f} MB {dur(out):.2f}s")


if __name__ == "__main__":
    main()
