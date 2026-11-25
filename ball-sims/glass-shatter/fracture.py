import numpy as np
from scipy.spatial import Voronoi


def clip_poly(poly, x0, x1, y0, y1):
    def clip(pts, inside, inter):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ia, ib = inside(a), inside(b)
            if ia and ib:
                out.append(b)
            elif ia and not ib:
                out.append(inter(a, b))
            elif not ia and ib:
                out.append(inter(a, b))
                out.append(b)
        return out
    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))
    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / (b[1] - a[1]), yv)
    pts = [tuple(p) for p in poly]
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            break
        pts = clip(pts, inside, inter)
    return np.array(pts)


def poly_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def poly_centroid(p):
    x, y = p[:, 0], p[:, 1]
    cr = x * np.roll(y, -1) - np.roll(x, -1) * y
    A = 0.5 * cr.sum()
    cx = ((x + np.roll(x, -1)) * cr).sum() / (6 * A)
    cy = ((y + np.roll(y, -1)) * cr).sum() / (6 * A)
    return np.array([cx, cy])


def seeds(center, half, rng, r0=0.012, ratio=1.22, per_ring=15, extra=150):
    pts = []
    r = r0
    while r < 2.2 * half:
        n = per_ring + int(2 * r / 0.25)
        a0 = rng.uniform(0, 2 * np.pi)
        for k in range(n):
            a = a0 + 2 * np.pi * (k + rng.uniform(-0.32, 0.32)) / n
            rr = r * rng.uniform(0.86, 1.14)
            pts.append((center[0] + rr * np.cos(a), center[1] + rr * np.sin(a)))
        r *= ratio * rng.uniform(0.94, 1.06)
    pts = np.array(pts)
    m = (np.abs(pts[:, 0]) < half - 0.004) & (np.abs(pts[:, 1]) < half - 0.004)
    pts = pts[m]
    ex = rng.uniform(-half + 0.01, half - 0.01, (extra, 2))
    dd = np.linalg.norm(ex - np.asarray(center), axis=1)
    ex = ex[dd > 0.18]
    return np.vstack([pts, ex])


def shatter(center, half=0.5, seed=0, **kw):
    rng = np.random.default_rng(seed)
    P = seeds(center, half, rng, **kw)
    allp = [P]
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        Q = P.copy()
        if sx:
            Q[:, 0] = sx * 2 * half - Q[:, 0]
        if sy:
            Q[:, 1] = sy * 2 * half - Q[:, 1]
        allp.append(Q)
    vor = Voronoi(np.vstack(allp))
    polys = []
    for i in range(len(P)):
        reg = vor.regions[vor.point_region[i]]
        if -1 in reg or len(reg) < 3:
            continue
        poly = vor.vertices[reg]
        c = poly.mean(0)
        ang = np.arctan2(poly[:, 1] - c[1], poly[:, 0] - c[0])
        poly = poly[np.argsort(ang)]
        poly = clip_poly(poly, -half, half, -half, half)
        if len(poly) < 3 or abs(poly_area(poly)) < 1e-6:
            continue
        if poly_area(poly) < 0:
            poly = poly[::-1]
        polys.append(poly)
    return polys


def prism(poly, t, shrink=0.0):
    c = poly_centroid(poly)
    p = poly - c
    if shrink > 0:
        d = np.linalg.norm(p, axis=1, keepdims=True)
        p = p * np.clip((d - shrink) / np.maximum(d, 1e-9), 0.5, 1.0)
    n = len(p)
    top = np.c_[p, np.full(n, t / 2)]
    bot = np.c_[p, np.full(n, -t / 2)]
    verts = np.vstack([top, bot])
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    mats = [0, 0]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, n + i, n + j, j])
        mats.append(1)
    return c, verts, faces, mats
