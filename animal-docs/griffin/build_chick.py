import os
import numpy as np, json, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.environ.get('GRIFFIN_CACHE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), '')
os.makedirs(CACHE, exist_ok=True)
from sdf import Prim, build_mesh, taubin, weights, field

def rotx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def rotz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

P = []
T = lambda v: {'tawny': v}
P.append(Prim('ell', 'spine', k=0.0, attrs={'tawny': 0.6, 'len': 1.0, 'dens': 1.0}, c=(0, 0.02, 0.15), r=(0.10, 0.16, 0.095)))
P.append(Prim('ell', 'chest', k=0.04, attrs={'tawny': 0.0, 'len': 1.0, 'dens': 1.0}, c=(0, -0.075, 0.17), r=(0.095, 0.085, 0.095)))
P.append(Prim('ell', 'hips', k=0.04, attrs={'tawny': 1.0, 'len': 0.9, 'dens': 1.0}, c=(0, 0.12, 0.145), r=(0.095, 0.09, 0.085)))
P.append(Prim('ell', 'spine', k=0.04, attrs={'tawny': 0.35, 'len': 1.0, 'dens': 1.0}, c=(0, 0.005, 0.11), r=(0.08, 0.11, 0.06)))
P.append(Prim('cone', 'neck', k=0.04, attrs={'tawny': 0.0, 'len': 0.9, 'dens': 1.0}, a=(0, -0.10, 0.19), b=(0, -0.135, 0.245), r1=0.07, r2=0.062))
P.append(Prim('sph', 'head', k=0.035, attrs={'tawny': 0.0, 'len': 0.62, 'dens': 1.0, 'face': 1.0}, c=(0, -0.15, 0.30), r=0.09))
for sx in (1, -1):
    P.append(Prim('ell', 'head', k=0.03, attrs={'tawny': 0.0, 'len': 0.45, 'dens': 1.0, 'face': 1.0}, c=(sx * 0.035, -0.185, 0.283), r=(0.05, 0.055, 0.05)))
P.append(Prim('ell', 'head', k=0.03, attrs={'tawny': 0.0, 'len': 0.5, 'dens': 1.0, 'face': 1.0}, c=(0, -0.18, 0.325), r=(0.06, 0.06, 0.05)))
for side, sx in (('L', 1), ('R', -1)):
    R = rotz(sx * 0.25) @ rotx(0.45)
    P.append(Prim('ell', 'wing_' + side, k=0.02, attrs={'tawny': 0.1, 'len': 0.85, 'dens': 1.0}, c=(sx * 0.097, -0.03, 0.205), r=(0.026, 0.062, 0.03), R=R))
    P.append(Prim('cone', 'f_up_' + side, k=0.03, attrs={'tawny': 0.0, 'len': 0.9, 'dens': 1.0}, a=(sx * 0.062, -0.085, 0.15), b=(sx * 0.066, -0.10, 0.075), r1=0.042, r2=0.033))
    P.append(Prim('cone', 'f_low_' + side, k=0.02, attrs={'tawny': 0.0, 'len': 0.75, 'dens': 1.0}, a=(sx * 0.066, -0.10, 0.075), b=(sx * 0.066, -0.106, 0.03), r1=0.033, r2=0.029))
    P.append(Prim('ell', 'f_foot_' + side, k=0.015, attrs={'tawny': 0.0, 'len': 0.45, 'dens': 0.8}, c=(sx * 0.066, -0.114, 0.022), r=(0.03, 0.034, 0.021)))
    P.append(Prim('ell', 'h_thigh_' + side, k=0.03, attrs={'tawny': 1.0, 'len': 0.9, 'dens': 1.0}, c=(sx * 0.07, 0.125, 0.125), r=(0.045, 0.065, 0.07)))
    P.append(Prim('cone', 'h_shin_' + side, k=0.025, attrs={'tawny': 1.0, 'len': 0.7, 'dens': 1.0}, a=(sx * 0.075, 0.15, 0.085), b=(sx * 0.075, 0.13, 0.035), r1=0.034, r2=0.029))
    P.append(Prim('ell', 'h_paw_' + side, k=0.02, attrs={'tawny': 0.9, 'len': 0.45, 'dens': 1.0}, c=(sx * 0.075, 0.108, 0.024), r=(0.041, 0.054, 0.025)))
    for j, dx in enumerate((-0.025, -0.0085, 0.0085, 0.025)):
        P.append(Prim('sph', 'h_paw_' + side, k=0.012, attrs={'tawny': 0.9, 'len': 0.35, 'dens': 1.0}, c=(sx * 0.075 + dx, 0.066 + abs(dx) * 0.35, 0.018), r=0.015))
P.append(Prim('cone', 'tail1', k=0.03, attrs={'tawny': 1.0, 'len': 0.5, 'dens': 1.0}, a=(0, 0.20, 0.17), b=(0, 0.27, 0.19), r1=0.026, r2=0.018))
P.append(Prim('cone', 'tail2', k=0.012, attrs={'tawny': 1.0, 'len': 0.32, 'dens': 1.0}, a=(0, 0.27, 0.19), b=(0, 0.33, 0.215), r1=0.018, r2=0.0145))
P.append(Prim('cone', 'tail3', k=0.01, attrs={'tawny': 1.0, 'len': 0.3, 'dens': 1.0}, a=(0, 0.33, 0.215), b=(0, 0.38, 0.25), r1=0.0145, r2=0.012))
P.append(Prim('cone', 'tail3', k=0.008, attrs={'tawny': 1.0, 'len': 0.3, 'dens': 1.0}, a=(0, 0.38, 0.25), b=(0, 0.405, 0.30), r1=0.012, r2=0.011))
P.append(Prim('ell', 'tail3', k=0.01, attrs={'tawny': 1.0, 'len': 1.0, 'dens': 1.0, 'dark': 1.0}, c=(0, 0.41, 0.318), r=(0.019, 0.019, 0.026)))
for sx in (1, -1):
    P.append(Prim('cone', 'head', k=0.02, attrs={'tawny': 0.0, 'len': 0.32, 'dens': 1.0, 'dark': 0.3}, a=(sx * 0.045, -0.125, 0.365), b=(sx * 0.07, -0.092, 0.432), r1=0.024, r2=0.006))

BONES = [
    ('root', (0, 0, 0), (0, 0, 0.06), None, (0, -1, 0)),
    ('hips', (0, 0.12, 0.15), (0, 0.02, 0.155), 'root', (0, 0, 1)),
    ('spine', (0, 0.02, 0.155), (0, -0.06, 0.165), 'hips', (0, 0, 1)),
    ('chest', (0, -0.06, 0.165), (0, -0.105, 0.195), 'spine', (0, 0, 1)),
    ('neck', (0, -0.105, 0.195), (0, -0.14, 0.25), 'chest', (0, -1, 0)),
    ('head', (0, -0.14, 0.25), (0, -0.16, 0.36), 'neck', (0, -1, 0)),
    ('jaw', (0, -0.205, 0.283), (0, -0.245, 0.272), 'head', (0, 0, 1)),
    ('tail1', (0, 0.20, 0.17), (0, 0.27, 0.19), 'hips', (0, 0, 1)),
    ('tail2', (0, 0.27, 0.19), (0, 0.33, 0.215), 'tail1', (0, 0, 1)),
    ('tail3', (0, 0.33, 0.215), (0, 0.41, 0.31), 'tail2', (0, 0, 1)),
]
for side, sx in (('L', 1), ('R', -1)):
    BONES += [
        ('wing_' + side, (sx * 0.075, -0.06, 0.215), (sx * 0.112, 0.01, 0.195), 'chest', (0, 0, 1)),
        ('f_up_' + side, (sx * 0.062, -0.085, 0.16), (sx * 0.066, -0.10, 0.075), 'chest', (0, -1, 0)),
        ('f_low_' + side, (sx * 0.066, -0.10, 0.075), (sx * 0.066, -0.106, 0.025), 'f_up_' + side, (0, -1, 0)),
        ('f_foot_' + side, (sx * 0.066, -0.106, 0.025), (sx * 0.066, -0.146, 0.012), 'f_low_' + side, (0, 0, 1)),
        ('h_thigh_' + side, (sx * 0.068, 0.11, 0.16), (sx * 0.075, 0.15, 0.085), 'hips', (0, -1, 0)),
        ('h_shin_' + side, (sx * 0.075, 0.15, 0.085), (sx * 0.075, 0.13, 0.028), 'h_thigh_' + side, (0, 1, 0)),
        ('h_paw_' + side, (sx * 0.075, 0.13, 0.028), (sx * 0.075, 0.085, 0.016), 'h_shin_' + side, (0, 0, 1)),
    ]

def surface_point(origin, direction, prims, maxd=0.3):
    o = np.asarray(origin, float); d = np.asarray(direction, float); d /= np.linalg.norm(d)
    ts = np.linspace(0, maxd, 3000)
    pts = o[None, :] + ts[:, None] * d[None, :]
    f = field(prims, pts)
    i = np.where(f > 0)[0][0]
    return pts[i], f

if __name__ == '__main__':
    t0 = time.time()
    v, f = build_mesh(P, h=0.0032)
    v = taubin(v, f, iters=12)
    bones = [b[0] for b in BONES]
    W, A = weights(P, v, f, bones, falloff=0.010)
    print('verts', len(v), 'faces', len(f), 'time', round(time.time() - t0, 1))
    acc = {}
    for side, sx in (('L', 1), ('R', -1)):
        d = np.array([sx * 0.47, -0.88, 0.06]); d /= np.linalg.norm(d)
        sp_, _ = surface_point((sx * 0.015, -0.16, 0.308), d, P)
        r = 0.0235
        acc['eye_' + side] = {'center': (sp_ - d * r * 0.62).tolist(), 'radius': r, 'dir': d.tolist()}
    bd = np.array([0, -0.93, -0.36]); bd /= np.linalg.norm(bd)
    bp, _ = surface_point((0, -0.16, 0.30), bd, P)
    acc['beak'] = {'base': (bp - bd * 0.006).tolist(), 'dir': bd.tolist()}
    for side, sx in (('L', 1), ('R', -1)):
        acc['foot_' + side] = {'center': (sx * 0.066, -0.118, 0.016)}
    eyes = np.array([acc['eye_L']['center'], acc['eye_R']['center']])
    de = np.min(np.linalg.norm(v[:, None, :] - eyes[None], axis=2), axis=1)
    dens = A['dens'] * np.clip((de - 0.024) / 0.012, 0, 1)
    db = np.linalg.norm(v - np.array(acc['beak']['base']), axis=1)
    dens = dens * np.clip((db - 0.014) / 0.012, 0, 1)
    ln = A['len'] * np.clip(0.35 + (db - 0.02) / 0.05, 0.35, 1.0)
    rest = v.copy()
    rng = np.random.default_rng(7)
    lo, hi = v.min(0) - 0.05, v.max(0) + 0.05
    pts = lo + rng.random((900, 3)) * (hi - lo)
    from scipy.spatial import cKDTree
    dd, _ = cKDTree(pts).query(v, k=1)
    spot = np.clip((0.022 - dd) / 0.010, 0, 1) * np.clip((A['tawny'] - 0.5) / 0.4, 0, 1)
    pts2 = lo + rng.random((4000, 3)) * (hi - lo)
    d2, _ = cKDTree(pts2).query(v, k=2)
    var = 0.95 + 0.07 * np.clip(d2[:, 0] / 0.02, 0, 1)
    np.savez(CACHE + 'chick_mesh.npz', v=v, f=f, W=W, tawny=A['tawny'], dark=A.get('dark', np.zeros(len(v))),
             face=A.get('face', np.zeros(len(v))), hlen=ln, hdens=dens, rest=rest, spot=spot, var=var)
    json.dump({'bones': BONES, 'acc': acc}, open(CACHE + 'chick_rig.json', 'w'), indent=1)
    print('eyes', acc['eye_L'], 'beak', acc['beak'])
