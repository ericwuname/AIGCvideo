#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阿月 · 定妆（AST-CHAR-001）
剧本设定：18 岁渔家女，粗麻短褐，湿发，手上是撑船磨出的茧。暴雨夜。
目的：先出一张可靠的定妆，之后所有分镜都从它派生（人物一致性只能靠这条链）。
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "char")
os.makedirs(OUT, exist_ok=True)

NEG = ("no makeup, no lipstick, no eyeliner, no false eyelashes, no modern clothing, no plastic look, "
       "no glamour, no studio lighting, no smiling, no cute, no anime, no illustration, "
       "no 3d render, no CG, no plastic skin, no airbrushed skin, no text, no watermark")

CAM = ("Photorealistic live-action film still from a Chinese period feature film, shot on a real cinema "
       "camera with an anamorphic lens in torrential rain at night, practical lighting only, "
       "extremely shallow depth of field, natural film grain, desaturated cold teal-black grade, "
       "skin texture with visible pores, wet strands of hair stuck to the face and neck, "
       "water beading on the skin, no beauty retouching whatsoever")

PERSON = ("A Yue, an eighteen-year-old Chinese fisher girl from a riverside village, "
          "wearing a coarse undyed hemp short jacket and trousers, both soaked through and clinging to her, "
          "her long black hair wet and plastered to her head and neck, "
          "no jewellery, no makeup, her face bare and weather-beaten, "
          "a strong jaw, thick dark eyebrows that have never been plucked, "
          "calloused working hands, mud on her forearms and shins, "
          "her expression closed and hard, holding something back")

ITEMS = [
    ("AST-CHAR-001_ayue_face_a",
     f"Close-up three-quarter portrait of {PERSON}. She is standing in the rain at night, "
     f"looking slightly off camera, rain running down her face and dripping from her chin, "
     f"one cold practical light from the side, the rest of her face in shadow. " + CAM),
    ("AST-CHAR-001_ayue_face_b",
     f"Front-on close-up of {PERSON}, the face filling the frame, staring straight into the lens, "
     f"rain hitting her face, eyes red-rimmed and swollen from crying but dry now. " + CAM),
    ("AST-CHAR-001_ayue_body_c",
     f"Full-length shot of {PERSON}. She is standing knee-deep in flood water on a dark riverbank at "
     f"night, holding an old worn bamboo hat in one hand, the water around her churning, "
     f"torrential rain, the village behind her dissolving into darkness and rain. " + CAM),
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


def download(url, path):
    with urllib.request.urlopen(url, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    print(f"=== 阿月定妆：{len(ITEMS)} 张 ===")
    urls_file = os.path.join(OUT, "_ayue_urls.json")
    urls = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}

    def work(item):
        fname, p = item
        if fname in urls:
            print(f"  {fname} 已存在，跳过"); return fname, urls[fname]
        try:
            u, dt = api_gen(p + "。" + NEG)
            download(u, os.path.join(OUT, fname + ".png"))
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
    print(f"\n完成 {len(urls)}/{len(ITEMS)}")


if __name__ == "__main__":
    main()
