import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's13'; N = 85
C = nest_scene.NEST_C
CAMP = (0.55, 0.05)
sc, F, N_, ch = nest_setup(sun_elev=25, sun_rot=80, wide=True)
lz = N_['lining_z']
hk = [(0.0, (-6, -8, 0)), (0.9, (-14, 32, 3)), (2.0, (-9, -28, -4)), (2.9, (-16, 6, 0))]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((C.x, C.y, lz - 0.004), yaw=-25)
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
    hd = anim.saccade_track(t, hk)
    fl = 18 * max(0, math.sin((t - 1.4) * 2 * math.pi * 4.5)) if 1.4 < t < 1.85 else 0
    rots = anim.chick_rots(t, head=hd, wings=(fl, fl), body=(-4, 0.25 * hd[1], 0), seed=13)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, -0.004)), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 0.0)
cam = blib.camera('cam', (CAMP[0], CAMP[1], lz + 1.45), (-0.1, -3.2, lz - 1.35), lens=18, fstop=11.0)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], lz, margin_px=40, spp=4)
