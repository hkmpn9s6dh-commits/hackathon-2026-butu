# -*- coding: utf-8 -*-
"""把若干张图拼成一张联系表（contact sheet），带序号，方便一次看完做质检。"""
import sys, os
from PIL import Image, ImageDraw

def montage(files, out, cols=2, cell=760, label=True):
    files = [f for f in files if os.path.exists(f)]
    if not files:
        raise SystemExit("no files")
    rows = (len(files) + cols - 1) // cols
    im0 = Image.open(files[0])
    ar = im0.height / im0.width
    ch = int(cell * ar)
    W, H = cols * cell, rows * ch
    sheet = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((cell, ch), Image.LANCZOS)
        x = (i % cols) * cell + (cell - im.width) // 2
        y = (i // cols) * ch + (ch - im.height) // 2
        sheet.paste(im, (x, y))
        if label:
            d.rectangle([i % cols * cell + 6, i // cols * ch + 6,
                         i % cols * cell + 46, i // cols * ch + 42], fill=(0, 0, 0))
            d.text((i % cols * cell + 18, i // cols * ch + 14), str(i + 1), fill=(255, 255, 255))
    sheet.save(out, quality=88)
    print(out, sheet.size)

if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0]
    files = args[1:]
    cols = 2
    if files and files[0].startswith("--cols="):
        cols = int(files[0].split("=")[1]); files = files[1:]
    montage(files, out, cols=cols)
