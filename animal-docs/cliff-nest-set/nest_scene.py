import os
import bpy, math, sys
import numpy as np
from mathutils import Vector, Matrix, Euler
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, '..', 'griffin')):  # blib.py lives in ../griffin
    if _p not in sys.path:
        sys.path.insert(0, _p)
import blib, env
from env import _vnoise

NEST_C = Vector((0.0, -0.35, 0.0))


def fbm(X, Y, oct=5, seed=0, ridged=False, gain=0.5):
    out = np.zeros_like(X); amp = 1.0; fr = 1.0
    for o in range(oct):
        n = _vnoise(X * fr, Y * fr, seed + 31 * o)
        if ridged:
            n = (1 - np.abs(n)) ** 2
        out += amp * n; amp *= gain; fr *= 2.03
    return out


def sheet(name, U, V, P, mat, coll=None, flip=False):
    nu, nv = U.shape
    v = P.reshape(-1, 3)
    idx = np.arange(nu * nv).reshape(nu, nv)
    a = idx[:-1, :-1].ravel(); b = idx[1:, :-1].ravel(); c = idx[1:, 1:].ravel(); d = idx[:-1, 1:].ravel()
    f = np.stack([a, b, c, d], 1) if not flip else np.stack([a, d, c, b], 1)
    ob = blib.mesh_obj(name, v, f, coll=coll)
    ob.data.materials.append(mat)
    return ob


def ledge_top_fn(X, Y):
    # flat-ish top with rounded falloff at front (y<-1.3) and sides (|x|>2)
    top = 0.035 * fbm(X * 2.2, Y * 2.2, 4, seed=3) + 0.012 * fbm(X * 9, Y * 9, 3, seed=5)
    ex = np.maximum(0, np.abs(X) - 1.9 - 0.25 * fbm(Y * 0.8, X * 0.3, 2, seed=9))
    ey = np.maximum(0, -Y - 1.25 - 0.18 * fbm(X * 1.3, Y * 0.2, 3, seed=11))
    e = np.sqrt(ex * ex + ey * ey)
    drop = -(e ** 2) * 6.0 - e * 1.5
    return top + drop


def build(coll=None, with_nest=True, res=0.035, wide=False, drop=None):
    """drop=False hides the long drop face (as the 'nodrop' argv flag does); None follows sys.argv."""
    if drop is None:
        drop = 'nodrop' not in sys.argv
    m_rock = env.mat_rock('rock', scale=1.0)
    objs = {'rock_mat': m_rock}
    # ledge top
    xs = np.arange(-2.8, 2.8, res); ys = np.arange(-2.3, 1.0, res)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = ledge_top_fn(X, Y)
    Z = np.maximum(Z, -2.5 if 'oldgeo' in sys.argv else -45.0)
    objs['ledge'] = sheet('ledge', X, Y, np.stack([X, Y, Z], -1), m_rock, coll)
    # back wall (vertical sheet facing -y)
    xs = np.arange(-9, 9, res * 2.2) if not wide else np.arange(-26, 26, 0.12); zs = np.arange(-1.0, 9, res * 2.2) if not wide else np.arange(-1.0, 24, 0.12)
    if 'oldgeo' not in sys.argv:
        zs = np.concatenate([np.arange(-60.0, -1.0, 0.3), zs])
    X, Zg = np.meshgrid(xs, zs, indexing='ij')
    D = 0.55 * fbm(X * 0.25, Zg * 0.25, 4, seed=21) + 0.18 * fbm(X * 1.1, Zg * 0.35, 4, seed=22, ridged=True) + 0.05 * fbm(X * 4, Zg * 4, 3, seed=23)
    Yw = 0.85 + D + 0.12 * np.maximum(0, Zg - 2.5)
    objs['wall'] = sheet('wall', X, Zg, np.stack([X, Yw, Zg], -1), m_rock, coll, flip=True)
    # drop face below ledge
    xs = np.arange(-10, 10, 0.12) if not wide else np.arange(-34, 34, 0.25); zs = np.arange(-60, -0.3, 0.12) if not wide else np.arange(-170, -0.3, 0.25)
    X, Zg = np.meshgrid(xs, zs, indexing='ij')
    D = 0.9 * fbm(X * 0.15, Zg * 0.12, 4, seed=31) + 0.35 * fbm(X * 0.7, Zg * 0.2, 4, seed=32, ridged=True) + 0.08 * fbm(X * 3, Zg * 3, 3, seed=33)
    Yd = -1.55 + D + 0.02 * Zg
    if 'oldgeo' not in sys.argv:
        ax = np.abs(X)
        tt = np.clip((ax - 2.0) / 2.6, 0, 1)
        Yd = Yd + 2.35 * tt * tt * (3 - 2 * tt)
    objs['drop'] = sheet('drop', X, Zg, np.stack([X, Yd, Zg], -1), m_rock, coll, flip=True)
    if not drop:
        objs['drop'].hide_render = True; objs['drop'].hide_viewport = True
    if with_nest:
        z = height_at(objs['ledge'], NEST_C.x, NEST_C.y)
        sticks, lining = env.nest('nest', center=(NEST_C.x, NEST_C.y, z - 0.02), r_out=0.52, r_in=0.24, coll=coll)
        objs['sticks'] = sticks; objs['lining'] = lining
        objs['nest_z'] = z
    return objs


def height_at(ob, x, y, top=5.0):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    mw = ob.matrix_world
    inv = mw.inverted()
    o = inv @ Vector((x, y, top)); d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, nrm, idx = ob.evaluated_get(dg).ray_cast(o, d)
    return (mw @ loc).z if hit else None
