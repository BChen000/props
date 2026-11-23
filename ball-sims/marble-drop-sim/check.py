"""Sanity checks for a simulation: every marble ends in the basket, melody marbles hit the right bar on time,
nobody touched the invisible guards, and when everything has stopped moving.

Run:  python3 check.py SIM.npz CFG.json
Exits with an error if a marble escaped or a melody note landed wrong.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
from impacts import first_impact
import numpy as np

sim, cfgf = sys.argv[1], sys.argv[2]
d = np.load(sim); P = d['pos']; t = d['t']
cfg = json.load(open(cfgf))
bad = 0
for i, m in enumerate(cfg['marbles']):
    fin = P[-1, i]
    rb = np.hypot(fin[0] - BASKET_C[0], fin[1] - BASKET_C[1])
    if not (rb < 0.135 and fin[2] < 0.12):
        bad += 1
        print('marble %d (%s) ended outside the basket at %s' % (i, m['color'], np.round(fin, 3)))
    if 't_hit' in m and m.get('role') != 'pour':
        r = first_impact(P[:, i], t, m['t'])
        if r is None or r[1] != m['bar'] or abs(r[0] - m['t_hit']) > 0.012:
            bad += 1
            print('marble %d (%s) note wrong: wanted bar %d at %.3f, got %s' % (i, m['color'], m['bar'], m['t_hit'], r))
s_ = (P - TOP) @ D
onr = (s_ > 0) & (s_ < L) & (P[:, :, 2] > 0.15)
xm = np.abs(P[:, :, 0])
side = onr & (xm > BAR_LEN / 2 + SIDE_GUARD_GAP - 0.005 - MARBLE_R)
rb = np.hypot(P[:, :, 0] - BASKET_C[0], P[:, :, 1] - BASKET_C[1])
ring = (rb > RIM_GUARD['r'] - MARBLE_R - 0.002) & (P[:, :, 2] > RIM_GUARD['z0']) & (P[:, :, 2] < RIM_GUARD['z1'] + 0.01) & (P[:, :, 1] < -0.02)
v = np.linalg.norm(np.gradient(P, axis=0) * SIM_HZ, axis=2)
moving = np.where(v.max(1) > 0.05)[0]
print('marbles: %d   problems: %d' % (P.shape[1], bad))
print('max |x| on ramp: %.3f m   guard touches: side %d frames, rim %d frames' % (xm[onr].max(), side.sum(), ring.sum()))
print('everything slower than 5 cm/s after: %.2f s' % (t[moving[-1]] if len(moving) else t[0]))
if bad:
    sys.exit(1)
