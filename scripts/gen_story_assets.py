#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""剧情小样补齐镜头：斗笠带血 / 水下黑影 / 化龙金光（3 张）"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "frames", "story")
os.makedirs(OUT, exist_ok=True)

CAM = ("Photorealistic live-action film still from a Chinese period feature film, shot on a real cinema "
       "camera with an anamorphic lens at night, practical lighting only, extremely shallow depth of field, "
       "natural film grain, desaturated cold teal-black grade")
NEG = ("no text, no watermark, no cartoon, no anime, no illustration, no 3d render, no CG, "
       "no bright saturated colors, no extra creatures, no western dragon, no wings")

ITEMS = [
    ("STORY-001_hat_blood",
     "A worn old bamboo hat floating face-up on the black flood water of a river at night, slowly turning, "
     "rain hammering the surface into a thousand small craters, a thin dark red stain at the rim of the hat "
     "slowly diluted and carried away by the rain, nothing else in frame, no people. " + CAM),
    ("STORY-002_shadow",
     "Underwater in murky black river water at night: an extremely long dark shadow gliding along the bottom, "
     "seen only as a silhouette, the body far too big to see in full, the form fading into the darkness at "
     "both ends, silt lifting off the riverbed as it passes, weak light from the surface far above. " + CAM),
    ("STORY-003_light",
     "The black surface of a river exploding upward at night as a column of cold golden light bursts out of "
     "the water into the storm sky, water thrown into a fine blinding mist, the light too bright to look at, "
     "torrential rain lit from below, nothing of any creature visible, only light and water. " + CAM),
]


def api_gen(prompt, size="2K", ratio="16:9"):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt, "size": size, "ratio": ratio,
            "extra_body": {"response_format": "url"}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "data" not in d:
                raise RuntimeError(str(d)[:200])
            return d["data"][0]["url"], time.time() - t0
        except Exception as e:
            last = e
            print(f"    重试{attempt+1}: {e}")
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"失败: {last}")


def main():
    urls_file = os.path.join(OUT, "_story_urls.json")
    urls = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}

    def work(item):
        fname, p = item
        if fname in urls:
            print(f"  {fname} 已存在"); return fname, urls[fname]
        try:
            u, dt = api_gen(p + "。" + NEG)
            with urllib.request.urlopen(u, timeout=180) as r, open(os.path.join(OUT, fname + ".png"), "wb") as f:
                f.write(r.read())
            print(f"  ✓ {fname}  {dt:.1f}s")
            return fname, u
        except Exception as e:
            print(f"  ✗ {fname}: {e}")
            return fname, None

    with ThreadPoolExecutor(max_workers=3) as ex:
        for f in as_completed([ex.submit(work, it) for it in ITEMS]):
            fn, u = f.result()
            if u:
                urls[fn] = u
                json.dump(urls, open(urls_file, "w"), ensure_ascii=False, indent=2)
    print(f"完成 {len(urls)}/{len(ITEMS)}")


if __name__ == "__main__":
    main()
