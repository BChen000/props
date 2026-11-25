import numpy as np
from skimage.measure import marching_cubes
import scipy.sparse as sp


def _norm(v):
    return np.sqrt(np.sum(v * v, axis=-1))


def sd_ellipsoid(p, c, r, R=None):
    q = p - np.asarray(c, dtype=np.float64)
    if R is not None:
        q = q @ np.asarray(R)
    r = np.asarray(r, dtype=np.float64)
    k0 = _norm(q / r)
    k1 = _norm(q / (r * r))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def sd_roundcone(p, a, b, r1, r2):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = pa @ ba
    z = y - l2
    w = pa * l2 - ba[None, :] * y[:, None]
    x2 = np.sum(w * w, axis=-1)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d1 = np.sqrt(x2 + z2) * il2 - r2
    d2 = np.sqrt(x2 + y2) * il2 - r1
    d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
    out = np.where(np.sign(z) * a2 * z2 > k, d1, np.where(np.sign(y) * a2 * y2 < k, d2, d3))
    return out


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


class Prim:
    def __init__(self, kind, bone, k=0.02, attrs=None, sub=False, **kw):
        self.kind = kind
        self.bone = bone
        self.k = k
        self.attrs = attrs or {}
        self.sub = sub
        self.kw = kw

    def dist(self, p):
        if self.kind == 'ell':
            return sd_ellipsoid(p, self.kw['c'], self.kw['r'], self.kw.get('R'))
        if self.kind == 'cone':
            return sd_roundcone(p, self.kw['a'], self.kw['b'], self.kw['r1'], self.kw['r2'])
        if self.kind == 'sph':
            return _norm(p - np.asarray(self.kw['c'])) - self.kw['r']
        raise ValueError(self.kind)

    def bounds(self):
        if self.kind in ('ell',):
            c = np.asarray(self.kw['c']); r = max(self.kw['r'])
            return c - r, c + r
        if self.kind == 'sph':
            c = np.asarray(self.kw['c']); r = self.kw['r']
            return c - r, c + r
        a = np.asarray(self.kw['a']); b = np.asarray(self.kw['b'])
        r = max(self.kw['r1'], self.kw['r2'])
        return np.minimum(a, b) - r, np.maximum(a, b) + r


def field(prims, p):
    d = None
    for pr in prims:
        di = pr.dist(p)
        if d is None:
            d = di
        elif pr.sub:
            d = smax(d, -di, pr.k)
        else:
            d = smin(d, di, pr.k)
    return d


def build_mesh(prims, h, margin=0.03, chunk=400000):
    lo = np.min([pr.bounds()[0] for pr in prims if not pr.sub], axis=0) - margin
    hi = np.max([pr.bounds()[1] for pr in prims if not pr.sub], axis=0) + margin
    n = np.ceil((hi - lo) / h).astype(int) + 1
    xs = lo[0] + np.arange(n[0]) * h
    ys = lo[1] + np.arange(n[1]) * h
    zs = lo[2] + np.arange(n[2]) * h
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    vals = np.empty(len(P), dtype=np.float32)
    for i in range(0, len(P), chunk):
        vals[i:i + chunk] = field(prims, P[i:i + chunk])
    vol = vals.reshape(n)
    verts, faces, normals, _ = marching_cubes(vol, level=0.0, spacing=(h, h, h))
    verts = verts + lo
    v0, v1, v2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    vol_sign = np.sum(np.einsum('ij,ij->i', v0, np.cross(v1, v2)))
    if vol_sign < 0:
        faces = faces[:, ::-1]
    return verts.astype(np.float64), faces.astype(np.int64)


def adjacency(nv, faces):
    i = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2], faces[:, 1], faces[:, 2], faces[:, 0]])
    j = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0], faces[:, 0], faces[:, 1], faces[:, 2]])
    A = sp.coo_matrix((np.ones(len(i)), (i, j)), shape=(nv, nv)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(axis=1)).ravel()
    deg[deg == 0] = 1
    return sp.diags(1.0 / deg) @ A


def taubin(verts, faces, iters=10, lam=0.5, mu=-0.53):
    W = adjacency(len(verts), faces)
    v = verts.copy()
    for _ in range(iters):
        v = v + lam * (W @ v - v)
        v = v + mu * (W @ v - v)
    return v


def smooth_attr(values, faces, nv, iters=3):
    W = adjacency(nv, faces)
    x = values.copy()
    for _ in range(iters):
        x = 0.5 * x + 0.5 * (W @ x)
    return x


def weights(prims, verts, faces, bones, falloff=0.012, smooth_iters=4, top=3):
    D = np.stack([pr.dist(verts) for pr in prims if not pr.sub], axis=1)
    use = [pr for pr in prims if not pr.sub]
    infl = np.exp(-np.maximum(D, 0.0) / falloff) * np.where(D < 0, 1.0 + np.minimum(-D, 0.05) * 0.0, 1.0)
    bidx = {b: i for i, b in enumerate(bones)}
    Wb = np.zeros((len(verts), len(bones)))
    for k, pr in enumerate(use):
        if isinstance(pr.bone, dict):
            for b, f in pr.bone.items():
                Wb[:, bidx[b]] += infl[:, k] * f
        else:
            Wb[:, bidx[pr.bone]] += infl[:, k]
    Wb = Wb / np.maximum(Wb.sum(axis=1, keepdims=True), 1e-12)
    Wb = smooth_attr(Wb, faces, len(verts), smooth_iters)
    if top:
        idx = np.argsort(-Wb, axis=1)[:, top:]
        np.put_along_axis(Wb, idx, 0.0, axis=1)
    Wb = Wb / np.maximum(Wb.sum(axis=1, keepdims=True), 1e-12)
    attrs = {}
    keys = sorted({k for pr in use for k in pr.attrs})
    wsum = infl.sum(axis=1)
    for key in keys:
        vals = np.array([pr.attrs.get(key, 0.0) for pr in use])
        a = (infl * vals[None, :]).sum(axis=1) / np.maximum(wsum, 1e-12)
        attrs[key] = smooth_attr(a, faces, len(verts), 2)
    return Wb, attrs


def decimate_none(verts, faces):
    return verts, faces
