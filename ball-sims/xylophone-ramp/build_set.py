"""Builds the xylophone-ramp set in Blender and saves it.

Run:  python3 build_set.py                      (Blender as a Python module, bpy 5.3.0)
  or: blender --background --python build_set.py

Writes next to this file:
  xylophone-ramp.blend, xylophone-ramp.glb
  build/scene_meta.json   (camera + light matrices, stand heights; read by the other props)
  build/basket_tube.npz   (basket rope mesh; the physics uses it as the collider)
Geometry and tuning live in params.py. Looks (colors, lights, camera, side props) are set below.
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ======================================================================= SETTINGS
# Colors are linear RGB, exactly as typed into Blender's Principled BSDF.
BACKDROP_COLOR = (0.30, 0.305, 0.315)
BAR_COLOR = (0.80, 0.81, 0.83)          # brushed aluminum (metallic)
SCREW_COLOR = (0.55, 0.55, 0.57)
FELT_COLOR = (0.22, 0.025, 0.035)
RAIL_COLOR = (0.085, 0.048, 0.028)
STAND_COLOR = (0.018, 0.018, 0.02)
POT_COLOR = (0.50, 0.21, 0.11)
SOIL_COLOR = (0.06, 0.04, 0.03)
CACTUS_COLOR = (0.05, 0.16, 0.06)
BLOCK_COLORS = [(0.85, 0.42, 0.48), (0.35, 0.68, 0.62), (0.92, 0.78, 0.36)]
BASKET_DARK = (0.42, 0.32, 0.19)
BASKET_LIGHT = (0.62, 0.51, 0.33)
BASKET_STITCH = (0.60, 0.50, 0.33)

CACTUS_POS = (-0.272, 0.50, 0.0)
BLOCKS_POS = (0.262, 0.47, 0.0)

# (location, target, size, power in watts)
KEY_LIGHT = ((-0.62, -0.95, 1.30), (0.0, 0.15, 0.10), (0.9, 0.9), 18.0)
TOP_LIGHT = ((0.10, 0.45, 1.45), (0.0, 0.35, 0.0), (1.4, 1.0), 8.0)
FILL_LIGHT = ((1.10, -0.55, 0.55), (0.0, 0.15, 0.12), (1.0, 1.0), 2.5)
WORLD_COLOR = (0.25, 0.25, 0.26)
WORLD_STRENGTH = 0.35

CAMERA_POS = (0.0, -1.25, 0.74)
CAMERA_TARGET = (0.0, 0.20, 0.12)
CAMERA_LENS = 56.0                       # mm, vertical sensor fit, 36 mm sensor height
WIDTH, HEIGHT = 1080, 1920

BLEND_OUT = os.path.join(HERE, 'xylophone-ramp.blend')
GLB_OUT = os.path.join(HERE, 'xylophone-ramp.glb')
BUILD_DIR = os.path.join(HERE, 'build')
# ===================================================================== END SETTINGS

import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector
from params import *

os.makedirs(BUILD_DIR, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
sc = bpy.context.scene
col = sc.collection


def link(ob):
    col.objects.link(ob)
    return ob


def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    return m, nt, bsdf


def setin(bsdf, key, val):
    if key in bsdf.inputs:
        bsdf.inputs[key].default_value = val


def simple_mat(name, color, rough, metal=0.0, coat=0.0, sheen=0.0):
    m, nt, b = node_mat(name)
    setin(b, 'Base Color', (*color, 1))
    setin(b, 'Roughness', rough)
    setin(b, 'Metallic', metal)
    setin(b, 'Coat Weight', coat)
    setin(b, 'Sheen Weight', sheen)
    return m


def mesh_from(name, verts, faces, mat=None, smooth=False, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        loop_vi = np.zeros(len(me.loops), dtype=np.int64)
        me.loops.foreach_get('vertex_index', loop_vi)
        uvl.data.foreach_set('uv', uvs[loop_vi].astype(np.float32).ravel())
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    return link(ob)


def box(name, center, dims, mat, basis=None, bevel=0.0, segs=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    me.materials.append(mat)
    M = Matrix.Identity(4)
    if basis is not None:
        for i in range(3):
            for j in range(3):
                M[i][j] = basis[i][j]
    M.translation = Vector(center)
    ob.matrix_world = M
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL')
        md.width = bevel
        md.segments = segs
        md.limit_method = 'NONE'
    return ob


# ---------------- materials
m_back = simple_mat('backdrop', BACKDROP_COLOR, 0.92)
nt = m_back.node_tree
b = nt.nodes['Principled BSDF']
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 60.0
bmp = nt.nodes.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.03
nt.links.new(tex.outputs['Fac'], bmp.inputs['Height'])
nt.links.new(bmp.outputs['Normal'], b.inputs['Normal'])

m_bar = simple_mat('bar', BAR_COLOR, 0.26, metal=1.0)
nt = m_bar.node_tree
b = nt.nodes['Principled BSDF']
tc = nt.nodes.new('ShaderNodeTexCoord')
mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (2.0, 260.0, 260.0)
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6.0
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.20; mr.inputs['To Max'].default_value = 0.33
nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
bb = nt.nodes.new('ShaderNodeBump'); bb.inputs['Strength'].default_value = 0.015
nt.links.new(nz.outputs['Fac'], bb.inputs['Height'])
nt.links.new(bb.outputs['Normal'], b.inputs['Normal'])

m_screw = simple_mat('screw', SCREW_COLOR, 0.32, metal=1.0)
m_felt = simple_mat('felt', FELT_COLOR, 1.0, sheen=0.6)
m_rail = simple_mat('rail', RAIL_COLOR, 0.55)
m_box = simple_mat('box', STAND_COLOR, 0.62)
m_pot = simple_mat('pot', POT_COLOR, 0.85)
m_soil = simple_mat('soil', SOIL_COLOR, 1.0)
m_cactus = simple_mat('cactus', CACTUS_COLOR, 0.55)
m_blk = [simple_mat('blk%d' % i, c, 0.45) for i, c in enumerate(BLOCK_COLORS)]

m_bask, nt, b = node_mat('basket')
uvn = nt.nodes.new('ShaderNodeUVMap')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
nt.links.new(uvn.outputs['UV'], sep.inputs['Vector'])


def mnode(op, a, bval=None, c=None):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    for i, v in enumerate((a, bval, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


u = sep.outputs['X']
v = sep.outputs['Y']
ph = mnode('ADD', mnode('MULTIPLY', v, 13.0), mnode('MULTIPLY', u, 13.0 / 2.6))
strands = mnode('SINE', mnode('MULTIPLY', ph, 2 * math.pi))
strands = mnode('MULTIPLY_ADD', strands, 0.5, 0.5)
strands = mnode('POWER', strands, 0.6)
st = mnode('FRACT', mnode('MULTIPLY', u, 1.0 / 1.9))
st = mnode('ABSOLUTE', mnode('SUBTRACT', st, 0.5))
stitch = mnode('LESS_THAN', st, 0.07)
fine = nt.nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 900.0; fine.inputs['Detail'].default_value = 4.0
tcb = nt.nodes.new('ShaderNodeTexCoord')
nt.links.new(tcb.outputs['Object'], fine.inputs['Vector'])
height = mnode('ADD', mnode('MULTIPLY', strands, 0.8), mnode('MULTIPLY', fine.outputs['Fac'], 0.35))
height = mnode('ADD', height, mnode('MULTIPLY', stitch, 0.25))
bmpb = nt.nodes.new('ShaderNodeBump'); bmpb.inputs['Strength'].default_value = 0.55; bmpb.inputs['Distance'].default_value = 0.0012
nt.links.new(height, bmpb.inputs['Height'])
nt.links.new(bmpb.outputs['Normal'], b.inputs['Normal'])
cn = nt.nodes.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 35.0; cn.inputs['Detail'].default_value = 3.0
nt.links.new(tcb.outputs['Object'], cn.inputs['Vector'])
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.30
ramp.color_ramp.elements[0].color = (*BASKET_DARK, 1)
ramp.color_ramp.elements[1].position = 0.70
ramp.color_ramp.elements[1].color = (*BASKET_LIGHT, 1)
nt.links.new(cn.outputs['Fac'], ramp.inputs['Fac'])


def sock(coll, ident):
    return [s for s in coll if s.identifier == ident][0]


mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
sock(mix.inputs, 'Factor_Float').default_value = 1.0
nt.links.new(ramp.outputs['Color'], sock(mix.inputs, 'A_Color'))
shade = mnode('MULTIPLY_ADD', strands, 0.35, 0.72)
shade_c = nt.nodes.new('ShaderNodeCombineColor')
for ch in ('Red', 'Green', 'Blue'):
    nt.links.new(shade, shade_c.inputs[ch])
nt.links.new(shade_c.outputs['Color'], sock(mix.inputs, 'B_Color'))
mix2 = nt.nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'
sock(mix2.inputs, 'B_Color').default_value = (*BASKET_STITCH, 1)
nt.links.new(stitch, sock(mix2.inputs, 'Factor_Float'))
nt.links.new(sock(mix.outputs, 'Result_Color'), sock(mix2.inputs, 'A_Color'))
nt.links.new(sock(mix2.outputs, 'Result_Color'), b.inputs['Base Color'])
b.inputs['Roughness'].default_value = 0.82

# ---------------- backdrop (table + sweep)
ys = np.concatenate([np.linspace(-1.6, 1.05, 40), 1.05 + 0.45 * np.sin(np.linspace(0, math.pi / 2, 24)[1:])])
zs = np.concatenate([np.zeros(40), 0.45 * (1 - np.cos(np.linspace(0, math.pi / 2, 24)[1:]))])
ys = np.concatenate([ys, np.full(10, 1.5)])
zs = np.concatenate([zs, np.linspace(0.45, 2.2, 11)[1:]])
xs = np.linspace(-2.0, 2.0, 9)
verts, faces = [], []
for i, x in enumerate(xs):
    for j in range(len(ys)):
        verts.append((x, ys[j], zs[j]))
nj = len(ys)
for i in range(len(xs) - 1):
    for j in range(nj - 1):
        a = i * nj + j
        faces.append((a, a + nj, a + nj + 1, a + 1))
bd = mesh_from('backdrop', verts, faces, m_back, smooth=True)
bd.pass_index = 1

# ---------------- bars, screws, felt, rails
ROT = np.array([[1, 0, 0], [0, math.cos(THETA), -math.sin(THETA)], [0, math.sin(THETA), math.cos(THETA)]])
bars = []
for k in range(NB):
    ln = bar_len(k)
    c = bar_top_center(k) - N * BAR_T / 2
    ob = box(f'bar{k:02d}', c, (ln, BAR_W, BAR_T), m_bar, basis=ROT, bevel=0.0009, segs=2)
    ob.pass_index = 2
    bars.append(ob)
    for sgn in (-1, 1):
        xo = sgn * 0.276 * ln
        p = bar_top_center(k) + np.array([xo, 0, 0])
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0033, segments=20, ring_count=10, location=tuple(p))
        sw = bpy.context.active_object
        sw.name = f'screw{k:02d}{sgn}'
        sw.scale = (1, 1, 0.42)
        sw.rotation_euler = (THETA, 0, 0)
        sw.data.materials.append(m_screw)
        sw.data.shade_smooth()
        sw.pass_index = 3

hb_felt = BAR_T + FELT_T / 2
hb_rail = BAR_T + FELT_T + RAIL_H / 2
for sgn in (-1, 1):
    s0, s1 = -0.022, L + 0.004
    x0 = x1 = sgn * 0.276 * BAR_LEN
    for hb, dims_w, dims_h, mat, nm in ((hb_felt, 0.011, FELT_T, m_felt, 'felt'), (hb_rail, RAIL_W, RAIL_H, m_rail, 'rail')):
        A = ramp_point(s0, x0, -hb)
        B = ramp_point(s1, x1, -hb)
        yv = (A - B) / np.linalg.norm(A - B)
        zv = N.copy()
        xv = np.cross(yv, zv); xv /= np.linalg.norm(xv)
        zv = np.cross(xv, yv)
        basis = np.stack([xv, yv, zv], axis=1)
        ob = box(f'{nm}{sgn}', (A + B) / 2, (dims_w, np.linalg.norm(A - B), dims_h), mat, basis=basis, bevel=0.0015 if nm == 'rail' else 0.0)
        ob.pass_index = 4


def rail_bottom_z(y):
    hb = BAR_T + FELT_T + RAIL_H
    s = (TOP[1] + hb * math.sin(THETA) - y) / math.cos(THETA)
    return TOP[2] - s * math.sin(THETA) - hb * math.cos(THETA)


zb = rail_bottom_z(BOX['y0'])
bx = box('stand', ((BOX['x0'] + BOX['x1']) / 2, (BOX['y0'] + BOX['y1']) / 2, zb / 2),
         (BOX['x1'] - BOX['x0'], BOX['y1'] - BOX['y0'], zb), m_box, bevel=0.004, segs=3)
bx.pass_index = 5
zb2 = rail_bottom_z(BACK['y0'])
bk = box('backstand', ((BACK['x0'] + BACK['x1']) / 2, (BACK['y0'] + BACK['y1']) / 2, zb2 / 2),
         (BACK['x1'] - BACK['x0'], BACK['y1'] - BACK['y0'], zb2), m_box, bevel=0.004, segs=3)
bk.pass_index = 5

# ---------------- basket (one coiled rope following BASKET_PROFILE)
pr = 2 * ROPE_R * 0.93
pts = []
r0, r1 = 0.007, BASKET_PROFILE[0][0]
th_b = 2 * math.pi * (r1 - r0) / pr
nb_pts = int(th_b / (2 * math.pi) * 90) + 2
for t in np.linspace(0, th_b, nb_pts):
    r = r0 + (r1 - r0) * t / th_b
    pts.append((r * math.cos(t), r * math.sin(t), ROPE_R))
prof = np.array(BASKET_PROFILE)
seg = np.linalg.norm(np.diff(prof, axis=0), axis=1)
cum = np.concatenate([[0], np.cumsum(seg)])
Sw = cum[-1]
th_w = 2 * math.pi * Sw / pr
nw_pts = int(th_w / (2 * math.pi) * 110) + 2
for t in np.linspace(0, th_w, nw_pts)[1:]:
    sg = Sw * t / th_w
    r = np.interp(sg, cum, prof[:, 0]); z = np.interp(sg, cum, prof[:, 1])
    tt = th_b + t
    pts.append((r * math.cos(tt), r * math.sin(tt), z))
P = np.array(pts) + BASKET_C
Tn = np.gradient(P, axis=0); Tn /= np.linalg.norm(Tn, axis=1, keepdims=True)
up = np.array([0, 0, 1.0])
Nn = np.zeros_like(P)
n0 = np.cross(Tn[0], up); n0 /= np.linalg.norm(n0)
Nn[0] = n0
for i in range(1, len(P)):
    nprev = Nn[i - 1]
    n = nprev - Tn[i] * np.dot(nprev, Tn[i]); n /= np.linalg.norm(n)
    Nn[i] = n
Bn = np.cross(Tn, Nn)
K = 10
arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
rad = np.full(len(P), ROPE_R)
taper = np.clip((arc[-1] - arc) / 0.035, 0, 1)
rad *= 0.35 + 0.65 * np.sqrt(taper)
rad *= np.clip(arc / 0.02, 0.3, 1)
phis = np.linspace(0, 2 * math.pi, K, endpoint=False)
V = (P[:, None, :] + rad[:, None, None] * (np.cos(phis)[None, :, None] * Nn[:, None, :] + np.sin(phis)[None, :, None] * Bn[:, None, :])).reshape(-1, 3)
F = []
for i in range(len(P) - 1):
    for j in range(K):
        a = i * K + j; b2 = i * K + (j + 1) % K
        F.append((a, b2, b2 + K, a + K))
uvs = np.stack([np.repeat(arc * 100.0, K), np.tile(phis / (2 * math.pi), len(P))], axis=1)
bask = mesh_from('basket', V, F, m_bask, smooth=True, uvs=uvs)
np.savez(os.path.join(BUILD_DIR, 'basket_tube.npz'), V=V, F=np.array(F), P=P, rad=rad)
bask.pass_index = 6


# ---------------- side props
def lathe(name, prof_rz, center, mat, nseg=64, smooth=True, ripple=None):
    prof_rz = np.array(prof_rz)
    verts = []
    for i in range(nseg):
        a = 2 * math.pi * i / nseg
        for (r, z) in prof_rz:
            rr = r * (1 + (ripple(a, z) if ripple else 0))
            verts.append((center[0] + rr * math.cos(a), center[1] + rr * math.sin(a), center[2] + z))
    m = len(prof_rz)
    faces = []
    for i in range(nseg):
        i2 = (i + 1) % nseg
        for j in range(m - 1):
            faces.append((i * m + j, i2 * m + j, i2 * m + j + 1, i * m + j + 1))
    return mesh_from(name, verts, faces, mat, smooth=smooth)


cp = CACTUS_POS
pot = lathe('pot', [(0.0, 0.0), (0.033, 0.0), (0.035, 0.002), (0.041, 0.050), (0.0465, 0.051), (0.047, 0.066), (0.0455, 0.068), (0.040, 0.068), (0.0395, 0.062), (0.0, 0.062)], cp, m_pot)
pot.pass_index = 7
soil = lathe('soil', [(0.0, 0.0605), (0.0398, 0.0605)], cp, m_soil)
soil.pass_index = 7
cprof = [(0.0001, 0.052), (0.018, 0.054), (0.030, 0.062), (0.037, 0.075), (0.039, 0.090), (0.036, 0.106), (0.027, 0.120), (0.014, 0.128), (0.0001, 0.130)]
cac = lathe('cactus', cprof, cp, m_cactus, nseg=144, ripple=lambda a, z: 0.075 * (abs(math.cos(7 * a)) - 0.6))
cac.pass_index = 7
bp = BLOCKS_POS
for i, (dz, rot, off) in enumerate(((0.0225, 0.10, (0, 0)), (0.0675, -0.22, (0.004, -0.003)), (0.1125, 0.35, (-0.003, 0.002)))):
    ob = box(f'block{i}', (bp[0] + off[0], bp[1] + off[1], dz), (0.044, 0.044, 0.044), m_blk[i], bevel=0.0035, segs=3)
    ob.rotation_euler = (0, 0, rot)
    ob.pass_index = 7


# ---------------- lights
def area(name, loc, target, size, energy):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size = size[0]; ld.size_y = size[1]
    ld.energy = energy
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    dvec = Vector(target) - Vector(loc)
    ob.rotation_euler = dvec.to_track_quat('-Z', 'Y').to_euler()
    ob.visible_camera = False
    return ob


key = area('key', *KEY_LIGHT)
top = area('top', *TOP_LIGHT)
fill = area('fill', *FILL_LIGHT)
world = bpy.data.worlds.new('world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (*WORLD_COLOR, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = WORLD_STRENGTH
sc.world = world

# ---------------- camera
cd = bpy.data.cameras.new('cam')
cd.sensor_fit = 'VERTICAL'
cd.sensor_height = 36.0
cd.lens = CAMERA_LENS
cd.clip_start = 0.01
cam = link(bpy.data.objects.new('cam', cd))
cam.location = CAMERA_POS
tgt = Vector(CAMERA_TARGET)
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.render.resolution_x = WIDTH
sc.render.resolution_y = HEIGHT
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.sample_clamp_indirect = 8.0

bpy.context.view_layer.update()
camd = dict(matrix=[list(r) for r in cam.matrix_world], lens=cd.lens, sensor_h=cd.sensor_height, W=WIDTH, H=HEIGHT)
lights = {}
for ob in (key, top, fill):
    lights[ob.name] = dict(matrix=[list(r) for r in ob.matrix_world], size=[ob.data.size, ob.data.size_y], energy=ob.data.energy)
json.dump(dict(camera=camd, lights=lights, box_top=zb, back_top=zb2, blender=bpy.app.version_string),
          open(os.path.join(BUILD_DIR, 'scene_meta.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
try:
    bpy.ops.export_scene.gltf(filepath=GLB_OUT, export_format='GLB', export_cameras=True, export_lights=True, export_apply=True)
except Exception as e:
    print('glb export failed:', e)
print('saved', BLEND_OUT, 'stand height %.4f back stand %.4f' % (zb, zb2), 'blender', bpy.app.version_string)
