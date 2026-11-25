import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's20'; N = 199
sc, F, N_, _ = nest_setup(sun_elev=26, sun_rot=40, chick=False, shells=False)
L = N_['ledge']
g = Griffin('juv', variant='juvenile', scale=0.8)
SUBJ = Vector((0.1, -0.80, 0))
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
M = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.02), yaw=0)
feet0 = ledge_feet(g, M, L, scale=0.8)
for k in ('fl', 'fr'):
    z = nest_scene.height_at(L, feet0[k].x, feet0[k].y)
    feet0[k].z = z + 0.045
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    key_object(g.arm, f, M)
    lift = 0.05 * max(0.0, math.sin(math.pi * (t - 3.4) / 0.7)) if 3.4 < t < 4.1 else 0.0
    feet = dict(feet0)
    feet['fl'] = feet0['fl'] + Vector((0, -0.01 * lift / 0.05, lift))
    rots = anim.perch_rots(t, wing_spread=0.0, head=(18, 0, 0), seed=7, fold=0.5, breathe=0.6)
    anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0.01 * math.sin(t * 1.3), 0)), feet=feet, legs=anim.ADULT_LEGS)
    g.key_feathers(f, 0.5)
    cL = 0.25 + 0.75 * ease((t - 0.5) / 1.6)
    if 3.3 < t < 4.3:
        cL = lerp(cL, 0.05, math.sin(math.pi * (t - 3.3) / 1.0))
    if t > 4.3:
        cL = 0.25 + 0.85 * ease((t - 4.3) / 1.2)
    g.key_toes(f, {'L': cL, 'R': 0.75})
    g.key_lids(f, 0.0)
sc.frame_set(1)
bpy.context.view_layer.update()
fw = g.arm.matrix_world @ g.arm.pose.bones['f_low_L'].tail
cam = blib.camera('cam', fw + Vector((0.30, -0.80, -0.06)), fw + Vector((-0.02, -0.06, -0.02)), lens=45, fstop=5.6)
add_fill(tuple(fw + Vector((0.6, -0.8, 0.5))), tuple(fw), power=10, size=1.0)
run(NAME, N, F, cam, dyn('juv_'), F['to_sun'], gz, margin_px=40, step=2, spp=3)
