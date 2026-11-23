"""Measures how long a marble takes to fall from above the frame onto each bar.

melody.py needs this so every marble lands exactly on its beat.
Run:  python3 calibrate.py       ->  build/fall_calib.json   (about 15 s)
Re-run whenever the camera, the ramp or the physics settings change.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
from impacts import first_impact
import numpy as np

# ======================================================================= SETTINGS
BARS = list(range(0, 15))       # bars to calibrate (the melody and arpeggio use bars 0-14)
GAP = 2.5                       # seconds between test drops
CFG = os.path.join(BUILD_DIR, 'calib.json')
SIM = os.path.join(BUILD_DIR, 'calib_sim.npz')
OUT = os.path.join(BUILD_DIR, 'fall_calib.json')
# ===================================================================== END SETTINGS

ms = []
for j, k in enumerate(BARS):
    s = k * BAR_P + BAR_W / 2
    p = ramp_point(s, 0.0, 0)
    ms.append(dict(t=0.5 + GAP * j, pos=[0.0, float(p[1]), spawn_z(p[1])], color='red', bar=k))
cfg = base_cfg(0.5 + GAP * len(BARS) + 2)
cfg['marbles'] = ms
os.makedirs(BUILD_DIR, exist_ok=True)
json.dump(cfg, open(CFG, 'w'))
run_bpy(os.path.join(HERE, 'sim.py'), CFG, SIM)
d = np.load(SIM)
P, t = d['pos'], d['t']
cal = {}
for i, m in enumerate(ms):
    r = first_impact(P[:, i], t, m['t'])
    if r is None or r[1] != m['bar']:
        raise SystemExit(f"bar {m['bar']}: marble did not land where expected ({r})")
    cal[m['bar']] = r[0] - m['t']
    print('bar %2d  fall %.4f s' % (m['bar'], cal[m['bar']]))
json.dump(cal, open(OUT, 'w'))
print('saved', OUT)
