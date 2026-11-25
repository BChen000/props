import sys, json, time
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import bpy
import settings as C
import glass_scene as G
from PIL import Image

args = sys.argv[sys.argv.index('--') + 1:]
stage, frames, out = int(args[0]), [int(x) for x in args[1].split(',')], args[2]
W = int(args[3]) if len(args) > 3 else 270
spp = int(args[4]) if len(args) > 4 else 8
eng = args[5] if len(args) > 5 else 'CYCLES'
d = np.load(f'{C.SIMS}/stage{stage}.npz')
info = json.loads(str(d['shards']))
sc = G.reset()
studio, mats, panes, ball, cam = G.build()
r = float(d['r'])
ball.scale = (r, r, r)
sh = G.Shards(info, mats)
H = int(W * 16 / 9)
G.setup_cycles(sc, W, H, spp)
if eng == 'WB':
    sc.render.engine = 'BLENDER_WORKBENCH'
tiles = []
for f in frames:
    ball.location = tuple(d['ball_pos'][f])
    q = d['ball_quat'][f]
    ball.rotation_mode = 'QUATERNION'
    ball.rotation_quaternion = (q[3], q[0], q[1], q[2])
    for k in range(C.N_P):
        panes[k].hide_render = not bool(d['intact'][f][k])
    sh.pose(d['sh_pos'][f], d['sh_quat'][f], f)
    sc.render.filepath = f'/tmp/gp_{f}.png'
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print('frame', f, round(time.time() - t, 1), flush=True)
    tiles.append(Image.open(sc.render.filepath).convert('RGB'))
sheet = Image.new('RGB', (W * len(tiles), H))
for i, t in enumerate(tiles):
    sheet.paste(t, (i * W, 0))
sheet.save(out)
print('done', out)
