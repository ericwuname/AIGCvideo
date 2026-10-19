#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V10 —— 把 V9 验证成功的"犀利眼"装到带角/须/鬃的整头上

V9 结论：
  ✅ `real9_eye_brow` 竖瞳成功：黑色竖针瞳 + 上睑压低的窄缝 + 眉骨阴影 → 真的凶
  ❌ 单拍眼球微距第三次失败（圆瞳 + 黄绿蜥蜴色）
  ⭐ 新规律：**离"整条龙"越远，越吸附鳄鱼**。只拍眼 → 龙的全套锚点缺席 → 只剩鳄鱼这个真实先验。

V10 打法：
  - 眼型沿用 V9 成功配方（黑色竖针瞳 + 窄眼缝 + 眉骨前压阴影）
  - 但一律放在"带角/长须/长鬃/下颌长髯"的整头上 → 给模型"龙"的锚点
  - 压掉 V9 的黄绿蜥蜴色，拉回墨黑 + 苔绿、低饱和
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

NEG = ("no round pupil, no circular pupil, no round eye, no wide open eye, no big eye, no doe eye, "
       "no puppy eye, no visible white of the eye, no eyelashes, no fur around the eye, "
       "no smiling mouth, no upturned mouth corner, no crocodile body, no alligator head, no snout only, "
       "no komodo dragon, no monitor lizard, no iguana, no dinosaur, no wyvern, no wings, no feathers, "
       "no headdress, no crown, no jewelry, no ornament, no glow, no neon, no bioluminescence, "
       "no yellow scales, no olive skin, no khaki, no light green, no emerald, no bright palette, "
       "no cartoon, no anime, no illustration, no concept art, no digital painting, "
       "no 3d render, no 3d model, no CG, no game asset, no plastic, no statue, "
       "no uniform surface, no clean surface, no text, no watermark")

# 眼型（V9 已验证）
EYE = ("THE EYES ARE THE FOCAL POINT AND THEY ARE HOSTILE. Each eyeball sits deep in a socket of heavy "
       "bone, the scaled lid drawn down over it so the opening is a narrow horizontal crescent. "
       "Inside, the pupil is a black vertical needle, not a circle, set in a cold pale amber iris with a "
       "darker ring at its rim. No white of the eye shows at all. The deep crease of the lid is hard and "
       "scaled. The brow ridges are heavy bone pushed forward, throwing both sockets into shadow. "
       "The gaze is level and unblinking — the flat appraising attention of an old predator.")

# 龙的身份锚：角、须、鬃、髯 —— 有它们在，模型才不会滑成鳄鱼
DRAGON = ("It is unmistakably an Eastern dragon, a Chinese dragon: two long branched antler-like horns "
          "sweep back from the skull, two long thin whiskers trail backwards from the upper jaw, "
          "a beard of coarse hair hangs beneath the lower jaw, a mane of long matted hair runs down the "
          "back of the neck. The skull is long and narrow and tapers forward with the snout tip turned "
          "slightly upward. The jaws are closed, the lips meet in one long line, no teeth are visible, "
          "and the corner of the mouth is pulled down hard.")

SKIN = ("THE HIDE IS ALMOST BLACK, not green: dark slate-black plates with only a faint moss-green "
        "patina in the seams, patchy and mottled, some plates sun-bleached grey, some stained rust-brown, "
        "some missing and showing raw hide, algae along one side only, old scars crossing the plates at "
        "random angles, some areas slick and wet and others dry with silt crusted in. Desaturated and cold.")

CAM = ("Photorealistic live-action film still from a feature film, a practical animatronic creature "
       "photographed on a wet set with practical lighting. Anamorphic lens wide open, extremely shallow "
       "depth of field, slight chromatic aberration at the frame edges, a few specks of dust and water on "
       "the lens, visible sensor noise in the shadows, natural film grain, cold teal-black grade.")

ITEMS = [
    ("AST-CREATURE-001_real10_head_34",
     f"Close three-quarter portrait of the head of a colossal water dragon filling the frame. "
     f"{DRAGON} {EYE} One cold hard practical light rakes from the upper left, the far side of the face "
     f"in shadow, murky black water out of focus behind. {SKIN} " + CAM),

    ("AST-CREATURE-001_real10_head_low",
     f"Close-up from below, looking up at the head of a colossal water dragon as it lowers toward the "
     f"lens. {DRAGON} {EYE} Rain falling between the lens and the face, a single cold light from above "
     f"and behind so the horns rim in silver. {SKIN} " + CAM),

    ("AST-CREATURE-001_real10_head_rain",
     f"Close profile-to-three-quarter of the head of a colossal water dragon in torrential rain at night. "
     f"{DRAGON} {EYE} A lightning flash behind it throws the head into near silhouette, "
     f"only the narrow slit of the near eye catching a spark of light. {SKIN} " + CAM),

    ("AST-CREATURE-001_real10_head_water",
     f"The head of a colossal water dragon held just above the surface of black water at night, "
     f"the waterline cutting across the lower jaw. {DRAGON} {EYE} "
     f"Rain dimpling the black water, one cold light from the side, the rest of the frame black. "
     f"{SKIN} " + CAM),
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
    print(f"=== V10 犀利整头：{len(ITEMS)} 张 ===")
    urls_file = os.path.join(OUT, "_real10_urls.json")
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
