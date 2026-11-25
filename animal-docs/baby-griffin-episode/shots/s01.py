import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sc_common import *
from adult import Griffin
NAME = 's01'; N = 209
sc, F = base_scene(sun_elev=14, sun_rot=70)
g = Griffin('adult', variant='adult')
cam = blib.camera('cam', (0, 0, 0), (0, -1, 0), lens=38, clip_end=80000)
speed = 13.0
def P(t):
    return Vector((-20 + speed * t, -2500 + 1.5 * math.sin(t * 0.4), 80 + 2.0 * math.sin(t * 0.9)))
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    gl = keyed([(0, 0.92), (2.6, 0.92), (3.0, 0.35), (4.3, 0.35), (4.8, 0.92), (7.5, 0.92)], t)
    p = P(t)
    flight_key(g, f, t, p, yaw=90, pitch=-2 + 2 * math.sin(t * 0.9), roll=-6 + 4 * wob(t, 3, 0.15), period=1.15, amp=30, glide=gl,
               head=(4 * wob(t, 11, 0.2), 14 * keyed([(0, -6), (2.5, -6), (3.2, 18), (7, 12)], t), 0), legs='tuck', dihedral=10)
    g.key_lids(f, 1.0 if abs(t - 4.6) < 0.06 else 0.0)
    off = Vector((5.0 + 0.12 * t, 4.6 + 0.45 * t, 1.2 + 0.25 * math.sin(t * 0.5)))
    tgt = p + Vector((-0.6, -0.4, 1.0))
    look(cam, f, p + off, tgt + Vector((0.08 * wob(t, 21, 0.6), 0, 0.06 * wob(t, 22, 0.7))))
sc.frame_set(1)
pc = plate_camera('platecam', P(3.5) + Vector((5.4, 6.2, 1.3)), P(3.5) + Vector((-0.6, -0.4, 1.0)), lens=28)
fg_hide = creature_objects('adult_')
if 'plate' in sys.argv:
    drv.render_plate(NAME, F, fg_hide, cam=pc, spp=24, res=(1080, 1920))
    drv.save_plate_cam(NAME, pc)
drv.set_visible(drv.far_objects(F), False)
only = None
if 'test' in sys.argv:
    only = [1, 60, 120]
drv.render_frames(NAME, 1, N, spp=6, only=only)
