"""Camera, light and look of the marble run, in the form ../marble-raytrace-kit/compositor.py reads (a scene module).

A bright room instead of the kit's dark studio: a light gray wall, a pale wood floor, soft daylight from the upper
left. The values live in settings.py. (Copied from ../marble-run-picture/scene.py.)
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


def write_scene(path, meshpath, w, h, ns, na):
    pos, fwd, right, up = camera()
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
        f.write(f"mesh {meshpath}\n")


if __name__ == "__main__":
    import layout as LY
    x0, x1, z0, z1 = C.MAT
    for name, p in {"mat_back_left": (x0, 0, z0), "mat_back_right": (x1, 0, z0), "mat_front_left": (x0, 0, z1),
                    "mat_front_right": (x1, 0, z1), "base_top": (0, 12.8, LY.BASE[1]), "found_row": (0, 1, LY.FOUND_Z),
                    "pen": (LY.PEN[0], 0, LY.PEN[1]), "tunnel": (LY.TUNNEL[0], 0, LY.TUNNEL[1])}.items():
        x, y, z = project(p)
        print(f"{name:20s} ({x / W:.3f}, {y / H:.3f})")
