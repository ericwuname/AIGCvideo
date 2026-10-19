#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分镜帧批量生成器
用法: python gen_frames.py [镜号,镜号,...]   不带参数则生成全部
输出: work/frames/ep01/shot_XX.png + work/frames/ep01/urls.json
"""
import json, os, sys, time, urllib.request, urllib.error

KEY = "cpk-mzkDZfpAidgqI3vMf1dniX6XRxUe9K1onvMQf1gzUGCRqqI9"
BASE = "https://api.agnes-ai.cn/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "frames", "ep01")
os.makedirs(OUT, exist_ok=True)

NEG = "不要动漫风，不要游戏CG，不要塑料感皮肤，不要过度磨皮，不要高饱和，不要棚拍平光，不要现代元素，不要文字水印，不要镜像扭曲，不要五官不对称，不要多余的手指"

# 角色锚点（定妆图 URL）
CAST_FILE = os.path.join(ROOT, "work", "cast_url.txt")
CAST = open(CAST_FILE).read().strip() if os.path.exists(CAST_FILE) else None

SHOTS = {
 1: dict(use_cast=False, prompt=(
   "电影感特写镜头，细雨打在水面上，一顶破旧的竹编斗笠漂浮在浑黄的洪水表面，缓缓打转。"
   "斗笠边缘有一道暗红色的血迹，被雨水冲淡。背景是失焦的江面和远处的黑暗。"
   "冷蓝色调，只有远处一点微弱的暖黄渔火映在水面。浅景深，微距般的特写，35mm 胶片颗粒，写实电影质感。")),

 2: dict(use_cast=True, prompt=(
   "电影感近景，同一位中国江南渔家少女，湿透的乌黑长发贴在脸上，粗麻深色短褐，"
   "她半跪在齐膝的浑浊洪水里，身体前倾，一只手伸向水面去够什么东西，脸上是焦急与急切。"
   "暴雨夜，冷蓝调，一束暖黄光从左侧照来。浅景深，35mm 胶片颗粒。")),

 3: dict(use_cast=True, prompt=(
   "电影感中景，暴雨夜的江面，浑黄翻涌的洪水表面。水面之下有一道极长的、庞大的黑色暗影正在水中缓缓穿行，"
   "那是水下的巨大物体把水面顶起一道长长的隆起波纹，暗影在水里，不在岸上，不是地面上的投影。"
   "画面右下角有一位渔家少女，深褐色粗麻短褐，湿发贴脸，她半跪在洪水里抬头望向水中那道暗影，只有侧脸。"
   "冷蓝调，远处一点暖黄渔火。浅景深，35mm 胶片颗粒，写实电影质感。")),

 4: dict(use_cast=True, prompt=(
   "电影感近景，同一位渔家少女跌坐在浑浊的洪水里向后退缩，巨大的水花在她面前炸开，"
   "水珠在冷光里被定格成细小的亮点，她的脸被打湿，眼睛睁大，嘴微张，表情惊恐。"
   "暴雨夜，冷蓝调，唯有水花反射的冷白光。浅景深，35mm 胶片颗粒，写实电影质感。")),

 5: dict(use_cast=False, prompt=(
   "电影感特写，一只巨大水生生物的头部浮出水面，形似鳄鱼与巨蛇的结合体，没有角，"
   "鳞甲湿润呈深墨色，鳞片边缘有崩裂的伤口渗着暗红血迹，一只巨大的金色竖瞳眼睛正望向画面外。"
   "真实动物的质感，像纪录片拍到的真实猛兽，有湿润的皮肤反光和泥沙附着。"
   "暴雨夜，微弱的冷光，浅景深。")),

 6: dict(use_cast=False, prompt=(
   "极端特写，一只巨大爬行动物的眼睛，竖直的瞳孔，虹膜是金黄与墨黑交织，"
   "眼周是湿润的深色鳞片，水珠挂在鳞片边缘，瞳孔里有极微小的光点倒影。"
   "真实动物质感，纪录片式拍摄，湿润反光，浅景深。冷蓝色调。")),

 7: dict(use_cast=False, prompt=(
   "电影感特写，一只年轻女子的手紧紧攥着一顶破旧竹编斗笠的边缘，指节发白，"
   "手背上有撑船磨出的茧和旧伤，皮肤被雨水泡得发白起皱。斗笠上有暗红血迹被雨水冲淡。"
   "冷蓝调，一束微弱的暖光从侧面打在手背上。浅景深，35mm 胶片颗粒，写实电影质感。")),

 8: dict(use_cast=True, prompt=(
   "电影感近景特写，同一位中国江南渔家少女，湿发贴在脸颊，雨水顺着下颌滴落，"
   "她张着嘴正在说话，表情是强烈的犹豫与挣扎，眼眶发红有泪光但没有落下。"
   "冷蓝调，一束暖黄光从侧面照亮半张脸。浅景深，面部占画面大半，35mm 胶片颗粒，写实电影质感。")),

 9: dict(use_cast=False, prompt=(
   "电影感特写，一只巨大水生生物的头颅低垂下来，几乎贴到水面，鳞甲湿润深墨色，没有角，"
   "眼睛半闭着，像是在等待什么。水面上倒映着它模糊的轮廓。"
   "真实动物质感，湿润的皮肤反光，纪录片式拍摄。暴雨夜，冷蓝调，浅景深。")),

 10: dict(use_cast=True, prompt=(
   "电影感近景特写，同一位中国江南渔家少女，她闭着眼睛，睫毛上挂着水珠，"
   "表情正从挣扎转向平静，面部肌肉放松下来。冷蓝调，一束暖黄光从侧面照亮半张脸。"
   "浅景深，35mm 胶片颗粒，写实电影质感。")),

 11: dict(use_cast=False, prompt=(
   "电影感中景，暴雨夜的江面，水面轰然炸开，巨大的水柱与白色水雾冲天而起。"
   "一道耀眼的金色光芒从水中穿出，笔直冲向暴雨的夜空，光柱边缘散落着细小的金色光点，像燃着的鳞片。"
   "强烈逆光，画面几乎全为剪影与光，看不到具体的形体。冷蓝夜空与金光的强烈对比。"
   "写实电影质感，35mm 胶片颗粒，暴雨中，水雾弥漫。")),

 12: dict(use_cast=False, prompt=(
   "电影感全景，黎明时分的江边泥地，一位渔家少女跪在画面偏右的位置，背影很小，"
   "天边泛出一线冷白的晨光，洪水退去留下大片泥泞和水洼，水洼里反着天光，"
   "一顶破旧斗笠落在她身旁的泥里。安静，空旷，大面积留白。"
   "写实电影质感，35mm 胶片颗粒，地平线压在下三分之一。")),
}

def gen(shot_id, retries=2):
    s = SHOTS[shot_id]
    body = {
        "model": "agnes-image-2.5-flash",
        "prompt": s["prompt"] + NEG,
        "size": "2K",
        "ratio": "16:9",
        "extra_body": {"response_format": "url"},
    }
    if s["use_cast"] and CAST:
        body["extra_body"]["image"] = [CAST]
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                BASE + "/images/generations", data=data,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
            url = d["data"][0]["url"]
            print(f"  镜{shot_id:02d} OK  {time.time()-t0:.1f}s  {url}")
            return url
        except Exception as e:
            print(f"  镜{shot_id:02d} 第{attempt+1}次失败: {e}")
            time.sleep(3)
    return None

def download(url, path):
    with urllib.request.urlopen(url, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())

def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if len(sys.argv) > 1:
        ids = [int(x) for x in sys.argv[1].split(",")]
    else:
        ids = sorted(SHOTS)

    urlfile = os.path.join(OUT, "urls.json")
    urls = json.load(open(urlfile)) if os.path.exists(urlfile) else {}

    # 跳过已完成的
    todo = [i for i in ids if str(i) not in urls]
    if not todo:
        print("全部已完成，无需生成。")
        return
    print(f"待生成 {len(todo)} 镜: {todo}")

    def work(sid):
        u = gen(sid)
        if not u:
            return sid, None
        try:
            download(u, os.path.join(OUT, f"shot_{sid:02d}.png"))
        except Exception as e:
            print(f"  镜{sid:02d} 下载失败: {e}")
        return sid, u

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(work, s): s for s in todo}
        for f in as_completed(futs):
            sid, u = f.result()
            if u:
                urls[str(sid)] = u
                json.dump(urls, open(urlfile, "w"), ensure_ascii=False, indent=2)

    print(f"完成 {len(urls)}/{len(SHOTS)}。URL 表: {urlfile}")

if __name__ == "__main__":
    main()
