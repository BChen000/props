import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
from adult import Griffin
NAME = 's22'; N = 123
SUBJ = Vector((0.0, -0.82, 0))
CAM = (2.75, -1.65)
sc, F, N_, _ = nest_setup(sun_elev=20, sun_rot=sun_from_cam(CAM, SUBJ.xy, -40), chick=False, shells=False, wide=True)
L = N_['ledge']
g = Griffin('juv', variant='juvenile', scale=0.8)
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
M0 = obj_matrix((SUBJ.x, SUBJ.y, gz - 0.015), yaw=0)
feet0 = ledge_feet(g, M0, L, scale=0.8)
T0 = 2.45
FOLD0 = float([a for a in sys.argv if a.startswith('f0=')][0][3:]) if any(a.startswith('f0=') for a in sys.argv) else 0.6
def bump(x):
    return math.sin(math.pi * x) if 0.0 < x < 1.0 else 0.0
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    crouch = ease((t - 0.3) / 1.1) * (1 - ease((t - T0) / 0.2))
    r = bump((t - 1.45) / 0.75)
    if t < T0:
        M = obj_matrix((SUBJ.x, SUBJ.y - 0.04 * r, gz - 0.015 - 0.10 * crouch), yaw=0, pitch=-8 * crouch + 9 * r)
        key_object(g.arm, f, M)
        openw = ease((t - 0.9) / 0.6)
        rots = anim.perch_rots(t, wing_spread=0.0, head=(lerp(5, 22, crouch) + 10 * r, 0, 0), seed=9, fold=lerp(FOLD0, 0.35, openw))
        anim.pose_creature(g.rig, f, M, rots, feet=feet0, legs=anim.ADULT_LEGS)
        g.key_feathers(f, lerp(FOLD0, 0.45, openw))
    else:
        u = t - T0
        x = SUBJ.x + 0.05 * u
        y = SUBJ.y - 0.6 * ease(u / 0.35) - 0.6 * u
        z = gz + 0.4 * ease(u / 0.35) - 0.5 * 2.4 * max(0.0, u - 0.45) ** 2
        pitch = -8 - 12 * ease(u / 0.3) + 30 * ease((u - 0.3) / 0.6) + 30 * ease((u - 1.3) / 0.8)
        M = obj_matrix((x, y, z), yaw=0, pitch=pitch, roll=8 * math.sin(u * 5))
        key_object(g.arm, f, M)
        b = ease(u / 0.4)
        rots, fold, bob = anim.flight_rots(t, period=0.56, amp=44, glide=0.0, legs='tuck', dihedral=15, head=(10 - 25 * ease((u - 1.3) / 0.8), 10 * math.sin(u * 4), 0))
        pr = anim.perch_rots(t, wing_spread=0.0, fold=0.35)
        rr = blend_rots(pr, rots, b)
        anim.pose_creature(g.rig, f, M, rr)
        g.key_feathers(f, {k: lerp(0.45, v, b) for k, v in fold.items()})
    g.key_toes(f, 0.4)
    g.key_lids(f, 0.0)
cam = blib.camera('cam', (CAM[0], CAM[1], gz + 0.85), (-0.1, -1.55, gz + 0.35), lens=22, fstop=8.0)
sc.frame_set(1)
run(NAME, N, F, cam, dyn('juv_'), F['to_sun'], gz, margin_px=40, spp=3)
