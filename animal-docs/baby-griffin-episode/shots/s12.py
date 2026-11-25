import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's12'; N = 106
SUBJ = Vector((0.35, -1.11, 0))
CAM2 = (0.78, -1.55)
sc, F, N_, ch = nest_setup(sun_elev=30, sun_rot=sun_from_cam(CAM2, SUBJ.xy, 30))
gz = nest_scene.height_at(N_['ledge'], SUBJ.x, SUBJ.y)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((SUBJ.x, SUBJ.y, gz), yaw=0)
    key_object(ch.arm, f, M)
    if f == 1:
        feet = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
        for k in feet:
            feet[k].z = nest_scene.height_at(N_['ledge'], feet[k].x, feet[k].y) + 0.014
    sway = 4 * math.sin(t * 1.6)
    rots = anim.chick_rots(t, head=(25 + 5 * wob(t, 9, 0.3), 10 * wob(t, 8, 0.25), 0), body=(6, 0, sway), seed=6)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0.006 * math.sin(t * 1.6), 0, -0.004)), feet=feet, legs=anim.CHICK_LEGS)
    curl = 0.05 + 0.42 * ease((t - 0.6) / 1.6) - 0.12 * ease((t - 2.8) / 0.5) + 0.15 * ease((t - 3.4) / 0.4)
    ch.key_toes(f, {'L': curl, 'R': curl * 0.9})
    ch.key_lids(f, 0.0)
foot = anim.bone_tail_rest(ch.rig, 'f_low_L')
fw = obj_matrix((SUBJ.x, SUBJ.y, gz), yaw=0) @ foot
cam = blib.camera('cam', (fw.x + 0.20, fw.y - 0.26, gz + 0.06), (fw.x - 0.03, fw.y - 0.01, gz + 0.03), lens=70, fstop=4.0)
add_fill((0.9, -1.9, gz + 0.3), (fw.x, fw.y, gz), power=6)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], gz, margin_px=40, step=2)
