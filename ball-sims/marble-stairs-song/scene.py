"""Geometry and camera of the single rainbow staircase: 8 tiles on dark pillars, a feeder chute with a tube,
and a tray. Marbles hop one tile per beat, so the hop physics (G, V_UP, ...) and the chute position follow BPM.

Overrides (environment): MARBLE_BPM (default 112.5, the shipped tempo), MARBLE_CAM=thumb (closer thumbnail camera).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import look
from look import (W, H, FPS, R, LIGHT_ANG, LIGHT_COL, SKY_Z, SKY_H, EXPOSURE, FLOOR_LIN, DARK_LIN, srgb2lin,
                  vignette, tonemap)

# ===================================================================== SETTINGS (shipped values)
T = 8
DX = 3.0
DY = 2.4
Y7 = 3.0
Y0 = Y7 + (T - 1) * DY
TILE_HX = 1.35
TILE_HZ = 3.6
TILE_TH = 0.7
PIL_H = 1.05

TRAY_WALL = 0.5
TRAY_IN_X = (22.6, 32.2)
TRAY_IN_Z = (-5.2, 5.2)
TRAY_FLOOR = 0.6
TRAY_TOP = 2.25

BPM = float(os.environ.get("MARBLE_BPM", "112.5"))
TAU = 60.0 / BPM
HOP_APEX = 1.7

_s1 = math.sqrt(2 * HOP_APEX)
_s2 = math.sqrt(2 * HOP_APEX + 2 * DY)
G = ((_s1 + _s2) / TAU) ** 2
V_UP = math.sqrt(2 * G * HOP_APEX)
V_LAND = G * TAU - V_UP
VX = DX / TAU

CHUTE_THETA = math.radians(6.0)
CH_TF = (V_LAND - VX * math.tan(CHUTE_THETA)) / G
CH_DX = VX * CH_TF
CH_DY = VX * math.tan(CHUTE_THETA) * CH_TF + 0.5 * G * CH_TF ** 2
CH_EXIT = np.array([-CH_DX, Y0 + R + CH_DY, 0.0])
CH_U = np.array([math.cos(CHUTE_THETA), -math.sin(CHUTE_THETA), 0.0])
CH_N = np.array([math.sin(CHUTE_THETA), math.cos(CHUTE_THETA), 0.0])
CH_PIVOT = CH_EXIT - R * CH_N
CH_LEN = 60.0
CH_IN_HW = 1.18
CH_WALL_T = 0.32
CH_WALL_H = 0.95
CH_FLOOR_T = 0.38
TUBE_MOUTH = -5.4
TUBE_TOP = 2.45


TILE_SRGB = [
    (238, 52, 52),
    (250, 138, 28),
    (250, 206, 38),
    (150, 214, 48),
    (36, 190, 96),
    (28, 196, 204),
    (44, 118, 238),
    (152, 82, 228),
]
TILE_LIN = [srgb2lin(c) for c in TILE_SRGB]

OID_FLOOR = 0
OID_TILE0 = 1
OID_PILLAR0 = 9
OID_TRAY = 17
OID_CHUTE = 18
OID_POST = 19
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


def camera():
    return look.camera_from(CAM_TARGET, CAM_AZ, CAM_EL, CAM_DIST)


def light_dir():
    return look.light_dir_for(camera())


def project(p, w=W, h=H):
    return look.project_with(camera(), CAM_FOVY, CAM_SHIFT, p, w, h)


def tile_top(k):
    return k * DX, Y0 - k * DY


def boxes():
    out = []

    def box(mn, mx, alb, gloss, rough, oid, rot=0.0, piv=(0.0, 0.0, 0.0)):
        out.append(dict(mn=list(map(float, mn)), mx=list(map(float, mx)), alb=list(map(float, alb)),
                        gloss=float(gloss), rough=float(rough), oid=int(oid), rot=float(rot),
                        piv=list(map(float, piv))))

    for i in range(T):
        x = i * DX
        y = Y0 - i * DY
        box((x - TILE_HX, y - TILE_TH, -TILE_HZ), (x + TILE_HX, y, TILE_HZ), TILE_LIN[i], 1.0, 0.22,
            OID_TILE0 + i)
        box((x - PIL_H, 0.0, -PIL_H), (x + PIL_H, y - TILE_TH + 0.02, PIL_H), DARK_LIN, 0.5, 0.45,
            OID_PILLAR0 + i)
    x0, x1 = TRAY_IN_X
    z0, z1 = TRAY_IN_Z
    w = TRAY_WALL
    box((x0 - w, 0.0, z0 - w), (x1 + w, TRAY_FLOOR, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x0 - w, 0.0, z0 - w), (x0, TRAY_TOP, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x1, 0.0, z0 - w), (x1 + w, TRAY_TOP, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x0, 0.0, z0 - w), (x1, TRAY_TOP, z0), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x0, 0.0, z1), (x1, TRAY_TOP, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)

    rot = -CHUTE_THETA
    piv = CH_PIVOT
    hw = CH_IN_HW
    box((-CH_LEN, -CH_FLOOR_T, -hw - CH_WALL_T), (0.0, 0.0, hw + CH_WALL_T), DARK_LIN, 0.5, 0.45, OID_CHUTE,
        rot, piv)
    box((-CH_LEN, -CH_FLOOR_T, hw), (0.0, CH_WALL_H, hw + CH_WALL_T), DARK_LIN, 0.5, 0.45, OID_CHUTE, rot, piv)
    box((-CH_LEN, -CH_FLOOR_T, -hw - CH_WALL_T), (0.0, CH_WALL_H, -hw), DARK_LIN, 0.5, 0.45, OID_CHUTE, rot, piv)
    box((-CH_LEN, -CH_FLOOR_T, -hw - CH_WALL_T - 0.12), (TUBE_MOUTH, TUBE_TOP, hw + CH_WALL_T + 0.12), DARK_LIN, 0.5,
        0.45, OID_CHUTE, rot, piv)
    box((TUBE_MOUTH, 0.02, -hw + 0.06), (TUBE_MOUTH + 0.012, TUBE_TOP - 0.28, hw - 0.06), np.array([0.004, 0.004, 0.005]),
        0.0, 0.9, OID_CHUTE, rot, piv)
    for px in (-9.0, -24.0, -39.0):
        s = (px - CH_PIVOT[0]) / CH_U[0]
        ytop = CH_PIVOT[1] + s * CH_U[1] - CH_FLOOR_T / math.cos(CHUTE_THETA)
        box((px - 0.55, 0.0, -0.55), (px + 0.55, ytop + 0.05, 0.55), DARK_LIN, 0.5, 0.45, OID_POST)
    return out


def write_scene(path, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        look.write_boxes(f, boxes())


if os.environ.get("MARBLE_CAM") == "thumb":
    CAM_FOVY = math.radians(24.0)
    CAM_AZ = math.radians(62.0)
    CAM_EL = math.radians(26.0)
    CAM_DIST = 126.0
    CAM_TARGET = np.array([14.5, 12.8, 0.5])
