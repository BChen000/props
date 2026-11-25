import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
NAME = 's04'; N = 140
sc, F = base_scene(sun_elev=16, sun_rot=40)
g = Griffin('adult', variant='adult')
CAMP = Vector((5.0, -2.0, 3.0))
cam = blib.camera('cam', CAMP, (0, -1, 0), lens=30, clip_end=80000)
pts = [(0.0, Vector((-30, -70, 30))), (2.9, Vector((-12, -32, 13))), (4.4, Vector((1.0, -8.5, 4.6))), (5.0, Vector((4.2, -1.6, 4.4))), (5.8, Vector((9, 8, 4.2)))]
def path(t):
    for (t0, a), (t1, b) in zip(pts[:-1], pts[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            return a.lerp(b, u)
    return pts[-1][1]
def vel(t):
    return (path(t + 0.05) - path(t - 0.05)) / 0.1
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = path(t); v = vel(t)
    yaw = math.degrees(math.atan2(-v.x, v.y)) + 180
    hv = math.hypot(v.x, v.y)
    pitch = math.degrees(math.atan2(v.z, hv))
    strike = ease((t - 3.5) / 0.5)
    legs = 'strike' if t > 3.5 else 'tuck'
    sweep = 0.45 * (1 - strike)
    flight_key(g, f, t, p, yaw=yaw, pitch=-pitch * 0.6 + 8 * strike * 0, roll=-10, period=0.9, amp=30, glide=0.9 - 0.6 * strike,
               head=(10 - 25 * strike, 0, 0), legs=legs, dihedral=4 + 12 * strike, sweep=sweep)
    g.key_toes(f, -0.35 * strike + 0.6 * ease((t - 4.6) / 0.3))
    g.key_lids(f, 0.0)
    tgt = p + Vector((0, 0, 1.0))
    th = min(t, 4.45)
    d = (path(th) + Vector((0, 0, 1.0)) - CAMP).normalized()
    look(cam, f, CAMP + Vector((0, 0, 0.02 * math.sin(t * 7))), CAMP + d * 10)
pc = plate_camera('platecam', CAMP, Vector((-10, -38, 12)), lens=16)
run_flight(NAME, N, F, cam, pc, crop=True, dynamic=[o for o in creature_objects('adult_') if o.type == 'MESH'])
