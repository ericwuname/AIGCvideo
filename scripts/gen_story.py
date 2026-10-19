#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
《走蛟》剧情小样 · 6 镜约 40 秒
目的：验证"能不能讲清一个故事"，不是"龙好不好看"。
故事链：斗笠带血（死人）→ 阿月攥住斗笠认出爹的（她的痛）→ 水下黑影（威胁）→
        她说"好大一条"（恨）→ 她说"……龙"（放下，核心转折）→ 她跪下，龙吟起（结果）
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "clips", "story")
os.makedirs(OUT, exist_ok=True)
PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "video_urls.json")


def load(p, d=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else (d if d is not None else {})


def save(p, o):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


U = {}
for p in [os.path.join(ROOT, "work", "frames", "story", "_story_urls.json"),
          os.path.join(ROOT, "assets", "char", "_ayue_urls.json")]:
    U.update(load(p))

SHOTS = {
    1: ("6", "STORY-001_hat_blood",
        "固定机位，俯拍雨夜的黑色江面，那顶旧竹编斗笠在水上极缓慢地打转漂移，"
        "雨点不断砸在水面溅起细小的水花把斗笠边缘那道暗红血迹一点点冲淡，镜头几乎不动"),
    2: ("7", "AST-CHAR-001_ayue_body_c",
        "阿月蹚着齐膝的洪水向前走两步，弯腰一把攥住漂在水上的旧斗笠，把它从水里提起来，"
        "低头看清了上面的血迹，动作猛地停住，然后缓缓抬起头望向江心方向，"
        "雨水顺着她的头发和脸往下淌，镜头缓慢向她推近"),
    3: ("6", "STORY-002_shadow",
        "水下极暗的水中，一道极长的黑影贴着河底极缓慢地向前滑过，"
        "河底的泥沙被它带起翻涌成一片浑浊，黑影的一端渐渐隐入更深的黑暗，"
        "镜头几乎静止，只有水和泥沙在动"),
    4: ("7", "AST-CHAR-001_ayue_face_b",
        "阿月的近景，她死死盯着前方，眼里是压不住的恨意，嘴角向下压着，下颌绷得极紧，"
        "眉心皱起，眼睛微微发红发湿。她几乎是从牙缝里挤出四个中文字「好大一条」，"
        "说完嘴唇立刻紧紧闭合，仍然盯着前方。雨水顺着下颌滴落。"
        "整段只有她说话的人声和很轻的雨声，人声清晰突出。她绝对不笑"),
    5: ("7", "AST-CHAR-001_ayue_face_a",
        "阿月的近景，她闭着眼，睫毛上挂着雨水，然后极缓慢地睁开眼睛，眼神已经从恨变成平静，"
        "她很轻地说出一个中文字「龙」，只有一个字，说完嘴唇轻轻闭合，"
        "脸上的肌肉完全松开，雨水混着眼泪流下来。背景的雨声很轻，人声清晰突出"),
    6: ("7", "STORY-004_back_glow",
        "阿月背对镜头跪在浅水里，怀里紧紧抱着那顶旧斗笠，肩膀极轻微地起伏，"
        "雨还在下，远处黑色江面上有一层极淡的金光从水底透上来，缓慢地变亮，"
        "镜头极缓慢地向后拉远，最后画面慢慢暗下去"),
}

NEG = ("。保持人物长相、发型和服装与首帧完全一致，不要变形，不要换脸，动作幅度小，镜头稳定，"
       "不要出现其他人物，不要出现龙或任何生物的完整身体")


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
                print(f"    429 等待 {wait}s…"); time.sleep(wait); continue
            raise
    raise RuntimeError("重试耗尽")


def submit(sid):
    secs, name, action = SHOTS[sid]
    if name not in U:
        raise RuntimeError(f"缺首帧 URL: {name}")
    body = {"model": MODEL, "mode": "keyframe", "prompt": action + NEG,
            "first_frame": U[name], "seconds": secs, "size": "720P",
            "aspect_ratio": "16:9", "n": 1}
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
                        path = os.path.join(OUT, f"s{int(sid):02d}.mp4")
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
                print(f"  镜{sid} 查询异常: {e}")
            time.sleep(3)
        if pending:
            print(f"  …剩 {len(pending)}，{(time.time()-t0)/60:.1f} 分钟")

    print(f"\n完成 {len(done)}/{len(SHOTS)}，{(time.time()-t0)/60:.1f} 分钟")
    if pending:
        print("未完成:", sorted(pending, key=int))


if __name__ == "__main__":
    main()
