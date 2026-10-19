#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
身临其境版（IMM 批次）
用户反馈：方向对了，但缺"真实感"和"代入感"，缺身临其境的压迫感。
三条对策：
  1. 机位站进人的位置——贴水面（手离水面一掌高）、人眼高度、手持
  2. 画面不干净——前景芦苇/雨丝遮挡、水花糊住镜头、镜头有水渍、闪电瞬间过曝
  3. 声音有空间（在 make_immerse.py 里做：静默→爆发）
另外修一个 bug：之前只 trim 了画面没 trim 声音，导致音画不同步。
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "imm")
os.makedirs(OUT, exist_ok=True)
PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "urls.json")


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def save(p, o):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


CRE = load(os.path.join(ROOT, "assets", "creature", "_real7_urls.json"))
CRE.update(load(os.path.join(ROOT, "assets", "creature", "_real10_urls.json")))
CHR = load(os.path.join(ROOT, "assets", "char", "_ayue_urls.json"))
IMM = load(os.path.join(ROOT, "work", "frames", "immerse", "_imm_urls.json"))

REF_CREATURE = [CRE["AST-CREATURE-001_real7_bank"],
                CRE["AST-CREATURE-001_real10_head_low"],
                CRE["AST-CREATURE-001_real7_water_side"]]
REF_AYUE = [CHR["AST-CHAR-001_ayue_face_b"], CHR["AST-CHAR-001_ayue_body_c"]]

# 镜头：(时长, 模式, prompt, keyframe资产名/None, 用哪组参考图)
SHOTS = {
    1: ("5", "keyframe",
        "镜头贴在水面上方一掌高，前景左侧湿透的芦苇在风雨里剧烈摇晃、扫过画面，"
        "雨点密集砸在水面上溅起无数细小水花，远处有几点模糊的暖光，"
        "镜头像被人端在手里一样随呼吸轻微起伏，画面左下角有一道水渍", "IMM-001_waterlevel_reeds", None),
    2: ("5", "reference",
        "水下，那道极长的黑影贴着镜头极近地高速掠过，几乎是擦着镜头过去，"
        "泥沙被带得炸开翻涌糊住画面，镜头被水压推得晃了两下，黑影占满整个画面后迅速掠过消失",
        None, REF_CREATURE),
    3: ("4", "reference",
        "水面像被从底下猛然顶开，黑水和白色水沫一起炸起来，大量水花直接扑向镜头，"
        "镜头被水糊住、画面瞬时一片模糊和水珠，随后水珠滑落视线恢复，镜头剧烈晃动",
        None, REF_CREATURE),
    4: ("6", "reference",
        "这条巨大的东方蛟龙迎面高速冲过来，头几乎顶到镜头前，它的身体把水面劈开、"
        "水向两侧高高翻起，水花直接打在镜头上，长鬃和龙须被速度甩得向后飞，"
        "镜头被冲击推得连晃几下，前景有几根芦苇被风浪压弯扫过画面",
        None, REF_CREATURE),
    5: ("5", "reference",
        "阿月站在齐膝的洪水里，被扑面而来的水浪从正面拍中，整个人向后踉跄两步差点摔倒，"
        "她抬起手臂挡在脸前，水花砸在她身上和脸上，湿透的衣服头发被冲得向后扯，"
        "镜头与人眼同高、离她两步远，被水浪推得后退并晃动",
        None, REF_AYUE),
    6: ("5", "reference",
        "阿月的近景，她浑身湿透站在水里喘着气，缓缓抬起头望向镜头后方的江面，"
        "雨水顺着她的脸和下巴不断往下淌，她眨了一下眼，水珠从睫毛上抖落，"
        "镜头几乎贴在她面前，轻微呼吸起伏",
        None, REF_AYUE),
}

NEG = ("。镜头必须是手持感：有呼吸、有抖动、有被冲击推动的位移；"
       "画面不要干净，要有前景遮挡、水渍、雨丝、局部过曝；"
       "动作要快、有力量、有惯性，水和毛发必须有被带动的次级动态；不要缓慢，不要像定格")


def api(url, body=None, retries=5):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data,
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 20 * (i + 1); print(f"    429 等 {w}s"); time.sleep(w); continue
            raise
    raise RuntimeError("重试耗尽")


def submit(sid):
    secs, mode, prompt, kf, refs = SHOTS[sid]
    body = {"model": MODEL, "mode": mode, "prompt": prompt + NEG,
            "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    if mode == "reference":
        body["images"] = refs
    else:
        body["first_frame"] = IMM[kf]
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
        with ThreadPoolExecutor(max_workers=3) as ex:
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
                        path = os.path.join(OUT, f"i{int(sid):02d}.mp4")
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
