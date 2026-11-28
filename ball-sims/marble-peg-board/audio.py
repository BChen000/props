"""The peg board's soundtrack, all synthesized (../marble-raytrace-kit/bells.py): every peg hit rings a bell, tuned
by row (high at the top, falling through a C major pentatonic scale as the marble drops), panned by where it hits;
landings in a bin are a wooden clunk, knocks between resting marbles are clicks; a short count-up tick on every
landing, and a fanfare chord with a sparkle run for the winner.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B
import settings as C
import scene as S

FANFARE = [(48, 0.5), (60, 0.45), (64, 0.38), (67, 0.36), (72, 0.42), (76, 0.32), (79, 0.28), (84, 0.22)]
FANFARE_ARP = [72, 76, 79, 84, 88, 91, 96, 100]


def build(tl, out_wav):
    B.reset_rng()
    rng = np.random.default_rng(C.SOUND_SEED)
    total = tl["n_frames"] / C.FPS
    buf = np.zeros((2, int((total + 3.0) * B.SR)))
    cache = {}

    def bell(m, kind, dur=None):
        if (m, kind, dur) not in cache:
            cache[(m, kind, dur)] = B.bell(B.mtof(m), dur, kind=kind)
        return cache[(m, kind, dur)]

    half = S.HALF
    for t, _, p, _, sp, x in tl["hits"]:
        row = S.PEGS[int(p)][2]
        m = C.SCALE[min(len(C.SCALE) - 1, C.ROWS - row)]
        g = C.PEG_GAIN * min(1.0, max(sp, 2.0) / 14.0) ** 0.8
        B.add(buf, bell(m, "lead", 1.4), t, g * (1.0 + rng.uniform(-0.06, 0.06)), float(np.clip(x / half, -1, 1)) * 0.7)
    for t, kind, a, _, sp, x in tl["ev"]:
        pan = float(np.clip(x / half, -1, 1)) * 0.6
        if kind == 1:
            y = B.knock(rng.uniform(330, 420), 0.035, 0.5, 0.18)
            B.add(buf, y, t, C.LAND_GAIN * min(1.0, max(sp, 4.0) / 18.0) ** 0.7, pan)
            B.add(buf, bell(96, "spark", 0.4), t + 0.01, 0.05, pan)
        elif kind == 2:
            y, g = B.impact_sound("ball" if a == 1 else "floor", sp, rng)
            B.add(buf, y, t, g * 0.8, pan)
    tw = tl["t_win"]
    for m, g in FANFARE:
        B.add(buf, bell(m, "bass" if m < 55 else "inner"), tw, g * 0.45, rng.uniform(-0.3, 0.3))
    for i, m in enumerate(FANFARE_ARP):
        B.add(buf, bell(m, "spark"), tw + 0.05 + i * 0.06, 0.12, -0.5 + i * 0.14)
    B.write_wav(out_wav, B.master(buf, total))
