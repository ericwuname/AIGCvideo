#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V9 —— 眼部二轮：把"犀利"焊死

V8 结论：
  ✅ 侧影/水面露出头部时，眼裂窄 + 阴影 → 确实凶了
  ❌ 眼部微距失败：出现圆眼 + 圆黑瞳（模型对 dragon eye 的默认认知就是琥珀色圆瞳）
  ❌ 整脸容易漂向狼/犀牛

V9 打法：
  1. 不用 abstract 的 "vertical slit pupil"，改成物理描述：
     "the pupil is squeezed into a black vertical needle"（针，不是裂）
     "the eyeball is almost entirely covered by the lid, only a thin crescent of iris shows"
  2. 引入真实动物锚（只锚"眼"这一个部件，不锚整体）：crocodile / serpent 的眼睛结构
  3. 补上此前漏掉的"凶"信号：嘴角下垂（downturned mouth corner）+ 上唇绷紧
  4. 避开整脸漂移：本轮只拍眼与眼周，不拍整体头骨
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes.ai/v1"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

NEG = ("no round pupil, no circular pupil, no round eye, no wide open eye, no big eye, no doe eye, "
       "no puppy eye, no visible white of the eye, no soft eyelid, no eyelashes, no fur around the eye, "
       "no smiling mouth, no upturned mouth corner, no crocodile body, no alligator body, "
       "no komodo dragon, no monitor lizard, no dinosaur, no wyvern, no wings, no feathers, no fur, "
       "no headdress, no crown, no jewelry, no ornament, no glow, no neon, no emerald, no bright green, "
       "no cartoon, no anime, no illustration, no concept art, no digital painting, "
       "no 3d render, no 3d model, no CG, no game asset, no plastic, no statue, "
       "no uniform surface, no clean surface, no text, no watermark")

# 眼部结构：用物理描述 + 真实动物锚，不用抽象形容词
EYE = ("THE EYE IS THAT OF A CROCODILE OR A VIPER, NOT OF A MAMMAL. "
       "The eyeball sits deep in a socket of heavy bone. The scaled lid is three quarters closed over it, "
       "so the visible opening is a narrow horizontal crescent, and the eyeball is almost entirely hidden "
       "under the lid. The pupil inside is squeezed into a black vertical needle, not a circle. "
       "The iris around the needle is a cold pale amber, hard and glassy, with a ring of darker pigment "
       "at its outer edge. No white of the eye is visible anywhere. "
       "The lid itself is armoured with small wet scales, and the crease of the lid is deep and hard. "
       "The gaze is level and unblinking, the flat appraising attention of an old predator.")

MOUTH = ("The corner of the mouth is pulled down hard, the lip line long and level and slightly "
         "downturned, the upper lip drawn tight so the line of the jaw reads as clenched.")

SKIN = ("The hide around it is patchy: dark slate-black with a moss-green patina, some plates "
        "sun-bleached pale, some stained rust-brown, some missing and showing raw grey hide, "
        "algae along one side only, old scars crossing the plates at random angles, "
        "some areas slick and wet and others dry with silt crusted in the seams.")

CAM = ("Photorealistic live-action film still from a feature film, a practical animatronic creature "
       "photographed on a wet set with practical lighting. Anamorphic lens wide open, extremely shallow "
       "depth of field, slight chromatic aberration at the frame edges, a few specks of dust and water "
       "on the lens, visible sensor noise in the shadows, natural film grain, cold teal-black grade.")

ITEMS = [
    # 1 纯眼部微距（最难，V8 就败在这）
    ("AST-CREATURE-001_real9_eye_macro",
     f"Extreme macro of a single eye of a Chinese water dragon, the eye fills seventy percent of the "
     f"frame. {EYE} {MOUTH} One hard cold light from the left rakes across the brow, "
     f"the rest of the socket falling into black. {SKIN} " + CAM),

    # 2 眼 + 眉弓 + 上颌，带嘴角，验证"凶"能否组合成立
    ("AST-CREATURE-001_real9_eye_brow",
     f"Tight crop on one eye, the brow ridge above it and the corner of the mouth below it. {EYE} "
     f"{MOUTH} The heavy brow is pushed forward and throws the eye into shadow; a thin cold light "
     f"catches only the edge of the lid. {SKIN} " + CAM),

    # 3 双眼 + 鼻梁，正面，压迫感
    ("AST-CREATURE-001_real9_eyes_both",
     f"Tight front-on crop of both eyes and the bridge of the snout between them, nothing else in "
     f"frame. {EYE} {MOUTH} Torrential rain between the lens and the face, one hard cold light "
     f"from above. {SKIN} " + CAM),

    # 4 水面露出一双眼（不拍头骨，避开漂移）
    ("AST-CREATURE-001_real9_eyes_water",
     f"Only the top of a skull and a pair of eyes break the surface of black water at night, "
     f"everything else submerged and invisible. {EYE} "
     f"Rain dimpling the black water around it, one cold light from the side, "
     f"the rest of the frame pure black water. {SKIN} " + CAM),
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
    print(f"=== V9 眼部二轮：{len(ITEMS)} 张 ===")
    urls_file = os.path.join(OUT, "_real9_urls.json")
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

    with ThreadPoolExecutor(max_workers=2) as ex:
        for f in as_completed([ex.submit(work, it) for it in ITEMS]):
            fn, u = f.result()
            if u:
                urls[fn] = u
                json.dump(urls, open(urls_file, "w"), ensure_ascii=False, indent=2)
    print(f"\n完成 {len(urls)}/{len(ITEMS)}")


if __name__ == "__main__":
    main()
