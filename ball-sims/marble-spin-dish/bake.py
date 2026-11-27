"""Paints the wood grain of the dish and pegs and the table's boards into the path-traced G-buffer (copied from
../marble-run-picture/bake.py).

meshtrace has no textures, so every surface is traced with a flat albedo and gloss 0. Its key-light (D) and
sky/bounce (A) layers are then albedo x lighting, so multiplying them by a texture factor per pixel is the same as
having traced a textured albedo (apart from the colour of light bounced off the texture, which is invisible here).
World positions come from the depth layer, so the grain is fixed to the blocks.

    bake(gprefix, out_prefix)   writes out_prefix_D/_A.f32 and links the other layers
"""
import math
import os

import numpy as np

import settings as C
import dish as DS
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


def fbm(x, y, z, octaves=3):
    s, amp, tot = 0.0, 1.0, 0.0
    for _ in range(octaves):
        s = s + amp * vnoise(x, y, z)
        tot += amp
        x, y, z, amp = x * 2.03, y * 2.03, z * 2.03, amp * 0.5
    return s / tot


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def wood(P, oid):
    """Per-pixel RGB factor for the blocks: growth rings seen from the side, a different log for every block."""
    out = np.ones((len(P), 3))
    for k in np.unique(oid):
        m = oid == k
        p = P[m]
        rg = np.random.default_rng(int(k) * 7 + 3)
        axis = 0 if rg.random() < 0.7 else 2
        u_ax, v_ax = (1, 2) if axis == 0 else (1, 0)
        cu, cv = rg.uniform(-9, 9), rg.choice([-1, 1]) * rg.uniform(6, 16)
        cen = p.mean(0)
        pu, pv = p[:, u_ax] - cen[u_ax] - cu, p[:, v_ax] - cen[v_ax] - cv
        warp = 0.55 * (fbm(p[:, axis] * 0.11 + k, p[:, u_ax] * 0.5, p[:, v_ax] * 0.5) - 0.5)
        r = np.hypot(pu, pv) + warp
        freq = rg.uniform(1.25, 1.75)
        t = (r * freq) % 1.0
        late = smooth(0.62, 0.86, t) * (1 - smooth(0.93, 1.0, t))
        streak = vnoise(p[:, axis] * 0.35, p[:, u_ax] * 7.0, p[:, v_ax] * 7.0)
        tone = 1.0 + rg.uniform(-0.05, 0.05)
        f = tone * (1 - 0.13 * late) * (0.97 + 0.06 * streak)
        out[m, 0] = f * (1 + 0.02 * late)
        out[m, 1] = f * (1 - 0.03 * late)
        out[m, 2] = f * (1 - 0.10 * late)
    return out


def floor(P):
    """Whitewashed boards running toward the camera, with thin seams and staggered ends."""
    pw = 9.0
    x, z = P[:, 0] + 4.0, P[:, 2]
    plank = np.floor(x / pw)
    fx = x / pw - plank
    rg = np.random.default_rng(5)
    offs = rg.uniform(0, 70, 64)
    pid = plank.astype(np.int64) & 63
    zz = z + offs[pid]
    seg = np.floor(zz / 70.0)
    fz = zz / 70.0 - seg
    tone = 1 + 0.035 * (vnoise(plank * 3.1, seg * 1.7, 0.5) - 0.5) * 2
    grain = vnoise(x * 1.6, z * 0.08, plank) * 0.6 + vnoise(x * 5.0, z * 0.2, plank + 9) * 0.4
    f = tone * (0.975 + 0.05 * grain)
    seam = np.minimum(fx, 1 - fx) * pw
    endj = np.minimum(fz, 1 - fz) * 70.0
    f = f * (1 - 0.35 * (1 - smooth(0.03, 0.11, seam))) * (1 - 0.25 * (1 - smooth(0.03, 0.09, endj)))
    return np.stack([f, f, f * 0.995], 1)


def felt(P):
    x, z = P[:, 0], P[:, 2]
    fine = vnoise(x * 6.0, z * 6.0, 3.0) * 0.5 + vnoise(x * 13.0, z * 13.0, 7.0) * 0.5
    mott = fbm(x * 0.18, z * 0.18, 11.0)
    f = (0.94 + 0.10 * fine) * (0.96 + 0.08 * mott)
    return np.stack([f, f * 1.01, f], 1)


def wall(P):
    f = 0.985 + 0.03 * fbm(P[:, 0] * 0.2, P[:, 1] * 0.2, 1.0)
    return np.stack([f, f, f], 1)


def bake(gprefix, out_prefix, log=print, size=None):
    W2, H2 = size or (2 * S.W, 2 * S.H)
    D = np.fromfile(gprefix + "_D.f32", np.float32).reshape(H2, W2, 3)
    A = np.fromfile(gprefix + "_A.f32", np.float32).reshape(H2, W2, 3)
    Z = np.fromfile(gprefix + "_Z.f32", np.float32).reshape(H2, W2)
    I = np.fromfile(gprefix + "_I.u8", np.uint8).reshape(H2, W2)
    cam, fwd, right, up = S.camera()
    th = math.tan(S.CAM_FOVY / 2)
    asp = S.W / S.H
    a = ((np.arange(W2) + 0.5) / W2 * 2 - 1 + S.CAM_SHIFT[0]) * th * asp
    b = (1 - (np.arange(H2) + 0.5) / H2 * 2 + S.CAM_SHIFT[1]) * th
    fac = np.ones((H2, W2, 3), np.float32)
    for y0 in range(0, H2, 480):
        y1 = min(H2, y0 + 480)
        d = fwd[None, None] + a[None, :, None] * right[None, None] + b[y0:y1, None, None] * up[None, None]
        d /= np.linalg.norm(d, axis=-1, keepdims=True)
        z = Z[y0:y1]
        ok = z < 1e29
        P = cam[None, None] + d * np.where(ok, z, 0)[..., None]
        ids = I[y0:y1]
        f = np.ones(P.shape)
        for sel, fn in (((ids == DS.OID_DISH) | np.isin(ids, DS.OID_PEGS)), None), ((ids == DS.OID_TABLE) & ok, floor):
            sel = sel & ok
            if not sel.any():
                continue
            if fn is None:
                f[sel] = wood(P[sel], ids[sel])
            else:
                f[sel] = fn(P[sel])
        fac[y0:y1] = f
    (D * fac).astype(np.float32).tofile(out_prefix + "_D.f32")
    (A * fac).astype(np.float32).tofile(out_prefix + "_A.f32")
    for ext in ("_O.f32", "_Z.f32", "_N.f32", "_I.u8"):
        dst = out_prefix + ext
        if os.path.lexists(dst):
            os.remove(dst)
        os.symlink(os.path.abspath(gprefix + ext), dst)
    log("textures baked into the G-buffer")
    return fac
