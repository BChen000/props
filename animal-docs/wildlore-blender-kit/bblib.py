"""wildlore-blender-kit / bblib.py: the Blender 4.0 (EEVEE Legacy) toolkit behind the Wildlore "Blue Raspberry" episode.

Units are metres, 24 fps, 1080x1920. Sections, top to bottom:
  render + look     reset, setup_render (AgX Medium High Contrast), compositor, render (mp4), render_still (png)
  world + lights    world_hdri (separate strength/clamp for what the camera sees), world_color, sun, area_light, point_light
  camera + motion   camera (7-blade bokeh), look_at, camera_path, ease, keys, path_keys, driver_expr
  geometry          make_mesh, obj_from_mesh, empty, link, unit_sphere, tube_mesh, catmull, frame_from_normal
  shader nodes      NT (compact node-tree builder), new_mat, principled
  materials         drupelet, berry core, simple, leaf, cane, petal, soil, image, pedicel, sepal, stem, pistil,
                    forest floor, moss, light ray, growth
  the bramble       berry_mesh / make_berry, calyx_mesh, compound_leaf_mesh, flower_mesh, cane_points, make_cane,
                    make_cluster, attach_leaf, make_plant, receptacle_mesh, grow_tube
  forest set        ground, scatter_litter, make_fern, make_trunk, make_rock, scatter_groundcover, god_ray, forest_env
  animals           load_bee (Bee.glb with its hover action), bee_land_switch
Third-party HDRIs, textures and models load from ASSETS (env WILDLORE_ASSETS); get_assets.py downloads them.
"""
import bpy, bmesh, math, random, os, sys
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion

ASSETS = os.environ.get("WILDLORE_ASSETS", "/home/claude/assets")  # third-party HDRIs, textures, models: run get_assets.py
FPS = 24
RES = tuple(int(v) for v in os.environ.get("RES", "1080x1920").split("x"))
GOLDEN = math.pi * (3 - math.sqrt(5))
LEAF_RES = (46, 8)
BERRY_LOD = None  # (N, seg, rings) for non-hero berries
CORE_FACTOR = 0.76  # berry core radius / outer radius (picked berries show it as the hollow); macro shots raise it to fill gaps


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    return sc


def setup_render(sc, frames, out, samples=3, res=RES, motion_blur=False, bloom=False, gtao_dist=0.2,
                 shadow_cube='512', cascade='1024', soft=True, look='AgX - Medium High Contrast', exposure=0.0,
                 still=False, sss_samples=5):
    sc.render.engine = 'BLENDER_EEVEE'
    e = sc.eevee
    e.taa_render_samples = samples
    e.use_soft_shadows = soft
    e.shadow_cube_size = shadow_cube
    e.shadow_cascade_size = cascade
    e.use_shadow_high_bitdepth = True
    e.use_gtao = gtao_dist > 0
    e.gtao_distance = max(gtao_dist, 0.001)
    e.gtao_factor = 1.0
    e.use_bloom = bloom
    e.bloom_threshold = 1.2
    e.bloom_intensity = 0.035
    e.bloom_radius = 5.0
    e.use_ssr = False
    e.use_motion_blur = motion_blur
    e.motion_blur_shutter = 0.5
    e.motion_blur_steps = 1
    e.sss_samples = sss_samples
    e.bokeh_max_size = 60 * res[0] / 720
    e.bokeh_threshold = 4.0
    e.bokeh_neighbor_max = 3.0
    e.use_bokeh_jittered = False
    e.light_threshold = 0.01
    e.gi_cubemap_resolution = '128'
    e.gi_filter_quality = 0.5
    e.gi_diffuse_bounces = 1
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.film_transparent = False
    sc.frame_start = 1
    sc.frame_end = frames
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = look
    except Exception:
        pass
    sc.view_settings.exposure = exposure
    sc.render.use_compositing = True
    if still:
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.compression = 30
    else:
        sc.render.image_settings.file_format = 'FFMPEG'
        ff = sc.render.ffmpeg
        ff.format = 'MPEG4'
        ff.codec = 'H264'
        ff.constant_rate_factor = 'PERC_LOSSLESS'
        ff.ffmpeg_preset = 'GOOD'
        ff.gopsize = 12
        ff.audio_codec = 'NONE'
    sc.render.filepath = out


def world_hdri(sc, name, strength=1.0, cam_strength=None, rot=0.0, tint=(1, 1, 1), sat=1.0, clamp_bg=2.5):
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, rot)
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(ASSETS, "hdri", name), check_existing=True)
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = sat
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = 'MULTIPLY'; mul.inputs["Fac"].default_value = 1.0
    mul.inputs["Color2"].default_value = (*tint, 1)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], mul.inputs["Color1"])
    nt.links.new(mul.outputs["Color"], bg.inputs["Color"])
    if cam_strength is not None:
        bg2 = nt.nodes.new("ShaderNodeBackground"); bg2.inputs["Strength"].default_value = cam_strength
        vm = nt.nodes.new("ShaderNodeVectorMath"); vm.operation = 'MINIMUM'; vm.inputs[1].default_value = (clamp_bg, clamp_bg, clamp_bg)
        nt.links.new(mul.outputs["Color"], vm.inputs[0])
        nt.links.new(vm.outputs[0], bg2.inputs["Color"])
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        nt.links.new(bg.outputs[0], mix.inputs[1])
        nt.links.new(bg2.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(bg.outputs[0], out.inputs["Surface"])
    w["bg_nodes"] = 1
    return w


def world_color(sc, col, strength=1.0):
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*col, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = strength
    return w


def sun(rot, energy=3.0, angle=2.0, color=(1, 0.95, 0.88), cascade_max=10.0, contact=True, name="Sun"):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = energy
    ld.angle = math.radians(angle)
    ld.color = color
    ld.shadow_cascade_max_distance = cascade_max
    ld.shadow_cascade_count = 4
    ld.shadow_cascade_exponent = 0.8
    ld.use_contact_shadow = contact
    ld.contact_shadow_distance = 0.05
    ld.contact_shadow_thickness = 0.005
    ld.shadow_buffer_bias = 0.2
    o = bpy.data.objects.new(name, ld)
    o.rotation_euler = rot
    bpy.context.scene.collection.objects.link(o)
    return o


def area_light(loc, target, size=1.0, energy=50, color=(1, 1, 1), name="Area", spread=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.size = size
    ld.color = color
    ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    look_at(o, target)
    bpy.context.scene.collection.objects.link(o)
    return o


def point_light(loc, energy=10, radius=0.05, color=(1, 1, 1), name="Point"):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.shadow_soft_size = radius
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o


def look_at(o, target, up='Y'):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat('-Z', up).to_euler()


def camera(loc, target, lens=50, fstop=4.0, focus=None, clip=(0.01, 100), name="Cam", blades=7):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.sensor_fit = 'AUTO'
    cd.clip_start, cd.clip_end = clip
    cd.dof.use_dof = fstop is not None
    if fstop:
        cd.dof.aperture_fstop = fstop
        cd.dof.aperture_blades = blades
        cd.dof.aperture_rotation = 0.3
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look_at(o, target)
    if focus is not None:
        if isinstance(focus, bpy.types.Object):
            cd.dof.focus_object = focus
        else:
            cd.dof.focus_distance = focus
    else:
        cd.dof.focus_distance = (Vector(target) - Vector(loc)).length
    bpy.context.scene.camera = o
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    if parent:
        o.parent = parent
    return o


def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


# ---------------------------------------------------------------- animation helpers
def ease(t, kind='inout'):
    t = min(max(t, 0.0), 1.0)
    if kind == 'inout':
        return t * t * (3 - 2 * t)
    if kind == 'inout2':
        return t * t * t * (t * (6 * t - 15) + 10)
    if kind == 'in':
        return t * t
    if kind == 'out':
        return 1 - (1 - t) * (1 - t)
    return t


def keys(obj, path, kv, index=-1, interp='BEZIER', easing='AUTO'):
    """kv: list of (frame, value)"""
    target = obj
    for f, v in kv:
        if index >= 0:
            arr = getattr(target, path)
            arr[index] = v
        else:
            setattr(target, path, v)
        target.keyframe_insert(data_path=path, frame=f, index=index)
    ad = target.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            if fc.data_path == path and (index < 0 or fc.array_index == index):
                for kp in fc.keyframe_points:
                    kp.interpolation = interp
                    if interp == 'BEZIER':
                        kp.handle_left_type = 'AUTO_CLAMPED'
                        kp.handle_right_type = 'AUTO_CLAMPED'
                    else:
                        kp.easing = easing


def path_keys(obj, path, func, f0, f1, step=1, index=-1):
    """bake a python function of frame into linear keyframes"""
    for f in range(f0, f1 + 1, step):
        v = func(f)
        if index >= 0:
            getattr(obj, path)[index] = v
        else:
            setattr(obj, path, v)
        obj.keyframe_insert(data_path=path, frame=f, index=index)
    ad = obj.animation_data
    for fc in ad.action.fcurves:
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def camera_path(cam, f0, f1, pos_fn, tgt_fn, step=1, focus_fn=None):
    for f in range(f0, f1 + 1, step):
        t = (f - f0) / max(1, f1 - f0)
        p = Vector(pos_fn(t))
        cam.location = p
        d = Vector(tgt_fn(t)) - p
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        if focus_fn is not None:
            cam.data.dof.focus_distance = focus_fn(t)
            cam.data.dof.keyframe_insert("focus_distance", frame=f)
    for ad in (cam.animation_data, cam.data.animation_data):
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
    # unwrap euler to avoid flips
    ad = cam.animation_data
    for i in range(3):
        fc = ad.action.fcurves.find("rotation_euler", index=i)
        prev = None
        for kp in fc.keyframe_points:
            v = kp.co[1]
            if prev is not None:
                while v - prev > math.pi:
                    v -= 2 * math.pi
                while v - prev < -math.pi:
                    v += 2 * math.pi
            kp.co[1] = v
            kp.handle_left[1] = v
            kp.handle_right[1] = v
            prev = v


def driver_expr(obj, path, index, expr):
    fc = obj.driver_add(path, index)
    fc.driver.type = 'SCRIPTED'
    fc.driver.expression = expr
    for m in list(fc.modifiers):
        fc.modifiers.remove(m)
    return fc


# ---------------------------------------------------------------- mesh helpers
def make_mesh(name, V, F, uv=None, smooth=True, pattrs=None, cattrs=None, mat_idx=None):
    me = bpy.data.meshes.new(name)
    V = np.asarray(V, dtype=np.float32)
    me.from_pydata(V.tolist(), [], [list(map(int, f)) for f in F])
    if uv is not None:
        ul = me.uv_layers.new(name="UVMap")
        uvarr = np.asarray(uv, dtype=np.float32)  # per vertex uv
        li = np.zeros(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", li)
        ul.data.foreach_set("uv", uvarr[li].ravel())
    if pattrs:
        for k, arr in pattrs.items():
            a = me.attributes.new(k, 'FLOAT', 'POINT')
            a.data.foreach_set("value", np.asarray(arr, dtype=np.float32))
    if cattrs:
        for k, arr in cattrs.items():
            a = me.color_attributes.new(k, 'FLOAT_COLOR', 'POINT')
            arr = np.asarray(arr, dtype=np.float32)
            if arr.shape[1] == 3:
                arr = np.concatenate([arr, np.ones((len(arr), 1), np.float32)], 1)
            a.data.foreach_set("color", arr.ravel())
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", np.asarray(mat_idx, dtype=np.int32))
    me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
    me.update()
    return me


def obj_from_mesh(name, me, mats=(), loc=(0, 0, 0), parent=None, coll=None):
    o = bpy.data.objects.new(name, me)
    for m in mats:
        if m.name not in [x.name for x in me.materials if x]:
            me.materials.append(m)
    o.location = loc
    link(o, coll)
    if parent is not None:
        o.parent = parent
    return o


def unit_sphere(seg=12, rings=8):
    V = []
    F = []
    V.append((0, 0, -1))
    for r in range(1, rings):
        th = math.pi * r / rings - math.pi / 2
        for s in range(seg):
            ph = 2 * math.pi * s / seg
            V.append((math.cos(th) * math.cos(ph), math.cos(th) * math.sin(ph), math.sin(th)))
    V.append((0, 0, 1))
    top = len(V) - 1
    for s in range(seg):
        F.append((0, 1 + (s + 1) % seg, 1 + s))
    for r in range(rings - 2):
        b = 1 + r * seg
        for s in range(seg):
            F.append((b + s, b + (s + 1) % seg, b + seg + (s + 1) % seg, b + seg + s))
    b = 1 + (rings - 2) * seg
    for s in range(seg):
        F.append((b + s, b + (s + 1) % seg, top))
    return np.array(V, np.float32), F


def frame_from_normal(n):
    n = n / np.linalg.norm(n)
    a = np.array([0, 0, 1.0]) if abs(n[2]) < 0.95 else np.array([1.0, 0, 0])
    t1 = np.cross(a, n); t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    return t1, t2, n


def tube_mesh(points, radii, sides=8, close_end=True, uv_len=1.0):
    """points: (n,3), radii (n,). returns V, F, uv"""
    P = np.asarray(points, np.float64)
    n = len(P)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    # parallel transport frames
    a = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N0 = np.cross(T[0], a); N0 /= np.linalg.norm(N0)
    Ns = [N0]
    for i in range(1, n):
        v = Ns[-1] - np.dot(Ns[-1], T[i]) * T[i]
        ln = np.linalg.norm(v)
        Ns.append(v / ln if ln > 1e-9 else Ns[-1])
    Ns = np.array(Ns)
    Bs = np.cross(T, Ns)
    V = []
    UV = []
    seglen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    for i in range(n):
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            V.append(P[i] + radii[i] * (math.cos(ang) * Ns[i] + math.sin(ang) * Bs[i]))
            UV.append((s / sides, seglen[i] * uv_len))
    F = []
    for i in range(n - 1):
        for s in range(sides):
            a0 = i * sides + s
            a1 = i * sides + (s + 1) % sides
            F.append((a0, a1, a1 + sides, a0 + sides))
    if close_end:
        V.append(P[-1] + T[-1] * radii[-1] * 0.5)
        UV.append((0.5, seglen[-1] * uv_len))
        c = len(V) - 1
        b = (n - 1) * sides
        for s in range(sides):
            F.append((b + s, b + (s + 1) % sides, c))
    return np.array(V), F, np.array(UV)


def catmull(pts, samples_per_seg=8):
    P = [np.asarray(p, np.float64) for p in pts]
    P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(samples_per_seg):
            t = j / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


# ---------------------------------------------------------------- node helpers
class NT:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.n = self.nt.nodes
        self.l = self.nt.links

    def new(self, typ, **kw):
        nd = self.n.new(typ)
        for k, v in kw.items():
            if k.startswith("i_"):
                nd.inputs[k[2:].replace("_", " ")].default_value = v
            else:
                setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.l.new(a, b)

    def math(self, op, a, b=None, c=None, clamp=False):
        m = self.n.new("ShaderNodeMath")
        m.operation = op
        m.use_clamp = bool(clamp)
        for i, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                m.inputs[i].default_value = x
            else:
                self.l.new(x, m.inputs[i])
        return m.outputs[0]

    def mix(self, fac, c1, c2, blend='MIX'):
        m = self.n.new("ShaderNodeMixRGB")
        m.blend_type = blend
        for sock, x in ((m.inputs["Fac"], fac), (m.inputs["Color1"], c1), (m.inputs["Color2"], c2)):
            if isinstance(x, (int, float)):
                sock.default_value = x
            elif isinstance(x, tuple):
                sock.default_value = x if len(x) == 4 else (*x, 1)
            else:
                self.l.new(x, sock)
        return m.outputs[0]

    def ramp(self, fac, stops, interp='LINEAR'):
        r = self.n.new("ShaderNodeValToRGB")
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        for i, (p, c) in enumerate(stops):
            e = els[0] if i == 0 else els.new(p)
            e.position = p
            e.color = c if len(c) == 4 else (*c, 1)
        self.l.new(fac, r.inputs[0])
        return r.outputs[0]

    def noise(self, vec=None, scale=5.0, detail=4.0, rough=0.5, dist=0.0, dims='3D'):
        nz = self.n.new("ShaderNodeTexNoise")
        nz.noise_dimensions = dims
        nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = detail
        nz.inputs["Roughness"].default_value = rough
        nz.inputs["Distortion"].default_value = dist
        if vec is not None:
            self.l.new(vec, nz.inputs["Vector"])
        return nz

    def voronoi(self, vec=None, scale=5.0, feature='F1', dims='3D', dist_metric='EUCLIDEAN'):
        v = self.n.new("ShaderNodeTexVoronoi")
        v.voronoi_dimensions = dims
        v.feature = feature
        v.distance = dist_metric
        v.inputs["Scale"].default_value = scale
        if vec is not None:
            self.l.new(vec, v.inputs["Vector"])
        return v

    def attr(self, name, kind='GEOMETRY'):
        a = self.n.new("ShaderNodeAttribute")
        a.attribute_name = name
        a.attribute_type = kind
        return a

    def bump(self, height, strength=0.5, distance=0.01, normal=None):
        b = self.n.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = distance
        self.l.new(height, b.inputs["Height"])
        if normal is not None:
            self.l.new(normal, b.inputs["Normal"])
        return b.outputs[0]

    def texcoord(self):
        return self.n.new("ShaderNodeTexCoord")

    def image(self, path, vec=None, colorspace='sRGB', interp='Linear', ext='REPEAT'):
        t = self.n.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        t.image.colorspace_settings.name = colorspace
        t.interpolation = interp
        t.extension = ext
        if vec is not None:
            self.l.new(vec, t.inputs["Vector"])
        return t

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
        m = self.n.new("ShaderNodeMapping")
        m.inputs["Scale"].default_value = scale
        m.inputs["Location"].default_value = loc
        m.inputs["Rotation"].default_value = rot
        self.l.new(vec, m.inputs["Vector"])
        return m.outputs[0]


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, NT(m)


def principled(nt, **kw):
    p = nt.n["Principled BSDF"]
    for k, v in kw.items():
        key = k.replace("_", " ")
        if isinstance(v, bpy.types.NodeSocket):
            nt.link(v, p.inputs[key])
        else:
            p.inputs[key].default_value = v
    return p


# ---------------------------------------------------------------- materials
_MATS = {}


def mat_drupelet(name="Drupelet", hue_shift=0.0):
    """Blue raspberry drupelet. object color: R = ripeness (0 green .. 1 blue), G = random"""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    m.use_sss_translucency = True
    oi = nt.new("ShaderNodeObjectInfo")
    sep = nt.new("ShaderNodeSeparateColor")
    nt.link(oi.outputs["Color"], sep.inputs[0])
    ripe = sep.outputs[0]
    dr = nt.attr("drup").outputs["Fac"]
    rnd = nt.math('ADD', dr, oi.outputs["Random"])
    rnd = nt.math('FRACT', rnd)
    # base colour by ripeness
    col_ripe = nt.ramp(ripe, [(0.0, (0.30, 0.45, 0.06)), (0.35, (0.45, 0.55, 0.30)), (0.6, (0.20, 0.42, 0.62)),
                              (0.82, (0.02, 0.09, 0.62)), (1.0, (0.012, 0.05, 0.50))])
    var = nt.ramp(rnd, [(0.0, (0.72, 0.82, 1.0)), (0.35, (1, 1, 1)), (0.7, (1.35, 0.92, 0.88)), (1.0, (0.82, 1.15, 1.12))])
    base = nt.mix(1.0, col_ripe, var, 'MULTIPLY')
    # radial darkening between drupelets via pointiness-like attribute "edge"
    ed = nt.attr("edge").outputs["Fac"]
    dark = nt.ramp(ed, [(0.0, (0.22, 0.16, 0.42)), (0.6, (1, 1, 1))])
    base = nt.mix(1.0, base, dark, 'MULTIPLY')
    # waxy bloom, like a blueberry's: a pale dusty film, patchy, strongest where the surface turns away
    tc = nt.texcoord()
    lw = nt.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.45
    bn = nt.noise(tc.outputs["Object"], scale=160.0, detail=3.0, rough=0.6)
    patch = nt.math('MULTIPLY', nt.math('SUBTRACT', bn.outputs["Fac"], 0.32), 2.2, clamp=True)
    bloom = nt.math('MULTIPLY', nt.math('ADD', 0.25, nt.math('MULTIPLY', patch, 0.75)),
                    nt.math('ADD', 0.35, nt.math('MULTIPLY', lw.outputs["Facing"], 0.65)))
    bloom = nt.math('MULTIPLY', bloom, nt.math('MULTIPLY', ripe, 0.62))
    base = nt.mix(nt.math('MULTIPLY', bloom, 0.20), base, (0.16, 0.24, 0.56, 1))
    rough = nt.math('ADD', 0.22, nt.math('MULTIPLY', bloom, 0.25))
    p = principled(nt, Base_Color=base, Roughness=rough, Subsurface_Weight=0.6,
                   Subsurface_Radius=(0.3, 0.6, 1.0), Subsurface_Scale=0.004,
                   Specular_IOR_Level=0.5, Coat_Weight=0.3, Coat_Roughness=0.07,
                   Sheen_Weight=0.10, Sheen_Roughness=0.45, Sheen_Tint=(0.70, 0.80, 1.0, 1))
    # fine surface cells bump
    vor = nt.voronoi(tc.outputs["Object"], scale=900.0)
    nz = nt.noise(tc.outputs["Object"], scale=400.0, detail=2)
    h = nt.math('ADD', vor.outputs["Distance"], nt.math('MULTIPLY', nz.outputs["Fac"], 0.4))
    nt.link(nt.bump(h, 0.06, 0.0002), p.inputs["Normal"])
    _MATS[name] = m
    return m


def mat_berry_core(name="BerryCore"):
    """inside of a picked berry: matte, dark violet-blue, pitted where the drupelets sat on the receptacle"""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    vor = nt.voronoi(tc.outputs["Object"], scale=320.0)
    pit = nt.math('POWER', vor.outputs["Distance"], 0.7)
    c = nt.mix(pit, (0.035, 0.03, 0.11, 1), (0.07, 0.065, 0.19, 1))
    p = principled(nt, Base_Color=c, Roughness=0.85, Specular_IOR_Level=0.2)
    nt.link(nt.bump(pit, 0.6, 0.0004), p.inputs["Normal"])
    _MATS[name] = m
    return m


def mat_simple(name, color, rough=0.5, sss=0.0, sss_r=(1, 0.5, 0.3), sss_scale=0.01, spec=0.5, emission=None,
               emit_strength=0.0, metallic=0.0, transl=0.0):
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    p = principled(nt, Base_Color=(*color, 1), Roughness=rough, Subsurface_Weight=sss, Subsurface_Radius=sss_r,
                   Subsurface_Scale=sss_scale, Specular_IOR_Level=spec, Metallic=metallic)
    if emission is not None:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    if transl > 0:
        out = nt.n["Material Output"]
        tr = nt.new("ShaderNodeBsdfTranslucent")
        tr.inputs["Color"].default_value = (*color, 1)
        mx = nt.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = transl
        nt.link(p.outputs[0], mx.inputs[1]); nt.link(tr.outputs[0], mx.inputs[2])
        nt.link(mx.outputs[0], out.inputs["Surface"])
    if sss > 0:
        m.use_sss_translucency = True
    _MATS[name] = m
    return m


def mat_leaf(name="Leaf", top=(0.035, 0.13, 0.025), under=(0.30, 0.38, 0.28), autumn=False, rough=0.42, spec=0.45, bump_dist=0.0015):
    """leaflet uv: u along midrib 0..1, v across -1..1 (stored in uv.y*2-1). object color R = health (1 green, 0 brown)"""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    uvn = nt.new("ShaderNodeUVMap"); uvn.uv_map = "UVMap"
    sep = nt.new("ShaderNodeSeparateXYZ"); nt.link(uvn.outputs[0], sep.inputs[0])
    u = sep.outputs["X"]
    v = nt.math('SUBTRACT', nt.math('MULTIPLY', sep.outputs["Y"], 2.0), 1.0)
    av = nt.math('ABSOLUTE', v)
    # secondary veins: lines along u*N + |v|*k
    x = nt.math('ADD', nt.math('MULTIPLY', u, 9.0), nt.math('MULTIPLY', av, -2.2))
    d = nt.math('ABSOLUTE', nt.math('SUBTRACT', nt.math('FRACT', x), 0.5))  # 0.5 at vein, 0 mid
    vein = nt.math('MINIMUM', 1.0, nt.math('MULTIPLY', nt.math('MAXIMUM', nt.math('SUBTRACT', d, 0.43), 0.0), 16.0))
    fade = nt.math('SUBTRACT', 1.0, nt.math('POWER', av, 3.0))
    vein = nt.math('MULTIPLY', vein, fade)
    mid = nt.math('SUBTRACT', 1.0, nt.math('MULTIPLY', av, 18.0), clamp=True)
    veins = nt.math('MAXIMUM', vein, mid)
    # tertiary net
    tc = nt.texcoord()
    vor = nt.voronoi(tc.outputs["UV"], scale=55.0, feature='DISTANCE_TO_EDGE')
    net = nt.math('SUBTRACT', 1.0, nt.math('MULTIPLY', vor.outputs["Distance"], 14.0), clamp=True)
    oi = nt.new("ShaderNodeObjectInfo")
    sepc = nt.new("ShaderNodeSeparateColor"); nt.link(oi.outputs["Color"], sepc.inputs[0])
    health = sepc.outputs[0]
    nz = nt.noise(tc.outputs["UV"], scale=6.0, detail=3)
    topc = nt.mix(nt.math('MULTIPLY', nz.outputs["Fac"], 0.5), (*top, 1), (top[0] * 1.6, top[1] * 1.3, top[2] * 0.8, 1))
    topc = nt.mix(nt.math('MULTIPLY', veins, 0.55), topc, (0.16, 0.30, 0.06, 1))
    rnd = nt.ramp(oi.outputs["Random"], [(0, (0.8, 0.85, 0.8)), (1, (1.15, 1.1, 0.95))])
    topc = nt.mix(1.0, topc, rnd, 'MULTIPLY')
    dead = nt.mix(nz.outputs["Fac"], (0.20, 0.09, 0.025, 1), (0.42, 0.25, 0.07, 1))
    topc = nt.mix(nt.math('SUBTRACT', 1.0, health), topc, dead)
    geo = nt.new("ShaderNodeNewGeometry")
    underc = nt.mix(nt.math('MULTIPLY', veins, 0.4), (*under, 1), (0.45, 0.5, 0.35, 1))
    underc = nt.mix(nt.math('SUBTRACT', 1.0, health), underc, dead)
    col = nt.mix(geo.outputs["Backfacing"], topc, underc)
    h = nt.math('ADD', nt.math('MULTIPLY', veins, -1.0), nt.math('MULTIPLY', net, -0.25))
    h = nt.math('ADD', h, nt.math('MULTIPLY', nz.outputs["Fac"], 0.3))
    p = principled(nt, Base_Color=col, Roughness=rough, Specular_IOR_Level=spec, Sheen_Weight=0.0)
    nt.link(nt.bump(h, 0.35, bump_dist), p.inputs["Normal"])
    # translucency
    tr = nt.new("ShaderNodeBsdfTranslucent")
    trc = nt.mix(1.0, col, (1.4, 1.6, 0.6, 1), 'MULTIPLY')
    nt.link(trc, tr.inputs["Color"])
    mx = nt.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.15
    nt.link(p.outputs[0], mx.inputs[1]); nt.link(tr.outputs[0], mx.inputs[2])
    nt.link(mx.outputs[0], nt.n["Material Output"].inputs["Surface"])
    m.use_backface_culling = False
    _MATS[name] = m
    return m


def mat_cane(name="Cane"):
    """uv.y along length (meters). object color R = age (0 green young, 1 brown woody), G = dieback (1 dead)"""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    oi = nt.new("ShaderNodeObjectInfo")
    sepc = nt.new("ShaderNodeSeparateColor"); nt.link(oi.outputs["Color"], sepc.inputs[0])
    nz = nt.noise(tc.outputs["Object"], scale=60.0, detail=5)
    n2 = nt.noise(nt.mapping(tc.outputs["Object"], scale=(4, 4, 40)), scale=30.0, detail=6)
    young = nt.mix(n2.outputs["Fac"], (0.09, 0.15, 0.045, 1), (0.16, 0.11, 0.06, 1))
    old = nt.mix(n2.outputs["Fac"], (0.13, 0.06, 0.04, 1), (0.22, 0.12, 0.07, 1))
    c = nt.mix(sepc.outputs[0], young, old)
    dead = nt.mix(nz.outputs["Fac"], (0.25, 0.18, 0.12, 1), (0.40, 0.31, 0.22, 1))
    c = nt.mix(sepc.outputs[1], c, dead)
    # whitish bloom streaks
    st = nt.noise(nt.mapping(tc.outputs["Object"], scale=(30, 30, 3)), scale=8.0, detail=2)
    bloom = nt.math('MULTIPLY', nt.math('SUBTRACT', st.outputs["Fac"], 0.55, clamp=True), 0.5)
    c = nt.mix(bloom, c, (0.30, 0.28, 0.30, 1))
    p = principled(nt, Base_Color=c, Roughness=0.62, Specular_IOR_Level=0.3)
    nt.link(nt.bump(nt.math('ADD', nz.outputs["Fac"], n2.outputs["Fac"]), 0.5, 0.0005), p.inputs["Normal"])
    _MATS[name] = m
    return m


def mat_petal(name="Petal"):
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    uvn = nt.new("ShaderNodeUVMap")
    sep = nt.new("ShaderNodeSeparateXYZ"); nt.link(uvn.outputs[0], sep.inputs[0])
    # faint veins running from the base out to the margin (along the petal), irregular like real petals
    w = nt.new("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Y')
    w.inputs["Scale"].default_value = 3.4
    w.inputs["Distortion"].default_value = 2.2
    w.inputs["Detail"].default_value = 1.5
    w.inputs["Detail Scale"].default_value = 1.2
    nt.link(uvn.outputs[0], w.inputs["Vector"])
    vein = nt.math('POWER', w.outputs["Fac"], 3.0)
    base = nt.mix(nt.math('MULTIPLY', vein, 0.10), (0.93, 0.935, 0.89, 1), (0.84, 0.87, 0.79, 1))
    basec = nt.mix(nt.math('SUBTRACT', 1.0, nt.math('MULTIPLY', sep.outputs["X"], 5.0), clamp=True), base, (0.75, 0.85, 0.55, 1))
    p = principled(nt, Base_Color=basec, Roughness=0.40, Subsurface_Weight=0.25, Subsurface_Radius=(1, 1, 1),
                   Subsurface_Scale=0.002, Specular_IOR_Level=0.35)
    nz = nt.noise(uvn.outputs[0], scale=24.0, detail=2.0)
    h = nt.math('ADD', nt.math('MULTIPLY', vein, 0.5), nt.math('MULTIPLY', nz.outputs["Fac"], 0.5))
    nt.link(nt.bump(h, 0.05, 0.0002), p.inputs["Normal"])
    tr = nt.new("ShaderNodeBsdfTranslucent")
    nt.link(basec, tr.inputs["Color"])
    mx = nt.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 0.35
    nt.link(p.outputs[0], mx.inputs[1]); nt.link(tr.outputs[0], mx.inputs[2])
    nt.link(mx.outputs[0], nt.n["Material Output"].inputs["Surface"])
    m.use_backface_culling = False
    m.use_sss_translucency = True
    _MATS[name] = m
    return m


def mat_soil(name="Soil", scale=1.0, wet=0.0):
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    co = nt.mapping(tc.outputs["Object"], scale=(scale,) * 3)
    n1 = nt.noise(co, scale=3.0, detail=8, rough=0.6)
    n2 = nt.noise(co, scale=40.0, detail=4, rough=0.6)
    vor = nt.voronoi(co, scale=25.0)
    c = nt.mix(n1.outputs["Fac"], (0.05, 0.032, 0.02, 1), (0.13, 0.085, 0.05, 1))
    c = nt.mix(nt.math('MULTIPLY', nt.math('SUBTRACT', 1.0, vor.outputs["Distance"], clamp=True), 0.35), c, (0.18, 0.13, 0.09, 1))
    h = nt.math('ADD', n2.outputs["Fac"], nt.math('MULTIPLY', vor.outputs["Distance"], -0.6))
    p = principled(nt, Base_Color=c, Roughness=0.85 - 0.4 * wet, Specular_IOR_Level=0.3)
    nt.link(nt.bump(h, 0.6, 0.004), p.inputs["Normal"])
    _MATS[name] = m
    return m


def mat_image(name, color_path, normal_path=None, scale=1.0, rough=0.7, tint=(1, 1, 1), uv='UV', nstrength=1.0,
              rough_path=None):
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    vec = nt.mapping(tc.outputs[uv], scale=(scale, scale, scale))
    ct = nt.image(color_path, vec)
    c = nt.mix(1.0, ct.outputs["Color"], (*tint, 1), 'MULTIPLY')
    p = principled(nt, Base_Color=c, Roughness=rough, Specular_IOR_Level=0.35)
    if rough_path:
        rt = nt.image(rough_path, vec, colorspace='Non-Color')
        nt.link(rt.outputs["Color"], p.inputs["Roughness"])
    if normal_path:
        nimg = nt.image(normal_path, vec, colorspace='Non-Color')
        nm = nt.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstrength
        nt.link(nimg.outputs["Color"], nm.inputs["Color"])
        nt.link(nm.outputs[0], p.inputs["Normal"])
    _MATS[name] = m
    return m


# ---------------------------------------------------------------- berry
def berry_profile(t, R, H):
    return R * (np.clip(1 - t ** 2.3, 0, 1) ** 0.55) * (1 + 0.06 * np.sin(np.pi * t))


_BERRY_MESH = {}


def berry_mesh(N=80, R=0.0085, H=0.019, seg=10, rings=7, seed=1, hairs=False, core=True, name=None):
    key = (N, R, H, seg, rings, seed, hairs, core, CORE_FACTOR)
    if key in _BERRY_MESH:
        return _BERRY_MESH[key]
    rng = np.random.default_rng(seed)
    # area cdf along z
    zs = np.linspace(0, H, 400)
    t = zs / H
    r = berry_profile(t, R, H)
    dr = np.gradient(r, zs)
    dA = 2 * np.pi * r * np.sqrt(1 + dr ** 2)
    cdf = np.concatenate([[0], np.cumsum((dA[1:] + dA[:-1]) / 2 * np.diff(zs))])
    A = cdf[-1]
    d = math.sqrt(A / N)
    us, uf = unit_sphere(seg, rings)
    V = []; F = []; drup = []; edge = []
    centers = []; normals = []
    for i in range(N):
        s = (i + 0.5) / N
        z = float(np.interp(s * A, cdf, zs))
        z = min(max(z, 0.06 * H), 0.985 * H)
        rz = float(np.interp(z, zs, r))
        drz = float(np.interp(z, zs, dr))
        ph = i * GOLDEN + rng.normal(0, 0.05)
        nrm = np.array([math.cos(ph), math.sin(ph), -drz]); nrm /= np.linalg.norm(nrm)
        c = np.array([rz * math.cos(ph), rz * math.sin(ph), z])
        sz = d * rng.uniform(0.86, 1.12)
        ra = 0.68 * sz
        rn = 0.52 * sz
        t1, t2, n = frame_from_normal(nrm)
        c2 = c + n * (0.08 * sz)
        loc = us.copy()
        # slight point at apex
        loc[:, 2] = loc[:, 2] + 0.10 * np.clip(loc[:, 2], 0, 1) ** 6
        sq = rng.uniform(0.85, 1.15)
        P = c2 + np.outer(loc[:, 0] * ra * sq, t1) + np.outer(loc[:, 1] * ra / sq, t2) + np.outer(loc[:, 2] * rn * rng.uniform(0.9, 1.1), n)
        base = len(V)
        V.extend(P.tolist())
        F.extend([[base + k for k in f] for f in uf])
        rv = rng.random()
        drup.extend([rv] * len(P))
        edge.extend(np.clip(loc[:, 2] * 0.5 + 0.5, 0, 1).tolist())
        centers.append(c2); normals.append(n)
    core_f0 = core_f1 = len(F)
    if core:
        nz_ = 24; nseg = 20
        base = len(V)
        core_f0 = len(F)
        for k in range(nz_ + 1):
            z = H * 0.02 + (H * 0.99 - H * 0.02) * k / nz_
            rz = float(np.interp(z, zs, r)) * (CORE_FACTOR - 0.2 * max(0.0, (z / H - 0.6) / 0.4))
            for s in range(nseg):
                ph = 2 * math.pi * s / nseg
                V.append([rz * math.cos(ph), rz * math.sin(ph), z])
                drup.append(0.5); edge.append(0.0)
        for k in range(nz_):
            for s in range(nseg):
                a = base + k * nseg + s
                b = base + k * nseg + (s + 1) % nseg
                F.append([a, a + nseg, b + nseg, b])
        tip = len(V); V.append([0, 0, H * 0.995]); drup.append(0.5); edge.append(0.0)
        lb = base + nz_ * nseg
        for s in range(nseg):
            F.append([lb + s, tip, lb + (s + 1) % nseg])
        core_f1 = len(F)
    nonhair = len(F)
    hair_faces = 0
    if hairs:
        for c, n in zip(centers, normals):
            if rng.random() < 0.3:
                L = d * rng.uniform(0.25, 0.55)
                bend = rng.normal(0, 0.35, 3)
                p0 = c + n * (0.5 * d)
                pts = [p0, p0 + (n + bend * 0.3) * L * 0.5, p0 + (n + bend) / np.linalg.norm(n + bend) * L]
                tv, tf, _ = tube_mesh(np.array(pts), np.array([0.012, 0.008, 0.004]) * d * 1.0, sides=3, close_end=False)
                base = len(V)
                V.extend(tv.tolist())
                F.extend([[base + k for k in f] for f in tf])
                hair_faces += len(tf)
                drup.extend([-1.0] * len(tv)); edge.extend([1.0] * len(tv))
    mi = [0] * nonhair + [1] * (len(F) - nonhair)
    if core:
        for k in range(core_f0, core_f1):
            mi[k] = 2
    me = make_mesh(name or "berry", V, F, pattrs={"drup": drup, "edge": edge}, smooth=True, mat_idx=mi)
    me["d"] = d
    _BERRY_MESH[key] = me
    return me


def calyx_mesh(R=0.0085, n=5, seed=2, stem_len=0.012, stem_r=0.0009, name="calyx"):
    """sepals around origin pointing outward/back toward -z (berry grows along +z). stem along -z."""
    rng = np.random.default_rng(seed)
    V = []; F = []; UV = []
    for i in range(n):
        ph = 2 * math.pi * i / n + rng.normal(0, 0.15)
        L = R * rng.uniform(0.9, 1.2)
        W = R * 0.45
        rows = 6
        base = len(V)
        for k in range(rows + 1):
            s = k / rows
            w = W * (1 - s) ** 0.8 * (0.6 + 0.4 * math.sin(math.pi * min(1, s + 0.2)))
            # sepal goes outward and curls back (toward -z)
            rad = R * 0.35 + L * s
            zz = -L * 0.55 * s * s + R * 0.05
            for j, sgn in enumerate((-1, 0, 1)):
                tang = np.array([-math.sin(ph), math.cos(ph), 0])
                radial = np.array([math.cos(ph), math.sin(ph), 0])
                p = radial * rad + tang * w * sgn + np.array([0, 0, zz + (0.15 * W * (1 - abs(sgn)))])
                V.append(p.tolist()); UV.append((s, (sgn + 1) / 2))
        for k in range(rows):
            for j in range(2):
                a = base + k * 3 + j
                F.append([a, a + 1, a + 4, a + 3])
    # calyx base: a shallow green dome that closes the top of the fruit around the stalk
    nr, ns = 5, 20
    dbase = len(V)
    V.append([0.0, 0.0, -0.035 * R]); UV.append((0.0, 0.5))
    for k in range(1, nr + 1):
        rr = 0.80 * R * k / nr
        zz = -0.035 * R * (1 - (k / nr) ** 2) + 0.03 * R * (k / nr) ** 3
        for s_ in range(ns):
            a = 2 * math.pi * s_ / ns
            V.append([rr * math.cos(a), rr * math.sin(a), zz]); UV.append((0.0, 0.5))
    for s_ in range(ns):
        F.append([dbase, dbase + 1 + (s_ + 1) % ns, dbase + 1 + s_])
    for k in range(nr - 1):
        b0 = dbase + 1 + k * ns; b1 = b0 + ns
        for s_ in range(ns):
            F.append([b0 + s_, b0 + (s_ + 1) % ns, b1 + (s_ + 1) % ns, b1 + s_])
    # stem
    pts = np.array([[0, 0, R * 0.1], [0, 0, -stem_len * 0.5], [0, 0, -stem_len]])
    tv, tf, tuv = tube_mesh(pts, np.array([stem_r * 1.4, stem_r, stem_r]), sides=6, close_end=False)
    base = len(V)
    V.extend(tv.tolist()); UV.extend(tuv.tolist())
    F.extend([[base + k for k in f] for f in tf])
    nsep = base
    me = make_mesh(name, V, F, uv=UV, mat_idx=[0] * (len(F) - len(tf)) + [1] * len(tf))
    return me



def mat_pedicel():
    if "Pedicel" in _MATS:
        return _MATS["Pedicel"]
    m, nt = new_mat("Pedicel")
    tc = nt.texcoord()
    nz = nt.noise(tc.outputs["Object"], scale=300.0, detail=2)
    c = nt.mix(nz.outputs["Fac"], (0.05, 0.08, 0.02, 1), (0.10, 0.07, 0.03, 1))
    principled(nt, Base_Color=c, Roughness=0.55, Sheen_Weight=0.6, Sheen_Tint=(0.8, 0.85, 0.7, 1), Specular_IOR_Level=0.35)
    _MATS["Pedicel"] = m
    return m


def mat_sepal():
    return mat_simple("Sepal", (0.12, 0.22, 0.05), rough=0.55, transl=0.15)


def mat_stem():
    return mat_cane("Cane")


def make_berry(name, ripeness=1.0, scale=1.0, hero=False, seed=1, parent=None, loc=(0, 0, 0), rot=(0, 0, 0),
               calyx=True, stem_len=0.012, N=None, seg=None, rings=None):
    """creates berry object whose local +z points from attachment toward tip. returns root empty-like object (calyx)"""
    me = berry_mesh(N=N or (95 if hero else 70), seg=seg or (14 if hero else 9), rings=rings or (10 if hero else 6), seed=seed % 4 + 1, hairs=hero)
    root = bpy.data.objects.new(name, calyx_mesh(stem_len=stem_len, seed=seed) if calyx else None)
    if calyx:
        root.data.materials.append(mat_sepal())
        root.data.materials.append(mat_pedicel())
    link(root)
    root.location = loc
    root.rotation_euler = rot
    root.scale = (scale,) * 3
    if parent:
        root.parent = parent
    b = bpy.data.objects.new(name + "_fruit", me)
    if not me.materials:
        me.materials.append(mat_drupelet())
        me.materials.append(mat_simple("BerryHair", (0.38, 0.42, 0.55), rough=0.4, transl=0.5))
        me.materials.append(mat_berry_core())
    link(b)
    b.parent = root
    b.color = (ripeness, random.random(), 0, 1)
    root.color = (0.3, 0, 0, 1)
    return root, b


# ---------------------------------------------------------------- leaves
_LEAF_MESH = {}


def leaflet_geom(L=0.07, W=0.03, rows=46, cols=8, teeth=17, fold=0.25, arch=0.18, seed=0, twist=0.0):
    rng = np.random.default_rng(seed)
    V = []; UV = []
    for k in range(rows + 1):
        s = k / rows
        w = W * (math.sin(math.pi * min(1.0, s ** 0.72)) ** 0.85)
        if s > 0.82:
            w *= (1 - s) / 0.18 * 0.85 + 0.15 * ((1 - s) / 0.18) ** 3
        # serration (doubly)
        x = s * teeth
        tooth = (x - math.floor(x)) ** 2.2
        x2 = s * teeth * 2
        tooth2 = (x2 - math.floor(x2)) ** 2
        ws = w * (1 + 0.075 * tooth + 0.03 * tooth2) if 0.05 < s < 0.97 else w
        for j in range(cols + 1):
            v = -1 + 2 * j / cols
            xx = v * ws
            yy = s * L
            zz = fold * abs(v) * ws - arch * L * s * s
            zz += 0.0012 * math.sin(s * 23 + v * 3 + seed) * (abs(v))
            # twist
            ang = twist * s
            xx2 = xx * math.cos(ang) - zz * math.sin(ang)
            zz2 = xx * math.sin(ang) + zz * math.cos(ang)
            V.append((xx2, yy, zz2))
            UV.append((s, (v + 1) / 2))
    F = []
    for k in range(rows):
        for j in range(cols):
            a = k * (cols + 1) + j
            F.append([a, a + 1, a + cols + 2, a + cols + 1])
    return np.array(V), F, np.array(UV)


def compound_leaf_mesh(variant=0, n_leaflets=3, size=1.0, name="leaf"):
    key = (variant, n_leaflets, size, LEAF_RES)
    if key in _LEAF_MESH:
        return _LEAF_MESH[key]
    rng = np.random.default_rng(variant + 10)
    V = []; F = []; UV = []; MI = []
    petiole = 0.045 * size
    rachis = 0.025 * size if n_leaflets > 1 else 0.0

    def add(v, f, uv, mi, M):
        base = len(V)
        vv = (np.array(M) @ np.c_[v, np.ones(len(v))].T).T[:, :3]
        V.extend(vv.tolist()); UV.extend(uv.tolist())
        F.extend([[base + k for k in ff] for ff in f]); MI.extend([mi] * len(f))

    # petiole along +y from origin, slight up curve
    pts = np.array([[0, 0, 0], [0, petiole * 0.5, 0.004 * size], [0, petiole + rachis, 0.005 * size]])
    tv, tf, tuv = tube_mesh(pts, np.array([0.0012, 0.001, 0.0008]) * size, sides=5, close_end=False)
    add(tv, tf, tuv * 0.0 + 0.5, 1, Matrix.Identity(4))
    tipy = petiole + rachis
    # terminal
    lv, lf, luv = leaflet_geom(L=0.075 * size * rng.uniform(0.9, 1.1), W=0.032 * size, seed=variant, twist=rng.normal(0, 0.15),
                               arch=rng.uniform(0.12, 0.25), rows=LEAF_RES[0], cols=LEAF_RES[1])
    M = Matrix.Translation((0, tipy, 0.005 * size)) @ Matrix.Rotation(rng.normal(0, 0.08), 4, 'Z')
    add(lv, lf, luv, 0, M)
    pairs = [(petiole + rachis * 0.0, 0.85)] if n_leaflets >= 3 else []
    if n_leaflets >= 5:
        pairs = [(petiole + rachis * 0.0, 0.8), (petiole * 0.72, 0.6)]
    for (py, sc_) in pairs:
        for sgn in (-1, 1):
            lv, lf, luv = leaflet_geom(L=0.062 * size * sc_ * rng.uniform(0.9, 1.1), W=0.028 * size * sc_, seed=variant + 3 + sgn,
                                       twist=rng.normal(0, 0.15), arch=rng.uniform(0.1, 0.22), rows=LEAF_RES[0], cols=LEAF_RES[1])
            M = Matrix.Translation((0, py, 0.004 * size)) @ Matrix.Rotation(sgn * -math.radians(rng.uniform(55, 75)), 4, 'Z') @ \
                Matrix.Rotation(math.radians(sgn * 6), 4, 'Y')
            add(lv, lf, luv, 0, M)
    me = make_mesh(name + str(variant), V, F, uv=UV, mat_idx=MI)
    me.materials.append(mat_leaf())
    me.materials.append(mat_cane())
    _LEAF_MESH[key] = me
    return me


# ---------------------------------------------------------------- flower
_FLOWER_MESH = {}


def mat_pistil(name="Pistil"):
    """the flower's green centre: a tight cluster of tiny pistils rather than a smooth ball"""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    vor = nt.voronoi(tc.outputs["Object"], scale=2600.0)
    bumpy = nt.math('POWER', nt.math('SUBTRACT', 1.0, nt.math('MINIMUM', 1.0, nt.math('MULTIPLY', vor.outputs["Distance"], 1.6))), 0.6)
    c = nt.mix(bumpy, (0.22, 0.40, 0.11, 1), (0.40, 0.60, 0.20, 1))
    p = principled(nt, Base_Color=c, Roughness=0.5, Subsurface_Weight=0.2, Subsurface_Radius=(0.5, 1, 0.3), Subsurface_Scale=0.001,
                   Specular_IOR_Level=0.35)
    nt.link(nt.bump(bumpy, 0.7, 0.00025), p.inputs["Normal"])
    m.use_sss_translucency = True
    _MATS[name] = m
    return m


def flower_mesh(open_amt=1.0, variant=0, size=1.0):
    key = (round(open_amt, 2), variant, size)
    if key in _FLOWER_MESH:
        return _FLOWER_MESH[key]
    rng = np.random.default_rng(variant + 50)
    V = []; F = []; UV = []; MI = []

    def add(v, f, uv, mi):
        base = len(V)
        V.extend(np.asarray(v).tolist()); UV.extend(np.asarray(uv).tolist())
        F.extend([[base + k for k in ff] for ff in f]); MI.extend([mi] * len(f))

    R = 0.011 * size  # petal length
    # petals: 5, flower faces +z (same surface as before, sampled finer, with a gentle crinkle at the margin)
    for i in range(5):
        ph = 2 * math.pi * i / 5 + rng.normal(0, 0.06)
        rows, cols = 16, 10
        pv = []; puv = []
        L = R * rng.uniform(0.9, 1.05)
        Wd = R * 0.42
        lift = (1 - open_amt) * 1.3 + 0.18
        cph = rng.uniform(0, 2 * math.pi)
        for k in range(rows + 1):
            s = k / rows
            w = Wd * (0.35 + 0.65 * math.sin(math.pi * min(1, s * 0.85 + 0.12)) ** 0.7)
            for j in range(cols + 1):
                v = -1 + 2 * j / cols
                rad = 0.0018 * size + L * s * math.cos(lift * s)
                zz = L * s * math.sin(lift * s) + 0.25 * Wd * v * v * (0.3 + s)  # cupped
                zz += 0.045 * Wd * math.sin(3.0 * math.pi * v + cph) * s ** 3  # crinkled margin
                tang = w * v
                x = rad * math.cos(ph) - tang * math.sin(ph)
                y = rad * math.sin(ph) + tang * math.cos(ph)
                pv.append((x, y, zz + 0.0006 * size)); puv.append((s, (v + 1) / 2))
        pf = []
        for k in range(rows):
            for j in range(cols):
                a = k * (cols + 1) + j
                pf.append([a, a + 1, a + cols + 2, a + cols + 1])
        add(pv, pf, puv, 0)
    # sepals (behind petals, pointing back)
    for i in range(5):
        ph = 2 * math.pi * (i + 0.5) / 5
        L = R * 0.85
        rows = 5
        sv = []; suv = []
        for k in range(rows + 1):
            s = k / rows
            w = R * 0.22 * (1 - s) ** 0.9
            for j, sg in enumerate((-1, 0, 1)):
                rad = 0.002 * size + L * s * 0.9
                zz = -L * 0.5 * s * s * open_amt - 0.0008 * size + (1 - open_amt) * L * s * 0.9
                tang = w * sg
                sv.append((rad * math.cos(ph) - tang * math.sin(ph), rad * math.sin(ph) + tang * math.cos(ph), zz + 0.0005 * size * (1 - abs(sg))))
                suv.append((s, (sg + 1) / 2))
        sf = []
        for k in range(rows):
            for j in range(2):
                a = k * 3 + j
                sf.append([a, a + 1, a + 4, a + 3])
        add(sv, sf, suv, 2)
    # center dome of pistils (green), round enough for macro shots
    us, uf = unit_sphere(10, 6)
    ds, df = unit_sphere(32, 16)
    dome = ds * np.array([0.0028, 0.0028, 0.0022]) * size + np.array([0, 0, 0.0012 * size])
    add(dome, df, np.zeros((len(dome), 2)), 3)
    # stamens ring: filament + anther
    nst = 34
    for i in range(nst):
        ph = 2 * math.pi * i / nst + rng.normal(0, 0.05)
        r0 = 0.0034 * size
        L = 0.0042 * size * rng.uniform(0.85, 1.1) * (0.4 + 0.6 * open_amt)
        out = 0.6 * open_amt + 0.2
        d = np.array([math.cos(ph) * math.sin(out), math.sin(ph) * math.sin(out), math.cos(out)])
        p0 = np.array([r0 * math.cos(ph), r0 * math.sin(ph), 0.0008 * size])
        p1 = p0 + d * L
        tv, tf, _ = tube_mesh(np.array([p0, (p0 + p1) / 2, p1]), np.array([0.00018, 0.00015, 0.00012]) * size, sides=3, close_end=False)
        add(tv, tf, np.zeros((len(tv), 2)), 1)
        an = us * np.array([0.00042, 0.00042, 0.00032]) * size + p1
        add(an, uf, np.zeros((len(an), 2)), 4)
    # small pedicel stub
    tv, tf, tuv = tube_mesh(np.array([[0, 0, 0.0008 * size], [0, 0, -0.004 * size], [0, 0, -0.009 * size]]),
                            np.array([0.0012, 0.0009, 0.0008]) * size, sides=6, close_end=False)
    add(tv, tf, tuv, 2)
    me = make_mesh("flower", V, F, uv=UV, mat_idx=MI)
    me.materials.append(mat_petal())
    me.materials.append(mat_simple("Filament", (0.85, 0.85, 0.75), rough=0.5, transl=0.2))
    me.materials.append(mat_sepal())
    me.materials.append(mat_pistil())
    me.materials.append(mat_simple("Anther", (0.85, 0.65, 0.18), rough=0.6))
    _FLOWER_MESH[key] = me
    return me


# ---------------------------------------------------------------- cane & plant
def cane_points(base, direction, length, arch=0.55, droop=0.3, wobble=0.04, rng=None, n=7):
    rng = rng or np.random.default_rng(0)
    base = np.asarray(base, float)
    dh = np.array([direction[0], direction[1], 0.0]); dh /= np.linalg.norm(dh) + 1e-9
    pts = []
    for i in range(n):
        s = i / (n - 1)
        h = length * arch * math.sin(min(s * 1.15, 1.0) * math.pi / 2) - length * droop * max(0, s - 0.6) ** 2 * 2.5
        out = length * (0.18 * s + 0.55 * s * s)
        p = base + dh * out + np.array([0, 0, h]) + rng.normal(0, wobble * length * s, 3) * np.array([1, 1, 0.5])
        pts.append(p)
    return np.array(pts)


def make_cane(name, ctrl, r0=0.006, r1=0.0018, prickles=True, rng=None, parent=None, sides=8, grow=1.0):
    rng = rng or np.random.default_rng(1)
    P = catmull(ctrl, 10)
    n = len(P)
    tt = np.linspace(0, 1, n)[:, None]
    ph = rng.uniform(0, 6.28, 3)
    P = P + r0 * 0.6 * np.c_[np.sin(tt * 23 + ph[0]), np.sin(tt * 19 + ph[1]), np.sin(tt * 17 + ph[2]) * 0.5]
    keep = max(2, int(n * grow))
    P = P[:keep]
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    sl = np.concatenate([[0], np.cumsum(seg)])
    L = sl[-1]
    t = sl / max(L, 1e-6)
    radii = r0 * (1 - t) ** 0.7 + r1 * t
    V, F, UV = tube_mesh(P, radii, sides=sides)
    MI = [0] * len(F)
    if prickles:
        cone_v = []
        tot = int(L / 0.007)
        for k in range(tot):
            s = rng.uniform(0.02, 0.97)
            i = int(s * (len(P) - 1))
            p = P[i]
            T = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
            T /= np.linalg.norm(T) + 1e-9
            a = rng.uniform(0, 2 * math.pi)
            t1, t2, _ = frame_from_normal(T)
            nrm = math.cos(a) * t1 + math.sin(a) * t2
            rr = radii[i]
            h = rng.uniform(0.0022, 0.0042) * (0.6 + 0.4 * rr / r0)
            bw = h * 0.22
            tipd = nrm * 0.85 - T * 0.5
            tipd /= np.linalg.norm(tipd)
            c0 = p + nrm * rr * 0.85
            base = len(V)
            ring = []
            for q in range(4):
                aa = 2 * math.pi * q / 4
                u1, u2, _ = frame_from_normal(tipd)
                ring.append(c0 + (math.cos(aa) * u1 + math.sin(aa) * u2) * bw)
            V = np.vstack([V, np.array(ring), (c0 + tipd * h)[None]])
            UV = np.vstack([UV, np.zeros((5, 2))])
            for q in range(4):
                F.append([base + q, base + (q + 1) % 4, base + 4])
                MI.append(1)
    me = make_mesh(name, V, F, uv=UV, mat_idx=MI)
    me.materials.append(mat_cane())
    me.materials.append(mat_simple("Prickle", (0.16, 0.035, 0.05), rough=0.35, transl=0.3))
    o = obj_from_mesh(name, me, parent=parent)
    return o, P, radii


def attach_frame(P, i):
    p = P[i]
    T = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
    T /= np.linalg.norm(T) + 1e-9
    return p, T



def make_cluster(name, parent, p0, out_dir, n=4, kind='fruit', ripeness=1.0, rng=None, hero=0, berry_scale=1.0, open_amt=1.0,
                 wind=1.0, ripe_jitter=0.06, flower_prob=0.0, length=None, berry_list=None, flower_list=None, spread=1.0):
    rng = rng or np.random.default_rng(0)
    up = np.array([0, 0, 1.0])
    out = np.asarray(out_dir, float).copy(); out[2] *= 0.2; out /= np.linalg.norm(out) + 1e-9
    L = length or rng.uniform(0.03, 0.05)
    p0 = np.asarray(p0, float)
    if kind == 'flower':
        ctrl = [p0, p0 + out * L * 0.45 + up * L * 0.12, p0 + out * L * 0.8 + up * L * 0.05, p0 + out * L * 1.0 - up * L * 0.15]
    else:
        ctrl = [p0, p0 + out * L * 0.4 - up * L * 0.05, p0 + out * L * 0.75 - up * L * 0.3, p0 + out * L * 0.9 - up * L * 0.7]
    Pp = catmull(ctrl, 6)
    V, F, UV = tube_mesh(Pp, np.linspace(0.0012, 0.0008, len(Pp)), sides=6)
    V = V.tolist(); F = list(F); UV = UV.tolist()
    side0 = np.cross(out, up); side0 /= np.linalg.norm(side0) + 1e-9
    ends = []
    items = []
    tries = 0
    min_d = 0.024 * berry_scale * spread
    down = -up
    while len(items) < n and tries < 400:
        tries += 1
        if tries % 100 == 0:
            min_d *= 0.92
        if len(items) == 0 and kind != 'flower':
            i = len(Pp) - 1
        else:
            i = int(rng.uniform(0.3, 0.95) * (len(Pp) - 1))
        A = Pp[i]
        is_flower = kind == 'flower' or (rng.random() < flower_prob)
        ang = rng.uniform(0, 2 * math.pi)
        sd = math.cos(ang) * side0 + math.sin(ang) * out
        sd /= np.linalg.norm(sd)
        ln = rng.uniform(0.012, 0.022)
        if is_flower:
            B = A + sd * ln * 0.85 + up * ln * rng.uniform(0.0, 0.45)
            mid = A + sd * ln * 0.5 + up * ln * 0.12
        else:
            if i == len(Pp) - 1:
                ln = 0.007
                sd = out
            B = A + sd * ln * 0.65 - up * ln * 0.75
            mid = A + sd * ln * 0.45 + up * ln * 0.06
        ped = catmull([A, mid, B], 4)
        Tend = ped[-1] - ped[-2]; Tend /= np.linalg.norm(Tend)
        if not is_flower:
            Tend = 0.35 * Tend + 0.65 * down
            Tend /= np.linalg.norm(Tend)
        centre = B + Tend * 0.009 * berry_scale
        if any(np.linalg.norm(centre - c) < min_d for c in ends):
            continue
        if min(np.linalg.norm(Pp - centre, axis=1)) < 0.0095 * berry_scale:
            continue
        ends.append(centre)
        tv, tf, tuv = tube_mesh(ped, np.linspace(0.0005, 0.00042, len(ped)), sides=5, close_end=False)
        base = len(V)
        V.extend(tv.tolist()); UV.extend(tuv.tolist()); F.extend([[base + k for k in f] for f in tf])
        items.append((is_flower, B, Tend))
    if not items:
        return None, []
    me = make_mesh(name + "_ped", V, F, uv=UV)
    me.materials.append(mat_pedicel())
    ped_o = obj_from_mesh(name + "_ped", me, parent=parent)
    ped_o.color = (0.25, 0, 0, 1)
    out_items = []
    for q, (is_flower, B, T) in enumerate(items):
        if is_flower:
            fme = flower_mesh(open_amt=open_amt, variant=int(rng.integers(0, 3)))
            fo = bpy.data.objects.new(f"{name}_fl{q}", fme); link(fo); fo.parent = parent
            fs = rng.uniform(0.9, 1.1)
            fo.matrix_local = Matrix.Translation(Vector(B)) @ Vector(T).to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Diagonal((fs, fs, fs, 1))
            if flower_list is not None:
                flower_list.append(fo)
            out_items.append(('flower', fo))
        else:
            r = float(np.clip(ripeness + rng.normal(0, ripe_jitter), 0, 1))
            bs = berry_scale * rng.uniform(0.9, 1.08)
            is_hero = berry_list is not None and len(berry_list) < hero
            lod = {} if (is_hero or BERRY_LOD is None) else dict(N=BERRY_LOD[0], seg=BERRY_LOD[1], rings=BERRY_LOD[2])
            bo, fruit = make_berry(f"{name}_b{q}", ripeness=r, scale=bs, hero=is_hero, seed=int(rng.integers(0, 99)), parent=parent, stem_len=0.0015, **lod)
            bo.matrix_local = Matrix.Translation(Vector(B)) @ Vector(T).to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Diagonal((bs, bs, bs, 1))
            if wind > 0:
                ph = rng.uniform(0, 6.28)
                driver_expr(bo, "rotation_euler", 0, f"{bo.rotation_euler[0]:.4f}+{0.03 * wind:.4f}*sin(frame*0.2+{ph:.2f})")
            if berry_list is not None:
                berry_list.append((bo, fruit))
            out_items.append(('berry', (bo, fruit)))
    return ped_o, out_items


def attach_leaf(name, cane_obj, P, radii, i, out, scale=1.0, variant=0, n_leaflets=3, tilt=-10.0, roll=0.0, wind=1.0, rng=None):
    rng = rng or np.random.default_rng(0)
    i = int(min(max(i, 0), len(P) - 2))
    p = P[i]
    out = np.asarray(out, float); out /= np.linalg.norm(out)
    me = compound_leaf_mesh(variant=variant, n_leaflets=n_leaflets)
    lo = bpy.data.objects.new(name, me)
    link(lo)
    lo.parent = cane_obj
    y = Vector(out); z = Vector((0, 0, 1))
    if abs(y.dot(z)) > 0.95:
        z = Vector((0, 1, 0))
    x = y.cross(z).normalized(); z2 = x.cross(y).normalized()
    M = Matrix((x, y, z2)).transposed().to_4x4()
    M = M @ Matrix.Rotation(math.radians(tilt), 4, 'X') @ Matrix.Rotation(roll, 4, 'Y')
    lo.matrix_local = Matrix.Translation(Vector(p) + Vector(out) * radii[i] * 0.7) @ M @ Matrix.Diagonal((scale, scale, scale, 1))
    lo.color = (1.0, 0, 0, 1)
    if wind > 0:
        ph = rng.uniform(0, 6.28)
        r = lo.rotation_euler
        driver_expr(lo, "rotation_euler", 1, f"{r[1]:.4f}+{0.04 * wind:.4f}*sin(frame*0.23+{ph:.2f})+{0.02 * wind:.4f}*sin(frame*0.61+{ph * 1.7:.2f})")
        driver_expr(lo, "rotation_euler", 0, f"{r[0]:.4f}+{0.025 * wind:.4f}*sin(frame*0.17+{ph + 2:.2f})")
    return lo


def make_plant(name, loc=(0, 0, 0), seed=1, n_canes=5, height=0.9, stage='fruit', ripeness=1.0, leaf_density=1.0,
               fruit_per_cluster=(3, 6), clusters_per_cane=4, wind=1.0, hero_berries=0, open_amt=1.0,
               cane_dirs=None, leaf_scale=1.0, berry_scale=1.0, parent=None, upright=False):
    """stage: 'leaf', 'flower', 'fruit', 'mixed'"""
    rng = np.random.default_rng(seed)
    root = empty(name, loc)
    if parent:
        root.parent = parent
    berries = []; flowers = []; leaves = []; canes = []
    for c in range(n_canes):
        ang = (cane_dirs[c] if cane_dirs else c * 2.4 + rng.uniform(-0.4, 0.4))
        dirv = (math.cos(ang), math.sin(ang))
        L = height * rng.uniform(0.75, 1.2)
        base = (math.cos(ang) * 0.06 + rng.normal(0, 0.03), math.sin(ang) * 0.06 + rng.normal(0, 0.03), -0.02)
        if upright:
            ctrl = cane_points(base, dirv, L, arch=rng.uniform(0.95, 1.05), droop=rng.uniform(0.0, 0.05), rng=rng, wobble=0.015)
            ctrl[:, :2] = ctrl[0, :2] + (ctrl[:, :2] - ctrl[0, :2]) * 0.28
        else:
            ctrl = cane_points(base, dirv, L, arch=rng.uniform(0.55, 0.85), droop=rng.uniform(0.15, 0.4), rng=rng)
        co, P, radii = make_cane(f"{name}_cane{c}", ctrl, r0=0.0065, r1=0.002, rng=rng, parent=root)
        co.color = (0.6, 0, 0, 1)
        canes.append(co)
        if wind > 0:
            ph = rng.uniform(0, 6.28)
            driver_expr(co, "rotation_euler", 0, f"{0.006 * wind:.4f}*sin(frame*0.11+{ph:.2f})+{0.003 * wind:.4f}*sin(frame*0.37+{ph * 2:.2f})")
            driver_expr(co, "rotation_euler", 1, f"{0.006 * wind:.4f}*sin(frame*0.09+{ph + 1:.2f})")
        n = len(P)
        # leaves along cane
        nleaf = int((n / 4) * leaf_density)
        for k in range(nleaf):
            i = int((0.12 + 0.86 * (k + rng.uniform(0, 0.6)) / max(nleaf, 1)) * (n - 1))
            i = min(i, n - 2)
            p, T = attach_frame(P, i)
            a = k * GOLDEN * 1.0 + rng.uniform(-0.3, 0.3)
            t1, t2, _ = frame_from_normal(T)
            out = math.cos(a) * t1 + math.sin(a) * t2
            out[2] = abs(out[2]) * 0.5 + 0.15
            out /= np.linalg.norm(out)
            me = compound_leaf_mesh(variant=int(rng.integers(0, 4)), n_leaflets=3 if rng.random() < 0.7 else 5)
            lo = bpy.data.objects.new(f"{name}_leaf{c}_{k}", me)
            link(lo)
            lo.parent = co
            # orient: leaf +y along out, leaf +z up-ish
            y = Vector(out); z = Vector((0, 0, 1)); x = y.cross(z).normalized(); z2 = x.cross(y).normalized()
            M = Matrix((x, y, z2)).transposed().to_4x4()
            M = M @ Matrix.Rotation(math.radians(rng.uniform(-25, 10)), 4, 'X') @ Matrix.Rotation(rng.normal(0, 0.15), 4, 'Y')
            lo.matrix_local = Matrix.Translation(Vector(p) + Vector(out) * radii[i] * 0.8) @ M
            s = leaf_scale * 1.3 * rng.uniform(0.8, 1.15) * (1.0 - 0.3 * (i / n))
            lo.scale = (s, s, s)
            lo.color = (1.0, 0, 0, 1)
            if wind > 0:
                ph = rng.uniform(0, 6.28)
                driver_expr(lo, "rotation_euler", 1, f"{lo.rotation_euler[1]:.4f}+{0.05 * wind:.4f}*sin(frame*0.23+{ph:.2f})+{0.025 * wind:.4f}*sin(frame*0.61+{ph * 1.7:.2f})")
                driver_expr(lo, "rotation_euler", 0, f"{lo.rotation_euler[0]:.4f}+{0.03 * wind:.4f}*sin(frame*0.17+{ph + 2:.2f})")
            leaves.append(lo)
        # clusters (laterals) on upper part
        if stage in ('flower', 'fruit', 'mixed'):
            for k in range(clusters_per_cane):
                i = int((0.42 + 0.55 * (k + rng.uniform(0, 0.8)) / clusters_per_cane) * (n - 1))
                i = min(i, n - 2)
                p, T = attach_frame(P, i)
                a = rng.uniform(0, 2 * math.pi)
                t1, t2, _ = frame_from_normal(T)
                side = math.cos(a) * t1 + math.sin(a) * t2
                side[2] = -abs(side[2]) * 0.3
                side /= np.linalg.norm(side)
                p0 = p + side * radii[i] * 0.6
                nf = int(rng.integers(fruit_per_cluster[0], fruit_per_cluster[1] + 1))
                kind = 'flower' if stage == 'flower' else 'fruit'
                make_cluster(f"{name}_c{c}_{k}", co, p0, side, n=nf, kind=kind, ripeness=ripeness, rng=rng, hero=hero_berries,
                             berry_scale=berry_scale, open_amt=open_amt, wind=wind, flower_prob=0.35 if stage == 'mixed' else 0.0,
                             ripe_jitter=0.06 if stage != 'mixed' else 0.4, berry_list=berries, flower_list=flowers)
    return dict(root=root, canes=canes, leaves=leaves, berries=berries, flowers=flowers)


# ---------------------------------------------------------------- ground / forest
def ground(name="Ground", size=6.0, subdiv=7, disp=0.05, mat=None, loc=(0, 0, 0), noise_scale=1.2, seed=0):
    rng = np.random.default_rng(seed)
    n = 2 ** subdiv
    xs = np.linspace(-size / 2, size / 2, n + 1)
    X, Y = np.meshgrid(xs, xs)
    ph = rng.uniform(0, 100, 4)
    Z = disp * (np.sin(X * noise_scale * 2.1 + ph[0]) * np.cos(Y * noise_scale * 1.7 + ph[1]) * 0.6 +
                np.sin(X * noise_scale * 5.3 + Y * 3.1 + ph[2]) * 0.25 + np.cos(Y * noise_scale * 7.7 - X * 2.3 + ph[3]) * 0.15)
    V = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    F = []
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            F.append([a, a + 1, a + n + 2, a + n + 1])
    UV = np.c_[(X.ravel() + size / 2) / size, (Y.ravel() + size / 2) / size]
    me = make_mesh(name, V, F, uv=UV)
    o = obj_from_mesh(name, me, mats=[mat] if mat else [], loc=loc)
    return o


def ground_height_fn(o):
    me = o.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    n = int(round(math.sqrt(len(co)))) - 1
    xs = co[:n + 1, 0]
    Z = co[:, 2].reshape(n + 1, n + 1)
    x0, x1 = xs[0], xs[-1]

    def h(x, y):
        x = x - o.location.x; y = y - o.location.y
        fi = (y - x0) / (x1 - x0) * n; fj = (x - x0) / (x1 - x0) * n
        i = int(np.clip(math.floor(fi), 0, n - 1)); j = int(np.clip(math.floor(fj), 0, n - 1))
        ti = fi - i; tj = fj - j
        z = (Z[i, j] * (1 - ti) * (1 - tj) + Z[i, j + 1] * (1 - ti) * tj + Z[i + 1, j] * ti * (1 - tj) + Z[i + 1, j + 1] * ti * tj)
        return float(z) + o.location.z
    return h


def mat_forest_floor(name="ForestFloor", scale=1.0):
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    co = nt.mapping(tc.outputs["Object"], scale=(scale,) * 3)
    img = nt.image(os.path.join(ASSETS, "tex", "rockyGround_basecolor.png"), nt.mapping(tc.outputs["Object"], scale=(0.9 * scale,) * 3))
    n1 = nt.noise(co, scale=1.5, detail=6, rough=0.6)
    soil = nt.mix(n1.outputs["Fac"], (0.045, 0.03, 0.018, 1), (0.10, 0.065, 0.035, 1))
    c = nt.mix(0.45, soil, img.outputs["Color"], 'MULTIPLY')
    c = nt.mix(0.5, soil, c)
    moss = nt.noise(co, scale=0.8, detail=4, rough=0.55)
    mfac = nt.math('MULTIPLY', nt.math('SUBTRACT', moss.outputs["Fac"], 0.55, clamp=True), 4.0)
    mfac = nt.math('MINIMUM', mfac, 1.0)
    mcol = nt.mix(n1.outputs["Fac"], (0.04, 0.09, 0.015, 1), (0.10, 0.16, 0.03, 1))
    c = nt.mix(mfac, c, mcol)
    p = principled(nt, Base_Color=c, Roughness=0.85, Specular_IOR_Level=0.3)
    nimg = nt.image(os.path.join(ASSETS, "tex", "rockyGround_normal.png"), nt.mapping(tc.outputs["Object"], scale=(0.9 * scale,) * 3), colorspace='Non-Color')
    nm = nt.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.8
    nt.link(nimg.outputs["Color"], nm.inputs["Color"])
    nt.link(nm.outputs[0], p.inputs["Normal"])
    _MATS[name] = m
    return m


_LITTER = []


def litter_leaf_meshes():
    if _LITTER:
        return _LITTER
    for v in range(4):
        lv, lf, luv = leaflet_geom(L=0.05 * (0.8 + 0.12 * v), W=0.017 + 0.003 * v, rows=12, cols=4, teeth=6, fold=0.35, arch=-0.35 + 0.15 * v, seed=v + 40,
                                   twist=0.6 * (v - 1.5))
        me = make_mesh(f"litter{v}", lv, lf, uv=luv)
        m = mat_simple(f"Litter{v}", [(0.11, 0.05, 0.018), (0.16, 0.09, 0.03), (0.08, 0.045, 0.02), (0.13, 0.085, 0.04)][v], rough=0.7, transl=0.1)
        me.materials.append(m)
        _LITTER.append(me)
    return _LITTER


def scatter_litter(ground_obj, hfn, count=800, area=(-2, 2, -2, 2), seed=3, avoid=None, scale=1.0, coll=None):
    rng = np.random.default_rng(seed)
    meshes = litter_leaf_meshes()
    objs = []
    # build one merged mesh for performance
    V = []; F = []; UV = []; MI = []
    for k in range(count):
        x = rng.uniform(area[0], area[1]); y = rng.uniform(area[2], area[3])
        if avoid and avoid(x, y):
            continue
        me = meshes[k % 4]
        co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        s = scale * rng.uniform(0.5, 1.2)
        Rm = np.array(Euler((rng.normal(0, 0.25), rng.normal(0, 0.25), rng.uniform(0, 6.28))).to_matrix())
        P = (co * s) @ Rm.T + np.array([x, y, hfn(x, y) + 0.004 + rng.uniform(0, 0.006)])
        base = len(V)
        V.extend(P.tolist())
        uvs = np.zeros(len(me.loops) * 2, np.float32)
        for poly in me.polygons:
            F.append([base + vi for vi in poly.vertices]); MI.append(k % 4)
        lv, lf, luv = None, None, None
    UVv = np.zeros((len(V), 2))
    m = make_mesh("Litter", V, F, uv=UVv, mat_idx=MI)
    for me in meshes:
        m.materials.append(me.materials[0])
    return obj_from_mesh("Litter", m, coll=coll)


def fern_mesh(variant=0, L=0.5):
    rng = np.random.default_rng(variant + 70)
    V = []; F = []; UV = []; MI = []
    # one frond along +y with arch
    nseg = 24
    rach = []
    for k in range(nseg + 1):
        s = k / nseg
        rach.append((0.0, L * s, L * (0.55 * s - 0.65 * s * s)))
    rach = np.array(rach)
    tv, tf, tuv = tube_mesh(rach, np.linspace(0.0025, 0.0008, nseg + 1), sides=4)
    V.extend(tv.tolist()); F.extend(tf); UV.extend(tuv.tolist()); MI.extend([1] * len(tf))
    for k in range(2, nseg):
        s = k / nseg
        p = rach[k]
        pl = L * 0.28 * math.sin(math.pi * min(1, s * 1.1)) ** 0.8 * (1 - s * 0.3)
        for sgn in (-1, 1):
            lv, lf, luv = leaflet_geom(L=pl, W=pl * 0.16, rows=8, cols=2, teeth=10, fold=0.2, arch=0.25, seed=k + variant)
            M = Matrix.Translation(Vector(p)) @ Matrix.Rotation(sgn * -math.radians(70), 4, 'Z') @ Matrix.Rotation(math.radians(-10), 4, 'Y')
            vv = (np.array(M) @ np.c_[lv, np.ones(len(lv))].T).T[:, :3]
            base = len(V)
            V.extend(vv.tolist()); UV.extend(luv.tolist())
            F.extend([[base + q for q in f] for f in lf]); MI.extend([0] * len(lf))
    me = make_mesh(f"frond{variant}", V, F, uv=UV, mat_idx=MI)
    me.materials.append(mat_leaf("FernLeaf", top=(0.05, 0.16, 0.025), under=(0.12, 0.22, 0.06), rough=0.8, spec=0.06, bump_dist=0.0006))
    me.materials.append(mat_simple("FernStem", (0.10, 0.12, 0.04), rough=0.6))
    return me


def make_fern(name, loc, n=9, seed=0, scale=1.0, wind=1.0):
    rng = np.random.default_rng(seed)
    root = empty(name, loc)
    fronds = [fern_mesh(v, 0.45) for v in range(3)]
    for k in range(n):
        me = fronds[k % 3]
        o = bpy.data.objects.new(f"{name}_f{k}", me); link(o); o.parent = root
        a = k / n * 2 * math.pi + rng.normal(0, 0.2)
        o.rotation_euler = (math.radians(rng.uniform(20, 50)), 0, a - math.pi / 2)
        s = scale * rng.uniform(0.7, 1.15)
        o.scale = (s, s, s)
        o.color = (1, 0, 0, 1)
        if wind > 0:
            ph = rng.uniform(0, 6.28)
            driver_expr(o, "rotation_euler", 0, f"{o.rotation_euler[0]:.4f}+{0.02 * wind:.4f}*sin(frame*0.13+{ph:.2f})")
    return root


def make_trunk(name, loc, height=8.0, r=0.18, seed=0):
    rng = np.random.default_rng(seed)
    pts = np.array([[0, 0, -0.2], [rng.normal(0, 0.05), rng.normal(0, 0.05), height * 0.4], [rng.normal(0, 0.15), rng.normal(0, 0.15), height]])
    P = catmull(pts, 8)
    radii = r * (1.25 - 0.45 * np.linspace(0, 1, len(P)))
    radii[0] *= 1.25
    V, F, UV = tube_mesh(P, radii, sides=16)
    UV[:, 0] *= 3
    me = make_mesh(name, V, F, uv=UV)
    bark, bark_n = os.path.join(ASSETS, "tex", "BroadleafBark.jpg"), os.path.join(ASSETS, "tex", "BroadleafBark_Normal.png")
    if os.path.exists(bark):
        m = mat_image("Bark", bark, bark_n if os.path.exists(bark_n) else None, scale=1.0, rough=0.85, tint=(0.75, 0.7, 0.65))
    else:  # no bark photo (get_assets.py fetches it): procedural bark instead
        m = mat_bark_procedural()
    me.materials.append(m)
    o = obj_from_mesh(name, me, loc=loc)
    return o


def mat_moss(name="Moss", scale=4.0):
    col, nrm = os.path.join(ASSETS, "tex", "Moss_01_Color.png"), os.path.join(ASSETS, "tex", "Moss_01_Normal.png")
    if not os.path.exists(col):  # no moss photo (get_assets.py fetches it): procedural moss instead
        return mat_moss_procedural(name, scale)
    return mat_image(name, col, nrm if os.path.exists(nrm) else None, scale=scale, rough=0.9, tint=(0.85, 0.95, 0.7), uv='Object')


def mat_bark_procedural(name="Bark"):
    """grey-brown broadleaf bark: vertical plates split by dark crevices, fine fibres, pale and lichen patches. No image files."""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    oc = tc.outputs["Object"]
    # domain-warped, vertically stretched cells give long irregular plates instead of a tile pattern
    wn = nt.noise(nt.mapping(oc, scale=(4.0, 4.0, 1.0)), scale=2.0, detail=4.0, rough=0.6)
    ws = nt.new("ShaderNodeVectorMath"); ws.operation = 'SCALE'; ws.inputs["Scale"].default_value = 0.16
    nt.link(wn.outputs["Color"], ws.inputs[0])
    wa = nt.new("ShaderNodeVectorMath"); wa.operation = 'ADD'
    nt.link(oc, wa.inputs[0]); nt.link(ws.outputs[0], wa.inputs[1])
    plates = nt.voronoi(nt.mapping(wa.outputs[0], scale=(7.0, 7.0, 1.1)), scale=1.0, feature='DISTANCE_TO_EDGE')
    crev = nt.math('SUBTRACT', 1.0, nt.math('MULTIPLY', plates.outputs["Distance"], 14.0), clamp=True)   # 1 in the cracks
    fibre = nt.noise(nt.mapping(oc, scale=(60.0, 60.0, 6.0)), scale=3.0, detail=6.0, rough=0.6)
    patch = nt.noise(oc, scale=2.2, detail=3.0, rough=0.5)
    lichen = nt.noise(oc, scale=4.0, detail=4.0, rough=0.55)
    face = nt.ramp(nt.math('ADD', nt.math('MULTIPLY', fibre.outputs["Fac"], 0.6), nt.math('MULTIPLY', patch.outputs["Fac"], 0.5)),
                   [(0.35, (0.045, 0.038, 0.030)), (0.55, (0.10, 0.085, 0.068)), (0.75, (0.19, 0.17, 0.14))])
    c = nt.mix(nt.math('POWER', crev, 1.5), face, (0.012, 0.010, 0.008, 1))
    lp = nt.math('MULTIPLY', nt.math('SUBTRACT', lichen.outputs["Fac"], 0.58), 6.0, clamp=True)
    c = nt.mix(nt.math('MULTIPLY', lp, 0.6), c, (0.22, 0.26, 0.17, 1))
    p = principled(nt, Base_Color=c, Roughness=0.9, Specular_IOR_Level=0.25)
    h = nt.math('SUBTRACT', nt.math('MULTIPLY', fibre.outputs["Fac"], 0.25), nt.math('MULTIPLY', crev, 0.8))
    nt.link(nt.bump(h, 1.0, 0.02), p.inputs["Normal"])
    _MATS[name] = m
    return m


def mat_moss_procedural(name="Moss", scale=4.0):
    """moss in patches over grey stone: clumpy green with yellow-green tips, bare rock between patches. No image files."""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    tc = nt.texcoord()
    oc = tc.outputs["Object"]
    cover = nt.noise(nt.mapping(oc, scale=(scale * 1.2,) * 3), scale=2.0, detail=5.0, rough=0.6)
    mask = nt.math('MULTIPLY', nt.math('SUBTRACT', cover.outputs["Fac"], 0.42), 7.0, clamp=True)   # 1 = moss, 0 = bare rock
    clump = nt.noise(nt.mapping(oc, scale=(scale * 8,) * 3), scale=4.0, detail=8.0, rough=0.7)
    tips = nt.voronoi(nt.mapping(oc, scale=(scale * 70,) * 3), scale=1.0)
    t = nt.math('POWER', nt.math('SUBTRACT', 1.0, tips.outputs["Distance"], clamp=True), 3.0)
    moss = nt.ramp(clump.outputs["Fac"], [(0.30, (0.010, 0.020, 0.005)), (0.52, (0.045, 0.09, 0.018)), (0.72, (0.12, 0.17, 0.03))])
    moss = nt.mix(nt.math('MULTIPLY', t, 0.4), moss, (0.25, 0.27, 0.05, 1))
    grit = nt.noise(nt.mapping(oc, scale=(scale * 20,) * 3), scale=3.0, detail=6.0)
    rock = nt.ramp(grit.outputs["Fac"], [(0.3, (0.05, 0.048, 0.045)), (0.7, (0.14, 0.13, 0.12))])
    c = nt.mix(mask, rock, moss)
    p = principled(nt, Base_Color=c, Roughness=0.9, Specular_IOR_Level=0.25, Sheen_Weight=0.35, Sheen_Tint=(0.8, 0.9, 0.6, 1))
    h = nt.math('ADD', nt.math('MULTIPLY', mask, nt.math('ADD', clump.outputs["Fac"], nt.math('MULTIPLY', t, 0.3))),
                nt.math('MULTIPLY', grit.outputs["Fac"], 0.3))
    nt.link(nt.bump(h, 0.7, 0.006), p.inputs["Normal"])
    _MATS[name] = m
    return m


def make_rock(name, loc, size=0.3, seed=0, mat=None):
    rng = np.random.default_rng(seed)
    us, uf = unit_sphere(24, 14)
    ph = rng.uniform(0, 10, 3)
    d = 1 + 0.18 * np.sin(us[:, 0] * 3 + ph[0]) * np.cos(us[:, 1] * 2.5 + ph[1]) + 0.08 * np.sin(us[:, 2] * 7 + ph[2])
    V = us * d[:, None] * np.array([size, size * rng.uniform(0.7, 1.0), size * 0.6])
    me = make_mesh(name, V, uf)
    me.materials.append(mat or mat_moss())
    return obj_from_mesh(name, me, loc=loc)


# ---------------------------------------------------------------- compositor
def compositor(sc, vignette=0.0, fog=None, grain=0.0, glare=False):
    sc.use_nodes = True
    nt = sc.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    cur = rl.outputs["Image"]
    if fog is not None:
        bpy.context.view_layer.use_pass_mist = True
        col, start, depth, amount = fog
        sc.world.mist_settings.start = start
        sc.world.mist_settings.depth = depth
        sc.world.mist_settings.falloff = 'QUADRATIC'
        mr = nt.nodes.new("CompositorNodeMath"); mr.operation = 'MULTIPLY'; mr.inputs[1].default_value = amount
        nt.links.new(rl.outputs["Mist"], mr.inputs[0])
        mx = nt.nodes.new("CompositorNodeMixRGB")
        mx.inputs[2].default_value = (*col, 1)
        nt.links.new(mr.outputs[0], mx.inputs[0])
        nt.links.new(cur, mx.inputs[1])
        cur = mx.outputs[0]
    if vignette > 0:
        em = nt.nodes.new("CompositorNodeEllipseMask")
        em.width = 1.15; em.height = 0.95
        bl = nt.nodes.new("CompositorNodeBlur")
        bl.filter_type = 'FAST_GAUSS'; bl.use_relative = True; bl.factor_x = 0.35; bl.factor_y = 0.35; bl.size_x = 200; bl.size_y = 200
        nt.links.new(em.outputs[0], bl.inputs[0])
        mr = nt.nodes.new("CompositorNodeMapRange")
        mr.inputs[3].default_value = 1 - vignette; mr.inputs[4].default_value = 1.0
        nt.links.new(bl.outputs[0], mr.inputs[0])
        mx = nt.nodes.new("CompositorNodeMixRGB"); mx.blend_type = 'MULTIPLY'
        mx.inputs[0].default_value = 1.0
        nt.links.new(cur, mx.inputs[1]); nt.links.new(mr.outputs[0], mx.inputs[2])
        cur = mx.outputs[0]
    nt.links.new(cur, comp.inputs["Image"])
    return nt


def render(sc, out_final):
    fr = os.environ.get("FRANGE")
    if fr:
        a, b = map(int, fr.split("-"))
        sc.frame_start, sc.frame_end = a, b
        out_final = out_final.replace(".mp4", f"_r{a}-{b}_{sc.render.resolution_x}.mp4")
    tmp = out_final.replace(".mp4", "_tmp.mp4")
    if os.path.exists(tmp):
        os.remove(tmp)
    sc.render.filepath = tmp
    bpy.ops.render.render(animation=True)
    # blender appends frame range to name if no extension handling; find file
    os.replace(tmp, out_final)


def render_still(sc, frame, out_png):
    sc.frame_set(frame)
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- god rays & forest environment
def mat_ray(name="Ray", color=(1.0, 0.9, 0.7), strength=0.25):
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    nt.n.remove(nt.n["Principled BSDF"])
    uvn = nt.new("ShaderNodeUVMap")
    sep = nt.new("ShaderNodeSeparateXYZ"); nt.link(uvn.outputs[0], sep.inputs[0])
    # fade across (x) and along (y)
    ax = nt.math('SUBTRACT', 1.0, nt.math('ABSOLUTE', nt.math('SUBTRACT', nt.math('MULTIPLY', sep.outputs["X"], 2.0), 1.0)))
    ax = nt.math('POWER', ax, 1.6)
    ay = nt.math('SINE', nt.math('MULTIPLY', sep.outputs["Y"], 3.14159))
    a = nt.math('MULTIPLY', ax, ay)
    tc = nt.texcoord()
    nz = nt.noise(tc.outputs["Object"], scale=2.0, detail=2)
    a = nt.math('MULTIPLY', a, nt.math('ADD', 0.4, nz.outputs["Fac"]))
    em = nt.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    nt.link(nt.math('MULTIPLY', a, strength), em.inputs["Strength"])
    tr = nt.new("ShaderNodeBsdfTransparent")
    add = nt.new("ShaderNodeAddShader")
    nt.link(em.outputs[0], add.inputs[0]); nt.link(tr.outputs[0], add.inputs[1])
    nt.link(add.outputs[0], nt.n["Material Output"].inputs["Surface"])
    m.blend_method = 'BLEND'
    m.shadow_method = 'NONE'
    m.use_backface_culling = False
    m.show_transparent_back = True
    _MATS[name] = m
    return m


def god_ray(name, base, direction, length=6.0, width=0.5, strength=0.25, color=(1, 0.9, 0.7), face=None):
    d = Vector(direction).normalized()
    V = [(-width / 2, 0, 0), (width / 2, 0, 0), (width / 2, length, 0), (-width / 2, length, 0)]
    me = make_mesh(name, V, [[0, 1, 2, 3]], uv=[(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    me.materials.append(mat_ray(f"Ray{strength:.2f}", color, strength))
    o = obj_from_mesh(name, me, loc=base)
    # local +y along -d (from ground up toward light)
    y = -d
    zf = Vector(face) if face is not None else Vector((0, -1, 0))
    x = y.cross(zf).normalized(); z = x.cross(y).normalized()
    o.matrix_world = Matrix.Translation(Vector(base)) @ Matrix((x, y, z)).transposed().to_4x4()
    return o


def forest_env(sc, seed=1, size=40.0, litter=1500, litter_area=2.5, ferns=8, rocks=4, trunks=10, trunk_min=2.5,
               trunk_max=8.0, hdri="babylon_forest.hdr", hdri_rot=2.0, hdri_strength=0.9, cam_strength=1.0, clear=(0, 0),
               clear_r=0.5, fern_min=0.9, fern_max=3.0, extra_plants=0, cover=0, cover_area=3.0):
    rng = np.random.default_rng(seed)
    world_hdri(sc, hdri, strength=hdri_strength, cam_strength=cam_strength, rot=hdri_rot, clamp_bg=2.0)
    g = ground("Ground", size=size, subdiv=8, disp=0.05, mat=mat_forest_floor(), seed=seed)
    h = ground_height_fn(g)
    avoid = lambda x, y: (x - clear[0]) ** 2 + (y - clear[1]) ** 2 < (clear_r * 0.35) ** 2
    if litter:
        scatter_litter(g, h, count=litter, area=(-litter_area, litter_area, -litter_area, litter_area), seed=seed, avoid=avoid)
    if cover:
        scatter_groundcover(h, count=cover, area=(clear[0] - cover_area, clear[0] + cover_area, clear[1] - cover_area, clear[1] + cover_area),
                            seed=seed + 9, avoid=avoid)
    out = dict(ground=g, h=h, ferns=[], rocks=[], trunks=[])
    for k in range(ferns):
        for _ in range(50):
            a = rng.uniform(0, 2 * math.pi); r = rng.uniform(fern_min, fern_max)
            x, y = clear[0] + r * math.cos(a), clear[1] + r * math.sin(a)
            if all((x - f.location.x) ** 2 + (y - f.location.y) ** 2 > 0.6 ** 2 for f in out["ferns"]):
                break
        f = make_fern(f"fern{k}", (x, y, h(x, y) - 0.02), n=int(rng.integers(7, 11)), seed=k + seed, scale=rng.uniform(0.9, 1.5))
        out["ferns"].append(f)
    for k in range(rocks):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.9, 3.0)
        x, y = clear[0] + r * math.cos(a), clear[1] + r * math.sin(a)
        rk = make_rock(f"rock{k}", (x, y, h(x, y) - 0.05), size=rng.uniform(0.15, 0.4), seed=k + seed)
        rk.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        out["rocks"].append(rk)
    for k in range(trunks):
        for _ in range(50):
            a = rng.uniform(0, 2 * math.pi); r = rng.uniform(trunk_min, trunk_max)
            x, y = clear[0] + r * math.cos(a), clear[1] + r * math.sin(a)
            if all((x - t.location.x) ** 2 + (y - t.location.y) ** 2 > 1.2 ** 2 for t in out["trunks"]):
                break
        t = make_trunk(f"trunk{k}", (x, y, h(x, y) if abs(x) < size / 2 and abs(y) < size / 2 else 0), height=12, r=rng.uniform(0.12, 0.3), seed=k)
        out["trunks"].append(t)
    for k in range(extra_plants):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(1.2, 3.5)
        x, y = clear[0] + r * math.cos(a), clear[1] + r * math.sin(a)
        make_plant(f"bg{k}", (x, y, h(x, y)), seed=100 + k, n_canes=4, height=rng.uniform(0.5, 0.8), stage='leaf', wind=0.6)
    return out


def scatter_groundcover(hfn, count=1200, area=(-2, 2, -2, 2), seed=5, avoid=None, scale=1.0, name="GroundCover"):
    rng = np.random.default_rng(seed)
    protos = []
    for v in range(3):
        V = []; F = []; UV = []
        nl = 3 + v
        for k in range(nl):
            lv, lf, luv = leaflet_geom(L=0.035 + 0.01 * v, W=0.016, rows=8, cols=4, teeth=1, fold=0.3, arch=-0.2, seed=v * 7 + k)
            a = 2 * math.pi * k / nl + rng.normal(0, 0.2)
            M = np.array(Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(math.radians(rng.uniform(15, 35)), 4, 'X'))
            vv = (M @ np.c_[lv, np.ones(len(lv))].T).T[:, :3] + np.array([0, 0, 0.012 + 0.006 * v])
            base = len(V)
            V.extend(vv.tolist()); UV.extend(luv.tolist()); F.extend([[base + q for q in f] for f in lf])
        protos.append((np.array(V), F, np.array(UV)))
    V = []; F = []; UV = []
    for k in range(count):
        x = rng.uniform(area[0], area[1]); y = rng.uniform(area[2], area[3])
        if avoid and avoid(x, y):
            continue
        pv, pf, puv = protos[k % 3]
        s = scale * rng.uniform(0.6, 1.4)
        Rm = np.array(Euler((rng.normal(0, 0.1), rng.normal(0, 0.1), rng.uniform(0, 6.28))).to_matrix())
        P = (pv * s) @ Rm.T + np.array([x, y, hfn(x, y) - 0.004])
        base = len(V)
        V.extend(P.tolist()); UV.extend(puv.tolist()); F.extend([[base + q for q in f] for f in pf])
    me = make_mesh(name, V, F, uv=UV)
    me.materials.append(mat_leaf("CoverLeaf", top=(0.05, 0.14, 0.03), under=(0.15, 0.25, 0.08)))
    o = obj_from_mesh(name, me)
    o.color = (1, 0, 0, 1)
    return o


# ---------------------------------------------------------------- bee (pre-existing model: BabylonJS Assets Bee.glb)
def load_bee(name="Bee", length=0.014, action="_bee_hover_skeletal.1", speed=1.0, frames=400, offset=0):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, "models", "Bee.glb"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    new = [o for o in bpy.data.objects if o not in before]
    arm = [o for o in new if o.type == 'ARMATURE'][0]
    mesh = [o for o in new if o.type == 'MESH'][0]
    top = [o for o in new if o.parent is None]
    root = empty(name)
    for o in top:
        o.parent = root
    s = length / 22.23
    root.scale = (s, s, s)
    # wings: polygons weighted to wing bones get a translucent material
    wing_groups = {vg.index for vg in mesh.vertex_groups if "wing" in vg.name.lower()}
    me = mesh.data
    wingv = np.zeros(len(me.vertices), bool)
    for v in me.vertices:
        w = sum(g.weight for g in v.groups if g.group in wing_groups)
        wingv[v.index] = w > 0.5
    if "BeeWing" not in _MATS:
        m, nt = new_mat("BeeWing")
        lw = nt.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.3
        col = nt.mix(lw.outputs["Facing"], (0.75, 0.8, 0.85, 1), (0.85, 0.7, 0.95, 1))
        principled(nt, Base_Color=col, Roughness=0.15, Alpha=0.22, Specular_IOR_Level=0.8)
        m.blend_method = 'BLEND'; m.shadow_method = 'HASHED'; m.use_backface_culling = False; m.show_transparent_back = False
        _MATS["BeeWing"] = m
    me.materials.append(_MATS["BeeWing"])
    wi = len(me.materials) - 1
    mi = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi)
    for p in me.polygons:
        if all(wingv[v] for v in p.vertices):
            mi[p.index] = wi
    me.polygons.foreach_set("material_index", mi)
    # animation: repeat chosen action via NLA
    act = bpy.data.actions.get(action)
    arm.animation_data_create()
    arm.animation_data.action = None
    tr = arm.animation_data.nla_tracks.new()
    st = tr.strips.new("loop", 1 + offset, act)
    st.scale = 1.0 / speed
    st.repeat = max(1.0, frames / ((act.frame_range[1] - act.frame_range[0]) / speed))
    root["arm"] = arm.name
    return root, arm, mesh


def bee_land_switch(arm, land_frame, frames, blend=6):
    act = bpy.data.actions.get("_bee_idle_skeletal.1")
    tr = arm.animation_data.nla_tracks.new()
    st = tr.strips.new("idle", int(land_frame), act)
    st.blend_in = blend
    st.repeat = max(1.0, (frames - land_frame + 10) / (act.frame_range[1] - act.frame_range[0]))


def receptacle_mesh(R=0.0085, H=0.019, name="receptacle"):
    zs = np.linspace(0.0, 0.72 * H, 26)
    V = []
    seg = 36
    for k, z in enumerate(zs):
        t = z / (0.72 * H)
        r = 0.48 * R * (1 - t ** 1.8) ** 0.6 + 0.0004
        for s_ in range(seg):
            a = 2 * math.pi * s_ / seg
            bump = 1 + 0.06 * math.sin(a * 5 + k * 0.9)
            V.append((r * bump * math.cos(a), r * bump * math.sin(a), z))
    V.append((0, 0, 0.72 * H + 0.0006))
    F = [[k * seg + s_, k * seg + (s_ + 1) % seg, (k + 1) * seg + (s_ + 1) % seg, (k + 1) * seg + s_] for k in range(len(zs) - 1) for s_ in range(seg)]
    top = len(V) - 1
    F += [[(len(zs) - 1) * seg + s_, (len(zs) - 1) * seg + (s_ + 1) % seg, top] for s_ in range(seg)]
    me = make_mesh(name, V, F)
    if "Receptacle" not in _MATS:
        m, nt = new_mat("Receptacle")
        tc = nt.texcoord()
        vor = nt.voronoi(tc.outputs["Object"], scale=700.0)
        c = nt.mix(vor.outputs["Distance"], (0.80, 0.78, 0.66, 1), (0.62, 0.60, 0.50, 1))
        p = principled(nt, Base_Color=c, Roughness=0.45, Subsurface_Weight=0.4, Subsurface_Radius=(1, 0.9, 0.7), Subsurface_Scale=0.002)
        nt.link(nt.bump(vor.outputs["Distance"], 0.5, 0.0004), p.inputs["Normal"])
        _MATS["Receptacle"] = m
    me.materials.append(_MATS["Receptacle"])
    return me


def mat_grow(name, color, rough=0.5, sss=0.2, emission=None, emit=0.0):
    """tube material that reveals along uv.y up to obj colour R (0..1)"""
    if name in _MATS:
        return _MATS[name]
    m, nt = new_mat(name)
    uvn = nt.new("ShaderNodeUVMap")
    sep = nt.new("ShaderNodeSeparateXYZ"); nt.link(uvn.outputs[0], sep.inputs[0])
    oi = nt.new("ShaderNodeObjectInfo"); sc_ = nt.new("ShaderNodeSeparateColor"); nt.link(oi.outputs["Color"], sc_.inputs[0])
    alpha = nt.math('LESS_THAN', sep.outputs["Y"], sc_.outputs[0])
    tc = nt.texcoord(); nz = nt.noise(tc.outputs["Object"], scale=120.0, detail=3)
    c = nt.mix(nz.outputs["Fac"], (*color, 1), (color[0] * 0.75, color[1] * 0.75, color[2] * 0.7, 1))
    p = principled(nt, Base_Color=c, Roughness=rough, Subsurface_Weight=sss, Subsurface_Radius=(1, 0.8, 0.6), Subsurface_Scale=0.002)
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1); p.inputs["Emission Strength"].default_value = emit
    nt.link(alpha, p.inputs["Alpha"])
    m.blend_method = 'CLIP'; m.shadow_method = 'CLIP'; m.alpha_threshold = 0.5
    _MATS[name] = m
    return m


def grow_tube(name, pts, r0, r1, mat, f0, f1, sides=8, parent=None, tip_mat=None):
    P = catmull(pts, 8)
    V, F, UV = tube_mesh(P, np.linspace(r0, r1, len(P)), sides=sides)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    UV[:len(P) * sides, 1] = np.repeat(L / L[-1], sides)
    UV[len(P) * sides:, 1] = 1.0
    me = make_mesh(name, V, F, uv=UV); me.materials.append(mat)
    o = obj_from_mesh(name, me, parent=parent)
    o.color = (0.0, 0, 0, 1); o.keyframe_insert("color", frame=1)
    o.color = (0.0, 0, 0, 1); o.keyframe_insert("color", frame=f0)
    o.color = (1.001, 0, 0, 1); o.keyframe_insert("color", frame=f1)
    if tip_mat is not None:
        us, uf = unit_sphere(10, 8)
        tme = make_mesh(name + "_tip", us, uf); tme.materials.append(tip_mat)
        tip = obj_from_mesh(name + "_tip", tme, parent=parent)
        for f in range(f0, f1 + 1, 2):
            u = (f - f0) / max(1, f1 - f0)
            # ease matches linear colour interpolation approximately (bezier) -> sample object colour curve
            o.animation_data.action.fcurves[0]
            tip.keyframe_insert("location", frame=f)
        tip["path"] = 1
        return o, P, L
    return o, P, L
