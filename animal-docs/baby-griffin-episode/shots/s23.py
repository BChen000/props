import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's23'; N = 71
CAM22 = (2.75, -1.65)
sc, F, N_, _ = nest_setup(sun_elev=20, sun_rot=sun_from_cam(CAM22, (0.0, -0.82), -40), chick=False, shells=False, wide=True)
g = Griffin('juv', variant='juvenile', scale=0.8)
for k in ('ledge', 'wall', 'sticks', 'lining'):
    if k in N_ and hasattr(N_[k], 'hide_render'):
        N_[k].hide_render = True; N_[k].hide_viewport = True
cam = blib.camera('cam', (0, 0, 0), (0, -1, 0), lens=24, clip_end=80000)
TE = (N - 1) / 24.0
def P(t):
    return Vector((0.3 + 0.15 * t, -3.6 - 0.25 * t, -4.5 - 0.5 * 8.5 * t * t))
def target(t):
    p = P(t)
    return Vector((p.x, p.y - 0.35, p.z + 0.25 + 1.5 * (t / TE) ** 2))
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = P(t)
    rots, fold, bob = anim.flight_rots(t, period=0.42, amp=48, glide=0.0, legs='tuck', dihedral=lerp(30, 10, t / TE), head=(-15, 18 * math.sin(t * 5), 0))
    M = obj_matrix(p, yaw=68 + 16 * math.sin(t * 1.7), pitch=30 + 10 * math.sin(t * 2.6), roll=14 * math.sin(t * 2.3))
    key_object(g.arm, f, M)
    anim.pose_creature(g.rig, f, M, rots)
    g.key_feathers(f, fold)
    g.key_lids(f, 0.0)
    tg = target(t)
    camp = Vector((p.x + 3.3, p.y + 0.35, tg.z + 0.45))
    look(cam, f, camp, tg)
sc.frame_set(1)
tm = target(TE / 2)
pc = plate_camera('platecam', Vector((P(TE / 2).x + 3.3, P(TE / 2).y + 0.35, tm.z + 0.45)), tm + Vector((0, 0, -0.3)), lens=16)
far_objs = drv.far_objects(F)
hide = [o for o in bpy.data.objects if o.type == 'MESH' and o not in far_objs and not o.hide_render]
if 'quick' in sys.argv:
    quick(NAME, [int(x) for x in sys.argv[sys.argv.index('quick') + 1].split(',')])
else:
    if 'noplate' not in sys.argv:
        drv.render_plate(NAME, F, hide, cam=pc, spp=12, res=(1080, 1920))
        drv.save_plate_cam(NAME, pc)
    drv.set_visible(far_objs, False)
    SPP = int([a for a in sys.argv if a.startswith('spp=')][0][4:]) if any(a.startswith('spp=') for a in sys.argv) else 3
    drv.render_frames(NAME, 1, N, spp=SPP, crop=False)
