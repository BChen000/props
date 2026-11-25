import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's07'; N = 177
C = nest_scene.NEST_C
CAM = (0.05, 0.24, 0.0)
sc, F, N_, ch = nest_setup(sun_elev=30, sun_rot=sun_from_cam((0.05, 0.24), (0, -0.35), 28))
lz = N_['lining_z']
CAM = (0.05, 0.24, lz + 0.345)
keys = [(0, (0, 0, 0)), (0.7, (-6, 14, 16)), (1.7, (-3, -12, -12)), (2.6, (2, 2, 0)), (3.5, (-9, 9, 20)), (4.4, (-2, -6, -6)), (5.0, (-2, -6, -6))]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((C.x, C.y, lz - 0.004), yaw=180)
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
    hd = anim.saccade_track(t, keys)
    jaw = 16 * math.sin(math.pi * min(1, max(0, (t - 2.15) / 0.35))) if 2.15 < t < 2.5 else 0.0
    rots = anim.chick_rots(t, head=hd, jaw=jaw, seed=2)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, -0.006)), feet=feet, legs=anim.CHICK_LEGS)
    blink = 1.0 if (abs(t - 1.25) < 0.07 or abs(t - 3.15) < 0.07 or abs(t - 4.6) < 0.06) else 0.0
    ch.key_lids(f, blink)
cam = blib.camera('cam', CAM, (0, -0.21, lz + 0.285), lens=66, fstop=2.8, focus=0.45)
add_fill((0.5, 0.6, lz + 0.5), (0, -0.2, lz + 0.3), power=6)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], lz, margin_px=40, step=2)
