import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's09'; N = 85
C = nest_scene.NEST_C
sc, F, N_, ch = nest_setup(sun_elev=30, sun_rot=sun_from_cam((0.07, 0.15), (0, -0.35), -30))
lz = N_['lining_z']
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((C.x, C.y, lz - 0.004), yaw=180)
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
    call = 0.0
    for c0 in (0.4, 0.75, 1.1, 1.9, 2.2):
        if c0 < t < c0 + 0.25:
            call = 34 * math.sin(math.pi * (t - c0) / 0.25)
    up = ease(t / 0.4)
    hd = (lerp(0, -16, up) + 4 * math.sin(t * 9) * (call > 0), 8 * wob(t, 4, 0.4), 5 * wob(t, 5, 0.3))
    fl = 25 * max(0, math.sin(t * 2 * math.pi * 5)) if 1.0 < t < 1.5 else 0
    rots = anim.chick_rots(t, head=hd, jaw=call * 1.15, wings=(fl, fl), body=(lerp(0, -8, up), 0, 0), seed=4)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, lerp(-0.006, 0.01, up))), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 0.0)
cam = blib.camera('cam', (0.07, 0.15, lz + 0.13), (0, -0.22, lz + 0.36), lens=40, fstop=4.0, focus=0.42)
add_fill((0.3, 0.5, lz + 0.2), (0, -0.2, lz + 0.3), power=8)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], lz, margin_px=40, spp=4)
