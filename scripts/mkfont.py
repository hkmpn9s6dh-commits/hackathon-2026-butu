# -*- coding: utf-8 -*-
"""把 Noto Serif SC 子集化到本片用到的字，随包带走（不依赖系统字体）。"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story, texts

SRC = r"C:\Windows\Fonts\NotoSerifSC-VF.ttf"
DST = os.path.join(story.ROOT, "fonts", "NotoSerifSC-sub.ttf")
TXT = os.path.join(story.ROOT, "build", "chars.txt")


def main():
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    os.makedirs(os.path.dirname(TXT), exist_ok=True)
    s = texts.all_text()
    with open(TXT, "w", encoding="utf-8") as f:
        f.write("".join(sorted(set(s))))
    cmd = [sys.executable, "-m", "fontTools.subset", SRC,
           "--text-file=" + TXT, "--output-file=" + DST,
           "--layout-features=*", "--drop-tables+=DSIG", "--no-hinting",
           "--desubroutinize", "--name-IDs=*", "--recalc-bounds"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:])
        raise SystemExit("子集化失败")
    print("唯一字 %d 个 → %s (%.1f KB)" % (len(set(s)), DST, os.path.getsize(DST) / 1024))


if __name__ == "__main__":
    main()
