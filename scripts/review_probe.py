#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评审验证脚本 / review_probe.py  (守门人工具)

用途：不信任任何报告数字，直接从成片实测。
  1. 按镜头区间抽帧，实测 亮度 / R-B / 饱和度，对比 AST-STYLE-001 规范
  2. 检测相邻镜头之间的跨组跳变
  3. 实测音频能量包络，定位语音段，检查字幕与语音是否对齐
  4. 输出 PASS / FAIL 清单（门禁用）

用法：
  python scripts/review_probe.py release/走蛟-ep01-v15.mp4
"""
import os, sys, subprocess, json
import numpy as np
from PIL import Image

FF = r"C:/Users/87465/.workbuddy/binaries/python/envs/aitv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"

# ---- 与 make_film_v15.py 保持一致的时间轴 ----
INTRO = 3.5
DUR = {1:6.58, 2:7.30, 3:7.30, 4:7.30, 5:8.00, 6:7.30, 7:7.30,
       8:8.00, 9:7.30, 10:8.00, 11:8.00, 12:8.00}
XF = 0.30

# ---- AST-STYLE-001 规范（来自 assets/REGISTRY.md）----
SPEC = {
    "A": dict(shots=[1,2,3,4,7,8,10], Y=(55,70),  RB=(-30,-20), SAT=(45,55)),
    "B": dict(shots=[5,6,9],          Y=(35,48),  RB=(-25,-15), SAT=(45,55)),
    "C": dict(shots=[11],             Y=(70,85),  RB=(-10,0),   SAT=(45,55)),
    "D": dict(shots=[12],             Y=(95,115), RB=(0,10),    SAT=(30,40)),
}
# 组内相邻限制
MAX_DY, MAX_DRB = 12, 10


def starts_map():
    s, t = {}, INTRO
    order = sorted(DUR)
    for idx, sid in enumerate(order):
        s[sid] = t
        t += DUR[sid] - XF
    return s, t


def group_of(sid):
    for g, d in SPEC.items():
        if sid in d["shots"]:
            return g
    return "?"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-1500:])
    return r


def probe_stream(path):
    r = subprocess.run([FF, "-i", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = {"video": "", "audio": "", "duration": ""}
    for line in (r.stderr or "").splitlines():
        if "Duration:" in line:
            out["duration"] = line.strip()
        elif "Video:" in line:
            out["video"] = line.strip()
        elif "Audio:" in line:
            out["audio"] = line.strip()
    return out


def grab(path, t, tmp):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
         "-i", path, "-frames:v", "1", tmp])
    return np.asarray(Image.open(tmp).convert("RGB")).astype(np.float32)


def metrics(a):
    Y = (0.299*a[:,:,0] + 0.587*a[:,:,1] + 0.114*a[:,:,2]).mean()
    rb = a[:,:,0].mean() - a[:,:,2].mean()
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = ((mx-mn)/(mx+1e-6)).mean()*100
    return Y, rb, sat


def in_range(v, lo, hi):
    return lo <= v <= hi


def audio_envelope(path, tmpwav):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmpwav])
    raw = open(tmpwav, "rb").read()
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    win = 1600  # 100ms
    n = len(x) // win
    env = np.sqrt((x[:n*win].reshape(n, win) ** 2).mean(axis=1))
    return env, 0.1


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/review_probe.py <成片路径>")
        sys.exit(2)
    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"找不到文件: {src}"); sys.exit(2)

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WORK = os.path.join(ROOT, "work", "review")
    os.makedirs(WORK, exist_ok=True)
    tmp = os.path.join(WORK, "_f.png")

    print("=" * 74)
    print(f"评审实测对象: {os.path.basename(src)}")
    print("=" * 74)

    st = probe_stream(src)
    print("\n[容器/流]")
    print(" ", st["duration"])
    print(" ", st["video"])
    print(" ", st["audio"])
    if "yuv444p" in st["video"]:
        print("  🔴 FAIL 色度采样为 yuv444p —— 平台/播放器兼容性高风险")
    elif "yuv420p" in st["video"]:
        print("  🟢 PASS 色度采样 yuv420p")
    if "1280x704" in st["video"]:
        print("  🟡 WARN 画幅 1280x704 = 20:11(1.818)，非标准 16:9(1.778)")

    s, total = starts_map()
    print(f"\n[时间轴] 片头 {INTRO}s + 12 镜，脚本推算总长 {total:.2f}s")

    print("\n" + "=" * 74)
    print("[色彩实测] 每镜取中点帧，对比 AST-STYLE-001")
    print("=" * 74)
    print(f"{'镜':>3} {'组':>2} {'起点':>7} {'亮度':>7} {'规范':>11} "
          f"{'R-B':>7} {'规范':>11} {'饱和%':>7} {'规范':>11}  判定")
    res = {}
    for sid in sorted(DUR):
        g = group_of(sid)
        sp = SPEC[g]
        t = s[sid] + DUR[sid] / 2.0
        a = grab(src, t, tmp)
        Y, rb, sat = metrics(a)
        res[sid] = (g, Y, rb, sat)
        okY = in_range(Y, *sp["Y"]); okRB = in_range(rb, *sp["RB"])
        okS = in_range(sat, *sp["SAT"])
        flag = "✓" if (okY and okRB and okS) else "✗"
        print(f"{sid:>3} {g:>2} {s[sid]:>7.2f} {Y:>7.1f} "
              f"{str(sp['Y']):>11} {rb:>7.1f} {str(sp['RB']):>11} "
              f"{sat:>7.1f} {str(sp['SAT']):>11}  {flag}"
              + ("" if okY else " 亮度超界") + ("" if okRB else " 色温超界")
              + ("" if okS else " 饱和超界"))

    print("\n[相邻镜跳变] 规范: 同组内 亮度差<=12, 色温差<=10")
    order = sorted(DUR)
    hard = 0
    for a_i, b_i in zip(order, order[1:]):
        ga, gb = res[a_i][0], res[b_i][0]
        dY = abs(res[b_i][1] - res[a_i][1])
        dRB = abs(res[b_i][2] - res[a_i][2])
        same = ga == gb
        lim = (MAX_DY, MAX_DRB) if same else (999, 999)
        bad = dY > lim[0] or dRB > lim[1]
        if bad: hard += 1
        mark = ("🔴" if bad else ("·" if not same else "🟢"))
        print(f"  {mark} 镜{a_i:>2}({ga}) → 镜{b_i:>2}({gb}): "
              f"Δ亮度={dY:>5.1f} Δ色温={dRB:>5.1f}"
              + ("  [跨组，需转场缓冲]" if not same else ""))
    print(f"  同组超标跳变: {hard} 处")

    print("\n" + "=" * 74)
    print("[音频实测] 100ms 窗口 RMS 包络")
    print("=" * 74)
    wav = os.path.join(WORK, "_a.wav")
    env, step = audio_envelope(src, wav)
    print(f"  总窗口 {len(env)} ({len(env)*step:.1f}s)  "
          f"峰值 {env.max():.4f} 中位 {np.median(env):.4f} 最小 {env.min():.4f}")
    head = env[:int(INTRO/step)]
    print(f"  前 {INTRO}s(片头) 峰值 RMS = {head.max():.6f}"
          + ("  🔴 完全静音" if head.max() < 1e-4 else ""))
    # 低能量段（可能是"静默"或"音频凹陷"）
    thr = max(np.median(env) * 0.15, 1e-4)
    quiet = [i*step for i, v in enumerate(env) if v < thr]
    if quiet:
        # 归并连续段
        seg, cs = [], [quiet[0]]
        for t in quiet[1:]:
            if t - cs[-1] <= step * 1.5: cs.append(t)
            else: seg.append((cs[0], cs[-1])); cs = [t]
        seg.append((cs[0], cs[-1]))
        print(f"  低于中位15%的低能量段 {len(seg)} 段（>0.5s 的列出）:")
        for a0, b0 in seg:
            if b0 - a0 > 0.5:
                print(f"     {a0:6.1f}s – {b0:6.1f}s  ({b0-a0:.1f}s)")
    print("\n[对白区间实测] 与脚本 SPEECH 常量对照")
    SPEECH = {8: (1.78, 2.94), 10: (3.58, 3.90)}
    for sid, (a0, b0) in SPEECH.items():
        t0 = s[sid] + a0; t1 = s[sid] + b0
        i0, i1 = int(t0/step), int(t1/step)
        seg_e = env[i0:i1]
        before = env[max(0, i0-int(1.0/step)):i0]
        print(f"  镜{sid:>2} 声称语音 {a0:.2f}-{b0:.2f}s (绝对 {t0:.2f}-{t1:.2f}s): "
              f"段内峰值 {seg_e.max() if len(seg_e) else 0:.4f} / "
              f"前1s基线 {before.max() if len(before) else 0:.4f}")

    print("\n完成。以上数字全部来自成片实测，非报告引用。")


if __name__ == "__main__":
    main()
