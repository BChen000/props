import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
NAME = 's05'; N = 102
sc, F = base_scene(sun_elev=12, sun_rot=-15)
g = Griffin('adult', variant='adult')
CAMP = Vector((0.0, -1500.0, 40.0))
cam = blib.camera('cam', CAMP, (0, -3000, 0), lens=35, clip_end=80000)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = CAMP + Vector((-1.6 + 1.0 * t, -9.5 - 12.0 * t, -2.6 - 1.8 * t))
    flight_key(g, f, t, p, yaw=12 - 6 * t, pitch=-3, roll=8 + 6 * ease(t / 3), period=1.1, amp=42,
               glide=keyed([(0, 0.0), (1.6, 0.0), (2.1, 0.9), (4, 0.9)], t), head=(0, -10, 0), legs='tuck', dihedral=9)
    g.key_lids(f, 0.0)
    look(cam, f, CAMP + Vector((0.3 * t, -1.5 * t, 0)), CAMP + Vector((0.6 * t - 1.0, -40.0, -9.0 - 0.8 * t)))
pc = plate_camera('platecam', CAMP, CAMP + Vector((0, -40, -9.5)), lens=26)
run_flight(NAME, N, F, cam, pc, crop=True, dynamic=[o for o in creature_objects('adult_') if o.type == 'MESH'])
