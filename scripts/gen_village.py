#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
村庄夜惊（VIL 批次）
按用户给的导演思路搭结构：
  村内各人本来在干自己的事 → 被龙吟/巨雷惊动 → 各有各的反应 → 收进主角视点
并且按用户要求改龙的呈现方式：
  **不让观众看清**。大部分时间只有黑暗里的轮廓，闪电瞬间才照亮局部。
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "vil")
os.makedirs(OUT, exist_ok=True)
PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "urls.json")


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def save(p, o):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


VIL = load(os.path.join(ROOT, "work", "frames", "vil", "_vil_urls.json"))
S2 = load(os.path.join(ROOT, "work", "frames", "shot2", "_s2_urls.json"))
NAR = load(os.path.join(ROOT, "work", "frames", "nar", "_nar_urls.json"))
CHR = load(os.path.join(ROOT, "assets", "char", "_ayue_urls.json"))

WATER = ("The water is NEVER still: rain keeps striking the surface in a constant pattern of expanding "
         "rings, the flood current keeps heaving and sliding, foam keeps breaking and reforming. ")

# (时长, prompt, 首帧资产名, 资产表)
SHOTS = {
    1: ("7", "摄影机在高处极缓慢地向前下方推移，画面是被洪水淹没的水乡村道：左侧黑瓦屋顶和几点灯笼，"
        "右侧黑水翻涌；雨线密集。突然一道闪电把整个村子照亮一瞬，屋顶、水面、雨丝全被镀上一层白光，"
        "随后立刻暗回去，只剩雨声。远处巷口有个小小的人影站着。", "S2-001_highangle_bend", S2),
    2: ("7", "屋内，老妇跪在土灶前，手里攥着一把稻草停在半空，她的头极缓慢地转向左边的门口；"
        "灶膛里的火在跳动，火光在她脸上一明一暗，把皱纹照得很深；她张了张嘴没出声，喉咙动了一下。"
        "门外雨下得很大。镜头极缓慢地向她推近一点点。", "VIL-001_stove_oldwoman", VIL),
    3: ("5", "屋内极暗，一个人把眼睛贴在半开的门缝上往外看，只有半张脸在缝里；"
        "他的眼珠微微左右动了一下，然后瞳孔猛地一缩，呼吸加快，睫毛抖动，"
        "门外的冷光在他眼睛里闪了一下。镜头几乎不动。", "VIL-002_peek_doorgap", VIL),
    4: ("6", "雨中湿透的石板巷子，挑着竹担的渔夫本来在往前走，突然停住，身体慢慢转回来，"
        "抬头望向画面外的方向；雨水顺着他的斗笠和蓑衣往下淌，脚下的积水被雨点不断打出涟漪，"
        "屋檐的灯笼在雨里摇晃，光在湿地上抖。镜头极缓慢地横移一点。", "VIL-003_alley_fisherman", VIL),
    5: ("7", "河边浅水里，她弯着腰在水里摸索着什么，手指插进浑水里；突然她停住，慢慢直起腰，"
        "抬起头望向画面右方的江心；水一直在她腿边翻涌推挤，雨打在她身上。"
        "镜头从她身后极缓慢地向上升起一点。", "AST-CHAR-001_ayue_body_c", CHR),
    6: ("5", "镜头越过她的肩膀望向江面：黑水上有一道隆起的水线正由远处向这边推进，"
        "水面被从底下顶起又塌下，白沫在它前面散开；雨点密集砸在水面上。镜头极轻微地跟着水线移动。",
        "NAR-001_waterline", NAR),
    7: ("9", "几乎全黑的水面上，一个巨大的东西在水下缓慢移动：只能看到一道极长的黑色轮廓勉强破开水面，"
        "脊背上有一排低矮的凸起，身后拖着河水的尾迹；它的具体形状完全看不清，"
        "画面里没有任何细节被照亮。它缓慢地向画面前方移动，水面被它推开。镜头贴着水面轻微跟随。",
        "VIL-004_dark_mass", VIL),
    8: ("5", "极近距离的特写，湿滑的深色鳞片在画面里铺满；鳞片之间有透明的粘液拉成细丝、"
        "被重力拉长后断开，水成一层连续的水膜从鳞面上流下去，鳞缝里积着淤泥。"
        "一道闪电照亮一瞬，鳞面反光，随后又暗下去。镜头几乎不动。", "VIL-005_mucus_scales", VIL),
    9: ("7", "黑水上那道巨大的黑色轮廓忽然加速、朝画面前方压过来，水面被它顶得剧烈翻涌、"
        "大片白沫炸开；闪电在它身后炸亮，一瞬勾出它背棘的锯齿轮廓，随即又归于黑暗，"
        "只剩水声和雨声。镜头被涌来的水推得向后晃。", "VIL-004_dark_mass", VIL),
}

NEG = ("。" + WATER + "动作有重量和惯性；**不要让它被清晰地照亮，大部分时间必须是看不清的轮廓**；"
       "不要静止，不要像定格照片")


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
    secs, prompt, kf, src = SHOTS[sid]
    body = {"model": MODEL, "mode": "keyframe", "prompt": prompt + NEG,
            "first_frame": src[kf], "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
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
                v = submit(i); print(f"  镜{i:02d} → {v}"); return i, v
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
                        path = os.path.join(OUT, f"v{int(sid):02d}.mp4")
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
