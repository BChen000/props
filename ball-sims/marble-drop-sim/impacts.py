"""Finds the moment a dropped marble first hits a bar (robust to fast impacts between sim frames)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
import numpy as np


def first_impact(p, t, t_after):
    """p: (frames, 3) marble centers, t: times. Returns (time, bar index, normal speed) or None."""
    rel = p - TOP
    s = rel @ D
    h = rel @ N - MARBLE_R
    vn = np.gradient(h) * SIM_HZ
    for f in range(np.searchsorted(t, t_after) + 1, len(t) - 1):
        if h[f] < 0.012 and vn[f - 1] < -0.2 and vn[f + 1] > vn[f - 1] + 0.3 and -0.01 < s[f] < L + 0.01:
            fb = int(np.argmin(h[f - 3:f + 3])) + f - 3
            hprev = h[fb - 1]
            vprev = vn[fb - 2]
            tim = t[fb - 1] + max(hprev, 0) / max(-vprev, 1e-3)
            sim_ = s[fb - 1] + (s[fb] - s[fb - 1]) * 0.5
            return float(tim), int(np.floor(sim_ / BAR_P)), float(-vprev)
    return None
