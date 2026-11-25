"""Rubber duck mesh from a signed distance field + marching cubes (scikit-image). Imported by scene.add_duck()."""
import numpy as np
from skimage.measure import marching_cubes


def rotY(p, ang):
    c, s = np.cos(ang), np.sin(ang)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    return np.stack([c * x + s * z, y, -s * x + c * z], -1)


def ell(p, c, r, tilt=0.0):
    q = p - np.asarray(c)
    if tilt:
        q = rotY(q, tilt)
    k0 = np.linalg.norm(q / np.asarray(r), axis=-1)
    return (k0 - 1.0) * min(r)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def body_sdf(p):
    d = ell(p, (-0.02, 0, 0.17), (0.56, 0.42, 0.31))
    d = smin(d, ell(p, (0.20, 0, 0.22), (0.36, 0.37, 0.31)), 0.10)
    d = smin(d, ell(p, (-0.47, 0, 0.36), (0.20, 0.15, 0.11), tilt=0.65), 0.12)
    d = smin(d, ell(p, (0.25, 0, 0.66), (0.27, 0.26, 0.26)), 0.13)
    for sy in (1, -1):
        d = smin(d, ell(p, (-0.10, sy * 0.36, 0.27), (0.30, 0.09, 0.15), tilt=-0.25), 0.05)
    d = np.maximum(d, -(p[..., 2] + 0.12))
    return d


def beak_sdf(p):
    d = ell(p, (0.50, 0, 0.615), (0.16, 0.13, 0.05), tilt=-0.12)
    d = smin(d, ell(p, (0.47, 0, 0.575), (0.12, 0.10, 0.035), tilt=-0.05), 0.02)
    return d


def mesh_from_sdf(f, lo, hi, step):
    xs = np.arange(lo[0], hi[0] + step, step)
    ys = np.arange(lo[1], hi[1] + step, step)
    zs = np.arange(lo[2], hi[2] + step, step)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([X, Y, Z], -1)
    vol = f(P)
    v, faces, n, _ = marching_cubes(vol, level=0.0, spacing=(step, step, step))
    v = v + np.asarray([xs[0], ys[0], zs[0]])
    return v.astype(np.float32), faces.astype(np.int32)


def build(step=0.012):
    bv, bf = mesh_from_sdf(body_sdf, (-0.75, -0.5, -0.14), (0.62, 0.5, 0.96), step)
    kv, kf = mesh_from_sdf(beak_sdf, (0.3, -0.18, 0.5), (0.72, 0.18, 0.72), step * 0.6)
    eyes = [(0.405, s * 0.145, 0.745) for s in (1, -1)]
    return (bv, bf), (kv, kf), eyes


if __name__ == '__main__':
    (bv, bf), (kv, kf), eyes = build()
    print('body', bv.shape, bf.shape, 'beak', kv.shape, kf.shape)
    print('bbox', bv.min(0), bv.max(0))
