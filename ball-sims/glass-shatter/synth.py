"""Small numpy synth used by audio.py: envelopes, filtered noise, pops, glockenspiel notes, thumps and the music bed.
Shared with ../cloth-faces/audio.py."""
import math
import numpy as np
from scipy import signal

SR = 48000
FPS = 30
rng = np.random.default_rng(5)


def env_exp(n, tau, attack=0.002):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / tau)


def bandnoise(n, lo, hi, order=2):
    x = rng.standard_normal(n)
    sos = signal.butter(order, [lo, min(hi, SR / 2 - 100)], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lowpass(x, fc, order=2):
    sos = signal.butter(order, fc, btype='low', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def highpass(x, fc, order=2):
    sos = signal.butter(order, fc, btype='high', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def shaped_noise(n, frames_env, centers, widths):
    nper = 1024
    hop = 256
    x = rng.standard_normal(n + nper)
    f, t, Z = signal.stft(x, fs=SR, nperseg=nper, noverlap=nper - hop)
    ft = t * SR / (SR / FPS)
    fe = np.interp(ft, np.arange(len(frames_env)), frames_env)
    fc = np.interp(ft, np.arange(len(centers)), centers)
    fw = np.interp(ft, np.arange(len(widths)), widths)
    lf = np.log2(np.maximum(f, 20))[:, None]
    g = np.exp(-0.5 * ((lf - np.log2(fc)[None, :]) / fw[None, :]) ** 2)
    Z = Z * g * fe[None, :]
    _, y = signal.istft(Z, fs=SR, nperseg=nper, noverlap=nper - hop)
    y = y[:n]
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    return y


def pop(f0=660.0, dur=0.22):
    n = int(SR * dur)
    t = np.arange(n) / SR
    fr = f0 * (1 + 0.7 * (1 - np.exp(-t / 0.03)))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    y = np.sin(ph) * env_exp(n, 0.07, 0.001) + 0.35 * np.sin(2 * ph) * env_exp(n, 0.04, 0.001)
    click = bandnoise(n, 2000, 9000) * env_exp(n, 0.004, 0.0005) * 0.5
    return (y + click) * 0.55


def glock_note(midi, dur=1.4, amp=1.0):
    f = 440 * 2 ** ((midi - 69) / 12)
    n = int(SR * dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for r, a, d in ((1.0, 1.0, 0.9), (2.76, 0.35, 0.25), (5.40, 0.18, 0.09), (8.93, 0.08, 0.04)):
        if f * r < SR / 2 - 500:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d)
    y *= np.clip(t / 0.001, 0, 1)
    y += bandnoise(n, 3000, 12000) * env_exp(n, 0.003) * 0.15
    return y * amp


def thump(f0=70, dur=0.35, tau=0.09):
    n = int(SR * dur)
    t = np.arange(n) / SR
    fr = f0 * (1 + 1.2 * np.exp(-t / 0.015))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * env_exp(n, tau, 0.002)


def add(buf, x, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= buf.shape[0]:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), buf.shape[0] - i)
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    buf[i:i + n, 0] += x[:n] * gain * l * 1.414
    buf[i:i + n, 1] += x[:n] * gain * r * 1.414


def music(D, bars=12):
    bpm = bars * 4 * 60.0 / D
    beat = 60.0 / bpm
    n = int(SR * D)
    out = np.zeros((n, 2))
    prog = [(48, [60, 64, 67, 72]), (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69]), (43, [55, 59, 62, 67])]
    for b in range(bars):
        root, ch = prog[b % 4]
        t0 = b * 4 * beat
        for q in (0, 2, 3.5):
            if q == 3.5 and b % 2 == 0:
                continue
            m = root if q != 3.5 else root + 7
            f = 440 * 2 ** ((m - 69) / 12)
            L = int(SR * beat * (1.6 if q == 0 else 1.2))
            t = np.arange(L) / SR
            tri = signal.sawtooth(2 * np.pi * f * t, 0.5)
            x = lowpass(tri, 700) * env_exp(L, beat * 0.9, 0.01) * 0.55
            add(out, x, t0 + q * beat, 0.9, 0.0)
        pat = [0, 2, 1, 3, 2, 1, 3, 2]
        for e in range(8):
            m = ch[pat[e]] + 12
            x = glock_note(m, 0.9, 0.22) * np.exp(-np.arange(int(SR * 0.9)) / SR / 0.25)
            add(out, x, t0 + e * beat * 0.5, 0.55, -0.35 if e % 2 else 0.35)
        for q in range(4):
            if q in (0, 2):
                add(out, thump(58, 0.3, 0.07), t0 + q * beat, 0.5, 0.0)
            hh = highpass(rng.standard_normal(int(SR * 0.05)), 7000) * env_exp(int(SR * 0.05), 0.012, 0.0005)
            add(out, hh, t0 + (q + 0.5) * beat, 0.12, 0.2)
    head = int(SR * 0.004)
    out[:head] *= np.linspace(0, 1, head)[:, None]
    return out
