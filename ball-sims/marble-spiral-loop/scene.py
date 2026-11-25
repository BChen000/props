"""Geometry and camera of the spiral loop: the rainbow helix of marble-spiral-round, rebuilt for a landscape stream
background. The track has N_SEG equal segments whose colors cycle, a feeder rail brings marbles in from off-screen
left at the top, an exit rail takes them off-screen right at the bottom, and the round dish stays as the base.

The set is a triangle mesh for ../marble-raytrace-kit/meshtrace.c. The motion is in timeline.py.
"""
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import look

look.W, look.H = int(os.environ.get("LOOP_W", "1920")), int(os.environ.get("LOOP_H", "1080"))
from look import (W, H, FPS, R, LIGHT_ANG, LIGHT_COL, SKY_Z, SKY_H, EXPOSURE, FLOOR_LIN, DARK_LIN, srgb2lin,
                  vignette, tonemap)

# ===================================================================== SETTINGS (shipped values)
RC = 6.4                # helix center radius
TW = 3.4                # track width
RIN = RC - TW / 2
ROUT = RC + TW / 2
TTH = 0.45              # track thickness
PITCH = 7.2             # rise per turn
HH = PITCH / (2 * math.pi)
DS = math.sqrt(RC * RC + HH * HH)
TURNS = 4               # whole turns, so the track starts and ends at the back (theta = 1.5 pi)
SEGS_PER_TURN = 7       # 7 segments a turn with 6 colors: the rainbow shifts one color per turn
N_SEG = TURNS * SEGS_PER_TURN
TH_S = 1.5 * math.pi
TH_E = TH_S + 2 * math.pi * TURNS
L_HELIX = DS * (TH_E - TH_S)
L_SEG = L_HELIX / N_SEG
Y_END = 4.6
Y_S = Y_END + HH * (TH_E - TH_S)
SEP = 0.14
IN_RAIL_W, IN_RAIL_H = 0.2, 0.42
GL_W, GL_H = 0.10, 1.25
POLE_R = 1.3
POLE_TOP = Y_S + 4.2
DISH_R = 11.0
DISH_RIM = 0.5
DISH_FLOOR = 0.7
DISH_TOP = 2.2
FEED_BETA = math.radians(7.0)   # feeder rail slope (top left)
FEED_X0 = -90.0
EXIT_BETA = math.radians(3.0)   # exit rail slope (bottom right)
EXIT_X1 = 90.0

SEG_SRGB = [(238, 50, 50), (250, 138, 28), (250, 206, 38), (44, 196, 96), (36, 150, 240), (176, 84, 232)]

TRACK_BASE_LIN = srgb2lin((62, 66, 74))
POLE_LIN = srgb2lin((92, 98, 108))
EDGE_LIN = srgb2lin((214, 224, 236))

OID_FLOOR = 0
OID_SEG0 = 1
OID_DARK = 40
OID_POLE = 41
OID_DISH = 42
OID_RAIL = 43
OID_GLASS = 50
OID_SKY = 255

CAM_TARGET = np.array([0.0, 18.6, 0.0])
CAM_AZ = math.radians(0.0)
CAM_EL = math.radians(20.0)
CAM_DIST = 104.0
CAM_FOVY = math.radians(26.5)
CAM_SHIFT = (0.0, 0.0)

FOG_START = 190.0
FOG_DIST = 120.0
# ================================================================= END SETTINGS


def seg_srgb(k):
    return SEG_SRGB[k % len(SEG_SRGB)]


def camera():
    return look.camera_from(CAM_TARGET, CAM_AZ, CAM_EL, CAM_DIST)


def light_dir():
    return look.light_dir_for(camera())


def y_top(th):
    return Y_S - HH * (th - TH_S)


def theta_of_s(s):
    return TH_S + s / DS


def seg_bounds(k):
    return theta_of_s(k * L_SEG), theta_of_s((k + 1) * L_SEG)


def surf_normal(th, r=RC):
    n = np.array([-HH * math.sin(th), r, HH * math.cos(th)])
    return n / np.linalg.norm(n)


def center_on_track(s):
    th = theta_of_s(s)
    p = np.array([RC * math.cos(th), y_top(th), RC * math.sin(th)])
    return p + R * surf_normal(th)


def rail_y(x):
    """Top of the feeder rail for x <= 0, of the exit rail for x >= 0."""
    return Y_S - x * math.tan(FEED_BETA) if x <= 0 else Y_END - x * math.tan(EXIT_BETA)


def project(p, w=W, h=H):
    return look.project_with(camera(), CAM_FOVY, CAM_SHIFT, p, w, h)


class Mesh:
    def __init__(self):
        self.mats = []
        self.tris = []

    def mat(self, alb, gloss, rough, oid, glass=0.0):
        self.mats.append((*map(float, alb), float(gloss), float(rough), float(oid), float(glass)))
        return len(self.mats) - 1

    def tri(self, a, b, c, na, nb, nc, m):
        self.tris.append((*a, *b, *c, *na, *nb, *nc, float(m)))

    def quad(self, a, b, c, d, na, nb, nc, nd, m):
        self.tri(a, b, c, na, nb, nc, m)
        self.tri(a, c, d, na, nc, nd, m)

    def flatquad(self, a, b, c, d, m):
        n = np.cross(np.subtract(b, a), np.subtract(c, a))
        n = n / (np.linalg.norm(n) + 1e-12)
        self.quad(a, b, c, d, n, n, n, n, m)

    def box(self, center, axes, half, m):
        c = np.asarray(center, float)
        ax = [np.asarray(a, float) for a in axes]
        hx, hy, hz = half
        corners = {}
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    corners[(sx, sy, sz)] = c + sx * hx * ax[0] + sy * hy * ax[1] + sz * hz * ax[2]
        faces = [((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)), ((-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)),
                 ((-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)), ((-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)),
                 ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1))]
        for f in faces:
            self.flatquad(*[corners[k] for k in f], m)

    def write(self, path):
        with open(path, "wb") as f:
            f.write(struct.pack("ii", len(self.tris), len(self.mats)))
            f.write(np.array(self.mats, np.float32).tobytes())
            f.write(np.array(self.tris, np.float32).tobytes())


def _rail(M, x0, x1, ry, slope, m_rail):
    """A straight rail at z = -RC from x0 to x1 (x0 < x1) with top surface y = ry(x): floor, side walls, bottom."""
    zc = -RC
    zl, zr = zc - TW / 2, zc + TW / 2
    M.flatquad((x0, ry(x0), zr), (x1, ry(x1), zr), (x1, ry(x1), zl), (x0, ry(x0), zl), m_rail)
    for zz, w_ in ((zl - 0.26, 0.26), (zr, 0.26)):
        za, zb = zz, zz + w_
        for (p0, p1, p2, p3) in [
            ((x0, ry(x0) - TTH, zb), (x1, ry(x1) - TTH, zb), (x1, ry(x1) + 0.45, zb), (x0, ry(x0) + 0.45, zb)),
            ((x1, ry(x1) - TTH, za), (x0, ry(x0) - TTH, za), (x0, ry(x0) + 0.45, za), (x1, ry(x1) + 0.45, za)),
            ((x0, ry(x0) + 0.45, za), (x0, ry(x0) + 0.45, zb), (x1, ry(x1) + 0.45, zb), (x1, ry(x1) + 0.45, za)),
        ]:
            M.flatquad(p0, p1, p2, p3, m_rail)
    M.flatquad((x0, ry(x0) - TTH, zl), (x1, ry(x1) - TTH, zl), (x1, ry(x1) - TTH, zr), (x0, ry(x0) - TTH, zr),
               m_rail)
    M.flatquad((x0, ry(x0) - TTH, zr), (x1, ry(x1) - TTH, zr), (x1, ry(x1), zr), (x0, ry(x0), zr), m_rail)


def build_mesh():
    M = Mesh()
    seg_mats = [M.mat(srgb2lin(seg_srgb(k)), 1.0, 0.22, OID_SEG0 + k) for k in range(N_SEG)]
    m_track = M.mat(TRACK_BASE_LIN, 0.6, 0.35, OID_DARK)
    m_dark = M.mat(DARK_LIN, 0.5, 0.45, OID_DARK)
    m_under = M.mat(DARK_LIN, 0.3, 0.5, OID_DARK)
    m_pole = M.mat(POLE_LIN, 1.6, 0.18, OID_POLE)
    m_dish = M.mat(DARK_LIN, 0.5, 0.45, OID_DISH)
    m_rail = M.mat(DARK_LIN, 0.5, 0.45, OID_RAIL)
    m_glass = M.mat((0.85, 0.92, 1.0), 0.0, 0.05, OID_GLASS, 1.0)
    m_edge = M.mat(EDGE_LIN, 0.8, 0.2, OID_DARK)

    bounds = [seg_bounds(k) for k in range(N_SEG)]

    def track_mat(th):
        for k, (a, b) in enumerate(bounds):
            if a <= th < b:
                ds = min(th - a, b - th) * DS
                if ds < SEP / 2:
                    return m_track
                return seg_mats[k]
        return m_track

    breaks = [TH_S, TH_E]
    for a, b in bounds:
        breaks += [a, b, a + SEP / 2 / DS, b - SEP / 2 / DS]
    breaks = sorted(set(round(x, 9) for x in breaks if TH_S <= x <= TH_E))
    ths = []
    for a, b in zip(breaks[:-1], breaks[1:]):
        n = max(1, int(math.ceil((b - a) / math.radians(2.5))))
        for i in range(n):
            ths.append(a + (b - a) * i / n)
    ths.append(TH_E)

    def P(r, th, dy=0.0):
        return (r * math.cos(th), y_top(th) + dy, r * math.sin(th))

    def radial(th, sgn=1.0):
        return (sgn * math.cos(th), 0.0, sgn * math.sin(th))

    for t0, t1 in zip(ths[:-1], ths[1:]):
        tm = 0.5 * (t0 + t1)
        m = track_mat(tm)
        n0i, n1i = surf_normal(t0, RIN), surf_normal(t1, RIN)
        n0o, n1o = surf_normal(t0, ROUT), surf_normal(t1, ROUT)
        M.quad(P(RIN, t0), P(RIN, t1), P(ROUT, t1), P(ROUT, t0), n0i, n1i, n1o, n0o, m)
        M.quad(P(ROUT, t0, -TTH), P(ROUT, t1, -TTH), P(RIN, t1, -TTH), P(RIN, t0, -TTH),
               -n0o, -n1o, -n1i, -n0i, m_under)
        ri = RIN - IN_RAIL_W
        M.quad(P(ri, t0, -TTH), P(ri, t1, -TTH), P(ri, t1, IN_RAIL_H), P(ri, t0, IN_RAIL_H),
               radial(t0, -1), radial(t1, -1), radial(t1, -1), radial(t0, -1), m_dark)
        M.quad(P(RIN, t0, IN_RAIL_H), P(RIN, t1, IN_RAIL_H), P(RIN, t1, 0), P(RIN, t0, 0),
               radial(t0), radial(t1), radial(t1), radial(t0), m_dark)
        up = (0.0, 1.0, 0.0)
        M.quad(P(ri, t0, IN_RAIL_H), P(ri, t1, IN_RAIL_H), P(RIN, t1, IN_RAIL_H), P(RIN, t0, IN_RAIL_H),
               up, up, up, up, m_dark)
        ro = ROUT + GL_W
        M.quad(P(ROUT, t0, 0), P(ROUT, t1, 0), P(ROUT, t1, GL_H), P(ROUT, t0, GL_H),
               radial(t0, -1), radial(t1, -1), radial(t1, -1), radial(t0, -1), m_glass)
        M.quad(P(ROUT, t0, GL_H), P(ROUT, t1, GL_H), P(ro, t1, GL_H), P(ro, t0, GL_H), up, up, up, up, m_edge)
        M.quad(P(ROUT, t0, -TTH), P(ROUT, t1, -TTH), P(ROUT, t1, 0), P(ROUT, t0, 0),
               radial(t0), radial(t1), radial(t1), radial(t0), m_under)
        M.quad(P(ro, t0, -TTH), P(ro, t1, -TTH), P(ro, t1, GL_H - 0.06), P(ro, t0, GL_H - 0.06),
               radial(t0), radial(t1), radial(t1), radial(t0), m_glass)

    nseg = 64
    for i in range(nseg):
        a0 = 2 * math.pi * i / nseg
        a1 = 2 * math.pi * (i + 1) / nseg

        def cyl(r, a, y):
            return (r * math.cos(a), y, r * math.sin(a))

        M.quad(cyl(POLE_R, a0, DISH_FLOOR), cyl(POLE_R, a1, DISH_FLOOR), cyl(POLE_R, a1, POLE_TOP),
               cyl(POLE_R, a0, POLE_TOP), radial(a0), radial(a1), radial(a1), radial(a0), m_pole)
        cr = POLE_R + 0.25
        M.quad(cyl(cr, a0, POLE_TOP), cyl(cr, a1, POLE_TOP), cyl(cr, a1, POLE_TOP + 0.45),
               cyl(cr, a0, POLE_TOP + 0.45), radial(a0), radial(a1), radial(a1), radial(a0), m_pole)
        up = (0.0, 1.0, 0.0)
        M.tri((0.0, POLE_TOP + 0.45, 0.0), cyl(cr, a1, POLE_TOP + 0.45), cyl(cr, a0, POLE_TOP + 0.45), up, up, up,
              m_pole)
        dn = (0.0, -1.0, 0.0)
        M.quad(cyl(POLE_R, a0, POLE_TOP), cyl(POLE_R, a1, POLE_TOP), cyl(cr, a1, POLE_TOP), cyl(cr, a0, POLE_TOP),
               dn, dn, dn, dn, m_pole)
        rin = DISH_R - DISH_RIM
        M.tri(cyl(0.0, a0, DISH_FLOOR), cyl(rin, a1, DISH_FLOOR), cyl(rin, a0, DISH_FLOOR), up, up, up, m_dish)
        M.quad(cyl(rin, a0, DISH_TOP), cyl(rin, a1, DISH_TOP), cyl(rin, a1, DISH_FLOOR), cyl(rin, a0, DISH_FLOOR),
               radial(a0, -1), radial(a1, -1), radial(a1, -1), radial(a0, -1), m_dish)
        M.quad(cyl(rin, a0, DISH_TOP), cyl(DISH_R, a0, DISH_TOP), cyl(DISH_R, a1, DISH_TOP), cyl(rin, a1, DISH_TOP),
               up, up, up, up, m_dish)
        M.quad(cyl(DISH_R, a0, 0.0), cyl(DISH_R, a1, 0.0), cyl(DISH_R, a1, DISH_TOP), cyl(DISH_R, a0, DISH_TOP),
               radial(a0), radial(a1), radial(a1), radial(a0), m_dish)

    th = TH_S + 0.6
    while th < TH_E - 0.3:
        rmid = 0.5 * (POLE_R - 0.2 + RIN - IN_RAIL_W)
        half_len = 0.5 * (RIN - IN_RAIL_W - (POLE_R - 0.2))
        yc = y_top(th) - TTH - 0.17
        c = (rmid * math.cos(th), yc, rmid * math.sin(th))
        ax = (math.cos(th), 0.0, math.sin(th))
        az = (-math.sin(th), 0.0, math.cos(th))
        M.box(c, (ax, (0.0, 1.0, 0.0), az), (half_len, 0.17, 0.17), m_dark)
        th += 2 * math.pi / 3

    _rail(M, FEED_X0, 0.0, lambda x: Y_S - x * math.tan(FEED_BETA), FEED_BETA, m_rail)
    _rail(M, 0.0, EXIT_X1, lambda x: Y_END - x * math.tan(EXIT_BETA), EXIT_BETA, m_rail)
    return M


def write_scene(path, meshpath, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        f.write(f"mesh {meshpath}\n")


if __name__ == "__main__":
    m = build_mesh()
    print("tris", len(m.tris), "mats", len(m.mats), "Y_S", round(Y_S, 2), "L_HELIX", round(L_HELIX, 2),
          "L_SEG", round(L_SEG, 2))
    for name, p in {"poleTop": (0, POLE_TOP + 0.45, 0), "dishFront": (0, 0, DISH_R), "dishL": (-DISH_R, 0, 0),
                    "dishR": (DISH_R, 2.2, 0), "start": (0, Y_S, -RC), "end": (0, Y_END, -RC),
                    "feed-45": (-45, rail_y(-45), -RC), "feed-43": (-43, rail_y(-43), -RC),
                    "exit+45": (45, rail_y(45), -RC), "spiralR": (ROUT, 20, 0)}.items():
        x, y, z = project(p)
        print(f"{name}: ({x / W:.3f}, {y / H:.3f})")
