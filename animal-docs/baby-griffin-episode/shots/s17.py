import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's17'; N = 87
CAM = (0.9, -3.7)
sc, F, N_, ch = nest_setup(sun_elev=28, sun_rot=sun_from_cam(CAM, (-0.3, -0.8), 30))
L = N_['ledge']
g = Griffin('adult', variant='adult')
CH = Vector((0.2, -1.0, 0))
cz = nest_scene.height_at(L, CH.x, CH.y)
AD = Vector((-1.05, -0.5, 0))
az = nest_scene.height_at(L, AD.x, AD.y)
AYAW = 75
Mland = obj_matrix((AD.x, AD.y, az - 0.02), yaw=AYAW)
afeet = ledge_feet(g, Mland, L)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    # chick turns toward mother and flutters
    cy = lerp(0, 125, ease((t - 0.35) / 0.8))
    Mc = obj_matrix((CH.x, CH.y, cz), yaw=cy)
    key_object(ch.arm, f, Mc)
    cfeet = anim.rest_feet_world(ch.rig, Mc, anim.CHICK_LEGS)
    for k in cfeet:
        cfeet[k].z = nest_scene.height_at(L, cfeet[k].x, cfeet[k].y) + 0.012
    fl = 35 * max(0, math.sin(t * 2 * math.pi * 6)) if 1.3 < t < 2.2 else 0.0
    crot = anim.chick_rots(t, head=(-25 * ease((t - 0.8) / 0.6), 10 * wob(t, 2, 0.4), 0), wings=(fl, fl), seed=12)
    anim.pose_creature(ch.rig, f, Mc, crot, root_off=Vector((0, 0, -0.004)), feet=cfeet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 0.0)
    # mother landing
    land = ease(t / 1.05)
    if t < 1.05:
        p = Vector((lerp(-2.6, AD.x, land), lerp(-2.8, AD.y, land), lerp(3.4, az - 0.02, land)))
        flare = ease(t / 0.9)
        rots, fold, bob = anim.flight_rots(t, period=0.6, amp=lerp(40, 25, flare), glide=0.2, legs='carry', dihedral=lerp(10, 35, flare), head=(15, 0, 0))
        M = obj_matrix(p, yaw=AYAW, pitch=-28 * flare)
        key_object(g.arm, f, M)
        anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0, 0)))
        g.key_feathers(f, fold)
    else:
        u = ease((t - 1.05) / 0.9)
        u2 = ease((t - 1.05) / 1.5)
        prot = anim.perch_rots(t, wing_spread=lerp(0.8, 0.0, u2), wing_raise=lerp(30, 0, u2), head=(lerp(10, 30, u), lerp(0, 18, u), 0), seed=3, fold=0.6)
        M = obj_matrix((AD.x, AD.y, az - 0.02 - 0.05 * math.sin(math.pi * min(1, (t - 1.05) / 0.5))), yaw=AYAW)
        key_object(g.arm, f, M)
        anim.pose_creature(g.rig, f, M, prot, root_off=Vector((0, 0, 0)), feet=afeet, legs=anim.ADULT_LEGS)
        g.key_feathers(f, {'L': 0.6 * u2, 'R': 0.6 * u2})
    g.key_toes(f, 0.35)
    g.key_lids(f, 0.0)
cam = blib.camera('cam', (CAM[0], CAM[1], 1.05), (-0.45, -0.75, 0.75), lens=24, fstop=8.0)
add_fill((1.2, -4.2, 2.0), (-0.4, -0.7, 0.6), power=80, size=3)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch) + dyn('adult_'), F['to_sun'], cz, margin_px=40)
