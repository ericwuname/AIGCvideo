#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把素材库拼成一张联系表（contact sheet），一次看完全部 19 张"""
import os, textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "assets", "lib")
OUT = os.path.join(ROOT, "release")
os.makedirs(OUT, exist_ok=True)

COLS, CW, CH, PAD, LABEL_H = 4, 420, 231, 10, 26
BG = (18, 18, 20)
FG = (225, 225, 228)

names = sorted([f[:-4] for f in os.listdir(LIB) if f.endswith(".png") and not f.startswith("_")])
rows = (len(names) + COLS - 1) // COLS
W = COLS * (CW + PAD) + PAD
H = rows * (CH + LABEL_H + PAD) + PAD

sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)
font = None
for fp in [r"C:/Windows/Fonts/msyh.ttc", r"C:/Windows/Fonts/simhei.ttf", r"C:/Windows/Fonts/arial.ttf"]:
    if os.path.exists(fp):
        try:
            font = ImageFont.truetype(fp, 15); break
        except Exception:
            pass
if font is None:
    font = ImageFont.load_default()

for i, n in enumerate(names):
    r, c = divmod(i, COLS)
    x = PAD + c * (CW + PAD)
    y = PAD + r * (CH + LABEL_H + PAD)
    im = Image.open(os.path.join(LIB, n + ".png")).convert("RGB")
    im = im.resize((CW, CH), Image.LANCZOS)
    sheet.paste(im, (x, y))
    d.rectangle([x, y, x + CW - 1, y + CH - 1], outline=(60, 60, 64))
    d.text((x + 4, y + CH + 5), n, fill=FG, font=font)

out = os.path.join(OUT, "素材库-联系表.jpg")
sheet.save(out, quality=92)
print(f"✓ {out}  {len(names)} 张  {sheet.size}")
