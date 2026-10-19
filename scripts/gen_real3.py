#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V3 —— 专攻"写实的东方龙脸"
V2 结论：写实会滑向鳄鱼（真实爬行类），东方龙会滑向插画。
V3 解法：以 "Eastern dragon / Chinese dragon" 做概念锚，再把解剖逐条写死，
        最后才叠摄影语言；负面压死所有真实爬行类。
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

# 负面：重点压死"真实爬行类"（V2 就是全部滑到这里）
NEG = ("no crocodile, no alligator, no komodo dragon, no monitor lizard, no dinosaur, no godzilla, "
       "no t-rex, no iguana, no snake head, no exposed teeth, no fangs, no open mouth, "
       "no square snout, no boxy skull, no four legs, no long upright neck, no wyvern, "
       "no wings, no feathers, no fur, no headdress, no crown, no jewelry, no ornament, "
       "no bright green, no emerald, no neon, no cartoon, no anime, no illustration, no concept art, "
       "no digital painting, no 3d render, no CG, no plastic, no text, no watermark")

CAM = ("Photorealistic live-action film still from a feature film, a real animatronic and CGI creature "
       "photographed on set with practical lighting. Anamorphic lens, extremely shallow depth of field, "
       "fine natural film grain, desaturated cold teal-black grade, "
       "every scale a wet physical plate with silt in the seams, physically accurate specular highlights.")

# 解剖配方：每条都是"中国龙有、鳄鱼没有"的判据
FACE = ("The head of an Eastern dragon, a Chinese dragon — NOT a lizard and NOT a crocodile. "
        "Anatomy, precisely: "
        "the skull is long and narrow and tapers forward, the tip of the snout turns slightly upward, "
        "the nostrils sit at the very tip of the snout. "
        "The jaws are closed, the lips meet in one long straight line, no teeth are visible. "
        "Two long whiskers grow from the sides of the upper jaw, thin and sinuous, trailing backwards "
        "far past the head. "
        "A beard of long coarse hair hangs beneath the lower jaw. "
        "A mane of long flowing hair runs from behind the skull down the back of the neck. "
        "Two branched antler-like horns sweep backwards from the top of the skull, clearly forked, "
        "like a deer's antlers covered in hard skin. "
        "The brow ridges are heavy and protrude, the eyes are small and deep set, "
        "pale amber with a vertical slit pupil. "
        "The skin is armoured with dark slate-black scales carrying a moss-green patina, "
        "wet, dull, crusted with silt.")

ITEMS = [
    ("AST-CREATURE-001_real3_face_a",
     f"{FACE} Extreme close-up three-quarter portrait filling the whole frame, "
     f"the head turned toward the lens, one cold practical light raking across the wet scales from the "
     f"upper left, the rest of the face in deep shadow, dark murky water out of focus behind. " + CAM),

    ("AST-CREATURE-001_real3_face_b",
     f"{FACE} Pure side profile close-up filling the whole frame. "
     f"The head is silhouetted against a faint pale glow deep in the water, a hard rim light tracing the "
     f"forks of the horns, the line of the whiskers and the hang of the beard, "
     f"each scale reading as a separate wet plate. " + CAM),

    ("AST-CREATURE-001_real3_face_c",
     f"{FACE} Low angle close-up looking up at the head, the head lowered toward the lens, "
     f"one pale amber eye catching the light, water running off the horns and the mane, "
     f"torrential rain between the lens and the face. " + CAM),

    # 全身：只验证"无后腿 + 蛇身 + 两前肢"能不能同时成立
    ("AST-CREATURE-001_real3_body",
     f"An Eastern dragon, a Chinese dragon, not a lizard and not a crocodile. "
     f"Its body is one long thick serpentine coil that tapers into a finned tail, "
     f"armoured in dark slate-black scales with a moss-green patina, "
     f"a mane of long flowing hair running down the spine, "
     f"it has only two short powerful forelimbs held close to the chest, and no hind legs at all, "
     f"it lies coiled in three great loops on the silt of a flooded riverbed at night, "
     f"the head raised at the centre of the coil, two branched antler horns, long whiskers, "
     f"faint green light filtering down from the surface. " + CAM),
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
    only = sys.argv[1] if len(sys.argv) > 1 else None
    items = [it for it in ITEMS if not only or only in it[0]]
    print(f"=== 写实东方龙脸 V3：{len(items)} 张 ===")
    urls_file = os.path.join(OUT, "_real3_urls.json")
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
