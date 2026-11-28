"""lowpoly-gl demo: a faceted sphere, boxes, a soft-shadowed spot light, a rim light, an emissive screen, a light beam and
a glow, finished by the post pass. No Blender needed.

  python3 demo.py                 -> out/demo.png (540x960)
  RES=1080x1920 python3 demo.py   -> full size
"""
import math
import os
import time

import numpy as np
from PIL import Image

import meshkit as mk
from meshkit import box, plane, uvsphere, jitter, add
from glr import Renderer, T, S, R3, euler
import post

HERE = os.path.dirname(os.path.abspath(__file__))
RES = tuple(int(v) for v in os.environ.get('RES', '540x960').split('x'))
OUT = os.environ.get('LPGL_OUT', os.path.join(HERE, 'out'))


def scene():
    mk.PARTS.clear()
    add('floor', box(6, 6, 0.02, (0, 0, -0.01)), (0.05, 0.035, 0.025))
    add('wall', plane(6, 3, (0, 1.2, 1.5)), (0.035, 0.04, 0.045))
    add('ball', jitter(uvsphere(14, 9, 0.35), 0.012, 1).moved((0, 0, 0.36)), (0.42, 0.42, 0.44))
    add('crate', box(0.4, 0.4, 0.4, (-0.62, 0.35, 0.2)), (0.25, 0.12, 0.05))
    add('screen', plane(0.5, 0.32, (0.62, 0.6, 0.75)), (1, 1, 1))
    add('beam', mk.M(*_cone()), (1, 1, 1))
    add('quad', plane(1, 1), (1, 1, 1))
    return {k: v for k, v in mk.PARTS.items()}


def _cone(n=24):
    v, f, uv = [], [], []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        v += [(0, 0, 0), (math.cos(a), math.sin(a), -1.0)]
    for k in range(n):
        f.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2)); uv.append([(0, 0), (0, 1), (1, 1), (1, 0)])
    return np.array(v, float), f, uv


def main():
    os.makedirs(OUT, exist_ok=True)
    r = Renderer(*RES)
    r.add_meshes(scene())
    y, x = np.mgrid[0:160, 0:256]
    r.add_texture('scr', np.dstack([(40 + 60 * (x // 32 % 2)) * np.ones_like(x), 180 + 0 * x, 160 + 60 * (y // 20 % 2)]).astype(np.uint8))
    lamp = np.array([0.1, -0.3, 2.3])
    lights = [dict(type='spot', pos=tuple(lamp), dir=(0, 0.25, -1), col=(1.0, 0.78, 0.5), energy=2.2, outer=40, inner=20,
                   shadow=True, range=8, soft=3, sh_fov=90),
              dict(type='spot', pos=(-0.8, 0.9, 1.6), dir=(0.8, -0.9, -1.2), col=(0.3, 0.5, 1.0), energy=1.5, outer=30, range=5, spec=2),
              dict(type='point', pos=(0.62, 0.2, 0.75), col=(0.3, 0.9, 0.8), energy=0.08, range=2)]
    env = dict(amb_top=(0.012, 0.014, 0.02), amb_bot=(0.003, 0.003, 0.004), fog_col=(0.005, 0.006, 0.01), fog_d=0.05)
    cam = dict(eye=(0.25, -2.6, 1.15), target=(0, 0.2, 0.6), fov=44)
    items = [('floor', np.eye(4), dict(spec=0.2)), ('wall', np.eye(4), {}), ('ball', np.eye(4), dict(spec=0.15)),
             ('crate', np.eye(4), {}), ('screen', np.eye(4), dict(tex='scr', tmode=2, temit=0.8, cast=False))]
    adds = [('beam', T(lamp) @ R3(euler(-0.24, 0, 0)) @ S((1.0, 1.0, 2.3)), dict(amode=0, col=(1, 0.78, 0.5), int=0.06)),
            ('quad', T(lamp) @ R3(euler(0, 0, 0.1)) @ S(0.4), dict(amode=1, col=(1, 0.75, 0.45), int=1.2))]
    t0 = time.time()
    img = r.render(items, cam, lights, env, adds)
    t1 = time.time()
    out = post.finish(img, dict(dof=3, focus=2.7, exposure=1.1, vignette=0.5, grain=0.02, bloom=0.4))
    t2 = time.time()
    Image.fromarray(out).save(os.path.join(OUT, 'demo.png'))
    print(f'{RES[0]}x{RES[1]}: render {t1 - t0:.2f} s, post {t2 - t1:.2f} s -> {os.path.join(OUT, "demo.png")}')


if __name__ == '__main__':
    main()
