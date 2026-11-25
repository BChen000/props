import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's18'; N = 266
SUBJ = Vector((0.3, -0.5, 0))
CAM = (2.45, -2.25)
sc, F, N_, _ = nest_setup(sun_elev=24, sun_rot=sun_from_cam(CAM, SUBJ.xy, -30), chick=False, shells=False)
L = N_['ledge']
g = Griffin('juv', variant='juvenile', scale=0.8)
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
M0 = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.015), yaw=0)
feet0 = ledge_feet(g, M0, L, scale=0.8)
bouts = [(-0.3, 3.9, 0.12), (5.2, 8.9, 0.28)]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    flap = 0.0; hop = 0.0
    for a, b, h in bouts:
        if a <= t <= b:
            flap = min(1.0, (t - a) / 0.3, (b - t) / 0.3)
            mid = (a + b) / 2
            hop = h * max(0.0, 1 - ((t - mid) / ((b - a) * 0.28)) ** 2)
    base = anim.perch_rots(t, wing_spread=0.0, wing_raise=9.0, head=(-6 + 8 * flap, 10 * wob(t, 3, 0.3), 0), seed=5, fold=0.66)
    rots, fold, bob = ground_flap_rots(t, base, period=0.55, amp=46, glide=0.0, dihedral=14)
    for side in ('L', 'R'):
        for k in ('w_hum_', 'w_fore_', 'w_hand_'):
            a_ = base[k + side]; b_ = rots[k + side]
            rots[k + side] = tuple(x + (y - x) * flap for x, y in zip(a_, b_))
    restfold = 0.66
    M = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.015 + hop + bob * 0.8 * flap), yaw=0)
    key_object(g.arm, f, M)
    feet = {k: v + Vector((0, 0, max(0.0, hop - 0.03))) for k, v in feet0.items()}
    anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0, 0)), feet=feet, legs=anim.ADULT_LEGS)
    fl = {k: v * flap + restfold * (1 - flap) for k, v in fold.items()}
    g.key_feathers(f, fl)
    g.key_toes(f, 0.4)
    g.key_lids(f, 1.0 if abs(t - 4.8) < 0.06 else 0.0)
cam = blib.camera('cam', (CAM[0], CAM[1], gz + 1.15), (SUBJ.x - 0.05, SUBJ.y, gz + 1.05), lens=22, fstop=8.0)
add_fill((3.5, -3.5, 2.0), (SUBJ.x, SUBJ.y, 0.9), power=80, size=3)
sc.frame_set(1)
run(NAME, N, F, cam, dyn('juv_'), F['to_sun'], gz, margin_px=40, spp=3)
