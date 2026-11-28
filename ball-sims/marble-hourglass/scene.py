"""The marble hourglass as boxes for the kit's boxtrace: a dark walnut board, a pale maple frame, four slanted rails
that narrow to the neck and open out again, a floor and a plinth; and the camera, which frames the whole board.
`walls()` gives the same rails as oriented rectangles for the physics."""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import look
from look import (FPS, R, LIGHT_ANG, LIGHT_COL, SKY_Z, SKY_H, EXPOSURE, FLOOR_LIN, srgb2lin, vignette, tonemap)
import settings as C

W, H = C.W, C.H
OID_BOARD, OID_FRAME, OID_RAIL, OID_BASE, OID_FLOOR = 1, 2, 3, 4, 5

XO = C.HALF_W + C.RAIL_T / 2            # centre line of the side rails
BOARD_TOP = C.TOP_Y + C.RAIL_T


def slanted(a, b):
    """A rail whose inner face runs from a to b (inner side on the left when walking from a to b): centre, half
    length, half thickness, angle."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    ln = float(np.hypot(*d))
    u = d / ln
    n_out = np.array([u[1], -u[0]])                      # right-hand normal points out of the hourglass
    c = (a + b) / 2 + n_out * C.RAIL_T / 2
    return c, ln / 2 + C.RAIL_T * 0.6, C.RAIL_T / 2, math.atan2(d[1], d[0])


def rails():
    hw, nh = C.HALF_W, C.NECK_HALF
    return [slanted((-hw, C.FUNNEL_TOP_Y), (-nh, C.NECK_Y)),          # top left: inner side faces right/up
            slanted((nh, C.NECK_Y), (hw, C.FUNNEL_TOP_Y)),
            slanted((-nh, C.NECK_Y), (-hw, C.FUNNEL_BOT_Y)),
            slanted((hw, C.FUNNEL_BOT_Y), (nh, C.NECK_Y))]


def walls():
    """Oriented rectangles (cx, cy, half_x, half_y, angle) for the physics: the four slanted rails, the side rails,
    the top rail and the floor."""
    out = [(c[0], c[1], hl, ht, ang) for c, hl, ht, ang in rails()]
    t = C.RAIL_T
    span = (BOARD_TOP - (C.FLOOR_Y - 1.0)) / 2
    mid = (BOARD_TOP + C.FLOOR_Y - 1.0) / 2
    out.append((-XO, mid, t / 2, span, 0.0))
    out.append((XO, mid, t / 2, span, 0.0))
    out.append((0.0, C.TOP_Y + t / 2, XO, t / 2, 0.0))
    out.append((0.0, C.FLOOR_Y - 0.5, XO, 0.5, 0.0))
    return np.array(out, np.float64)


FOG_START, FOG_DIST = C.FOG_START, C.FOG_DIST
CAM_FOVY, CAM_SHIFT, CAM_AZ, CAM_EL = C.CAM_FOVY, C.CAM_SHIFT, C.CAM_AZ, C.CAM_EL
CAM_TARGET = np.array([0.0, BOARD_TOP / 2 - 0.6, C.Z_MARBLE])
CAM_DIST = (BOARD_TOP / 2 * C.FRAME_PAD) / math.tan(CAM_FOVY / 2) + C.DEPTH


def camera():
    return look.camera_from(CAM_TARGET, CAM_AZ, CAM_EL, CAM_DIST)


def light_dir():
    return look.light_dir_for(camera())


def project(p, w=None, h=None):
    return look.project_with(camera(), CAM_FOVY, CAM_SHIFT, p, w or W, h or H)


def boxes():
    out = []

    def box(mn, mx, srgb, gloss, rough, oid, rot=0.0, piv=(0.0, 0.0, 0.0)):
        out.append(dict(mn=list(map(float, mn)), mx=list(map(float, mx)), alb=list(map(float, srgb2lin(srgb))),
                        gloss=float(gloss), rough=float(rough), oid=int(oid), rot=float(rot),
                        piv=list(map(float, piv))))

    d, t, bm = C.DEPTH, C.RAIL_T, C.BOARD_MARGIN
    box((-XO - t / 2 - bm, 0.0, -C.BOARD_T), (XO + t / 2 + bm, BOARD_TOP + bm, 0.0), C.BOARD_SRGB, 0.12, 0.55,
        OID_BOARD)
    box((-XO - t / 2 - bm - 1.5, 0.0, -C.BOARD_T - 1.6), (XO + t / 2 + bm + 1.5, C.FLOOR_Y - 1.0, d + 1.6),
        C.BASE_SRGB, 0.2, 0.5, OID_BASE)
    for sx in (-1, 1):
        box((sx * XO - t / 2, C.FLOOR_Y - 1.0, 0.0), (sx * XO + t / 2, BOARD_TOP, d), C.RAIL_SRGB, 0.18, 0.5,
            OID_FRAME)
    box((-XO, C.TOP_Y, 0.0), (XO, BOARD_TOP, d), C.RAIL_SRGB, 0.18, 0.5, OID_FRAME)
    box((-XO, C.FLOOR_Y - 1.0, 0.0), (XO, C.FLOOR_Y, d), C.RAIL_SRGB, 0.18, 0.5, OID_FLOOR)
    for c, hl, ht, ang in rails():
        box((-hl, -ht, 0.0), (hl, ht, d), C.RAIL_SRGB, 0.18, 0.5, OID_RAIL, ang, (c[0], c[1], 0.0))
    return out


def write_scene(path, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        look.write_boxes(f, boxes())


if __name__ == "__main__":
    print("boxes", len(boxes()), "walls", len(walls()), "cam dist", round(CAM_DIST, 1))
    for name, p in {"top_left": (-XO, BOARD_TOP, 0), "bottom_right": (XO, 0, 0), "neck": (0, C.NECK_Y, 1)}.items():
        x, y, _ = project(p)
        print(f"{name:14s} ({x / W:.3f}, {y / H:.3f})")
