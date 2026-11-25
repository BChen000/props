"""Marble Funnel Drain soundtrack, synthesized from the simulation's own events (numpy + scipy, no samples).

- clicks: every marble-marble impact (modal steel ticks, louder for harder hits, a little louder in slow motion)
- knocks: marbles hitting the invisible walls (soft wood knocks)
- drops: each marble landing at the bottom of the hole (muffled clack with a low thump)
- rolling: filtered noise whose level follows the summed marble speed
- whooshes: under each quick camera move
- chimes: a bell as each coloured marble drops out (4th D5, 3rd B4, 2nd G4) and a C-major arpeggio for the winner
Seeded, so the WAV is the same every run.
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

import timeline as TL

SR = 48000
SEED = 42
CLICK_GAIN, KNOCK_GAIN, DROP_GAIN = 0.15, 0.09, 0.2
ROLL_LEVEL, WHOOSH_LEVEL = 0.05, 0.05
LOSER_BELLS = [392.0, 493.88, 587.33]           # 2nd, 3rd, 4th place out
WIN_ARPEGGIO = [523.25, 659.25, 783.99, 1046.5]


def make_audio(ep, out_wav):
    rng = np.random.default_rng(SEED)
    d = ep.d
    ev = d['ev']; RV = d['RV']; hz = ep.HZ
    dur = TL.NFR / TL.FPS
    n = int(dur * SR)
    L = np.zeros(n); Rr = np.zeros(n)

    def bp(x, lo, hi, order=2):
        return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)

    def hp(x, f, order=2):
        return sosfilt(butter(order, f, btype='high', fs=SR, output='sos'), x)

    def lp(x, f, order=2):
        return sosfilt(butter(order, f, btype='low', fs=SR, output='sos'), x)

    def modal(freqs, decays, amps, length):
        t = np.arange(length) / SR
        y = np.zeros(length)
        for f, dcy, a in zip(freqs, decays, amps):
            y += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / dcy)
        return y

    def bank(kind, k):
        out = []
        for _ in range(k):
            if kind == 'click':
                ln = int(0.03 * SR)
                y = modal(rng.uniform(2600, 7800, 3), rng.uniform(0.0025, 0.009, 3), rng.uniform(0.4, 1.0, 3), ln)
                nz = rng.normal(0, 1, ln) * np.exp(-np.arange(ln) / (0.0012 * SR))
                y += 0.8 * hp(nz, 2500)
                y *= np.minimum(1, np.arange(ln) / 6.0)
                y = lp(y, 11000, 4)
            elif kind == 'knock':
                ln = int(0.07 * SR)
                y = modal(rng.uniform(380, 950, 3), rng.uniform(0.008, 0.02, 3), rng.uniform(0.5, 1.0, 3), ln)
                nz = rng.normal(0, 1, ln) * np.exp(-np.arange(ln) / (0.003 * SR))
                y += 0.5 * bp(nz, 300, 2500)
                y *= np.minimum(1, np.arange(ln) / 10.0)
            else:
                ln = int(0.18 * SR)
                y = modal(rng.uniform(1400, 3600, 4), rng.uniform(0.01, 0.04, 4), rng.uniform(0.3, 1.0, 4), ln)
                y = lp(y, 3200)
                y += modal([rng.uniform(110, 170)], [0.05], [1.4], ln)
                nz = rng.normal(0, 1, ln) * np.exp(-np.arange(ln) / (0.006 * SR))
                y += 0.3 * lp(nz, 1800)
                y *= np.minimum(1, np.arange(ln) / 20.0)
            out.append(y / np.max(np.abs(y)))
        return out

    def add(sig, t, x, gain):
        i = int(t * SR)
        if i >= n or i < 0:
            return
        m = min(len(sig), n - i)
        p = np.clip(x / 26.0, -1, 1) * 0.55
        gl = np.cos((p + 1) * np.pi / 4); gr = np.sin((p + 1) * np.pi / 4)
        L[i:i + m] += sig[:m] * gain * gl
        Rr[i:i + m] += sig[:m] * gain * gr

    def bell(f, length, amp, tau=0.5):
        t = np.arange(int(length * SR)) / SR
        y = (np.sin(2 * np.pi * f * t) * np.exp(-t / tau) + 0.45 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / (tau * 0.55))
             + 0.2 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.15))
        y *= np.minimum(1, t / 0.004)
        return y * amp

    clicks = bank('click', 80); knocks = bank('knock', 24); drops = bank('drop', 24)
    tv_ev = TL.vid_t(ev[:, 0])
    for (t, v, x, typ, y), tv in zip(ev, tv_ev):
        if tv >= dur:
            continue
        sp = TL.speed(float(t))
        slow = (1.0 / sp) ** 0.3
        vis = 1.0 if y < 50 else 0.5
        if typ == 0:
            add(clicks[rng.integers(len(clicks))], tv, x, min((v / 45.0) ** 1.15, 1.6) * CLICK_GAIN * vis * slow)
        elif typ == 1:
            add(knocks[rng.integers(len(knocks))], tv, x, min(v / 40.0, 1.5) * KNOCK_GAIN * vis)
        elif typ == 3:
            add(drops[rng.integers(len(drops))], tv + 0.02, x * 0.3, DROP_GAIN * slow)

    tt = np.arange(n) / SR
    ts = np.interp(tt, TL.TAU, TL.TG)
    rv = np.interp(ts, np.arange(len(RV)) / hz, RV)
    env = lp(np.clip(rv / 6500.0, 0, None) ** 0.75, 12)
    nz1 = rng.normal(0, 1, n); nz2 = rng.normal(0, 1, n); nz3 = rng.normal(0, 1, n)
    crackle = np.clip(1 + 0.6 * lp(rng.normal(0, 1, n), 90) / 0.15, 0.2, 2.5)
    roll = 0.55 * bp(nz1, 90, 420) + 0.35 * bp(nz2, 420, 1600) * crackle + 0.06 * bp(nz3, 2500, 7000) * crackle
    roll = roll / np.std(roll) * ROLL_LEVEL
    L += roll * env * 0.95
    Rr += roll * env * 1.05

    for (a, b) in TL.camera_moves():
        i0 = max(int(a * SR), 0); i1 = min(int(b * SR), n); ln = i1 - i0
        u = np.linspace(0, 1, ln)
        envw = np.sin(np.pi * u) ** 2
        w = rng.normal(0, 1, ln)
        wl = bp(w, 250, 2200) * envw
        wl = wl / (np.max(np.abs(wl)) + 1e-9) * WHOOSH_LEVEL
        L[i0:i1] += wl * 0.9; Rr[i0:i1] += wl * 1.1

    drain = d['drain_t']
    for place, b in enumerate(ep.picks):
        tv = float(TL.vid_t(drain[b])) + 0.04
        if place == 0:
            for k, f in enumerate(WIN_ARPEGGIO):
                add(bell(f, 0.9, 0.085, 0.3), tv + 0.06 + 0.08 * k, 0, 1)
        else:
            add(bell(LOSER_BELLS[place - 1], 1.2, 0.10), tv, 0, 1)

    mix = np.stack([L, Rr], 1)
    fade = int(0.02 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)[:, None]
    fo = int(0.3 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    pk = np.max(np.abs(mix))
    mix = np.tanh(mix / pk * 1.2) / np.tanh(1.2) * 0.89
    wavfile.write(out_wav, SR, (mix * 32767).astype(np.int16))
    return out_wav
