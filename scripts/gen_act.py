#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动作/一致性验证（reference 模式）
用户三条反馈：
  1. 角色不统一 → 改用 reference 模式（喂同一组参考图，让每镜认同一只）
  2. 动作僵硬   → 这是我自己写的：上一批 prompt 里有「极缓慢」「镜头几乎不动」「动作幅度小」
                   本批全部反着写：冲刺/甩/炸/掀/踉跄 + 次级动态（水、雨、鬃、须、衣）
  3. 交互感弱   → 让画面里的东西互相作用：水被犁开、浪把人掀退、水花砸在身上
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "act")
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

# reference 模式的参考图组（同一组喂给每一镜，保证是同一只）
REF_CREATURE = [CRE["AST-CREATURE-001_real7_bank"],
                CRE["AST-CREATURE-001_real10_head_low"],
                CRE["AST-CREATURE-001_real7_water_side"]]

# 镜头：(时长, 模式, prompt, keyframe资产名或None)
SHOTS = {
    1: ("5", "reference",
        "这条巨大的东方蛟龙在水中猛然向前冲刺，身体剧烈起伏、发力推动，"
        "它的脊背像犁一样把水面剖开，水向两侧高高翻涌出去，大片水花被它的动作甩到半空，"
        "长鬃和龙须被速度带得全部向后飞起，镜头贴着水面，被涌来的水浪推得左右晃动", None),
    2: ("5", "reference",
        "它的头部猛地向镜头方向甩过来，甩动的力量把长鬃、龙须和下颌的长髯一起甩得向外飞起，"
        "水珠成片从身上甩出，眼睛死死盯住镜头，镜头被这一下带得猛地一颤后稳住", None),
    3: ("4", "keyframe",
        "水面像被从底下顶开一样剧烈隆起，黑水成片掀起向四周砸落，水雾炸开弥漫，"
        "冲击形成的白色浪头快速向外推，镜头被水冲得剧烈晃动，雨点被气流带得横向拉飞",
        "STORY-002_shadow"),
    4: ("5", "keyframe",
        "阿月被扑面而来的水浪掀得踉跄后退，抬起手臂挡在脸前，整个人向后仰，脚下在水里打滑，"
        "水花砸在她身上，湿透的衣服和头发被冲得向后扯，她站定后猛地抬头盯向前方，镜头随之后退",
        "AST-CHAR-001_ayue_body_c"),
    5: ("5", "keyframe",
        "阿月的近景，她猛地被水浪扑中，闭眼偏头，雨水和浪花打在她脸上，"
        "她很快睁开眼死死盯向前方，喘着气，胸口剧烈起伏，镜头轻微晃动",
        "AST-CHAR-001_ayue_face_b"),
}

NEG = ("。动作要有力量、有惯性、有速度，不要缓慢，不要静止，不要像定格；"
       "水、雨、毛发必须有被带动起来的次级动态；镜头要有真实的呼吸和晃动")


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
    secs, mode, prompt, kf = SHOTS[sid]
    body = {"model": MODEL, "mode": mode, "prompt": prompt + NEG,
            "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    if mode == "reference":
        body["images"] = REF_CREATURE
    else:
        if kf is not None:
            src = CHR if kf.startswith("AST-CHAR") else load(
                os.path.join(ROOT, "work", "frames", "story", "_story_urls.json"))
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
                        path = os.path.join(OUT, f"a{int(sid):02d}.mp4")
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
