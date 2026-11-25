import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's21'; N = 79
SUBJ = Vector((0.0, -0.82, 0))
sc, F, N_, _ = nest_setup(sun_elev=14, sun_rot=-20, chick=False, shells=False)
L = N_['ledge']
g = Griffin('juv', variant='juvenile', scale=0.8)
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
M = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.015), yaw=0)
feet = ledge_feet(g, M, L, scale=0.8)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    key_object(g.arm, f, M)
    rots = anim.perch_rots(t, wing_spread=0.0, head=(lerp(4, 16, ease(t / 2.5)), 8 * wob(t, 2, 0.3), 0), seed=8, fold=0.8)
    for side, s in (('L', 1), ('R', -1)):
        h = rots['w_hum_' + side]
        rots['w_hum_' + side] = (h[0], h[1] - s * (3 * wob(t, 11 + s, 1.2)), h[2])
    anim.pose_creature(g.rig, f, M, rots, feet=feet, legs=anim.ADULT_LEGS)
    g.key_feathers(f, {'L': 0.8 + 0.04 * wob(t, 21, 1.5), 'R': 0.8 + 0.04 * wob(t, 22, 1.5)})
    g.key_toes(f, 0.5)
    g.key_lids(f, 0.0)
cam = blib.camera('cam', (0.65, 0.28, 2.0), (-0.15, -3.2, -0.6), lens=24, fstop=8.0)
sc.frame_set(1)
run(NAME, N, F, cam, dyn('juv_'), F['to_sun'], gz, margin_px=40, step=2, spp=3)
