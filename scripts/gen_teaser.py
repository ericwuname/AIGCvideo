#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
走蛟 · 成片小样（teaser）—— 6 镜，约 29 秒
目的：不再抠静帧，直接用已有最好资产当首帧做视频，看"动起来"能不能立住。
提交 3 并发；轮询单线程串行（间隔 3s，429 退避）；断点续传。
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "teaser")
os.makedirs(OUT, exist_ok=True)
PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "video_urls.json")


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def save(p, o):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


CRE = os.path.join(ROOT, "assets", "creature")
ENV = os.path.join(ROOT, "assets", "env")
U = {}
for f in ["_real10_urls.json", "_real7_urls.json", "_real2_urls.json", "_real6_urls.json", "_real9_urls.json"]:
    p = os.path.join(CRE, f)
    if os.path.exists(p):
        U.update(load(p))
U.update(load(os.path.join(ENV, "_env_urls.json")))

# 镜号: (时长, 首帧资产名, 动作描述)
SHOTS = {
    1: ("5", "AST-ENV-001_village_rain_v1",
        "雨夜的江南水乡河面，雨点不断打在水面上泛起涟漪，乌篷船随水流极轻微地晃动，"
        "屋檐下的水珠连续滴落，镜头极缓慢地向前推进，画面保持安静，没有人物出现"),
    2: ("5", "AST-CREATURE-001_real7_water_side",
        "水下昏暗浑浊，庞大的长躯从画面右侧极缓慢地游入，身体在水中缓缓起伏波动，"
        "悬浮的泥沙被带起翻涌，鳞片反着微弱的光，镜头贴着它缓慢侧向平移跟随"),
    3: ("4", "AST-CREATURE-001_real2_ridge",
        "雨夜的黑水面上，一道长长的脊背缓缓破水而出向前推进，水从鳞片上不停地淌落，"
        "水面被顶开两道向外扩散的波纹，镜头贴着水面缓慢横移"),
    4: ("5", "AST-CREATURE-001_real10_head_water",
        "蛟的头部缓慢浮出黑水，水线从下颌处缓缓退下，它的眼睛极缓慢地转向镜头方向，"
        "水珠顺着鳞片滑落，雨点打在水面，镜头极缓慢地推近"),
    5: ("4", "AST-CREATURE-001_real10_head_low",
        "低角度仰拍，蛟极缓慢地低下头逼近镜头，阴影里的眼睛一动不动地盯着镜头，"
        "雨水顺着它的面部流下，长须极轻微地飘动，镜头极轻微地上摇"),
    6: ("6", "AST-CREATURE-001_real7_bank",
        "蛟伏在湿漉漉的石岸上，前肢撑住石头，身体向后延伸进黑色的江水里，"
        "它极缓慢地把头抬起来，抬向画面上方，雨水顺着鳞片和鬃毛不断淌下，"
        "镜头极缓慢地向上摇，露出它更长的身体，水面被雨点打出密密麻麻的涟漪"),
    7: ("4", "AST-CREATURE-001_real9_eye_brow",
        "极近特写，蛟的一只眼睛，上眼睑压成一道窄缝，竖瞳在阴影里缓缓收缩了一下，"
        "眼周湿润的鳞片上有一滴水珠滑落，镜头纹丝不动，只有极轻微的对焦呼吸感"),
}

NEG = "。保持生物形态和比例稳定，不要变形，不要长出翅膀或额外肢体，不要张开嘴露出獠牙，不要出现西方龙，动作缓慢克制，镜头稳定"


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
                wait = 20 * (i + 1)
                print(f"    429 限速，等待 {wait}s…"); time.sleep(wait); continue
            raise
    raise RuntimeError("重试耗尽")


def submit(sid):
    secs, name, action = SHOTS[sid]
    if name not in U:
        raise RuntimeError(f"缺首帧 URL: {name}")
    body = {"model": MODEL, "mode": "keyframe",
            "prompt": action + NEG, "first_frame": U[name],
            "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    d = api(BASE + "/videos", body)
    vid = d.get("video_id") or d.get("id")
    if not vid:
        raise RuntimeError(str(d)[:200])
    return vid


def main():
    ids = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else sorted(SHOTS)
    pending = load(PENDING); done = load(DONE)

    todo = [i for i in ids if str(i) not in pending and str(i) not in done]
    if todo:
        print(f"提交 {len(todo)} 个任务…")
        def sub(i):
            try:
                vid = submit(i); print(f"  镜{i:02d} → {vid}"); return i, vid
            except Exception as e:
                print(f"  镜{i:02d} 提交异常: {e}"); return i, None
        with ThreadPoolExecutor(max_workers=3) as ex:
            for f in as_completed([ex.submit(sub, i) for i in todo]):
                i, vid = f.result()
                if vid:
                    pending[str(i)] = vid; save(PENDING, pending)

    print(f"\n轮询 {len(pending)} 个（串行，间隔 3s）")
    t0 = time.time()
    while pending and time.time() - t0 < 1200:
        for sid in sorted(pending, key=int):
            try:
                d = api(f"{POLL}?video_id={pending[sid]}&model_name={MODEL}")
                st = d.get("status")
                if st == "completed":
                    url = d.get("url")
                    if url:
                        path = os.path.join(OUT, f"t{int(sid):02d}.mp4")
                        with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
                            f.write(r.read())
                        done[sid] = url; save(DONE, done)
                        pending.pop(sid); save(PENDING, pending)
                        print(f"  ✓ 镜{sid} 完成 {os.path.getsize(path)/1024:.0f} KB")
                    else:
                        print(f"  ⚠ 镜{sid} 无 url: {json.dumps(d, ensure_ascii=False)[:150]}")
                elif st == "failed":
                    print(f"  ✗ 镜{sid} 失败: {json.dumps(d, ensure_ascii=False)[:200]}")
                    pending.pop(sid); save(PENDING, pending)
            except Exception as e:
                print(f"  镜{sid} 查询异常: {e}")
            time.sleep(3)
        if pending:
            print(f"  …剩余 {len(pending)}，已用 {(time.time()-t0)/60:.1f} 分钟")

    print(f"\n完成 {len(done)}/{len(SHOTS)}，用时 {(time.time()-t0)/60:.1f} 分钟")
    if pending:
        print("未完成:", sorted(pending, key=int))


if __name__ == "__main__":
    main()
