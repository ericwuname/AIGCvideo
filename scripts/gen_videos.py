#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分镜视频批量生成器（keyframe 模式）v2
- 提交阶段：3 并发（提交的 RPM 与轮询的 RPM 是分开计量的）
- 轮询阶段：单线程串行，每次请求间隔 3 秒，遇 429 退避 20 秒
- 断点续传：video_id 立即落盘 pending.json，中断后可继续轮询而不用重新提交（省配额）

用法: python gen_videos.py [镜号,镜号,...]
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
POLL = "https://api.agnes-ai.cn/agnesapi"
MODEL = "agnes-video-2.5-flash"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "work", "frames", "ep01")
OUT = os.path.join(ROOT, "work", "clips", "ep01")
os.makedirs(OUT, exist_ok=True)

PENDING = os.path.join(OUT, "pending.json")
DONE = os.path.join(OUT, "video_urls.json")

NEG = "保持人物五官和服装一致，不要变形，不要脸部扭曲，动作幅度小"

SHOTS = {
 1: ("6", "水面上那顶破旧斗笠缓缓漂移、慢慢打转，雨点不断打在水面上泛起细小涟漪，水面轻微起伏"),
 2: ("7", "她身体前倾，伸手去够水面上的斗笠，手指插进浑水里，水面荡开波纹，湿发随动作轻晃"),
 3: ("7", "水下的庞大暗影缓缓向前移动，水面被顶起一道长长的隆起波纹向前推进，她抬头望着，雨水顺着脸流下"),
 4: ("7", "巨大的水花在她面前炸开扑面而来，她向后跌坐进水里，抬起手臂挡在脸前，嘴张开"),
 5: ("8", "蛟的头部缓缓浮出水面，眼睛转向她，湿润的鳞片上有水珠滑落，极轻微地起伏呼吸"),
 6: ("7", "巨兽眼睛的竖直瞳孔极缓慢地收缩了一下，眼周的水珠滑落，一次缓慢的眨眼"),
 7: ("7", "她的手指缓缓收紧，攥住斗笠边缘，指节发白，手在轻微发抖，雨水打在手背上"),
 8: ("8", "她张着嘴清晰地说话，说出一句中文台词「好大一条」，嘴唇有明确的音节开合动作，说完后嘴唇微张停住，雨水顺着下颌滴落，眼睛眨了一下。背景的雨声很轻，人声清晰突出"),
 9: ("7", "蛟的头颅极缓慢地低垂下去，几乎贴到水面，眼睛半闭，水面映出它模糊的倒影"),
 10: ("8", "她注视着前方，嘴唇缓缓张开，用很轻的声音说出一个中文字「龙」，只有一个字，说完嘴唇轻轻闭合。眼神从挣扎变得平静。背景的雨声很轻，人声清晰突出"),
 11: ("8", "水面轰然炸开，巨大水柱冲天而起，一道金光从水中穿出冲向夜空，白色水雾向四周弥漫"),
 12: ("8", "她跪在泥地里一动不动，天边晨光极缓慢地变亮，水洼里的倒影微微晃动，湿衣角被风吹动"),
}

def api(url, body=None, retries=4):
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
                print(f"    429 限速，等待 {wait}s…")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("重试耗尽")

def submit(sid, frame_url):
    secs, action = SHOTS[sid]
    body = {"model": MODEL, "mode": "keyframe",
            "prompt": action + "。" + NEG, "first_frame": frame_url,
            "seconds": secs, "size": "720P", "aspect_ratio": "16:9", "n": 1}
    d = api(BASE + "/videos", body)
    return d.get("video_id") or d.get("id")

def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default

def save(p, obj):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    urls = load(os.path.join(FRAMES, "urls.json"), {})
    ids = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else sorted(SHOTS)

    pending = load(PENDING, {})
    done = load(DONE, {})

    # ---- 阶段一：提交（只提交既不在 pending 也不在 done 的） ----
    to_submit = [i for i in ids if str(i) not in pending and str(i) not in done]
    if to_submit:
        print(f"提交 {len(to_submit)} 个任务…")
        for i in to_submit:
            if str(i) not in urls:
                print(f"  ⚠ 镜{i} 缺少分镜帧，跳过"); continue
            try:
                vid = submit(i, urls[str(i)])
                pending[str(i)] = vid
                save(PENDING, pending)
                print(f"  镜{i:02d} → {vid}")
            except Exception as e:
                print(f"  镜{i:02d} 提交异常: {e}")
            time.sleep(1)

    # ---- 阶段二：串行轮询（关键：同一时刻只有一个请求） ----
    print(f"\n轮询 {len(pending)} 个任务（串行，间隔 3s）")
    t0 = time.time()
    while pending and time.time() - t0 < 900:
        for sid in sorted(pending, key=int):
            vid = pending[sid]
            try:
                d = api(f"{POLL}?video_id={vid}&model_name={MODEL}")
                st = d.get("status")
                if st == "completed":
                    url = d.get("url")
                    if url:
                        path = os.path.join(OUT, f"shot_{int(sid):02d}.mp4")
                        with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
                            f.write(r.read())
                        done[sid] = url; save(DONE, done)
                        pending.pop(sid); save(PENDING, pending)
                        print(f"  ✓ 镜{sid} 完成 {os.path.getsize(path)/1024:.0f} KB")
                    else:
                        print(f"  ⚠ 镜{sid} completed 但无 url")
                elif st == "failed":
                    print(f"  ✗ 镜{sid} 失败，移除待重试: {json.dumps(d, ensure_ascii=False)[:150]}")
                    pending.pop(sid); save(PENDING, pending)
            except Exception as e:
                print(f"  镜{sid} 查询异常: {e}")
            time.sleep(3)
        if pending:
            print(f"  …剩余 {len(pending)} 个，已用 {(time.time()-t0)/60:.1f} 分钟")

    print(f"\n完成 {len(done)}/{len(SHOTS)}，用时 {(time.time()-t0)/60:.1f} 分钟")
    if pending:
        print("未完成:", sorted(pending, key=int))

if __name__ == "__main__":
    main()
