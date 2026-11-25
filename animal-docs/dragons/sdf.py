import numpy as np
from skimage.measure import marching_cubes
import fast_simplification


def _rot(euler):
    rx, ry, rz = euler
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


class Prim:
    def __init__(self, kind, bone, k=0.12, neg=False, **kw):
        self.kind, self.bone, self.k, self.neg = kind, bone, k, neg
        self.kw = kw
        if kind == "cone":
            a, b = np.array(kw["a"], float), np.array(kw["b"], float)
            r1, r2 = kw["r1"], kw["r2"]
            sq = np.array(kw.get("squash", (1, 1, 1)), float)
            self.a, self.b, self.r1, self.r2, self.sq = a, b, r1, r2, sq
            lo = np.minimum(a - r1, b - r2); hi = np.maximum(a + r1, b + r2)
        elif kind == "ell":
            c = np.array(kw["c"], float); r = np.array(kw["r"], float)
            self.c, self.r = c, r
            self.R = _rot(kw.get("rot", (0, 0, 0)))
            m = r.max()
            lo, hi = c - m, c + m
        elif kind == "sph":
            c = np.array(kw["c"], float); self.c, self.rad = c, kw["r"]
            lo, hi = c - self.rad, c + self.rad
        elif kind == "box":
            c = np.array(kw["c"], float); h = np.array(kw["h"], float)
            self.c, self.h = c, h
            self.R = _rot(kw.get("rot", (0, 0, 0)))
            m = np.linalg.norm(h)
            lo, hi = c - m, c + m
        self.lo, self.hi = lo, hi

    def dist(self, p):
        if self.kind == "cone":
            ctr = (self.a + self.b) / 2
            q = ctr + (p - ctr) / self.sq
            a, b, r1, r2 = self.a, self.b, self.r1, self.r2
            ba = b - a; l2 = ba @ ba; rr = r1 - r2; a2 = l2 - rr * rr; il2 = 1.0 / l2
            pa = q - a
            y = pa @ ba
            z = y - l2
            xv = pa * l2 - np.outer(y, ba)
            x2 = (xv * xv).sum(1)
            y2 = y * y * l2; z2 = z * z * l2
            kk = np.sign(rr) * rr * rr * x2
            d = np.where(np.sign(z) * a2 * z2 > kk, np.sqrt(x2 + z2) * il2 - r2,
                np.where(np.sign(y) * a2 * y2 < kk, np.sqrt(x2 + y2) * il2 - r1,
                         (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1))
            return d * self.sq.min()
        if self.kind == "ell":
            q = (p - self.c) @ self.R
            k0 = np.linalg.norm(q / self.r, axis=1)
            k1 = np.linalg.norm(q / (self.r * self.r), axis=1)
            return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
        if self.kind == "sph":
            return np.linalg.norm(p - self.c, axis=1) - self.rad
        if self.kind == "box":
            q = np.abs((p - self.c) @ self.R) - self.h
            return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def build_field(prims, h, pad=0.15):
    pos = [p for p in prims if not p.neg]
    lo = np.min([p.lo for p in pos], 0) - pad
    hi = np.max([p.hi for p in pos], 0) + pad
    n = np.ceil((hi - lo) / h).astype(int) + 1
    xs = lo[0] + np.arange(n[0]) * h
    ys = lo[1] + np.arange(n[1]) * h
    zs = lo[2] + np.arange(n[2]) * h
    F = np.full(n, 1.0, np.float32)
    for p in prims:
        m = p.k + 0.05
        i0 = np.clip(np.searchsorted(xs, p.lo[0] - m), 0, n[0]); i1 = np.clip(np.searchsorted(xs, p.hi[0] + m), 0, n[0])
        j0 = np.clip(np.searchsorted(ys, p.lo[1] - m), 0, n[1]); j1 = np.clip(np.searchsorted(ys, p.hi[1] + m), 0, n[1])
        k0 = np.clip(np.searchsorted(zs, p.lo[2] - m), 0, n[2]); k1 = np.clip(np.searchsorted(zs, p.hi[2] + m), 0, n[2])
        if i1 <= i0 or j1 <= j0 or k1 <= k0:
            continue
        X, Y, Z = np.meshgrid(xs[i0:i1], ys[j0:j1], zs[k0:k1], indexing="ij")
        P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        d = p.dist(P).reshape(X.shape).astype(np.float32)
        sub = F[i0:i1, j0:j1, k0:k1]
        if p.neg:
            F[i0:i1, j0:j1, k0:k1] = smax(sub, -d, p.k)
        else:
            F[i0:i1, j0:j1, k0:k1] = smin(sub, d, p.k)
    return F, lo, h


def mesh_from_field(F, lo, h, target_faces=None):
    v, f, nrm, _ = marching_cubes(F, level=0.0, spacing=(h, h, h))
    v = v + lo
    f = f.copy()
    if target_faces and len(f) > target_faces:
        red = 1.0 - target_faces / len(f)
        v, f = fast_simplification.simplify(v.astype(np.float32), f.astype(np.int32), target_reduction=red, agg=5)
    return v.astype(np.float64), f.astype(np.int64)


def bone_weights(verts, prims, tau=0.06, cutoff=5.0):
    pos = [p for p in prims if not p.neg and p.bone]
    D = np.stack([p.dist(verts) for p in pos], 1)
    dmin = D.min(1, keepdims=True)
    W = np.exp(-(D - dmin) / tau)
    W[(D - dmin) > cutoff * tau] = 0
    bones = sorted(set(p.bone for p in pos))
    out = {b: np.zeros(len(verts)) for b in bones}
    for i, p in enumerate(pos):
        out[p.bone] += W[:, i]
    tot = sum(out.values())
    for b in bones:
        out[b] /= np.maximum(tot, 1e-9)
    return out


def tube(points, radii, ring=12, cap=True):
    """Tapered tube along polyline. returns verts, faces, (t along, ring index)."""
    P = np.array(points, float); R = np.array(radii, float)
    n = len(P)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0])
    if abs(T[0] @ up) > 0.9:
        up = np.array([0, 1.0, 0])
    N = np.cross(T[0], up); N /= np.linalg.norm(N)
    verts = []; frames = []
    for i in range(n):
        if i > 0:
            N = N - (N @ T[i]) * T[i]; N /= np.linalg.norm(N)
        B = np.cross(T[i], N)
        frames.append((N.copy(), B.copy()))
        for j in range(ring):
            a = 2 * np.pi * j / ring
            verts.append(P[i] + R[i] * (np.cos(a) * N + np.sin(a) * B))
    faces = []
    for i in range(n - 1):
        for j in range(ring):
            a = i * ring + j; b = i * ring + (j + 1) % ring
            faces.append((a, b, b + ring, a + ring))
    verts = list(verts)
    if cap:
        tip = len(verts); verts.append(P[-1] + T[-1] * R[-1] * 0.5)
        for j in range(ring):
            faces.append(((n - 1) * ring + j, (n - 1) * ring + (j + 1) % ring, tip))
        base = len(verts); verts.append(P[0] - T[0] * R[0] * 0.3)
        for j in range(ring):
            faces.append(((j + 1) % ring, j, base))
    tparam = np.concatenate([np.repeat(np.linspace(0, 1, n), ring), [1.0, 0.0] if cap else []])
    return np.array(verts), faces, tparam


def bezier(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(lambda x: np.array(x, float), (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
