"""griffin / demo.py: render the griffin at its three ages on a plain ground under a Cycles sky.

  python3 demo.py adult        out/adult.png     perched, wings folded, 3/4 view
  python3 demo.py juvenile     out/juvenile.png  the same pose, juvenile plumage at 0.8 scale
  python3 demo.py chick        out/chick.png     the downy chick, head turned to camera
  python3 demo.py flight       out/flight.png    the adult in a flight pose (mid downstroke)
  python3 demo.py sheet        all four, then out/sheet.png (2x2 tile, 720x1280 at the default size)

Uses Blender 5.3 as a Python module (pip install bpy==5.3.0), Cycles on the CPU. The first run builds the meshes
into build/ (see blib.ensure_assets), which takes a few minutes; later runs reuse them.
"""
import os, sys, math, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---------------------------------------------------------------- settings (shipped values; env overrides)
SETTINGS = dict(
    RES=os.environ.get('RES', '360x640'),          # per still
    SPP=int(os.environ.get('SPP', '24')),
    OUT=os.environ.get('OUT', os.path.join(HERE, 'out')),
    SUN_ELEV=float(os.environ.get('SUN_ELEV', '28')),
    SUN_ROT=float(os.environ.get('SUN_ROT', '-40')),  # degrees, Blender sky convention (see blib.sky_world)
    EXPOSURE=float(os.environ.get('EXPOSURE', '-0.9')),
    HAIR_PARENTS=int(os.environ.get('HAIR_PARENTS', '2600')),
    HAIR_CHILDREN=int(os.environ.get('HAIR_CHILDREN', '3')),
)
# ----------------------------------------------------------------

import bpy
from mathutils import Vector
import blib, anim
from anim import obj_matrix, key_object


def ground(size=40.0, col=(0.30, 0.27, 0.22)):
    v = [(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)]
    ob = blib.mesh_obj('ground', v, [(0, 1, 2, 3)], smooth=False)
    blib.assign(ob, blib.mat_simple('ground', col, rough=0.9, spec=0.2))
    return ob


def scene():
    sc = blib.reset()
    blib.sky_world(sun_elev=SETTINGS['SUN_ELEV'], sun_rot=SETTINGS['SUN_ROT'], strength=0.22)
    blib.sun_light(SETTINGS['SUN_ELEV'], SETTINGS['SUN_ROT'], strength=3.8, color=(1.0, 0.78, 0.55))
    ground()
    rx, ry = [int(x) for x in SETTINGS['RES'].split('x')]
    blib.render_settings(res=(rx, ry), spp=SETTINGS['SPP'])
    sc.view_settings.exposure = SETTINGS['EXPOSURE']
    sc.frame_start = sc.frame_end = 1
    return sc


def flat_feet(rig, M, legs, lift):
    feet = anim.rest_feet_world(rig, M, legs)
    for k in feet:
        feet[k].z = lift
    return feet


def standing(variant):
    from adult import Griffin
    s = 1.0 if variant == 'adult' else 0.8
    g = Griffin(variant, variant=variant, scale=s)
    M = obj_matrix((0, 0, -0.02 * s), yaw=25)
    key_object(g.arm, 1, M)
    feet = flat_feet(g.rig, M, anim.ADULT_LEGS, 0.06 * s)
    rots = anim.perch_rots(0.0, wing_spread=0.0, wing_raise=9.0, head=(-6, 22, 0), seed=2, fold=0.66)
    anim.pose_creature(g.rig, 1, M, rots, feet=feet, legs=anim.ADULT_LEGS)
    g.key_feathers(1, 0.66)
    g.key_toes(1, 0.35)
    g.key_lids(1, 0.0)
    blib.camera('cam', (2.75 * s, -1.4 * s, 1.0 * s), (0.0, -0.18 * s, 0.9 * s), lens=30, fstop=8.0)


def flight():
    from adult import Griffin
    g = Griffin('adult', variant='adult')
    M = obj_matrix((0, 0, 1.6), yaw=-62, pitch=-4, roll=6)
    key_object(g.arm, 1, M)
    rots, fold, bob = anim.flight_rots(0.42, period=1.1, amp=42, glide=0.0, legs='tuck', head=(0, -10, 0))
    anim.pose_creature(g.rig, 1, M, rots, root_off=Vector((0, 0, bob)))
    g.key_feathers(1, fold)
    g.key_lids(1, 0.0)
    blib.camera('cam', (4.3, -3.2, 1.45), (0.25, 0.0, 1.75), lens=26, fstop=11.0)


def chick():
    from chick import Chick
    ch = Chick(hair=True, hair_parents=SETTINGS['HAIR_PARENTS'], hair_children=SETTINGS['HAIR_CHILDREN'])
    M = obj_matrix((0, 0, 0.004), yaw=22)
    key_object(ch.arm, 1, M)
    feet = flat_feet(ch.rig, M, anim.CHICK_LEGS, 0.012)
    rots = anim.chick_rots(0.0, head=(6, 12, 4), wings=(12, 12), tail=(10, 12), seed=3)
    anim.pose_creature(ch.rig, 1, M, rots, feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(1, 0.0)
    blib.camera('cam', (0.5, -0.78, 0.23), (0.02, 0.0, 0.12), lens=55, fstop=4.0)


def render(name):
    sc = scene()
    {'adult': lambda: standing('adult'), 'juvenile': lambda: standing('juvenile'), 'flight': flight, 'chick': chick}[name]()
    sc.camera = bpy.data.objects['cam']
    sc.frame_set(1)
    os.makedirs(SETTINGS['OUT'], exist_ok=True)
    sc.render.filepath = os.path.join(SETTINGS['OUT'], name + '.png')
    bpy.ops.render.render(write_still=True)
    print('wrote', sc.render.filepath, flush=True)


def sheet():
    for n in ('adult', 'juvenile', 'chick', 'flight'):  # one process each: a fresh scene, and hair memory is freed
        subprocess.run([sys.executable, os.path.abspath(__file__), n], check=True)
    from PIL import Image
    ims = [Image.open(os.path.join(SETTINGS['OUT'], n + '.png')).convert('RGB') for n in ('adult', 'juvenile', 'chick', 'flight')]
    w, h = ims[0].size
    out = Image.new('RGB', (2 * w, 2 * h))
    for i, im in enumerate(ims):
        out.paste(im, ((i % 2) * w, (i // 2) * h))
    p = os.path.join(SETTINGS['OUT'], 'sheet.png')
    out.save(p)
    print('wrote', p)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'sheet'
    sheet() if what == 'sheet' else render(what)
