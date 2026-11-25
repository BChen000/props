import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's19'; N = 165
SUBJ = Vector((0.3, -0.5, 0))
sc, F, N_, _ = nest_setup(sun_elev=22, sun_rot=60, chick=False, shells=False)
L = N_['ledge']
g = Griffin('juv', variant='juvenile', scale=0.8)
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
M = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.015), yaw=-20)
feet = ledge_feet(g, M, L, scale=0.8)
hk = [(0, (2, 0, 0)), (0.9, (3, 4, 0)), (1.6, (1, -3, 2)), (2.5, (4, 6, -2)), (3.3, (2, 1, 0)), (4.2, (5, -4, 0)), (5.0, (3, 2, 0)), (5.6, (3, 2, 0))]
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    key_object(g.arm, f, M)
    rots = anim.perch_rots(t, wing_spread=0.0, head=anim.saccade_track(t, hk), seed=6, fold=0.5, breathe=0.4)
    anim.pose_creature(g.rig, f, M, rots, feet=feet, legs=anim.ADULT_LEGS)
    g.key_feathers(f, 0.5)
    g.key_lids(f, 1.0 if abs(t - 2.05) < 0.07 else 0.0)
sc.frame_set(1)
bpy.context.view_layer.update()
eye = g.eyes['L']
acc = json.load(open(blib.ASSETS + 'adult_rig.json'))['acc']
cl = sum((v.co for v in eye.data.vertices), Vector()) / len(eye.data.vertices)
ec = eye.matrix_world @ cl
ed = (eye.matrix_world.to_3x3() @ Vector(acc['eye_L']['dir'])).normalized()
side = ed.cross(Vector((0, 0, 1))).normalized()
camp = ec + ed * 0.34 - side * 0.05 + Vector((0, 0, 0.03))
cam = blib.camera('cam', camp, ec + Vector((0, 0, 0.004)), lens=85, fstop=4.0, focus=(camp - ec).length)
for f in (1, N):
    t = (f - 1) / 24.0
    look(cam, f, camp + (ec - camp) * 0.10 * (f - 1) / (N - 1), ec + Vector((0, 0, 0.004)))
add_fill(tuple(camp + Vector((0, 0, 0.5))), tuple(ec), power=6, size=1.0)
run(NAME, N, F, cam, dyn('juv_'), F['to_sun'], gz, margin_px=40, crop=False, step=2, spp=3)
