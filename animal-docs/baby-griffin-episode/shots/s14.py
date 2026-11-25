import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's14'; N = 149
CAM = (0.55, -1.85)
sc, F, N_, ch = nest_setup(sun_elev=32, sun_rot=sun_from_cam(CAM, (0.6, -1.0), 25), hair_children=2)
L = N_['ledge']
gcache = {}
def ground(x, y):
    k = (round(x, 3), round(y, 3))
    if k not in gcache:
        gcache[k] = nest_scene.height_at(L, x, y)
    return gcache[k]
T_STOP = 2.75
def path(t):
    tt = max(0.0, min(t, T_STOP))
    x = 0.95 - 0.15 * tt
    if t > T_STOP:
        x -= 0.03 * ease((t - T_STOP) / 0.3)
    y = -1.0 + 0.02 * math.sin(tt * 1.3)
    return Vector((x, y, ground(x, y) + 0.0))
yawf = lambda t: -90 + 6 * math.sin(t * 1.1)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = path(t)
    st = 0.0
    if T_STOP < t < 4.6:
        st = math.sin(math.pi * min(1, (t - T_STOP) / 0.35) * 0.5) if t < T_STOP + 0.35 else (1 - ease((t - 3.7) / 0.9) if t > 3.7 else 1.0)
    walk = 1.0 if t < T_STOP else 0.0
    bob = 0.005 * math.sin(4 * math.pi * t / 0.5) * walk
    roll = 6 * math.sin(2 * math.pi * t / 0.5) * walk
    M = obj_matrix(p + Vector((0, 0, bob)), yaw=yawf(t), roll=roll * 0.5)
    key_object(ch.arm, f, M)
    feet = gait_feet(t, path, yawf, ch.rig, anim.CHICK_LEGS, ground, period=0.5, freeze=T_STOP)
    if st > 0:
        for k in ('fl', 'fr'):
            d = Vector((-math.cos(math.radians(0)), 0, 0))
            feet[k] = feet[k] + Vector((-0.035 * st, 0, 0))
    hd = (lerp(8, 45, st), 10 * wob(t, 3, 0.4) * walk, 0)
    rots = anim.chick_rots(t, head=hd, body=(lerp(0, 30, st), 0, roll), wings=(25 * st, 30 * st), tail=(lerp(10, 40, st), 15 * math.sin(t * 4) * walk), seed=8)
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, -0.004 - 0.05 * st)), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 1.0 if (abs(t - 3.05) < 0.12 or abs(t - 4.3) < 0.06) else 0.0)
cam = blib.camera('cam', (CAM[0] - 0.03, CAM[1], 0.28), (0.54, -0.95, 0.10), lens=31, fstop=5.6)
add_fill((0.6, -2.2, 0.7), (0.6, -1.0, 0.1), power=10)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch), F['to_sun'], ground(0.6, -1.0), margin_px=36)
