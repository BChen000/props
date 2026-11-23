"""Rigid-body simulation of marbles dropped on the xylophone ramp (Blender / Bullet).

Run:  python3 sim.py CFG.json OUT.npz            (bpy module)
  or: blender --background --python sim.py -- CFG.json OUT.npz
CFG.json comes from rounds.py, melody.py or calibrate.py. OUT.npz holds
pos (frames x marbles x 3, meters), quat, and t (seconds, video time) at 240 Hz.
Each marble waits off-scene, appears just above the frame, and is released at its time t.
"""
import os, sys, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
cfg = json.load(open(argv[0]))
out = argv[1]
S = WORLD_SCALE
PRE = cfg.get('preroll', PREROLL)
DUR = cfg['duration']
NFR = int((PRE + DUR) * SIM_HZ) + 1
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = SIM_HZ
sc.frame_start = 1
sc.frame_end = NFR
sc.gravity = (0, 0, -9.81 * S)
col = sc.collection


def add_rb(ob, typ, shape, fric, rest, mass=1.0, lin=0.0, ang=0.0, margin=0.002):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.rigidbody.object_add(type=typ)
    rb = ob.rigid_body
    rb.collision_shape = shape
    rb.friction = fric
    rb.restitution = rest
    rb.mass = mass
    rb.linear_damping = lin
    rb.angular_damping = ang
    rb.use_margin = True
    rb.collision_margin = margin
    rb.use_deactivation = False
    return rb


def mesh_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def box_obj(name, center, dims, rot=(0, 0, 0)):
    hx, hy, hz = dims[0] / 2, dims[1] / 2, dims[2] / 2
    v = [(sx * hx, sy * hy, sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    ob = mesh_obj(name, v, f)
    ob.location = tuple(center)
    ob.rotation_euler = rot
    return ob


bpy.ops.rigidbody.world_add()
rbw = sc.rigidbody_world
rbw.substeps_per_frame = cfg.get('substeps', SUBSTEPS)
rbw.solver_iterations = cfg.get('iters', SOLVER_ITERS)
rbw.point_cache.frame_start = 1
rbw.point_cache.frame_end = NFR

P = cfg['phys']
for k in range(NB):
    c = (bar_top_center(k) - N * BAR_T / 2) * S
    ob = box_obj(f'bar{k}', c, (bar_len(k) * S, BAR_W * S, BAR_T * S), (THETA, 0, 0))
    add_rb(ob, 'PASSIVE', 'BOX', P['bar_fric'], P['bar_rest'])

zb = scene_meta()['box_top']
ob = box_obj('stand', (np.array([0, (BOX['y0'] + BOX['y1']) / 2, zb / 2])) * S, ((BOX['x1'] - BOX['x0']) * S, (BOX['y1'] - BOX['y0']) * S, zb * S))
add_rb(ob, 'PASSIVE', 'BOX', 0.5, 0.3)
ob = box_obj('table', np.array([0, 0, -0.05]) * S, (4 * S, 4 * S, 0.1 * S))
add_rb(ob, 'PASSIVE', 'BOX', 0.6, 0.2)

bt = np.load(BASKET_TUBE)
ob = mesh_obj('basket', bt['V'] * S, [tuple(f) for f in bt['F']])
add_rb(ob, 'PASSIVE', 'MESH', P['bask_fric'], P['bask_rest'], margin=0.001)
disk_v = [(BASKET_C[0] * S, BASKET_C[1] * S, 0.004 * S)] + [((BASKET_C[0] + 0.15 * math.cos(a)) * S, (BASKET_C[1] + 0.15 * math.sin(a)) * S, 0.004 * S) for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
disk_f = [(0, i, i % 64 + 1) for i in range(1, 65)]
ob = mesh_obj('bdisk', disk_v, disk_f)
add_rb(ob, 'PASSIVE', 'MESH', P['bask_fric'], P['bask_rest'], margin=0.001)

for g in cfg.get('guards', []):
    if g.get('kind') == 'ring':
        r0, z0, z1 = g['r'], g['z0'], g['z1']
        vv, ff = [], []
        nseg = 72
        for i in range(nseg):
            a = 2 * math.pi * i / nseg
            for z in (z0, z1):
                vv.append(((BASKET_C[0] + r0 * math.cos(a)) * S, (BASKET_C[1] + r0 * math.sin(a)) * S, z * S))
        for i in range(nseg):
            i2 = (i + 1) % nseg
            ff.append((2 * i, 2 * i2, 2 * i2 + 1, 2 * i + 1))
        ob = mesh_obj(g['name'], vv, ff)
        add_rb(ob, 'PASSIVE', 'MESH', 0.3, 0.2, margin=0.001)
        continue
    ob = box_obj(g['name'], (0, 0, 0), np.array(g['dims']) * S)
    M = Matrix.Identity(4)
    B = np.array(g['basis'])
    for r in range(3):
        for c in range(3):
            M[r][c] = B[r][c]
    M.translation = Vector(np.array(g['center']) * S)
    ob.matrix_world = M
    add_rb(ob, 'PASSIVE', 'BOX', 0.3, 0.2)

marbles = []
for i, mb in enumerate(cfg['marbles']):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=MARBLE_R * S, segments=12, ring_count=6, location=tuple(np.array(mb['pos']) * S))
    ob = bpy.context.active_object
    ob.name = f'm{i:03d}'
    rb = add_rb(ob, 'ACTIVE', 'SPHERE', P['m_fric'], P['m_rest'], mass=1.0, lin=P['lin'], ang=P['ang'], margin=0.0)
    f_rel = max(8, int(round((mb['t'] + PRE) * SIM_HZ)) + 1)
    spawn_loc = ob.location.copy()
    park = (3.0 * S + 0.05 * S * i, 3.0 * S, 2.0 * S)
    rb.kinematic = True
    rb.keyframe_insert('kinematic', frame=1)
    rb.keyframe_insert('kinematic', frame=f_rel - 1)
    rb.kinematic = False
    rb.keyframe_insert('kinematic', frame=f_rel)
    ob.location = park
    ob.keyframe_insert('location', frame=1)
    ob.keyframe_insert('location', frame=f_rel - 5)
    ob.location = spawn_loc
    ob.keyframe_insert('location', frame=f_rel - 4)
    ob.keyframe_insert('rotation_euler', frame=1)
    marbles.append(ob)

nm = len(marbles)
pos = np.zeros((NFR, nm, 3), np.float32)
quat = np.zeros((NFR, nm, 4), np.float32)
t0 = time.time()
for f in range(1, NFR + 1):
    sc.frame_set(f)
    for i, ob in enumerate(marbles):
        mw = ob.matrix_world
        pos[f - 1, i] = np.array(mw.translation) / S
        quat[f - 1, i] = np.array(mw.to_quaternion())
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
np.savez_compressed(out, pos=pos, quat=quat, t=(np.arange(NFR) / SIM_HZ - PRE).astype(np.float32))
print('saved', out, nm, 'marbles', NFR, 'frames', '%.1fs' % (time.time() - t0))
