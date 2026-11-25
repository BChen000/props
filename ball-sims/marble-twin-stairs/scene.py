"""Geometry and camera of the twin staircase: two parallel lanes of 16 rainbow tiles on dark pillars, side by side
toward the camera, ending in one tray. Marbles drop in from above the top tile and hop one tile per beat; the
melody lane is in front, the harmony lane behind. The hop physics (G, V_UP, ...) follow BPM.

Overrides (environment): MARBLE_BPM (default 120, the shipped tempo), MARBLE_CAM=wide (16:9 front camera; use with
MARBLE_RES=1920x1080 and its own BUILD_DIR).
"""
import colorsys
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
T = 16                  # tiles per lane
NL = 2
NT = T * NL
LANE_Z = [-3.6, 3.6]    # lane 0 (harmony, back), lane 1 (melody, front)
DX = 2.7
DY = 1.6
Y7 = 3.0                # top of the lowest tile
Y0 = Y7 + (T - 1) * DY
TILE_HX = 1.2
TILE_HZ = 2.5
TILE_TH = 0.6
PIL_HX = 1.0
PIL_HZ = 2.1

TRAY_WALL = 0.5
TRAY_IN_X = (42.3, 50.3)
TRAY_IN_Z = (-6.6, 6.6)
TRAY_FLOOR = 0.6
TRAY_TOP = 2.25

BPM = float(os.environ.get("MARBLE_BPM", "120.0"))
TAU = 60.0 / BPM
HOP_APEX = 1.4

OID_FLOOR = 0
OID_TILE0 = 1           # 1..32
OID_PILLAR0 = 40
OID_TRAY = 60
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


def _rainbow(u, s=0.80, v=0.96):
    r, g, b = colorsys.hsv_to_rgb(u % 1.0, s, v)
    return (r * 255, g * 255, b * 255)


# back lane runs red -> violet, front lane starts half way round the color wheel
TILE_SRGB = [_rainbow(0.0 + 0.82 * i / (T - 1)) for i in range(T)] + [_rainbow(0.5 + 0.82 * i / (T - 1)) for i in
                                                                         range(T)]
TILE_LIN = [srgb2lin(c) for c in TILE_SRGB]


def tile_pos(k):
    lane, i = divmod(k, T)
    return i * DX, Y0 - i * DY, LANE_Z[lane]


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

    for k in range(NT):
        x, y, zc = tile_pos(k)
        i = k % T
        box((x - TILE_HX, y - TILE_TH, zc - TILE_HZ), (x + TILE_HX, y, zc + TILE_HZ), TILE_LIN[k], 1.0, 0.22,
            OID_TILE0 + k)
        box((x - PIL_HX, 0.0, zc - PIL_HZ), (x + PIL_HX, y - TILE_TH + 0.02, zc + PIL_HZ), DARK_LIN, 0.5, 0.45,
            OID_PILLAR0 + i)
    x0, x1 = TRAY_IN_X
    z0, z1 = TRAY_IN_Z
    w = TRAY_WALL
    box((x0 - w, 0.0, z0 - w), (x1 + w, TRAY_FLOOR, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x0 - w, 0.0, z0 - w), (x0, TRAY_TOP, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x1, 0.0, z0 - w), (x1 + w, TRAY_TOP, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x0, 0.0, z0 - w), (x1, TRAY_TOP, z0), DARK_LIN, 0.5, 0.45, OID_TRAY)
    box((x0, 0.0, z1), (x1, TRAY_TOP, z1 + w), DARK_LIN, 0.5, 0.45, OID_TRAY)
    return out


def write_scene(path, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        look.write_boxes(f, boxes())


if os.environ.get("MARBLE_CAM") == "wide":
    CAM_FOVY = math.radians(float(os.environ.get("WIDE_FOVY", "30")))
    CAM_AZ = math.radians(float(os.environ.get("WIDE_AZ", "24")))
    CAM_EL = math.radians(float(os.environ.get("WIDE_EL", "15")))
    CAM_DIST = float(os.environ.get("WIDE_DIST", "82"))
    CAM_TARGET = np.array([float(v) for v in os.environ.get("WIDE_TARGET", "24.5,12.6,0.0").split(",")])
elif os.environ.get("MARBLE_CAM") == "widethumb":
    CAM_FOVY = math.radians(float(os.environ.get("WIDE_FOVY", "30")))
    CAM_AZ = math.radians(float(os.environ.get("WIDE_AZ", "28")))
    CAM_EL = math.radians(float(os.environ.get("WIDE_EL", "13")))
    CAM_DIST = float(os.environ.get("WIDE_DIST", "62"))
    CAM_TARGET = np.array([float(v) for v in os.environ.get("WIDE_TARGET", "22.0,13.0,0.0").split(",")])
