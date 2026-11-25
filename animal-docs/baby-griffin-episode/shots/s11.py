import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
import props
NAME = 's11'; N = 147
C = nest_scene.NEST_C
CAM = (0.24, 0.22)
import nest_common
sc, F, N_, ch = nest_setup(sun_elev=32, sun_rot=sun_from_cam(CAM, (0, -0.2), 30))
lz = N_['lining_z']
for o in N_['shells']:
    if (o.location - Vector((C.x, C.y, o.location.z))).length < 0.3 and o.location.y > C.y - 0.05:
        o.location.x += 0.12 * (1 if o.location.x > 0 else -1)
mt = props.meat(size=0.12)
mt.rotation_euler = (0.1, 0.05, 0.6)
tugs = [(0.3, 1.25), (1.7, 2.6), (3.0, 4.1), (4.6, 5.7)]
grab = []
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((C.x, C.y - 0.07, lz - 0.004), yaw=180)
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
    hp, jaw, pull, shake, holding = 8, 10, 0.0, 0.0, False
    for a, b in tugs:
        if a <= t <= b:
            u = (t - a) / (b - a)
            if u < 0.3:
                hp = lerp(8, 50, ease(u / 0.3)); jaw = lerp(10, 28, ease(u / 0.3))
            elif u < 0.45:
                hp = 50; jaw = lerp(28, 2, ease((u - 0.3) / 0.15)); holding = u > 0.38
            else:
                v = (u - 0.45) / 0.55
                hp = lerp(50, 14, ease(v)); jaw = 2 if v < 0.8 else lerp(2, 10, (v - 0.8) / 0.2)
                pull = math.sin(math.pi * min(1, v * 1.3)) if v < 0.77 else 0.0
                holding = v < 0.62
                shake = 14 * math.sin(v * 40) * (1 - v)
    grab.append(holding)
    rots = anim.chick_rots(t, head=(hp, 4 * wob(t, 7, 0.3), shake), jaw=jaw, body=(hp * 0.25, 0, 0), tail=(0, 10 * math.sin(t * 3)), seed=5)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, -0.006 - 0.02 * pull)), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 1.0 if abs(t - 2.9) < 0.06 else 0.0)
tip_i = len(ch.beak.data.vertices) - 2
tips = []
for f in range(1, N + 1):
    sc.frame_set(f)
    tips.append((ch.beak.matrix_world @ ch.beak.data.vertices[tip_i].co).copy())
low = min(range(N), key=lambda i: tips[i].z)
p0 = tips[low].copy()
mt.location = (0, 0, 0)
bpy.context.view_layer.update()
zs = [(mt.matrix_world @ v.co) for v in mt.data.vertices]
top = max(zs, key=lambda v: v.z)
base = Vector((p0.x - top.x, p0.y - top.y + 0.01, p0.z - top.z - 0.004))
anchor = None
for f in range(1, N + 1):
    i = f - 1
    if grab[i]:
        if anchor is None:
            anchor = tips[i].copy()
        d = (tips[i] - anchor) * 0.7
        d.z = max(0.0, d.z)
    else:
        anchor = None
        d = Vector((0, 0, 0))
    mt.location = base + d
    mt.rotation_euler = (0.1 - 2.0 * d.z, 0.05, 0.6)
    mt.keyframe_insert('location', frame=f); mt.keyframe_insert('rotation_euler', frame=f)
cam = blib.camera('cam', (0.30, 0.36, lz + 0.42), (0.0, -0.10, lz + 0.13), lens=48, fstop=4.0)
add_fill((0.7, 0.4, lz + 0.5), (0, -0.1, lz + 0.1), power=8)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch) + [mt], F['to_sun'], lz, margin_px=40, spp=4)
