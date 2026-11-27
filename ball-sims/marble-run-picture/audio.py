"""The soundtrack, synthesized from the timeline (numpy + scipy, no samples): marbles rattling along wooden grooves,
hollow clonks at the bottom of each hole, a soft thud onto the felt, glassy clacks as each marble pushes into the
picture, and a sparkle when the picture is finished. Seeded, so the WAV is the same every run.
"""
import os
import sys

import numpy as np
import scipy.signal as sig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B

import settings as C

SR = B.SR
RES = [(620, 4.0, 0.16), (1250, 2.5, 1.0), (2950, 3.0, 0.65), (6200, 2.0, 0.38)]   # wood resonances: Hz, Q, gain


def _bandbank(x):
    y = np.zeros_like(x)
    for f, q, g in RES:
        b, a = sig.iirpeak(f / (SR / 2), q)
        y += g * sig.lfilter(b, a, x)
    return y


def _tick_kernels(rng):
    ks = []
    for fc in (2600, 3900, 5600):
        n = int(0.004 * SR)
        t = np.arange(n) / SR
        k = rng.standard_normal(n) * np.exp(-t / 0.0007)
        b, a = sig.butter(2, [fc * 0.6 / (SR / 2), min(fc * 1.6, 20000) / (SR / 2)], btype="band")
        ks.append(sig.lfilter(b, a, k))
    return ks


def build(tl, m, out_wav, log=print):
    rng = np.random.default_rng(C.SOUND_SEED)
    B.reset_rng(C.SOUND_SEED)
    fps = tl["fps"]
    nf = tl["n_frames"]
    dur = nf / fps + 0.5
    n = int(dur * SR)
    buf = np.zeros((2, n))
    pos, s, onmat = m["pos"], m["s"], m["mat"]
    # rolling intensity per frame, split left/right by x
    sp = np.zeros_like(s)
    sp[1:] = np.abs(np.diff(s, axis=0)) * fps
    sp = np.nan_to_num(sp)
    rolling = (~np.isnan(s)) & (sp > 0.5) & (sp < 80)
    w = np.where(rolling, (np.clip(sp, 0, 60) / C.V_TRACK) ** 1.3, 0.0)
    pan = np.clip(np.nan_to_num(pos[..., 0]) / 22.0, -1, 1)
    inten = np.stack([(w * (1 - pan) / 2).sum(1), (w * (1 + pan) / 2).sum(1)])
    t_f = (np.arange(nf) + 0.5) / fps
    t_s = np.arange(n) / SR
    env = np.stack([np.interp(t_s, t_f, inten[c]) for c in range(2)])
    env = sig.lfilter(*sig.butter(1, 12 / (SR / 2)), env, axis=1)
    noise = rng.standard_normal((2, n))
    flutter = 1 + 0.6 * sig.lfilter(*sig.butter(2, 28 / (SR / 2)), rng.standard_normal((2, n)), axis=1) * 9
    rollsnd = np.stack([_bandbank(noise[c]) for c in range(2)]) * np.clip(flutter, 0.2, 2.5)
    buf += C.ROLL_LEVEL * rollsnd * np.sqrt(env + 1e-9) * 0.5
    # rattling ticks: a Poisson stream whose rate follows the rolling marbles
    kern = _tick_kernels(rng)
    rate = C.TICK_RATE * (inten[0] + inten[1])
    for c in range(2):
        share = inten[c] / np.maximum(inten[0] + inten[1], 1e-9)
        for fi in range(nf):
            lam = rate[fi] * share[fi] / fps
            k = rng.poisson(lam)
            if k == 0:
                continue
            at = (fi + rng.random(k)) / fps
            gains = rng.exponential(1.0, k) * 0.016
            for tt, g in zip(at, gains):
                kk = kern[rng.integers(3)]
                i0 = int(tt * SR)
                j = min(len(kk), n - i0)
                if j > 0:
                    buf[c, i0:i0 + j] += g * kk[:j]
    # hollow clonks at the bottom of each hole (inside the block: darker)
    lp = sig.butter(2, 2600 / (SR / 2))
    for e in tl["events"]["drops"]:
        y = B.knock(rng.uniform(560, 760), 0.026, 0.25, 0.16)
        y = sig.lfilter(*lp, y)
        B.add(buf, y, e["t"], C.CLONK_GAIN * rng.uniform(0.8, 1.1), np.clip(e["x"] / 22.0, -1, 1) * 0.7)
    for te in tl["events"]["exits"]:
        y = sig.lfilter(*sig.butter(2, 900 / (SR / 2)), B.knock(rng.uniform(240, 320), 0.03, 0.2, 0.12))
        B.add(buf, y, te + 0.02, 0.035, -0.05)
    for ta in tl["events"]["arrivals"]:
        B.add(buf, B.knock(rng.uniform(2700, 3500), 0.007, 0.5, 0.07), ta, C.CLACK_GAIN, rng.uniform(-0.15, 0.15))
        for _ in range(rng.integers(2, 5)):
            B.add(buf, B.knock(rng.uniform(2500, 3800), 0.005, 0.5, 0.05), ta + rng.uniform(0.02, 0.16),
                  C.CLACK_GAIN * rng.uniform(0.15, 0.45), rng.uniform(-0.5, 0.5))
    # sparkle when the picture is done
    td = tl["t_done"] - 0.1
    for i, mm in enumerate([84, 88, 91, 96, 100]):
        B.add(buf, B.bell(B.mtof(mm), kind="spark"), td + i * 0.07, C.CHIME_GAIN, -0.4 + 0.2 * i)
    B.add(buf, B.bell(B.mtof(72), kind="lead"), td, C.CHIME_GAIN * 0.8, 0.0)
    B.write_wav(out_wav, B.master(buf, nf / fps))
    log("soundtrack written")
