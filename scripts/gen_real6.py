#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V6 —— 按用户给的 3.png 修正「身体结构」
用户原话：real3_body 身体比例不对，不知道尾巴是从哪里出来的。

3.png 的结构规范：
  1. 一条 S 形连续长躯，头→颈→躯干→尾可以一眼追踪，身体不自我穿插
  2. 四条短腿（前对在颈后，后对在体后段）—— 推翻此前"无后腿"的错误设定
  3. 背脊棘刺连续不断，从头一直排到尾巴
  4. 尾巴约占全长 1/3，逐级收细，末端收成一片小鳍
  5. 躯干粗细基本均匀，不是胸腹鼓胀、颈部细长

画风仍沿用 V3 的写实电影剧照配方。
本轮同时测两种打法：
  A. 纯 T2I（结构描述写死）
  B. I2I（以 3.png 为结构模板 → 改成写实渲染）—— 只保结构，不保画风
"""
import json, os, sys, time, base64, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


REF3 = data_uri(os.path.join(OUT, "3.png"))

# 负面：本轮重点压「一盘绳圈 / 结构看不清」，不再压四条腿
NEG = ("no coiled pile, no overlapping coils, no knot, no tangle, no two bodies, no extra limbs, "
       "no missing legs, no crocodile, no alligator, no komodo dragon, no monitor lizard, "
       "no dinosaur, no godzilla, no t-rex, no exposed teeth, no fangs, no open mouth, "
       "no square snout, no boxy skull, no wyvern, no wings, no feathers, no fur, "
       "no headdress, no crown, no jewelry, no ornament, "
       "no bright green, no emerald, no neon, no cartoon, no anime, no illustration, "
       "no concept art, no digital painting, no 3d render, no CG, no plastic, no text, no watermark")

CAM = ("Photorealistic live-action film still from a feature film, a real animatronic creature "
       "photographed on set with practical lighting. Anamorphic lens, extremely shallow depth of field, "
       "fine natural film grain, desaturated cold teal-black grade, "
       "every scale a wet physical plate with silt in the seams, physically accurate specular highlights.")

# 结构规范（照 3.png 写死）
BODY = ("An Eastern dragon, a Chinese dragon — not a lizard and not a crocodile. "
        "PROPORTION AND STRUCTURE, stated precisely: it has ONE single continuous serpentine body, "
        "and the whole animal from skull to tail-tip is visible in the frame as one readable S-curve, "
        "with no part of the body hidden behind another and the body never crossing over itself. "
        "The head is small; behind it a long thick neck curves down and back; the torso is the thickest "
        "section and the thickness stays even along the torso rather than ballooning; "
        "from the end of the torso the body narrows steadily into a long tapering tail "
        "that is about one third of the total length and finishes in a small leaf-shaped fin. "
        "It has FOUR short powerful legs: one pair set immediately behind the neck, "
        "one pair set two thirds of the way along the body, each leg ending in four curved claws. "
        "A continuous row of bony spikes runs from the skull, over the neck and along the whole spine "
        "to the tip of the tail without any gap. "
        "A mane of long flowing hair hangs from the neck, two branched antler-like horns sweep back "
        "from the skull, two long whiskers trail from the upper jaw, a beard hangs beneath the jaw. "
        "The jaws are closed and no teeth are visible. "
        "The hide is dark slate-black with a moss-green patina, wet and dull, crusted with silt, "
        "and the belly plates are a dull dark red.")

ITEMS = [
    # ===== A 纯 T2I =====
    ("AST-CREATURE-001_real6_side_a",
     f"{BODY} Seen from the side at eye level, the entire animal in clean profile, "
     f"swimming through murky dark river water at night, faint light filtering down from the surface. " + CAM, None),

    ("AST-CREATURE-001_real6_side_b",
     f"{BODY} Seen from a low three-quarter angle, the whole animal readable in one S-curve against "
     f"the dark water, silt drifting off the spine, a single hard light raking from the upper left. " + CAM, None),

    ("AST-CREATURE-001_real6_side_c",
     f"{BODY} Full body in profile, the creature hanging motionless in deep black water, "
     f"lit only by a narrow shaft of surface light that falls across the middle of the body, "
     f"the head and the tail-tip fading into darkness. " + CAM, None),

    # ===== B I2I：只保 3.png 的结构，画风改成写实 =====
    ("AST-CREATURE-001_real6_i2i_a",
     f"Keep the exact body structure, proportions, limb placement and spine curve of the reference "
     f"drawing, and keep the same full-body side view. Do NOT keep its drawing style. "
     f"Re-render this creature as a real animal: the same Eastern dragon anatomy but now a "
     f"photorealistic creature with wet dark slate-black scales, a moss-green patina, "
     f"the belly plates dull dark red and the tail fin a muted teal, "
     f"suspended in murky dark river water at night with faint light from the surface. " + CAM, REF3),

    ("AST-CREATURE-001_real6_i2i_b",
     f"Keep the exact body structure, proportions, limb placement and spine curve of the reference "
     f"drawing. Do NOT keep its drawing style, its white background or its flat lighting. "
     f"Re-render this creature as a real animal photographed on a film set, "
     f"coiled in two loose loops on wet dark stone at the edge of a river at night, "
     f"the whole body still readable, head raised, torrential rain falling. " + CAM, REF3),
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
    print(f"=== V6 结构修正：{len(ITEMS)} 张 ===")
    urls_file = os.path.join(OUT, "_real6_urls.json")
    urls = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}

    def work(item):
        fname, p, ref = item
        if fname in urls:
            print(f"  {fname} 已存在，跳过"); return fname, urls[fname]
        try:
            u, dt = api_gen(p + "。" + NEG, ref=ref)
            download(u, os.path.join(OUT, fname + ".png"))
            print(f"  ✓ {fname}  {dt:.1f}s  {'I2I' if ref else 'T2I'}")
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
