# 《补图》

> 2026「兴光」AIGC 短视频大赛参赛作品（北京大兴 · 南海子）
> 一张乾隆年间的南苑舆图被"补"了三次：一七七七年墨线长出行宫，一九〇〇年火把线烧断，
> 一九八五年麋鹿回到图上——最后一笔始终没落。**这张图没画完，所以它还在长。**
>
> ≈126 秒 ｜ 1920×1080 ｜ 24fps ｜ H.264 + AAC ｜ 中文字幕烧入 ｜ 左下角全程「AI 生成」标注

## 一、成品

| 东西 | 路径 |
| --- | --- |
| 成片 | `submission/补图.mp4` |
| 字幕 | `submission/补图.srt` |
| 创作说明（≤200 字） | `submission/创作说明.md` |
| 分镜表（自动生成） | `submission/分镜表.md` |
| 版权承诺书 | `submission/版权承诺书.md` |
| 复验 | `bash scripts/verify.sh` |

## 二、一条命令重建

```bash
bash scripts/build.sh        # 字体 → 旁白 → 时间轴 → 音频 → 逐帧渲染 → 混流 → 复验
```

单步：

```bash
py -3 scripts/mkfont.py      # 字体子集（只收片中用到的字）
py -3 scripts/vo.py          # edge-tts 合成 9 句旁白并量长度
py -3 scripts/timeline.py    # 按实测旁白排时间轴，出 srt / ass / 分镜表
py -3 scripts/audio.py       # 程序合成配乐、音效、混旁白（含 ducking）→ build/mix.wav
py -3 scripts/clips.py       # 图生视频片段裁掉顶部水印 → build/clips/*.npy
py -3 scripts/render.py      # 逐帧：裁切运镜 → 调色 → 颗粒 → 烧字 → ffmpeg
bash scripts/mux.sh          # 混流 + loudnorm
py -3 scripts/verify.py      # 全部断言
```

## 三、怎么做的（AI 在哪里）

- **画面**：17 幅 AI 生成画面板（文生图）+ 3 段图生视频（火、麋鹿、墨洇）。
  提示词全部记在 `plates/PROMPTS.md`。
- **不靠 AI 的部分**：运镜（裁切 + 缓动）、墨线揭示、调色、颗粒、暗角、全部字幕与标注、
  全部音乐与音效——都是代码，可复现、可改。
- **声音**：古琴用 Karplus-Strong 合成，箫用谐波 + 气声，鼓与低频铺底、火的噼啪、墨滴，全是 numpy 生成。
  旁白是 edge-tts（zh-CN-YunyangNeural，−8% 语速），先量长度再排时间轴。
- **字体**：Noto Serif SC（OFL 1.1）子集到 244 个字，233 KB，随包，不依赖系统字体。

## 四、目录

```
plates/       17 幅画面板 + PROMPTS.md（提示词存档）
motion/       3 段图生视频原始片段
scripts/      story.py 是唯一事实来源（分镜、旁白、调色都在里面）
build/        中间产物（字体子集、旁白、时间轴、混音、无音轨视频）
submission/   交件
proof/        闸 C 复验与闸 D 盲测记录
docs/         史料与做法
```

## 五、纪律

- 规则要求"未在其他平台发布过"：本片不部署、不公开，仓库私有。
- 画面、音乐、字体全部合规授权（AI 生成 / 程序合成 / OFL）。
- 不改 `build/` 里的文件——所有内容都由 `scripts/` 生成，改源头再重建。
