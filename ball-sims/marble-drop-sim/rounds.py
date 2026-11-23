"""Drop schedule for the "1, 2, 3, 4 ... 40 marbles" video (escalating rounds, then a rainbow pour).

Run:  python3 rounds.py            ->  build/rounds.json   (then: python3 sim.py build/rounds.json build/rounds_sim.npz)
Marbles fall from just above the frame onto the top bars and roll down.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
import numpy as np

# ======================================================================= SETTINGS
SEED = 3
DURATION = 12.8
DROP_Z = 0.605                    # start height (just above the frame)
OUT = os.path.join(BUILD_DIR, 'rounds.json')
# Each round: (release time s, distance down the ramp s, left/right x, color)
ROUNDS = [
    [(-0.12, 0.06, 0.0, 'red')],
    [(1.80, 0.060, -0.021, 'orange'), (1.85, 0.064, 0.021, 'yellow')],
    [(3.65, 0.055, -0.036, 'green'), (3.72, 0.065, 0.0, 'teal'), (3.685, 0.055, 0.036, 'blue')],
    [(5.50, 0.050, -0.050, 'purple'), (5.55, 0.062, -0.017, 'pink'), (5.60, 0.050, 0.017, 'gold'), (5.53, 0.062, 0.050, 'silver')],
]
POUR_COUNT = 40
POUR_START, POUR_END = 7.35, 9.0
POUR_LANES = [-0.048, -0.016, 0.016, 0.048]
POUR_ROWS = [0.025 + 0.032 * i for i in range(10)]    # distance down the ramp of each drop row
POUR_COLORS = ['red', 'orange', 'yellow', 'green', 'teal', 'blue', 'purple', 'pink']
POUR_METALS = ['gold', 'silver']                      # every 5th pour marble alternates these
# ===================================================================== END SETTINGS

rng = np.random.default_rng(SEED)
marbles = []


def spawn(s, x, t, color, z=DROP_Z, role='round'):
    p = ramp_point(s, x, 0)
    marbles.append(dict(t=float(t), pos=[float(x), float(p[1]), float(z)], color=color, role=role))


for rnd in ROUNDS:
    for (t, s, x, c) in rnd:
        spawn(s, x, t, c)

cols = []
for k in range(POUR_COUNT):
    if k % 5 == 4:
        cols.append(POUR_METALS[(k // 5) % 2])
    else:
        cols.append(POUR_COLORS[len([c for c in cols if c in POUR_COLORS]) % len(POUR_COLORS)])
lanes = np.array(POUR_LANES)
rows = np.array(POUR_ROWS)
slots = []
for s in rows[::-1]:
    for l_i in rng.permutation(len(lanes)):
        slots.append((lanes[l_i], s))
times = POUR_START + (POUR_END - POUR_START) * (np.arange(POUR_COUNT) + rng.uniform(0.1, 0.9, POUR_COUNT)) / POUR_COUNT
for k in range(POUR_COUNT):
    x, s = slots[k]
    spawn(s + rng.uniform(-0.001, 0.001), x + rng.uniform(-0.001, 0.001), times[k], cols[k], 0.603 + rng.uniform(0, 0.012), role='pour')

cfg = base_cfg(DURATION)
cfg['marbles'] = marbles
os.makedirs(BUILD_DIR, exist_ok=True)
json.dump(cfg, open(OUT, 'w'), indent=0)
print('saved', OUT, len(marbles), 'marbles')
