"""
把资产图压缩成"知识库可读版" —— 长边限 1024，JPEG q82。

⚠️只读原图、只写 assets_opt/。**绝不删除或修改 assets/ 下的任何文件。**
输出：assets_opt/  供 GitHub 入库使用。
"""
import os
from PIL import Image

SRC = r"D:\0.个人文档\个人文档\AI短剧\assets"
DST = r"D:\0.个人文档\个人文档\AI短剧\assets_opt"
MAX = 1024


def conv(src, dst):
    try:
        im = Image.open(src).convert("RGB")
        w, h = im.size
        if max(w, h) > MAX:
            r = MAX / max(w, h)
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        return os.path.getsize(dst)
    except Exception as e:
        print(f"  SKIP {os.path.basename(src)}: {e}")
        return 0


total_in = total_out = n_ok = 0
for root, _dirs, files in os.walk(SRC):
    for fn in sorted(files):
        if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        sp = os.path.join(root, fn)
        rel = os.path.relpath(sp, SRC)
        dp = os.path.join(DST, os.path.splitext(rel)[0] + ".jpg")
        if os.path.exists(dp):
            continue
        so = conv(sp, dp)
        total_in += os.path.getsize(sp)
        total_out += so
        n_ok += 1
        if n_ok % 30 == 0:
            print(f"  ... {n_ok} done, {total_out/1048576:.1f} MB")

print(f"\n{n_ok} images")
print(f"in : {total_in/1048576:.1f} MB")
print(f"out: {total_out/1048576:.1f} MB")
print(f"原图未做任何改动：{SRC}")
