#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实风格蛟龙资产（real_* 组）
锚点：assets/creature/2.jpeg（水下实拍风）
与旧 gen_assets.py 完全隔离，不带任何旧规则
"""
import json, os, sys, time, base64, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

# ===== 写实压舱词：杀掉插画/CG/设定图 =====
NEG = ("NOT an illustration, NOT concept art, NOT a digital painting, NOT anime, NOT cartoon, "
       "NOT a 3d render, NOT CG, NOT a video game screenshot, no plastic skin, no flat lighting, "
       "no white background, no design sheet, no turnaround sheet, no text, no watermark, no logo, "
       "no wings, no western dragon, no crocodile snout, no crocodile body, no visible hind legs, "
       "no fur, no feathers, not cute, not a pet, not a baby")

# 摄影语言：写实的核心是"摄影机在场"
CAM = ("photorealistic live-action cinematic film still, shot on ARRI Alexa with anamorphic lens, "
       "shallow depth of field, volumetric light, natural film grain, desaturated teal-black color grade, "
       "extremely detailed wet scale texture with algae film and silt, physically accurate specular highlights")

# 蛟的固定描述片段（避免每张写一遍）
BODY = ("a colossal serpentine water dragon, body a thick snake-like coil of wet black-green scales "
        "filmed with river algae and silt, a crown of swept-back bony spines above the brow, "
        "long barbels trailing from the jaw, milky pale eyes with a faint inner glow, "
        "a pair of small powerful forelimbs held close to the chest, no hind legs")


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


REF = data_uri(os.path.join(OUT, "2.jpeg"))

ITEMS = [
    # (文件名, prompt, 是否用 2.jpeg 做图生图参考)
    ("AST-CREATURE-001_real_fullbody",
     f"Full body side view of {BODY}, suspended in the murky dark water of a flooded riverbed at night, "
     f"the long body tapering into a finned tail, the head raised and turning toward the camera, "
     f"the whole silhouette readable against the dark water, suspended silt particles drifting, "
     f"weak shafts of light from the surface above, the bottom a waste of mud and broken stone. " + CAM, True),

    ("AST-CREATURE-001_real_free_coiled",
     f"{BODY}, coiled into a massive spiral resting on the silt of a flooded riverbed at night, "
     f"the head raised at the center of the coil, water thick with suspended particles, "
     f"faint green light filtering down from the surface and raking across the wet black scales, "
     f"mud and broken tombstones beneath it, the scale of the body dwarfing everything around. " + CAM, True),

    ("AST-CREATURE-001_real_chained",
     f"{BODY}, heavy rusted iron chains wrapped around the coils and staked deep into the riverbed, "
     f"the chains corroded and furred with algae, half-buried human skeletons and shattered tombstones "
     f"scattered in the silt around it, dark blood drifting in the water, "
     f"the head lowered and still, milky eyes open. " + CAM, True),

    ("AST-CREATURE-001_real_head",
     f"Extreme close-up of the head of {BODY}, three-quarter view, "
     f"dark wet scales crusted with a film of green algae and silt, every scale edge catching the light, "
     f"the crown of swept-back bony spines rising above the brow, long fanned barbels curving around the jaw, "
     f"the mouth closed, one dim shaft of light from above raking across the wet ridges of the face, "
     f"murky black water behind. " + CAM, True),

    ("AST-CREATURE-001_real_eye",
     f"Extreme macro of a single eye of {BODY}, filling the frame, "
     f"a pale jade iris crazed with fine cracks around a vertical slit pupil, "
     f"the lid made of wet armored scales crusted with silt, tiny water droplets clinging to the lashes, "
     f"a dim reflection of the surface light in the cornea, "
     f"everything behind it falling into black water. " + CAM, True),

    ("AST-CREATURE-001_real_ridge",
     f"The enormous scaled back of {BODY} breaking the surface of black flood water at night, "
     f"a long row of wet black-green plates cutting the water like a chain of stones, "
     f"water sheeting off the ridge in thin silver streams, only the back and the shoulders visible, "
     f"torrential rain hammering the surface, a distant lightning flash as the only light source. " + CAM, True),

    ("AST-CREATURE-001_real_claw",
     f"The forelimb and claw of {BODY} gripping a broken slab of wet stone underwater, "
     f"three long curved black talons sunk into the stone, "
     f"the scales of the wrist armored and coated in silt and algae, silt swirling up around the grip, "
     f"a single cold light raking from the side. " + CAM, True),

    ("AST-CREATURE-001_real_breakout",
     f"{BODY} bursting up out of black water at night, the head and shoulders exploding through the surface "
     f"in a wall of spray, mouth open, water pouring off the crown of spines, "
     f"torrential rain, a lightning bolt splitting the sky directly behind it and lighting the wet scales "
     f"from behind, the riverbank dark and empty below. " + CAM, False),

    ("AST-CREATURE-001_real_silhouette",
     f"Silhouette of {BODY} rearing up out of black flood water at night, "
     f"only the sinuous outline and the glint of wet scales readable, backlit by a lightning flash, "
     f"rain streaking through the frame, the head lifted high against the storm. " + CAM, False),
]


def api_gen(prompt, size="2K", ratio="16:9", ref=None):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt, "size": size, "ratio": ratio,
            "extra_body": {"response_format": "url"}}
    if ref:
        body["extra_body"]["image"] = [ref]
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
    only = sys.argv[1] if len(sys.argv) > 1 else None
    items = [it for it in ITEMS if not only or only in it[0]]
    print(f"=== 写实蛟龙：{len(items)} 张 ===")

    urls_file = os.path.join(OUT, "_real_urls.json")
    urls = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}

    def work(item):
        fname, p, use_ref = item
        if fname in urls:
            print(f"  {fname} 已存在，跳过"); return fname, urls[fname]
        full = p + "。" + NEG
        try:
            u, dt = api_gen(full, ref=REF if use_ref else None)
            download(u, os.path.join(OUT, fname + ".png"))
            print(f"  ✓ {fname}  {dt:.1f}s  ref={use_ref}")
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
