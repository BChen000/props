"""The spinning-dish soundtrack, from the physics events and the channel's sound kit (../battle-audio, synthesized,
seeded): marbles rolling on wood (noise through wood resonances, following their speed), clacks when they touch,
knocks off the rim and the pegs, a hollow plonk and a stinger for every marble that drops, a whoosh for each near
miss, a bell when a peg lights up, a suspense pulse that gets louder in the final, a heartbeat while the last two
fight it out, and the brass fanfare with claps and a happy loop for the winner.
"""
import os
import sys

import numpy as np
import scipy.signal as sig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "battle-audio"))
import battle_audio as ba

import settings as C

RES = [(620, 4.0, 0.16), (1250, 2.5, 1.0), (2950, 3.0, 0.6), (6200, 2.0, 0.35)]
PEG_BELL = [1567.98, 1975.53, 2349.32]         # G6, B6, D7


def build(tl, out_wav, log=print):
    ba.reset_rng(C.SOUND_SEED)
    SR = ba.SR
    nf = tl["n_frames"]
    dur = nf / C.FPS + 0.3
    n = int(dur * SR)
    L, Rr = np.zeros(n), np.zeros(n)
    ev = tl["events"]
    t_win = next(t for t, k, _ in ev if k == "winner")
    t_f2 = next((t for t, k, _ in ev if k == "final2"), t_win - 5)
    # suspense pulse: quiet, louder for the final, stops at the win
    pulse = ba.suspense_music(t_win, 132)
    gain = np.interp(np.arange(len(pulse)) / SR, [0, t_f2 - 1, t_f2, t_win - 0.3, t_win], [0.27, 0.24, 0.34, 0.4, 0.0])
    ba.add_st(L, Rr, pulse * gain, 0.0)
    ba.add_st(L, Rr, ba.whoosh(0.5, 0.4, 400, 4000), 0.0)           # straight in: everyone already spinning
    ba.add_st(L, Rr, ba.pop(0.5, 700), 0.05)
    for t, k, v in ev:
        if k == "clack":
            sp, x, z = v
            ba.add_st(L, Rr, ba.clack(min(1.0, sp / 25.0) ** 1.2 * 0.5, np.random.default_rng(int(t * 1000)).uniform(3200, 4000)),
                      t, 1.0, np.clip(x / 18, -0.8, 0.8))
        elif k in ("rim", "peg"):
            sp, x, z = v[:3]
            f = 760 if k == "rim" else 1250
            y = ba.bandpass(ba.noise(0.05), f * 0.7, f * 2.2) * ba.env_ad(int(0.05 * SR), 0.0005, 0.012)
            y += np.sin(2 * np.pi * f * np.arange(int(0.05 * SR)) / SR) * ba.env_ad(int(0.05 * SR), 0.0008, 0.02)
            ba.add_st(L, Rr, y, t, min(1.0, sp / 30.0) * (0.35 if k == "rim" else 0.45), np.clip(x / 18, -0.8, 0.8))
            if k == "peg":                                  # the peg lights up: a bright bumper bell, one pitch per peg
                ba.add_st(L, Rr, ba.ding(1.0, PEG_BELL[v[3] % len(PEG_BELL)], 0.35), t,
                          0.16 * min(1.0, sp / 22.0) ** 0.7, np.clip(x / 18, -0.8, 0.8))
        elif k == "out":
            plonk = ba.sweep_sine(210, 120, 0.25, 4) * ba.env_ad(int(0.25 * SR), 0.002, 0.08)
            ba.add_st(L, Rr, plonk, t, 0.55)
            for q in range(4):
                ba.add_st(L, Rr, ba.clack(0.18 / (q + 1), 2400 - 250 * q), t + 0.05 + 0.06 * q, 1.0)
            ba.add_st(L, Rr, ba.note("tri", 74, 0.12, 0.35), t + 0.05)
            ba.add_st(L, Rr, ba.note("tri", 67, 0.22, 0.35), t + 0.17)
        elif k == "close":
            ba.add_st(L, Rr, ba.whoosh(0.35, 0.3, 500, 4500), t - 0.12)
        elif k == "final2":
            ba.add_st(L, Rr, ba.riser(1.2, 0.18), t - 1.2)
            ba.add_st(L, Rr, ba.ding(0.35, 1568.0, 0.8), t)
        elif k in ("cut", "back"):
            ba.add_st(L, Rr, ba.whoosh(0.4, 0.3 if k == "cut" else 0.2, 300, 3000), t - 0.2)
        elif k == "winner":
            ba.add_st(L, Rr, ba.brass_fanfare(1.0), t, 0.9)
            ba.add_st(L, Rr, ba.crash(0.45, 1.6), t + 0.32)
            for q in range(6):
                ba.add_st(L, Rr, ba.clap(0.35), t + 0.5 + q * 0.18, 1.0, -0.3 + 0.12 * q)
            tail = dur - (t + 1.6)                          # a happy loop under the winner until the end
            if tail > 0.3:
                ol = ba.outro_loop(tail, 118)
                ol *= np.minimum(1.0, np.arange(len(ol)) / (0.4 * SR))
                ba.add_st(L, Rr, ol, t + 1.6, 0.45)
    hb_t = t_f2 + 1.0
    while hb_t < t_win - 0.4:
        ba.add_st(L, Rr, ba.heartbeat(0.8), hb_t)
        hb_t += 0.85
    # rolling on wood, following the marbles' speed
    pos = tl["pos"]
    sp = np.linalg.norm(np.gradient(pos[:, :, [0, 2]], axis=0), axis=-1) * C.FPS
    on = tl["roll"]
    w = np.where(on, np.clip(sp / 30.0, 0, 1.5) ** 1.2, 0.0)
    pan = np.clip(pos[:, :, 0] / 18.0, -1, 1)
    lw, rw = (w * (1 - pan) / 2).sum(1), (w * (1 + pan) / 2).sum(1)
    tf = (np.arange(nf) + 0.5) / C.FPS
    ts = np.arange(n) / SR
    nz = ba.noise(dur)[:n]
    bank = np.zeros(n)
    for f, q, g in RES:
        b, a = sig.iirpeak(f / (SR / 2), q)
        bank += g * sig.lfilter(b, a, nz)
    L += 0.045 * bank * np.sqrt(np.interp(ts, tf, lw) + 1e-9)
    Rr += 0.045 * bank * np.sqrt(np.interp(ts, tf, rw) + 1e-9)
    ba.master_and_write(L, Rr, out_wav, limit=0.46)
    log("soundtrack written")
