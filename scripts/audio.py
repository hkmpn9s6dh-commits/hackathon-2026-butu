# -*- coding: utf-8 -*-
"""程序合成配乐与音效（无版权素材），按 timeline.json 落点，混旁白，出 48k 立体声。"""
import json, os, sys, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story

ROOT = story.ROOT
B = os.path.join(ROOT, "build")
SR = story.SR
RNG = np.random.default_rng(77)

# 五声音阶（D 羽调式）
NOTE = {"D3": 146.83, "F3": 174.61, "G3": 196.00, "A3": 220.00,
        "C4": 261.63, "D4": 293.66, "F4": 349.23, "G4": 392.00,
        "A4": 440.00, "D2": 73.42, "A2": 110.00}


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_adsr(n, a=0.01, d=0.1, s=0.7, r=0.3):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(n - a_n - d_n - r_n, 1)
    e = np.concatenate([
        np.linspace(0, 1, max(a_n, 1)),
        np.linspace(1, s, max(d_n, 1)),
        np.full(s_n, s),
        np.linspace(s, 0, max(r_n, 1))])
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]


def pluck(freq, dur, bright=0.55, decay=0.9965):
    """Karplus-Strong：古琴的拨弦感。"""
    n = int(dur * SR)
    p = max(int(SR / freq), 2)
    buf = RNG.uniform(-1, 1, p)
    # 揉一点初始亮度
    for _ in range(2):
        buf = 0.5 * (buf + np.roll(buf, 1)) * bright + buf * (1 - bright)
    out = np.zeros(n)
    idx = 0
    for i in range(n):
        v = buf[idx]
        out[i] = v
        nxt = (idx + 1) % p
        buf[idx] = decay * 0.5 * (v + buf[nxt])
        idx = nxt
    out *= env_adsr(n, a=0.002, d=0.25, s=0.55, r=min(1.2, dur * 0.5))
    return out


def xiao(freq, dur, amp=0.2):
    """箫/笛的长音：谐波 + 气声 + 慢颤音。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.0035 * np.sin(2 * np.pi * 4.3 * t) * np.clip(t / 1.5, 0, 1)
    ph = 2 * np.pi * freq * np.cumsum(vib) / SR
    x = np.zeros(n)
    for k, g in enumerate([1, 0.45, 0.28, 0.16, 0.09, 0.05], start=1):
        x += g * np.sin(ph * k) * np.exp(-0.06 * (k - 1))
    breath = RNG.normal(0, 1, n)
    b = np.convolve(breath, np.ones(24) / 24, mode="same")
    b = np.convolve(b, np.ones(24) / 24, mode="same")
    x = (x * 0.85 + b * 0.35) * env_adsr(n, a=0.9, d=0.4, s=0.85, r=min(1.4, dur * 0.4))
    return x / (np.max(np.abs(x)) + 1e-9) * amp


def drum(freq=55, dur=1.4, amp=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.5 * np.exp(-t * 18))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    tr = RNG.normal(0, 1, n) * np.exp(-t * 45)
    tr = np.convolve(tr, np.ones(6) / 6, mode="same")
    x = body * 0.9 + tr * 0.35
    return x / (np.max(np.abs(x)) + 1e-9) * amp


def noise_bed(dur, lo, hi, amp=0.06, mod=0.15, rate=0.07):
    """风/水：带通噪声 + 慢起伏。"""
    n = int(dur * SR)
    x = RNG.normal(0, 1, n)
    # 简易带通：两级一阶差分再做滑动平均
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    m = np.exp(-0.5 * ((np.log(freqs + 1) - np.log((lo + hi) / 2)) / 0.55) ** 2)
    x = np.fft.irfft(X * m, n=n)
    t = np.arange(n) / SR
    lfo = 1 + mod * np.sin(2 * np.pi * rate * t + RNG.uniform(0, 6))
    x = x / (np.max(np.abs(x)) + 1e-9) * amp * lfo
    return x


def crackle(dur, density=28, amp=0.16):
    n = int(dur * SR)
    out = np.zeros(n)
    cnt = int(density * dur)
    for _ in range(cnt):
        pos = RNG.integers(0, n - 400)
        ln = RNG.integers(60, 420)
        burst = RNG.normal(0, 1, ln) * np.exp(-np.arange(ln) / (ln * 0.25))
        burst = np.convolve(burst, np.ones(4) / 4, mode="same")
        out[pos:pos + ln] += burst * RNG.uniform(0.3, 1.0)
    out = out / (np.max(np.abs(out)) + 1e-9) * amp
    return out


def pad_low(freq, dur, amp=0.14):
    """低频铺底：几个谐波 + 缓慢呼吸，用在夜与火下面。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, g in enumerate([1, 0.35, 0.18, 0.08], start=1):
        x += g * np.sin(2 * np.pi * freq * k * t + RNG.uniform(0, 6))
    x *= 1 + 0.18 * np.sin(2 * np.pi * 0.07 * t)
    x *= env_adsr(n, a=1.6, d=0.5, s=0.9, r=min(2.0, dur * 0.4))
    return x / (np.max(np.abs(x)) + 1e-9) * amp


def plip(amp=0.3):
    """一滴墨落进水里/落在绢上的那一声。"""
    dur = 0.9
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 980 * np.exp(-t * 9) + 220
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    x += RNG.normal(0, 1, n) * np.exp(-t * 90) * 0.3
    return x / (np.max(np.abs(x)) + 1e-9) * amp


def _fftconv(x, h):
    """FFT 卷积。np.convolve 对 2 秒以上的 IR 是 O(n·m)，会把整个渲染拖死。"""
    n = len(x) + len(h) - 1
    N = 1 << int(np.ceil(math.log2(n)))
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(h, N), n=N)
    return y


def reverb(x, decay=2.2, mix=0.35, pre=0.02, seed=3):
    r = np.random.default_rng(seed)
    ir_n = int(decay * SR)
    ir = r.normal(0, 1, ir_n) * np.exp(-np.arange(ir_n) / (SR * decay / 3.2))
    ir[:int(pre * SR)] = 0
    ir = ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)
    wet = _fftconv(x, ir)[:len(x)]
    return x * (1 - mix) + wet * mix * 2.0


def place(track, x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= len(track):
        return
    n = min(len(x), len(track) - i)
    l = np.sqrt((1 - pan) / 2) * 1.414
    r = np.sqrt((1 + pan) / 2) * 1.414
    track[i:i + n, 0] += x[:n] * gain * l
    track[i:i + n, 1] += x[:n] * gain * r


def build():
    tl = json.load(open(os.path.join(B, "timeline.json"), encoding="utf-8"))
    shots = {s["id"]: s for s in tl["shots"]}
    total = tl["total"]
    n = int(total * SR) + SR
    L = np.zeros((n, 2))     # 音乐/音效总线
    V = np.zeros((n, 2))     # 旁白总线

    def at(sid, off=0.0):
        return shots[sid]["start"] + off

    # ---------- 底噪：风，全片；水声只在有水的镜头
    place(L, noise_bed(total, 260, 900, amp=0.045, mod=0.5, rate=0.05), 0)
    for sid in ("s04", "s05", "s07", "s08", "s13", "s15"):
        d = shots[sid]["dur"]
        place(L, noise_bed(d, 700, 2600, amp=0.022, mod=0.35, rate=0.11), at(sid))
    # 鸟：Act IV 两次
    for k, (sid, off) in enumerate([("s13", 3.4), ("s14", 2.2), ("s14", 5.1)]):
        d = 0.7
        t = t_axis(d)
        f = RNG.uniform(2400, 3300)
        chirp = np.sin(2 * np.pi * (f + 500 * np.sin(2 * np.pi * 9 * t)) * t) * \
            np.exp(-t * 6) * 0.05
        place(L, chirp, at(sid, off), 1.0, pan=RNG.uniform(-0.6, 0.6))

    # ---------- 古琴：按幕落弦
    cues = [("s02", 0.4, "D3", 4.5, 0.30), ("s02", 3.1, "A3", 4.0, 0.22),
            ("s03", 0.6, "F4", 3.6, 0.20), ("s04", 0.3, "D3", 5.0, 0.30),
            ("s04", 2.4, "A3", 4.2, 0.22), ("s05", 0.5, "G3", 4.2, 0.24),
            ("s06", 0.8, "D4", 3.4, 0.18), ("s07", 0.6, "F3", 4.0, 0.22),
            ("s08", 0.4, "A3", 4.4, 0.22), ("s08", 2.6, "C4", 3.6, 0.18),
            ("s09", 0.8, "D4", 4.6, 0.24), ("s09", 3.4, "F4", 4.0, 0.20),
            ("s13", 1.2, "G3", 4.4, 0.26), ("s13", 4.0, "D4", 4.0, 0.22),
            ("s14", 0.6, "A3", 4.6, 0.24), ("s14", 4.2, "C4", 4.0, 0.20),
            ("s16", 0.8, "D3", 5.5, 0.28), ("s18", 1.4, "D4", 5.0, 0.24),
            ("s18", 4.6, "A3", 5.0, 0.20)]
    for sid, off, nm, d, g in cues:
        x = reverb(pluck(NOTE[nm], d, bright=0.5), decay=2.6, mix=0.34)
        place(L, x, at(sid, off), g, pan=RNG.uniform(-0.25, 0.25))

    # ---------- 箫：Act II 与 Act IV 的长音
    for sid, off, nm, d, g in [("s05", 0.0, "D4", 6.0, 0.16), ("s06", 0.0, "A3", 7.5, 0.13),
                               ("s08", 0.0, "F4", 6.5, 0.12),
                               ("s13", 0.0, "D4", 8.0, 0.14), ("s14", 0.0, "A4", 7.0, 0.11),
                               ("s16", 0.0, "D4", 8.0, 0.12)]:
        x = reverb(xiao(NOTE[nm], d), decay=3.0, mix=0.4)
        place(L, x, at(sid, off), g, pan=0.1)

    # ---------- Act III：鼓、火
    for off, f, g in [(0.0, 58, 0.34), (0.55, 62, 0.20), (1.6, 52, 0.26), (3.1, 48, 0.19)]:
        place(L, drum(f, 1.6, g), at("s10", off))
    place(L, crackle(shots["s10"]["dur"], density=34, amp=0.085), at("s10", 0.1))
    place(L, drum(44, 2.4, 0.22), at("s11", 0.2))
    place(L, drum(40, 3.0, 0.16), at("s12", 0.1))

    # ---------- 低频铺底：火的下面、夜跑的下面
    place(L, pad_low(NOTE["D2"], shots["s10"]["dur"] + 1.0, 0.085), at("s10"))
    place(L, pad_low(NOTE["D2"], shots["s15"]["dur"] + 1.5, 0.055), at("s15"))
    place(L, pad_low(NOTE["A2"], shots["s16"]["dur"], 0.045), at("s16"))

    # ---------- Act V：墨滴
    place(L, reverb(plip(0.34), decay=1.6, mix=0.35), at("s17", 0.8))

    # ---------- 旁白
    for sid, s in shots.items():
        if s.get("vo"):
            mp3 = os.path.join(ROOT, tl["vo"][s["vo"]]["file"])
            wav = mp3.replace(".mp3", ".wav")
            if not os.path.exists(wav) or os.path.getmtime(wav) < os.path.getmtime(mp3):
                os.system('ffmpeg -y -v error -i "%s" -ar %d -ac 1 "%s"' % (mp3, SR, wav))
            import wave
            with wave.open(wav) as w:
                a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            a = np.concatenate([a, np.zeros(int(0.6 * SR))])
            place(V, reverb(a, decay=1.3, mix=0.16), s["vo_start"], 1.38)

    # ---------- 总线：旁白在说话时把音乐压下去 6 dB
    L = L[:int(total * SR)]
    V = V[:int(total * SR)]
    env = np.abs(V).mean(axis=1)
    k = int(0.12 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")       # 120ms 平滑
    env = np.convolve(env, np.ones(k) / k, mode="same")
    env = env / (np.max(env) + 1e-9)
    duck = 1.0 - 0.60 * np.clip(env * 4.5, 0, 1)
    L = L * duck[:, None] + V
    L -= np.mean(L, axis=0)
    peak = np.max(np.abs(L))
    L = L / (peak + 1e-9) * 0.92
    L = np.tanh(L * 1.15) / np.tanh(1.15) * 0.95     # 软限幅
    out = os.path.join(B, "mix.wav")
    import wave
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(L, -1, 1) * 32767).astype(np.int16).tobytes())
    print("混音完成：%s  %.1f 秒  峰值 %.2f" % (out, len(L) / SR, np.max(np.abs(L))))


if __name__ == "__main__":
    build()
