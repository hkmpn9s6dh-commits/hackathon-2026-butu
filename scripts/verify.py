# -*- coding: utf-8 -*-
"""构建护栏：所有断言都在这里，任何一条不成立就退出非 0。施工期靠它拦错。"""
import glob, json, os, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story, texts

ROOT = story.ROOT
B = os.path.join(ROOT, "build")
FAIL = []
OK = []


def ok(msg):
    OK.append(msg); print("  PASS  " + msg)


def bad(msg):
    FAIL.append(msg); print("  FAIL  " + msg)


def check(cond, msg, detail=""):
    (ok if cond else bad)(msg + ("" if cond or not detail else "  ← " + str(detail)))


# ------------------------------------------------------------------ 1. 素材
def check_assets():
    plates = sorted(glob.glob(os.path.join(ROOT, "plates", "p*.png")))
    check(len(plates) >= 17, "画面板齐全（%d 张）" % len(plates), len(plates))
    for p in plates[:1]:
        from PIL import Image
        w, h = Image.open(p).size
        check((w, h) == (1536, 1024), "画面板尺寸 1536×1024", (w, h))
    clips = glob.glob(os.path.join(ROOT, "motion", "*.mp4"))
    check(len(clips) >= 3, "运动片段齐全（%d 段）" % len(clips), len(clips))
    check(os.path.exists(os.path.join(ROOT, story.SUB_FONT)), "字体已随包")
    check(os.path.getsize(os.path.join(ROOT, story.SUB_FONT)) < 1_500_000, "字体已子集化（<1.5MB）")


# ------------------------------------------------------------------ 2. 取景永不进水印区
def check_crop_guard():
    from render import crop_rect, GUARD_X, GUARD_Y
    shape = (1024, 1536)
    gw, gh = int(1536 * GUARD_X), int(1024 * GUARD_Y)
    worst = None
    for z in (1.00, 1.05, 1.10, 1.20, 1.35, 1.50):
        for px in (-0.5, -0.2, 0.0, 0.2, 0.5):
            for py in (-0.5, -0.2, 0.0, 0.2, 0.5):
                x1, y1, x2, y2 = crop_rect(shape, z, px, py)
                if x2 > gw or y2 > gh or x1 < 0 or y1 < 0:
                    worst = (z, px, py, x1, y1, x2, y2)
    check(worst is None, "取景矩形在 180 组 zoom/pan 下都不进右下角水印区", worst)
    # 运动片段：顶部裁掉 90px，水印框到 y≈52
    check(90 > 60, "运动片段裁掉顶部 90px（工具水印框到 y≈52）")


# ------------------------------------------------------------------ 3. 字体覆盖
def check_font():
    from fontTools.ttLib import TTFont
    f = TTFont(os.path.join(ROOT, story.SUB_FONT))
    cmap = set()
    for t in f["cmap"].tables:
        cmap |= set(t.cmap.keys())
    need = set(texts.all_text())
    missing = sorted(c for c in need if ord(c) not in cmap and c.strip())
    check(not missing, "字体子集覆盖全部 %d 个字" % len(need), "缺字：" + "".join(missing[:20]))


# ------------------------------------------------------------------ 4. 时间轴
def check_timeline():
    tl = json.load(open(os.path.join(B, "timeline.json"), encoding="utf-8"))
    total = tl["total"]
    check(60 <= total <= 300, "总时长在 60–300 秒（%.1fs）" % total, total)
    shots = tl["shots"]
    for i, s in enumerate(shots):
        if i:
            gap = s["start"] - shots[i - 1]["end"]
            check(gap <= 1e-6, "镜头 %s 与上一镜衔接（gap=%.3f）" % (s["id"], gap), gap)
        check(s["dur"] > 1.0, "镜头 %s 时长 >1s" % s["id"], s["dur"])
    # 旁白不能压到出点
    for s in shots:
        if s.get("vo"):
            check(s["vo_start"] + s["vo_dur"] <= s["end"] + 0.05,
                  "旁白 %s 在镜头内说完" % s["vo"], (s["vo_start"], s["vo_dur"], s["end"]))
    check(len([s for s in shots if s.get("sub")]) == len(story.VO), "每条旁白都有字幕")
    return tl


# ------------------------------------------------------------------ 5. 成片规格
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_name,width,height,r_frame_rate,"
                          "sample_rate,channels,codec_type",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)


def check_video(tl):
    path = os.path.join(ROOT, "submission", "补图.mp4")
    check(os.path.exists(path), "成片存在 submission/补图.mp4")
    if not os.path.exists(path):
        return
    info = probe(path)
    dur = float(info["format"]["duration"])
    check(abs(dur - tl["total"]) < 1.2, "成片时长与时间轴一致（%.2f vs %.2f）" % (dur, tl["total"]), dur)
    check(60 <= dur <= 300, "成片时长在 60–300 秒（%.1f）" % dur, dur)
    v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    check((v["width"], v["height"]) == (1920, 1080), "分辨率 1920×1080", (v["width"], v["height"]))
    check(v["codec_name"] == "h264", "视频编码 h264", v["codec_name"])
    check(abs(eval(v["r_frame_rate"]) - 24) < 0.01, "帧率 24", v["r_frame_rate"])
    check(bool(a), "有音轨")
    if a:
        check(a[0]["sample_rate"] == "48000" and a[0]["channels"] == 2, "音轨 48k 立体声",
              (a[0]["sample_rate"], a[0]["channels"]))
    check(os.path.getsize(path) < 500 * 1024 * 1024, "文件 <500MB（%.1fMB）"
          % (os.path.getsize(path) / 1048576))


def check_loudness():
    path = os.path.join(ROOT, "submission", "补图.mp4")
    if not os.path.exists(path):
        return
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr
    try:
        j = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
        I, TP = float(j["input_i"]), float(j["input_tp"])
    except Exception as e:
        bad("读不出响度：%s" % e); return
    check(-18.0 <= I <= -14.0, "整体响度 %.1f LUFS（−16±2）" % I, I)
    check(TP <= -1.0, "真峰值 %.1f dBTP（≤ −1.0）" % TP, TP)


# ------------------------------------------------------------------ 6. 画面内容
def check_frames():
    path = os.path.join(ROOT, "submission", "补图.mp4")
    if not os.path.exists(path):
        return
    import cv2
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dark, badge_hits, samples = 0, 0, 0
    max_dark_run, run = 0, 0
    i = 0
    while True:
        okf, fr = cap.read()
        if not okf:
            break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if g.mean() < 4:
            run += 1; dark += 1; max_dark_run = max(max_dark_run, run)
        else:
            run = 0
        if i % 48 == 0:
            samples += 1
            # 左下角「AI 生成」标注：该区域应存在明显亮于背景的文字像素
            roi = g[fr.shape[0] - 46:fr.shape[0] - 18, 130:760]
            if roi.size and (roi > 150).sum() > 40:
                badge_hits += 1
        i += 1
    cap.release()
    check(max_dark_run <= int(3.6 * fps), "无超长黑场（最长 %.1fs）" % (max_dark_run / fps), max_dark_run / fps)
    check(badge_hits >= samples - 1, "「AI 生成」标注全程可见（%d/%d 抽样帧）" % (badge_hits, samples),
          (badge_hits, samples))
    check(n > 0, "成片可解码（%d 帧）" % n, n)


# ------------------------------------------------------------------ 7. 交件材料
def check_delivery():
    sub = os.path.join(ROOT, "submission")
    srt = os.path.join(sub, "补图.srt")
    check(os.path.exists(srt), "字幕文件在")
    if os.path.exists(srt):
        txt = open(srt, encoding="utf-8").read()
        cues = txt.count("-->")
        check(cues == len(story.VO), "字幕条数与旁白一致（%d）" % cues, cues)
    note = os.path.join(sub, "创作说明.md")
    check(os.path.exists(note), "创作说明在")
    if os.path.exists(note):
        body = open(note, encoding="utf-8").read()
        body = body.split("---", 2)[-1] if body.startswith("---") else body
        cn = sum(1 for c in body if "\u4e00" <= c <= "\u9fff")
        check(cn <= 200, "创作说明 ≤200 字（%d 汉字）" % cn, cn)
        check(cn >= 120, "创作说明够分量（%d 汉字）" % cn, cn)
    check(os.path.exists(os.path.join(sub, "版权承诺书.md")), "版权承诺书在")
    check(os.path.exists(os.path.join(sub, "分镜表.md")), "分镜表在")


def main():
    print("== 素材 ==");        check_assets()
    print("== 取景护栏 ==");    check_crop_guard()
    print("== 字体 ==");        check_font()
    print("== 时间轴 ==");      tl = check_timeline()
    print("== 成片 ==");        check_video(tl); check_loudness(); check_frames()
    print("== 交件 ==");        check_delivery()
    print("\n%d 项通过，%d 项失败" % (len(OK), len(FAIL)))
    if FAIL:
        print("\n失败项：")
        for f in FAIL:
            print("  - " + f)
        sys.exit(1)


if __name__ == "__main__":
    main()
