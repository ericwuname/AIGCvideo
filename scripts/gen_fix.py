#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修正批次（FIX）
用户四条：
  1. "怎么变成大鳄鱼了" → 鳄鱼感来自头部轮廓。新 prompt 强制 **头部完全在水下/画外，不出现任何头形**
  2. "水慢慢滴在鳞片上是啥情况" → 那一镜是物料空镜，删掉（不再生成）
  3. "雨与人的交互不明显，雨都看不到，衣服头发" → 新 prompt 写死：雨在逆光里成条、湿发贴额、
     衣服吸水变重贴身、水从斗笠边连续流下、雨在肩头炸开
  4. "没有惊天动地的龙吟，这些人转头看啥" → 龙吟已本地合成（39~75Hz），会放在**第一次有人转头之前**
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "fix")
os.makedirs(OUT, exist_ok=True)
PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "urls.json")


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def save(p, o):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


VIL = load(os.path.join(ROOT, "work", "frames", "vil", "_vil_urls.json"))
S2 = load(os.path.join(ROOT, "work", "frames", "shot2", "_s2_urls.json"))

# 雨的可读性（每镜带）
RAIN = ("Heavy rain is clearly VISIBLE: bright diagonal streaks crossing the darker background, "
        "drops bursting into small crowns wherever they strike, water pouring off every edge. ")
# 生物：只要没有头，就不可能读成鳄鱼
NOHEAD = ("CRITICAL: the head is completely submerged and OUT OF FRAME — no head, no skull, no snout, "
          "no jaw, no eyes, and no head shape is visible anywhere in the picture. Only a section of the "
          "back and the ridge above the water. ")
WATER = ("The water is NEVER still: the flood current keeps heaving and sliding, foam breaks and reforms, "
         "rain rings spread continuously. ")

SHOTS = {
    "F1": ("9", "黑暗巨物·无头",
           f"{NOHEAD}In almost total darkness over a flooded river at night, an enormous body is moving "
           f"just below the surface: only a long low ridge of bony spikes breaks the black water, trailing "
           f"a wake of disturbed foam behind it. Nothing about the animal is identifiable. "
           f"The camera tracks alongside it very low, just above the surface. {RAIN}{WATER}",
           "VIL-004_dark_mass", VIL),
    "F2": ("7", "压过来·无头",
           f"{NOHEAD}The body suddenly surges forward toward the camera — a wall of dark scaled flank and "
           f"a ridge of spikes driving through the water, shoving a great mass of white foam ahead of it. "
           f"A lightning flash behind it picks out the saw-tooth ridge for a split second, then darkness. "
           f"The camera is pushed back by the surge. {RAIN}{WATER}",
           "VIL-004_dark_mass", VIL),
    "F3": ("6", "门缝偷看·有雨",
           "Inside a dark cottage at night, half of a young villager's face fills the narrow gap of a "
           "half-open wooden door, one eye pressed to the opening looking out. His hair is soaked and "
           "plastered flat to his forehead, water runs down his temple and drips off his jaw; his collar "
           "is dark and heavy with water. Outside, rain is visible as bright streaks through the gap, and "
           "drops blow in and strike his cheek. His pupil contracts sharply. Camera almost still. "
           f"{RAIN}",
           "VIL-002_peek_doorgap", VIL),
    "F4": ("6", "渔夫回头·有雨",
           "A fisherman with a bamboo carrying pole stops in a flooded stone alley at night and slowly "
           "turns back over his shoulder. Torrential rain is VISIBLE as bright diagonal streaks against "
           "the lantern light; water pours in a continuous stream off the brim of his straw hat, his "
           "soaked clothes hang heavy and cling to his back, rain bursts into spray off his shoulders, "
           "and standing water at his feet is being hammered into a mass of small crowns. "
           f"{RAIN}{WATER}",
           "VIL-003_alley_fisherman", VIL),
}


def api(url, body=None, retries=5):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data,
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 20 * (i + 1); print(f"    429 等 {w}s"); time.sleep(w); continue
            raise
    raise RuntimeError("重试耗尽")


def submit(tag):
    secs, name, prompt, kf, src = SHOTS[tag]
    body = {"model": MODEL, "mode": "keyframe", "prompt": prompt + "。动作有重量和惯性，不要静止。",
            "first_frame": src[kf], "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    d = api(BASE + "/videos", body)
    vid = d.get("video_id") or d.get("id")
    if not vid:
        raise RuntimeError(str(d)[:300])
    return vid


def main():
    tags = sys.argv[1].split(",") if len(sys.argv) > 1 else list(SHOTS)
    pending = load(PENDING); done = load(DONE)
    todo = [t for t in tags if t not in pending and t not in done]

    if todo:
        print(f"提交 {len(todo)}…")
        def sub(tg):
            try:
                v = submit(tg); print(f"  {tg} → {v}"); return tg, v
            except Exception as e:
                print(f"  {tg} 异常: {e}"); return tg, None
        with ThreadPoolExecutor(max_workers=2) as ex:
            for f in as_completed([ex.submit(sub, t) for t in todo]):
                t, v = f.result()
                if v:
                    pending[t] = v; save(PENDING, pending)

    print(f"\n轮询 {len(pending)}（串行 3s）")
    t0 = time.time()
    while pending and time.time() - t0 < 1500:
        for tag in list(pending):
            try:
                d = api(f"{POLL}?video_id={pending[tag]}&model_name={MODEL}")
                st = d.get("status")
                if st == "completed":
                    url = d.get("url")
                    if url:
                        path = os.path.join(OUT, f"{tag}.mp4")
                        with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
                            f.write(r.read())
                        done[tag] = url; save(DONE, done)
                        pending.pop(tag); save(PENDING, pending)
                        print(f"  ✓ {tag} {os.path.getsize(path)/1024:.0f} KB")
                    else:
                        print(f"  ⚠ {tag} 无 url")
                elif st == "failed":
                    print(f"  ✗ {tag} 失败 {json.dumps(d, ensure_ascii=False)[:160]}")
                    pending.pop(tag); save(PENDING, pending)
            except Exception as e:
                print(f"  {tag} 异常: {e}")
            time.sleep(3)
        if pending:
            print(f"  …剩 {len(pending)}，{(time.time()-t0)/60:.1f} 分钟")

    print(f"\n完成 {len(done)}/{len(SHOTS)}")
    if pending:
        print("未完成:", list(pending))


if __name__ == "__main__":
    main()
