"""Draws preview.png: marble paths seen from the side, and the notes they play over time.

Run:  python3 plot_preview.py SIM.npz CFG.json EVENTS.npz [OUT.png]
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS = {'red': '#E5252A', 'orange': '#F98C17', 'yellow': '#FDDA27', 'green': '#54C440', 'teal': '#00BAB5',
          'blue': '#1C73F0', 'purple': '#A23EE2', 'pink': '#FC7DB8', 'gold': '#D7B068', 'silver': '#A9AAB0'}
sim, cfgf, evf = sys.argv[1:4]
out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, 'preview.png')
d = np.load(sim); P = d['pos']; t = d['t']
cfg = json.load(open(cfgf))
ev = np.load(evf)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 11), dpi=120, gridspec_kw=dict(height_ratios=[1.1, 1]))
fig.patch.set_facecolor('#F4F4F2')
bars_s = [(k * BAR_P, k * BAR_P + BAR_W) for k in range(NB)]
for s0, s1 in bars_s:
    p0, p1 = ramp_point(s0), ramp_point(s1)
    a1.plot([p0[1], p1[1]], [p0[2], p1[2]], color='#9A9DA3', lw=4, solid_capstyle='butt')
prof = np.array(BASKET_PROFILE)
for sgn in (-1, 1):
    a1.plot(BASKET_C[1] + sgn * prof[:, 0], prof[:, 1], color='#B89B6A', lw=5)
a1.plot([BASKET_C[1] - 0.11, BASKET_C[1] + 0.11], [0.006, 0.006], color='#B89B6A', lw=5)
for i, m in enumerate(cfg['marbles']):
    p = P[:, i]
    ok = (t > m['t']) & (np.abs(p[:, 0]) < 1.2) & (p[:, 2] < 1.0)
    a1.plot(p[ok, 1], p[ok, 2], color=COLORS.get(m['color'], '#555'), lw=1.0, alpha=0.75)
a1.set_aspect('equal'); a1.set_xlim(-0.36, 0.95); a1.set_ylim(-0.01, 0.66)
a1.invert_xaxis()
a1.set_title('Marble paths (side view, camera on the left)', fontsize=12)
a1.set_xlabel('depth y (m)'); a1.set_ylabel('height z (m)')
nt = ev['notes']
first = nt[:, 6] > 0
for f_, sz, al in ((~first, 10, 0.35), (first, 60, 0.95)):
    cols = [COLORS.get(cfg['marbles'][int(i)]['color'], '#555') for i in nt[f_, 5]]
    a2.scatter(nt[f_, 0], nt[f_, 2], s=sz * np.clip(nt[f_, 3], 0.2, 1), c=cols, alpha=al, edgecolors='none')
names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
ticks = sorted(set(int(m) for m in nt[:, 2]))
a2.set_yticks(ticks); a2.set_yticklabels([names[m % 12] + str(m // 12 - 1) for m in ticks], fontsize=7)
a2.grid(axis='y', color='#E4E4E0', lw=0.6)
a2.set_xlim(-0.2, float(t[-1])); a2.set_xlabel('time (s)'); a2.set_ylabel('note')
a2.set_title('Notes played (big dots = first hit of each marble)', fontsize=12)
for a in (a1, a2):
    a.set_facecolor('#FBFBFA')
plt.tight_layout()
plt.savefig(out, facecolor=fig.get_facecolor())
print('saved', out)
