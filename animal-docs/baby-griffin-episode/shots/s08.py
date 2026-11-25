import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's08'; N = 92
SUBJ = Vector((0.62, -0.34, 0))
CAM2 = (1.55, -0.62)
sc, F, N_, ch = nest_setup(sun_elev=32, sun_rot=sun_from_cam(CAM2, SUBJ.xy, 25))
gz = nest_scene.height_at(N_['ledge'], SUBJ.x, SUBJ.y)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((SUBJ.x, SUBJ.y, gz + 0.004), yaw=-8)
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
        for k in feet:
            feet[k].z = nest_scene.height_at(N_['ledge'], feet[k].x, feet[k].y) + 0.012
    flap = 0.0
    if 1.2 < t < 2.7:
        e = math.sin(math.pi * (t - 1.2) / 1.5)
        flap = 42 * e * (0.5 + 0.5 * math.sin((t - 1.2) * 2 * math.pi * 4.5))
    hd = anim.saccade_track(t, [(0, (0, 10, 0)), (0.6, (-8, -18, 0)), (1.2, (-12, 0, 0)), (2.9, (5, 25, 10)), (3.4, (5, -25, -10)), (3.8, (0, 8, 0)), (4.5, (0, 8, 0))])
    bounce = 0.012 * abs(math.sin((t - 1.2) * 2 * math.pi * 2.2)) if 1.2 < t < 2.7 else 0.0
    rots = anim.chick_rots(t, head=hd, wings=(flap, flap), tail=(10, 25 * math.sin(t * 2.2)), seed=3)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, bounce)), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 1.0 if abs(t - 0.9) < 0.07 or abs(t - 3.9) < 0.07 else 0.0)
cam = blib.camera('cam', (CAM2[0], CAM2[1], gz + 0.30), (SUBJ.x + 0.0, SUBJ.y + 0.03, gz + 0.12), lens=46, fstop=4.0)
add_fill((1.6, -1.2, gz + 0.6), SUBJ + Vector((0, 0, gz + 0.15)), power=10)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], gz, margin_px=36)
