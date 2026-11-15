# -*- coding: utf-8 -*-
"""《补图》唯一事实来源：分镜、旁白、字幕、调色。render / timeline / audio 都读这一份。

修改片子只改这里，别去改生成出来的 build/ 文件。
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1920, 1080, 24
SR = 48000

TITLE = "补图"
SUBTITLE = "南海子 · 一七七七 — 二〇八〇"

# 旁白：id -> 文本。合成后按实测时长排时间轴（先量长度，再定时长）
VO = {
    "vo1": "一七七七年，这张图落了最后一笔。画它，用了五年。",
    "vo2": "图上没有画光。光是自己来的。",
    "vo3": "南海子，方一百六十里。墙有九门，门里是水，水里是宫。",
    "vo4": "璇源、涵道、清怀、漪鉴——八个景，各有各的名字。",
    "vo5": "一九〇〇年，火从纸上烧过去。",
    "vo6": "鹿走得更早。一八九四年，永定河冲开围墙；六年之后，南海子再没有一只麋鹿。",
    "vo7": "一九八五年八月二十四日，二十只麋鹿从英国飞回南海子。图，从另一面重新起笔。",
    "vo8": "四十年后，一万四千只，九十二处栖息地。",
    "vo9": "这张图没画完。所以它还在长。",
    "vo10": "八景之外，还有六百零三间房。",
}

# 分镜：(id, 画面板, 最短时长s, 运镜, 调色, 幕标, 地点标, 旁白[, 额外参数])
# 运镜  move=(kind, z0, z1) / pan 用 (dx, dy) 相对位移（占画面比例）
SHOTS = [
    dict(id="s01", plate=None, dur=3.0, card="open",
         note="黑场起：南海子 · 一七七七。"),
    dict(id="s02", plate="p01_silk_lamp.png", dur=6.0, act="一 · 起图",
         move=("push", 1.00, 1.07), grade=("cool", 0.95), vo="vo1",
         note="油灯下一张空白的绢——图还没画。"),
    dict(id="s03", plate="p02_silk_torn.png", dur=5.0, act=None,
         move=("push", 1.14, 1.02), grade=("warm", 1.0), vo="vo2",
         note="缝里的光斑：光是自己来的。"),
    dict(id="s04", plate="p03_map.png", dur=6.0, act="二 · 落墨", year="一七七七",
         move=("push", 1.02, 1.10), grade=("warm", 1.05), vo="vo3", reveal=True,
         note="舆图全貌：方一百六十里、九门、水、宫。"),
    dict(id="s05", plate="p04_palace_aerial.png", dur=5.0, act=None,
         move=("push", 1.00, 1.08), grade=("warm", 1.0), vo="vo4",
         note="团河行宫鸟瞰，葫芦形水系。"),
    dict(id="s06", plate="p05_hall_front.png", dur=5.5, act=None,
         move=("pan", (0.03, 0.0), 1.03), grade=("warm", 1.02),
         note="正殿立面：重檐、丹陛、院落。"),
    dict(id="s07", plate="p06_hall_rear.png", dur=5.5, act=None, vo="vo10",
         move=("push", 1.12, 1.02), grade=("warm", 1.0),
         note="后寝院落：前堂后寝、抄手游廊。"),
    dict(id="s08", plate="p07_pavilion.png", dur=5.5, act=None,
         move=("pan", (-0.025, 0.0), 1.05), grade=("warm", 1.0), place="团河行宫 八景",
         note="湖心敞轩，水与倒影。"),
    dict(id="s09", plate="p08_deer_herd.png", dur=8.5, act=None,
         move=("push", 1.00, 1.09), grade=("warm", 1.0),
         note="猎苑里的麋鹿群——图上有活物。"),
    dict(id="s10", plate="p09_fire.png", clip="fire", dur=6.0, act="三 · 断墨", year="一九〇〇",
         move=("push", 1.00, 1.12), grade=("fire", 1.0), vo="vo5",
         note="火从纸上烧过去。"),
    dict(id="s11", plate="p10_stele.png", dur=7.0, act=None,
         move=("push", 1.03, 1.12), grade=("cool", 0.9), vo="vo6", place="德寿寺 双碑",
         note="只剩两座碑。鹿也没有了。"),
    dict(id="s12", plate="p11_snow.png", dur=5.5, act=None,
         move=("push", 1.00, 1.06), grade=("cool", 0.85),
         note="雪地空栏：这一格是空的。"),
    dict(id="s13", plate="p12_today.png", dur=6.0, act="四 · 另起", year="一九八五",
         move=("push", 1.10, 1.00), grade=("neutral", 1.0), vo="vo7", place="团河行宫 遗址",
         note="今天的遗址公园与葫芦湖。"),
    dict(id="s14", plate="p13_deer_backlit.png", clip="deer", dur=7.0, act=None,
         move=("push", 1.00, 1.08), grade=("warm", 1.02), vo="vo8", place="南海子 麋鹿苑",
         note="鹿回来了。"),
    dict(id="s15", plate="p14_runway.png", dur=8.5, act=None,
         move=("push", 1.00, 1.10), grade=("cool", 0.95),
         note="跑道灯：新城在图的另一侧。"),
    dict(id="s16", plate="p15_brush.png", dur=8.5, act="五 · 留白", year="二〇八〇",
         move=("push", 1.06, 1.00), grade=("neutral", 1.0),
         note="笔尖悬在空白处。"),
    dict(id="s17", plate="p16_inkdrop.png", clip="ink", dur=5.0, act=None,
         move=("push", 1.00, 1.10), grade=("neutral", 0.95), sfx="ink",
         note="一滴墨落下。"),
    dict(id="s18", card="title", dur=8.0, act=None, vo="vo9", note="片名。"),
    dict(id="s19", card="end", dur=8.0, act=None, note="尾卡：创作说明与标注。"),
]

# 幕间转场：cut 硬切 / dip 黑场 / xfade 叠化
TRANS = {"default": ("xfade", 0.6), "s09|s10": ("dip", 1.0), "s12|s13": ("xfade", 1.2),
         "s15|s16": ("dip", 1.2), "s17|s18": ("xfade", 0.8), "s01|s02": ("xfade", 1.2)}

# 字幕（旁白）样式
SUB_FONT = "fonts/NotoSerifSC-sub.ttf"
SUB_SIZE = 46
SUB_Y = 962          # 基线 y
SUB_MAX = 18         # 每行最多字

BADGE = "AI 生成 · 画面由 AI 生成，音乐与音效为程序合成"
