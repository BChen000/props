"""The hourglass soundtrack, all synthesized (../marble-raytrace-kit/bells.py): every marble that passes the neck
rings its colour's note (one C major pentatonic note per colour, so the stream plays a twinkling run), marbles
landing on the pile below click and knock, a soft chord and sparkle run as the question appears, a tick for each
count of 3-2-1, a wooden clack as the pin slides out and
a bright chord for GO, a falling two-note bell when a colour runs out, and a fanfare chord with a sparkle run for
the winner.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B
import settings as C

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

    col = tl["col"]
    for t, kind, i, sp, x in tl["ev"]:
        if t < 0 or t > total:
            continue
        pan = float(np.clip(x / C.HALF_W, -1, 1)) * 0.6
        if kind == 0:
            m = C.NOTES[C.COLOURS[int(col[int(i)])][0]]
            B.add(buf, bell(m, "lead", 1.2), t, C.NECK_GAIN * (1.0 + rng.uniform(-0.1, 0.1)), pan * 0.5)
        elif kind == 1:
            y, g = B.impact_sound("floor", sp, rng)
            B.add(buf, y, t, g * C.KNOCK_GAIN, pan)
        elif sp > 9.0:
            y, g = B.impact_sound("ball", sp, rng)
            B.add(buf, y, t, g * C.KNOCK_GAIN * 0.7, pan)
    for m in (60, 64, 67, 72):
        B.add(buf, bell(m, "inner"), 0.05, 0.13, 0.0)
    for i, m in enumerate((79, 84, 88, 91, 96)):
        B.add(buf, bell(m, "spark"), 0.12 + i * 0.07, 0.09, -0.4 + i * 0.2)
    tg = tl["t_go"]
    for j in range(3):
        B.add(buf, bell(79, "lead", 0.6), tg - 1.8 + 0.6 * j, 0.32, 0.0)
    B.add(buf, B.knock(520.0, 0.02, 0.4, 0.12), tg - 0.15, 0.45, 0.2)
    for m in (84, 88, 91):
        B.add(buf, bell(m, "lead", 1.2), tg, 0.24, 0.0)
    for t, k in tl["outs"][:-1]:
        B.add(buf, bell(67, "inner", 0.9), t, 0.3, 0.0)
        B.add(buf, bell(60, "inner", 1.2), t + 0.14, 0.3, 0.0)
    tw = tl["t_win"]
    for m, g in FANFARE:
        B.add(buf, bell(m, "bass" if m < 55 else "inner"), tw, g * 0.45, rng.uniform(-0.3, 0.3))
    for i, m in enumerate(FANFARE_ARP):
        B.add(buf, bell(m, "spark"), tw + 0.05 + i * 0.06, 0.12, -0.5 + i * 0.14)
    B.write_wav(out_wav, B.master(buf, total))
