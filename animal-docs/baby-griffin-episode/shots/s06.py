import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's06'; N = 154
CAM = (0.26, 0.58, 0.56)
sc, F, N_, ch = nest_setup(sun_elev=30, sun_rot=sun_from_cam(CAM, (0, -0.35, 0), 40))
lz = N_['lining_z']
C = nest_scene.NEST_C
look_keys = [(0, (35, 0, 0)), (1.9, (-8, 10, 0)), (2.6, (-5, 38, 8)), (3.4, (0, -30, -6)), (4.2, (-12, 5, 10)), (5.4, (-12, 5, 10))]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    rise = ease((t - 0.7) / 1.3)
    M = obj_matrix((C.x, C.y, lz - 0.004), yaw=180 + 8 * wob(t, 5, 0.1))
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
    hd = anim.saccade_track(t, look_keys) if t > 1.9 else (lerp(35, -8, ease((t - 0.6) / 1.3)), lerp(0, 10, ease((t - 0.6) / 1.3)), 0)
    fl = 30 * max(0, math.sin((t - 3.0) * 2 * math.pi * 3)) if 3.0 < t < 3.66 else 0.0
    jaw = 20 * math.sin(math.pi * (t - 1.95) / 0.3) if 1.95 < t < 2.25 else 0.0
    rots = anim.chick_rots(t, head=hd, jaw=jaw, wings=(fl, fl), body=(lerp(28, 0, rise), 0, 0), tail=(lerp(-20, 10, rise), 0), seed=1)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, lerp(-0.075, -0.008, rise))), feet=feet, legs=anim.CHICK_LEGS)
    blink = 1.0 if (abs(t - 2.35) < 0.07 or abs(t - 4.5) < 0.07) else 0.0
    ch.key_lids(f, max(blink, lerp(0.5, 0.0, ease(t / 1.2))))
cam = blib.camera('cam', CAM, (0, -0.36, 0.14), lens=42, fstop=5.6, focus=0.98)
add_fill((0.8, 1.6, 0.9), (0, -0.35, 0.15), power=18)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], lz)
