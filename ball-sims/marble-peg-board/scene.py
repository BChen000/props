"""The peg board as boxes for the kit's boxtrace: back board, side rails, brass diamond pegs, bin walls and floor,
hopper and plinth; and the camera, which frames the whole board."""
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

OID_BOARD, OID_RAIL, OID_BASE, OID_HOPPER, OID_WALL, OID_FLOOR_BIN, OID_PEG0 = 1, 2, 3, 4, 5, 6, 10

HALF = C.BINS * C.DX / 2                                  # inner faces of the side rails at +-(HALF - WALL_T/2)
BIN_X = [(k - (C.BINS - 1) / 2) * C.DX for k in range(C.BINS)]
WALL_X = [(k - C.BINS / 2) * C.DX for k in range(C.BINS + 1)]
BIN_TOP = C.BIN_FLOOR_Y + C.BIN_H
ROW_Y = [BIN_TOP + C.GAP_PEGS_BINS + (C.ROWS - 1 - r) * C.DY for r in range(C.ROWS)]
MOUTH_Y = ROW_Y[0] + C.HOPPER_GAP                         # marbles appear at the hopper's bottom face
TOP_Y = MOUTH_Y + C.HOPPER_H + 1.5


def pegs():
    """(x, y, row) of every peg. Rows alternate pegs at the bin centres (without the outermost two, so a marble can't
    wedge against a rail) and pegs in line with the bin walls; the lowest row is in line with the walls, so marbles
    leave the pegs over the middle of a bin."""
    out = []
    for r, y in enumerate(ROW_Y):
        if (C.ROWS - 1 - r) % 2 == 0:
            xs = WALL_X[1:-1]
        else:
            xs = BIN_X[1:-1]
        out += [(x, y, r) for x in xs]
    return out


PEGS = pegs()
PEG_LIN = srgb2lin(C.PEG_SRGB)
PEG_GLOW_LIN = srgb2lin(C.PEG_GLOW_SRGB)

FOG_START, FOG_DIST = C.FOG_START, C.FOG_DIST
CAM_FOVY = C.CAM_FOVY
CAM_SHIFT = C.CAM_SHIFT
CAM_AZ, CAM_EL = C.CAM_AZ, C.CAM_EL
CAM_TARGET = np.array([0.0, TOP_Y / 2 - 0.9, C.Z_MARBLE])
CAM_DIST = (TOP_Y / 2 * C.FRAME_PAD) / math.tan(CAM_FOVY / 2) + C.PEG_DEPTH


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

    d = C.PEG_DEPTH
    t = C.WALL_T
    xo = HALF + t / 2
    bm = C.BOARD_MARGIN
    box((-xo - bm, 0.0, -C.BOARD_T), (xo + bm, TOP_Y + bm, 0.0), C.BOARD_SRGB, 0.12, 0.55, OID_BOARD)
    box((-xo - bm - 1.5, 0.0, -C.BOARD_T - 1.6), (xo + bm + 1.5, C.BIN_FLOOR_Y - 1.0, d + 1.6), C.BASE_SRGB, 0.2,
        0.5, OID_BASE)
    for sx in (-1, 1):
        box((min(sx * xo, sx * (xo - t)), C.BIN_FLOOR_Y - 1.0, 0.0), (max(sx * xo, sx * (xo - t)), TOP_Y, d),
            C.RAIL_SRGB, 0.18, 0.5, OID_RAIL)
    box((-xo, C.BIN_FLOOR_Y - 1.0, 0.0), (xo, C.BIN_FLOOR_Y, d), C.RAIL_SRGB, 0.18, 0.5, OID_FLOOR_BIN)
    for x in WALL_X[1:-1]:
        box((x - t / 2, C.BIN_FLOOR_Y, 0.0), (x + t / 2, BIN_TOP, d), C.RAIL_SRGB, 0.18, 0.5, OID_WALL)
    hw = C.HOPPER_W / 2
    box((-hw, MOUTH_Y, 0.0), (hw, MOUTH_Y + C.HOPPER_H, d + 0.4), C.RAIL_SRGB, 0.18, 0.5, OID_HOPPER)
    box((-xo, TOP_Y - 0.8, 0.0), (xo, TOP_Y, d), C.RAIL_SRGB, 0.18, 0.5, OID_RAIL)
    a = C.PEG_HALF
    for i, (x, y, _) in enumerate(PEGS):
        box((-a, -a, 0.0), (a, a, d), C.PEG_SRGB, 0.85, 0.25, OID_PEG0 + i, math.pi / 4, (x, y, 0.0))
    assert len(out) <= 128, len(out)
    return out


def write_scene(path, w, h, ns, na):
    with open(path, "w") as f:
        look.write_scene_header(f, camera(), CAM_FOVY, CAM_SHIFT, w, h, ns, na, FOG_START, FOG_DIST)
        look.write_boxes(f, boxes())


if __name__ == "__main__":
    print("pegs", len(PEGS), "boxes", len(boxes()), "rows y", [round(y, 1) for y in ROW_Y], "mouth", MOUTH_Y,
          "top", TOP_Y, "cam dist", round(CAM_DIST, 1))
    for name, p in {"top_left": (-HALF, TOP_Y, 0), "bottom_right": (HALF, 0, 0), "bin1_bottom": (BIN_X[0], C.BIN_FLOOR_Y, 1)}.items():
        x, y, _ = project(p)
        print(f"{name:14s} ({x / W:.3f}, {y / H:.3f})")
