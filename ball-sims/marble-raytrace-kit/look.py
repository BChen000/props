"""The shared studio look of the 3D marble music Shorts: blue-gray cyclorama, soft key light, ACES tone curve.

Scene modules (one per template) do `from look import *`, set their own camera and geometry, and call the helpers
below with their own camera values. Every value here is the one the shipped videos used.
"""
import math
import os
import numpy as np

# ===================================================================== SETTINGS (shipped values)
W, H = (int(v) for v in os.environ.get("MARBLE_RES", "1080x1920").split("x"))   # MARBLE_RES=1920x1080: landscape
FPS = 30
R = 1.0
LIGHT_ANG = math.radians(11.0)
LIGHT_COL = np.array([2.35, 2.25, 2.10])
SKY_Z = np.array([0.30, 0.37, 0.50])
SKY_H = np.array([0.36, 0.42, 0.52])
EXPOSURE = 0.80
BG_TOP = np.array([0.080, 0.100, 0.140])
BG_BOT = np.array([0.205, 0.272, 0.385])
BG_GLOW = np.array([0.36, 0.62, 1.75])
BG_GLOW_POS = (0.98, -0.02)
BG_GLOW_RAD = 0.62
VIG = 0.16
FLOOR_LIN = np.array([0.235, 0.30, 0.405])
# ================================================================= END SETTINGS


def srgb2lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


DARK_LIN = srgb2lin((50, 54, 60))


def camera_from(target, az, el, dist):
    pos = target + dist * np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
    fwd = target - pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return pos, fwd, right, up


def light_dir_for(cam):
    pos, fwd, right, up = cam
    toward_cam = -np.array([fwd[0], 0.0, fwd[2]])
    toward_cam /= np.linalg.norm(toward_cam)
    rh = np.array([right[0], 0.0, right[2]])
    rh /= np.linalg.norm(rh)
    d = 0.62 * rh + 0.30 * toward_cam + np.array([0.0, 1.05, 0.0])
    return d / np.linalg.norm(d)


def background(sx, sy):
    t = np.clip(sy, 0, 1)
    t = t * t * (3 - 2 * t)
    base = BG_TOP[None] * (1 - t[..., None]) + BG_BOT[None] * t[..., None]
    dx = sx - BG_GLOW_POS[0]
    dy = (sy - BG_GLOW_POS[1]) * (H / W)
    g = np.exp(-(dx * dx + dy * dy) / (BG_GLOW_RAD ** 2))
    return base + BG_GLOW[None] * g[..., None]


def vignette(sx, sy):
    dx = sx - 0.5
    dy = (sy - 0.5) * (H / W) * 0.62
    return 1.0 - VIG * (dx * dx + dy * dy) * 2.2


def tonemap(lin):
    x = np.maximum(lin, 0) * EXPOSURE
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    y = np.clip(y, 0, 1)
    return np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(y, 1 / 2.4) - 0.055)


def project_with(cam, fovy, shift, p, w=W, h=H):
    pos, fwd, right, up = cam
    d = np.asarray(p, dtype=np.float64) - pos
    zc = d @ fwd
    th = math.tan(fovy / 2)
    nx = (d @ right) / (zc * th * (w / h)) - shift[0]
    ny = (d @ up) / (zc * th) - shift[1]
    return (nx + 1) * 0.5 * w, (1 - ny) * 0.5 * h, zc


def write_scene_header(f, cam, fovy, shift, w, h, ns, na, fog_start, fog_dist):
    pos, fwd, right, up = cam
    L = light_dir_for(cam)
    f.write(f"res {w} {h}\n")
    f.write("cam " + " ".join(f"{v:.9g}" for v in [*pos, *fwd, *right, *up, math.tan(fovy / 2), shift[0],
                                                    shift[1]]) + "\n")
    f.write("light " + " ".join(f"{v:.9g}" for v in [*L, LIGHT_ANG, *LIGHT_COL]) + "\n")
    f.write("sky " + " ".join(f"{v:.9g}" for v in [*SKY_Z, *SKY_H]) + "\n")
    f.write("floor " + " ".join(f"{v:.9g}" for v in FLOOR_LIN) + "\n")
    f.write(f"fog {fog_start} {fog_dist}\n")
    f.write("bg " + " ".join(f"{v:.9g}" for v in [*BG_TOP, *BG_BOT, *BG_GLOW, *BG_GLOW_POS, BG_GLOW_RAD, VIG,
                                                   EXPOSURE]) + "\n")
    f.write(f"samples {ns} {na}\n")


def write_boxes(f, boxes):
    for b in boxes:
        f.write("box " + " ".join(f"{v:.9g}" for v in [*b["mn"], *b["mx"], b["rot"], *b["piv"], *b["alb"],
                                                        b["gloss"], b["rough"], b["oid"]]) + "\n")
