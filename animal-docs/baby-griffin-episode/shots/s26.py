import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
NAME = 's26'; N = 95
sc, F = base_scene(sun_elev=10, sun_rot=-30)
g = Griffin('juv', variant='juvenile', scale=0.8)
CAMP = Vector((30.0, -900.0, -10.0))
cam = blib.camera('cam', CAMP, CAMP + Vector((-8, -100, 4)), lens=35, clip_end=80000)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = CAMP + Vector((-2.5 - 1.2 * t, -12.0 - 13.0 * t, 1.0 + 1.0 * t))
    flight_key(g, f, t, p, yaw=-5, pitch=-1, roll=-6, scale=0.8, period=1.0, amp=42, glide=keyed([(0, 0.1), (1.6, 0.1), (2.0, 0.9), (4, 0.9)], t),
               legs='tuck', dihedral=10)
    g.key_lids(f, 0.0)
    look(cam, f, CAMP, CAMP + Vector((-8 - 1.0 * t, -100, 5)))
pc = plate_camera('platecam', CAMP, CAMP + Vector((-9.5, -100, 5)), lens=30)
run_flight(NAME, N, F, cam, pc, crop=True, dynamic=[o for o in creature_objects('juv_') if o.type == 'MESH'])
