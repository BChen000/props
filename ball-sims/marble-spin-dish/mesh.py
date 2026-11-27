"""The triangle-mesh writer for ../marble-raytrace-kit/meshtrace.c (copied from ../marble-run-picture/mesh.py)."""
import math
import os
import struct

import numpy as np



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
