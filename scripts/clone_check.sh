#!/usr/bin/env bash
# 全新 clone 复验：只信 clone 里的东西，不信工作目录。
set -uo pipefail
cd "$(dirname "$0")/.."
SRC=$(pwd)
DST=${1:-"$SRC/../_clone-test"}
rm -rf "$DST"
echo "== clone → $DST =="
git clone -q "$SRC" "$DST" || { echo "clone 失败"; exit 1; }
cd "$DST"
echo "== 文件数 =="; git ls-files | wc -l
echo "== 构建 =="
bash scripts/build.sh 2>&1 | tail -30
