#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V7 —— 结构沿用 3.png（已由 V6 T2I 验证可行），本轮专攻「材质写实度」

V6 结论：
  ✅ T2I 解决结构：四足齐全、S 形连续可追踪、背棘连续、尾鳍成型
  ❌ I2I 依旧不可用：保结构的同时也保了画风，还带进 3.png 的绿色荧光污染
  ❌ 材质像 3D 渲染 / 塑料模型，不像实拍真动物

V7 解法：CG 感的头号病根是「太均匀」。真实动物没有一块皮肤是均匀的。
  → 加入不均匀性：斑驳、疤痕、缺鳞、只长一侧的藻、干湿不均、水痕
  → 加入摄影机缺陷：镜头脏点、轻微色差、焦外不完美
  → 结构描述压到最短（避免模型进入"建模思维"），材质描述放到最后压轴
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

NEG = ("no coiled pile, no overlapping coils, no knot, no two bodies, no extra limbs, no missing legs, "
       "no crocodile, no alligator, no komodo dragon, no monitor lizard, no dinosaur, no godzilla, "
       "no t-rex, no exposed teeth, no fangs, no open mouth, no square snout, no wyvern, "
       "no wings, no feathers, no fur, no headdress, no crown, no jewelry, no ornament, "
       "no glow, no glowing, no glowing green, no bioluminescence, no neon, no emerald, no bright green, "
       "no cartoon, no anime, no illustration, no concept art, no digital painting, "
       "no 3d render, no 3d model, no CG, no game asset, no plastic, no vinyl toy, no statue, "
       "no uniform surface, no clean surface, no perfectly even scales, no text, no watermark")

# 结构：只写必要项，简短（长结构描述会把模型拉去建模）
STRUCT = ("An Eastern dragon, a Chinese dragon — not a lizard and not a crocodile. "
          "One single continuous serpentine body in a readable S-curve, the whole animal visible, "
          "the body never crossing over itself. Four short heavy legs, one pair behind the neck and "
          "one pair two thirds along, each ending in four curved claws. A continuous row of bony spikes "
          "from the skull along the whole spine to the tail. The tail tapers to about a third of the "
          "total length and ends in a small flattened fin. Two branched antler horns, two long whiskers, "
          "a beard under the jaw and a mane down the neck. Jaws closed, no teeth visible.")

# 材质：写实的真正重量都压在这里（放最后）
SKIN = ("THE SURFACE IS NOT UNIFORM — this is what makes it read as a real animal rather than a model: "
        "the hide is dark slate-black with a moss-green patina, but the tone is patchy and mottled, "
        "some plates sun-bleached pale, some stained rust-brown, some missing entirely leaving raw grey "
        "hide underneath, algae growing thickly along one flank and not the other, old scars and healed "
        "gouges crossing the plates at random angles. Some areas of the skin are slick and wet with water "
        "running off them, other areas are dull and dry with dried silt crusted in the seams between "
        "scales. Individual scales vary in size and shape. The belly plates are a dull dark red, "
        "scuffed and scratched. The mane and beard are matted and stuck together in wet rats' tails, "
        "not brushed. Nothing about the creature is symmetrical or clean.")

CAM = ("Photorealistic live-action film still from a feature film, a practical animatronic creature "
       "photographed on a wet set with real water and practical lighting. "
       "Anamorphic lens wide open, extremely shallow depth of field with imperfect out-of-focus falloff, "
       "slight chromatic aberration at the frame edges, a few specks of dust and water on the lens, "
       "visible sensor noise in the shadows, natural film grain, desaturated cold teal-black grade.")

ITEMS = [
    ("AST-CREATURE-001_real7_water_side",
     f"{STRUCT} It is swimming just under the surface of a dark river at night, seen from the side at "
     f"eye level, the whole body readable in profile, weak light from the surface above. {SKIN} " + CAM),

    ("AST-CREATURE-001_real7_bank",
     f"{STRUCT} It is lying half out of the water on a wet stone bank at night, the front legs braced on "
     f"the stone and the body curving back into the river, the head lifted and turned slightly toward the "
     f"lens, torrential rain, the only light a cold source from the left. {SKIN} " + CAM),

    ("AST-CREATURE-001_real7_rear",
     f"{STRUCT} It is rearing up out of black water in torrential rain at night, the front of the body "
     f"clear of the surface, water pouring off the spine, the head lifted, a lightning flash behind it. "
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
    print(f"=== V7 材质写实：{len(ITEMS)} 张 ===")
    urls_file = os.path.join(OUT, "_real7_urls.json")
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
