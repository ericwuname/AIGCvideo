#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第二批运镜（S2）—— 按用户要求铺开运镜语法 + 生物质感特写
用户要求：
  1. 不要只有推轨。要 从低到高 / 从高到低 / 从左到右 / 从右到左 / 斜下到斜上 / 斜上到斜下 / 环顾
  2. 穿过水面的压迫感不够 → 要头部特写、怒吼、面部细节、水与粘液、眼神变动
  3. 人物不要"整人从一个位置突然跑到另一个位置" → 改用多个不同的人、各自固定位置
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "s2")
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
S2 = load(os.path.join(ROOT, "work", "frames", "shot2", "_s2_urls.json"))

REF_CRE = [CRE["AST-CREATURE-001_real7_bank"], CRE["AST-CREATURE-001_real10_head_low"],
           CRE["AST-CREATURE-001_real10_head_water"]]
REF_AYUE = [CHR["AST-CHAR-001_ayue_body_c"], CHR["AST-CHAR-001_ayue_face_b"]]

WATER = ("The water is NEVER still: rain keeps striking the surface in a constant pattern of expanding "
         "rings, the flood current keeps heaving and sliding, foam keeps breaking and reforming.")

SHOTS = {
    # 1 从高到低（crane down）：俯瞰整条涨水的街 → 降到一个孩子的脸
    1: ("10", "keyframe", "S2-001_highangle_bend", S2,
        "摄影机从高处持续垂直下降（crane down，从大约三层楼高的俯角一路降下来），"
        "起幅是俯瞰整条被洪水淹没的街：左侧是黑瓦屋顶和几点暖黄灯笼，右侧是被水掀起的白浪，"
        "岸边一排小小的人影站在水边望着江面；镜头一边下降一边缓慢前移，"
        "最后降到人眼的高度，停在一个被母亲抱在怀里的孩子面前——孩子的脸占画面右下，"
        "睁大眼睛盯着江面，雨水打在孩子脸上。整个下降过程连续不停。" + WATER),

    # 2 从左到右横移（truck right）：掠过三个村民，交代"岸上有这么多人"
    2: ("9", "keyframe", "S2-002_villagers_row", S2,
        "摄影机贴着地面从画面左侧向右侧持续横移（truck right），像一个人沿着岸边走过去："
        "先经过披蓑衣的老渔夫，再经过抱着孩子的妇人，最后停在拄拐的老人身上，三个人依次从镜头前滑过，"
        "每个人都一动不动地望着同一个方向的江面；前景有雨丝和湿石板，"
        "灯笼的光在湿地上拖出长长的倒影，被雨点不断打碎又合起来。" + WATER),

    # 3 环顾（arc）：围绕她缓慢环绕
    3: ("9", "reference", None, REF_AYUE,
        "摄影机围绕她做半圈缓慢环绕（arc shot，从她的左后方绕到右前方），机位始终与她保持同样距离、"
        "高度不变；她站在齐膝的洪水里一动不动，头随着江面上的东西缓慢转动，"
        "水一直在她腿边翻涌、推挤，湿衣服被水流扯动；"
        "随着镜头绕过去，她身后的环境依次露出来：先是黑瓦房屋和灯笼，然后是整片被雨打花的江面。" + WATER),

    # 4 从斜下到斜上（diagonal crane up）：从水面斜着升起
    4: ("9", "reference", None, REF_CRE,
        "摄影机从贴近水面的低角度开始，沿着对角线向右上方持续升起（diagonal crane up）："
        "起幅几乎贴着水面，只有翻涌的水和一道正在被顶起的脊背，"
        "随着镜头斜向上抬，脊背后面整条长躯依次进入画面，鳞片上的水成片往下淌，"
        "升到高点时能看到它盘在洪水里的全貌和岸边的小小人影。整个斜升过程连续不停。" + WATER),

    # 5 头部怒吼特写（用户明确要求：面部细节、水与粘液、眼神变动）
    5: ("8", "reference", None, REF_CRE,
        "极近的头部特写，镜头几乎贴在它脸上，微微手持晃动。它张开嘴发出一声低吼："
        "上颌抬起时，唾液在上下颌之间拉出几道细丝然后断开，口腔内壁和舌是暗红色、湿润反光，"
        "锥形的牙齿上挂着水，水顺着牙尖一串串往下滴；"
        "鼻端喷出两股白色的水雾，脖颈的鳞片随着吼声一起一伏、鳞缝里挤出泥水；"
        "它的瞳孔在吼之前先猛地缩成一条细线，然后才张嘴。吼声低沉发闷。" + WATER),

    # 6 从水下穿出水面，加强压迫（低角度 + 水压 + 镜头被推）
    6: ("10", "reference", None, REF_CRE,
        "摄影机在水下极深的位置，仰视，然后猛地向上冲、穿过水面（crane up through surface，速度快）："
        "起幅是浑浊翻滚的暗水，庞大的躯体从镜头上方压下来、占满整个画面，水流被它挤压得猛烈翻搅；"
        "镜头加速上冲、撞开水面，一大片水被带起来泼向镜头，画面短暂被水糊住；"
        "出水后镜头继续抬升，露出暴雨中翻涌的江面和远处岸边一群极小的人影。" + WATER),
}

NEG = ("。镜头必须有明确方向感的连续运动，不能中途停住；水全程剧烈翻动；"
       "动作有重量和惯性；不要静止，不要像定格照片")


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


def submit(sid):
    secs, mode, kf, src, prompt = SHOTS[sid]
    body = {"model": MODEL, "mode": mode, "prompt": prompt + NEG,
            "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    if mode == "reference":
        body["images"] = src
    else:
        body["first_frame"] = src[kf]
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
                        path = os.path.join(OUT, f"p{int(sid):02d}.mp4")
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
