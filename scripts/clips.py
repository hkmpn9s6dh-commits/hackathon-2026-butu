# -*- coding: utf-8 -*-
"""把图生视频的片段转成 memmap 帧堆：裁掉顶部 90px（去掉工具水印），统一 16:9。"""
import glob, json, os, shutil, subprocess, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story

ROOT = story.ROOT
OUT = os.path.join(ROOT, "build", "clips")
CROP_TOP = 90
TARGET = {                      # 片段 id -> 源文件前缀
    "fire": "微距慢镜_火焰",
    "ink": "一滴墨在绢面上继续洇开",
    "deer": "镜头极缓慢向前推",
}


def to_ascii(src, idx):
    """中文路径会让 cv2.VideoCapture 静默失败，先拷成 ASCII 文件名。"""
    dst = os.path.join(OUT, "src_%d.mp4" % idx)
    if not os.path.exists(dst):
        shutil.copyfile(src, dst)
    return dst


def main():
    os.makedirs(OUT, exist_ok=True)
    index = {}
    for cid, prefix in TARGET.items():
        hit = [f for f in glob.glob(os.path.join(ROOT, "motion", "*.mp4")) if prefix in os.path.basename(f)]
        if not hit:
            print("跳过（没有片段）：", cid); continue
        src = max(hit, key=os.path.getmtime)
        path = to_ascii(src, len(index))
        cap = cv2.VideoCapture(path)
        frames = []
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            rgb = rgb[CROP_TOP:CROP_TOP + 648]
            if rgb.shape[:2] != (648, 1152):
                rgb = cv2.resize(rgb, (1152, 648), interpolation=cv2.INTER_AREA)
            frames.append(rgb)
        cap.release()
        if not frames:
            print("解码失败：", cid); continue
        arr = np.stack(frames)
        np.save(os.path.join(OUT, cid + ".npy"), arr)
        index[cid] = dict(n=len(frames), fps=24, w=1152, h=648,
                          src=os.path.relpath(src, ROOT))
        print("%s: %d 帧 %.2fs" % (cid, len(frames), len(frames) / 24.0))
    json.dump(index, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
