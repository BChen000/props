"""The twin rainbow staircase of ../marble-twin-stairs as an endless 16:9 loop: the same two lanes of 16 tiles, pillars
and camera, so the middle 9:16 strip of the frame is the Short's framing. The tray is replaced by a wide trough that
carries the marbles of both lanes into an exit tube, so marbles can flow forever.

A marble drops in from above the frame onto the top tile of its lane, hops one tile per beat, lands in the trough one
beat after its last tile and rolls into the exit tube. hop(e, t, vz, lane) gives its center at time t for a marble
that lands on its top tile at time e. Lane 1 (front) carries the melody, lane 0 (back) the accompaniment.
"""
import colorsys
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

NAME = "twin"

# ===================================================================== SETTINGS (shipped values)
T = 16                  # tiles per lane
NL = 2
LANE_Z = [-3.6, 3.6]    # lane 0 (accompaniment, back), lane 1 (melody, front)
DX = 2.7
DY = 1.6
Y7 = 3.0                # top of the lowest tile
Y0 = Y7 + (T - 1) * DY
TILE_HX = 1.2
TILE_HZ = 2.5
TILE_TH = 0.6
PIL_HX = 1.0
PIL_HZ = 2.1

TAU = 0.5               # s per hop (one beat); 15 frames
HOP_APEX = 1.4
DROP_T = 0.85           # a marble falls into view this long before landing on its top tile
DROP_V = 65.0

EX_Y = Y7 - DY          # trough floor top: where tile 16 would be
EX_X0 = (T - 1) * DX + TILE_HX + 0.2
EX_HZ = 6.3             # trough inner half-width (both lanes, plus their sideways drift)
EX_WALL_T = 0.4
EX_WALL_H = 0.95
EX_TUBE = 52.0          # exit tube mouth (x)
EX_TUBE_H = 2.7
EX_X1 = EX_TUBE + 4.5  # end of the exit block (a short tunnel)
VZ_MAX = 0.2            # sideways drift on the stairs, units per second

OID_FLOOR = 0
OID_TILE0 = 1           # 1..32
OID_PILLAR0 = 40
OID_TRAY = 60
OID_EXIT = 61
OID_SKY = 255

CAM_TARGET = np.array([26.0, 10.0, 0.0])
CAM_AZ = math.radians(72.0)
CAM_EL = math.radians(17.0)
CAM_DIST = 140.0
CAM_FOVY = math.radians(28.0)
CAM_SHIFT = (0.0, 0.0)
FOG_START = 200.0
FOG_DIST = 120.0
# ================================================================= END SETTINGS

_s1 = math.sqrt(2 * HOP_APEX)
_s2 = math.sqrt(2 * HOP_APEX + 2 * DY)
G = ((_s1 + _s2) / TAU) ** 2
V_UP = math.sqrt(2 * G * HOP_APEX)
V_LAND = G * TAU - V_UP
VX = DX / TAU
T_LAND = T * TAU
T_BEFORE = DROP_T


def _rainbow(u, s=0.80, v=0.96):
    r, g, b = colorsys.hsv_to_rgb(u % 1.0, s, v)
    return (r * 255, g * 255, b * 255)


# back lane runs red -> violet, front lane starts half way round the color wheel
TILE_SRGB = ([_rainbow(0.0 + 0.82 * i / (T - 1)) for i in range(T)]
             + [_rainbow(0.5 + 0.82 * i / (T - 1)) for i in range(T)])
TILE_LIN = [srgb2lin(c) for c in TILE_SRGB]


def tile_pos(k):
    lane, i = divmod(k, T)
    return i * DX, Y0 - i * DY, LANE_Z[lane]


def tile_oid(lane, i):
    return OID_TILE0 + lane * T + i


def lane_z(lane):
    return LANE_Z[lane]


def camera():
    return look.camera_from(CAM_TARGET, CAM_AZ, CAM_EL, CAM_DIST)


def light_dir():
    return look.light_dir_for(camera())


def project(p, w=W, h=H):
    return look.project_with(camera(), CAM_FOVY, CAM_SHIFT, p, w, h)


def boxes():
    out = []

    def box(mn, mx, alb, gloss, rough, oid, rot=0.0, piv=(0.0, 0.0, 0.0)):
        out.append(dict(mn=list(map(float, mn)), mx=list(map(float, mx)), alb=list(map(float, alb)),
                        gloss=float(gloss), rough=float(rough), oid=int(oid), rot=float(rot),
                        piv=list(map(float, piv))))

    for k in range(NL * T):
        x, y, zc = tile_pos(k)
        i = k % T
        box((x - TILE_HX, y - TILE_TH, zc - TILE_HZ), (x + TILE_HX, y, zc + TILE_HZ), TILE_LIN[k], 1.0, 0.22,
            OID_TILE0 + k)
        box((x - PIL_HX, 0.0, zc - PIL_HZ), (x + PIL_HX, y - TILE_TH + 0.02, zc + PIL_HZ), DARK_LIN, 0.5, 0.45,
            OID_PILLAR0 + i)

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


def hop(e, t, vz, lane):
    """Center of a marble that lands on its lane's top tile at time e, at time t."""
    zl = LANE_Z[lane]
    if t < e:
        tp = e - t
        y = Y0 + R + DROP_V * tp - 0.5 * G * tp * tp
        return np.array([-VX * tp, y, zl])
    if t < e + T_LAND:
        k = int(math.floor((t - e) / TAU))
        dt = t - (e + k * TAU)
        return np.array([k * DX + VX * dt, Y0 - k * DY + R + V_UP * dt - 0.5 * G * dt * dt, zl + vz * (t - e)])
    x = T * DX + VX * (t - e - T_LAND)
    return np.array([x, EX_Y + R, zl + vz * T_LAND])


def hidden(c):
    """Inside the exit tube."""
    return c[0] > EX_TUBE + 1.02 * R


def gone(e, t):
    return t < e - T_BEFORE or T * DX + VX * (t - e - T_LAND) > EX_TUBE + 4.0


def spill(k, c):
    if k >= NL * T:
        return None
    x, y, zc = tile_pos(k)
    return np.array([min(max(c[0], x - TILE_HX), x + TILE_HX), y, min(max(c[2], zc - TILE_HZ), zc + TILE_HZ)])
