"""Geometry, camera and light of the balance set, as a box scene for ../marble-raytrace-kit (boxtrace and the
compositor's marble lighting) and for the physics in sim.py.

The set: a light wall and a wooden floor; a seesaw (beam, a blue basket on the left, a wooden one on the right) on
a stand with a pivot pin and a stop post under each end; a nearly flat shelf that brings the glass marbles in from
the left, and a three-plank zigzag that brings the steel balls down on the right. The beam and baskets turn about
the z axis through PIVOT by the beam angle theta; everything else is fixed. Box conventions follow boxtrace: a box
with rot = 0 is in world coordinates, otherwise its min/max are in its own frame around its pivot.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import look

import settings as C

W, H, FPS, R = C.W, C.H, C.FPS, C.R
LIGHT_ANG = C.LIGHT_ANG
LIGHT_COL = np.array(C.LIGHT_COL, float)
SKY_Z = np.array(C.SKY_Z, float)
SKY_H = np.array(C.SKY_H, float)
EXPOSURE = C.EXPOSURE
CAM_FOVY = C.CAM_FOVY
CAM_SHIFT = C.CAM_SHIFT
CAM_TARGET = np.array(C.CAM_TARGET, float)
srgb2lin = look.srgb2lin
FLOOR_LIN = srgb2lin(C.FLOOR_SRGB)
PIVOT = np.array(C.PIVOT, float)

OID_FLOOR, OID_WALL, OID_STAND, OID_PIN, OID_GLASS_TRACK, OID_STEEL_TRACK = 0, 1, 2, 3, 4, 5
OID_BEAM, OID_LEFT_BASKET, OID_RIGHT_BASKET = 10, 11, 12
MOVING = (OID_BEAM, OID_LEFT_BASKET, OID_RIGHT_BASKET)
WOODY = (OID_FLOOR, OID_STAND, OID_GLASS_TRACK, OID_STEEL_TRACK, OID_BEAM, OID_RIGHT_BASKET)
PLANK_T = 0.7


def camera():
    return look.camera_from(CAM_TARGET, C.CAM_AZ, C.CAM_EL, C.CAM_DIST)


def light_dir():
    d = np.array(C.LIGHT_FROM, float)
    return d / np.linalg.norm(d)


def vignette(sx, sy):
    dx = sx - 0.5
    dy = (sy - 0.5) * (H / W) * 0.62
    return 1.0 - C.VIG * (dx * dx + dy * dy) * 2.2


def tonemap(lin):
    x = np.maximum(lin, 0) * EXPOSURE
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    y = np.clip(y, 0, 1)
    return np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(y, 1 / 2.4) - 0.055)


def project(p, w=W, h=H):
    return look.project_with(camera(), CAM_FOVY, CAM_SHIFT, p, w, h)


# ------------------------------------------------------------------------------------------------ geometry
def _box(out, mn, mx, srgb, oid, rot=0.0, piv=(0.0, 0.0, 0.0), gloss=0.0, rough=0.5, part=""):
    out.append(dict(mn=[float(v) for v in mn], mx=[float(v) for v in mx], alb=list(map(float, srgb2lin(srgb))),
                    gloss=float(gloss), rough=float(rough), oid=int(oid), rot=float(rot),
                    piv=[float(v) for v in piv], part=part))


def plank(out, left, right, srgb, oid, hz=C.TRACK_HZ, rail_h=C.RAIL_H, part=""):
    """A plank whose top surface runs from left (x, y) to right (x, y), with a rail on each side."""
    (x0, y0), (x1, y1) = left, right
    rot = math.atan2(y1 - y0, x1 - x0)
    ln = math.hypot(x1 - x0, y1 - y0)
    piv = (x0, y0, 0.0)
    _box(out, (0, -PLANK_T, -hz - 0.4), (ln, 0, hz + 0.4), srgb, oid, rot, piv, part=part)
    _box(out, (0, -PLANK_T, hz), (ln, rail_h, hz + 0.4), srgb, oid, rot, piv, part=part + "rail")
    _box(out, (0, -PLANK_T, -hz - 0.4), (ln, rail_h, -hz), srgb, oid, rot, piv, part=part + "rail")


def static_boxes():
    out = []
    _box(out, (-400, 0, -40), (400, 300, -9.0), C.WALL_SRGB, OID_WALL, part="wall")
    px, py = PIVOT[0], PIVOT[1]
    st = C.STAND_SRGB
    # stand: base, post, two braces, bearing plates either side of the beam, and the stop posts
    _box(out, (px - 7.0, 0, -3.6), (px + 7.0, 0.9, 3.6), st, OID_STAND, part="base")
    _box(out, (px - 0.9, 0.9, -1.0), (px + 0.9, py - 1.25, 1.0), st, OID_STAND, part="post")
    for s in (-1, 1):
        _box(out, (-0.35, 0, -0.6), (0.35, 9.6, 0.6), st, OID_STAND, rot=s * math.radians(31.0),
             piv=(px + s * 4.6, 0.9, 0.0), part="brace")
    for z0, z1 in ((C.BEAM_HZ + 0.05, C.BEAM_HZ + 0.75), (-C.BEAM_HZ - 0.75, -C.BEAM_HZ - 0.05)):
        _box(out, (px - 1.1, py - 3.2, z0), (px + 1.1, py + 1.1, z1), st, OID_STAND, part="plate")
    _box(out, (px - 0.42, py - 0.42, -C.BEAM_HZ - 1.15), (px + 0.42, py + 0.42, C.BEAM_HZ + 1.15), C.PIN_SRGB,
         OID_PIN, gloss=0.3, rough=0.35, part="pin")
    for s in (-1, 1):
        x, ytop = stop_post_top(s)
        _box(out, (x - 0.65, 0, -0.65), (x + 0.65, ytop, 0.65), st, OID_STAND, part="stop")
        _box(out, (x - 1.6, 0, -1.6), (x + 1.6, 0.5, 1.6), st, OID_STAND, part="stopfoot")
    # glass shelf on the left, with a post under it
    plank(out, C.GLASS_RAMP[0], C.GLASS_RAMP[1], C.WOOD_SRGB, OID_GLASS_TRACK, part="glass")
    xg = C.GLASS_RAMP[1][0] - 3.0
    _box(out, (xg - 0.5, 0, -0.5), (xg + 0.5, track_y(C.GLASS_RAMP, xg) - PLANK_T, 0.5), C.STAND_SRGB,
         OID_GLASS_TRACK, part="post")
    # steel zigzag on the right: planks, end stops, and posts down to the floor
    for a, b in C.STEEL_ZIG:
        plank(out, a, b, C.WOOD_SRGB, OID_STEEL_TRACK, part="steel")
    for x0, x1, y0, y1 in C.STEEL_WALLS:
        _box(out, (x0, y0, -C.TRACK_HZ - 0.4), (x1, y1, C.TRACK_HZ + 0.4), C.WOOD_SRGB, OID_STEEL_TRACK, part="stopwall")
    # the zigzag hangs on the wall: a bracket under each end of each plank
    for a, b in C.STEEL_ZIG:
        for (x, y) in (a, b):
            x = min(max(x, a[0] + 1.2), b[0] - 1.2)
            yb = track_y((a, b), x) - PLANK_T
            _box(out, (x - 0.35, yb - 1.6, -9.0), (x + 0.35, yb, -C.TRACK_HZ - 0.4), C.STAND_SRGB, OID_STEEL_TRACK,
                 part="bracket")
    return out


def track_y(seg, x):
    (x0, y0), (x1, y1) = seg
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def stop_post_top(s):
    """x and top height of the stop post under side s (-1 left, +1 right): the beam's underside rests on it at
    THETA_MAX."""
    th = C.THETA_MAX
    xl = 0.86 * C.BEAM_HALF
    c, sn = math.cos(th), math.sin(th)
    x = PIVOT[0] + s * xl * c + (-0.5 * C.BEAM_T) * sn * s
    y = PIVOT[1] - xl * sn - 0.5 * C.BEAM_T * c
    return x, y


def beam_local_boxes(physics=False):
    """The beam and both baskets, in the beam frame (origin at the pivot), level. For the physics the low front walls
    go up to full height, like a clear front pane, so a tall pile can't spill out toward the camera."""
    out = []
    bt, bz = C.BEAM_T, C.BEAM_HZ
    _box(out, (-C.BEAM_HALF, -0.5 * bt, -bz), (C.BEAM_HALF, 0.5 * bt, bz), C.WOOD_SRGB, OID_BEAM, part="beam")
    hx, hz, w = C.BASKET_HX, C.BASKET_HZ, C.BASKET_WALL
    y0 = 0.5 * bt
    for s, srgb, oid in ((-1, C.LEFT_BASKET_SRGB, OID_LEFT_BASKET), (1, C.RIGHT_BASKET_SRGB, OID_RIGHT_BASKET)):
        cx = s * C.ARM
        yf = y0 + w
        _box(out, (cx - hx - w, y0, -hz - w), (cx + hx + w, yf, hz + w), srgb, oid, part="floor")
        _box(out, (cx - hx - w, yf, -hz - w), (cx - hx, yf + C.BASKET_H, hz + w), srgb, oid, part="side")
        _box(out, (cx + hx, yf, -hz - w), (cx + hx + w, yf + C.BASKET_H, hz + w), srgb, oid, part="side")
        _box(out, (cx - hx, yf, -hz - w), (cx + hx, yf + C.BASKET_H, -hz), srgb, oid, part="back")
        fh = C.BASKET_H if physics else C.BASKET_FRONT_H
        _box(out, (cx - hx, yf, hz), (cx + hx, yf + fh, hz + w), srgb, oid, part="front")
    return out


def basket_floor_y():
    """Top of the basket floors in the beam frame."""
    return 0.5 * C.BEAM_T + C.BASKET_WALL


def beam_boxes(theta):
    """The beam assembly turned by theta about the pivot, in boxtrace's convention."""
    out = []
    for b in beam_local_boxes():
        b = dict(b)
        if theta == 0.0:
            b["mn"] = [b["mn"][k] + PIVOT[k] for k in range(3)]
            b["mx"] = [b["mx"][k] + PIVOT[k] for k in range(3)]
            b["rot"], b["piv"] = 0.0, [0.0, 0.0, 0.0]
        else:
            b["rot"], b["piv"] = float(theta), list(map(float, PIVOT))
        out.append(b)
    return out


def boxes(theta=0.0):
    return static_boxes() + beam_boxes(theta)


def write_scene(path, w, h, ns, na, theta=0.0, crop=None):
    cam = camera()
    pos, fwd, right, up = cam
    L = light_dir()
    wall = srgb2lin(C.WALL_SRGB)
    with open(path, "w") as f:
        f.write(f"res {w} {h}\n")
        f.write("cam " + " ".join(f"{v:.9g}" for v in [*pos, *fwd, *right, *up, math.tan(CAM_FOVY / 2),
                                                        CAM_SHIFT[0], CAM_SHIFT[1]]) + "\n")
        f.write("light " + " ".join(f"{v:.9g}" for v in [*L, LIGHT_ANG, *LIGHT_COL]) + "\n")
        f.write("sky " + " ".join(f"{v:.9g}" for v in [*SKY_Z, *SKY_H]) + "\n")
        f.write("floor " + " ".join(f"{v:.9g}" for v in FLOOR_LIN) + "\n")
        f.write(f"fog {C.FOG_START} {C.FOG_DIST}\n")
        f.write("bg " + " ".join(f"{v:.9g}" for v in [*wall, *wall, 0, 0, 0, 0.5, 0.5, 0.5, C.VIG, EXPOSURE]) + "\n")
        f.write(f"samples {ns} {na}\n")
        if crop is not None:
            f.write("crop " + " ".join(str(int(v)) for v in crop) + "\n")
        look.write_boxes(f, boxes(theta))


if __name__ == "__main__":
    for name, p in {"pivot": PIVOT, "left basket": (-C.ARM, PIVOT[1] + 3, 0), "right basket": (C.ARM, PIVOT[1] + 3, 0),
                    "glass lip": (*C.GLASS_RAMP[1], 0), "zig top": (*C.STEEL_ZIG[0][1], 0), "floor front": (0, 0, 9)}.items():
        x, y, _ = project(np.array(p, float))
        print(f"{name:14s} ({x / W:.3f}, {y / H:.3f})")
    print(len(boxes()), "boxes")
