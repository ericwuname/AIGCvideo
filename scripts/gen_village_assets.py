#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
村庄群像底图（VIL 批次）
按用户给的导演思路：先想象整个村庄，每个人本来都在干自己的事，
突然听到龙吟/巨雷/有人喊"龙"，被惊动 → 各有各的反应。
主角是"正好在龙附近的人"，我们通过她的视角看到具体情况。

同时解决"龙没有威压感"：**不要让观众看清**。雷雨夜，黑暗为主，
闪电瞬间照亮局部，其余时间只有巨大的黑色轮廓。
"""
import json, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "frames", "vil")
os.makedirs(OUT, exist_ok=True)

CAM = ("Photorealistic live-action film still from a Chinese period feature film, shot on a real cinema "
       "camera with an anamorphic lens at night, practical lighting only, extremely shallow depth of field, "
       "natural film grain, cold desaturated grade, deep crushed blacks with hot specular highlights on wet "
       "surfaces, real rain")
NEG = ("。no text, no watermark, no cartoon, no anime, no illustration, no 3d render, no CG, "
       "no dragon visible in this frame, no creature, no bright saturated colors, no modern clothing")

ITEMS = [
    ("VIL-001_stove_oldwoman",
     "Interior of a poor Chinese riverside cottage at night. An old woman kneels beside a low clay stove, "
     "her hand stopped in mid-air holding a bundle of straw, her head just beginning to turn toward the "
     "door, her face lit warm orange from below by the fire while the rest of the room is black. "
     "The wooden door stands half open on the left, rain and darkness beyond it. " + CAM),

    ("VIL-002_peek_doorgap",
     "A young man hides behind a half-open wooden door in a dark cottage at night. Only half of his face "
     "is visible through the narrow gap, one eye pressed close to the opening, peering out. The interior "
     "is almost black; a thin sliver of cold blue light falls across his eye and cheekbone. " + CAM),

    ("VIL-003_alley_fisherman",
     "A narrow flooded stone alley in a Chinese riverside village at night in torrential rain. A fisherman "
     "with a bamboo carrying pole stands in the middle of the alley, stopped, twisted back over his "
     "shoulder to look behind him, his body still turned the way he was walking. Warm lantern light from "
     "a doorway, cold reflections in the standing water, rain streaking down. " + CAM),

    ("VIL-004_dark_mass",
     "Almost total darkness over a flooded river at night. An enormous dark mass is moving just below the "
     "surface, barely discernible — only a long black silhouette breaking the water, a faint cold rim of "
     "light along its back, and a line of disturbed water trailing it. Nothing of it is clearly visible. "
     "Rain hammering the black water, everything else lost in darkness. " + CAM),

    ("VIL-005_mucus_scales",
     "Extreme macro of wet dark reptile scales lit by one hard cold light from the side. Thick clear "
     "mucus stretches in thin strings between the plates and sags under its own weight, water sheeting "
     "over the surface in a continuous film, the seams crusted with silt, one scale chipped. The "
     "background is pure black. " + CAM),
]


def gen(prompt):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt + NEG, "size": "2K", "ratio": "16:9",
            "extra_body": {"response_format": "url"}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))["data"][0]["url"]
        except Exception as e:
            last = e; print("  重试", e); time.sleep(15 * (i + 1))
    raise RuntimeError(last)


def main():
    p = os.path.join(OUT, "_vil_urls.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    def work(it):
        name, prompt = it
        if name in m:
            print(f"  {name} 已存在"); return name, m[name]
        try:
            u = gen(prompt)
            with urllib.request.urlopen(u, timeout=180) as r, open(os.path.join(OUT, name + ".png"), "wb") as f:
                f.write(r.read())
            print(f"  ✓ {name}")
            return name, u
        except Exception as e:
            print(f"  ✗ {name}: {e}"); return name, None

    with ThreadPoolExecutor(max_workers=3) as ex:
        for f in as_completed([ex.submit(work, it) for it in ITEMS]):
            n, u = f.result()
            if u:
                m[n] = u; json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("完成", len(m))


if __name__ == "__main__":
    main()
