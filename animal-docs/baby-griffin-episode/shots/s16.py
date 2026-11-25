import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
import props
NAME = 's16'; N = 139
SUBJ = Vector((0.12, -1.06, 0))
CAM = (1.25, -1.62)
sc, F, N_, ch = nest_setup(sun_elev=34, sun_rot=sun_from_cam(CAM, SUBJ.xy, 40), wide=True, hair_children=2)
L = N_['ledge']
gz = nest_scene.height_at(L, SUBJ.x, SUBJ.y)
peb = props.pebble('pebble', 0.022, N_['rock_mat'])
pz0 = nest_scene.height_at(L, SUBJ.x - 0.03, -1.27) or (gz - 0.05)
for f in range(1, N + 1):
    t = (f - 1) / 24.0
    back = ease((t - 2.05) / 0.25) * (1 - ease((t - 3.4) / 0.8))
    M = obj_matrix((SUBJ.x, SUBJ.y + 0.05 * back, gz), yaw=0 + 5 * wob(t, 3, 0.2))
    key_object(ch.arm, f, M)
    if f == 1:
        feet0 = anim.rest_feet_world(ch.rig, M, anim.CHICK_LEGS)
        for k in feet0:
            feet0[k].z = nest_scene.height_at(L, feet0[k].x, feet0[k].y) + 0.012
    peer = ease(t / 0.8)
    hd = (lerp(10, 52, peer) - 60 * back, 15 * wob(t, 5, 0.3), 0)
    rots = anim.chick_rots(t, head=hd, body=(lerp(0, 22, peer) - 26 * back, 0, 0), wings=(18 * back, 18 * back), tail=(10 - 20 * back, 0), seed=10)
    feet = dict(feet0)
    if back > 0:
        for k in ('fl', 'fr'):
            feet[k] = feet0[k] + Vector((0, 0.04 * back, 0))
    anim.pose_creature(ch.rig, f, M, rots, root_off=Vector((0, 0, -0.005)), feet=feet, legs=anim.CHICK_LEGS)
    ch.key_lids(f, 1.0 if abs(t - 2.1) < 0.12 else 0.0)
    if t < 1.55:
        pp = Vector((SUBJ.x - 0.03, -1.255, pz0 + 0.01)); rr = (0, 0, 0)
    else:
        u = t - 1.55
        pp = Vector((SUBJ.x - 0.03 - 0.05 * u, -1.255 - 0.25 * u, pz0 + 0.01 - 4.9 * u * u)); rr = (u * 9, u * 5, u * 3)
    peb.location = pp; peb.rotation_euler = rr
    peb.keyframe_insert('location', frame=f); peb.keyframe_insert('rotation_euler', frame=f)
cam = blib.camera('cam', (CAM[0], CAM[1], gz + 0.32), (0.0, -1.32, gz - 0.85), lens=24, fstop=8.0, focus=1.25)
sc.frame_set(1)
run(NAME, N, F, cam, chick_dynamic(ch) + [peb], F['to_sun'], gz, margin_px=36)
