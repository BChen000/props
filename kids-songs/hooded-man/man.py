"""Posing the hooded man: torso lean, head turn, two-bone IK arms with hand poses, and the facet-explode glitch.

A pose is a dict:
  root=(x, y, z, yaw_deg), lean=(pitch_deg, roll_deg), head=(pitch_deg, yaw_deg, roll_deg),
  R / L = dict(w=(x, y, z) wrist in torso space, f=finger direction, p=palm direction, g=hand pose name)
Torso space: origin at the hips pivot, axes as the world at rest (he faces -Y; his right is -X).
Head pitch > 0 looks down, yaw > 0 turns to his left (screen right).
"""
import math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'shared', 'lowpoly-gl'))
import numpy as np
from glr import T, R3, euler
from rig import HIPS, HEAD, SHOULDER, UPPER, FORE, SIDE

MAN_PARTS = ['head', 'neck', 'hat_crown', 'hat_band', 'hat_brim', 'torso', 'hem', 'hood', 'hood_bag', 'strings',
             'aglets', 'pocket', 'legs', 'shoes']
HEAD_PARTS = ['head', 'neck', 'hat_crown', 'hat_band', 'hat_brim']
TORSO_PARTS = ['torso', 'hem', 'hood', 'hood_bag', 'strings', 'aglets', 'pocket']

MAT = {
    'head': dict(spec=0.10, shin=18), 'neck': dict(spec=0.08), 'hat_crown': dict(spec=0.12, shin=20),
    'hat_brim': dict(spec=0.12, shin=20), 'hat_band': dict(spec=0.2, shin=30), 'aglets': dict(spec=1.2, shin=60),
    'torso': dict(spec=0.05, shin=8), 'hood': dict(spec=0.05, shin=8), 'hood_bag': dict(spec=0.05, shin=8),
}


def rest_arm(s):
    sd = SIDE[s]
    sh = SHOULDER[s] - HIPS
    return dict(w=tuple(sh + [sd * 0.035, -0.035, -0.515]), f=(sd * 0.06, -0.05, -1), p=(-sd, 0.1, 0), g='relax')


REST = dict(root=(0, 0, 0, 0), lean=(0, 0), head=(0, 0, 0), R=rest_arm('R'), L=rest_arm('L'))


def _frame(negz, hint):
    z = -np.asarray(negz, float); z /= np.linalg.norm(z)
    x = np.cross(hint, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross((0.3, 0.2, 0.9), z)
    x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def ik(S, Tt, a, b, pole):
    d = Tt - S; dist = np.linalg.norm(d)
    dist_c = np.clip(dist, abs(a - b) + 1e-3, a + b - 1e-3)
    u = d / max(dist, 1e-6)
    Tt = S + u * dist_c
    cos_a = (a * a + dist_c * dist_c - b * b) / (2 * a * dist_c)
    al = math.acos(np.clip(cos_a, -1, 1))
    p = pole - S; p = p - np.dot(p, u) * u
    p = p / max(np.linalg.norm(p), 1e-6)
    E = S + a * (math.cos(al) * u + math.sin(al) * p)
    return E, Tt


def hand_rot(f, p, side):
    z = -np.asarray(f, float); z /= np.linalg.norm(z)
    pp = np.asarray(p, float); pp = pp - np.dot(pp, z) * z
    if np.linalg.norm(pp) < 1e-6:
        pp = np.cross(z, (0, 0, 1.0))
    pp /= np.linalg.norm(pp)
    x = pp if side == 'R' else -pp
    y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def items(pose, base=None, mats=None, glitch_head=None):
    """Return [(mesh, M, mat)] for the man in this pose. glitch_head: name of an exploded head mesh to use."""
    base = np.eye(4) if base is None else base
    rx, ry, rz, yaw = pose.get('root', (0, 0, 0, 0))
    Wroot = base @ T((rx, ry, rz)) @ R3(euler(0, 0, math.radians(yaw)))
    lp, lr = pose.get('lean', (0, 0))
    Wt = Wroot @ T(HIPS) @ R3(euler(math.radians(lp), math.radians(lr), 0))
    hp, hy, hr = pose.get('head', (0, 0, 0))
    Wh = Wt @ T(HEAD - HIPS) @ R3(euler(math.radians(hp), math.radians(hr), math.radians(hy)))
    out = []
    mats = mats or {}

    def m(nm):
        d = dict(MAT.get(nm, {})); d.update(mats.get(nm, {})); return d

    for nm in HEAD_PARTS:
        mesh = glitch_head.get(nm, nm) if glitch_head else nm
        out.append((mesh, Wh, m(nm)))
    for nm in TORSO_PARTS:
        out.append((nm, Wt, m(nm)))
    out.append(('legs', Wroot, m('legs'))); out.append(('shoes', Wroot, m('shoes')))
    for s in ('R', 'L'):
        arm = pose.get(s, REST[s])
        sd = SIDE[s]
        S = SHOULDER[s] - HIPS
        Tt = np.asarray(arm['w'], float)
        pole = S + np.array([sd * 0.30, 0.22, -0.30]) + np.asarray(arm.get('pole', (0, 0, 0)), float)
        E, Tt = ik(S, Tt, UPPER, FORE, pole)
        hint_up = np.cross(E - S, pole - S)
        Ru = _frame(E - S, hint_up if np.linalg.norm(hint_up) > 1e-6 else (1, 0, 0))
        Rf = _frame(Tt - E, hint_up if np.linalg.norm(hint_up) > 1e-6 else (1, 0, 0))
        Rh = hand_rot(arm['f'], arm['p'], s)
        out.append((f'upper_{s}', Wt @ T(S) @ R3(Ru), m('upper')))
        out.append((f'fore_{s}', Wt @ T(E) @ R3(Rf), m('fore')))
        out.append((f'hand_{arm.get("g", "relax")}_{s}', Wt @ T(Tt) @ R3(Rh), m('hand')))
    return out


# ------------------------------------------------------------------ pose blending
def _norm(v):
    v = np.asarray(v, float); return v / max(np.linalg.norm(v), 1e-9)


def ease(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def blend(a, b, t):
    """Blend two poses (t in 0..1, already eased)."""
    out = {}
    for k in ('root', 'lean', 'head'):
        va, vb = np.asarray(a.get(k, REST[k]), float), np.asarray(b.get(k, REST[k]), float)
        out[k] = tuple(va + (vb - va) * t)
    for s in ('R', 'L'):
        A, B = a.get(s, REST[s]), b.get(s, REST[s])
        w = np.asarray(A['w'], float) + (np.asarray(B['w'], float) - np.asarray(A['w'], float)) * t
        # lift the hand a little mid-move so it doesn't pass through the body
        lift = 4 * t * (1 - t) * np.array([0, -0.05, 0.02]) * (np.linalg.norm(np.asarray(B['w']) - np.asarray(A['w'])) > 0.12)
        out[s] = dict(w=tuple(w + lift), f=tuple(_norm(_norm(A['f']) * (1 - t) + _norm(B['f']) * t)),
                      p=tuple(_norm(_norm(A['p']) * (1 - t) + _norm(B['p']) * t)),
                      g=A.get('g', 'relax') if t < 0.5 else B.get('g', 'relax'),
                      pole=tuple(np.asarray(A.get('pole', (0, 0, 0)), float) * (1 - t) + np.asarray(B.get('pole', (0, 0, 0)), float) * t))
    return out


def merge(base, over):
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in over.items():
        out[k] = v
    return out


def track(keys, t, dur=0.45):
    """keys: list of (time, pose-overrides) sorted by time; each pose holds from its time; moves take `dur` s
    (or the key's own 'dur'), easing in from the previous pose."""
    pose = merge(REST, keys[0][1]) if keys else dict(REST)
    for i in range(1, len(keys)):
        tk, over = keys[i]
        d = over.get('dur', dur)
        if t <= tk:
            break
        target = merge(pose, {k: v for k, v in over.items() if k != 'dur'})
        pose = blend(pose, target, ease((t - tk) / d)) if t < tk + d else target
    return pose


def add_life(pose, t, env=0.0, seed=0.0, amt=1.0):
    """Breathing, sway, micro head motion and speech nods (env: 0..1 speech emphasis at this moment)."""
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in pose.items()}
    lp, lr = p.get('lean', (0, 0))
    br = math.sin(2 * math.pi * 0.23 * t + seed)
    p['lean'] = (lp + amt * (0.5 * br + 0.35 * math.sin(2 * math.pi * 0.07 * t + 1.3 + seed)),
                 lr + amt * 0.5 * math.sin(2 * math.pi * 0.11 * t + 0.4 + seed))
    hp, hy, hr = p.get('head', (0, 0, 0))
    n1 = math.sin(2 * math.pi * 0.31 * t + seed * 2) + 0.5 * math.sin(2 * math.pi * 0.73 * t + 1.1)
    n2 = math.sin(2 * math.pi * 0.19 * t + 2.2 + seed) + 0.4 * math.sin(2 * math.pi * 0.57 * t)
    p['head'] = (hp + amt * (0.8 * n1 + 5.0 * env), hy + amt * 1.2 * n2, hr + amt * 0.6 * math.sin(2 * math.pi * 0.17 * t + 0.7))
    return p


def explode(d, amt, seed=7, swirl=1.0):
    """Exploded copy of a part's triangle soup: each facet flies out along its normal and spins about its centre."""
    rng = np.random.default_rng(seed)
    P = d['pos'].reshape(-1, 3, 3).astype(np.float64)
    n = len(P)
    c = P.mean(1, keepdims=True)
    nrm = d['nrm'].reshape(-1, 3, 3)[:, 0]
    dist = amt * (0.02 + 0.10 * rng.random(n)) ** 1.0
    ax = rng.normal(size=(n, 3)); ax /= np.linalg.norm(ax, axis=1, keepdims=True)
    ang = amt * swirl * rng.normal(0, 1.2, n)
    out = np.empty_like(P)
    for i in range(n):
        k = ax[i]; a = ang[i]
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        R = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * (K @ K)
        out[i] = (P[i] - c[i]) @ R.T + c[i] + nrm[i] * dist[i] + rng.normal(0, 0.15, 3) * amt * 0.05
    e1, e2 = out[:, 1] - out[:, 0], out[:, 2] - out[:, 0]
    nn = np.cross(e1, e2); nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)
    return dict(pos=out.reshape(-1, 3).astype(np.float32), nrm=np.repeat(nn[:, None], 3, 1).reshape(-1, 3).astype(np.float32),
                uv=d['uv'], col=d['col'])
