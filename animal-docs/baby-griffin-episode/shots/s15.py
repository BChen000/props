import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's15'; N = 121
SUBJ = Vector((0.55, -0.92, 0))
CAM = (1.25, -1.55)
sc, F, N_, ch = nest_setup(sun_elev=32, sun_rot=sun_from_cam(CAM, SUBJ.xy, -25), hair_children=2)
L = N_['ledge']
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
hops = [(0.55, 0.30, 0.38, 0.05), (2.0, 0.32, 0.42, 0.07)]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    jump = 0.0; crouch = 0.0; flap = 0.0; tip = 0.0
    for i, (t0, cd, air, h) in enumerate(hops):
        if t0 - 0.35 < t < t0 + cd + air + 0.6:
            flap = 52
        if t0 < t < t0 + cd:
            crouch = math.sin(math.pi * (t - t0) / cd) * 0.9
        if t0 + cd <= t < t0 + cd + air:
            u = (t - t0 - cd) / air
            jump = h * 4 * u * (1 - u)
        if t0 + cd + air <= t < t0 + cd + air + 0.3:
            crouch = math.sin(math.pi * (t - t0 - cd - air) / 0.3) * (0.7 if i == 0 else 1.0)
    if t > 2.0 + 0.32 + 0.42:
        tip = ease((t - 2.74) / 0.35)
    fl = flap * (0.5 + 0.5 * math.sin(t * 2 * math.pi * 6.5)) if flap else 0.0
    M = obj_matrix((SUBJ.x, SUBJ.y, gz + jump), yaw=-55, roll=22 * tip)
    key_object(ch.arm, f, M)
    if f == 1:
        M0 = obj_matrix((SUBJ.x, SUBJ.y, gz), yaw=-55)
        feet0 = anim.rest_feet_world(ch.rig, M0, anim.CHICK_LEGS)
        for k in feet0:
            feet0[k].z = nest_scene.height_at(L, feet0[k].x, feet0[k].y) + 0.012
    feet = {k: v + Vector((0, 0, jump)) for k, v in feet0.items()}
    if tip > 0:
        feet['fl'] = feet['fl'] + Vector((0.02, -0.03, 0)) * tip
    rots = anim.chick_rots(t, head=(-10 + 25 * crouch - 15 * tip, 12 * wob(t, 2, 0.5), 15 * tip), wings=(fl, fl * 0.9 + 20 * tip),
                           body=(18 * crouch, 0, 0), tail=(-10 + 20 * crouch, 12 * math.sin(t * 5)), seed=9)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, -0.03 * crouch - 0.05 * tip)), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 1.0 if abs(t - 2.9) < 0.1 else 0.0)
cam = blib.camera('cam', (CAM[0], CAM[1], gz + 0.24), (SUBJ.x, SUBJ.y, gz + 0.14), lens=55, fstop=4.5)
add_fill((1.4, -1.9, gz + 0.6), (SUBJ.x, SUBJ.y, gz + 0.15), power=10)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], gz, margin_px=40)
