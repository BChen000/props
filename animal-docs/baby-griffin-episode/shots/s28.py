import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's28'; N = 114
SUBJ = Vector((0.15, 0.52, 0))
CAM = (0.55, -2.55)
sc, F, N_, _ = nest_setup(sun_elev=12, sun_rot=sun_from_cam(CAM, SUBJ.xy, -55), chick=False, shells=False)
L = N_['ledge']
lz = nest_scene.height_at(N_['lining'], nest_scene.NEST_C.x, nest_scene.NEST_C.y)
import bmesh
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0)
me = bpy.data.meshes.new('egg'); bm.to_mesh(me); bm.free()
me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
egg = bpy.data.objects.new('egg', me); blib.link(egg)
egg.scale = (0.075, 0.075, 0.098); egg.rotation_euler = (1.35, 0.0, 0.5)
egg.location = (nest_scene.NEST_C.x + 0.02, nest_scene.NEST_C.y, lz + 0.068)
me.materials.append(env.mat_shell('eggmat'))
g = Griffin('adult', variant='adult')
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
YAW = 100
M0 = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.02), yaw=YAW)
feet = ledge_feet(g, M0, L)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    M = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.02), yaw=YAW)
    key_object(g.arm, f, M)
    rots = anim.perch_rots(t, wing_spread=0.55 + 0.15 * ease(t / 2.0), wing_raise=18, head=(lerp(-4, -12, ease(t / 3)), lerp(-55, -40, ease(t / 3)), 0), seed=4, fold=0.55)
    anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0, 0)), feet=feet, legs=anim.ADULT_LEGS)
    g.key_feathers(f, {'L': 0.3, 'R': 0.3})
    g.key_toes(f, 0.35)
    g.key_lids(f, 0.0)
cam = blib.camera('cam', (CAM[0], CAM[1], gz + 0.62), (-0.05, 0.05, gz + 0.85), lens=26, fstop=8.0)
add_fill((1.5, -3.0, 1.6), (SUBJ.x, SUBJ.y, 1.0), power=90, size=3)
sc.frame_set(1)
run(NAME, N, F, cam, dyn('adult_'), F['to_sun'], gz, margin_px=40, step=2, spp=3)
