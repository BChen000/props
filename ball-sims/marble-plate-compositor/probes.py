"""Turns the probe cube maps from render_plates.py into lat-long maps + spherical-harmonic irradiance.

Run:  python3 probes.py        ->  build/probes_proc.npz
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from settings import *
import numpy as np

FACES = {'px': ((1, 0, 0), (0, 0, 1)), 'nx': ((-1, 0, 0), (0, 0, 1)), 'py': ((0, 1, 0), (0, 0, 1)),
         'ny': ((0, -1, 0), (0, 0, 1)), 'pz': ((0, 0, 1), (0, -1, 0)), 'nz': ((0, 0, -1), (0, 1, 0))}
FN = list(FACES.keys())
EQ_H, EQ_W = 256, 512
BLUR_SIGMA = 3.0          # blur of the lat-long map used for metal marbles


def eq_dirs(H=EQ_H, W=EQ_W):
    v = (np.arange(H) + 0.5) / H
    u = (np.arange(W) + 0.5) / W
    lat = np.pi / 2 - v * np.pi
    lon = u * 2 * np.pi - np.pi
    lat, lon = np.meshgrid(lat, lon, indexing='ij')
    d = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], -1)
    dA = (np.pi / H) * (2 * np.pi / W) * np.cos(lat)
    return d, dA


def cube_lookup(faces, d):
    n = faces.shape[1]
    ad = np.abs(d)
    out = np.zeros(d.shape[:-1] + (3,), np.float32)
    for fi, fn in enumerate(FN):
        fwd, up = FACES[fn]
        fwd = np.array(fwd, float); up = np.array(up, float)
        right = np.cross(fwd, up)
        ax = int(np.argmax(np.abs(fwd))); sg = fwd[ax]
        m = (np.argmax(ad, -1) == ax) & (np.sign(d[..., ax]) == sg)
        dd = d[m]
        z = dd @ fwd
        uu = (dd @ right) / z
        vv = (dd @ up) / z
        px = (uu + 1) / 2 * n - 0.5
        py = (1 - vv) / 2 * n - 0.5
        x0 = np.clip(np.floor(px).astype(int), 0, n - 1); y0 = np.clip(np.floor(py).astype(int), 0, n - 1)
        x1 = np.clip(x0 + 1, 0, n - 1); y1 = np.clip(y0 + 1, 0, n - 1)
        fx = np.clip(px - x0, 0, 1)[:, None]; fy = np.clip(py - y0, 0, 1)[:, None]
        F = faces[fi]
        out[m] = (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x1] * fx * (1 - fy) + F[y1, x0] * (1 - fx) * fy + F[y1, x1] * fx * fy)
    return out


def sh_basis(d):
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    return np.stack([0.282095 * np.ones_like(x), 0.488603 * y, 0.488603 * z, 0.488603 * x,
                     1.092548 * x * y, 1.092548 * y * z, 0.315392 * (3 * z * z - 1), 1.092548 * x * z, 0.546274 * (x * x - y * y)], -1)


A_HAT = np.array([np.pi, 2 * np.pi / 3, 2 * np.pi / 3, 2 * np.pi / 3, np.pi / 4, np.pi / 4, np.pi / 4, np.pi / 4, np.pi / 4])


def light_mask(p, d, L):
    M = np.array(L['matrix'])
    R = M[:3, :3]; c = M[:3, 3]
    sx, sy = L['size']
    nrm = R[:, 2]
    denom = d @ nrm
    t = ((c - p) @ nrm) / np.where(np.abs(denom) < 1e-9, 1e-9, denom)
    hit = p + t[..., None] * d
    loc = (hit - c) @ R
    return (t > 0) & (np.abs(loc[..., 0]) <= sx / 2) & (np.abs(loc[..., 1]) <= sy / 2) & (denom > 0)


def build():
    import cv2
    meta = json.load(open(SCENE_META))
    P = np.array(json.load(open(os.path.join(PLATE_DIR, 'probes.json'))))
    d, dA = eq_dirs()
    Y = sh_basis(d)
    eqs, shs = [], []
    for i in range(len(P)):
        faces = np.stack([np.load(os.path.join(PLATE_DIR, f'probe{i}_{fn}.npy')) for fn in FN])
        eq = cube_lookup(faces, d)
        eqs.append(eq)
        co = {}
        mk = light_mask(P[i], d, meta['lights']['key'])
        mt = light_mask(P[i], d, meta['lights']['top'])
        for nm, mask in (('all', None), ('key', mk), ('top', mt)):
            Lr = eq if mask is None else eq * mask[..., None]
            co[nm] = np.einsum('hwk,hwc,hw->kc', Y, Lr, dA)
        shs.append(np.stack([co['all'] - co['key'] - co['top'], co['key'], co['top']]))
    eqs = np.stack(eqs).astype(np.float32)
    shs = np.stack(shs).astype(np.float32)

    def wblur(e, sg):
        pad = int(4 * sg) + 2
        ep = np.pad(e, ((0, 0), (pad, pad), (0, 0)), mode='wrap')
        b = cv2.GaussianBlur(ep, (0, 0), sg, borderType=cv2.BORDER_REFLECT)
        return b[:, pad:-pad]
    blur = np.stack([wblur(e, BLUR_SIGMA) for e in eqs]).astype(np.float32)
    np.savez(PROBES_FILE, pos=P, eq=eqs, eqb=blur, sh=shs)
    return P, eqs, shs


if __name__ == '__main__':
    P, eqs, shs = build()
    print('saved', PROBES_FILE, P.shape, eqs.shape, shs.shape)
