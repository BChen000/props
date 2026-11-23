"""battle-audio: the synthesized soundtrack kit of the Marble Pop ball-sim Shorts.

Everything is generated with numpy/scipy (no samples): chiptune loops (battle, suspense,
outro), a victory fanfare and the SFX set (roulette tick, ding, whoosh, sword shing, metal
clash, hit, KO boom, taiko, heartbeat, riser, pop, click, bell, drums).
From Ring Escape: marble clack, glass shatter, sweep-up, clap, brass stab, a B-major brass
fanfare, and the "In the Hall of the Mountain King" accelerando music (mountain_king()).
Mix with add()/add_st() into float buffers, then master_and_write(), then loudnorm_filter()
when you mux (two-pass ffmpeg loudnorm to -14 LUFS).
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


def gnoise(dur):
    """Gaussian noise (the Ring Escape sounds use it; it is about 1.7x louder than noise())."""
    return rng.standard_normal(int(dur * SR))


RISER_LEVEL = 3.31  # riser(3.0) has the same RMS as the old 8-step riser, so existing gains still fit


def riser(dur, vol=1.0, lo=250.0, hi=3500.0, steps=24, xfade=0.006):
    """Noise riser: a one-octave band [0.7 f, 1.4 f] climbs from lo to hi in `steps` log steps
    (about 1.9 semitones each with the defaults), cross-faded over `xfade` s so the steps don't click,
    swelling as (t/dur)^2.2. (Ring Escape's reverse whoosh; replaced the 8-step riser in Nov 2026.)"""
    n = int(dur * SR)
    x = noise(dur)
    out = np.zeros(n)
    edges = np.linspace(0, n, steps + 1).astype(int)
    xf = max(1, int(xfade * SR))
    idx = np.arange(n)
    for s in range(steps):
        f = lo * (hi / lo) ** (s / steps)
        y = bandpass(x, f * 0.7, min(f * 1.4, SR * 0.45))
        a, b = edges[s], edges[s + 1]
        w = np.ones(n)
        if s > 0:
            w *= np.clip((idx - (a - xf / 2)) / xf, 0, 1)
        if s < steps - 1:
            w *= np.clip(((b + xf / 2) - idx) / xf, 0, 1)
        out += y * w
    e = (idx / SR / dur) ** 2.2
    return out * e * vol * RISER_LEVEL


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


# ---------------------------------------------------------------- Ring Escape sounds (Nov 2026)
def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def clack(vol=1.0, f=3650.0):
    """Marble hits marble: two short partials (f, 1.47 f) and a noise tick, 60 ms."""
    d = 0.06
    t = t_axis(d)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012) + 0.6 * np.sin(2 * np.pi * f * 1.47 * t) * np.exp(-t / 0.008)
    x += 0.4 * highpass(gnoise(d), 4000) * np.exp(-t / 0.002)
    return x * vol


def shatter(vol=1.0, seed=103):
    """Glass ring breaking: bright noise burst, 26 random glass pings in the first 0.28 s, low thump."""
    r = np.random.default_rng(seed)
    d = 0.55
    t = t_axis(d)
    x = highpass(gnoise(d), 2500) * np.exp(-t / 0.09) * 0.5
    m = int(0.03 * SR)
    tt = np.arange(m) / SR
    for _ in range(26):
        i0 = int(r.uniform(0, 0.28) * SR)
        f = r.uniform(2500, 7500)
        x[i0:i0 + m] += 0.35 * np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.006) * r.uniform(0.4, 1.0)
    thump = np.sin(2 * np.pi * (60 + 80 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.09)
    return (x + 0.7 * thump) * vol


def sweep_up(dur=0.5, vol=1.0, f0=300.0, f1=1300.0):
    """Tonal power-up glide (speed-up cue, fills): exponential pitch rise with a 2nd harmonic."""
    t = t_axis(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.sin(np.pi * t / dur) ** 0.7 * vol


def clap(vol=1.0):
    """Hand clap: band-passed noise with three quick bursts and a short tail."""
    d = 0.25
    t = t_axis(d)
    x = bandpass(gnoise(d), 900, 3800)
    e = np.exp(-t / 0.06)
    for dd in (0.0, 0.011, 0.022):
        e += 0.6 * (t >= dd) * np.exp(-np.clip(t - dd, 0, None) / 0.008)
    return x * e * 0.6 * vol


def saw_pluck(n, dur, vol=1.0, bright=1.0):
    """Staccato synth lead (saw + square, low-passed). bright 0..1 opens the filter. Rings 0.25 s past dur."""
    m = int((dur + 0.25) * SR)
    f = midi(n)
    t = np.arange(m) / SR
    x = 0.6 * saw(f, m) + 0.4 * np.sign(np.sin(2 * np.pi * f * t)) * 0.6 + 0.3 * saw(f * 1.004, m, 0.3)
    x = lowpass(x, 900 + 2600 * bright)
    e = np.minimum(1, t / 0.004) * np.exp(-t / (0.09 + 0.25 * dur))
    rel = np.clip((dur - t) / 0.03 + 1, 0, 1)
    return x * e * rel * vol


def bass_pluck(n, dur, vol=1.0):
    """Round staccato bass: sine + 2nd harmonic + a little low-passed saw."""
    m = int((dur + 0.2) * SR)
    f = midi(n)
    t = np.arange(m) / SR
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.25 * lowpass(saw(f, m), 700)
    e = np.minimum(1, t / 0.005) * np.exp(-t / 0.16)
    rel = np.clip((dur - t) / 0.03 + 1, 0, 1)
    return x * e * rel * vol


def brass_chord(notes, dur, vol=1.0):
    """Brass stab/pad: 3 detuned saws per MIDI note, low-passed at 2.4 kHz, slow decay."""
    t = t_axis(dur)
    m = len(t)
    x = np.zeros(m)
    for n in notes:
        f = midi(n)
        for det in (-0.004, 0.0, 0.005):
            x += saw(f * (1 + det), m, rng.random())
    x = lowpass(x, 2400)
    e = np.minimum(1, t / 0.03) * np.exp(-t / (dur * 0.6))
    rel = np.clip((dur - t) / 0.15, 0, 1)
    return x * e * rel / (3 * len(notes)) * vol


def brass_fanfare(vol=1.0):
    """B-major win fanfare: quick B-D#-F#-B arpeggio with dings, then a held brass chord + bass + kick (2.2 s)."""
    out = np.zeros(int(2.2 * SR))
    for q, n in enumerate((71, 75, 78, 83)):
        add(out, saw_pluck(n, 0.11, 0.22, 1.0), 0.02 + 0.075 * q)
        add(out, ding(0.06, midi(n + 12), 0.5), 0.02 + 0.075 * q)
    add(out, brass_chord((59, 63, 66, 71, 75), 1.8, 0.9), 0.32)
    add(out, bass_pluck(47, 1.4, 0.35), 0.32)
    add(out, kick(0.55), 0.32)
    return out * vol


MK_A = [(59, 1), (61, 1), (62, 1), (64, 1), (66, 1), (62, 1), (66, 2), (65, 1), (61, 1), (65, 2), (64, 1), (60, 1),
        (64, 2), (59, 1), (61, 1), (62, 1), (64, 1), (66, 1), (62, 1), (66, 1), (71, 1), (69, 1), (66, 1), (62, 1),
        (66, 1), (69, 4)]
MK_B = [(66, 1), (68, 1), (70, 1), (71, 1), (73, 1), (70, 1), (73, 2), (74, 1), (70, 1), (74, 2), (73, 1), (70, 1),
        (73, 2), (66, 1), (68, 1), (70, 1), (71, 1), (73, 1), (70, 1), (73, 2), (74, 1), (70, 1), (74, 2), (73, 4)]
MOUNTAIN_KING = MK_A + MK_A + MK_B + MK_A + MK_A + MK_B  # (MIDI note, eighths), B minor


def mountain_king(L, Rr, tau_final, tau_slow, tau_cut, t0=0.0, bpm=(132, 168, 196), song=MOUNTAIN_KING):
    """Grieg's "In the Hall of the Mountain King" (1875, public domain), accelerating, into stereo buffers.

    Stage 1 (0 -> tau_final): bpm[0] -> bpm[1], kick on beats 1 and 3, clap on 2 and 4, hats on 8ths.
    Stage 2 (tau_final -> tau_slow): bpm[1] -> bpm[2], kick every beat, lead doubled an octave up.
    Stops at tau_cut. Clap fill + small sweep on every long note. Times are seconds after t0.
    """
    def tempo(tau):
        if tau < tau_final:
            return bpm[0] + (bpm[1] - bpm[0]) * (tau / tau_final)
        return bpm[1] + (bpm[2] - bpm[1]) * min(1.0, (tau - tau_final) / max(0.1, tau_slow - tau_final))

    taus = np.arange(0, tau_cut + 0.5, 0.001)
    beats = np.cumsum([tempo(x) / 60 * 0.001 for x in taus])

    def at(k):
        return float(np.interp(k / 2.0, beats, taus))

    pos = 0
    for n, d in song:
        ta, tb = at(pos), at(pos + d)
        if ta >= tau_cut:
            break
        length = (tb - ta) * (0.62 if d == 1 else 0.8)
        stage = 1 if ta < tau_final else 2
        add_st(L, Rr, saw_pluck(n, length, 1.0, 0.6 + 0.2 * stage), t0 + ta, 0.17 if stage == 1 else 0.2, -0.15)
        if stage == 2:
            add_st(L, Rr, saw_pluck(n + 12, length, 1.0, 0.8), t0 + ta, 0.07, 0.25)
        add_st(L, Rr, bass_pluck(n - 24, length), t0 + ta, 0.26)
        if d == 4:
            for q in range(4):
                tq = at(pos + 2 + q * 0.5)
                if tq < tau_cut:
                    add_st(L, Rr, clap(), t0 + tq, 0.07 + 0.04 * q, -0.1 + 0.07 * q)
            add_st(L, Rr, sweep_up(max(0.15, at(pos + 4) - at(pos + 2)), 1.0, 250, 900), t0 + at(pos + 2), 0.035)
        pos += d
    nb = int(beats[np.searchsorted(taus, tau_cut) - 1]) + 1
    for b in range(nb * 2):
        ta = at(b)
        if ta >= tau_cut:
            break
        stage = 1 if ta < tau_final else 2
        if b % 2 == 0:
            beat = b // 2
            if beat % 2 == 0 or stage == 2:
                add_st(L, Rr, kick(MK_KICK * (1.0 if stage == 1 else 1.19)), t0 + ta)
            if beat % 2 == 1:
                add_st(L, Rr, clap(), t0 + ta, 0.22, 0.1)
        add_st(L, Rr, hat(MK_HAT * (1.0 if stage == 1 else 1.33), open_=(b % 4 == 3)), t0 + ta, 1.0, 0.3)


MK_KICK, MK_HAT = 0.386, 0.101  # kick()/hat() volumes matching Ring Escape's original drum levels (RMS)


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
def limiter(st, thr, look=0.006, release=0.08):
    """Look-ahead peak limiter on an (n, 2) array: instant gain drop, `release` s recovery."""
    from scipy.ndimage import maximum_filter1d
    env = maximum_filter1d(np.abs(st).max(1), size=int(look * SR), origin=-int(look / 2 * SR))
    g = np.minimum(1.0, thr / np.maximum(env, 1e-9))
    a = math.exp(-1.0 / (release * SR))
    gs = np.empty_like(g)
    cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else a * cur + (1 - a) * g[i]
        gs[i] = cur
    return st * gs[:, None]


def master_and_write(L, Rr, out_path, drive=1.25, ceiling=0.92, end_fade=0.4, limit=None):
    """Peak-normalise, soft-clip with tanh, fade the last `end_fade` s, write 16-bit stereo WAV.

    limit: None, or a threshold as a fraction of the post-tanh peak (0.46 in both Shorts). The look-ahead
    limiter then trims the peaks so loudnorm_filter() can reach -14 LUFS with plain gain (linear mode).
    """
    st = np.stack([L, Rr], axis=1)
    peak = np.max(np.abs(st))
    st = st / peak * drive
    if limit is None:
        st = np.tanh(st) * ceiling
    else:
        st = np.tanh(st)
        st = limiter(st, limit * np.max(np.abs(st)))
        st = st / np.max(np.abs(st)) * ceiling
    ef = int(end_fade * SR)
    if ef > 0:
        st[-ef:] *= np.linspace(1, 0, ef)[:, None]
    write_wav(out_path, st)
    return st


def loudnorm_filter(wav_path, I=-14, TP=-1.0, LRA=11):
    """Measure wav_path with ffmpeg and return the second-pass loudnorm filter (linear gain).
    Use it when muxing:  ffmpeg -i video -i wav -af "<filter>" -ar 48000 -c:a aac -b:a 192k ..."""
    import json
    import subprocess
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav_path, "-af",
                          f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    j = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    return (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
            f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")


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


def _mountain_king_demo():
    L, Rr = np.zeros(int(16.5 * SR)), np.zeros(int(16.5 * SR))
    mountain_king(L, Rr, tau_final=11.0, tau_slow=15.8, tau_cut=16.0)
    return ((L + Rr) / 2)[:int(16.2 * SR)]


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


def ring_escape_bank():
    """Sounds added from Ring Escape (Nov 2026). Exported after the other banks, so the older
    files keep their exact noise when you re-export."""
    return {
        "clack": (lambda: clack(0.5), "marble hits marble (Ring Escape)"),
        "shatter": (lambda: shatter(0.6), "glass ring breaks (Ring Escape)"),
        "sweep_up": (lambda: sweep_up(0.5, 0.45, 300, 1400), "power-up glide: speed-up cue (Ring Escape)"),
        "clap": (lambda: clap(0.9), "hand clap (Ring Escape drums)"),
        "brass_stab": (lambda: brass_chord((47, 54, 59, 62), 1.1, 0.9), "B-minor brass stab: last ring (Ring Escape)"),
        "fanfare_brass": (brass_fanfare, "B-major brass fanfare (Ring Escape win)"),
        "mountain_king": (_mountain_king_demo, "Mountain King accelerando, 16 s demo (Ring Escape music)"),
    }


def export_assets(folder):
    os.makedirs(folder, exist_ok=True)
    reset_rng()
    rows = []
    for name, (gen, desc) in list(sfx_bank().items()) + list(music_bank().items()) + list(ring_escape_bank().items()):
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
    items = list(sfx_bank().items()) + list(music_bank().items()) + list(ring_escape_bank().items())
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
