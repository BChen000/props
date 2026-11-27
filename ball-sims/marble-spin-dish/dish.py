"""The set: a turned wooden dish with a raised rim, a funnel dip and a hole in the middle, three wooden pegs, standing
on a wooden table (the tracer's ground plane). Everything is a surface of revolution built from a 2D profile, so
the mesh matches the physics surface in sim.py exactly.

    python3 dish.py      -> build/mesh.bin, and prints the triangle count
"""
import math
import os

import numpy as np

import settings as C
import sim
from mesh import Mesh, srgb2lin

OID_TABLE, OID_DISH, OID_HOLE = 0, 10, 12
OID_PEGS = (11, 13, 14, 15, 16, 17)              # one id per peg, so each can light up on its own


def lathe(M, prof, m, cx=0.0, cz=0.0, k=256):
    """Revolve a profile [(r, y), ...] around the vertical axis through (cx, cz)."""
    prof = np.asarray(prof, float)
    a = np.linspace(0, 2 * math.pi, k + 1)
    ca, sa = np.cos(a), np.sin(a)
    t = np.gradient(prof, axis=0)
    nr, ny = t[:, 1], -t[:, 0]
    ln = np.hypot(nr, ny) + 1e-12
    nr, ny = nr / ln, ny / ln
    n = len(prof)
    V = np.zeros((k + 1, n, 3))
    N = np.zeros((k + 1, n, 3))
    V[..., 0] = cx + ca[:, None] * prof[None, :, 0]
    V[..., 1] = prof[None, :, 1]
    V[..., 2] = cz + sa[:, None] * prof[None, :, 0]
    N[..., 0] = ca[:, None] * nr[None]
    N[..., 1] = ny[None]
    N[..., 2] = sa[:, None] * nr[None]
    idx = np.arange((k + 1) * n).reshape(k + 1, n)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    f = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    M.add(V.reshape(-1, 3), f, N.reshape(-1, 3), m)


def arc(c, r, a0, a1, n=10):
    a = np.linspace(a0, a1, n)
    return [(c[0] + r * math.cos(x), c[1] + r * math.sin(x)) for x in a]


def dish_profile():
    """(r, y) from the bottom of the hole, up the hole wall, across the floor, over the rim and down to the table."""
    y = sim.floor_y
    rs = np.concatenate([C.RH + (C.RD - 0.6 - C.RH) * np.linspace(0, 1, 160) ** 1.6])
    floor = [(r, float(y(r))) for r in rs]
    yrd = float(y(C.RD))
    lip = 0.35
    prof = [(C.RH, -0.05), (C.RH, floor[0][1] - lip)]
    prof += arc((C.RH + lip, floor[0][1] - lip), lip, math.pi, math.pi / 2, 6)[1:]
    prof += floor[2:]
    prof += arc((C.RD - 0.6, yrd + 0.6), 0.6, -math.pi / 2, 0.0, 8)[1:]
    top = yrd + C.RIM_H
    rr = C.RIM_T / 2
    prof += [(C.RD, top - rr)]
    prof += arc((C.RD + rr, top - rr), rr, math.pi, 0.0, 14)[1:]
    prof += [(C.RD + C.RIM_T, 0.45)]
    prof += arc((C.RD + C.RIM_T - 0.45, 0.45), 0.45, 0.0, -math.pi / 2, 6)[1:]
    return prof


def build_mesh(log=print):
    M = Mesh()
    wood = srgb2lin(C.DISH_SRGB)
    m_dish = M.mat(wood, 0.0, 0.5, OID_DISH)
    lathe(M, dish_profile(), m_dish)
    m_hole = M.mat((0.008, 0.007, 0.006), 0.0, 0.5, OID_HOLE)
    disk = [(0.0, 0.02), (C.RH + 0.01, 0.02)]
    lathe(M, disk, m_hole, k=96)
    for k, (px, pz) in enumerate(C.PEGS):
        m_peg = M.mat(srgb2lin(C.PEG_SRGB), 0.0, 0.5, OID_PEGS[k])
        r0 = math.hypot(px, pz)
        y0 = float(sim.floor_y(r0)) - 0.3
        pr = C.PEG_R
        prof = [(0.0, y0 + C.PEG_H + pr * 0.35)]
        prof += [(pr * math.sin(a), y0 + C.PEG_H - pr * 0.65 + pr * math.cos(a) * 1.0)
                 for a in np.linspace(0.15, math.pi / 2, 8)]
        prof += [(pr, y0)]
        lathe(M, prof, m_peg, px, pz, k=64)
    log(f"mesh: {M.ntris()} triangles, {len(M.mats)} materials")
    return M


if __name__ == "__main__":
    os.makedirs(C.BUILD, exist_ok=True)
    build_mesh().write(os.path.join(C.BUILD, "mesh.bin"))
