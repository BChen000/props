"""Turns a simulation into sound events: bar hits (with MIDI note), marble clicks, basket thuds, rolling.

Run:  python3 events.py SIM.npz CFG.json OUT.npz [--mode role|physics]
  role    : each marble's first hit is a loud "melody" note sized by its role, later hits are soft (Twinkle video)
  physics : every hit is sized by its impact speed (40 marbles video)
--scale major|pentatonic picks the bar tuning used for the MIDI notes (default: SCALE in xylophone-ramp/params.py).
The 40 marbles video used:  --mode physics --scale pentatonic
OUT.npz is read by glockenspiel-sounds/synth.py.
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
from impacts import first_impact
import numpy as np

# ======================================================================= SETTINGS
ROLE_AMP = {'melody': 1.0, 'melody2': 0.8, 'arp': 0.85, 'pour': 0.45}
DEFAULT_ROLE_AMP = 0.6
TAIL = 0.42                   # role mode: loudness of bounces / rolling after the first hit
# ===================================================================== END SETTINGS


def extract(sim_file, cfg_file, mode='role'):
    d = np.load(sim_file)
    P = d['pos'].astype(np.float64)
    t = d['t'].astype(np.float64)
    NF, NM, _ = P.shape
    r = MARBLE_R
    V = np.gradient(P, axis=0) * SIM_HZ
    g = np.array([0, 0, -9.81]) / SIM_HZ
    notes, clicks, thuds = [], [], []
    roll_bar = np.zeros((NF, NM))
    roll_bask = np.zeros((NF, NM))
    rel = P - TOP
    S_ = rel @ D
    Hh = rel @ N - r
    cfgm = json.load(open(cfg_file))['marbles']
    for i in range(NM):
        fi = None
        if mode == 'role':
            fi = first_impact(P[:, i], t, cfgm[i]['t'])
            if fi is not None:
                notes.append((fi[0], fi[1], ROLE_AMP.get(cfgm[i].get('role'), DEFAULT_ROLE_AMP), float(np.interp(fi[0], t, P[:, i, 0])), i, 1))
        s = S_[:, i]; h = Hh[:, i]
        contact = (h < 0.0012) & (s > -0.004) & (s < L + 0.004) & (P[:, i, 2] > 0.1)
        kc = np.clip(np.floor(s / BAR_P).astype(int), 0, NB - 1)
        onbar = contact & ((s - kc * BAR_P) < BAR_W + 0.0005)
        last = -1
        airborne = True
        for f in range(1, NF):
            if not contact[f]:
                if h[f] > 0.0025:
                    airborne = True
                continue
            if not onbar[f]:
                continue
            k = kc[f]
            if airborne or k != last:
                vprev = V[max(f - 2, 0), i]
                vn = max(0.0, -(vprev @ N))
                vt = np.linalg.norm(vprev - (vprev @ N) * N)
                if airborne and vn > 0.12:
                    amp = float(np.clip(vn / 2.2, 0.15, 1.0))
                else:
                    amp = float(0.22 + 0.33 * np.clip(vt / 0.9, 0, 1))
                if mode == 'physics':
                    notes.append((float(t[f]), int(k), amp, float(P[f, i, 0]), i, 0))
                elif fi is None or not (abs(t[f] - fi[0]) < 0.045 and k == fi[1]):
                    notes.append((float(t[f]), int(k), amp * TAIL, float(P[f, i, 0]), i, 0))
                last = k
                airborne = False
        sp = np.linalg.norm(V[:, i], axis=1)
        roll_bar[:, i] = np.where(contact, sp, 0)
        rb = np.hypot(P[:, i, 0] - BASKET_C[0], P[:, i, 1] - BASKET_C[1])
        inb = (rb < 0.16) & (P[:, i, 2] < 0.09)
        roll_bask[:, i] = np.where(inb & (P[:, i, 2] < 0.035), sp, 0)
    prevc = np.zeros((NM, NM), bool)
    contact_any = np.zeros((NF, NM), bool)
    for f in range(1, NF):
        diff = P[f][:, None, :] - P[f][None, :, :]
        dist = np.linalg.norm(diff, axis=-1)
        c = dist < 2 * r + 0.0008
        np.fill_diagonal(c, False)
        contact_any[f] = c.any(1)
        new = c & ~prevc
        ii, jj = np.where(np.triu(new, 1))
        for a, b in zip(ii, jj):
            n_ = diff[a, b] / max(dist[a, b], 1e-9)
            vrel = -((V[f - 2, a] - V[f - 2, b]) @ n_)
            if vrel > 0.03:
                clicks.append((float(t[f]), float(np.clip(vrel / 0.9, 0.05, 1.0)), float((P[f, a, 0] + P[f, b, 0]) / 2)))
        prevc = c
    for i in range(NM):
        rb = np.hypot(P[:, i, 0] - BASKET_C[0], P[:, i, 1] - BASKET_C[1])
        inb = (rb < 0.17) & (P[:, i, 2] < 0.10)
        dv = np.linalg.norm(np.diff(V[:, i], axis=0) - g, axis=1)
        lastf = -100
        for f in range(1, NF - 1):
            if not inb[f] or dv[f] < 0.07 or contact_any[f, i] or contact_any[f + 1, i]:
                continue
            if f - lastf < SIM_HZ * 0.03:
                continue
            if dv[f] < dv[f - 1] or dv[f] < dv[f + 1]:
                continue
            thuds.append((float(t[f]), float(np.clip(dv[f] / 1.2, 0.04, 1.0)), float(P[f, i, 0])))
            lastf = f
    xs = P[:, :, 0]
    env = {}
    for nm_, arr in (('bar', roll_bar), ('bask', roll_bask)):
        env['roll_%s_env' % nm_] = np.sqrt((arr ** 2).sum(1))
        env['roll_%s_x' % nm_] = (arr * xs).sum(1) / np.maximum(arr.sum(1), 1e-6)
    notes = np.array([(tt, k, bar_midi(int(k)), a, x, i, f1) for (tt, k, a, x, i, f1) in notes], float).reshape(-1, 7)
    return dict(notes=notes, clicks=np.array(clicks, float).reshape(-1, 3), thuds=np.array(thuds, float).reshape(-1, 3), t=t, **env)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('sim'); ap.add_argument('cfg'); ap.add_argument('out')
    ap.add_argument('--mode', default='role', choices=['role', 'physics'])
    ap.add_argument('--scale', default=None, choices=['major', 'pentatonic'])
    a = ap.parse_args()
    if a.scale:
        import params
        params.SCALE = params.SCALE_MAJOR if a.scale == 'major' else params.SCALE_PENTATONIC
    ev = extract(a.sim, a.cfg, a.mode)
    np.savez_compressed(a.out, **ev)
    print('saved', a.out, 'notes', len(ev['notes']), 'clicks', len(ev['clicks']), 'thuds', len(ev['thuds']))
