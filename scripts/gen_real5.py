#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V5 —— 「龙九似」配方
核心洞察：V3/V4 里我一直在"纠正"的牛耳、驼吻，其实是《尔雅翼》《本草纲目》记载的
正宗中国龙特征（九似：角似鹿/头似驼/眼似兔/项似蛇/腹似蜃/鳞似鱼/爪似鹰/掌似虎/耳似牛）。
而且负面词越压越冒头（反向召唤）。
因此 V5 不再压制，改用"九似"当解剖清单 —— 好处是给模型 9 个真实动物锚点，
模型画真实动物是强项，这正是把"写实"和"东方龙"焊在一起的桥。
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

# 负面只压"画风"和"西方龙"，不再压牛/驼/耳（那是九似的一部分）
NEG = ("no crocodile, no alligator, no komodo dragon, no monitor lizard, no dinosaur, no godzilla, "
       "no t-rex, no exposed teeth, no fangs, no open mouth, no square snout, no four legs, no wyvern, "
       "no wings, no feathers, no headdress, no crown, no jewelry, no ornament, "
       "no bright green, no emerald, no neon, no cartoon, no anime, no illustration, no concept art, "
       "no digital painting, no 3d render, no CG, no plastic, no text, no watermark")

CAM = ("Photorealistic live-action film still from a feature film, a real animatronic creature "
       "photographed on set with practical lighting. Anamorphic lens, extremely shallow depth of field, "
       "fine natural film grain, desaturated cold teal-black grade, "
       "every scale a wet physical plate with silt in the seams, physically accurate specular highlights.")

# 「龙九似」——原文配方
FACE = ("The head of a Chinese dragon, built to the classical canon of the Nine Resemblances "
        "(long jiu si), every part borrowed from a real animal so that it reads as a real creature: "
        "horns like a stag's, long and branched into tines; "
        "head like a camel's, long and high-crowned with a broad muzzle; "
        "eyes like a rabbit's, small and round and set deep, pale amber with a slit pupil; "
        "ears like a cow's, small and set low behind the jaw; "
        "neck like a serpent's, long and thick and sinuous; "
        "scales like a carp's, large overlapping wet plates; "
        "claws like an eagle's, curved and horned; "
        "paws like a tiger's, heavy and padded. "
        "Two long whiskers grow from the sides of the upper jaw and trail far back past the head. "
        "A beard of long coarse hair hangs beneath the lower jaw, and a mane of long flowing hair "
        "runs from behind the skull down the back of the neck. "
        "The jaws are closed, the lips meet in one long line, no teeth are visible. "
        "The hide is dark slate-black with a moss-green patina, wet and dull, crusted with silt.")

ITEMS = [
    ("AST-CREATURE-001_real5_face_a",
     f"{FACE} Extreme close-up three-quarter portrait filling the whole frame, the head turned toward the "
     f"lens, one cold practical light raking across the wet scales from the upper left, the rest of the face "
     f"in deep shadow, dark murky water out of focus behind. " + CAM),

    ("AST-CREATURE-001_real5_face_c",
     f"{FACE} Front-on close-up, the head lowered toward the lens, "
     f"one pale amber eye catching the light, water running off the antlers and the mane, "
     f"torrential rain between the lens and the face. " + CAM),

    ("AST-CREATURE-001_real5_body",
     f"A Chinese dragon built to the classical canon of the Nine Resemblances. "
     f"Its body is one long thick serpentine coil tapering into a finned tail, "
     f"scales like a carp's, a mane of long flowing hair down the spine, "
     f"horns like a stag's, head like a camel's, ears like a cow's, long whiskers, a long beard, "
     f"two short powerful forelimbs with eagle claws and tiger paws, and no hind legs at all, "
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
    print(f"=== 龙九似 V5：{len(items)} 张 ===")
    urls_file = os.path.join(OUT, "_real5_urls.json")
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
