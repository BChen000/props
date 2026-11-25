"""One Blender cloth sim. Writes build/sims/stageN.npz (pos [frames, verts, 3], faces, uv) and build/sims/hero_pts.npy.
Run:  HERO=duck python3 sim.py -- --stage 6 --frames 230 --dx 0.03 --fric 0.25
Test drape:  python3 sim.py -- --stage 5 --n 50 --frames 150 --out build/t50.npz"""
import os, sys, time, math, argparse, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import scene as S

ap = argparse.ArgumentParser()
ap.add_argument('--stage', type=int, required=True)
ap.add_argument('--n', type=int, default=0)
ap.add_argument('--frames', type=int, default=120)
ap.add_argument('--dx', type=float, default=0.0)
ap.add_argument('--dy', type=float, default=0.0)
ap.add_argument('--rot', type=float, default=0.0)
ap.add_argument('--tilt', type=float, default=0.0)
ap.add_argument('--quality', type=int, default=6)
ap.add_argument('--cq', type=int, default=3)
ap.add_argument('--mass', type=float, default=0.3)
ap.add_argument('--tension', type=float, default=15.0)
ap.add_argument('--shear', type=float, default=5.0)
ap.add_argument('--bend', type=float, default=0.5)
ap.add_argument('--air', type=float, default=1.0)
ap.add_argument('--fric', type=float, default=0.6)
ap.add_argument('--self', type=int, default=0)
ap.add_argument('--dist', type=float, default=0.012)
ap.add_argument('--out', default='')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

sc = S.reset()
st = S.STAGES[a.stage]
n = a.n or st['n']
plat, shaft, hero = S.build_set(with_materials=False)
hero = [o for o in hero if not o.name.startswith('HeroEye')]
for ob in list(bpy.data.objects):
    if ob.name.startswith('Vane') or ob.name.startswith('HeroEye'):
        bpy.data.objects.remove(ob)
bpy.context.view_layer.update()
hp = []
for o in hero:
    mw = np.array(o.matrix_world)
    vv = np.array([v.co for v in o.data.vertices])
    hp.append(vv @ mw[:3, :3].T + mw[:3, 3])
os.makedirs(S.CFG.SIMS, exist_ok=True)
np.save(os.path.join(S.CFG.SIMS, 'hero_pts.npy'), np.vstack(hp).astype(np.float32))
for ob, fr in [(plat, 5.0), (shaft, 5.0)] + [(o, a.fric) for o in hero]:
    md = ob.modifiers.new('Collision', 'COLLISION')
    ob.collision.thickness_outer = 0.006
    ob.collision.thickness_inner = 0.05
    ob.collision.cloth_friction = fr
    ob.collision.use_culling = True
    ob.collision.use_normal = False

z0 = S.STACK_Z0 + S.STACK_GAP * a.stage
v, f, uv = S.grid(n)
ca, sa = math.cos(math.radians(a.rot)), math.sin(math.radians(a.rot))
x = v[:, 0] * ca - v[:, 1] * sa
y = v[:, 0] * sa + v[:, 1] * ca
z = np.full(len(v), z0) + math.tan(math.radians(a.tilt)) * x
v = np.stack([x + a.dx, y + a.dy, z], 1)
cl = S.mesh_obj('Cloth', v, f)
md = cl.modifiers.new('Cloth', 'CLOTH')
cs = md.settings
cs.quality = a.quality
cs.mass = a.mass
cs.air_damping = a.air
cs.tension_stiffness = a.tension
cs.compression_stiffness = a.tension
cs.shear_stiffness = a.shear
cs.bending_stiffness = a.bend
cs.tension_damping = 5.0
cs.compression_damping = 5.0
cs.shear_damping = 5.0
cs.bending_damping = 0.5
cc = md.collision_settings
cc.collision_quality = a.cq
cc.distance_min = a.dist
cc.use_collision = True
cc.use_self_collision = bool(a.self)
cc.self_distance_min = max(0.002, min(0.006, 0.5 * S.SHEET / n))
cc.self_friction = 3.0
md.point_cache.frame_start = 1
md.point_cache.frame_end = a.frames
sc.frame_start, sc.frame_end = 1, a.frames

nv = len(v)
pos = np.empty((a.frames, nv, 3), np.float32)
buf = np.empty(nv * 3, np.float32)
dg = bpy.context.evaluated_depsgraph_get()
t0 = time.time()
for fr in range(1, a.frames + 1):
    sc.frame_set(fr)
    ev = cl.evaluated_get(dg)
    me = ev.to_mesh()
    me.vertices.foreach_get('co', buf)
    ev.to_mesh_clear()
    pos[fr - 1] = buf.reshape(-1, 3)
    if fr % 10 == 0 or fr == a.frames:
        print(f"frame {fr} {time.time() - t0:.1f}s zmin {pos[fr-1][:,2].min():.3f} zmean {pos[fr-1][:,2].mean():.3f}", flush=True)
out = a.out or os.path.join(S.CFG.SIMS, f'stage{a.stage}.npz')
np.savez(out, pos=pos, faces=f.astype(np.int32), uv=uv.astype(np.float32), n=n, args=json.dumps(vars(a)))
print("saved", out, time.time() - t0)
