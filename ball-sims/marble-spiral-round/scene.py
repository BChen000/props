"""Geometry and camera of the spiral round: a helix track around a pole, built from the song (one colored segment
per note, as long as the note), clear glass outer walls, a feeder rail with a gate at the top, and a round dish.

The set is a triangle mesh for ../marble-raytrace-kit/meshtrace.c. Overrides (environment): MARBLE_SONG (a key of
songs.SONGS, default row-row-row).
"""
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import look
from look import (W, H, FPS, R, LIGHT_ANG, LIGHT_COL, SKY_Z, SKY_H, EXPOSURE, FLOOR_LIN, DARK_LIN, srgb2lin,
                  vignette, tonemap)
from songs import SONGS, PITCH_SRGB

SONG_NAME = os.environ.get("MARBLE_SONG", "row-row-row")
SONG = [tuple(n) for n in SONGS[SONG_NAME]["notes"]]
EIGHTHS = sum(d for _, d in SONG)
STARTS = np.concatenate([[0], np.cumsum([d for _, d in SONG])])

# ===================================================================== SETTINGS (shipped values)
RC = 6.4
TW = 3.4
RIN = RC - TW / 2
ROUT = RC + TW / 2
TTH = 0.45
PITCH = 7.2
HH = PITCH / (2 * math.pi)
DS = math.sqrt(RC * RC + HH * HH)
LE = 3.3
LEAD_IN = 1.6
LEAD_OUT = 11.0
TOTAL = LEAD_IN + EIGHTHS * LE + LEAD_OUT
TH_S = 1.5 * math.pi
TH_E = TH_S + TOTAL / DS
Y_END = 4.0
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
RAIL_BETA = math.radians(7.0)
RAIL_X0 = -60.0
GATE_X = -9.0

EIGHTH = SONGS[SONG_NAME]["eighth"]
BAR_EIGHTHS = SONGS[SONG_NAME].get("bar_eighths", 6)
VEL = LE / EIGHTH
G = 75.0


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

CAM_TARGET = np.array([0.0, 17.6, 0.0])
CAM_AZ = math.radians(0.0)
CAM_EL = math.radians(21.0)
CAM_DIST = 121.0
CAM_FOVY = math.radians(30.0)
CAM_SHIFT = (0.0, 0.0)

FOG_START = 190.0
FOG_DIST = 120.0
# ================================================================= END SETTINGS


def camera():
    return look.camera_from(CAM_TARGET, CAM_AZ, CAM_EL, CAM_DIST)


def light_dir():
    return look.light_dir_for(camera())


def y_top(th):
    return Y_S - HH * (th - TH_S)


def theta_of_s(s):
    return TH_S + s / DS


def seg_bounds(k):
    s0 = LEAD_IN + STARTS[k] * LE
    s1 = LEAD_IN + STARTS[k + 1] * LE
    return theta_of_s(s0), theta_of_s(s1)


def surf_normal(th, r=RC):
    n = np.array([-HH * math.sin(th), r, HH * math.cos(th)])
    return n / np.linalg.norm(n)


def center_on_track(s):
    th = theta_of_s(s)
    p = np.array([RC * math.cos(th), y_top(th), RC * math.sin(th)])
    return p + R * surf_normal(th)


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


def build_mesh():
    M = Mesh()
    seg_mats = [M.mat(srgb2lin(PITCH_SRGB[p]), 1.0, 0.22, OID_SEG0 + k) for k, (p, _) in enumerate(SONG)]
    m_track = M.mat(TRACK_BASE_LIN, 0.6, 0.35, OID_DARK)
    m_dark = M.mat(DARK_LIN, 0.5, 0.45, OID_DARK)
    m_under = M.mat(DARK_LIN, 0.3, 0.5, OID_DARK)
    m_pole = M.mat(POLE_LIN, 1.6, 0.18, OID_POLE)
    m_dish = M.mat(DARK_LIN, 0.5, 0.45, OID_DISH)
    m_rail = M.mat(DARK_LIN, 0.5, 0.45, OID_RAIL)
    m_glass = M.mat((0.85, 0.92, 1.0), 0.0, 0.05, OID_GLASS, 1.0)
    m_edge = M.mat(EDGE_LIN, 0.8, 0.2, OID_DARK)

    bounds = []
    for k in range(len(SONG)):
        a, b = seg_bounds(k)
        bounds.append((a, b))

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

    for th, sgn in ((TH_E, 1.0), (TH_S, -1.0)):
        tang = np.array([-math.sin(th), -HH / RC, math.cos(th)]) * sgn
        tang /= np.linalg.norm(tang)
        ri = RIN - IN_RAIL_W
        ro = ROUT + GL_W
        quad = [P(ri, th, -TTH), P(ro, th, -TTH), P(ro, th, 0.0), P(ri, th, 0.0)]
        nrm = tuple(tang)
        M.quad(*quad, nrm, nrm, nrm, nrm, m_dark)

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

    zc = -RC
    x1 = 0.0
    x0 = RAIL_X0
    tb = math.tan(RAIL_BETA)

    def ry(x):
        return Y_S + (x1 - x) * tb

    nrm_up = np.array([tb, 1.0, 0.0])
    nrm_up /= np.linalg.norm(nrm_up)
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
    return M


def write_scene(path, meshpath, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        f.write(f"mesh {meshpath}\n")


if __name__ == "__main__":
    m = build_mesh()
    print("tris", len(m.tris), "mats", len(m.mats))
    print("Y_S", Y_S, "TH_E-TH_S", TH_E - TH_S, "turns", (TH_E - TH_S) / (2 * math.pi), "VEL", VEL)
    for name, p in {"poleTop": (0, POLE_TOP, 0), "dishFront": (0, 0, DISH_R), "dishL": (-DISH_R, 0, 0),
                    "dishR": (DISH_R, 2.2, 0), "start": (0, Y_S, -RC), "gate": (GATE_X, Y_S + 9 * math.tan(RAIL_BETA), -RC),
                    "railL": (-22, Y_S + 22 * math.tan(RAIL_BETA), -RC), "spiralR": (ROUT, 20, 0)}.items():
        x, y, z = project(p)
        print(f"{name}: ({x / W:.2f}, {y / H:.2f})")
