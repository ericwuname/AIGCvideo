#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
写实蛟龙 V2 —— 全部纯文生图（T2I）
V1 教训：
  1. 2.jpeg 是场景照不是设定照，I2I 只给氛围不给"这一只" → 弃用参考图
  2. "crown" 会画出金冠 → 禁用，改 "crest of tapered bony spikes"
  3. 负面里的 no fur / not cute 招来了白色小兽 → 改成正面锁"画面里只有它"
  4. "serpentine+冠" 会变眼镜蛇 → 明写颈部粗厚不展开
  5. 鳞色偏鲜绿 → 压成墨黑+苔绿、低饱和
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "creature")

# 负面：只留"压画风"和"压错误解剖"，不再堆 no-cute（会反向召唤）
NEG = ("NOT an illustration, NOT concept art, NOT a digital painting, NOT anime, NOT a 3d render, "
       "NOT CG, no text, no watermark, no logo, no wings, no feathers, no fur, "
       "no headdress, no crown on the head, no jewelry, no metal ornament, "
       "no flared neck, no spread hood, no bright green, no emerald, no neon, "
       "no plastic skin, no cartoon, no chibi, no toy")

# 摄影语言（写实的核心：摄影机在场、现场实用光）
CAM = ("Photorealistic live-action film still from a feature film. "
       "Shot on a real cinema camera with an anamorphic lens on location, practical lighting, "
       "suspended particulate in the air and water, extremely shallow depth of field, "
       "natural fine film grain, desaturated cold teal-black color grade, "
       "physically accurate wet specular highlights on every scale, "
       "nothing in the frame is rendered or painted")

# 造型锁定（V2 关键：禁用 crown / 压掉眼镜蛇 / 压暗鳞色）
LOOK = ("a colossal ancient water dragon. Its body is a thick serpentine coil, as thick as a man is tall, "
        "armoured in jet black scales carrying a dark moss-green patina and a dull wet sheen, "
        "the seams between the scales crusted with silt and algae. "
        "Its skull is long and heavy with a blunt closed jaw, and along the top of the skull runs "
        "a crest of tapered bony spikes swept backwards, grown out of the bone, "
        "NOT a crown and NOT a headdress. Long thin barbels trail from the upper jaw. "
        "The neck is thick and muscular and does not flare out. "
        "The eyes are pale and milky with a faint inner glow and vertical slit pupils. "
        "It has a pair of short powerful forelimbs held close to the chest, and no hind legs. "
        "The frame contains only this one creature, nothing else alive")

ITEMS = [
    # ===== 造型定稿：头部 3 个角度各出一张 =====
    ("AST-CREATURE-001_real2_head_a",
     f"Extreme close-up three-quarter portrait of the head of {LOOK}, filling the whole frame. "
     f"The head turns toward the lens, one cold practical light raking across the wet scales from the "
     f"upper left, the rest falling into deep shadow, dark murky water out of focus behind. " + CAM),

    ("AST-CREATURE-001_real2_head_b",
     f"Pure side profile close-up of the head of {LOOK}, filling the whole frame. "
     f"Silhouetted against a faint pale glow in the water, a rim light tracing the crest of spikes and "
     f"the line of the barbels, scales reading as individual wet plates. " + CAM),

    ("AST-CREATURE-001_real2_head_c",
     f"Low angle close-up looking up at the head of {LOOK}, the head lowered toward the lens, "
     f"one milky eye catching the light, water running off the crest of spikes. " + CAM),

    # ===== 全身＝能否撑起"这一只" =====
    ("AST-CREATURE-001_real2_body",
     f"{LOOK}. It is coiled into a massive spiral resting on the silt of a flooded riverbed at night, "
     f"the head raised at the centre of the coil and turned toward the lens, "
     f"faint green light filtering down from the surface and raking across the wet black scales, "
     f"broken stone and mud beneath it, its body dwarfing everything around. " + CAM),

    ("AST-CREATURE-001_real2_glide",
     f"{LOOK}. Seen from the side, the whole length of it gliding slowly through murky dark river water, "
     f"the long body undulating and tapering into a finned tail, the head leading, "
     f"silt swirling off the coils, weak shafts of surface light cutting down through the murk. " + CAM),

    # ===== 水面镜头（V1 全被拽成水下，这次写死"above the surface"）=====
    ("AST-CREATURE-001_real2_ridge",
     f"{LOOK}. Now ABOVE the water, at night in torrential rain: only its enormous scaled back breaks "
     f"the surface of the black river, a long row of wet black plates cutting the water like a chain of "
     f"stones, water sheeting off the ridge in thin silver streams, the head out of frame, "
     f"the camera low and close to the waterline, rain hammering the surface, "
     f"a distant lightning flash as the only light source. " + CAM),

    ("AST-CREATURE-001_real2_rear",
     f"{LOOK}. It rears up out of black flood water at night, the head and shoulders rising through the "
     f"surface in a wall of spray, water pouring off the crest of spikes, mouth closed, "
     f"rain streaking past, a lightning bolt behind it lighting the wet scales from behind, "
     f"the riverbank dark and empty. " + CAM),

    # ===== 真微距（V1 被拽成全景，这次明写"the eye fills 90% of the frame"）=====
    ("AST-CREATURE-001_real2_eye",
     f"Macro shot: the eye of {LOOK} fills ninety percent of the frame, nothing else visible. "
     f"A pale jade iris crazed with fine radial cracks around a vertical slit pupil, "
     f"the lid a rim of small wet armoured scales crusted with silt, "
     f"one water droplet clinging to the lower lid and catching a pinpoint of light. " + CAM),
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
    print(f"=== 写实蛟龙 V2（纯 T2I）：{len(items)} 张 ===")

    urls_file = os.path.join(OUT, "_real2_urls.json")
    urls = json.load(open(urls_file, encoding="utf-8")) if os.path.exists(urls_file) else {}

    def work(item):
        fname, p = item
        if fname in urls:
            print(f"  {fname} 已存在，跳过"); return fname, urls[fname]
        full = p + "。" + NEG
        try:
            u, dt = api_gen(full)
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
