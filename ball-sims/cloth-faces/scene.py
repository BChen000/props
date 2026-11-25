"""Blender scene builders: platform + hole + shaft, marble or duck hero, cloth materials, camera, lights,
and the window-mapped plate emission used by render_frames.py. Imported by the other scripts (not run directly)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as CFG
import bpy, bmesh, math, numpy as np
from mathutils import Vector, Matrix

FPS = CFG.FPS
R = 0.5
MARBLE_Z = 0.32
HOLE = 1.1
SHAFT = 9.0
PLAT_R = 5.6
PLAT_T = 0.6
SHEET = 2.0
STACK_Z0 = 2.35
STACK_GAP = 0.055
CAM_AZ = 45.0
CAM_PITCH = 20.0
CAM_DIST = 9.0
CAM_TARGET = (0.0, 0.0, 1.2)
CAM_LENS = 55.0
SUN_EL = 58.0
SUN_AZ = 200.0
HERO = CFG.HERO
DUCK_Z = 0.0
DUCK_YAW = 185.0

STAGES = [
    dict(n=1, color=(0.92, 0.16, 0.18), name="1"),
    dict(n=2, color=(0.98, 0.45, 0.10), name="4"),
    dict(n=4, color=(0.98, 0.80, 0.12), name="16"),
    dict(n=8, color=(0.20, 0.80, 0.35), name="64"),
    dict(n=16, color=(0.20, 0.55, 0.98), name="256"),
    dict(n=100, color=(0.62, 0.30, 0.95), name="10,000"),
    dict(n=250, color=(1.00, 0.66, 0.12), name="1,000,000", subdiv=2, gold=True),
]


def srgb2lin(c):
    c = np.asarray(c, float)
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.unit_settings.system = 'METRIC'
    return sc


def mesh_obj(name, verts, faces, smooth=False, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def grid(n, size=SHEET):
    s = np.linspace(-size / 2, size / 2, n + 1)
    xx, yy = np.meshgrid(s, s, indexing='xy')
    v = np.stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)], 1)
    idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    f = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    uv = (v[:, :2] + size / 2) / size
    return v, f, uv


def set_uv(me, uv):
    lay = me.uv_layers.new(name="UVMap")
    loops = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", loops)
    lay.data.foreach_set("uv", uv[loops].astype(np.float32).ravel())


def platform_mesh():
    bm = bmesh.new()
    seg = 160
    H = HOLE
    outer_top, outer_bot = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        outer_top.append(bm.verts.new((PLAT_R * math.cos(a), PLAT_R * math.sin(a), 0)))
        outer_bot.append(bm.verts.new((PLAT_R * math.cos(a), PLAT_R * math.sin(a), -PLAT_T)))
    sq = [(H, H), (-H, H), (-H, -H), (H, -H)]
    per = seg // 4
    inner_top, inner_bot = [], []
    for k in range(4):
        x0, y0 = sq[k]
        x1, y1 = sq[(k + 1) % 4]
        for j in range(per):
            t = j / per
            p = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            inner_top.append(bm.verts.new((p[0], p[1], 0)))
            inner_bot.append(bm.verts.new((p[0], p[1], -PLAT_T)))
    off = seg // 8
    for i in range(seg):
        j = (i + 1) % seg
        o0, o1 = outer_top[(i + off) % seg], outer_top[(j + off) % seg]
        bm.faces.new((o0, o1, inner_top[j], inner_top[i]))
        b0, b1 = outer_bot[(i + off) % seg], outer_bot[(j + off) % seg]
        bm.faces.new((inner_bot[i], inner_bot[j], b1, b0))
        bm.faces.new((outer_top[i], outer_bot[i], outer_bot[j], outer_top[j]))
    me = bpy.data.meshes.new("Platform")
    bm.to_mesh(me)
    bm.free()
    return me


def shaft_mesh():
    H = HOLE
    v, f = [], []
    rings = [0.0, -PLAT_T, -2.0, -4.0, -SHAFT]
    sq = [(H, H), (-H, H), (-H, -H), (H, -H)]
    for z in rings:
        for (x, y) in sq:
            v.append((x, y, z))
    for r in range(len(rings) - 1):
        for k in range(4):
            a, b = r * 4 + k, r * 4 + (k + 1) % 4
            f.append((a, b, b + 4, a + 4))
    base = len(v)
    for (x, y) in sq:
        v.append((x, y, -SHAFT))
    f.append((base + 3, base + 2, base + 1, base))
    return v, f


def node(nt, t, loc=(0, 0), **kw):
    n = nt.nodes.new(t)
    n.location = loc
    for k, val in kw.items():
        setattr(n, k, val)
    return n


def wood_material(name="Wood", dark=1.0, vertical=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    def M(op, a=None, b=None, c=None, loc=(0, 0)):
        n = node(nt, 'ShaderNodeMath', loc, operation=op)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]
    out = node(nt, 'ShaderNodeOutputMaterial', (1900, 0))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled', (1300, 0))
    cheap = node(nt, 'ShaderNodeBsdfDiffuse', (1300, -400))
    cavg = srgb2lin((0.72, 0.54, 0.35))
    cheap.inputs['Color'].default_value = (*[x * dark for x in cavg], 1)
    cat = node(nt, 'ShaderNodeAttribute', (1300, 300))
    cat.attribute_type = 'OBJECT'
    cat.attribute_name = 'cheap'
    cmx = node(nt, 'ShaderNodeMixShader', (1650, 0))
    L(cat.outputs['Fac'], cmx.inputs[0])
    L(bsdf.outputs[0], cmx.inputs[1])
    L(cheap.outputs[0], cmx.inputs[2])
    L(cmx.outputs[0], out.inputs[0])
    tc = node(nt, 'ShaderNodeTexCoord', (-1600, 0))
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-1400, 0))
    L(tc.outputs['Object'], sep.inputs[0])
    X, Y, Z = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']
    if vertical:
        X, Y, Z = Z, M('ADD', sep.outputs['X'], sep.outputs['Y']), M('MULTIPLY', M('SUBTRACT', sep.outputs['X'], sep.outputs['Y']), 0.5)
    pw = 0.42
    yq = M('DIVIDE', Y, pw)
    pid = M('FLOOR', yq)
    yf = M('FRACT', yq)
    wn1 = node(nt, 'ShaderNodeTexWhiteNoise', (-1000, 400), noise_dimensions='1D')
    L(pid, wn1.inputs['W'])
    r1 = wn1.outputs['Value']
    pid2 = M('ADD', pid, 31.7)
    wn2 = node(nt, 'ShaderNodeTexWhiteNoise', (-1000, 250), noise_dimensions='1D')
    L(pid2, wn2.inputs['W'])
    r2 = wn2.outputs['Value']
    xs = M('MULTIPLY_ADD', r1, 2.7, X)
    jf = M('FRACT', M('DIVIDE', xs, 2.7))
    def seam(src, w):
        return M('GREATER_THAN', M('PINGPONG', src, 0.5), w)
    smask = M('MULTIPLY', seam(yf, 0.006), seam(jf, 0.0022))
    lx = M('MULTIPLY_ADD', r1, 9.0, X)
    ly = M('MULTIPLY_ADD', M('SUBTRACT', yf, 0.5), pw, M('MULTIPLY_ADD', r2, 0.5, -0.25))
    lz = M('MULTIPLY_ADD', r2, 0.3, M('ADD', Z, 0.28))
    cv = node(nt, 'ShaderNodeCombineXYZ', (-500, 600))
    L(lx, cv.inputs['X']); L(ly, cv.inputs['Y']); L(lz, cv.inputs['Z'])
    dmap = node(nt, 'ShaderNodeMapping', (-350, 800))
    L(cv.outputs[0], dmap.inputs['Vector'])
    dmap.inputs['Scale'].default_value = (0.6, 4.0, 4.0)
    dn = node(nt, 'ShaderNodeTexNoise', (-150, 800))
    L(dmap.outputs[0], dn.inputs['Vector'])
    dn.inputs['Scale'].default_value = 1.3
    dn.inputs['Detail'].default_value = 3.0
    dsub = node(nt, 'ShaderNodeVectorMath', (50, 800), operation='SUBTRACT')
    L(dn.outputs['Color'], dsub.inputs[0])
    dsub.inputs[1].default_value = (0.5, 0.5, 0.5)
    dsc = node(nt, 'ShaderNodeVectorMath', (200, 800), operation='MULTIPLY')
    L(dsub.outputs[0], dsc.inputs[0])
    dsc.inputs[1].default_value = (0.0, 0.05, 0.05)
    vadd = node(nt, 'ShaderNodeVectorMath', (350, 650), operation='ADD')
    L(cv.outputs[0], vadd.inputs[0]); L(dsc.outputs[0], vadd.inputs[1])
    rings = node(nt, 'ShaderNodeTexWave', (500, 650), wave_type='RINGS', rings_direction='X', wave_profile='SIN')
    L(vadd.outputs[0], rings.inputs['Vector'])
    rings.inputs['Scale'].default_value = 5.5
    rings.inputs['Distortion'].default_value = 0.0
    rf = rings.outputs['Fac']
    sharp = M('POWER', rf, 3.0)
    fmap = node(nt, 'ShaderNodeMapping', (-350, 1100))
    L(cv.outputs[0], fmap.inputs['Vector'])
    fmap.inputs['Scale'].default_value = (3.0, 160.0, 160.0)
    fib = node(nt, 'ShaderNodeTexNoise', (-150, 1100))
    L(fmap.outputs[0], fib.inputs['Vector'])
    fib.inputs['Scale'].default_value = 3.0
    fib.inputs['Detail'].default_value = 2.0
    fibv = M('MULTIPLY_ADD', fib.outputs['Fac'], 0.5, 0.75)
    c_light = srgb2lin((0.80, 0.61, 0.40))
    c_dark = srgb2lin((0.62, 0.43, 0.25))
    cm = node(nt, 'ShaderNodeMix', (800, 500), data_type='RGBA')
    L(sharp, cm.inputs['Factor'])
    cm.inputs['A'].default_value = (*[x * dark for x in c_light], 1)
    cm.inputs['B'].default_value = (*[x * dark for x in c_dark], 1)
    tint = M('MULTIPLY', M('MULTIPLY_ADD', r1, 0.22, 0.86), fibv)
    tm = node(nt, 'ShaderNodeMix', (1000, 450), data_type='RGBA', blend_type='MULTIPLY')
    tm.inputs['Factor'].default_value = 1.0
    L(cm.outputs['Result'], tm.inputs['A'])
    tcol = node(nt, 'ShaderNodeCombineXYZ', (850, 300))
    L(tint, tcol.inputs['X']); L(M('MULTIPLY', tint, 0.97), tcol.inputs['Y']); L(M('MULTIPLY', tint, 0.93), tcol.inputs['Z'])
    L(tcol.outputs[0], tm.inputs['B'])
    sm = node(nt, 'ShaderNodeMix', (1150, 350), data_type='RGBA')
    L(smask, sm.inputs['Factor'])
    sm.inputs['A'].default_value = (*[x * 0.18 for x in c_dark], 1)
    L(tm.outputs['Result'], sm.inputs['B'])
    L(sm.outputs['Result'], bsdf.inputs['Base Color'])
    L(M('MULTIPLY_ADD', sharp, 0.12, 0.42), bsdf.inputs['Roughness'])
    bump = node(nt, 'ShaderNodeBump', (1100, -300))
    bump.inputs['Strength'].default_value = 0.3
    bump.inputs['Distance'].default_value = 0.002
    L(M('MULTIPLY_ADD', M('SUBTRACT', 1.0, smask), -1.0, M('MULTIPLY', sharp, 0.3)), bump.inputs['Height'])
    L(bump.outputs[0], bsdf.inputs['Normal'])
    return m


def simple_material(name, color, rough=0.5, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    return m


def glass_material():
    m = bpy.data.materials.new("Glass")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (0.93, 0.97, 1.0, 1)
    b.inputs['Roughness'].default_value = 0.0
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.5
    return m


def vane_material(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (*srgb2lin(color), 1)
    b.inputs['Roughness'].default_value = 0.35
    b.inputs['Subsurface Weight'].default_value = 0.0
    b.inputs['Emission Color'].default_value = (*srgb2lin(color), 1)
    b.inputs['Emission Strength'].default_value = 0.25
    return m


def cloth_material(name, color, n, gold=False, opacity=0.78):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = node(nt, 'ShaderNodeOutputMaterial', (1200, 0))
    col = srgb2lin(color)
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled', (600, 150))
    bsdf.inputs['Base Color'].default_value = (*col, 1)
    bsdf.inputs['Roughness'].default_value = 0.24 if not gold else 0.28
    bsdf.inputs['Metallic'].default_value = 0.0 if not gold else 1.0
    bsdf.inputs['Coat Weight'].default_value = 0.12 if not gold else 0.0
    bsdf.inputs['Coat Roughness'].default_value = 0.08
    bsdf.inputs['Sheen Weight'].default_value = 0.1
    bsdf.inputs['Sheen Tint'].default_value = (*col, 1)
    if gold:
        bsdf.inputs['Specular Tint'].default_value = (*srgb2lin((1.0, 0.80, 0.35)), 1)
        bsdf.inputs['Sheen Weight'].default_value = 0.0
    tr = node(nt, 'ShaderNodeBsdfTransparent', (600, -150))
    tcol = [0.35 + 0.65 * c for c in col]
    tr.inputs['Color'].default_value = (*tcol, 1)
    lw = node(nt, 'ShaderNodeLayerWeight', (0, 300))
    lw.inputs['Blend'].default_value = 0.35
    op = node(nt, 'ShaderNodeMapRange', (250, 300))
    L(lw.outputs['Facing'], op.inputs[0])
    op.inputs[3].default_value = opacity
    op.inputs[4].default_value = 0.97
    fac = op.outputs[0]
    if n <= 128:
        uvn = node(nt, 'ShaderNodeUVMap', (-600, -300))
        sep = node(nt, 'ShaderNodeSeparateXYZ', (-450, -300))
        L(uvn.outputs[0], sep.inputs[0])
        w = 0.012 if n <= 4 else (0.016 if n <= 16 else 0.03)
        ws = []
        for i, ax in enumerate(('X', 'Y')):
            mu = node(nt, 'ShaderNodeMath', (-300, -250 - 150 * i), operation='MULTIPLY')
            L(sep.outputs[ax], mu.inputs[0]); mu.inputs[1].default_value = float(n)
            fr = node(nt, 'ShaderNodeMath', (-150, -250 - 150 * i), operation='PINGPONG')
            L(mu.outputs[0], fr.inputs[0]); fr.inputs[1].default_value = 0.5
            lt = node(nt, 'ShaderNodeMath', (0, -250 - 150 * i), operation='LESS_THAN')
            L(fr.outputs[0], lt.inputs[0]); lt.inputs[1].default_value = w * n * 0.5 if n > 1 else w
            ws.append(lt)
        mx = node(nt, 'ShaderNodeMath', (150, -300), operation='MAXIMUM')
        L(ws[0].outputs[0], mx.inputs[0]); L(ws[1].outputs[0], mx.inputs[1])
        cm = node(nt, 'ShaderNodeMix', (400, 400), data_type='RGBA')
        L(mx.outputs[0], cm.inputs['Factor'])
        cm.inputs['A'].default_value = (*col, 1)
        cm.inputs['B'].default_value = (*[c * 0.22 for c in col], 1)
        L(cm.outputs['Result'], bsdf.inputs['Base Color'])
        om = node(nt, 'ShaderNodeMath', (400, 250), operation='MAXIMUM')
        L(op.outputs[0], om.inputs[0]); L(mx.outputs[0], om.inputs[1])
        fac = om.outputs[0]
    mix = node(nt, 'ShaderNodeMixShader', (900, 0))
    L(fac, mix.inputs[0])
    L(tr.outputs[0], mix.inputs[1])
    L(bsdf.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs[0])
    return m


def add_marble(coll=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=R, location=(0, 0, MARBLE_Z))
    mb = bpy.context.object
    mb.name = "Marble"
    bpy.ops.object.shade_smooth()
    mb.data.materials.append(glass_material())
    vane_cols = [(0.93, 0.25, 0.27), (0.98, 0.79, 0.20), (0.24, 0.51, 0.97)]
    nz, nr = 48, 10
    for k in range(3):
        verts, faces = [], []
        for i in range(nz + 1):
            z = -0.62 * R + 1.24 * R * i / nz
            rad = 0.44 * R * math.sqrt(max(0.0, 1 - (z / (0.64 * R)) ** 2))
            ang = 2 * math.pi * k / 3 + 2.2 * (z / R)
            for j in range(nr + 1):
                rr = 0.02 * R + rad * j / nr
                bulge = 0.025 * R * math.sin(math.pi * j / nr) * math.sqrt(max(0, 1 - (z / (0.64 * R)) ** 2))
                verts.append((rr * math.cos(ang) - bulge * math.sin(ang), rr * math.sin(ang) + bulge * math.cos(ang), z))
        for i in range(nz):
            for j in range(nr):
                a = i * (nr + 1) + j
                faces.append((a, a + 1, a + nr + 2, a + nr + 1))
        vo = mesh_obj(f"Vane{k}", verts, faces, smooth=True)
        vo.location = (0, 0, MARBLE_Z)
        vo.rotation_euler = (0.35, -0.2, 0.4)
        vo.data.materials.append(vane_material(f"VaneMat{k}", vane_cols[k]))
        vo.parent = None
    return mb


def plastic_material(name, color, rough=0.3, coat=0.35):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (*srgb2lin(color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.08
    return m


def add_duck():
    import sys as _s
    _s.path.insert(0, CFG.HERE)
    import duck as D
    (bv, bf), (kv, kf), eyes = D.build()
    yaw = math.radians(DUCK_YAW)
    objs = []
    body = mesh_obj("Hero", bv, bf, smooth=True)
    body.data.materials.append(plastic_material("DuckYellow", (1.0, 0.80, 0.10)))
    beak = mesh_obj("HeroBeak", kv, kf, smooth=True)
    beak.data.materials.append(plastic_material("DuckBeak", (1.0, 0.42, 0.06), rough=0.28))
    objs += [body, beak]
    eye_mat = plastic_material("DuckEye", (0.02, 0.02, 0.025), rough=0.08, coat=0.6)
    for i, e in enumerate(eyes):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.048, location=e)
        eo = bpy.context.object
        eo.name = f"HeroEye{i}"
        bpy.ops.object.shade_smooth()
        eo.data.materials.append(eye_mat)
        objs.append(eo)
    bpy.context.view_layer.update()
    R = Matrix.Translation((0, 0, DUCK_Z)) @ Matrix.Rotation(yaw, 4, 'Z')
    for o in objs:
        o.matrix_world = R @ o.matrix_world.copy()
    bpy.context.view_layer.update()
    return objs


def build_set(with_materials=True):
    sc = bpy.context.scene
    pm = platform_mesh()
    plat = bpy.data.objects.new("Platform", pm)
    sc.collection.objects.link(plat)
    sv, sf = shaft_mesh()
    shaft = mesh_obj("Shaft", sv, sf)
    if with_materials:
        wood = wood_material()
        plat.data.materials.append(wood)
        shaft.data.materials.append(wood_material("WoodDark", dark=0.75, vertical=True))
    if HERO == 'duck':
        hero = add_duck()
        return plat, shaft, hero
    mb = add_marble()
    return plat, shaft, [mb]


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def add_camera():
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("Cam")
    cam.lens = CAM_LENS
    cam.sensor_fit = 'VERTICAL'
    cam.sensor_height = 36.0
    ob = bpy.data.objects.new("Cam", cam)
    sc.collection.objects.link(ob)
    az, pt = math.radians(CAM_AZ + 180), math.radians(CAM_PITCH)
    t = Vector(CAM_TARGET)
    ob.location = t + CAM_DIST * Vector((math.cos(az) * math.cos(pt), math.sin(az) * math.cos(pt), math.sin(pt)))
    look_at(ob, t)
    sc.camera = ob
    return ob


def add_lights(world_strength=1.0):
    sc = bpy.context.scene
    sun = bpy.data.lights.new("Sun", 'SUN')
    sun.energy = 2.9
    sun.angle = math.radians(3.0)
    sun.color = srgb2lin((1.0, 0.95, 0.88))
    so = bpy.data.objects.new("Sun", sun)
    sc.collection.objects.link(so)
    el, az = math.radians(SUN_EL), math.radians(SUN_AZ)
    d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
    so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputWorld', (600, 0))
    bg = node(nt, 'ShaderNodeBackground', (400, 0))
    sky = node(nt, 'ShaderNodeTexSky', (0, 0))
    types = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for t in ('MULTIPLE_SCATTERING', 'SINGLE_SCATTERING', 'NISHITA', 'HOSEK_WILKIE'):
        if t in types:
            sky.sky_type = t
            break
    try:
        sky.sun_elevation = el
        sky.sun_rotation = az
        sky.sun_disc = False
        sky.altitude = 200.0
        sky.air_density = 1.0
        sky.aerosol_density = 1.2
    except Exception as ex:
        print("sky", ex)
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.2 * world_strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    return so, sky


def setup_cycles(sc, w, h, spp=16, denoise=True):
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = spp
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03
    cy.adaptive_min_samples = min(8, spp)
    cy.use_denoising = denoise
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
        cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        cy.denoising_prefilter = 'ACCURATE'
    except Exception:
        pass
    cy.max_bounces = 8
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 3
    cy.transmission_bounces = 6
    cy.transparent_max_bounces = 24
    cy.volume_bounces = 0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_indirect = 4.0
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.threads_mode = 'AUTO'


def sheet_object(name, n, mat, z=0.0, smooth=False, subdiv=0):
    v, f, uv = grid(n)
    v[:, 2] = z
    ob = mesh_obj(name, v, f, smooth=smooth)
    set_uv(ob.data, uv)
    ob.data.materials.append(mat)
    if subdiv:
        md = ob.modifiers.new("Sub", 'SUBSURF')
        md.levels = 0
        md.render_levels = subdiv
    return ob


def build_stack(mats, first=0):
    obs = []
    for i, st in enumerate(STAGES):
        if i < first:
            obs.append(None)
            continue
        ob = sheet_object(f"Stack{i}", max(1, min(st['n'], 16)), mats[i], z=STACK_Z0 + STACK_GAP * i)
        ob.visible_shadow = False
        obs.append(ob)
    return obs


def stage_materials():
    return [cloth_material(f"Cloth{i}", st['color'], st['n'], gold=st.get('gold', False)) for i, st in enumerate(STAGES)]


def window_emission_group(world=False):
    gname = "WinBGWorld" if world else "WinBG"
    if gname in bpy.data.node_groups:
        return bpy.data.node_groups[gname]
    g = bpy.data.node_groups.new(gname, 'ShaderNodeTree')
    g.interface.new_socket("Shader", in_out='INPUT', socket_type='NodeSocketShader')
    g.interface.new_socket("Shader", in_out='OUTPUT', socket_type='NodeSocketShader')
    gi = g.nodes.new('NodeGroupInput'); gi.location = (-600, 0)
    go = g.nodes.new('NodeGroupOutput'); go.location = (400, 0)
    tc = g.nodes.new('ShaderNodeTexCoord'); tc.location = (-600, -300)
    tex = g.nodes.new('ShaderNodeTexImage'); tex.location = (-350, -300)
    tex.name = "BGTex"
    tex.interpolation = 'Closest'
    tex.extension = 'EXTEND'
    em = g.nodes.new('ShaderNodeEmission'); em.location = (-100, -300)
    lp = g.nodes.new('ShaderNodeLightPath'); lp.location = (-350, 200)
    at = g.nodes.new('ShaderNodeAttribute'); at.location = (-350, 400)
    at.attribute_type = 'OBJECT'
    at.attribute_name = 'bgmix'
    mul = g.nodes.new('ShaderNodeMath'); mul.location = (-100, 250)
    mul.operation = 'MULTIPLY'
    mx = g.nodes.new('ShaderNodeMixShader'); mx.location = (150, 0)
    L = g.links.new
    L(tc.outputs['Window'], tex.inputs['Vector'])
    L(tex.outputs['Color'], em.inputs['Color'])
    L(lp.outputs['Is Camera Ray'], mul.inputs[0])
    if world:
        mul.inputs[1].default_value = 1.0
    else:
        L(at.outputs['Fac'], mul.inputs[1])
    L(mul.outputs[0], mx.inputs[0])
    L(gi.outputs[0], mx.inputs[1])
    L(em.outputs[0], mx.inputs[2])
    L(mx.outputs[0], go.inputs[0])
    return g


def no_emission_sampling():
    for m in bpy.data.materials:
        try:
            m.cycles.emission_sampling = 'NONE'
        except Exception as ex:
            print('emission_sampling', ex)


def wrap_with_bg(nt, is_world=False):
    out = [n for n in nt.nodes if n.bl_idname in ('ShaderNodeOutputMaterial', 'ShaderNodeOutputWorld')][0]
    src = out.inputs[0].links[0].from_socket
    gn = nt.nodes.new('ShaderNodeGroup')
    gn.node_tree = window_emission_group(is_world)
    gn.location = (out.location[0] - 200, out.location[1] - 200)
    nt.links.new(src, gn.inputs[0])
    nt.links.new(gn.outputs[0], out.inputs[0])
    return gn


def bg_image(name, w, h, world=None):
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Linear Rec.709'
    for wg in ((False, True) if world is None else (world,)):
        window_emission_group(wg).nodes["BGTex"].image = img
    return img


def set_bg_pixels(img, rgb):
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 4), np.float32)
    a[..., :3] = rgb[::-1]
    img.pixels.foreach_set(a.ravel())
    img.update()
    img.update_tag()
