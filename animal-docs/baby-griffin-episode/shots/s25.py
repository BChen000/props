import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
NAME = 's25'; N = 154
sc, F = base_scene(sun_elev=9, sun_rot=-8)
g = Griffin('juv', variant='juvenile', scale=0.8)
cam = blib.camera('cam', (0, 0, 0), (0, -1, 0), lens=32, clip_end=80000)
P = lambda t: Vector((3.0 * math.sin(t * 0.35), -600.0 - 13.0 * t, -40.0 + 1.2 * t))
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = P(t)
    gl = keyed([(0, 0.95), (2.0, 0.95), (2.4, 0.1), (3.6, 0.1), (4.1, 0.95), (6, 0.95)], t)
    flight_key(g, f, t, p, yaw=-6 * math.cos(t * 0.35), pitch=-1, roll=-8 * math.cos(t * 0.35) + 3 * wob(t, 4, 0.2), scale=0.8, period=1.0, amp=40,
               glide=gl, legs='tuck', dihedral=11, head=(2, 6 * wob(t, 5, 0.15), 0))
    g.key_lids(f, 0.0)
    off = Vector((-3.4 + 0.3 * t, 6.2 - 0.25 * t, 2.4 - 0.12 * t))
    look(cam, f, p + off, p + Vector((0.4, -6.0, 0.2)))
pc = plate_camera('platecam', P(2.6) + Vector((-2.6, 5.6, 2.1)), P(2.6) + Vector((0.4, -6.0, 0.2)), lens=22)
run_flight(NAME, N, F, cam, pc, crop=True, dynamic=[o for o in creature_objects('juv_') if o.type == 'MESH'])
