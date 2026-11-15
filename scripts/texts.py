# -*- coding: utf-8 -*-
"""片子里所有会出现在画面上的字。字体子集按这里收字，漏一个字就会被 verify 抓到。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story

ACTS = ["一 · 起图", "二 · 落墨", "三 · 断墨", "四 · 另起", "五 · 留白"]
YEARS = ["一七七七", "一九〇〇", "一九八五", "二〇八〇"]
PLACES = ["团河行宫 八景", "德寿寺 双碑", "团河行宫 遗址", "南海子 麋鹿苑"]

OPEN = ["南海子", "一七七七", "一张图的三个时刻"]

END = [
    "补图",
    "南海子 · 一七七七 — 二〇八〇",
    "画面由 AI 生成（文生图 / 图生视频）· 音乐与音效为程序合成",
    "史料：<帝京景物略>·中华文史网<南苑>·国家林业和草原局麋鹿回归四十年",
    "2026「兴光」AIGC 短视频大赛 参赛作品",
]

# 片中所有地名/年份/幕标/字幕/角标，全部收进字体子集。
# 关键：幕标/年份/地点直接从 story.SHOTS 里取，不另立一份清单——
# 另立清单就会漏字（2026-11-15 实测：改了场景标注，字体子集里没有「斋翠润轩」，成片出现豆腐块）。
def all_text():
    parts = list(story.VO.values()) + ACTS + YEARS + PLACES + OPEN + END
    for sh in story.SHOTS:
        for k in ("act", "year", "place"):
            if sh.get(k):
                parts.append(sh[k])
    parts += [story.TITLE, story.SUBTITLE, story.BADGE]
    parts += ["0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"]
    parts += list("，。、；：？！「」『』《》〈〉（）—…·％%+-/0123456789 ")
    return "".join(parts)
