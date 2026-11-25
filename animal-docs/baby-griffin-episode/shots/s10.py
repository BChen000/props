import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from flight_common import *
import props
NAME = 's10'; N = 140
sc, F = base_scene(sun_elev=18, sun_rot=150)
g = Griffin('adult', variant='adult')
CAMP = Vector((0.4, -0.9, 0.55))
cam = blib.camera('cam', CAMP, (0, -10, 1), lens=40, clip_end=80000)
mt = props.meat('meat', size=0.26)
def path(t):
    u = t / 5.8
    w = ease(u) * 0.35 + u * 0.65
    return Vector((lerp(-16, -1.2, w), lerp(-62, -6.5, w), lerp(6.5, 1.7, u)))
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    p = path(t)
    v = path(t + 0.05) - path(t - 0.05)
    yaw = math.degrees(math.atan2(-v.x, v.y)) + 180
    flare = ease((t - 4.9) / 0.7)
    flight_key(g, f, t, p, yaw=yaw, pitch=-25 * flare, roll=4 * wob(t, 5, 0.3), period=1.0, amp=44, glide=keyed([(0, 0.6), (1.4, 0.1), (4.2, 0.1), (4.9, 0.3)], t),
               head=(15 * flare, 0, 0), legs='carry', dihedral=8 + 20 * flare)
    g.key_toes(f, 0.55)
    g.key_lids(f, 0.0)
    if f == 1:
        sc.frame_set(1)
        bpy.context.view_layer.update()
        a = g.arm.matrix_world @ g.arm.pose.bones['f_low_L'].tail
        b = g.arm.matrix_world @ g.arm.pose.bones['f_low_R'].tail
        mt.matrix_world = Matrix.Translation((a + b) / 2 + Vector((0, 0, -0.10))) @ Euler((1.4, 0.2, 0.3)).to_matrix().to_4x4()
        blib.parent_to_bone(mt, g.arm, 'f_foot_L')
    tgt = p + Vector((0, 0, 1.0))
    look(cam, f, CAMP, CAMP.lerp(tgt, 1.0))
pc = plate_camera('platecam', CAMP, Vector((-25, -90, 18)), lens=24)
run_flight(NAME, N, F, cam, pc, crop=True, dynamic=[o for o in creature_objects('adult_') if o.type == 'MESH'] + [mt])
