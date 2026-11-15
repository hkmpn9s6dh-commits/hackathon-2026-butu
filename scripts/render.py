# -*- coding: utf-8 -*-
"""逐帧渲染《补图》：裁切运镜 → 调色 → 颗粒/暗角 → 烧字 → 帧直接喂给 ffmpeg。"""
import json, os, subprocess, sys, math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story, texts

ROOT = story.ROOT
B = os.path.join(ROOT, "build")
W, H, FPS = story.W, story.H, story.FPS

FONT = os.path.join(ROOT, story.SUB_FONT)
GUARD_X, GUARD_Y = 0.905, 0.920      # 右下角留给工具水印，裁切永不进入

# ---------------------------------------------------------------- 基础工具
def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def font(size, weight="Regular"):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


_FONTS = {}
def F(size, weight="Regular"):
    k = (size, weight)
    if k not in _FONTS:
        _FONTS[k] = font(size, weight)
    return _FONTS[k]


def text_layer(lines, size, weight="Regular", color=(255, 255, 255), alpha=255,
               stroke=0, stroke_color=(0, 0, 0), spacing=14, tracking=0, align="center"):
    """渲染一块文字为 RGBA，返回 (PIL图, w, h)。多行左对齐拼接。"""
    f = F(size, weight)
    pad = stroke + 6
    widths, heights = [], []
    for ln in lines:
        b = f.getbbox(ln) if ln else (0, 0, 0, 0)
        widths.append(b[2] - b[0] + tracking * max(len(ln) - 1, 0))
        heights.append(size * 1.34)
    tw = int(max(widths) + pad * 2) if widths else 1
    th = int(sum(heights) + spacing * (len(lines) - 1) + pad * 2)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = pad
    for i, ln in enumerate(lines):
        if not ln:
            y += heights[i] + spacing
            continue
        b = f.getbbox(ln)
        w = b[2] - b[0] + tracking * max(len(ln) - 1, 0)
        x = pad if align == "left" else (tw - w) / 2 - b[0]
        cx = x
        for ch in ln:
            d.text((cx, y - b[1]), ch, font=f, fill=color + (alpha,),
                   stroke_width=stroke, stroke_fill=stroke_color + (alpha,))
            cx += f.getlength(ch) + tracking
        y += heights[i] + spacing
    return im


# ---------------------------------------------------------------- 画面板
class Clips:
    """图生视频片段：memmap 帧堆，按镜头时长拉伸播放（= 慢镜）。"""
    def __init__(self):
        self.cache = {}

    def frame(self, cid, tlocal, dur):
        if cid not in self.cache:
            self.cache[cid] = np.load(os.path.join(B, "clips", cid + ".npy"), mmap_mode="r")
        arr = self.cache[cid]
        n = arr.shape[0]
        p = min(max(tlocal / max(dur, 1e-3), 0.0), 1.0)
        i = min(int(round(p * (n - 1))), n - 1)
        f = np.asarray(arr[i]).astype(np.float32) / 255.0
        return cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4)


class Plates:
    def __init__(self):
        self.cache = {}

    def get(self, name):
        if name not in self.cache:
            path = os.path.join(ROOT, "plates", name)
            # cv2.imread 在中文路径上会失败，走 fromfile + imdecode
            buf = np.fromfile(path, dtype=np.uint8)
            bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if bgr is None:
                raise SystemExit("画面板缺失：" + path)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            self.cache[name] = rgb
        return self.cache[name]


def crop_rect(shape, zoom, panx, pany):
    """取景矩形（x1,y1,x2,y2）。右下角是工具水印区，永远不进。verify 会拿它做断言。"""
    ph, pw = shape[:2]
    gw, gh = int(pw * GUARD_X), int(ph * GUARD_Y)
    cw = gw / zoom
    ch = cw * 9 / 16
    if ch > gh:
        ch = gh / zoom if gh / zoom * 16 / 9 <= gw else gh
        cw = ch * 16 / 9
    cx = gw / 2 + panx * gw
    cy = gh / 2 + pany * gh
    x0 = min(max(cx - cw / 2, 0), gw - cw)
    y0 = min(max(cy - ch / 2, 0), gh - ch)
    x1, y1 = int(round(x0)), int(round(y0))
    x2, y2 = int(round(x0 + cw)), int(round(y0 + ch))
    return x1, y1, min(x2, gw), min(y2, gh)


def crop_to_frame(plate, zoom, panx, pany):
    """按 zoom/pan 取一块 16:9，放大到 1920×1080。永不碰右下角。"""
    x1, y1, x2, y2 = crop_rect(plate.shape, zoom, panx, pany)
    sub = plate[y1:y2, x1:x2]
    out = cv2.resize(sub, (W, H), interpolation=cv2.INTER_LANCZOS4)
    # 轻锐化：3×3 卷积（比两次高斯快一个量级），抵掉 1.3~1.4 倍插值的软
    return cv2.filter2D(out, -1, SHARPEN)


def apply_grade(img, preset, strength=1.0, flicker=1.0):
    """只做通道增益。饱和度那一步在 1080p 上要 130ms/帧，肉眼看不出来，砍掉。"""
    if preset == "neutral":
        return img
    g = GAINS[preset]
    out = img * g
    if preset == "fire":
        out = out * flicker
    return out


# ---------------------------------------------------------------- 全局贴图
def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx / W - 0.5) * 2
    ny = (yy / H - 0.5) * 2
    r = np.sqrt(nx ** 2 * 0.85 + ny ** 2)
    v = 1.0 - 0.30 * np.clip(r - 0.35, 0, None) ** 1.6
    return np.clip(v, 0.55, 1.0)[..., None]


def make_film(n=6):
    """颗粒与暗角预乘成一张「胶片层」：一帧只做一次乘法，省掉两次 25MB 运算。"""
    rng = np.random.default_rng(20261115)
    vig = make_vignette()
    return [((1.0 + rng.normal(0, 1, (H, W, 1)).astype(np.float32) * 0.011) * vig)
            for _ in range(n)]


GAINS = {"warm": np.array([1.035, 1.000, 0.938], np.float32),
         "cool": np.array([0.955, 0.995, 1.060], np.float32),
         "fire": np.array([1.075, 0.995, 0.885], np.float32),
         "neutral": np.array([1, 1, 1], np.float32)}
SHARPEN = np.array([[0, -0.18, 0], [-0.18, 1.72, -0.18], [0, -0.18, 0]], np.float32)
VIGNETTE = make_vignette()
FILM = make_film()
DITHER = (np.random.default_rng(5).uniform(-0.5, 0.5, (H, W, 3))).astype(np.float32)


# ---------------------------------------------------------------- HUD
class HUD:
    def __init__(self):
        self.cache = {}

    def subtitle(self, lines):
        key = ("sub", tuple(lines))
        if key not in self.cache:
            self.cache[key] = text_layer(lines, story.SUB_SIZE, "Medium",
                                         stroke=3, stroke_color=(0, 0, 0), spacing=10)
        return self.cache[key]

    def small(self, text, size=30, weight="Light", alpha=210, tracking=2):
        key = ("s", text, size, weight, alpha, tracking)
        if key not in self.cache:
            self.cache[key] = text_layer([text], size, weight, (255, 255, 255), alpha,
                                         stroke=2, stroke_color=(0, 0, 0), tracking=tracking)
        return self.cache[key]

    def badge(self):
        if "badge" not in self.cache:
            self.cache["badge"] = text_layer([story.BADGE], 22, "Light", (255, 255, 255),
                                             175, stroke=2, stroke_color=(0, 0, 0), tracking=0.5)
        return self.cache["badge"]


def paste(canvas_pil, layer, xy, opacity=1.0):
    if opacity <= 0.01:
        return
    if opacity < 0.999:
        a = layer.getchannel("A").point(lambda v: int(v * opacity))
        layer = layer.copy()
        layer.putalpha(a)
    canvas_pil.paste(layer, (int(round(xy[0])), int(round(xy[1]))), layer)


# ---------------------------------------------------------------- 卡片
def card_open(tl_time, dur):
    img = np.zeros((H, W, 3), np.float32)
    img[:] = 0.02
    pil = Image.fromarray((img * 255).astype(np.uint8))
    a = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t1 = text_layer(["南海子"], 62, "Light", (255, 255, 255), 235, tracking=16)
    t2 = text_layer(["一 七 七 七"], 30, "Light", (255, 255, 255), 150, tracking=6)
    fade = smooth((tl_time - 0.4) / 1.4) * smooth((dur - tl_time) / 0.9)
    paste(a, t1, ((W - t1.width) / 2, H * 0.44 - t1.height / 2), fade)
    paste(a, t2, ((W - t2.width) / 2, H * 0.44 + 64), fade * 0.9)
    pil = Image.alpha_composite(pil.convert("RGBA"), a).convert("RGB")
    return np.asarray(pil).astype(np.float32) / 255.0


def card_title(plates, tl_time, dur):
    back = plates.get("p02_silk_torn.png")
    img = crop_to_frame(back, 1.25, 0.0, 0.0)
    img = cv2.GaussianBlur(img, (0, 0), 7.0)
    img = np.clip(img * 0.42 + 0.03, 0, 1)
    pil = Image.fromarray((img * 255).astype(np.uint8))
    a = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fade = smooth(tl_time / 1.2) * smooth((dur - tl_time) / 1.0)
    t = text_layer([story.TITLE], 210, "SemiBold", (255, 255, 255), 242, tracking=26)
    paste(a, t, ((W - t.width) / 2, H * 0.36), fade)
    s = text_layer([story.SUBTITLE], 40, "Light", (255, 255, 255), 190, tracking=3)
    paste(a, s, ((W - s.width) / 2, H * 0.36 + t.height + 26), fade * smooth((tl_time - 0.9) / 1.2))
    pil = Image.alpha_composite(pil.convert("RGBA"), a).convert("RGB")
    return np.asarray(pil).astype(np.float32) / 255.0


def card_end(tl_time, dur):
    img = np.zeros((H, W, 3), np.float32) + 0.015
    pil = Image.fromarray((img * 255).astype(np.uint8))
    a = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fade = smooth((tl_time - 0.2) / 1.2) * smooth((dur - tl_time) / 1.0)
    y = H * 0.30
    lines = [(texts.END[0], 78, "SemiBold", 235, 18),
             (texts.END[1], 30, "Light", 175, 4),
             (texts.END[2], 24, "Light", 150, 1),
             (texts.END[3], 24, "Light", 130, 0.5),
             (texts.END[4], 24, "Light", 170, 2)]
    for i, (txt, sz, wt, al, tr) in enumerate(lines):
        lay = text_layer([txt], sz, wt, (255, 255, 255), al, tracking=tr)
        paste(a, lay, ((W - lay.width) / 2, y), fade)
        y += lay.height + (34 if i == 0 else 16)
    pil = Image.alpha_composite(pil.convert("RGBA"), a).convert("RGB")
    return np.asarray(pil).astype(np.float32) / 255.0


# ---------------------------------------------------------------- 单帧
def blend_layer(img, ov):
    """只把文字层的包围盒混进画面，省掉整帧 RGBA 合成。"""
    bbox = ov.getbbox()
    if not bbox:
        return np.clip(img, 0, 1)
    x1, y1, x2, y2 = bbox
    x1, y1 = max(x1, 0), max(y1, 0)
    lay = np.asarray(ov.crop((x1, y1, x2, y2))).astype(np.float32) / 255.0
    a = lay[..., 3:4]
    base = img[y1:y2, x1:x2]
    img[y1:y2, x1:x2] = base * (1 - a) + lay[..., :3] * a
    return np.clip(img, 0, 1)


def shot_image(shot, tl, plates, tlocal, hud, clips=None):
    dur = shot["dur"]
    if shot.get("clip") and clips is not None:
        img = clips.frame(shot["clip"], tlocal, dur)
        preset, strength = (shot.get("grade") or ("neutral", 1.0))
        img = apply_grade(img, preset, strength)
        return finish_frame(img, shot, tl, tlocal, hud)
    kind = (shot.get("move") or ("push", 1.0, 1.0))[0]
    if kind == "push":
        _, z0, z1 = shot["move"]
        z = z0 + (z1 - z0) * ease_io(tlocal / max(dur, 0.001))
        panx = pany = 0.0
    else:
        _, (dx, dy), z = shot["move"]
        p = ease_io(tlocal / max(dur, 0.001)) - 0.5
        panx, pany = dx * p * 2, dy * p * 2
    img = crop_to_frame(plates.get(shot["plate"]), z, panx, pany)

    if shot.get("reveal"):          # 舆图从绢纹里「长」出来
        base = crop_to_frame(plates.get("p02_silk_torn.png"), z, panx, pany)
        a = smooth((tlocal - 0.15) / 2.2)
        edge = a * (W + 260) - 130
        xs = np.arange(W, dtype=np.float32)[None, :]
        m = np.clip((edge - xs) / 150.0, 0, 1)
        m = (m * m * (3 - 2 * m))[..., None]
        img = base * (1 - m) + img * m

    preset, strength = (shot.get("grade") or ("neutral", 1.0))
    fl = 1.0
    if preset == "fire":
        fl = 1.0 + 0.045 * math.sin(tlocal * 17.3) * math.sin(tlocal * 5.1)
    img = apply_grade(img, preset, strength, fl)
    return finish_frame(img, shot, tl, tlocal, hud)


def finish_frame(img, shot, tl, tlocal, hud):
    dur = shot["dur"]
    img = img * FILM[(int(tlocal * FPS) * 7) % len(FILM)]

    # ---- 字
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if shot.get("act"):
        act = hud.small(shot["act"], 32, "Medium", 215, tracking=4)
        fade = smooth(tlocal / 0.9) * smooth((dur - tlocal) / 0.9)
        paste(ov, act, (120, 92), fade)
    if shot.get("year"):
        yr = hud.small(shot["year"], 32, "Light", 165, tracking=6)
        fade = smooth(tlocal / 0.9) * smooth((dur - tlocal) / 0.9)
        paste(ov, yr, (W - 120 - yr.width, 92), fade)
    if shot.get("place"):
        pl = hud.small(shot["place"], 28, "Light", 150, tracking=2)
        fade = smooth((tlocal - 0.8) / 1.0) * smooth((dur - tlocal) / 0.8)
        paste(ov, pl, (120, H - 126), fade)
    if shot.get("sub"):
        if shot["sub_start"] - 0.05 <= tl <= shot["sub_end"]:
            sub = hud.subtitle(shot["sub"])
            a1 = smooth((tl - shot["sub_start"]) / 0.35)
            a2 = smooth((shot["sub_end"] - tl) / 0.35)
            paste(ov, sub, ((W - sub.width) / 2, story.SUB_Y - sub.height), min(a1, a2))

    badge = hud.badge()
    paste(ov, badge, (120, H - 64), 0.70)

    img = img + DITHER / 255.0
    return blend_layer(img, ov)


# ---------------------------------------------------------------- 总装
def build():
    tl = json.load(open(os.path.join(B, "timeline.json"), encoding="utf-8"))
    shots = tl["shots"]
    total = tl["total"]
    plates = Plates()
    clips = Clips()
    hud = HUD()

    # 转场参数：xfade 有重叠；dip 各自淡黑
    for i, s in enumerate(shots):
        s["_dip_in"] = s["trans_in"][1] / 2 if s["trans_in"][0] == "dip" else 0.0
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        s["_dip_out"] = 0.0
        if nxt and nxt["trans_in"][0] == "dip":
            s["_dip_out"] = nxt["trans_in"][1] / 2

    nframes = int(round(total * FPS))
    t_from, t_to = 0.0, total
    out = os.path.join(B, "video_silent.mp4")
    if len(sys.argv) >= 3:
        t_from, t_to = float(sys.argv[1]), float(sys.argv[2])
        if len(sys.argv) > 3:
            out = sys.argv[3]
        elif t_to - t_from < total:
            out = os.path.join(B, "seg.mp4")
    f0, f1 = int(round(t_from * FPS)), min(int(round(t_to * FPS)), nframes)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        t = fi / FPS
        active = [s for s in shots if s["start"] <= t < s["end"]]
        if not active:
            active = [shots[-1]]
        # 取画
        def render_one(s):
            tlocal = t - s["start"]
            if s.get("card") == "open":
                img = card_open(tlocal, s["dur"])
            elif s.get("card") == "title":
                img = card_title(plates, tlocal, s["dur"])
            elif s.get("card") == "end":
                img = card_end(tlocal, s["dur"])
            else:
                img = shot_image(s, t, plates, tlocal, hud, clips)
            if s["_dip_in"] > 0:
                img = img * smooth(tlocal / s["_dip_in"])
            if s["_dip_out"] > 0:
                img = img * smooth((s["dur"] - tlocal) / s["_dip_out"])
            return img

        if len(active) == 1:
            frame = render_one(active[0])
        else:
            a, b = active[0], active[-1]
            td = max(b["start"] - a["start"], 1e-3)
            overlap = max(a["end"] - b["start"], 1e-3)
            alpha = smooth((t - b["start"]) / overlap)
            frame = render_one(a) * (1 - alpha) + render_one(b) * alpha
        p.stdin.write((np.clip(frame, 0, 1) * 255).astype(np.uint8).tobytes())
        if (fi - f0) % 120 == 0:
            print(f"  {fi}/{f1}  {t:6.1f}s", flush=True)
    p.stdin.close()
    p.wait()
    if p.returncode != 0:
        raise SystemExit("ffmpeg 编码失败")
    print("视频（无音轨）：", os.path.join(B, "video_silent.mp4"))


if __name__ == "__main__":
    build()
