"""The balance soundtrack, from the physics events and the channel's sound kit (../battle-audio, synthesized,
seeded): glass marbles rolling along the shelf, bright clinks when glass hits glass, heavier metallic clunks for the
steel balls, wooden knocks on the zigzag, a deep thunk each time the beam lands on a stop post, a whoosh when the
lead changes, a suspense pulse that builds with the last steel ball, then the brass fanfare, claps and a happy loop.
"""
import os
import sys

import numpy as np
import scipy.signal as sig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "battle-audio"))
import battle_audio as ba

import settings as C

RES = [(700, 4.0, 0.25), (1400, 2.5, 1.0), (3100, 3.0, 0.5)]


def thunk(vol):
    n = int(0.35 * ba.SR)
    t = np.arange(n) / ba.SR
    body = np.sin(2 * np.pi * (95 + 40 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.09)
    knock = ba.bandpass(ba.noise(0.35), 180, 900) * np.exp(-t / 0.025)
    return vol * (0.9 * body + 0.6 * knock[:n])


def build(tl, out_wav, log=print):
    ba.reset_rng(C.SOUND_SEED)
    SR = ba.SR
    nf = tl["n_frames"]
    dur = nf / C.FPS + 0.3
    n = int(dur * SR)
    L, Rr = np.zeros(n), np.zeros(n)
    team = tl["team"]
    steel_side = 1 if C.RIGHT["metal"] else -1
    ev = tl["events"]
    t_win = tl["t_tip"]
    t_last = next(t for t, k, _ in ev if k == "last_one")
    pulse = ba.suspense_music(t_win, 128)
    gain = np.interp(np.arange(len(pulse)) / SR, [0, t_last - 0.5, t_last, t_win - 0.2, t_win],
                     [0.2, 0.22, 0.34, 0.42, 0.0])
    ba.add_st(L, Rr, pulse * gain, 0.0)
    ba.add_st(L, Rr, ba.whoosh(0.5, 0.35, 400, 4000), 0.0)
    ba.add_st(L, Rr, ba.pop(0.5, 700), 0.05)
    ba.add_st(L, Rr, ba.riser(max(0.6, t_win - t_last - 0.1), 0.25), t_last)
    for t, k, v in ev:
        if k == "clack":
            sp, x, y, i = v
            steel = team[int(i)] == steel_side
            vol = min(1.0, sp / 60.0) ** 1.1
            if steel:
                ba.add_st(L, Rr, ba.metal(1900.0, 0.35, 0.22 * vol), t, 1.0, np.clip(x / 25, -0.8, 0.8))
            else:
                ba.add_st(L, Rr, ba.clack(0.42 * vol, np.random.default_rng(int(t * 997)).uniform(3600, 4400)), t,
                          1.0, np.clip(x / 25, -0.8, 0.8))
        elif k in ("wood", "basket", "stand"):
            sp, x, y, i = v
            steel = team[int(i)] == steel_side
            vol = min(1.0, sp / 90.0)
            f = 520 if steel else 900
            m = int(0.07 * SR)
            y_ = ba.bandpass(ba.noise(0.07), f * 0.6, f * 2.6)[:m] * ba.env_ad(m, 0.0006, 0.018)
            y_ += np.sin(2 * np.pi * f * np.arange(m) / SR) * ba.env_ad(m, 0.001, 0.03)
            ba.add_st(L, Rr, y_, t, (0.55 if steel else 0.32) * vol, np.clip(x / 25, -0.8, 0.8))
            if steel and k == "basket" and sp > 40:
                ba.add_st(L, Rr, thunk(0.35 * min(1.0, sp / 120.0)), t, 1.0, np.clip(x / 25, -0.8, 0.8))
        elif k == "stop":
            sp = v[0]
            ba.add_st(L, Rr, thunk(min(1.0, 0.25 + sp / 1.2)), t, 0.9, 0.4 * v[3])
        elif k == "flip" and t < t_win - 0.05:
            ba.add_st(L, Rr, ba.whoosh(0.45, 0.3, 300, 3000), t - 0.25)
            ba.add_st(L, Rr, ba.ding(0.3, 1318.5, 0.6), t + 0.1)
        elif k == "close":
            ba.add_st(L, Rr, ba.whoosh(0.35, 0.25, 500, 4500), t - 0.1)
        elif k == "land" and v[0] == ("R" if steel_side > 0 else "L"):
            ba.add_st(L, Rr, ba.pop(0.25, 900), t + 0.02)
        elif k == "all_left":
            ba.add_st(L, Rr, ba.ding(0.35, 1568.0, 0.8), t)
        elif k == "winner":
            ba.add_st(L, Rr, ba.brass_fanfare(1.0), t + 0.3, 0.9)
            ba.add_st(L, Rr, ba.crash(0.45, 1.6), t + 0.62)
            for q in range(6):
                ba.add_st(L, Rr, ba.clap(0.35), t + 0.8 + q * 0.18, 1.0, -0.3 + 0.12 * q)
            tail = dur - (t + 1.9)
            if tail > 0.3:
                ol = ba.outro_loop(tail, 118)
                ol *= np.minimum(1.0, np.arange(len(ol)) / (0.4 * SR))
                ba.add_st(L, Rr, ol, t + 1.9, 0.45)
    # marbles rolling along the tracks: noise through wood resonances, following their speed
    pos = tl["pos"]
    sp = np.linalg.norm(np.gradient(pos[:, :, :2], axis=0), axis=-1) * C.FPS
    land = tl["land"]
    ft = np.arange(nf) / C.FPS
    rolling = tl["vis"] & (ft[:, None] < land[None, :] - 0.15)
    w = np.where(rolling, np.clip(sp / 40.0, 0, 1.5), 0.0)
    w *= np.where(team[None, :] == steel_side, 1.6, 1.0)
    pan = np.clip(pos[:, :, 0] / 25.0, -1, 1)
    lw, rw = (w * (1 - pan) / 2).sum(1), (w * (1 + pan) / 2).sum(1)
    tf = (np.arange(nf) + 0.5) / C.FPS
    ts = np.arange(n) / SR
    nz = ba.noise(dur)[:n]
    bank = np.zeros(n)
    for f, q, g in RES:
        b, a = sig.iirpeak(f / (SR / 2), q)
        bank += g * sig.lfilter(b, a, nz)
    L += 0.05 * bank * np.sqrt(np.interp(ts, tf, lw) + 1e-9)
    Rr += 0.05 * bank * np.sqrt(np.interp(ts, tf, rw) + 1e-9)
    ba.master_and_write(L, Rr, out_wav, limit=0.46)
    log("soundtrack written")
