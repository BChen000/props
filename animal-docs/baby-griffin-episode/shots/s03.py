import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's03'; N = 110
SUBJ = Vector((0.15, -0.55, 0))
CAM = (3.55, -1.55)
sc, F, N_, _ = nest_setup(sun_elev=24, sun_rot=sun_from_cam(CAM, SUBJ.xy, -35), chick=False, shells=False)
L = N_['ledge']
g = Griffin('adult', variant='adult')
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
YAW = 25
M0 = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.02), yaw=YAW)
feet = ledge_feet(g, M0, L)
hk = [(0, (0, -10, 0)), (1.6, (-6, 25, 0)), (2.6, (4, 32, 6)), (3.4, (-10, 5, 0)), (4.3, (-10, 5, 0))]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    spread = 0.45 + 0.55 * ease((t - 0.1) / 1.1)
    M = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.02 - 0.04 * (1 - spread)), yaw=YAW)
    key_object(g.arm, f, M)
    rots = anim.perch_rots(t, wing_spread=spread, wing_raise=lerp(5, 30, spread), head=anim.saccade_track(t, hk), seed=2, fold=0.5)
    for side, s_ in (('L', 1), ('R', -1)):
        h = rots['w_hum_' + side]
        rots['w_hum_' + side] = (h[0] - 28 * spread, h[1], h[2] - s_ * 18 * spread)
    for side, s in (('L', 1), ('R', -1)):
        h = rots['w_hum_' + side]
        rots['w_hum_' + side] = (h[0], h[1] - s * 6 * math.sin(t * 2.2) * spread, h[2])
    rf = anim.perch_rots(t, wing_spread=0.0, wing_raise=0.0, seed=2, fold=0.5)
    for k in ('w_hum_R', 'w_fore_R', 'w_hand_R'):
        rots[k] = rf[k]
    rots['jaw'] = (14 * math.sin(math.pi * min(1, max(0, (t - 2.2) / 0.5))) if 2.2 < t < 2.7 else 0, 0, 0)
    anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0, 0)), feet=feet, legs=anim.ADULT_LEGS)
    g.key_feathers(f, {'L': 0.5 * (1 - spread), 'R': 0.5})
    g.key_toes(f, 0.35)
    g.key_lids(f, 1.0 if abs(t - 3.0) < 0.06 else 0.0)
cam = blib.camera('cam', (CAM[0], CAM[1], gz + 1.15), (SUBJ.x + 0.1, SUBJ.y - 0.15, gz + 1.25), lens=24, fstop=8.0)
add_fill((4.5, -2.5, 2.5), (SUBJ.x, SUBJ.y, 1.2), power=90, size=3)
sc.frame_set(1)
run(NAME, N, F, cam, dyn('adult_'), F['to_sun'], gz, margin_px=40, step=2, spp=3)
