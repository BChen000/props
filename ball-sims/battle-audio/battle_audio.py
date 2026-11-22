"""battle-audio: the synthesized soundtrack kit of the Marble Pop ball-sim Shorts.

Everything is generated with numpy/scipy (no samples): chiptune loops (battle, suspense,
outro), a victory fanfare and the SFX set (roulette tick, ding, whoosh, sword shing, metal
clash, hit, KO boom, taiko, heartbeat, riser, pop, click, bell, drums).
Mix with add()/add_st() into float buffers, then master_and_write().
"""
import math
import os
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
RNG_SEED = 7
rng = np.random.default_rng(RNG_SEED)


def reset_rng(seed=RNG_SEED):
    """Re-seed the noise generator; call before building a soundtrack for repeatable output."""
    global rng
    rng = np.random.default_rng(seed)


# ---------------------------------------------------------------- primitives
def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_ad(n, a=0.004, d=0.2):
    t = np.arange(n) / SR
    e = np.exp(-t / d)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def adsr(n, a=0.005, d=0.08, s=0.6, r=0.05):
    e = np.full(n, s)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = max(1, min(na, n))
    e[:na] = np.linspace(0, 1, na)
    if nd > 0 and na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd)
    if nr > 0 and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def square(f, dur, harmonics=12):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for k in range(1, 2 * harmonics, 2):
        if k * f > 9000:
            break
        out += np.sin(2 * np.pi * k * f * t) / k
    return out * (4 / np.pi) * 0.5


def triangle(f, dur):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for i, k in enumerate(range(1, 16, 2)):
        if k * f > 9000:
            break
        out += ((-1) ** i) * np.sin(2 * np.pi * k * f * t) / (k * k)
    return out * (8 / np.pi ** 2)


def sweep_sine(f0, f1, dur, curve=3.0):
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-curve * t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph)


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def bandpass(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lowpass(x, f, order=2):
    sos = butter(order, f, btype="low", fs=SR, output="sos")
    return sosfilt(sos, x)


def highpass(x, f, order=2):
    sos = butter(order, f, btype="high", fs=SR, output="sos")
    return sosfilt(sos, x)


def slowdown(x, factor):
    """Play x slower/lower by `factor` (>1 = slower)."""
    n = int(len(x) * factor)
    return np.interp(np.arange(n) / factor, np.arange(len(x)), x)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------- instruments / sfx
def kick(vol=1.0):
    d = 0.22
    x = sweep_sine(160, 45, d, 6) * env_ad(int(d * SR), 0.001, 0.09)
    click = noise(0.006) * 0.4
    x[:len(click)] += click
    return x * vol


def snare(vol=1.0):
    d = 0.18
    n = highpass(noise(d), 1200) * env_ad(int(d * SR), 0.001, 0.05)
    tone_ = np.sin(2 * np.pi * 190 * t_axis(d)) * env_ad(int(d * SR), 0.001, 0.04)
    return (n * 0.8 + tone_ * 0.5) * vol


def hat(vol=1.0, open_=False):
    d = 0.12 if open_ else 0.04
    return highpass(noise(d), 7000) * env_ad(int(d * SR), 0.0005, 0.03 if open_ else 0.012) * vol


def crash(vol=1.0, dur=1.4):
    x = highpass(noise(dur), 4000) * env_ad(int(dur * SR), 0.002, 0.45)
    return x * vol


def tick(vol=1.0, f=2400):
    d = 0.035
    x = np.sin(2 * np.pi * f * t_axis(d)) * env_ad(int(d * SR), 0.0005, 0.008)
    x += bandpass(noise(d), 1500, 6000) * env_ad(int(d * SR), 0.0003, 0.004) * 0.6
    return x * vol


def ding(vol=1.0, f=1318.5, d=1.0):
    t = t_axis(d)
    x = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 2.0 * t)
         + 0.25 * np.sin(2 * np.pi * f * 3.01 * t)) * env_ad(len(t), 0.002, 0.35)
    return x * vol


def whoosh(dur=0.45, vol=1.0, lo=300, hi=3000):
    n = int(dur * SR)
    x = noise(dur)
    # sweep a band through the noise by crossfading two bands
    a = bandpass(x, lo, lo * 3)
    b = bandpass(x, hi / 3, hi)
    m = np.linspace(0, 1, n)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return (a * (1 - m) + b * m) * e * vol * 2.2


def metal(f0, dur, vol=1.0, partials=(1.0, 2.76, 5.40, 8.93, 13.34), taus=(0.35, 0.22, 0.12, 0.07, 0.05)):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for p, tau in zip(partials, taus):
        fr = f0 * p * (1 + rng.uniform(-0.01, 0.01))
        if fr > 16000:
            continue
        x += np.sin(2 * np.pi * fr * t + rng.uniform(0, 6)) * np.exp(-t / tau) / (1 + 0.3 * p)
    trans = bandpass(noise(0.02), 2000, 9000) * env_ad(int(0.02 * SR), 0.0003, 0.004)
    x[:len(trans)] += trans * 0.8
    return x * vol


def shing(vol=1.0):
    d = 0.8
    x = metal(1700, d, 0.8, taus=(0.5, 0.35, 0.2, 0.12, 0.08))
    sw = bandpass(noise(d), 3000, 11000) * env_ad(int(d * SR), 0.03, 0.18)
    return (x + sw * 0.7) * vol


def clash_sfx(big, vol=1.0):
    f0 = rng.uniform(780, 1050) if not big else rng.uniform(520, 640)
    d = 0.5 if big else 0.32
    x = metal(f0, d, 1.0, taus=(0.22, 0.14, 0.08, 0.05, 0.03) if not big else (0.35, 0.22, 0.12, 0.07, 0.05))
    return x * vol


def hit_sfx(big, vol=1.0):
    if big:
        d = 0.32
        th = sweep_sine(170, 42, d, 5) * env_ad(int(d * SR), 0.001, 0.12)
        sl = bandpass(noise(d), 600, 5000) * env_ad(int(d * SR), 0.001, 0.05)
        x = np.tanh(2.2 * (th * 1.0 + sl * 0.9))
    else:
        d = 0.18
        th = sweep_sine(260, 90, d, 6) * env_ad(int(d * SR), 0.001, 0.05)
        sl = bandpass(noise(d), 1500, 7000) * env_ad(int(d * SR), 0.001, 0.025)
        x = th * 0.8 + sl * 0.9
    return x * vol


def boom(vol=1.0, d=0.9):
    low = sweep_sine(110, 32, d, 4) * env_ad(int(d * SR), 0.002, 0.28)
    nz = lowpass(noise(d), 900) * env_ad(int(d * SR), 0.002, 0.22)
    crack = bandpass(noise(0.08), 1500, 8000) * env_ad(int(0.08 * SR), 0.0005, 0.02)
    x = np.tanh(1.8 * (low * 1.0 + nz * 1.2))
    x[:len(crack)] += crack * 0.6
    return x * vol


def pop(vol=1.0, f=900):
    d = 0.09
    x = sweep_sine(f * 1.8, f, d, 8) * env_ad(int(d * SR), 0.001, 0.03)
    return x * vol


def taiko(vol=1.0):
    d = 0.7
    x = sweep_sine(120, 55, d, 4) * env_ad(int(d * SR), 0.002, 0.2)
    x += lowpass(noise(d), 500) * env_ad(int(d * SR), 0.001, 0.05) * 0.6
    return np.tanh(1.5 * x) * vol


def heartbeat(vol=1.0):
    d = 0.5
    one = sweep_sine(70, 40, 0.18, 4) * env_ad(int(0.18 * SR), 0.003, 0.06)
    x = np.zeros(int(d * SR))
    x[:len(one)] += one
    k = int(0.2 * SR)
    x[k:k + len(one)] += one * 0.75
    return x * vol


def riser(dur, vol=1.0):
    n = int(dur * SR)
    x = noise(dur)
    seg = 8
    out = np.zeros(n)
    edges = np.linspace(0, n, seg + 1).astype(int)
    for s in range(seg):
        f = 300 * (12 ** (s / (seg - 1)))
        part = bandpass(x, f, min(f * 2.5, 18000))
        w = np.zeros(n)
        a, b = edges[s], edges[s + 1]
        w[a:b] = 1
        out += part * w
    e = np.linspace(0, 1, n) ** 2
    return out * e * vol * 2.0


def click(vol=1.0):
    d = 0.03
    x = np.sin(2 * np.pi * 3200 * t_axis(d)) * env_ad(int(d * SR), 0.0003, 0.005)
    x += highpass(noise(d), 3000) * env_ad(int(d * SR), 0.0002, 0.003)
    return x * vol


def bell_ring(vol=1.0):
    d = 1.2
    t = t_axis(d)
    x = np.zeros_like(t)
    for f, a, tau in ((1568, 1.0, 0.5), (2349, 0.5, 0.35), (3136, 0.3, 0.25), (4186, 0.2, 0.15)):
        x += a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
    # tremolo = ringing bell
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 9 * t)
    return x * vol


# ---------------------------------------------------------------- music
def note(inst, n, dur, vol):
    f = midi(n)
    if inst == "sq":
        x = square(f, dur, 10) * adsr(int(dur * SR), 0.004, 0.05, 0.55, 0.03)
    elif inst == "tri":
        x = triangle(f, dur) * adsr(int(dur * SR), 0.003, 0.06, 0.8, 0.03)
    elif inst == "pluck":
        x = square(f, dur, 6) * env_ad(int(dur * SR), 0.002, 0.09)
    else:
        raise ValueError(inst)
    return x * vol


def battle_music(dur, bpm=152):
    """Driving A-minor chiptune loop: bass + arp + drums (+ lead every other pass)."""
    out = np.zeros(int((dur + 1) * SR))
    beat = 60 / bpm
    s16 = beat / 4
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G
    lead = [76, 74, 72, 74, 76, 79, 76, 74, 72, 69, 72, 74, 72, 71, 67, 71]
    bar = 0
    t0 = 0.0
    while t0 < dur:
        root, chord = prog[bar % 4]
        # bass: 8ths, root/octave
        for k in range(8):
            t = t0 + k * 2 * s16
            n = root - 24 + (12 if k % 2 else 0)
            add(out, note("tri", n, 2 * s16 * 0.95, 0.42), t)
        # arp: 16ths
        pat = [0, 1, 2, 1, 0, 1, 2, 3]
        tones = chord + [chord[0] + 12]
        for k in range(16):
            t = t0 + k * s16
            n = tones[pat[k % 8]] + 12
            add(out, note("pluck", n, s16 * 0.9, 0.075), t)
        # lead on bars 4.. (every other 4-bar phrase)
        if (bar // 4) % 2 == 1:
            for k in range(4):
                n = lead[(bar % 4) * 4 + k]
                add(out, note("sq", n, beat * 0.92, 0.07), t0 + k * beat)
        # drums
        for k in range(4):
            tb = t0 + k * beat
            if k in (0, 2):
                add(out, kick(0.9), tb)
            if k in (1, 3):
                add(out, snare(0.5), tb)
            add(out, hat(0.22), tb)
            add(out, hat(0.32), tb + 2 * s16)
            if k == 3 and bar % 2 == 1:
                add(out, kick(0.7), tb + 2 * s16)
        if bar % 4 == 0:
            add(out, crash(0.18, 1.0), t0)
        bar += 1
        t0 += 4 * beat
    return out[:int(dur * SR)]


def suspense_music(dur, bpm=152):
    out = np.zeros(int((dur + 1) * SR))
    s8 = 60 / bpm / 2
    k = 0
    t = 0.0
    while t < dur:
        n = 33 if (k // 8) % 2 == 0 else 34
        add(out, note("tri", n + 12, s8 * 0.9, 0.38), t)
        if k % 2 == 1:
            add(out, hat(0.12), t)
        k += 1
        t += s8
    return out[:int(dur * SR)]


def fanfare():
    out = np.zeros(int(2.4 * SR))
    seq = [(72, 0.0, 0.13), (76, 0.13, 0.13), (79, 0.26, 0.13), (84, 0.39, 0.9)]
    for n, t, d in seq:
        add(out, note("sq", n, d, 0.16), t)
        add(out, note("sq", n + 0.08, d, 0.08), t)
    for n in (60, 64, 67, 72):
        add(out, note("tri", n, 1.2, 0.16), 0.39)
    add(out, crash(0.3, 1.6), 0.39)
    add(out, kick(0.9), 0.39)
    return out


def outro_loop(dur, bpm=118):
    out = np.zeros(int((dur + 1) * SR))
    beat = 60 / bpm
    prog = [(60, [60, 64, 67]), (57, [57, 60, 64]), (53, [53, 57, 60]), (55, [55, 59, 62])]  # C Am F G
    t0, bar = 0.0, 0
    while t0 < dur:
        root, chord = prog[bar % 4]
        for k in range(4):
            add(out, note("tri", root - 24, beat * 0.9, 0.3), t0 + k * beat)
            for j, n in enumerate(chord):
                add(out, note("pluck", n + 12, beat * 0.4, 0.05), t0 + k * beat + j * beat / 3)
        bar += 1
        t0 += 4 * beat
    return out[:int(dur * SR)]


# ---------------------------------------------------------------- mixing
def add(buf, x, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * gain


def add_st(L, Rr, x, t, gain=1.0, pan=0.0):
    pan = max(-1.0, min(1.0, pan))
    gl = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    gr = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    add(L, x, t, gain * gl)
    add(Rr, x, t, gain * gr)



# ---------------------------------------------------------------- mastering / export
def master_and_write(L, Rr, out_path, drive=1.25, ceiling=0.92, end_fade=0.4):
    """Peak-normalise, soft-clip with tanh, fade the last `end_fade` s, write 16-bit stereo WAV."""
    st = np.stack([L, Rr], axis=1)
    peak = np.max(np.abs(st))
    st = st / peak * drive
    st = np.tanh(st) * ceiling
    ef = int(end_fade * SR)
    st[-ef:] *= np.linspace(1, 0, ef)[:, None]
    write_wav(out_path, st)
    return st


def write_wav(path, x):
    """x: float array (n,) mono or (n, 2) stereo in [-1, 1]."""
    x = np.asarray(x)
    ch = 1 if x.ndim == 1 else x.shape[1]
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def sfx_bank():
    """name -> (generator, description). Volumes as used in the Sword Roulette mix."""
    return {
        "tick": (lambda: tick(0.55, 2200), "roulette needle passing a ball"),
        "ding": (lambda: ding(0.55), "roulette stops"),
        "whoosh": (lambda: whoosh(0.5, 0.6, 400, 5000), "sword flies to the chosen ball"),
        "shing": (lambda: shing(0.6), "sword attaches (metal ring + air)"),
        "pop": (lambda: pop(0.35, 700), "small sword pops on / UI pop"),
        "taiko": (lambda: taiko(0.9), "FIGHT! / FINAL DUEL! hit"),
        "crash": (lambda: crash(0.35, 1.6), "cymbal crash"),
        "clash_small": (lambda: clash_sfx(False, 0.3), "two small swords clash"),
        "clash_big": (lambda: clash_sfx(True, 0.42), "a clash involving the BIG sword"),
        "hit_small": (lambda: hit_sfx(False, 0.6), "small sword hits a ball"),
        "hit_big": (lambda: hit_sfx(True, 0.85), "BIG sword hits a ball"),
        "boom": (lambda: boom(0.75, 0.9), "ball knocked out"),
        "boom_final": (lambda: boom(1.0, 1.4), "final knockout"),
        "heartbeat": (lambda: heartbeat(0.55), "slow-mo heartbeat (repeat every 0.75 s)"),
        "riser": (lambda: riser(3.0, 0.22), "slow-mo build-up (set length to the slow-mo)"),
        "click": (lambda: click(0.6), "cursor clicks SUBSCRIBE"),
        "bell": (lambda: bell_ring(0.35), "notification bell after the click"),
        "kick": (lambda: kick(0.9), "drum kick"),
        "snare": (lambda: snare(0.5), "drum snare"),
        "hat": (lambda: hat(0.3), "closed hi-hat"),
    }


def music_bank():
    beat = 60 / 152
    return {
        "battle_loop": (lambda: battle_music(16 * beat), "A-minor battle loop, 152 BPM, 4 bars (cut at the bar line)"),
        "battle_loop_lead": (lambda: battle_music(32 * beat)[int(16 * beat * SR):],
                             "same loop, phrase 2 with square lead"),
        "suspense_loop": (lambda: suspense_music(16 * 60 / 152 / 2), "roulette suspense pulse, 152 BPM"),
        "outro_loop": (lambda: outro_loop(16 * 60 / 118), "C-major outro, 118 BPM, 4 bars"),
        "fanfare": (fanfare, "victory fanfare (winner reveal)"),
    }


def export_assets(folder):
    os.makedirs(folder, exist_ok=True)
    reset_rng()
    rows = []
    for name, (gen, desc) in list(sfx_bank().items()) + list(music_bank().items()):
        x = gen()
        peak = np.max(np.abs(x)) or 1.0
        if peak > 0.99:
            x = x / peak * 0.99
        write_wav(os.path.join(folder, name + ".wav"), x)
        rows.append((name, desc, len(x) / SR))
    return rows


def preview(path):
    import cairo
    reset_rng()
    items = list(sfx_bank().items()) + list(music_bank().items())
    W_, row = 1080, 54
    H_ = 90 + row * len(items)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W_, H_)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H_)
    g.add_color_stop_rgb(0, 30 / 255, 12 / 255, 51 / 255)
    g.add_color_stop_rgb(1, 9 / 255, 4 / 255, 20 / 255)
    ctx.set_source(g)
    ctx.paint()
    ctx.select_font_face("Poppins ExtraBold")
    ctx.set_font_size(40)
    ctx.set_source_rgb(251 / 255, 127 / 255, 211 / 255)
    ctx.move_to(30, 58)
    ctx.show_text("BATTLE AUDIO")
    for k, (name, (gen, desc)) in enumerate(items):
        x = gen()
        y0 = 90 + k * row
        ctx.select_font_face("Poppins", 0, 1)
        ctx.set_font_size(19)
        ctx.set_source_rgb(1, 1, 1)
        ctx.move_to(30, y0 + 22)
        ctx.show_text(name)
        ctx.select_font_face("Poppins", 0, 0)
        ctx.set_font_size(14)
        ctx.set_source_rgb(0.85, 0.8, 0.95)
        ctx.move_to(30, y0 + 42)
        ctx.show_text("%.2f s  %s" % (len(x) / SR, desc[:58]))
        wx0, ww = 520, 530
        mid = y0 + row / 2 - 2
        n = len(x)
        step = max(1, n // ww)
        peak = np.max(np.abs(x)) or 1.0
        ctx.set_source_rgb(155 / 255, 217 / 255, 251 / 255)
        ctx.set_line_width(1)
        for i in range(ww):
            seg = x[i * step:(i + 1) * step]
            if len(seg) == 0:
                break
            a = float(np.max(np.abs(seg))) / peak * (row / 2 - 6)
            ctx.move_to(wx0 + i + 0.5, mid - a)
            ctx.line_to(wx0 + i + 0.5, mid + a)
        ctx.stroke()
    surf.write_to_png(path)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    rows = export_assets(os.path.join(here, "assets"))
    preview(os.path.join(here, "preview.png"))
    for name, desc, d in rows:
        print(f"{name:18s} {d:5.2f}s  {desc}")
