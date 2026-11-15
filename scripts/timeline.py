# -*- coding: utf-8 -*-
"""按实测旁白时长排时间轴，输出 timeline.json / .srt / .ass / 分镜表。"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story, texts

ROOT = story.ROOT
B = os.path.join(ROOT, "build")


def wrap(s, n=story.SUB_MAX):
    lines, cur = [], ""
    for ch in s:
        cur += ch
        if len(cur) >= n and ch in "，。；：？！、—…":
            lines.append(cur); cur = ""
    if cur:
        if lines and len(cur) <= 2:
            lines[-1] += cur
        else:
            lines.append(cur)
    return lines


def build():
    vt = json.load(open(os.path.join(B, "vo_timing.json"), encoding="utf-8"))
    shots, prev_end, prev_id = [], None, None
    for raw in story.SHOTS:
        s = dict(raw)
        dur = float(s["dur"])
        if s.get("vo"):
            dur = max(dur, vt[s["vo"]]["dur"] + 1.5)
        s["dur"] = round(dur, 3)
        if prev_end is None:
            start, kind, td = 0.0, "cut", 0.0
        else:
            kind, td = story.TRANS.get(f"{prev_id}|{s['id']}", story.TRANS["default"])
            start = prev_end - td if kind == "xfade" else prev_end
        s["start"] = round(start, 3)
        s["end"] = round(start + dur, 3)
        s["trans_in"] = [kind, td]
        if s.get("vo"):
            lead = 0.9 if kind == "cut" else (td * 0.5 + 0.8 if kind == "xfade" else td * 0.5 + 0.9)
            s["vo_start"] = round(start + lead, 3)
            s["vo_dur"] = vt[s["vo"]]["dur"]
            s["sub"] = wrap(vt[s["vo"]]["text"])
            s["sub_start"] = s["vo_start"]
            s["sub_end"] = round(min(s["vo_start"] + vt[s["vo"]]["dur"] + 0.6, s["end"] + 0.4), 3)
        shots.append(s)
        prev_end, prev_id = s["end"], s["id"]

    total = shots[-1]["end"]
    tl = dict(total=round(total, 3), fps=story.FPS, w=story.W, h=story.H, shots=shots,
              vo=vt, title=story.TITLE, subtitle=story.SUBTITLE)
    json.dump(tl, open(os.path.join(B, "timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # SRT
    def ts(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    with open(os.path.join(ROOT, "submission", "补图.srt"), "w", encoding="utf-8") as f:
        for i, s in enumerate([x for x in shots if x.get("sub")], 1):
            f.write(f"{i}\n{ts(s['sub_start'])} --> {ts(s['sub_end'])}\n" + "\n".join(s["sub"]) + "\n\n")

    # ASS（留档；成片里字幕是逐帧烧的，这份用来比对）
    with open(os.path.join(B, "subtitles.ass"), "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\n\n"
                "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,"
                "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV\n"
                "Style: CN,Noto Serif SC,46,&H00FFFFFF,&H00000000,1,3,1,2,120,120,72\n\n"
                "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
                % (story.W, story.H))
        for s in [x for x in shots if x.get("sub")]:
            a = ts(s["sub_start"])[:-4] + "." + ts(s["sub_start"])[-3:]
            b = ts(s["sub_end"])[:-4] + "." + ts(s["sub_end"])[-3:]
            body = "\\N".join(s["sub"])
            f.write("Dialogue: 0,%s,%s,CN,,0,0,0,,%s\n" % (a, b, body))

    # 分镜表
    with open(os.path.join(ROOT, "submission", "分镜表.md"), "w", encoding="utf-8") as f:
        f.write("# 《%s》分镜表\n\n总长 **%.1f 秒**（%d fps，%d×%d）\n\n"
                "| # | 入点 | 出点 | 时长 | 幕 | 画面 | 旁白 |\n| --- | --- | --- | --- | --- | --- | --- |\n"
                % (story.TITLE, total, story.FPS, story.W, story.H))
        for s in shots:
            f.write("| %s | %s | %s | %.1fs | %s | %s | %s |\n" % (
                s["id"], f"{int(s['start']//60)}:{s['start']%60:04.1f}",
                f"{int(s['end']//60)}:{s['end']%60:04.1f}", s["dur"],
                s.get("act") or "", s.get("note", ""),
                story.VO.get(s.get("vo"), "")))
    print("总长 %.2f 秒，%d 个镜头，%d 条字幕" % (total, len(shots), sum(1 for s in shots if s.get("sub"))))


if __name__ == "__main__":
    build()
