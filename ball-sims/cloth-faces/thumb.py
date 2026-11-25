"""No-text thumbnail: full Cycles close-up of the gold stage. Writes build/out/thumb_raw.png.
Run:  HERO=duck python3 thumb.py [-- W H SPP OUT SIM_FRAME LENS TARGET_Z]"""
import sys, math, json
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import bpy
import scene as S
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
C = S.CFG
W = int(args[0]) if len(args) > 0 else C.WIDTH
H = int(args[1]) if len(args) > 1 else C.HEIGHT
spp = int(args[2]) if len(args) > 2 else 48
out = args[3] if len(args) > 3 else C.OUT + '/thumb_raw.png'
simf = float(args[4]) if len(args) > 4 else C.THUMB_SIM_FRAME[C.HERO]
lens = float(args[5]) if len(args) > 5 else C.THUMB_LENS
tz = float(args[6]) if len(args) > 6 else C.THUMB_TARGET_Z[C.HERO]
__import__('os').makedirs(__import__('os').path.dirname(out), exist_ok=True)

sc = S.reset()
plat, shaft, mb = S.build_set()
S.CAM_LENS = lens
S.CAM_TARGET = (0.0, 0.0, tz)
cam = S.add_camera()
S.add_lights()
for ob in (plat, shaft):
    ob['bgmix'] = 0.0
    ob['cheap'] = 0.0
sky = np.load(S.CFG.PLATES + '/sky_lin.npy')
wimg = S.bg_image("BGW", 1080, 1920, world=True)
S.set_bg_pixels(wimg, sky)
S.wrap_with_bg(sc.world.node_tree, True)
mats = S.stage_materials()
stack = S.build_stack(mats)
stack[6].hide_render = True
d = np.load(S.CFG.SIMS + '/stage6.npz')
k0 = int(math.floor(simf)); w = simf - k0
co = d['pos'][k0] * (1 - w) + d['pos'][k0 + 1] * w
cl = S.mesh_obj('Gold', co, d['faces'], smooth=True)
S.set_uv(cl.data, d['uv'])
cl.data.materials.append(mats[6])
md = cl.modifiers.new('Sub', 'SUBSURF')
md.levels = 0
md.render_levels = 2
S.setup_cycles(sc, W, H, spp=spp)
sc.cycles.adaptive_threshold = 0.01
sc.render.film_transparent = False
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('thumb done', out)
