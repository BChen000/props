import os
import numpy as np, json, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.environ.get('GRIFFIN_CACHE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), '')
os.makedirs(CACHE, exist_ok=True)
from sdf import Prim, build_mesh, taubin, weights, field
from scipy.spatial import cKDTree


def rotx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def roty(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rotz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def A(feath=0.0, pale=0.0, dark=0.0, belly=0.0, gold=0.0):
    return {'feath': feath, 'pale': pale, 'dark': dark, 'belly': belly, 'gold': gold}


P = []
# torso
P.append(Prim('ell', 'chest', k=0.0, attrs=A(feath=0.35), c=(0, -0.42, 0.97), r=(0.29, 0.36, 0.36)))
P.append(Prim('ell', 'spine', k=0.10, attrs=A(), c=(0, 0.02, 0.93), r=(0.26, 0.46, 0.29)))
P.append(Prim('ell', 'spine', k=0.10, attrs=A(belly=1.0), c=(0, 0.02, 0.78), r=(0.21, 0.40, 0.17)))
P.append(Prim('ell', 'hips', k=0.10, attrs=A(), c=(0, 0.50, 0.93), r=(0.25, 0.30, 0.28)))
P.append(Prim('ell', 'hips', k=0.08, attrs=A(), c=(0, 0.64, 0.99), r=(0.20, 0.20, 0.19)))
P.append(Prim('ell', 'chest', k=0.08, attrs=A(belly=0.6, feath=0.6, pale=0.3), c=(0, -0.58, 0.88), r=(0.24, 0.20, 0.30)))
for s in (1, -1):
    P.append(Prim('ell', 'chest', k=0.08, attrs=A(feath=0.2), c=(s * 0.17, -0.44, 1.05), r=(0.13, 0.22, 0.24)))
# neck with ruff
P.append(Prim('cone', 'neck1', k=0.10, attrs=A(feath=1.0, gold=0.5), a=(0, -0.62, 1.08), b=(0, -0.86, 1.42), r1=0.25, r2=0.165))
P.append(Prim('cone', 'neck2', k=0.06, attrs=A(feath=1.0, gold=1.0), a=(0, -0.86, 1.42), b=(0, -0.97, 1.63), r1=0.165, r2=0.135))
P.append(Prim('ell', 'neck1', k=0.10, attrs=A(feath=1.0, gold=0.3, pale=0.2), c=(0, -0.76, 1.15), r=(0.27, 0.22, 0.30)))
# head
P.append(Prim('ell', 'head', k=0.06, attrs=A(feath=1.0, gold=1.0), c=(0, -1.07, 1.745), r=(0.125, 0.185, 0.125)))
P.append(Prim('ell', 'head', k=0.05, attrs=A(feath=1.0, gold=0.8), c=(0, -0.99, 1.80), r=(0.11, 0.13, 0.09)))
for s in (1, -1):
    P.append(Prim('ell', 'head', k=0.035, attrs=A(feath=1.0, gold=0.2, dark=0.2), c=(s * 0.072, -1.165, 1.805), r=(0.055, 0.095, 0.038), R=rotz(s * 0.22) @ rotx(-0.18)))
    P.append(Prim('ell', 'head', k=0.05, attrs=A(feath=1.0, pale=0.5), c=(s * 0.07, -1.12, 1.685), r=(0.075, 0.12, 0.085)))
for s_ in (1, -1):
    P.append(Prim('cone', 'head', k=0.035, attrs=A(feath=1.0, gold=1.0, dark=0.25), a=(s_ * 0.07, -1.01, 1.82), b=(s_ * 0.125, -0.90, 1.995), r1=0.048, r2=0.009))
# front (eagle) legs, feathered to the toes
for side, s in (('L', 1), ('R', -1)):
    P.append(Prim('cone', 'f_up_' + side, k=0.07, attrs=A(feath=1.0, pale=0.3), a=(s * 0.19, -0.48, 0.92), b=(s * 0.21, -0.56, 0.55), r1=0.15, r2=0.11))
    P.append(Prim('cone', 'f_low_' + side, k=0.05, attrs=A(feath=1.0, pale=0.4), a=(s * 0.21, -0.56, 0.55), b=(s * 0.21, -0.60, 0.15), r1=0.105, r2=0.072))
    P.append(Prim('ell', 'f_foot_' + side, k=0.04, attrs=A(feath=1.0, pale=0.4), c=(s * 0.21, -0.635, 0.09), r=(0.075, 0.095, 0.06)))
    # hind (lion) legs
    P.append(Prim('ell', 'h_thigh_' + side, k=0.09, attrs=A(), c=(s * 0.19, 0.50, 0.76), r=(0.135, 0.24, 0.30), R=rotx(0.25)))
    P.append(Prim('cone', 'h_shin_' + side, k=0.06, attrs=A(), a=(s * 0.21, 0.44, 0.52), b=(s * 0.21, 0.72, 0.22), r1=0.10, r2=0.06))
    P.append(Prim('cone', 'h_meta_' + side, k=0.04, attrs=A(), a=(s * 0.21, 0.72, 0.22), b=(s * 0.21, 0.66, 0.07), r1=0.06, r2=0.052))
    P.append(Prim('ell', 'h_paw_' + side, k=0.04, attrs=A(belly=0.3), c=(s * 0.21, 0.585, 0.056), r=(0.085, 0.12, 0.056)))
    for j, dx in enumerate((-0.05, -0.017, 0.017, 0.05)):
        P.append(Prim('sph', 'h_paw_' + side, k=0.025, attrs=A(belly=0.3), c=(s * 0.21 + dx, 0.495 + abs(dx) * 0.4, 0.042), r=0.033))
# tail
pts = [(0, 0.78, 1.02), (0, 1.02, 0.98), (0, 1.25, 0.88), (0, 1.45, 0.74), (0, 1.62, 0.60), (0, 1.78, 0.50)]
rad = [0.075, 0.06, 0.05, 0.043, 0.038, 0.035]
for i in range(5):
    P.append(Prim('cone', f'tail{i+1}', k=0.03, attrs=A(), a=pts[i], b=pts[i + 1], r1=rad[i], r2=rad[i + 1]))
P.append(Prim('ell', 'tail5', k=0.03, attrs=A(dark=1.0), c=(0, 1.84, 0.46), r=(0.048, 0.085, 0.05), R=rotx(0.5)))

BONES = [
    ('root', (0, 0, 0), (0, 0, 0.3), None, (0, -1, 0)),
    ('hips', (0, 0.55, 0.95), (0, 0.05, 0.95), 'root', (0, 0, 1)),
    ('spine', (0, 0.05, 0.95), (0, -0.40, 1.00), 'hips', (0, 0, 1)),
    ('chest', (0, -0.40, 1.00), (0, -0.70, 1.12), 'spine', (0, 0, 1)),
    ('neck1', (0, -0.70, 1.12), (0, -0.86, 1.42), 'chest', (0, -1, 0)),
    ('neck2', (0, -0.86, 1.42), (0, -0.97, 1.64), 'neck1', (0, -1, 0)),
    ('head', (0, -0.97, 1.64), (0, -1.22, 1.74), 'neck2', (0, 0, 1)),
    ('jaw', (0, -1.20, 1.69), (0, -1.33, 1.62), 'head', (0, 0, 1)),
]
for i in range(5):
    BONES.append((f'tail{i+1}', pts[i], pts[i + 1], 'hips' if i == 0 else f'tail{i}', (0, 0, 1)))
for side, s in (('L', 1), ('R', -1)):
    BONES += [
        ('f_up_' + side, (s * 0.19, -0.48, 0.92), (s * 0.21, -0.56, 0.55), 'chest', (0, -1, 0)),
        ('f_low_' + side, (s * 0.21, -0.56, 0.55), (s * 0.21, -0.60, 0.13), 'f_up_' + side, (0, -1, 0)),
        ('f_foot_' + side, (s * 0.21, -0.60, 0.13), (s * 0.21, -0.78, 0.06), 'f_low_' + side, (0, 0, 1)),
        ('h_thigh_' + side, (s * 0.19, 0.52, 0.95), (s * 0.21, 0.44, 0.52), 'hips', (0, -1, 0)),
        ('h_shin_' + side, (s * 0.21, 0.44, 0.52), (s * 0.21, 0.72, 0.22), 'h_thigh_' + side, (0, 1, 0)),
        ('h_meta_' + side, (s * 0.21, 0.72, 0.22), (s * 0.21, 0.66, 0.06), 'h_shin_' + side, (0, -1, 0)),
        ('h_paw_' + side, (s * 0.21, 0.66, 0.06), (s * 0.21, 0.52, 0.04), 'h_meta_' + side, (0, 0, 1)),
        ('w_hum_' + side, (s * 0.20, -0.38, 1.18), (s * 0.78, -0.32, 1.26), 'chest', (0, 0, 1)),
        ('w_fore_' + side, (s * 0.78, -0.32, 1.26), (s * 1.58, -0.40, 1.29), 'w_hum_' + side, (0, 0, 1)),
        ('w_hand_' + side, (s * 1.58, -0.40, 1.29), (s * 2.25, -0.30, 1.28), 'w_fore_' + side, (0, 0, 1)),
    ]


def wing_tube_prims(side):
    s = 1 if side == 'L' else -1
    Q = []
    Q.append(Prim('cone', 'w_hum_' + side, k=0.0, attrs=A(feath=1.0), a=(s * 0.16, -0.38, 1.17), b=(s * 0.78, -0.32, 1.26), r1=0.12, r2=0.07))
    Q.append(Prim('cone', 'w_fore_' + side, k=0.04, attrs=A(feath=1.0), a=(s * 0.78, -0.32, 1.26), b=(s * 1.58, -0.40, 1.29), r1=0.07, r2=0.048))
    Q.append(Prim('cone', 'w_hand_' + side, k=0.03, attrs=A(feath=1.0, dark=0.3), a=(s * 1.58, -0.40, 1.29), b=(s * 2.22, -0.31, 1.28), r1=0.048, r2=0.03))
    return Q


def surface_point(origin, direction, prims, maxd=0.5):
    o = np.asarray(origin, float); d = np.asarray(direction, float); d /= np.linalg.norm(d)
    ts = np.linspace(0, maxd, 4000)
    pts_ = o[None, :] + ts[:, None] * d[None, :]
    f = field(prims, pts_)
    i = np.where(f > 0)[0][0]
    return pts_[i]


if __name__ == '__main__':
    t0 = time.time()
    v, f = build_mesh(P, h=0.0105, margin=0.04)
    v = taubin(v, f, iters=10)
    bones = [b[0] for b in BONES]
    W, At = weights(P, v, f, bones, falloff=0.03)
    print('body verts', len(v), 'faces', len(f), round(time.time() - t0, 1))
    rng = np.random.default_rng(3)
    lo, hi = v.min(0) - 0.1, v.max(0) + 0.1
    pts2 = lo + rng.random((20000, 3)) * (hi - lo)
    d2, _ = cKDTree(pts2).query(v, k=1)
    var = 0.9 + 0.18 * np.clip(d2 / 0.06, 0, 1)
    out = dict(v=v, f=f, W=W, var=var, **{k: At[k] for k in At})
    np.savez(CACHE + 'adult_body.npz', **out)
    for side in ('L', 'R'):
        Q = wing_tube_prims(side)
        vw, fw = build_mesh(Q, h=0.008, margin=0.03)
        vw = taubin(vw, fw, iters=8)
        Ww, Aw = weights(Q, vw, fw, bones, falloff=0.03)
        # blend root of tube into chest
        s = 1 if side == 'L' else -1
        rootw = np.clip((0.40 - np.abs(vw[:, 0])) / 0.2, 0, 1)
        ci = bones.index('chest'); hi_ = bones.index('w_hum_' + side)
        Ww[:, ci] += rootw * Ww[:, hi_]
        Ww[:, hi_] *= (1 - rootw)
        np.savez(CACHE + f'adult_wingtube_{side}.npz', v=vw, f=fw, W=Ww)
    acc = {}
    for side, s in (('L', 1), ('R', -1)):
        d = np.array([s * 0.60, -0.80, 0.02]); d /= np.linalg.norm(d)
        sp_ = surface_point((s * 0.02, -1.10, 1.755), d, P)
        r = 0.027
        acc['eye_' + side] = {'center': (sp_ - d * r * 0.55).tolist(), 'radius': r, 'dir': d.tolist()}
        acc['foot_' + side] = {'center': (s * 0.21, -0.665, 0.058)}
    bd = np.array([0, -0.90, -0.30]); bd /= np.linalg.norm(bd)
    bp = surface_point((0, -1.08, 1.72), bd, P)
    acc['beak'] = {'base': (bp - bd * 0.03).tolist(), 'dir': bd.tolist()}
    json.dump({'bones': BONES, 'acc': acc}, open(CACHE + 'adult_rig.json', 'w'), indent=1)
    print('done', round(time.time() - t0, 1), acc['beak'], acc['eye_L'])
