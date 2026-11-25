from sc_common import *
import nest_scene
from chick import Chick


def nest_setup(sun_elev=15, sun_rot=70, shells=True, chick=True, hair_parents=2600, hair_children=3, wide=False):
    sc, F = base_scene(sun_elev=sun_elev, sun_rot=sun_rot)
    N = nest_scene.build(wide=wide)
    nz = N['nest_z']
    lz = nest_scene.height_at(N['lining'], nest_scene.NEST_C.x, nest_scene.NEST_C.y)
    N['lining_z'] = lz
    if shells:
        sh = env.egg_shell_pieces('shell', (0, 0, 0), size=0.085, n=4, seed=5)
        spots = [(0.19, 0.10, 2.6, 0.3, 0.2), (-0.18, 0.15, 0.4, 2.8, 1.0), (0.13, -0.19, 3.0, 0.9, 2.0), (-0.20, -0.06, 0.6, 0.2, 2.6)]
        for o, (dx, dy, rx, ry, rz) in zip(sh, spots):
            o.rotation_euler = (rx, ry, rz)
            bpy.context.view_layer.update()
            zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
            cx = sum((o.matrix_world @ v.co).x for v in o.data.vertices) / len(o.data.vertices)
            cy = sum((o.matrix_world @ v.co).y for v in o.data.vertices) / len(o.data.vertices)
            px, py = nest_scene.NEST_C.x + dx, nest_scene.NEST_C.y + dy
            if 'oldshells' in sys.argv:
                o.location = (px - cx, py - cy, lz + 0.012 - min(zs))
            else:
                hz = max(nest_scene.height_at(N['lining'], px + ox, py + oy) or lz for ox in (-0.03, 0, 0.03) for oy in (-0.03, 0, 0.03))
                o.location = (px - cx, py - cy, hz + 0.006 - min(zs))
        N['shells'] = sh
    ch = Chick(hair=True, hair_parents=hair_parents, hair_children=hair_children) if chick else None
    return sc, F, N, ch


def chick_dynamic(ch):
    return [o for o in ch.all_objects if o.type == 'MESH']


def static_objs(N):
    out = [N['ledge'], N['wall'], N['drop'], N['sticks'], N['lining']] + N.get('shells', [])
    return out


def add_fill(loc, target, power=25.0, size=1.5, color=(1.0, 0.95, 0.9)):
    ld = bpy.data.lights.new('fill', 'AREA'); ld.energy = power; ld.size = size; ld.color = color
    ob = bpy.data.objects.new('fill', ld); blib.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    try:
        ob.visible_camera = False
    except Exception:
        pass
    return ob


def quick(NAME, frames):
    sc = bpy.context.scene
    for a in sys.argv:
        if a.startswith('hideobj='):
            for nm in a[8:].split('+'):
                ob = bpy.data.objects.get(nm)
                if ob is not None:
                    ob.hide_render = True
    blib.render_settings(res=(360, 640), spp=4, transparent=False, bounces=(3, 1, 1, 1, 4))
    if 'mblur' in sys.argv:
        sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.35
    os.makedirs(drv.SHOTS + NAME + '/quick', exist_ok=True)
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = drv.SHOTS + NAME + '/quick/%04d.png' % f
        bpy.ops.render.render(write_still=True)


def run(NAME, N, F, cam, dynamic, to_sun, ground_z, crop=True, plate_spp=12, spp=4, base_spp=16, margin_px=60, only=None, plate=True, step=1):
    if 'quick' in sys.argv:
        quick(NAME, [int(x) for x in sys.argv[sys.argv.index('quick') + 1].split(',')])
        return
    far_objs = drv.far_objects(F)
    hide = [o for o in bpy.data.objects if o.type == 'MESH' and o not in far_objs and not o.hide_render]
    if plate and 'noplate' not in sys.argv:
        drv.render_plate(NAME, F, hide, cam=cam, spp=plate_spp, res=drv.RES)
    drv.set_visible(far_objs, False)
    if 'test' in sys.argv:
        only = [int(x) for x in sys.argv[sys.argv.index('test') + 1].split(',')]
    for a in sys.argv:
        if a.startswith('spp='):
            spp = int(a[4:])
    drv.render_frames(NAME, 1, N, spp=spp, dynamic=dynamic, static=(True if crop else None) if 'keepbase' not in sys.argv else None, crop=crop, to_sun=to_sun,
                      ground_z=ground_z, base_spp=base_spp, margin_px=max(margin_px, 60), only=only, step=step)


def sun_from_cam(cam_loc, subj, side=35.0):
    d = Vector(cam_loc) - Vector(subj)
    return math.degrees(math.atan2(d.x, -d.y)) + side


def gait_feet(t, path, yawf, rig, legs, ground, period=0.5, duty=0.62, lift=0.022,
              phases=None, scale=1.0, freeze=None):
    """returns world foot targets per leg for a walking quadruped. path(t)->Vector, yawf(t)->deg"""
    phases = phases or {'hl': 0.0, 'fl': 0.25, 'hr': 0.5, 'fr': 0.75}
    out = {}
    for k, (u, l, e) in legs.items():
        off = anim.bone_tail_rest(rig, l) * scale
        ph = phases[k]
        tt = t if freeze is None else min(t, freeze)
        s = tt / period + ph
        n = math.floor(s); c = s - n
        def plant(nn):
            tm = (nn + duty * 0.5 - ph) * period
            M = obj_matrix(path(tm), yaw=yawf(tm), scale=scale)
            p = M @ off
            p.z = ground(p.x, p.y) + 0.012 * scale
            return p
        if c < duty:
            p = plant(n)
        else:
            w = (c - duty) / (1 - duty)
            a, b = plant(n), plant(n + 1)
            p = a.lerp(b, ease(w)) + Vector((0, 0, lift * math.sin(math.pi * w)))
        out[k] = p
    return out


def blend_rots(r1, r2, u):
    out = {}
    for k in set(r1) | set(r2):
        a = r1.get(k, (0, 0, 0)); b = r2.get(k, (0, 0, 0))
        out[k] = tuple(x + (y - x) * u for x, y in zip(a, b))
    return out


def ledge_feet(g, M, L, scale=1.0, lift=0.0):
    feet = anim.rest_feet_world(g.rig, M, anim.ADULT_LEGS)
    for k in feet:
        z = nest_scene.height_at(L, feet[k].x, feet[k].y)
        if z is not None:
            off = 0.06 * scale if k.startswith('f') else 0.06 * scale
            feet[k].z = z + off + lift
    return feet


def dyn(prefix):
    return [o for o in bpy.data.objects if o.name.startswith(prefix) and o.type == 'MESH']


def ground_flap_rots(t, base, period=0.55, amp=45.0, glide=0.0, dihedral=10.0, sweep=0.0):
    fr, fold, bob = anim.flight_rots(t, period=period, amp=amp, glide=glide, dihedral=dihedral, sweep=sweep, legs='none')
    out = dict(base)
    for k, v in fr.items():
        if k.startswith('w_'):
            out[k] = v
    return out, fold, bob
