#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
角色资产模块化（CHR 批次）
用户思路：把人物拆成 表情组 / 动作组 / 服饰组，分别做图，再组后拼装。

关键技术：**用同一张定妆图做图生图（I2I）参考**，才能保持"同一个人"。
  （此前 I2I 失败是因为拿"场景照"当参考；拿"脸部定妆照"当参考是正解。）

用法:
  python gen_char_sheet.py ayue exp      # 表情组 8 张
  python gen_char_sheet.py ayue pose     # 动作组 6 张
  python gen_char_sheet.py ayue cost     # 服饰组 4 张
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "assets", "lib")
OUT = os.path.join(ROOT, "assets", "char", "AYUE")
os.makedirs(OUT, exist_ok=True)

# 基准定妆（脸最正、最清晰的一张）
BASE_ID = "AYUE-02_face_fear"

KEEP = ("Keep EXACTLY the same person: same face, same bone structure, same nose, same eyes, same "
        "eyebrows, same hair, same age, same skin. Only the expression changes. ")
CAM = ("Photorealistic live-action film still, real cinema camera with an anamorphic lens, night, "
       "torrential rain, practical lighting only, extremely shallow depth of field, natural film grain, "
       "cold desaturated grade, wet skin and wet hair, no makeup, NO retouching")
NEG = ("。no makeup, no lipstick, no beauty retouching, no plastic skin, no smiling unless asked, "
       "no cartoon, no illustration, no 3d render, no CG, no text, no watermark")

EXP = [
    ("EXP-01_calm", "Her face is completely neutral and still, mouth closed, eyes looking slightly off to "
     "one side at nothing in particular, jaw relaxed. "),
    ("EXP-02_terror", "Her eyes are wide open, whites showing, lips slightly parted, the breath caught in "
     "her throat, every muscle frozen, staring at something just out of frame. "),
    ("EXP-03_hatred", "Her jaw is clenched hard, the corners of her mouth pulled DOWN, brows driven "
     "together and low, eyes narrowed and burning, absolutely not smiling. "),
    ("EXP-04_doubt", "She does not believe what she is seeing: brows slightly raised and drawn together, "
     "head tilted a fraction, lips pressed thin, eyes flicking as if searching for an explanation. "),
    ("EXP-05_resolve", "Her eyes are closed, then just opening, lashes wet, the muscles of her face "
     "releasing, mouth barely moving as if she has just decided something, a single tear track. "),
    ("EXP-06_grief", "Her face is crumpling, brows drawn up in the middle, mouth pulled down and open a "
     "little, tears mixed with rain on her cheeks, trying not to make a sound. "),
    ("EXP-07_numb", "Her face is empty and slack, eyes unfocused, seeing nothing, mouth slightly open, "
     "as if she has stopped thinking altogether. "),
    ("EXP-08_startle", "Her head has just snapped round toward a sound, eyes not yet focused, eyebrows "
     "lifted, lips parting, the very first instant of reaction. "),
]

POSE = [
    ("POSE-01_search", "Full length: she is bent over at the waist, both hands plunged into knee-deep "
     "black flood water, searching for something under the surface, her wet hair hanging down. "),
    ("POSE-02_rise", "Full length: she is straightening up out of the water, one hand still in the water, "
     "her back still curved, beginning to lift her head. "),
    ("POSE-03_lookback", "Full length: she stands in the water and has turned her upper body to look back "
     "over her shoulder, one arm hanging, the water swirling around her thighs. "),
    ("POSE-04_recoil", "Full length: she is stumbling back half a step, weight on her back foot, one arm "
     "thrown up across her face, her whole body leaning away from something. "),
    ("POSE-05_shield", "Full length: she stands braced, both feet planted wide in the water, one forearm "
     "raised in front of her face, her other hand clenched at her side. "),
    ("POSE-06_hat", "Full length: she kneels in shallow water, holding an old worn bamboo hat against her "
     "chest with both arms wrapped around it, her head bowed. "),
]

COST = [
    ("COST-01_front", "Full length front view, standing straight, arms at her sides, neutral pose, showing "
     "the full outfit clearly. Soaked coarse undyed hemp short jacket and trousers, a cloth sash, "
     "bare feet, mud on the hem. "),
    ("COST-02_side", "Full length side view, standing straight, neutral pose, showing the silhouette and "
     "the layers of the soaked hemp jacket. "),
    ("COST-03_back", "Full length back view, standing straight, showing how the wet jacket clings to her "
     "back and shoulders, the sash knotted behind. "),
    ("COST-04_detail", "Close-up of the fabric itself: soaked coarse hemp weave, water beaded on the "
     "surface, the fibres dark where wet and pale where dry, a mended patch with visible stitching, "
     "mud crusted along a seam. "),
]

GROUPS = {"exp": EXP, "pose": POSE, "cost": COST}


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def gen_i2i(ref_url, prompt):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt, "size": "2K", "ratio": "16:9",
            "extra_body": {"response_format": "url", "image": ref_url}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))["data"][0]["url"]
        except Exception as e:
            last = e; print("   重试", e); time.sleep(12 * (i + 1))
    raise RuntimeError(last)


def main():
    group = sys.argv[1] if len(sys.argv) > 1 else "exp"
    items = GROUPS[group]

    lib_urls = load(os.path.join(LIB, "_lib_urls.json"))
    ref = lib_urls.get(BASE_ID)
    if not ref:
        print("缺少基准图 URL:", BASE_ID); sys.exit(1)

    p = os.path.join(OUT, f"_{group}_urls.json")
    m = load(p)

    def work(it):
        name, desc = it
        if name in m:
            return name, m[name]
        try:
            full = (desc + "\n" + KEEP if group == "exp" else desc + "\nKeep the same face and hair. ") + \
                   "。A Yue, eighteen-year-old Chinese fisher girl, soaked coarse hemp clothes. " + CAM + NEG
            u = gen_i2i(ref, full)
            with urllib.request.urlopen(u, timeout=180) as r, open(os.path.join(OUT, name + ".png"), "wb") as f:
                f.write(r.read())
            print(f"  ✓ {name}")
            return name, u
        except Exception as e:
            print(f"  ✗ {name}: {e}"); return name, None

    with ThreadPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(work, it) for it in items]):
            n, u = f.result()
            if u:
                m[n] = u; json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"完成 {group}: {len(m)}/{len(items)}")


if __name__ == "__main__":
    main()
