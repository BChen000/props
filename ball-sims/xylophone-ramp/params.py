"""Shared settings for the xylophone-ramp set.

Every other xylophone prop (marble-drop-sim, marble-plate-compositor,
xylophone-song-template) imports this file, so the geometry, the bar tuning
and the timing stay in one place. Units are meters and seconds.
"""
import math
import numpy as np

# ---------------------------------------------------------------- tuning
# Bar 0 is the top (far) bar. Bars step down the scale toward the camera.
TOP_MIDI = 108                        # C8
SCALE_MAJOR = [0, 2, 4, 5, 7, 9, 11]  # used by the Twinkle video (C8 down to C5)
SCALE_PENTATONIC = [0, 2, 4, 7, 9]    # used by the "40 marbles" video (C8 down to A3)
SCALE = SCALE_MAJOR

# ---------------------------------------------------------------- timing
FPS = 30
SIM_HZ = 240

# ---------------------------------------------------------------- ramp
THETA = math.radians(11.0)   # slope of the ramp
NB = 22                      # number of bars
BAR_W = 0.034                # bar width along the slope
BAR_GAP = 0.005              # gap between bars (keep < 2*MARBLE_R*sin(THETA) so marbles never get stuck)
BAR_T = 0.007                # bar thickness
BAR_LEN = 0.24               # bar length (left to right)
FELT_T = 0.003
RAIL_H = 0.022
RAIL_W = 0.016
FRONT_Y = 0.0                # y of the bottom bar's front edge
FRONT_Z = 0.16               # height of the bar tops at the front edge

# ---------------------------------------------------------------- marbles
MARBLE_R = 0.015

# ---------------------------------------------------------------- basket (coiled rope bowl)
BASKET_C = np.array([0.0, -0.152, 0.0])
ROPE_R = 0.0062
BASKET_PROFILE = [(0.110, 0.0062), (0.1255, 0.0128), (0.1385, 0.0252), (0.1478, 0.0405),
                  (0.1532, 0.0560), (0.1556, 0.0665)]

# ---------------------------------------------------------------- stands under the ramp
BOX = dict(x0=-0.10, x1=0.10, y0=0.035, y1=0.27)
BACK = dict(x0=-0.09, x1=0.09, y0=0.66, y1=0.86)

# ---------------------------------------------------------------- derived (do not edit)
BAR_P = BAR_W + BAR_GAP
L = NB * BAR_P - BAR_GAP
D = np.array([0.0, -math.cos(THETA), -math.sin(THETA)])   # down-slope direction
N = np.array([0.0, -math.sin(THETA), math.cos(THETA)])    # ramp surface normal
TOP = np.array([0.0, FRONT_Y + L * math.cos(THETA), FRONT_Z + L * math.sin(THETA)])


def bar_len(k):
    return BAR_LEN


def bar_top_center(k):
    s = k * BAR_P + BAR_W / 2
    return TOP + s * D


def ramp_point(s, x=0.0, h=0.0):
    return TOP + s * D + h * N + np.array([x, 0.0, 0.0])


def bar_midi(k):
    notes = []
    m = TOP_MIDI
    pcs = set(SCALE)
    while len(notes) < NB:
        if (m % 12) in pcs:
            notes.append(m)
        m -= 1
    return notes[k]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def probe_positions():
    """Where the compositor captures lighting probes (marble centers on the ramp, in the air, in the basket)."""
    R = MARBLE_R
    return [ramp_point(0.06, 0, R), ramp_point(0.06, 0, 0.14), ramp_point(L * 0.5, 0, R), ramp_point(L - 0.03, 0, R),
            np.array([0.0, -0.06, 0.13]), BASKET_C + np.array([0, 0, 0.0124 + R]),
            BASKET_C + np.array([0, -0.08, 0.025 + R])]
