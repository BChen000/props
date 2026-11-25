import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
NAME = 's24'; N = 111
sc, F = base_scene(sun_elev=14, sun_rot=-25)
g = Griffin('juv', variant='juvenile', scale=0.8)
cam = blib.camera('cam', (0, 0, 0), (0, -30, -20), lens=34, clip_end=80000)
keys = [(0.0, Vector((-5.0, -14.0, -9.0))), (1.25, Vector((-1.0, -22.0, -21.0))), (2.55, Vector((5.0, -31.0, -20.0))), (4.7, Vector((16.0, -50.0, -14.0)))]
def hermite(K, t):
    ts = [k[0] for k in K]; ps = [k[1] for k in K]
    n = len(K)
    if t <= ts[0]:
        return ps[0] + (ps[1] - ps[0]) * ((t - ts[0]) / (ts[1] - ts[0]))
    if t >= ts[-1]:
        return ps[-1] + (ps[-1] - ps[-2]) * ((t - ts[-1]) / (ts[-1] - ts[-2]))
    m = []
    for i in range(n):
        if i == 0:
            m.append((ps[1] - ps[0]) / (ts[1] - ts[0]))
        elif i == n - 1:
            m.append((ps[-1] - ps[-2]) / (ts[-1] - ts[-2]))
        else:
            m.append((ps[i + 1] - ps[i - 1]) / (ts[i + 1] - ts[i - 1]))
    for i in range(n - 1):
        if ts[i] <= t <= ts[i + 1]:
            h = ts[i + 1] - ts[i]; u = (t - ts[i]) / h
            h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
            return ps[i] * h00 + m[i] * (h10 * h) + ps[i + 1] * h01 + m[i + 1] * (h11 * h)
def path(t):
    return hermite(keys, t)
ckeys = [(0.0, Vector((-7.5, -9.7, -6.3))), (1.25, Vector((-4.0, -16.84, -19.0))), (2.55, Vector((1.0, -24.12, -19.2))), (4.7, Vector((4.5, -29.5, -15.0)))]
def cpath(t):
    return hermite(ckeys, t)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = path(t)
    v = path(t + 0.12) - path(t - 0.12)
    yaw = math.degrees(math.atan2(-v.x, v.y)) + 180
    pitch = math.degrees(math.atan2(v.z, math.hypot(v.x, v.y)))
    spread = ease((t - 0.3) / 1.0)
    flight_key(g, f, t, p, yaw=yaw, pitch=-pitch * 0.7, roll=-18 * spread + 8, scale=0.8, period=0.9, amp=40 * (1 - spread) + 6,
               glide=lerp(0.2, 0.95, spread), legs='tuck', dihedral=lerp(25, 12, spread), sweep=0.5 * (1 - spread), head=(5, 0, 0))
    g.key_lids(f, 0.0)
    look(cam, f, cpath(t), p + Vector((0, 0, 0.8)))
PD = Vector((math.sin(math.radians(30)) * math.cos(math.radians(-8)), -math.cos(math.radians(30)) * math.cos(math.radians(-8)), math.sin(math.radians(-8))))
pc = plate_camera('platecam', Vector((-4.0, -16.84, -19.0)), Vector((-4.0, -16.84, -19.0)) + 30 * PD, lens=14)
run_flight(NAME, N, F, cam, pc, crop=True, plate_res=(2160, 3840), dynamic=[o for o in creature_objects('juv_') if o.type == 'MESH'])
