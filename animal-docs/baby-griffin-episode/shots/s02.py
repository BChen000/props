import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
NAME = 's02'; N = 51
sc, F = base_scene(sun_elev=14, sun_rot=70)
g = Griffin('adult', variant='adult')
cam = blib.camera('cam', (0, 0, 0), (0, -1, 0), lens=55, clip_end=80000)
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 4.0
speed = 13.0
P = lambda t: Vector((80 + speed * t, -2500, 80 + 1.5 * math.sin(t)))
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = P(t)
    hy = keyed([(0, -10), (0.35, -10), (0.75, 42), (1.4, 46)], t)
    M = flight_key(g, f, t, p, yaw=90, pitch=-1, roll=-4, period=1.05, amp=40, glide=0.85, head=(2, hy, 0), legs='tuck', dihedral=10)
    g.key_lids(f, 1.0 if abs(t - 1.1) < 0.05 else 0.0)
    sc.frame_set(f)
    h = head_world(g)
    look(cam, f, h + Vector((0.55 + 0.06 * t, 1.25, 0.10)), h + Vector((-0.05, 0.0, -0.02)))
    cam.data.dof.focus_distance = 1.36
    cam.data.keyframe_insert('dof.focus_distance', frame=f)
sc.frame_set(16)
h = head_world(g)
pc = plate_camera('platecam', h + Vector((0.58, 1.25, 0.10)), h + Vector((-0.05, 0, -0.02)), lens=36)
run_flight(NAME, N, F, cam, pc)
