"""The rainbow staircase of ../marble-stairs-song as an endless 16:9 loop: the same 8 tiles, pillars, feeder chute and
tube, and the Short's own camera, so the middle 9:16 strip of the frame is the Short's framing. The tray is replaced by
a trough that carries every marble right into an exit tube, so marbles can flow forever.

A marble rolls out of the feeder tube, falls onto tile 0, hops one tile per beat, lands in the trough one beat after
tile 7 and rolls into the exit tube. hop(e, t) gives its center at time t for a marble that lands on tile 0 at time e.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import look

look.W, look.H = int(os.environ.get("LOOP_W", "1920")), int(os.environ.get("LOOP_H", "1080"))
from look import (W, H, FPS, R, LIGHT_ANG, LIGHT_COL, SKY_Z, SKY_H, EXPOSURE, FLOOR_LIN, DARK_LIN, srgb2lin,
                  vignette, tonemap)

NAME = "stairs"

# ===================================================================== SETTINGS (shipped values)
T = 8                   # tiles
NL = 1                  # lanes
DX = 3.0
DY = 2.4
Y7 = 3.0
Y0 = Y7 + (T - 1) * DY
TILE_HX = 1.35
TILE_HZ = 3.6
TILE_TH = 0.7
PIL_H = 1.05

TAU = 0.5               # s per hop (one beat); 15 frames
HOP_APEX = 1.7

CHUTE_THETA = math.radians(6.0)
CH_LEN = 60.0
CH_IN_HW = 1.18
CH_WALL_T = 0.32
CH_WALL_H = 0.95
CH_FLOOR_T = 0.38
TUBE_MOUTH = -5.4
TUBE_TOP = 2.45

EX_Y = Y7 - DY          # trough floor top: where tile 8 would be
EX_X0 = (T - 1) * DX + TILE_HX + 0.25
EX_HZ = 3.2             # trough inner half-width (marbles drift up to 2 units sideways on the stairs)
EX_WALL_T = 0.32
EX_WALL_H = 0.95
EX_TUBE = 33.5          # exit tube mouth (x)
EX_TUBE_H = 3.3
EX_X1 = EX_TUBE + 7.0  # end of the exit block (a short tunnel)
VZ_MAX = 0.5            # sideways drift on the stairs, units per second

TILE_SRGB = [(238, 52, 52), (250, 138, 28), (250, 206, 38), (150, 214, 48), (36, 190, 96), (28, 196, 204),
             (44, 118, 238), (152, 82, 228)]
TILE_LIN = [srgb2lin(c) for c in TILE_SRGB]

OID_FLOOR = 0
OID_TILE0 = 1
OID_PILLAR0 = 9
OID_TRAY = 17
OID_CHUTE = 18
OID_POST = 19
OID_EXIT = 20
OID_SKY = 255

FOG_START = 160.0
FOG_DIST = 120.0
CAM_TARGET = np.array([16.0, 12.6, 0.5])
CAM_AZ = math.radians(55.0)
CAM_EL = math.radians(24.0)
CAM_DIST = 126.0
CAM_FOVY = math.radians(30.0)
CAM_SHIFT = (0.0, 0.0)
# ================================================================= END SETTINGS

_s1 = math.sqrt(2 * HOP_APEX)
_s2 = math.sqrt(2 * HOP_APEX + 2 * DY)
G = ((_s1 + _s2) / TAU) ** 2
V_UP = math.sqrt(2 * G * HOP_APEX)
V_LAND = G * TAU - V_UP
VX = DX / TAU

CH_TF = (V_LAND - VX * math.tan(CHUTE_THETA)) / G
CH_DX = VX * CH_TF
CH_DY = VX * math.tan(CHUTE_THETA) * CH_TF + 0.5 * G * CH_TF ** 2
CH_EXIT = np.array([-CH_DX, Y0 + R + CH_DY, 0.0])
CH_U = np.array([math.cos(CHUTE_THETA), -math.sin(CHUTE_THETA), 0.0])
CH_N = np.array([math.sin(CHUTE_THETA), math.cos(CHUTE_THETA), 0.0])
CH_PIVOT = CH_EXIT - R * CH_N
T_LAND = T * TAU        # from landing on tile 0 to landing in the trough
T_BEFORE = CH_TF + 8.0 / VX   # visible this long before landing on tile 0 (it is inside the tube before that)


def camera():
    return look.camera_from(CAM_TARGET, CAM_AZ, CAM_EL, CAM_DIST)


def light_dir():
    return look.light_dir_for(camera())


def project(p, w=W, h=H):
    return look.project_with(camera(), CAM_FOVY, CAM_SHIFT, p, w, h)


def tile_top(k):
    return k * DX, Y0 - k * DY


def tile_oid(lane, i):
    return OID_TILE0 + i


def lane_z(lane):
    return 0.0


def boxes():
    out = []

    def box(mn, mx, alb, gloss, rough, oid, rot=0.0, piv=(0.0, 0.0, 0.0)):
        out.append(dict(mn=list(map(float, mn)), mx=list(map(float, mx)), alb=list(map(float, alb)),
                        gloss=float(gloss), rough=float(rough), oid=int(oid), rot=float(rot),
                        piv=list(map(float, piv))))

    for i in range(T):
        x, y = tile_top(i)
        box((x - TILE_HX, y - TILE_TH, -TILE_HZ), (x + TILE_HX, y, TILE_HZ), TILE_LIN[i], 1.0, 0.22, OID_TILE0 + i)
        box((x - PIL_H, 0.0, -PIL_H), (x + PIL_H, y - TILE_TH + 0.02, PIL_H), DARK_LIN, 0.5, 0.45, OID_PILLAR0 + i)

    rot = -CHUTE_THETA
    piv = CH_PIVOT
    hw = CH_IN_HW
    box((-CH_LEN, -CH_FLOOR_T, -hw - CH_WALL_T), (0.0, 0.0, hw + CH_WALL_T), DARK_LIN, 0.5, 0.45, OID_CHUTE, rot, piv)
    box((-CH_LEN, -CH_FLOOR_T, hw), (0.0, CH_WALL_H, hw + CH_WALL_T), DARK_LIN, 0.5, 0.45, OID_CHUTE, rot, piv)
    box((-CH_LEN, -CH_FLOOR_T, -hw - CH_WALL_T), (0.0, CH_WALL_H, -hw), DARK_LIN, 0.5, 0.45, OID_CHUTE, rot, piv)
    box((-CH_LEN, -CH_FLOOR_T, -hw - CH_WALL_T - 0.12), (TUBE_MOUTH, TUBE_TOP, hw + CH_WALL_T + 0.12), DARK_LIN, 0.5,
        0.45, OID_CHUTE, rot, piv)
    box((TUBE_MOUTH, 0.02, -hw + 0.06), (TUBE_MOUTH + 0.012, TUBE_TOP - 0.28, hw - 0.06),
        np.array([0.004, 0.004, 0.005]), 0.0, 0.9, OID_CHUTE, rot, piv)
    for px in (-9.0, -24.0, -39.0):
        s = (px - CH_PIVOT[0]) / CH_U[0]
        ytop = CH_PIVOT[1] + s * CH_U[1] - CH_FLOOR_T / math.cos(CHUTE_THETA)
        box((px - 0.55, 0.0, -0.55), (px + 0.55, ytop + 0.05, 0.55), DARK_LIN, 0.5, 0.45, OID_POST)

    zo = EX_HZ + EX_WALL_T
    box((EX_X0, 0.0, -zo), (EX_X1, EX_Y, zo), DARK_LIN, 0.5, 0.45, OID_EXIT)
    box((EX_X0, 0.0, EX_HZ), (EX_X1, EX_Y + EX_WALL_H, zo), DARK_LIN, 0.5, 0.45, OID_EXIT)
    box((EX_X0, 0.0, -zo), (EX_X1, EX_Y + EX_WALL_H, -EX_HZ), DARK_LIN, 0.5, 0.45, OID_EXIT)
    box((EX_X0 - EX_WALL_T, 0.0, -zo), (EX_X0, EX_Y + EX_WALL_H, zo), DARK_LIN, 0.5, 0.45, OID_EXIT)
    box((EX_TUBE, 0.0, -zo - 0.12), (EX_X1, EX_Y + EX_TUBE_H, zo + 0.12), DARK_LIN, 0.5, 0.45, OID_EXIT)
    box((EX_TUBE - 0.012, EX_Y + 0.02, -EX_HZ + 0.06), (EX_TUBE, EX_Y + EX_TUBE_H - 0.3, EX_HZ - 0.06),
        np.array([0.004, 0.004, 0.005]), 0.0, 0.9, OID_EXIT)
    return out


def write_scene(path, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        look.write_boxes(f, boxes())


def hop(e, t, vz, lane=0):
    """Center of a marble that lands on tile 0 at time e, at time t (None once it is gone)."""
    th = CHUTE_THETA
    t_exit = e - CH_TF
    if t < t_exit:
        s = (t_exit - t) * VX / math.cos(th)
        p = CH_EXIT - s * CH_U
        return np.array([p[0], p[1], 0.0])
    if t < e:
        dt = t - t_exit
        return np.array([CH_EXIT[0] + VX * dt, CH_EXIT[1] - VX * math.tan(th) * dt - 0.5 * G * dt * dt, 0.0])
    if t < e + T_LAND:
        k = int(math.floor((t - e) / TAU))
        dt = t - (e + k * TAU)
        return np.array([k * DX + VX * dt, Y0 - k * DY + R + V_UP * dt - 0.5 * G * dt * dt, vz * (t - e)])
    x = T * DX + VX * (t - e - T_LAND)
    return np.array([x, EX_Y + R, vz * T_LAND])


def hidden(c):
    """Inside the feeder tube or the exit tube."""
    if c[0] < 0.5:
        return (c - CH_PIVOT) @ CH_U < TUBE_MOUTH - 1.02 * R
    return c[0] > EX_TUBE + 1.02 * R


def gone(e, t):
    """True before the marble is near the feeder tube's mouth and after it is deep in the exit tube."""
    return t < e - T_BEFORE or T * DX + VX * (t - e - T_LAND) > EX_TUBE + 4.0


def spill(k, c):
    """Point of tile k's top face nearest the marble (its glow lights the marble)."""
    if k >= T:
        return None
    tx, ty = tile_top(k)
    return np.array([min(max(c[0], tx - TILE_HX), tx + TILE_HX), ty, min(max(c[2], -TILE_HZ), TILE_HZ)])
