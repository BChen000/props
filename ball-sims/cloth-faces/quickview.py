"""Preview strip of one sim (Workbench is fast; Cycles shows the look).
Run:  python3 quickview.py -- build/sims/stage5.npz 5 20,30,40,60 build/q5.png WB"""
import sys, time, math
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import bpy
import scene as S

args = sys.argv[sys.argv.index('--') + 1:]
npz, stage, frames, out = args[0], int(args[1]), [int(x) for x in args[2].split(',')], args[3]
eng = args[4] if len(args) > 4 else 'CYCLES'
d = np.load(npz)
pos, faces, uv = d['pos'], d['faces'], d['uv']
sc = S.reset()
S.build_set()
S.add_camera()
S.add_lights()
mats = S.stage_materials()
S.build_stack(mats, first=stage + 1)
st = S.STAGES[stage]
ob = S.mesh_obj('Sheet', pos[0], faces, smooth=st['n'] >= 64)
S.set_uv(ob.data, uv)
ob.data.materials.append(mats[stage])
S.setup_cycles(sc, 270, 480, spp=8)
if eng == 'WB':
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
from PIL import Image
tiles = []
for fr in frames:
    ob.data.vertices.foreach_set('co', pos[min(fr, len(pos) - 1)].ravel())
    ob.data.update()
    sc.render.filepath = f'/tmp/qv_{fr}.png'
    bpy.ops.render.render(write_still=True)
    im = Image.open(sc.render.filepath).convert('RGBA')
    bg = Image.new('RGBA', im.size, (125, 175, 235, 255))
    bg.alpha_composite(im)
    tiles.append(bg.convert('RGB'))
W = 270
sheet = Image.new('RGB', (W * len(tiles), 480))
for i, t in enumerate(tiles):
    sheet.paste(t, (i * W, 0))
sheet.save(out)
print("done", out)
