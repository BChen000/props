import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math, json
import numpy as np
from mathutils import Vector
import settings as C

CAM_AZ = 225.0
CAM_PITCH = 30.0
CAM_DIST = 5.0
CAM_TARGET = (0.0, 0.0, 0.9)
CAM_LENS = 55.0
BG_COL = (0.60, 0.62, 0.88)


def srgb2lin(c):
    c = np.asarray(c, float)
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = C.FPS
    return sc


def node(nt, t, loc=(0, 0), **kw):
    n = nt.nodes.new(t)
    n.location = loc
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def mesh_obj(name, verts, faces, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def studio_mesh():
    prof = []
    for i in range(40):
        y = -16 + i * (16 + 3.0) / 39
        prof.append((y, 0.0))
    R = 2.4
    for i in range(1, 25):
        a = (math.pi / 2) * i / 24
        prof.append((3.0 + R * math.sin(a), R - R * math.cos(a)))
    for i in range(1, 12):
        prof.append((3.0 + R, R + i * 1.4))
    xs = np.linspace(-16, 16, 33)
    verts, faces = [], []
    for x in xs:
        for (y, z) in prof:
            verts.append((x, y, z))
    n = len(prof)
    for i in range(len(xs) - 1):
        for j in range(n - 1):
            a = i * n + j
            faces.append((a, a + n, a + n + 1, a + 1))
    return verts, faces


def studio_material():
    m = bpy.data.materials.new("Studio")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (*srgb2lin(BG_COL), 1)
    b.inputs['Roughness'].default_value = 0.6
    return m


def glass_materials():
    mats = []
    for k, col in enumerate(C.PANE_COLORS):
        lc = srgb2lin(col)
        for edge in (False, True):
            m = bpy.data.materials.new(f"Glass{k}{'E' if edge else 'F'}")
            m.use_nodes = True
            nt = m.node_tree
            nt.nodes.clear()
            L = nt.links.new
            def M(op, x=None, y=None, loc=(0, 0)):
                n = node(nt, 'ShaderNodeMath', loc, operation=op)
                for i, v in enumerate((x, y)):
                    if v is None:
                        continue
                    if isinstance(v, (int, float)):
                        n.inputs[i].default_value = v
                    else:
                        L(v, n.inputs[i])
                return n.outputs[0]
            out = node(nt, 'ShaderNodeOutputMaterial', (1400, 0))
            geo = node(nt, 'ShaderNodeNewGeometry', (-900, 0))
            neg = node(nt, 'ShaderNodeVectorMath', (-700, 100), operation='SCALE')
            L(geo.outputs['Incoming'], neg.inputs[0])
            neg.inputs['Scale'].default_value = -1.0
            refl = node(nt, 'ShaderNodeVectorMath', (-500, 100), operation='REFLECT')
            L(neg.outputs[0], refl.inputs[0])
            L(geo.outputs['Normal'], refl.inputs[1])
            sep = node(nt, 'ShaderNodeSeparateXYZ', (-300, 100))
            L(refl.outputs[0], sep.inputs[0])
            rz = M('MAXIMUM', sep.outputs['Z'], 0.06)
            u = M('DIVIDE', M('ADD', sep.outputs['X'], M('MULTIPLY', sep.outputs['Y'], -0.6)), rz)
            strips = None
            for c0 in (-0.95, -0.25, 0.45):
                dd = M('ABSOLUTE', M('SUBTRACT', u, c0))
                band = M('POWER', M('MAXIMUM', M('SUBTRACT', 1.0, M('DIVIDE', dd, 0.13)), 0.0), 2.0)
                strips = band if strips is None else M('ADD', strips, band)
            up = M('POWER', M('MAXIMUM', sep.outputs['Z'], 0.0), 1.5)
            lw = node(nt, 'ShaderNodeLayerWeight', (-300, 400))
            lw.inputs['Blend'].default_value = 0.12 if not edge else 0.35
            fr = node(nt, 'ShaderNodeMapRange', (-100, 400))
            L(lw.outputs['Fresnel'], fr.inputs[0])
            fr.inputs[3].default_value = 0.06 if not edge else 0.25
            fr.inputs[4].default_value = 0.95
            F = fr.outputs[0]
            em1 = node(nt, 'ShaderNodeEmission', (900, -150))
            em1.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1)
            L(M('MULTIPLY', M('MULTIPLY', strips, 5.0), F), em1.inputs['Strength'])
            em2 = node(nt, 'ShaderNodeEmission', (900, -300))
            sc_ = srgb2lin(BG_COL)
            em2.inputs['Color'].default_value = (*[0.55 * x + 0.45 * y for x, y in zip(sc_, lc)], 1)
            L(M('MULTIPLY', M('MULTIPLY', up, 0.55), F), em2.inputs['Strength'])
            em3 = node(nt, 'ShaderNodeEmission', (900, -450))
            em3.inputs['Color'].default_value = (*lc, 1)
            em3.inputs['Strength'].default_value = 0.07 if not edge else 0.12
            tr = node(nt, 'ShaderNodeBsdfTransparent', (900, 150))
            if edge:
                tc = [0.06 + 0.45 * c ** 1.8 for c in lc]
            else:
                tc = [0.28 + 0.72 * c for c in lc]
            tcn = node(nt, 'ShaderNodeMix', (700, 150), data_type='RGBA')
            tcn.inputs['A'].default_value = (*tc, 1)
            tcn.inputs['B'].default_value = (0, 0, 0, 1)
            L(F, tcn.inputs['Factor'])
            L(tcn.outputs['Result'], tr.inputs['Color'])
            a1 = node(nt, 'ShaderNodeAddShader', (1050, -200))
            L(em1.outputs[0], a1.inputs[0])
            L(em2.outputs[0], a1.inputs[1])
            a2 = node(nt, 'ShaderNodeAddShader', (1100, -350))
            L(a1.outputs[0], a2.inputs[0])
            L(em3.outputs[0], a2.inputs[1])
            ad = node(nt, 'ShaderNodeAddShader', (1150, 0))
            L(tr.outputs[0], ad.inputs[0])
            L(a2.outputs[0], ad.inputs[1])
            L(ad.outputs[0], out.inputs[0])
            try:
                m.cycles.emission_sampling = 'NONE'
            except Exception:
                pass
            mats.append(m)
    return mats


def steel_material():
    m = bpy.data.materials.new("Steel")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Base Color'].default_value = (0.80, 0.81, 0.84, 1)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.09
    return m


def pane_object(k, mats):
    h, t = C.HALF, C.T / 2
    v = [(-h, -h, -t), (h, -h, -t), (h, h, -t), (-h, h, -t), (-h, -h, t), (h, -h, t), (h, h, t), (-h, h, t)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(f"Pane{k}", v, f)
    ob.data.materials.append(mats[2 * k])
    ob.data.materials.append(mats[2 * k + 1])
    for i, poly in enumerate(ob.data.polygons):
        poly.material_index = 0 if i < 2 else 1
    ob.location = (0, 0, C.pane_z(k))
    bv = ob.modifiers.new("Bevel", 'BEVEL')
    bv.width = 0.0025
    bv.segments = 2
    bv.limit_method = 'NONE'
    return ob


class Shards:
    def __init__(self, info, mats, name="Shards"):
        self.n = len(info)
        verts, faces, fmat = [], [], []
        owner = []
        off = 0
        for i, s in enumerate(info):
            vs = s['verts']
            verts.extend(vs)
            owner.extend([i] * len(vs))
            for f, m in zip(s['faces'], s['mats']):
                faces.append([off + j for j in f])
                fmat.append(2 * s['pane'] + m)
            off += len(vs)
        self.local = np.array(verts, np.float32)
        self.owner = np.array(owner, np.int32)
        self.spawn = np.array([s['spawn'] for s in info], np.int32)
        ob = mesh_obj(name, self.local, faces)
        for m in mats:
            ob.data.materials.append(m)
        ob.data.polygons.foreach_set('material_index', np.array(fmat, np.int32))
        ob.data.update()
        self.ob = ob

    def pose(self, P, Q, frame):
        if self.n == 0:
            return
        x, y, z, w = Q[:, 0], Q[:, 1], Q[:, 2], Q[:, 3]
        Rm = np.empty((self.n, 3, 3), np.float32)
        Rm[:, 0, 0] = 1 - 2 * (y * y + z * z); Rm[:, 0, 1] = 2 * (x * y - z * w); Rm[:, 0, 2] = 2 * (x * z + y * w)
        Rm[:, 1, 0] = 2 * (x * y + z * w); Rm[:, 1, 1] = 1 - 2 * (x * x + z * z); Rm[:, 1, 2] = 2 * (y * z - x * w)
        Rm[:, 2, 0] = 2 * (x * z - y * w); Rm[:, 2, 1] = 2 * (y * z + x * w); Rm[:, 2, 2] = 1 - 2 * (x * x + y * y)
        Pp = np.nan_to_num(P, nan=0.0).copy()
        hidden = (self.spawn > frame) | np.isnan(P[:, 0])
        Pp[hidden] = (0, 0, -50)
        wv = np.einsum('vij,vj->vi', Rm[self.owner], self.local) + Pp[self.owner]
        self.ob.data.vertices.foreach_set('co', wv.astype(np.float32).ravel())
        self.ob.data.update()


def add_camera():
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("Cam")
    cam.lens = CAM_LENS
    cam.sensor_fit = 'VERTICAL'
    cam.sensor_height = 36.0
    ob = bpy.data.objects.new("Cam", cam)
    sc.collection.objects.link(ob)
    az, pt = math.radians(CAM_AZ), math.radians(CAM_PITCH)
    t = Vector(CAM_TARGET)
    ob.location = t + CAM_DIST * Vector((math.cos(az) * math.cos(pt), math.sin(az) * math.cos(pt), math.sin(pt)))
    d = t - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = ob
    return ob


def area_light(name, loc, target, size, power, color=(1, 1, 1), shape='RECTANGLE', size_y=None):
    sc = bpy.context.scene
    L = bpy.data.lights.new(name, 'AREA')
    L.shape = shape
    L.size = size
    if size_y is not None:
        L.size_y = size_y
    L.energy = power
    L.color = color
    ob = bpy.data.objects.new(name, L)
    sc.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def add_lights():
    area_light("Key", (-2.6, -1.4, 4.2), (0, 0, 0.6), 2.6, 160, (1.0, 0.97, 0.93))
    area_light("Fill", (2.8, -2.2, 2.6), (0, 0, 0.6), 3.5, 55, (0.92, 0.95, 1.0))
    rim = area_light("Rim", (1.0, 3.2, 3.0), (0, 0, 0.8), 2.0, 160, (1.0, 1.0, 1.0))
    rim.visible_diffuse = False
    for i, x in enumerate((-0.55, 0.0, 0.55)):
        ob = area_light(f"Strip{i}", (x - 0.6, x + 0.3, 3.3), (x - 0.25, x + 0.1, 0.0), 2.4, 110, (1, 1, 1), size_y=0.12)
        ob.visible_diffuse = False
    sc = bpy.context.scene
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*srgb2lin(BG_COL), 1)
    bg.inputs[1].default_value = 0.5


def build(stage_info=None):
    sc = bpy.context.scene
    sv, sf = studio_mesh()
    studio = mesh_obj("Studio", sv, sf, smooth=True)
    studio.data.materials.append(studio_material())
    mats = glass_materials()
    panes = [pane_object(k, mats) for k in range(C.N_P)]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=(0, 0, 3))
    ball = bpy.context.object
    ball.name = "Ball"
    bpy.ops.object.shade_smooth()
    ball.data.materials.append(steel_material())
    cam = add_camera()
    add_lights()
    return studio, mats, panes, ball, cam


def setup_cycles(sc, w, h, spp=16):
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = spp
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
        cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        cy.denoising_prefilter = 'FAST'
        cy.denoising_quality = 'BALANCED'
    except Exception:
        pass
    cy.max_bounces = 12
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 3
    cy.transmission_bounces = 2
    cy.transparent_max_bounces = 32
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_indirect = 5.0
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
