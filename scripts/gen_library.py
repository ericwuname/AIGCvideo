#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
素材库（IMG 批次）—— 视频配额快用完，先做图
核心要解决的是"鳄鱼感"。光"不出现头部"不够，真正的区别在**躯体断面与姿态**：

  鳄鱼 = 身体扁平、宽、贴着水面
  蛟   = 圆筒状躯干、拱起、成弧线，水面只切过它的一小段

所以本批重点做"圆筒躯 + 拱起弧线"的体型研究，另外补齐主角与环境。
"""
import json, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "lib")
os.makedirs(OUT, exist_ok=True)

CAM = ("Photorealistic live-action film still from a Chinese period fantasy feature, shot on a real cinema "
       "camera with an anamorphic lens at night, practical lighting only, extremely shallow depth of field, "
       "natural film grain, cold desaturated grade, deep blacks with hot specular highlights on wet "
       "surfaces, water running continuously off every surface")

# 体型核心：圆筒 + 拱起
BODY = ("The body is a ROUND CYLINDER, thick as a man's torso, with a circular cross-section — NOT flat, "
        "NOT wide, NOT low and sprawling. It arches UP out of the water in a high curve like a bent tree "
        "trunk, so only one short segment of it is above the surface, and the surface cuts across the "
        "cylinder. Overlapping fish-like scales, a continuous row of tall dorsal spines along the top, "
        "clear mucus and water streaming off it. ")
NEG_BODY = ("。not a crocodile, not an alligator, not a lizard, no flat wide body, no sprawling posture, "
            "no square bony scutes, no crocodile snout, no jaw, no teeth, no legs visible")

A = ("A Yue, an eighteen-year-old Chinese fisher girl, soaked coarse hemp clothes, wet hair plastered to "
     "her face and neck, bare weather-beaten face, no makeup, calloused hands. ")

ITEMS = [
    # ---- 龙躯：圆筒 + 拱起（8 张）----
    ("BODY-01_arch", BODY + "Night, black flood water, torrential rain. The arched segment rises out of "
     "the water diagonally across frame, water sheeting off it. " + CAM + NEG_BODY),
    ("BODY-02_loop", BODY + "The cylinder rises, bends over and re-enters the water, forming a loop. "
     "Only the loop is visible, the rest is submerged. Lightning rim-lights the top edge. " + CAM + NEG_BODY),
    ("BODY-03_cross", BODY + "The round body crosses the frame from lower left to upper right, close, "
     "filling much of the frame, water pouring off in sheets. " + CAM + NEG_BODY),
    ("BODY-04_ridge", BODY + "Low angle, only the top of the arch and the dorsal spine row break the "
     "surface, the rest is dark water and spray. " + CAM + NEG_BODY),
    ("BODY-05_tail", BODY + "The rear third of the body lifts out of the water, tapering, ending in a "
     "small fin, the round cross-section clearly visible. " + CAM + NEG_BODY),
    ("BODY-06_claw", "Extreme close-up: a huge four-toed claw with curved talons gripping a wet black "
     "rock, water running over the talons, silt in the joints, the limb above it thick and round. " + CAM),
    ("BODY-07_scale", "Extreme macro of overlapping fish-like scales, wet, clear mucus stretched into "
     "thin strings between the plates, water sheeting over, one hard cold rim light. " + CAM),
    ("BODY-08_silhouette", "Almost total darkness over black water at night. A tall arched silhouette of "
     "a long cylindrical body rises out of the water, backlit by a single lightning flash behind it, "
     "completely black, no detail at all, only the outline of the arch and a row of spines. " + CAM),

    # ---- 主角（6 张）----
    ("AYUE-01_face_neutral", A + "Front-on close-up in torrential rain at night, staring off to one side "
     "at something out of frame, jaw tight, no smile. " + CAM),
    ("AYUE-02_face_fear", A + "Close-up, her eyes wide, lips slightly parted, frozen mid-breath, rain "
     "running down her face. " + CAM),
    ("AYUE-03_face_resolve", A + "Close-up, eyes closed, tears mixing with rain, jaw set, the moment "
     "before she speaks. " + CAM),
    ("AYUE-04_body_water", A + "Full length, standing knee-deep in black flood water at night, holding an "
     "old bamboo hat against her chest, seen from behind, small in frame, the river ahead. " + CAM),
    ("AYUE-05_hands", "Close-up of a young woman's rough working hands gripping a worn bamboo hat, the "
     "knuckles white, rainwater running over the calloused skin, a dark red stain on the hat's rim. " + CAM),
    ("AYUE-06_recoil", A + "She stumbles back half a step as a sheet of water hits her, one arm thrown up "
     "across her face, hair and clothes dragged backwards by the surge. " + CAM),

    # ---- 环境（5 张）----
    ("ENV-01_street_flood", "High angle over a flooded Chinese riverside village at night in torrential "
     "rain: black water surging through a stone-paved street, tiled roofs, a few warm lanterns, a group "
     "of small human figures at the water's edge. " + CAM),
    ("ENV-02_quay", "A flooded stone quay at night, torrential rain, lantern light smeared on the wet "
     "paving, the black river beyond rising, no people. " + CAM),
    ("ENV-03_doorway", "The dark interior of a cottage seen from inside, a half-open wooden door framing "
     "the rain and blackness outside, a clay stove still burning orange at the edge of frame, no people. " + CAM),
    ("ENV-04_waterline_wide", "Camera a hand's width above a black flood river at night, near foreground "
     "reeds bent by wind, rain hammering the surface into a mass of small craters, distant bank lost in "
     "darkness. " + CAM),
    ("ENV-05_lightning", "A Chinese riverside village at night in a storm, the instant a lightning flash "
     "lights everything: roofs, water, rain streaks all briefly white, harsh and flat. " + CAM),
]


def gen(prompt):
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt, "size": "2K", "ratio": "16:9",
            "extra_body": {"response_format": "url"}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))["data"][0]["url"]
        except Exception as e:
            last = e; print("  重试", e); time.sleep(12 * (i + 1))
    raise RuntimeError(last)


def main():
    p = os.path.join(OUT, "_lib_urls.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    def work(it):
        name, prompt = it
        if name in m:
            return name, m[name]
        try:
            u = gen(prompt)
            with urllib.request.urlopen(u, timeout=180) as r, open(os.path.join(OUT, name + ".png"), "wb") as f:
                f.write(r.read())
            print(f"  ✓ {name}")
            return name, u
        except Exception as e:
            print(f"  ✗ {name}: {e}"); return name, None

    with ThreadPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(work, it) for it in ITEMS]):
            n, u = f.result()
            if u:
                m[n] = u; json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"完成 {len(m)}/{len(ITEMS)}")


if __name__ == "__main__":
    main()
