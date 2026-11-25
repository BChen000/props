"""cliff-nest-set / demo.py: the griffin nest set in one Cycles pass (far scenery and near set together).

  python3 demo.py nest     out/nest.png    behind the nest, over the ledge to the cloud sea and the peaks (the s13 view)
  python3 demo.py cliff    out/cliff.png   out over the drop, along the cliff to the ledge and nest (the s22 view)
  python3 demo.py both     both, then out/sheet.png side by side

Blender 5.3 as a Python module (bpy 5.3.0), Cycles CPU. blib.py comes from ../griffin.
"""
import os, sys, math, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, '..', 'griffin')):
    sys.path.insert(0, p)

# ---------------------------------------------------------------- settings (shipped values; env overrides)
SETTINGS = dict(
    RES=os.environ.get('RES', '360x640'),
    SPP=int(os.environ.get('SPP', '16')),
    OUT=os.environ.get('OUT', os.path.join(HERE, 'out')),
    SUN_STRENGTH=float(os.environ.get('SUN_STRENGTH', '3.8')),
    SKY_STRENGTH=float(os.environ.get('SKY_STRENGTH', '0.22')),
    SHELLS=int(os.environ.get('SHELLS', '1')),          # broken eggshell halves in the nest
)
SUN_COL = (1.0, 0.78, 0.55)
VIEWS = {
    # sun elevation, sun rotation (deg), camera location, look-at, lens (mm), drop face on/off; z is relative to the nest lining
    'nest': dict(sun_elev=25.0, sun_rot=80.0, cam=(0.55, 0.05, 1.45), look=(-0.1, -3.2, -1.35), lens=18, drop=True),
    'cliff': dict(sun_elev=24.0, sun_rot=None, cam=(2.75, -1.65, 0.85), look=(-0.1, -1.55, 0.35), lens=22, drop=False),
}
# ----------------------------------------------------------------

import bpy
from mathutils import Vector
import blib, env, far, nest_scene


def sun_from_cam(cam_loc, subj, side=35.0):
    """sun rotation that lights the subject from `side` degrees off the camera direction"""
    d = Vector(cam_loc) - Vector(subj)
    return math.degrees(math.atan2(d.x, -d.y)) + side


def place_shells(N, lz):
    """four broken shell pieces resting on the nest lining (as in the episode's nest_common.nest_setup)"""
    sh = env.egg_shell_pieces('shell', (0, 0, 0), size=0.085, n=4, seed=5)
    spots = [(0.19, 0.10, 2.6, 0.3, 0.2), (-0.18, 0.15, 0.4, 2.8, 1.0), (0.13, -0.19, 3.0, 0.9, 2.0), (-0.20, -0.06, 0.6, 0.2, 2.6)]
    C = nest_scene.NEST_C
    for o, (dx, dy, rx, ry, rz) in zip(sh, spots):
        o.rotation_euler = (rx, ry, rz)
        bpy.context.view_layer.update()
        W = [o.matrix_world @ v.co for v in o.data.vertices]
        cx = sum(w.x for w in W) / len(W); cy = sum(w.y for w in W) / len(W); zmin = min(w.z for w in W)
        px, py = C.x + dx, C.y + dy
        hz = max(nest_scene.height_at(N['lining'], px + ox, py + oy) or lz for ox in (-0.03, 0, 0.03) for oy in (-0.03, 0, 0.03))
        o.location = (px - cx, py - cy, hz + 0.006 - zmin)
    return sh


def render(view):
    V = VIEWS[view]
    sc = blib.reset()
    rot = V['sun_rot'] if V['sun_rot'] is not None else sun_from_cam(V['cam'][:2], (0.0, -0.82), -40)
    far.build_far(sun_elev=V['sun_elev'], sun_rot=rot, sun_strength=SETTINGS['SUN_STRENGTH'],
                  sky_strength=SETTINGS['SKY_STRENGTH'], clouds=True, sun_color=SUN_COL)
    N = nest_scene.build(wide=True, drop=V['drop'])
    lz = nest_scene.height_at(N['lining'], nest_scene.NEST_C.x, nest_scene.NEST_C.y)
    if SETTINGS['SHELLS']:
        place_shells(N, lz)
    cx, cy, cz = V['cam']; lx, ly, lzz = V['look']
    blib.camera('cam', (cx, cy, lz + cz), (lx, ly, lz + lzz), lens=V['lens'], fstop=11.0, clip_end=80000)
    rx, ry = [int(x) for x in SETTINGS['RES'].split('x')]
    blib.render_settings(res=(rx, ry), spp=SETTINGS['SPP'])
    os.makedirs(SETTINGS['OUT'], exist_ok=True)
    sc.render.filepath = os.path.join(SETTINGS['OUT'], view + '.png')
    bpy.ops.render.render(write_still=True)
    print('wrote', sc.render.filepath, flush=True)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if what == 'both':
        for v in ('nest', 'cliff'):
            subprocess.run([sys.executable, os.path.abspath(__file__), v], check=True)
        from PIL import Image
        a, b = [Image.open(os.path.join(SETTINGS['OUT'], v + '.png')).convert('RGB') for v in ('nest', 'cliff')]
        out = Image.new('RGB', (a.width + b.width, a.height)); out.paste(a, (0, 0)); out.paste(b, (a.width, 0))
        out.save(os.path.join(SETTINGS['OUT'], 'sheet.png')); print('wrote', os.path.join(SETTINGS['OUT'], 'sheet.png'))
    else:
        render(what)
