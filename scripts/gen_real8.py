#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V8 —— 眼神：从"和善"改成"犀利/邪恶"

病根：V3 那版我照「龙九似」写了 eyes like a rabbit's, small and round。
      兔子眼 = 圆、软、无害 → 直接就是"和善"的来源。九似不能进 prompt，这又是一例。

"犀利"在生成模型里是具体的视觉信号，不是形容词。按重要性排序：
  1. 上睑压低，只露一条窄缝（反派的通用眼型，最关键）
  2. 眉骨前突把眼窝罩进阴影
  3. 竖瞳收缩成一根细线
  4. 外眼角上挑
  5. 眼周是裸露的湿皮，没有软毛过渡
  6. 眼裂窄、不露眼白

负面注意：不要写 no friendly / not gentle（抽象形容词无效，且可能反向召唤）。
          要写具体的解剖错误：round eyes, wide open eyes, doe eyes, visible white of the eye。
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

NEG = ("no round eyes, no wide open eyes, no big eyes, no doe eyes, no puppy eyes, "
       "no visible white of the eye, no soft eyelids, no eyelashes, no fur around the eyes, "
       "no crocodile, no alligator, no komodo dragon, no monitor lizard, no dinosaur, "
       "no exposed teeth, no fangs, no open mouth, no square snout, no wyvern, "
       "no wings, no feathers, no fur, no headdress, no crown, no jewelry, no ornament, "
       "no glow, no glowing, no bioluminescence, no neon, no emerald, no bright green, "
       "no cartoon, no anime, no illustration, no concept art, no digital painting, "
       "no 3d render, no 3d model, no CG, no game asset, no plastic, no statue, "
       "no uniform surface, no clean surface, no text, no watermark")

# 眼：本轮的全部重量
EYE = ("THE EYES SET THE EXPRESSION AND THEY ARE HOSTILE. "
       "The upper eyelid is drawn down low over the eye in a hooded squint, so that only a narrow "
       "horizontal slit of the eye is exposed and no white of the eye shows at all. "
       "The outer corner of the eye is angled upward. "
       "The pupil is contracted to a thin vertical slit, black, on a pale cold amber iris. "
       "The brow ridge is heavy bone pushed forward over the eye, throwing the socket into shadow. "
       "The skin immediately around the eye is bare wet hide with no fur and no lashes, "
       "creased and scaled like the rest of the head. "
       "The gaze is level, unblinking, appraising — the flat cold attention of a predator deciding, "
       "with no warmth in it at all.")

# 头：沿用 V3 已验证的解剖（去掉 rabbit eyes 那一句）
FACE = ("The head of an Eastern dragon, a Chinese dragon — not a lizard and not a crocodile. "
        "The skull is long and narrow and tapers forward, the snout tip turns slightly upward. "
        "The jaws are closed, the lips meet in one long line, no teeth are visible. "
        "Two long whiskers trail backwards from the upper jaw, a beard of coarse hair hangs beneath "
        "the lower jaw, a mane of long hair runs down the back of the neck, "
        "two branched antler-like horns sweep back from the skull. ")

SKIN = ("THE SURFACE IS NOT UNIFORM: dark slate-black hide with a moss-green patina, patchy and "
        "mottled, some plates sun-bleached pale, some stained rust-brown, some missing and showing raw "
        "grey hide, algae growing along one side only, old scars crossing the plates at random angles, "
        "some areas slick and wet and others dry with silt crusted in the seams. Nothing is symmetrical.")

CAM = ("Photorealistic live-action film still from a feature film, a practical animatronic creature "
       "photographed on a wet set with practical lighting. Anamorphic lens wide open, extremely shallow "
       "depth of field, slight chromatic aberration at the frame edges, a few specks of dust and water on "
       "the lens, visible sensor noise in the shadows, natural film grain, cold desaturated teal-black grade.")

ITEMS = [
    # 眼部微距：验证"犀利"能不能单独成立
    ("AST-CREATURE-001_real8_eye_macro",
     f"Extreme macro of a single eye, the eye fills seventy percent of the frame. {EYE} "
     f"One hard cold light from the left rakes across the brow and the wet hide, "
     f"the rest of the socket falling into black. {SKIN} " + CAM),

    # 3/4 头：定妆用，最能判"邪恶"
    ("AST-CREATURE-001_real8_face_34",
     f"Extreme close-up three-quarter portrait of the head of {FACE} filling the whole frame, "
     f"the head lowered slightly and turned toward the lens. {EYE} "
     f"One cold practical light rakes from the upper left, the far side of the face in shadow, "
     f"dark murky water out of focus behind. {SKIN} " + CAM),

    # 正面：两只眼一起压，最能出"凶"
    ("AST-CREATURE-001_real8_face_front",
     f"Front-on extreme close-up of the head of {FACE} filling the whole frame, the head lowered "
     f"toward the lens, both eyes fixed on the viewer. {EYE} "
     f"Torrential rain between the lens and the face, a single cold hard light from above. {SKIN} " + CAM),

    # 侧 profile：眼缝窄在侧面的表现
    ("AST-CREATURE-001_real8_face_side",
     f"Pure side profile of the head of {FACE} filling the whole frame, silhouetted against a faint "
     f"pale glow in the water. {EYE} "
     f"A hard rim light traces the horns, the whiskers and the beard; one pinpoint of light sits in "
     f"the narrow slit of the eye. {SKIN} " + CAM),

    # 半沉水中：只露眼，最强的"不祥"感
    ("AST-CREATURE-001_real8_eye_water",
     f"The head of {FACE} barely breaking the surface of black water at night, only the top of the "
     f"skull, the brow and the eyes above the waterline, everything else submerged. {EYE} "
     f"Rain dimpling the water around it, one cold light from the side. {SKIN} " + CAM),
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
    print(f"=== V8 眼神犀利化：{len(ITEMS)} 张 ===")
    urls_file = os.path.join(OUT, "_real8_urls.json")
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
