"""Builds the hooded man (needs bpy) and renders his gestures on a contact sheet with ../../shared/lowpoly-gl.

  python3 pose_sheet.py              -> out/man.npz, out/pose_sheet.png
  python3 pose_sheet.py --preview    -> also redraws preview.png (720x1280)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'shared', 'lowpoly-gl'))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw

import meshkit as mk
from meshkit import box, plane, add
from glr import Renderer
import post
import man
from poses import G

OUT = os.environ.get('HM_OUT', os.path.join(HERE, 'out'))
POSES = ['rest', 'explain_R', 'present_R', 'finger_up_R', 'shrug', 'hand_chest_R', 'think', 'temple_R', 'clasp']
TILE = (240, 426)


def build():
    import bpy
    import build_man
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mk.PARTS.clear()
    build_man.build()
    os.makedirs(OUT, exist_ok=True)
    n = mk.save(os.path.join(OUT, 'man.npz'))
    print(len(n), 'parts,', sum(n.values()), 'triangles')
    return mk.load(os.path.join(OUT, 'man.npz'))


def sheet(parts, preview=False):
    mk.PARTS.clear()
    add('wall', plane(6, 4, (0, 1.2, 2)), (0.05, 0.055, 0.06))
    add('floor', box(6, 6, 0.02, (0, 0, -0.01)), (0.04, 0.035, 0.03))
    parts = dict(parts); parts.update(mk.PARTS)
    r = Renderer(540, 960); r.add_meshes(parts)

    def spot(pos, target, **k):
        return dict(type='spot', pos=pos, dir=tuple(np.subtract(target, pos)), **k)
    lights = [spot((0.35, -1.6, 2.35), (0, 0, 1.55), col=(1.0, 0.80, 0.58), energy=2.4, outer=26, inner=12, shadow=True,
                   range=12, soft=3, sh_fov=40),
              dict(type='point', pos=(0.0, -2.0, 1.4), col=(0.85, 0.9, 1.0), energy=0.3, range=8, spec=0.3),
              spot((-0.75, 0.75, 2.1), (0, 0, 1.55), col=(0.35, 0.6, 1.0), energy=1.4, outer=30, inner=15, range=6, spec=2),
              spot((0.8, 0.8, 2.0), (0, 0, 1.5), col=(0.35, 0.6, 1.0), energy=1.1, outer=30, inner=15, range=6, spec=2)]
    env = dict(amb_top=(0.02, 0.025, 0.035), amb_bot=(0.004, 0.004, 0.006), fog_col=(0.004, 0.005, 0.008), fog_d=0.02)
    cam = dict(eye=(0.25, -2.1, 1.45), target=(0, 0, 1.35), fov=36)
    W = Image.new('RGB', (TILE[0] * 3, TILE[1] * 3), (14, 14, 18))
    for i, nm in enumerate(POSES):
        pose = man.merge(man.REST, G[nm])
        items = man.items(pose) + [('wall', np.eye(4), {}), ('floor', np.eye(4), {})]
        out = post.finish(r.render(items, cam, lights, env), dict(vignette=0.4, grain=0.0))
        im = Image.fromarray(out).resize(TILE, Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 8), nm, fill=(255, 220, 60))
        W.paste(im, ((i % 3) * TILE[0], (i // 3) * TILE[1]))
    W.save(os.path.join(OUT, 'pose_sheet.png'))
    if preview:
        W.save(os.path.join(HERE, 'preview.png'), optimize=True)
    print('wrote', os.path.join(OUT, 'pose_sheet.png'))


if __name__ == '__main__':
    sheet(build(), '--preview' in sys.argv)
