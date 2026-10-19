#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
叙事重剪版（NAR 批次）—— 补上连续性剪辑的语法
用户：「单看几秒没问题，连起来不知道在说什么」
诊断见 docs/19。本批补的正是缺的那几件：
  - 建立镜头（人和威胁在同一空间）
  - 视线匹配（她看 → 她看到的）
  - 轴线统一（她在画面左，蛟在画面右远方）
  - Kuleshov（先给脸，后给对象）
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FR = os.path.join(ROOT, "work", "frames", "nar")
OUT = os.path.join(ROOT, "work", "clips", "nar")
os.makedirs(FR, exist_ok=True); os.makedirs(OUT, exist_ok=True)
PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "urls.json")


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def save(p, o):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


CHR = load(os.path.join(ROOT, "assets", "char", "_ayue_urls.json"))
REF_AYUE = [CHR["AST-CHAR-001_ayue_body_c"], CHR["AST-CHAR-001_ayue_face_b"]]

CAM = ("Photorealistic live-action film still from a Chinese period feature film, shot on a real cinema "
       "camera with an anamorphic lens at night in torrential rain, practical lighting, handheld, "
       "extremely shallow depth of field, natural film grain, desaturated cold teal-black grade, "
       "water droplets on the front element")

# ==== 需要先生成一张关键帧：她看到的东西（视线匹配的后件）====
KEYFRAME_PROMPT = (
    "THE SHOT IS FROM A PERSON'S EYE LEVEL STANDING AT THE EDGE OF A BLACK RIVER AT NIGHT, looking out "
    "across the water. The black river fills the frame. In the middle distance a long low line of water is "
    "heaving and bulging upward, a swelling ridge of displaced water running from the right side of the "
    "frame toward the left, water sliding off it, and a faint white wake spreading from it. Nothing of any "
    "creature is visible, only the water being pushed up from underneath. Rain striking the surface "
    "everywhere. Near the left edge, out of focus, wet reeds. " + CAM)
KEYFRAME_NEG = ("。no text, no watermark, no cartoon, no anime, no illustration, no 3d render, no CG, "
                "no dragon visible, no head, no animal, no person, no boat")

SHOTS = {
    # (时长, 模式, prompt, 首帧资产名, 参考图组)
    1: ("5", "reference",
        "全景，镜头在人的高度：阿月小小的一个人站在画面左侧岸边的浅水里，背对或侧对着镜头，"
        "她面前是画面右侧大片黑沉沉的江面，雨在下，她一动不动地盯着右边远处，"
        "镜头几乎不动，只有雨和水的动", None, REF_AYUE),
    2: ("4", "reference",
        "阿月的近景，她正面对着镜头，先是眼睛向画面右侧转过去，然后头跟着缓缓转向右边，"
        "视线离开镜头、望向画面右侧画外，下巴微微抬起，雨水打在脸上，镜头轻微手持呼吸", None, REF_AYUE),
    3: ("5", "keyframe",
        "镜头顺着她的视线望出去，远处黑色江面上那道隆起的水线正在由右向左缓缓推进，"
        "水面被从底下顶起、向上鼓起又塌下去，白色的浪迹向两侧散开，雨点不断砸在水面上，"
        "镜头极轻微地跟着水面移动，手持呼吸感", "NAR-001_waterline", None),
    4: ("4", "reference",
        "阿月的近景，她盯着画面右侧画外，身体完全僵住没有动，眼睛缓缓睁大，嘴唇微微张开，"
        "脸上没有夸张的表情，只是僵住了，雨水顺着脸往下淌，镜头几乎不动", None, REF_AYUE),
    5: ("4", "reference",
        "阿月站在浅水里，一大片水花突然从画面右侧扑过来打在她身上和脸上，"
        "她整个人向后缩、抬起手臂挡在脸前，脚下退了半步，湿衣服头发被冲得向后扯，"
        "镜头被水扑中晃了一下", None, REF_AYUE),
}

NEG = ("。镜头是手持的，有呼吸和轻微晃动；动作真实有惯性；"
       "画面不要干净，要有前景遮挡、水渍、雨丝；不要缓慢静止，不要像定格")


def api(url, body=None, retries=5):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data,
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 20 * (i + 1); print(f"    429 等 {w}s"); time.sleep(w); continue
            raise
    raise RuntimeError("重试耗尽")


def ensure_keyframe(name, prompt, neg):
    p = os.path.join(FR, "_nar_urls.json")
    m = load(p)
    if name in m:
        return m[name]
    body = {"model": "agnes-image-2.5-flash", "prompt": prompt + neg, "size": "2K", "ratio": "16:9",
            "extra_body": {"response_format": "url"}}
    d = api(BASE + "/images/generations", body)
    u = d["data"][0]["url"]
    with urllib.request.urlopen(u, timeout=180) as r, open(os.path.join(FR, name + ".png"), "wb") as f:
        f.write(r.read())
    m[name] = u; save(p, m)
    print(f"  ✓ 关键帧 {name}")
    return u


def submit(sid):
    secs, mode, prompt, kf, refs = SHOTS[sid]
    body = {"model": MODEL, "mode": mode, "prompt": prompt + NEG,
            "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    if mode == "reference":
        body["images"] = refs
    else:
        body["first_frame"] = ensure_keyframe(kf, KEYFRAME_PROMPT, KEYFRAME_NEG)
    d = api(BASE + "/videos", body)
    vid = d.get("video_id") or d.get("id")
    if not vid:
        raise RuntimeError(str(d)[:300])
    return vid


def main():
    ids = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else sorted(SHOTS)
    pending = load(PENDING); done = load(DONE)
    todo = [i for i in ids if str(i) not in pending and str(i) not in done]

    if todo:
        print(f"提交 {len(todo)}…")
        def sub(i):
            try:
                v = submit(i); print(f"  镜{i:02d} [{SHOTS[i][1]}] → {v}"); return i, v
            except Exception as e:
                print(f"  镜{i:02d} 异常: {e}"); return i, None
        with ThreadPoolExecutor(max_workers=2) as ex:
            for f in as_completed([ex.submit(sub, i) for i in todo]):
                i, v = f.result()
                if v:
                    pending[str(i)] = v; save(PENDING, pending)

    print(f"\n轮询 {len(pending)}（串行 3s）")
    t0 = time.time()
    while pending and time.time() - t0 < 1500:
        for sid in sorted(pending, key=int):
            try:
                d = api(f"{POLL}?video_id={pending[sid]}&model_name={MODEL}")
                st = d.get("status")
                if st == "completed":
                    url = d.get("url")
                    if url:
                        path = os.path.join(OUT, f"n{int(sid):02d}.mp4")
                        with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
                            f.write(r.read())
                        done[sid] = url; save(DONE, done)
                        pending.pop(sid); save(PENDING, pending)
                        print(f"  ✓ 镜{sid} {os.path.getsize(path)/1024:.0f} KB")
                    else:
                        print(f"  ⚠ 镜{sid} 无 url")
                elif st == "failed":
                    print(f"  ✗ 镜{sid} 失败 {json.dumps(d, ensure_ascii=False)[:160]}")
                    pending.pop(sid); save(PENDING, pending)
            except Exception as e:
                print(f"  镜{sid} 异常: {e}")
            time.sleep(3)
        if pending:
            print(f"  …剩 {len(pending)}，{(time.time()-t0)/60:.1f} 分钟")

    print(f"\n完成 {len(done)}/{len(SHOTS)}")
    if pending:
        print("未完成:", sorted(pending, key=int))


if __name__ == "__main__":
    main()
