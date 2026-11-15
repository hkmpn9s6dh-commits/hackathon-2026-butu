# -*- coding: utf-8 -*-
"""合成旁白并量长度。先出声音，再按实测时长排时间轴——反过来必漂。"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story

VOICE = "zh-CN-YunyangNeural"
RATE = "-8%"
OUT = os.path.join(story.ROOT, "build", "vo")


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(out.stdout.strip())


def synth(vid, text):
    dst = os.path.join(OUT, vid + ".mp3")
    cmd = [sys.executable, "-m", "edge_tts", "--voice", VOICE, "--rate=" + RATE,
           "--text", text, "--write-media", dst]
    for attempt in range(4):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(dst) and probe_dur(dst) > 0.3:
            return dst
        print(f"  retry {vid} ({attempt+1}): {r.stderr.strip()[:120]}")
    raise SystemExit(f"旁白合成失败：{vid}")


def main():
    os.makedirs(OUT, exist_ok=True)
    timing = {}
    for vid, text in story.VO.items():
        dst = os.path.join(OUT, vid + ".mp3")
        if not os.path.exists(dst) or probe_dur(dst) < 0.3:
            dst = synth(vid, text)
        d = probe_dur(dst)
        timing[vid] = dict(file=os.path.relpath(dst, story.ROOT), dur=round(d, 3), text=text)
        print(f"{vid}: {d:5.2f}s  {text[:24]}…")
    with open(os.path.join(story.ROOT, "build", "vo_timing.json"), "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=1)
    print("总旁白 %.1f 秒" % sum(v["dur"] for v in timing.values()))


if __name__ == "__main__":
    main()
