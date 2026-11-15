#!/usr/bin/env bash
# 一条命令重建《补图》。任何一步失败就停。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/7 字体子集 =="
py -3 scripts/mkfont.py

echo "== 2/7 旁白 =="
py -3 scripts/vo.py

echo "== 3/7 时间轴 =="
py -3 scripts/timeline.py

echo "== 4/7 段落帧堆 =="
py -3 scripts/clips.py

echo "== 5/7 混音 =="
py -3 scripts/audio.py

echo "== 6/7 逐帧渲染 =="
py -3 scripts/render.py

echo "== 7/7 混流 =="
bash scripts/mux.sh

echo "== 复验 =="
py -3 scripts/verify.py
