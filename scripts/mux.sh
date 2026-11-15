#!/usr/bin/env bash
# 混流：无音轨视频 + 混音 → 成片；响度按 −16 LUFS / −1.5 dBTP 两遍 loudnorm。
set -euo pipefail
cd "$(dirname "$0")/.."

V=build/video_silent.mp4
A=build/mix.wav
OUT=submission/补图.mp4

# 第一遍：量
read -r I TP LRA TH < <(ffmpeg -hide_banner -nostats -i "$A" \
  -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 \
  | py -3 -c "
import json,sys
t=sys.stdin.read(); j=json.loads(t[t.rindex('{'):t.rindex('}')+1])
print(j['input_i'], j['input_tp'], j['input_lra'], j['input_thresh'])")

echo "响度测量：I=$I TP=$TP LRA=$LRA TH=$TH"

# 第二遍：按测量值线性归一 + 限幅
ffmpeg -y -v error -i "$V" -i "$A" \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=$I:measured_TP=$TP:measured_LRA=$LRA:measured_thresh=$TH:linear=true,aresample=48000" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart -shortest "$OUT"

ffprobe -hide_banner -v error -show_entries format=duration,size:stream=codec_name,width,height,sample_rate,channels \
  -of default=nw=1 "$OUT"
