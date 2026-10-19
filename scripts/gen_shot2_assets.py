#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补齐"高处俯瞰"与"岸边人群"两张底图（用于 crane down 与 truck 横移）"""
import json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "frames", "shot2")
os.makedirs(OUT, exist_ok=True)

CAM = ("Photorealistic live-action film still from a Chinese period feature film, shot on a real cinema "
       "camera with an anamorphic lens at night in torrential rain, practical lighting only, "
       "extremely shallow depth of field, natural film grain, desaturated cold teal-black grade, "
       "deep blacks with hot specular highlights on the wet surfaces")
NEG = ("。no text, no watermark, no cartoon, no anime, no illustration, no 3d render, no CG, "
       "no dragon visible, no creature, no monster, no bright saturated colors")

ITEMS = [
    ("S2-001_highangle_bend",
     "HIGH ANGLE, looking down from above a Chinese riverside village at night in torrential rain. "
     "The frame is dominated by a wide black river that has burst its banks, the flood water heaving and "
     "streaked with foam. On the left bank, the roofs of low tiled houses, a few warm lantern lights, "
     "a stone quay, and three or four small human figures standing at the water's edge looking out, tiny "
     "in the frame. Rain visible as streaks. The whole scene cold and very dark. " + CAM),
    ("S2-002_villagers_row",
     "A row of three different villagers standing on a flooded stone quay at night in torrential rain, "
     "seen from the side, all facing the same direction out across the black water: an old fisherman in a "
     "straw cape with a rope over his shoulder, a young woman holding a small child wrapped in a cloth, "
     "and an old man with a stick. Each stands still, separate from the others, lit only by a lantern "
     "behind them. Cold, wet, very dark, the river behind them heaving. " + CAM),
]


def api_gen(prompt, size="2K", ratio="16:9"):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt + NEG, "size": size, "ratio": ratio,
            "extra_body": {"response_format": "url"}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    import time
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d["data"][0]["url"]
        except Exception as e:
            last = e; print("  重试", e); time.sleep(15 * (i + 1))
    raise RuntimeError(last)


def main():
    p = os.path.join(OUT, "_s2_urls.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    def work(it):
        name, prompt = it
        if name in m:
            print(f"  {name} 已存在"); return name, m[name]
        try:
            u = api_gen(prompt)
            with urllib.request.urlopen(u, timeout=180) as r, open(os.path.join(OUT, name + ".png"), "wb") as f:
                f.write(r.read())
            print(f"  ✓ {name}")
            return name, u
        except Exception as e:
            print(f"  ✗ {name}: {e}"); return name, None

    with ThreadPoolExecutor(max_workers=2) as ex:
        for f in as_completed([ex.submit(work, it) for it in ITEMS]):
            n, u = f.result()
            if u:
                m[n] = u; json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("完成", len(m))


if __name__ == "__main__":
    main()
