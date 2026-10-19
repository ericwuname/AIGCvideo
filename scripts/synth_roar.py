#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
龙吟合成器
视频模型生成不出"惊天动地"的吼声（实测 p05 的音轨频谱重心 1207Hz，是雨噪声不是吼）。
所以自己合成：低频下滑基频 + 谐波堆叠 + 喉部粗糙度（AM）+ 气流噪声 + 软削波 + 卷积混响。

输出：assets/audio/dragon_roar.wav（48k / 立体声 / -3dBFS）
"""
import os, wave
import numpy as np

SR = 48000
DUR = 4.6
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio")
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(7)
N = int(SR * DUR)
t = np.arange(N) / SR


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


# ---------- 1. 基频轨迹：从高到低滑，尾段再抬一点（像一口气将尽又顶上去） ----------
f0 = np.zeros(N)
seg1 = t < 1.6
f0[seg1] = 74 - (74 - 43) * smoothstep(t[seg1] / 1.6)
seg2 = (t >= 1.6) & (t < 3.2)
f0[seg2] = 43 - 3.5 * smoothstep((t[seg2] - 1.6) / 1.6)
seg3 = t >= 3.2
f0[seg3] = 39.5 + 6.0 * smoothstep((t[seg3] - 3.2) / 1.4)

# 颤动（喉咙的抖）
vib = 1 + 0.016 * np.sin(2 * np.pi * 4.3 * t) + 0.006 * np.sin(2 * np.pi * 7.1 * t)
f0 = f0 * vib

# 相位积分
phase = 2 * np.pi * np.cumsum(f0) / SR

# ---------- 2. 谐波堆叠 ----------
harm = np.zeros(N)
for n in range(1, 15):
    amp = 1.0 / (n ** 0.85)
    if n == 2:
        amp *= 1.35          # 二次谐波加强 → 更"粗"
    if n == 3:
        amp *= 1.15
    harm += amp * np.sin(n * phase + rng.uniform(0, 2 * np.pi))
harm /= np.max(np.abs(harm)) + 1e-9

# ---------- 3. 喉部粗糙度：低频 AM + 随机抖动 ----------
rough = 1 - 0.45 * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 27 * t + 0.6 * np.sin(2 * np.pi * 1.7 * t))))
jitter = 1 + 0.10 * np.convolve(rng.normal(0, 1, N), np.ones(90) / 90, mode="same")
voice = harm * rough * jitter

# ---------- 4. 气流噪声（带通到 150~900Hz，跟着吼声走） ----------
noise = rng.normal(0, 1, N)
# 简易带通：低通 + 高通
def _lp(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y

def _hp(x, a):
    return x - _lp(x, a)

lp = _lp(noise, 0.055)          # ~900Hz 以下
band = _hp(_lp(noise, 0.012), 0.0025)   # 150~900Hz 之间
breath = band / (np.max(np.abs(band)) + 1e-9)

# 高频气流摩擦（1.5k~6k）
air = _hp(_hp(noise, 0.30), 0.10)
air = air / (np.max(np.abs(air)) + 1e-9)

# ---------- 5. 包络 ----------
env = np.ones(N)
att = int(0.07 * SR)
env[:att] = smoothstep(np.arange(att) / att)
rel_start = int(2.05 * SR)
env[rel_start:] = (1 - smoothstep((t[rel_start:] - t[rel_start]) / (DUR - t[rel_start]))) ** 1.6
# 中段两次"顶上去"的起伏
env *= 1 + 0.16 * np.sin(2 * np.pi * 0.55 * t) * (t > 1.0)

mix = (voice * 1.00 + breath * 0.42 + air * 0.10) * env

# ---------- 6. 软削波（饱和，产生"体量"） ----------
mix = np.tanh(mix * 2.6) / np.tanh(2.6)

# ---------- 7. 卷积混响 ----------
ir_len = int(2.6 * SR)
ir_t = np.arange(ir_len) / SR
ir = rng.normal(0, 1, ir_len) * np.exp(-ir_t / 0.55)
ir[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
ir /= np.max(np.abs(ir)) + 1e-9
ir = ir + np.concatenate([[0.55], np.zeros(ir_len - 1)])   # 直达声

n_fft = 1 << int(np.ceil(np.log2(N + ir_len)))
rev = np.fft.irfft(np.fft.rfft(mix, n_fft) * np.fft.rfft(ir, n_fft))[:N]
rev /= np.max(np.abs(rev)) + 1e-9
mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.75 + rev * 0.45

# ---------- 8. 轻微加宽（左右去相关） ----------
delay = int(0.011 * SR)
left = mix
right = np.concatenate([np.zeros(delay), mix[:-delay]]) * 0.92 + mix * 0.12

peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
left = left / peak * 0.707
right = right / peak * 0.707

stereo = np.stack([left, right], axis=1)
pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")

path = os.path.join(OUT, "dragon_roar.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())

print(f"✓ {path}  {os.path.getsize(path)/1024/1024:.2f} MB  {DUR}s")
print(f"  基频 {f0.min():.0f}~{f0.max():.0f} Hz   峰值 -3.0 dBFS")
