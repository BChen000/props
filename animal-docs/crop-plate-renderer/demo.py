"""crop-plate-renderer / demo.py: two one-second shots that exercise both render modes, then the composite.

  python3 demo.py flight   moving camera: the far scenery is rendered once as a wide plate, the griffin as transparent
                           crops every frame; comp.py warps the plate per frame with a homography -> out/flight.mp4
  python3 demo.py perch    static camera: plate + base (the ledge and nest, no griffin) once, then only the griffin's
                           box every 2nd frame; comp.py fills the gaps with optical-flow in-betweens -> out/perch.mp4
  python3 demo.py both     both, then out/sheet.png (frames 1, 12 and 24 of each); `sheet` redraws only the sheet

Uses ../griffin (creature, blib) and ../cliff-nest-set (ledge, nest, far scenery). Blender 5.3 as a Python module.
"""
import os, sys, math, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
# ---------------------------------------------------------------- settings (shipped values; env overrides)
os.environ.setdefault('CPR_SHOTS', os.path.join(HERE, 'build', 'shots'))
os.environ.setdefault('CPR_RES', '304x540')      # the episode rendered 608x1080
os.environ.setdefault('CPR_OUT', '540x960')      # the episode composited to 1080x1920
SETTINGS = dict(
    N=int(os.environ.get('N', '24')),
    SPP=int(os.environ.get('SPP', '4')),
    PLATE_SPP=int(os.environ.get('PLATE_SPP', '12')),
    OUT=os.environ.get('OUT', os.path.join(HERE, 'out')),
)
SUN_COL = (1.0, 0.78, 0.55)
# ----------------------------------------------------------------
for p in (HERE, os.path.join(HERE, '..', 'griffin'), os.path.join(HERE, '..', 'cliff-nest-set')):
    sys.path.insert(0, p)


def look(cam, frame, loc, target):
    from mathutils import Vector
    q = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y')
    cam.rotation_mode = 'QUATERNION'
    cam.location = loc; cam.rotation_quaternion = q
    cam.keyframe_insert('location', frame=frame); cam.keyframe_insert('rotation_quaternion', frame=frame)


def plate_camera(name, loc, target, lens):
    import bpy, blib
    from mathutils import Vector
    cd = bpy.data.cameras.new(name)
    cd.lens = lens; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.clip_end = 80000; cd.clip_start = 0.5
    ob = bpy.data.objects.new(name, cd)
    blib.link(ob)
    ob.rotation_mode = 'QUATERNION'
    ob.location = loc; ob.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y')
    return ob


def shot_flight():
    import bpy, blib, anim, far, drv
    from mathutils import Vector
    from adult import Griffin
    N = SETTINGS['N']
    sc = blib.reset()
    F = far.build_far(sun_elev=15, sun_rot=70, sun_strength=3.8, sky_strength=0.22, sun_color=SUN_COL)
    g = Griffin('adult', variant='adult')
    cam = blib.camera('cam', (0, 0, 0), (0, -1, 0), lens=30, clip_end=80000)
    for f in range(1, N + 1):
        t = (f - 1) / 24.0
        p = Vector((-10 + 13.0 * t, -2500.0, 80.0 + 0.6 * math.sin(t * 2)))
        M = anim.obj_matrix(p, yaw=90, pitch=-2, roll=-6)               # yaw 90: flying toward +X
        anim.key_object(g.arm, f, M)
        rots, fold, bob = anim.flight_rots(t, period=1.1, amp=40, glide=0.3, dihedral=10)
        anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0, bob)))
        g.key_feathers(f, fold)
        look(cam, f, p + Vector((5.0 + 0.6 * t, 4.6 + 1.2 * t, 1.2)), p + Vector((-0.6, -0.4, 1.0)))
    sc.frame_set(1)
    mid = Vector((-10 + 6.5 * N / 24.0, -2500.0, 80.0))
    pc = plate_camera('platecam', mid + Vector((5.4, 6.2, 1.3)), mid + Vector((-0.6, -0.4, 1.0)), lens=20)
    far_objs = drv.far_objects(F)
    hide = [o for o in bpy.data.objects if o.type == 'MESH' and o not in far_objs and not o.hide_render]
    W, H = drv.RES
    drv.render_plate('flight', F, hide, cam=pc, spp=SETTINGS['PLATE_SPP'], res=(W * 2, H * 2))
    drv.save_plate_cam('flight', pc)
    drv.set_visible(far_objs, False)
    dyn = [o for o in bpy.data.objects if o.name.startswith('adult') and o.type == 'MESH']
    drv.render_frames('flight', 1, N, spp=SETTINGS['SPP'], dynamic=dyn, crop=True, margin_px=30)


def shot_perch():
    import bpy, blib, anim, far, drv, nest_scene
    from adult import Griffin
    N = SETTINGS['N']
    sc = blib.reset()
    F = far.build_far(sun_elev=24, sun_rot=40, sun_strength=3.8, sky_strength=0.22, sun_color=SUN_COL)
    S = nest_scene.build(wide=True, drop=False)
    g = Griffin('adult', variant='adult')
    x, y = 0.15, -0.55
    gz = nest_scene.height_at(S['ledge'], x, y)
    M = anim.obj_matrix((x, y, gz - 0.02), yaw=25)
    feet = anim.rest_feet_world(g.rig, M, anim.ADULT_LEGS)
    for k in feet:
        feet[k].z = nest_scene.height_at(S['ledge'], feet[k].x, feet[k].y) + 0.06
    keys = [(0, (-4, -12, 0)), (0.4, (-8, 28, 4)), (1.0, (-8, 28, 4))]
    for f in range(1, N + 1):
        t = (f - 1) / 24.0
        anim.key_object(g.arm, f, M)
        rots = anim.perch_rots(t, wing_raise=9.0, head=anim.saccade_track(t, keys), seed=2, fold=0.66)
        anim.pose_creature(g.rig, f, M, rots, feet=feet, legs=anim.ADULT_LEGS)
        g.key_feathers(f, 0.66); g.key_toes(f, 0.35); g.key_lids(f, 0.0)
    blib.camera('cam', (3.0, -1.6, gz + 1.15), (x + 0.1, y - 0.15, gz + 1.15), lens=24, fstop=8.0, clip_end=80000)
    sc.frame_set(1)
    far_objs = drv.far_objects(F)
    hide = [o for o in bpy.data.objects if o.type == 'MESH' and o not in far_objs and not o.hide_render]
    drv.render_plate('perch', F, hide, cam=sc.camera, spp=SETTINGS['PLATE_SPP'], res=drv.RES)
    drv.set_visible(far_objs, False)
    dyn = [o for o in bpy.data.objects if o.name.startswith('adult') and o.type == 'MESH']
    drv.render_frames('perch', 1, N, spp=SETTINGS['SPP'], dynamic=dyn, static=True, crop=True,
                      to_sun=F['to_sun'], ground_z=gz, margin_px=60, step=2)


def composite(name):
    import comp
    os.makedirs(SETTINGS['OUT'], exist_ok=True)
    comp.compose_shot(name, 1, SETTINGS['N'], os.path.join(SETTINGS['OUT'], name + '.mp4'))


def sheet():
    import numpy as np, cv2
    rows = []
    for name in ('flight', 'perch'):
        ims = []
        for i in (0, SETTINGS['N'] // 2 - 1, SETTINGS['N'] - 1):
            cap = cv2.VideoCapture(os.path.join(SETTINGS['OUT'], name + '.mp4'))
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, fr = cap.read()
            ims.append(cv2.resize(fr, (fr.shape[1] * 2 // 3, fr.shape[0] * 2 // 3), interpolation=cv2.INTER_AREA))
        rows.append(np.hstack(ims))
    cv2.imwrite(os.path.join(SETTINGS['OUT'], 'sheet.png'), np.vstack(rows))
    print('wrote', os.path.join(SETTINGS['OUT'], 'sheet.png'))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if what in ('flight', 'perch'):
        {'flight': shot_flight, 'perch': shot_perch}[what]()
        subprocess.run([sys.executable, os.path.abspath(__file__), 'comp-' + what], check=True)  # comp.py needs no Blender
    elif what.startswith('comp-'):
        composite(what[5:])
    elif what == 'both':
        for n in ('flight', 'perch'):
            subprocess.run([sys.executable, os.path.abspath(__file__), n], check=True)
        sheet()
    elif what == 'sheet':
        sheet()
