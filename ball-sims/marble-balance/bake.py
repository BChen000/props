"""Paints wood grain, the painted basket and the floorboards into the path-traced G-buffers (boxtrace has no
textures; see ../marble-spin-dish/bake.py for the idea).

Every surface is traced with a flat albedo and gloss 0, so its key-light (D) and sky/bounce (A) layers are albedo x
lighting, and multiplying them by a texture factor per pixel is the same as having traced a textured surface. World
positions come from the depth layer. The beam and baskets get their grain in the beam's own frame, so it turns
with them from pose to pose.

    bake(gprefix, out_prefix, theta, window)   writes out_prefix_D/_A.f32 and links the other layers
"""
import math
import os

import numpy as np

import settings as C
import scene as S

_PERM = np.random.default_rng(1234).permutation(256)
_PERM = np.concatenate([_PERM, _PERM]).astype(np.int64)
_VAL = np.random.default_rng(99).random(256)


def vnoise(x, y, z):
    """3D value noise in [0, 1] (smooth, period 256)."""
    xi, yi, zi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.floor(z).astype(np.int64)
    xf, yf, zf = x - xi, y - yi, z - zi
    xi, yi, zi = xi & 255, yi & 255, zi & 255
    u, v, w = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf), zf * zf * (3 - 2 * zf)

    def h(a, b, c):
        return _VAL[_PERM[_PERM[_PERM[a] + b] + c] & 255]

    x1, y1, z1 = (xi + 1) & 255, (yi + 1) & 255, (zi + 1) & 255
    c000, c100, c010, c110 = h(xi, yi, zi), h(x1, yi, zi), h(xi, y1, zi), h(x1, y1, zi)
    c001, c101, c011, c111 = h(xi, yi, z1), h(x1, yi, z1), h(xi, y1, z1), h(x1, y1, z1)
    a = c000 + u * (c100 - c000)
    b = c010 + u * (c110 - c010)
    c = c001 + u * (c101 - c001)
    d = c011 + u * (c111 - c011)
    e = a + v * (b - a)
    f = c + v * (d - c)
    return e + w * (f - e)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def grain(P, axis, seed):
    """Wood with its fibres along axis: growth rings around a log centre off to one side, wavy and streaky."""
    rg = np.random.default_rng(seed)
    u_ax, v_ax = [k for k in range(3) if k != axis]
    cu, cv = rg.uniform(-30, 30), rg.choice([-1, 1]) * rg.uniform(8, 20)
    warp = 0.7 * (vnoise(P[:, axis] * 0.08 + seed, P[:, u_ax] * 0.4, P[:, v_ax] * 0.4) - 0.5)
    r = np.hypot(P[:, u_ax] - cu, P[:, v_ax] - cv) + warp
    t = (r * rg.uniform(1.4, 1.9)) % 1.0
    late = smooth(0.6, 0.85, t) * (1 - smooth(0.93, 1.0, t))
    streak = vnoise(P[:, axis] * 0.3, P[:, u_ax] * 6.0 + seed, P[:, v_ax] * 6.0)
    f = (1 - 0.16 * late) * (0.96 + 0.08 * streak)
    return np.stack([f * (1 + 0.02 * late), f * (1 - 0.03 * late), f * (1 - 0.10 * late)], 1)


def floorboards(P):
    """Boards running left to right, 7 units wide, with seams and staggered ends."""
    bw = 7.0
    z, x = P[:, 2] + 3.0, P[:, 0]
    row = np.floor(z / bw)
    fz = z / bw - row
    rg = np.random.default_rng(5)
    offs = rg.uniform(0, 60, 64)
    rid = row.astype(np.int64) & 63
    xx = x + offs[rid]
    seg = np.floor(xx / 60.0)
    fx = xx / 60.0 - seg
    tone = 1 + 0.05 * (vnoise(row * 3.1, seg * 1.7, 0.5) - 0.5) * 2
    g = grain(np.stack([xx, P[:, 1], z], 1), 0, 7)
    f = tone[:, None] * g
    seam = np.minimum(fz, 1 - fz) * bw
    endj = np.minimum(fx, 1 - fx) * 60.0
    f *= ((1 - 0.4 * (1 - smooth(0.03, 0.10, seam))) * (1 - 0.3 * (1 - smooth(0.03, 0.08, endj))))[:, None]
    return f


def paint(P):
    f = 0.97 + 0.05 * vnoise(P[:, 0] * 1.3, P[:, 1] * 1.3, P[:, 2] * 1.3)
    return np.stack([f, f, f], 1)


def wall(P):
    f = 0.985 + 0.03 * vnoise(P[:, 0] * 0.15, P[:, 1] * 0.15, 3.0)
    return np.stack([f, f, f], 1)


def texture(P, oid, theta):
    """Texture factor for world points P with object ids oid, the beam turned by theta (radians)."""
    out = np.ones((len(P), 3))
    piv = np.array(C.PIVOT)
    c, s = math.cos(theta), math.sin(theta)
    for k in np.unique(oid):
        m = oid == k
        p = P[m]
        if k in S.MOVING:
            d = p - piv
            p = np.stack([c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1], d[:, 2]], 1)
        if k == S.OID_FLOOR:
            out[m] = floorboards(p)
        elif k == S.OID_WALL:
            out[m] = wall(p)
        elif k == S.OID_LEFT_BASKET:
            out[m] = paint(p)
        elif k in (S.OID_STAND, S.OID_GLASS_TRACK, S.OID_STEEL_TRACK, S.OID_BEAM, S.OID_RIGHT_BASKET):
            out[m] = grain(p, 0, int(k) * 13 + 1)
    return out


def bake(gprefix, out_prefix, theta=0.0, window=None, log=print):
    """window: (x0, y0, w, h) of the 2x image that these files hold (None: the whole image)."""
    W2, H2 = 2 * S.W, 2 * S.H
    x0, y0, w, h = window or (0, 0, W2, H2)
    D = np.fromfile(gprefix + "_D.f32", np.float32).reshape(h, w, 3)
    A = np.fromfile(gprefix + "_A.f32", np.float32).reshape(h, w, 3)
    Z = np.fromfile(gprefix + "_Z.f32", np.float32).reshape(h, w)
    I = np.fromfile(gprefix + "_I.u8", np.uint8).reshape(h, w)
    cam, fwd, right, up = S.camera()
    th = math.tan(S.CAM_FOVY / 2)
    asp = S.W / S.H
    a = ((np.arange(x0, x0 + w) + 0.5) / W2 * 2 - 1 + S.CAM_SHIFT[0]) * th * asp
    b = (1 - (np.arange(y0, y0 + h) + 0.5) / H2 * 2 + S.CAM_SHIFT[1]) * th
    fac = np.ones((h, w, 3), np.float32)
    for r0 in range(0, h, 480):
        r1 = min(h, r0 + 480)
        d = fwd[None, None] + a[None, :, None] * right[None, None] + b[r0:r1, None, None] * up[None, None]
        d /= np.linalg.norm(d, axis=-1, keepdims=True)
        z = Z[r0:r1]
        ok = z < 1e29
        P = cam[None, None] + d * np.where(ok, z, 0)[..., None]
        ids = I[r0:r1]
        f = np.ones(P.shape)
        f[ok] = texture(P[ok], ids[ok], theta)
        fac[r0:r1] = f
    (D * fac).astype(np.float32).tofile(out_prefix + "_D.f32")
    (A * fac).astype(np.float32).tofile(out_prefix + "_A.f32")
    for ext in ("_O.f32", "_Z.f32", "_N.f32", "_I.u8"):
        dst = out_prefix + ext
        if os.path.lexists(dst):
            os.remove(dst)
        os.symlink(os.path.abspath(gprefix + ext), dst)
    return fac
