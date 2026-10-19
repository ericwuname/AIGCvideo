#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V4 —— 基于 V3 成功的解剖配方，只修两个残留问题：
  1. 长了肉质大耳朵（马/精灵耳）→ 压成藏在颌后的小孔
  2. 吻部偏牛（宽扁）→ 收成窄长、鼻端上翻
其余配方与 V3 完全一致（V3 已验证可同时成立"写实 + 东方龙"）
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

NEG = ("no crocodile, no alligator, no komodo dragon, no monitor lizard, no dinosaur, no godzilla, "
       "no t-rex, no iguana, no snake head, no exposed teeth, no fangs, no open mouth, "
       "no square snout, no boxy skull, no cow muzzle, no bovine face, no horse face, no bull, "
       "no big fleshy ear, no external ear, no elf ear, no pointed ear, no rabbit ear, "
       "no four legs, no long upright neck, no wyvern, no wings, no feathers, no fur, "
       "no headdress, no crown, no jewelry, no ornament, no bright green, no emerald, no neon, "
       "no cartoon, no anime, no illustration, no concept art, no digital painting, no 3d render, "
       "no CG, no plastic, no text, no watermark")

CAM = ("Photorealistic live-action film still from a feature film, a real animatronic creature "
       "photographed on set with practical lighting. Anamorphic lens, extremely shallow depth of field, "
       "fine natural film grain, desaturated cold teal-black grade, "
       "every scale a wet physical plate with silt in the seams, physically accurate specular highlights.")

FACE = ("The head of an Eastern dragon, a Chinese dragon — NOT a lizard and NOT a crocodile. "
        "Anatomy, precisely: "
        "the skull is long and narrow and tapers forward, the muzzle is slender and does NOT broaden toward "
        "the front, the tip of the snout turns upward and the nostrils flare at the very tip. "
        "There is no external ear: only a small slit low behind the jaw. "
        "The jaws are closed, the lips meet in one long straight line, no teeth are visible. "
        "Two long whiskers grow from the sides of the upper jaw, thin and sinuous, trailing backwards "
        "far past the head. "
        "A beard of long coarse hair hangs beneath the lower jaw. "
        "A mane of long flowing hair runs from behind the skull down the back of the neck. "
        "Two long branched antlers, forked like a stag's and covered in hard skin, sweep backwards "
        "from the top of the skull, clearly splitting into tines. "
        "The brow ridges are heavy and protrude, the eyes are small and deep set, "
        "pale amber with a vertical slit pupil. "
        "The skin is armoured with dark slate-black scales carrying a moss-green patina, "
        "wet, dull, crusted with silt.")

ITEMS = [
    ("AST-CREATURE-001_real4_face_a",
     f"{FACE} Extreme close-up three-quarter portrait filling the whole frame, the head turned toward the "
     f"lens, one cold practical light raking across the wet scales from the upper left, the rest of the face "
     f"in deep shadow, dark murky water out of focus behind. " + CAM),

    ("AST-CREATURE-001_real4_face_c",
     f"{FACE} Low angle close-up looking up at the head, the head lowered toward the lens, "
     f"one pale amber eye catching the light, water running off the antlers and the mane, "
     f"torrential rain between the lens and the face. " + CAM),

    ("AST-CREATURE-001_real4_body",
     f"An Eastern dragon, a Chinese dragon, not a lizard and not a crocodile. "
     f"Its body is one long thick serpentine coil tapering into a finned tail, "
     f"armoured in dark slate-black scales with a moss-green patina, "
     f"a mane of long flowing hair running down the spine, "
     f"it has only two short powerful forelimbs held close to the chest and no hind legs at all, "
     f"no external ears, two long branched antlers, long whiskers, a long beard, "
     f"it lies coiled in three great loops on the silt of a flooded riverbed at night, "
     f"the head raised at the centre of the coil, faint green light filtering down from the surface. " + CAM),
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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    items = ITEMS
    print(f"=== 写实东方龙 V4（修耳/修吻）：{len(items)} 张 ===")
    urls_file = os.path.join(OUT, "_real4_urls.json")
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
        for f in as_completed([ex.submit(work, it) for it in items]):
            fn, u = f.result()
            if u:
                urls[fn] = u
                json.dump(urls, open(urls_file, "w"), ensure_ascii=False, indent=2)
    print(f"\n完成 {len(urls)}/{len(items)}")


if __name__ == "__main__":
    main()
