"""Builds the playground as one triangle mesh for ../marble-raytrace-kit/meshtrace.c (helpers copied from
../marble-run-picture/mesh.py).

Plain blocks and walls are analytic rounded boxes; the tunnel and arch cubes are signed distance fields (rounded box
minus the tunnel tube) turned into triangles with marching cubes. The room wall, baseboard and felt mat are boxes;
the floor is the tracer's own ground plane.

    python3 mesh.py      -> build/mesh.bin, and prints the triangle count
"""
import math
import os
import struct
import sys

import numpy as np
from numba import njit, prange
from skimage.measure import marching_cubes

import settings as C
import layout as LY


def srgb2lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


class Mesh:
    def __init__(self):
        self.mats = []
        self.chunks = []

    def mat(self, alb, gloss, rough, oid, glass=0.0):
        self.mats.append((*map(float, alb), float(gloss), float(rough), float(oid), float(glass)))
        return len(self.mats) - 1

    def add(self, v, f, n, m):
        """v: (nv,3) vertices, f: (nf,3) int faces, n: (nv,3) vertex normals, m: material index."""
        tri = np.empty((len(f), 19), np.float32)
        tri[:, 0:3], tri[:, 3:6], tri[:, 6:9] = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        tri[:, 9:12], tri[:, 12:15], tri[:, 15:18] = n[f[:, 0]], n[f[:, 1]], n[f[:, 2]]
        tri[:, 18] = m
        self.chunks.append(tri)

    def flatquad(self, a, b, c, d, m):
        v = np.array([a, b, c, d], float)
        n = np.cross(v[1] - v[0], v[2] - v[0])
        n /= np.linalg.norm(n)
        self.add(v, np.array([[0, 1, 2], [0, 2, 3]]), np.repeat(n[None], 4, 0), m)

    def box(self, lo, hi, m):
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        P = lambda x, y, z: (x, y, z)
        self.flatquad(P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1), m)
        self.flatquad(P(x0, y0, z1), P(x0, y1, z1), P(x0, y1, z0), P(x0, y0, z0), m)
        self.flatquad(P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), m)
        self.flatquad(P(x0, y0, z1), P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), m)
        self.flatquad(P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1), m)
        self.flatquad(P(x1, y0, z0), P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0), m)

    def ntris(self):
        return sum(len(c) for c in self.chunks)

    def write(self, path):
        with open(path, "wb") as f:
            f.write(struct.pack("ii", self.ntris(), len(self.mats)))
            f.write(np.array(self.mats, np.float32).tobytes())
            for c in self.chunks:
                f.write(c.tobytes())


def rounded_box(lo, hi, rr, k=4):
    """Vertices, faces and normals of a box with edges rounded to radius rr: a cube-sphere of normals (k steps per
    45 degrees), each octant pushed out to its corner, with the flat faces and edge strips in the gaps."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c, h = (lo + hi) / 2, (hi - lo) / 2 - rr
    phi = np.linspace(0, math.pi / 4, k + 1)
    t = np.concatenate([-np.tan(phi[::-1]), np.tan(phi)])
    sg = np.concatenate([-np.ones(k + 1), np.ones(k + 1)])
    m = 2 * k + 2
    V, F, N = [], [], []
    base = 0
    for axis in range(3):
        a1, a2 = [i for i in range(3) if i != axis]
        for s in (-1.0, 1.0):
            U, W = np.meshgrid(t, t, indexing="ij")
            S1, S2 = np.meshgrid(sg, sg, indexing="ij")
            n = np.zeros(U.shape + (3,))
            n[..., a1], n[..., a2], n[..., axis] = U, W, s
            n /= np.linalg.norm(n, axis=-1, keepdims=True)
            p = np.zeros_like(n)
            p[..., a1], p[..., a2], p[..., axis] = S1 * h[a1], S2 * h[a2], s * h[axis]
            p = c + p + rr * n
            idx = np.arange(m * m).reshape(m, m) + base
            a, b, cc, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
            F.append(np.stack([a, b, cc], -1).reshape(-1, 3))
            F.append(np.stack([a, cc, d], -1).reshape(-1, 3))
            V.append(p.reshape(-1, 3))
            N.append(n.reshape(-1, 3))
            base += m * m
    return np.concatenate(V), np.concatenate(F), np.concatenate(N)


@njit(cache=True)
def _carve_field(ox, oy, oz, h, nx, ny, nz, segs, out):
    """out[i,j,k] = min over tube segments of (distance to segment - radius); segs rows: ax ay az bx by bz r."""
    for si in range(segs.shape[0]):
        ax, ay, az, bx, by, bz, r = segs[si]
        pad = r + 2 * h
        i0 = max(0, int((min(ax, bx) - pad - ox) / h))
        i1 = min(nx, int((max(ax, bx) + pad - ox) / h) + 2)
        j0 = max(0, int((min(ay, by) - pad - oy) / h))
        j1 = min(ny, int((max(ay, by) + pad - oy) / h) + 2)
        k0 = max(0, int((min(az, bz) - pad - oz) / h))
        k1 = min(nz, int((max(az, bz) + pad - oz) / h) + 2)
        dx, dy, dz = bx - ax, by - ay, bz - az
        ll = dx * dx + dy * dy + dz * dz
        for i in range(i0, i1):
            px = ox + i * h
            for j in range(j0, j1):
                py = oy + j * h
                for k in range(k0, k1):
                    pz = oz + k * h
                    t = 0.0
                    if ll > 0:
                        t = ((px - ax) * dx + (py - ay) * dy + (pz - az) * dz) / ll
                        t = min(1.0, max(0.0, t))
                    qx, qy, qz = ax + t * dx - px, ay + t * dy - py, az + t * dz - pz
                    d = math.sqrt(qx * qx + qy * qy + qz * qz) - r
                    if d < out[i, j, k]:
                        out[i, j, k] = d


def carved_piece(pc, segs, h):
    lo, hi = pc["lo"], pc["hi"]
    o = lo - 3 * h
    n = np.ceil((hi - lo) / h).astype(int) + 7
    gx = o[0] + np.arange(n[0]) * h
    gy = o[1] + np.arange(n[1]) * h
    gz = o[2] + np.arange(n[2]) * h
    X, Y, Z = np.meshgrid(gx, gy, gz, indexing="ij")
    c, hh = (lo + hi) / 2, (hi - lo) / 2 - C.ROUND
    q = np.stack([np.abs(X - c[0]) - hh[0], np.abs(Y - c[1]) - hh[1], np.abs(Z - c[2]) - hh[2]], -1)
    f = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - C.ROUND
    if pc.get("top") is not None:
        f = np.maximum(f, Y - pc["top"](X))
    near = segs[(np.minimum(segs[:, 0], segs[:, 3]) - segs[:, 6] < hi[0] + 1) &
                (np.maximum(segs[:, 0], segs[:, 3]) + segs[:, 6] > lo[0] - 1) &
                (np.minimum(segs[:, 1], segs[:, 4]) - segs[:, 6] < hi[1] + 1) &
                (np.maximum(segs[:, 1], segs[:, 4]) + segs[:, 6] > lo[1] - 1) &
                (np.minimum(segs[:, 2], segs[:, 5]) - segs[:, 6] < hi[2] + 1) &
                (np.maximum(segs[:, 2], segs[:, 5]) + segs[:, 6] > lo[2] - 1)]
    cv = np.full(tuple(n), 50.0)
    if len(near):
        _carve_field(o[0], o[1], o[2], h, n[0], n[1], n[2], np.ascontiguousarray(near), cv)
        f = np.maximum(f, -cv)
    v, faces, nrm, _ = marching_cubes(f.astype(np.float32), 0.0, spacing=(h, h, h), gradient_direction="ascent")
    v = v + o
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    return v, faces, nrm


def all_segments():
    rows = []
    for pl, r in LY.carves():
        for a, b in zip(pl[:-1], pl[1:]):
            rows.append([*a, *b, r])
    return np.array(rows, np.float64)


def build_mesh(log=print):
    M = Mesh()
    wood = srgb2lin(C.WOOD_SRGB)
    segs = all_segments()
    for pc in LY.pieces():
        m = M.mat(wood, 0.0, 0.5, pc["oid"])
        if pc["carved"]:
            v, f, n = carved_piece(pc, segs, C.MC_STEP)
        else:
            v, f, n = rounded_box(pc["lo"], pc["hi"], C.ROUND)
        M.add(v, f, n, m)
    m_wall = M.mat(srgb2lin(C.WALL_SRGB), 0.0, 0.5, LY.OID_WALL)
    zw, hw = C.ROOM_WALL_Z, C.ROOM_WALL_H
    M.flatquad((-200, 0, zw), (200, 0, zw), (200, hw, zw), (-200, hw, zw), m_wall)
    m_base = M.mat(srgb2lin(C.BASEBOARD_SRGB), 0.0, 0.5, LY.OID_BASEBOARD)
    M.box((-200, 0, zw), (200, C.BASEBOARD_H, zw + C.BASEBOARD_D), m_base)
    m_mat = M.mat(srgb2lin(C.MAT_SRGB), 0.0, 0.5, LY.OID_MAT)
    x0, x1, z0, z1 = C.MAT
    M.box((x0, 0.0, z0), (x1, C.MAT_T, z1), m_mat)
    log(f"mesh: {M.ntris()} triangles, {len(M.mats)} materials")
    return M


if __name__ == "__main__":
    os.makedirs(C.BUILD, exist_ok=True)
    import time
    t = time.time()
    M = build_mesh()
    M.write(os.path.join(C.BUILD, "mesh.bin"))
    print(f"{time.time() - t:.1f}s")
