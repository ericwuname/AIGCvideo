#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运镜版（MOV 批次）
用户三条批评：
  1. 水静止不动 → 我把 prompt 写成"镜头几乎不动"，模型连水一起冻住了
  2. 视角局限、人物呆板 → 缺运镜。镜头必须从远到近/从近到远，先交代环境再聚焦
  3. 审美下降、压迫感没了 → 我把每镜亮度归一化到同一个均值（Y≈48），全片成了中灰。
     真正的电影感是"深黑 + 高光锐利"，不是"均值统一"

本批做法：
  - 每个镜头开头第一句就写摄影机运动（dolly in / pull back / crane up / truck / tracking）
  - 每个镜头都写死"水持续在动"
  - 人物给明确动作与走位，不给"站着不动"
  - 长镜优先（7–10s），用运镜而不是剪切来完成空间交代
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "mov")
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
NAR = load(os.path.join(ROOT, "work", "frames", "nar", "_nar_urls.json"))
IMM = load(os.path.join(ROOT, "work", "frames", "immerse", "_imm_urls.json"))

REF_CRE = [CRE["AST-CREATURE-001_real7_bank"], CRE["AST-CREATURE-001_real10_head_low"],
           CRE["AST-CREATURE-001_real7_water_side"]]
REF_AYUE = [CHR["AST-CHAR-001_ayue_body_c"], CHR["AST-CHAR-001_ayue_face_b"],
            CHR["AST-CHAR-001_ayue_face_a"]]

# 水必须在动的固定句（每镜都带）
WATER = ("The water is NEVER still: rain keeps striking the surface leaving a constant pattern of expanding "
         "rings, the current keeps heaving and sliding, ripples spread and fade continuously, "
         "and water runs off every surface.")

SHOTS = {
    # 1 从远到近的推进：先给环境，再落到她的背影
    1: ("10", "keyframe", "NAR-001_waterline", None,
        "摄影机持续向前推进（slow dolly in），镜头一路贴近水面向前移动、逐渐降低高度，"
        "起幅是辽阔黑沉、被雨点不断砸出涟漪的江面，画面里看不到人；随着推进，岸边湿透的芦苇从镜头两侧滑过，"
        "最后镜头停在她的背后：她一个人站在齐膝的浅水里，手里攥着一顶旧斗笠，望着江心，"
        "她的肩膀在雨里极轻地起伏，雨水顺着她的背往下流。全程雨不停、水流不停。"),

    # 2 跟随她涉水前行：身体有重心起伏，水被搅动
    2: ("8", "reference", None, REF_AYUE,
        "摄影机跟在她身后偏侧方，与她同步向前移动（tracking shot，手持），"
        "她蹚着齐膝的洪水一步一步向前走，每一步都带起水花、把水向两侧推开，水面被她的腿搅出一圈圈波纹；"
        "她的身体随步伐有真实的上下起伏，湿衣服贴在身上被水推得晃动，"
        "走了几步后她停下，微微转头看向画面右方的江面。全程雨不停、水流不停。"),

    # 3 从近到远：起幅是她的脸，镜头后拉露出环境和威胁
    3: ("9", "keyframe", "AST-CHAR-001_ayue_face_b", CHR,
        "起幅是她的脸部近景，她死死盯着画面右方的画外，瞳孔缩了一下，睫毛上的水珠抖落；"
        "然后摄影机持续向后拉远（pull back），她的上半身、腰、腿依次进入画面，露出她站在齐膝的水里，"
        "继续后拉，露出她脚下的水面和身后黑沉的江岸，最后画面里她变成中景，"
        "而画面右方的江面上，一道长长的水线正在由远及近地鼓起来、向她推进。"
        "整个后拉过程连续不停，全程雨不停、水流不停。"),

    # 4 贴水面低机位：水线由远及近涌来，最后扑上镜头
    4: ("7", "keyframe", "NAR-001_waterline", None,
        "摄影机贴在水面上一掌高的位置，镜头本身极缓慢地向前漂移，"
        "远处那道隆起的水线由远及近快速推过来，水面被从底下持续顶起、鼓高、塌下，"
        "白色浪迹在它前面散开又合拢，雨点密密麻麻砸在水面；"
        "水线越来越近，最后大股水直接涌上来扑满镜头，画面被水糊住。全程水流剧烈不停。"),

    # 5 从水下向上穿出水面（crane up）—— 一个镜头完成"水下威胁 → 水上她的渺小"
    5: ("10", "reference", None, REF_CRE,
        "摄影机在水下，镜头持续向上摇升（crane up through the surface）："
        "起幅在水下浑浊的暗流里，巨大的躯体从镜头上方极近地掠过，水流被它带得剧烈翻涌、泥沙成团炸开；"
        "镜头边升边穿过水面，带起一片水花和气泡，出水面后继续向上抬，露出暴雨中的江面和岸边；"
        "画面下方是刚被顶开、还在剧烈翻涌的水，远处岸边站着一个极小的身影。"
        "整个上升过程连续，水全程剧烈翻动。"),

    # 6 侧移逼近：镜头横移，蛟头从画面右侧进入
    6: ("8", "reference", None, REF_CRE,
        "摄影机贴着水面向画面左侧横移（truck left，手持），前景湿透的芦苇不断从镜头前掠过；"
        "随着横移，蛟的头部从画面右侧进入画面，越来越近，它的颈和鬃被速度带得向后甩，"
        "水被它的动作向两侧高高劈开、水花直接甩到镜头上，雨丝在逆光里拉成条。"
        "镜头在移动中被水浪推得晃动。全程水剧烈翻涌不停。"),
}

NEG = ("。" + WATER + " 动作要有力量、有惯性和速度；人物身体每一处都要有真实的重量感和次级动态；"
       "绝对不要静止，不要像定格照片，不要让水停住")


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
        body["first_frame"] = src[kf] if src else (NAR.get(kf) or IMM.get(kf))
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
                        path = os.path.join(OUT, f"m{int(sid):02d}.mp4")
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
