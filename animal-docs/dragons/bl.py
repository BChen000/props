import bpy, bmesh, math, numpy as np, addon_utils
from mathutils import Vector, Matrix, Euler, Quaternion


def reset(fps=24):
    addon_utils.enable('cycles', default_set=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.render.fps = fps
    s.view_settings.view_transform = 'AgX'
    try:
        s.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    return s


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def mesh_obj(name, verts, faces, smooth=True, coll=None):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float32)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    faces = [list(f) for f in faces]
    lens = np.array([len(f) for f in faces], np.int32)
    me.loops.add(int(lens.sum()))
    me.loops.foreach_set("vertex_index", np.concatenate(faces).astype(np.int32))
    me.polygons.add(len(faces))
    starts = np.concatenate([[0], np.cumsum(lens)[:-1]]).astype(np.int32)
    me.polygons.foreach_set("loop_start", starts)
    me.update(calc_edges=True)
    me.validate()
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    return ob


def add_attr(ob, name, values, kind='FLOAT'):
    me = ob.data
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    if kind == 'VEC':
        a = me.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set("vector", np.asarray(values, np.float32).ravel())
    else:
        a = me.attributes.new(name, 'FLOAT', 'POINT')
        a.data.foreach_set("value", np.asarray(values, np.float32).ravel())


def store_rest(ob):
    co = np.zeros(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    add_attr(ob, "rest", co.reshape(-1, 3), 'VEC')


def set_weights(ob, weights):
    for name, w in weights.items():
        vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
        w = np.asarray(w)
        idx = np.nonzero(w > 0.002)[0]
        for i in idx:
            vg.add([int(i)], float(w[i]), 'REPLACE')


def set_weights_fast(ob, weights):
    for name, w in weights.items():
        vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
        w = np.asarray(w)
        idx = np.nonzero(w > 0.002)[0]
        if len(idx) == 0:
            continue
        q = np.round(w[idx] * 50) / 50
        for val in np.unique(q):
            sel = idx[q == val]
            vg.add(sel.tolist(), float(max(val, 0.02)), 'REPLACE')


def make_armature(name, bones, coll=None):
    """bones: list of (name, head, tail, parent, roll_axis) roll_axis = vector to align Z."""
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    link(ob, coll)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for bn, h, t, par, zaxis in bones:
        b = eb.new(bn)
        b.head = Vector(h); b.tail = Vector(t)
        if zaxis is not None:
            b.align_roll(Vector(zaxis))
        if par:
            b.parent = eb[par]
            b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'XYZ'
    return ob


def bind(mesh_ob, arm_ob):
    mesh_ob.parent = arm_ob
    m = mesh_ob.modifiers.new("arm", 'ARMATURE')
    m.object = arm_ob
    m.use_deform_preserve_volume = False
    return m


def nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    return nt.nodes, nt.links


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt.nodes, nt.links, out


def N(nodes_, kind, **inputs):
    n = nodes_.new(kind)
    for k, v in inputs.items():
        if k.startswith("_"):
            setattr(n, k[1:], v)
        else:
            n.inputs[k].default_value = v
    return n


def render_settings(s, w, h, spp, transparent=False, mblur=True, dn=True, thresh=0.05,
                    bounces=(3, 2, 2, 4), clamp_ind=4.0):
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.resolution_percentage = 100
    c = s.cycles
    c.samples = spp
    c.use_adaptive_sampling = True
    c.adaptive_threshold = thresh
    c.adaptive_min_samples = 4
    c.use_denoising = dn
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.denoising_prefilter = 'FAST'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = bounces[0], bounces[1], bounces[2], bounces[3]
    c.volume_bounces = 0
    c.transparent_max_bounces = 16
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = clamp_ind
    c.sample_clamp_direct = 0
    c.use_light_tree = True
    s.render.film_transparent = transparent
    s.render.use_motion_blur = mblur
    s.render.motion_blur_shutter = 0.5
    s.render.use_persistent_data = True
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    s.render.image_settings.color_depth = '8'
    try:
        c.texture_limit_render = 'OFF'
    except Exception:
        pass


def camera(name, loc, target=None, lens=50, rot=None, fstop=None, focus=None, sensor=36, fit='VERTICAL'):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_fit = fit
    cam.sensor_height = sensor
    cam.sensor_width = sensor
    cam.clip_start = 0.05
    cam.clip_end = 20000
    ob = bpy.data.objects.new(name, cam)
    link(ob)
    ob.location = Vector(loc)
    if target is not None:
        look_at(ob, target)
    elif rot is not None:
        ob.rotation_euler = Euler(rot)
    if fstop:
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
        cam.dof.focus_distance = focus if focus else (Vector(target) - Vector(loc)).length
    bpy.context.scene.camera = ob
    return ob


def look_at(ob, target, roll=0.0):
    d = Vector(target) - ob.location
    q = d.to_track_quat('-Z', 'Y')
    ob.rotation_euler = q.to_euler()
    if roll:
        ob.rotation_euler.rotate_axis('Z', roll)


def sun(name, rot, energy=3.0, color=(1, 1, 1), angle=0.02):
    l = bpy.data.lights.new(name, 'SUN')
    l.energy = energy; l.color = color; l.angle = angle
    ob = bpy.data.objects.new(name, l); link(ob)
    ob.rotation_euler = Euler(rot)
    return ob


def point(name, loc, energy=100, color=(1, 1, 1), radius=0.2):
    l = bpy.data.lights.new(name, 'POINT')
    l.energy = energy; l.color = color; l.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, l); link(ob)
    ob.location = Vector(loc)
    return ob


def area(name, loc, target, energy=100, size=2, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA')
    l.energy = energy; l.size = size; l.color = color
    ob = bpy.data.objects.new(name, l); link(ob)
    ob.location = Vector(loc)
    look_at(ob, target)
    return ob


def sun_dir(elev_deg, azim_deg):
    """Euler for a sun light coming FROM direction (elev, azim) (azim 0 = +X, 90 = +Y)."""
    el = math.radians(elev_deg); az = math.radians(azim_deg)
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    q = (-d).to_track_quat('-Z', 'Y')
    return q.to_euler()


def key_obj(ob, frame, loc=None, rot=None):
    if loc is not None:
        ob.location = Vector(loc); ob.keyframe_insert("location", frame=frame)
    if rot is not None:
        ob.rotation_euler = Euler(rot); ob.keyframe_insert("rotation_euler", frame=frame)


def linear_interp(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    try:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    except AttributeError:
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def screen_bbox(objs, cam, margin=0.04):
    """normalized (xmin, xmax, ymin, ymax) of evaluated objects in camera view."""
    from bpy_extras.object_utils import world_to_camera_view
    s = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    xs, ys = [], []
    for ob in objs:
        ev = ob.evaluated_get(dg)
        mw = ev.matrix_world
        for c in ev.bound_box:
            p = world_to_camera_view(s, cam, mw @ Vector(c))
            if p.z > 0:
                xs.append(p.x); ys.append(p.y)
    if not xs:
        return None
    x0, x1 = max(min(xs) - margin, 0), min(max(xs) + margin, 1)
    y0, y1 = max(min(ys) - margin, 0), min(max(ys) + margin, 1)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, x1, y0, y1


def auto_border(objs, cam, margin=0.04):
    s = bpy.context.scene
    bb = screen_bbox(objs, cam, margin)
    if bb is None:
        s.render.use_border = True
        s.render.border_min_x, s.render.border_max_x, s.render.border_min_y, s.render.border_max_y = 0, 0.01, 0, 0.01
        return 0.0
    s.render.use_border = True
    s.render.use_crop_to_border = False
    s.render.border_min_x, s.render.border_max_x, s.render.border_min_y, s.render.border_max_y = bb
    return (bb[1] - bb[0]) * (bb[3] - bb[2])
