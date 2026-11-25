"""Blender 4.0 (EEVEE Legacy) scene: obstacles, rails, marble, camera, lights, moods. Renders RGBA PNGs.

  blender -b --python scene.py -- test 60,450,1150      # a few frames -> build/test/test_XXXX.png
  blender -b --python scene.py -- full [start end]      # every frame -> build/frames/f_XXXX.png (resumable)

Needs build/plan.json (export.py). Must be Blender 4.0/4.1: EEVEE Legacy renders a frame in ~3.3 s on
2 CPU cores at 864x1536 with 4 samples; EEVEE Next (4.2+, bpy 5.x) was ~4x slower here on software GL.
The film is transparent: the backdrop, bloom, snow, marble glow and HUD are added later by post.py.
Each obstacle type shares one mesh and one material; per-object custom properties `glow` (animated),
`gcol` and `base` drive the emission and colours through Attribute nodes.
"""
import bpy
import bmesh
import json
import math
import os
import sys
import time
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE = argv[0] if argv else 'full'
PLAN = settings.PLAN_JSON
OUTDIR = settings.TEST if MODE == 'test' else settings.FRAMES
os.makedirs(OUTDIR, exist_ok=True)
FRAMES = [int(x) for x in argv[1].split(',')] if MODE == 'test' and len(argv) > 1 else []
SAMPLES = settings.SAMPLES

D = json.load(open(PLAN))
FPS = D['fps']
N = D['N']

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 0
scene.frame_end = N - 1
scene.render.resolution_x = settings.WIDTH
scene.render.resolution_y = settings.HEIGHT
scene.render.resolution_percentage = settings.RENDER_PCT
scene.render.film_transparent = True
scene.render.engine = 'BLENDER_EEVEE'
ev = scene.eevee
ev.taa_render_samples = SAMPLES
ev.use_bloom = False
ev.bloom_threshold = 1.0
ev.bloom_knee = 0.5
ev.bloom_intensity = 0.06
ev.bloom_radius = 5.5
ev.use_gtao = False
ev.gtao_distance = 0.8
ev.gtao_factor = 1.0
ev.use_soft_shadows = False
ev.shadow_cascade_size = '2048'
ev.shadow_cube_size = '512'
ev.use_ssr = False
ev.use_motion_blur = False
scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'AgX - Punchy'
except Exception:
    pass
scene.render.use_persistent_data = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.render.image_settings.compression = 15
scene.render.use_overwrite = False
scene.render.use_placeholder = True

MOODS = settings.MOODS


def lin(c):
    return tuple(c) + (1.0,)


# ---------------- fog node group ----------------
fog = bpy.data.node_groups.new('FogMix', 'ShaderNodeTree')
fog.interface.new_socket('Shader', in_out='INPUT', socket_type='NodeSocketShader')
fog.interface.new_socket('Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
gi = fog.nodes.new('NodeGroupInput')
go = fog.nodes.new('NodeGroupOutput')
cam = fog.nodes.new('ShaderNodeCameraData')
sub = fog.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = 9.0
mx = fog.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; mx.inputs[1].default_value = 0.0
dv = fog.nodes.new('ShaderNodeMath'); dv.operation = 'MULTIPLY'; dv.inputs[1].default_value = -1.0 / 34.0
ex = fog.nodes.new('ShaderNodeMath'); ex.operation = 'EXPONENT'
om = fog.nodes.new('ShaderNodeMath'); om.operation = 'SUBTRACT'; om.inputs[0].default_value = 1.0
cl = fog.nodes.new('ShaderNodeMath'); cl.operation = 'MINIMUM'; cl.inputs[1].default_value = 0.93
rgb = fog.nodes.new('ShaderNodeRGB'); rgb.name = 'FogRGB'
rgb.outputs[0].default_value = lin(MOODS[settings.INTRO_MOOD]['fog'])
em = fog.nodes.new('ShaderNodeEmission'); em.inputs[1].default_value = 1.0
mix = fog.nodes.new('ShaderNodeMixShader')
L = fog.links
L.new(cam.outputs['View Distance'], sub.inputs[0])
L.new(sub.outputs[0], mx.inputs[0])
L.new(mx.outputs[0], dv.inputs[0])
L.new(dv.outputs[0], ex.inputs[0])
L.new(ex.outputs[0], om.inputs[1])
L.new(om.outputs[0], cl.inputs[0])
L.new(cl.outputs[0], mix.inputs[0])
L.new(gi.outputs[0], mix.inputs[1])
L.new(rgb.outputs[0], em.inputs[0])
L.new(em.outputs[0], mix.inputs[2])
L.new(mix.outputs[0], go.inputs[0])


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = fog
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], g.inputs[0])
    nt.links.new(g.outputs[0], out.inputs['Surface'])
    return m, nt, bs


def attr(nt, name):
    a = nt.nodes.new('ShaderNodeAttribute')
    a.attribute_type = 'OBJECT'
    a.attribute_name = name
    return a


def glow_emission(nt, bs, gain, extra_fac=None):
    ga = attr(nt, 'glow')
    ca = attr(nt, 'gcol')
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = gain
    nt.links.new(ga.outputs['Fac'], mul.inputs[0])
    src = mul.outputs[0]
    if extra_fac is not None:
        m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
        nt.links.new(src, m2.inputs[0]); nt.links.new(extra_fac, m2.inputs[1])
        src = m2.outputs[0]
    nt.links.new(src, bs.inputs['Emission Strength'])
    nt.links.new(ca.outputs['Color'], bs.inputs['Emission Color'])


# body materials
m_slab, nt, bs = new_mat('slab_body')
bs.inputs['Base Color'].default_value = (0.018, 0.018, 0.022, 1)
bs.inputs['Roughness'].default_value = 0.38
m_panel, nt, bs = new_mat('slab_panel')
bs.inputs['Base Color'].default_value = (0.03, 0.03, 0.035, 1)
bs.inputs['Roughness'].default_value = 0.2
glow_emission(nt, bs, 7.0)
m_rivet, nt, bs = new_mat('rivet')
bs.inputs['Base Color'].default_value = (0.75, 0.75, 0.75, 1)
bs.inputs['Metallic'].default_value = 1.0
bs.inputs['Roughness'].default_value = 0.3

m_gift, nt, bs = new_mat('gift_paper')
ba = attr(nt, 'base')
nt.links.new(ba.outputs['Color'], bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value = 0.45
glow_emission(nt, bs, 2.6)
m_ribbon, nt, bs = new_mat('gift_ribbon')
bs.inputs['Base Color'].default_value = (0.9, 0.62, 0.15, 1)
bs.inputs['Metallic'].default_value = 0.8
bs.inputs['Roughness'].default_value = 0.25
glow_emission(nt, bs, 5.0)

m_mint, nt, bs = new_mat('mint')
tc = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
nt.links.new(tc.outputs['Object'], sep.inputs[0])
at = nt.nodes.new('ShaderNodeMath'); at.operation = 'ARCTAN2'
nt.links.new(sep.outputs[1], at.inputs[0]); nt.links.new(sep.outputs[0], at.inputs[1])
ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
nt.links.new(tc.outputs['Object'], ln.inputs[0])
sw = nt.nodes.new('ShaderNodeMath'); sw.operation = 'MULTIPLY'; sw.inputs[1].default_value = 9.0
nt.links.new(ln.outputs['Value'], sw.inputs[0])
a6 = nt.nodes.new('ShaderNodeMath'); a6.operation = 'MULTIPLY'; a6.inputs[1].default_value = 4.0
nt.links.new(at.outputs[0], a6.inputs[0])
ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'
nt.links.new(a6.outputs[0], ad.inputs[0]); nt.links.new(sw.outputs[0], ad.inputs[1])
sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'
nt.links.new(ad.outputs[0], sn.inputs[0])
gt = nt.nodes.new('ShaderNodeMapRange'); gt.inputs[1].default_value = -0.12; gt.inputs[2].default_value = 0.12
nt.links.new(sn.outputs[0], gt.inputs[0])
mixc = nt.nodes.new('ShaderNodeMix'); mixc.data_type = 'RGBA'
mixc.inputs[6].default_value = (0.92, 0.9, 0.88, 1)
mixc.inputs[7].default_value = (0.75, 0.02, 0.04, 1)
nt.links.new(gt.outputs[0], mixc.inputs[0])
nt.links.new(mixc.outputs[2], bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value = 0.12
bs.inputs['Coat Weight'].default_value = 0.6
glow_emission(nt, bs, 2.2)

m_orn, nt, bs = new_mat('ornament')
ba = attr(nt, 'base')
nt.links.new(ba.outputs['Color'], bs.inputs['Base Color'])
bs.inputs['Metallic'].default_value = 0.35
bs.inputs['Roughness'].default_value = 0.22
bs.inputs['Coat Weight'].default_value = 1.0
glow_emission(nt, bs, 3.2)
m_cap, nt, bs = new_mat('ornament_cap')
bs.inputs['Base Color'].default_value = (0.85, 0.65, 0.25, 1)
bs.inputs['Metallic'].default_value = 1.0
bs.inputs['Roughness'].default_value = 0.3

m_coal, nt, bs = new_mat('coal')
bs.inputs['Base Color'].default_value = (0.012, 0.011, 0.011, 1)
bs.inputs['Roughness'].default_value = 0.75
tcc = nt.nodes.new('ShaderNodeTexCoord')
vz = nt.nodes.new('ShaderNodeTexVoronoi'); vz.voronoi_dimensions = '3D'; vz.feature = 'DISTANCE_TO_EDGE'
vz.inputs['Scale'].default_value = 3.2
nt.links.new(tcc.outputs['Object'], vz.inputs['Vector'])
cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs[1].default_value = 0.0; cr.inputs[2].default_value = 0.07
cr.inputs[3].default_value = 1.0; cr.inputs[4].default_value = 0.06
nt.links.new(vz.outputs['Distance'], cr.inputs[0])
glow_emission(nt, bs, 10.0, extra_fac=cr.outputs[0])

m_cane, nt, bs = new_mat('cane')
tc = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
nt.links.new(tc.outputs['Object'], sep.inputs[0])
ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'
nt.links.new(sep.outputs[0], ad.inputs[0]); nt.links.new(sep.outputs[2], ad.inputs[1])
mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 22.0
nt.links.new(ad.outputs[0], mm.inputs[0])
sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'
nt.links.new(mm.outputs[0], sn.inputs[0])
gt = nt.nodes.new('ShaderNodeMapRange'); gt.inputs[1].default_value = -0.1; gt.inputs[2].default_value = 0.1
nt.links.new(sn.outputs[0], gt.inputs[0])
mixc = nt.nodes.new('ShaderNodeMix'); mixc.data_type = 'RGBA'
mixc.inputs[6].default_value = (0.92, 0.9, 0.88, 1)
mixc.inputs[7].default_value = (0.78, 0.02, 0.03, 1)
nt.links.new(gt.outputs[0], mixc.inputs[0])
nt.links.new(mixc.outputs[2], bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value = 0.15
bs.inputs['Coat Weight'].default_value = 0.5
glow_emission(nt, bs, 2.2)

m_marble, nt, bs = new_mat('marble')
bs.inputs['Base Color'].default_value = (1.0, 0.70, 0.26, 1)
bs.inputs['Metallic'].default_value = 0.85
bs.inputs['Roughness'].default_value = 0.2
bs.inputs['Emission Color'].default_value = (1.0, 0.6, 0.2, 1)
bs.inputs['Emission Strength'].default_value = 0.35
m_rail, nt, bs = new_mat('rail')
bs.inputs['Base Color'].default_value = (0.32, 0.32, 0.34, 1)
bs.inputs['Metallic'].default_value = 0.9
bs.inputs['Roughness'].default_value = 0.32
m_ground, nt, bs = new_mat('ground')
bs.inputs['Base Color'].default_value = (0.8, 0.84, 0.9, 1)
bs.inputs['Roughness'].default_value = 0.95


# ---------------- meshes ----------------
def mesh_from_bm(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def rounded_box(bm, sx, sy, sz, bevel, mat_index=0, center=(0, 0, 0)):
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res['verts']
    for v in vs:
        v.co.x = v.co.x * sx + center[0]
        v.co.y = v.co.y * sy + center[1]
        v.co.z = v.co.z * sz + center[2]
    edges = list({e for v in vs for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=vs + edges, offset=bevel, segments=3, affect='EDGES', profile=0.5)
    return res


def set_faces_mat(bm, before_faces, idx):
    for f in bm.faces:
        if f not in before_faces:
            f.material_index = idx


def build_slab():
    bm = bmesh.new()
    rounded_box(bm, 0.78, 0.40, 0.16, 0.025)
    f0 = set(bm.faces)
    rounded_box(bm, 0.66, 0.30, 0.02, 0.008, center=(0, 0, 0.075))
    set_faces_mat(bm, f0, 1)
    f1 = set(bm.faces)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.016,
                                      matrix=Matrix.Translation((sx * 0.355, sy * 0.172, 0.078)))
    set_faces_mat(bm, f1, 2)
    me = mesh_from_bm('slab', bm)
    for m in (m_slab, m_panel, m_rivet):
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return me, (0.78, 0.40, 0.16)


def build_gift():
    bm = bmesh.new()
    rounded_box(bm, 0.44, 0.44, 0.40, 0.02)
    f0 = set(bm.faces)
    rounded_box(bm, 0.455, 0.09, 0.415, 0.01)
    rounded_box(bm, 0.09, 0.455, 0.415, 0.01)
    set_faces_mat(bm, f0, 1)
    me = mesh_from_bm('gift', bm)
    me.materials.append(m_gift)
    me.materials.append(m_ribbon)
    return me, (0.44, 0.44, 0.40)


def build_mint():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=0.23, radius2=0.23, depth=0.10)
    rim = [e for e in bm.edges if all(abs(abs(v.co.z) - 0.05) < 1e-4 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=rim, offset=0.025, segments=3, affect='EDGES')
    me = mesh_from_bm('mint', bm)
    me.materials.append(m_mint)
    for p in me.polygons:
        p.use_smooth = True
    return me, (0.46, 0.46, 0.10)


def build_ornament():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=16, radius=1.0)
    f0 = set(bm.faces)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.2, radius2=0.2, depth=0.22,
                          matrix=Matrix.Translation((0, 0, -0.98)))
    set_faces_mat(bm, f0, 1)
    me = mesh_from_bm('ornament', bm)
    me.materials.append(m_orn)
    me.materials.append(m_cap)
    for p in me.polygons:
        p.use_smooth = True
    return me


def build_coal():
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    import random
    rnd = random.Random(7)
    for v in bm.verts:
        n = v.co.normalized()
        v.co = n * (1.0 + 0.16 * math.sin(3.1 * n.x + 1.7) * math.cos(2.3 * n.y) + rnd.uniform(-0.06, 0.06))
    me = mesh_from_bm('coal', bm)
    me.materials.append(m_coal)
    return me


def build_cane():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.09, radius2=0.09, depth=0.80,
                          matrix=Matrix.Rotation(math.pi / 2, 4, 'Y'))
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs(abs(e.verts[0].co.x) - 0.4) < 1e-4 and abs(abs(e.verts[1].co.x) - 0.4) < 1e-4],
                    offset=0.05, segments=4, affect='EDGES')
    me = mesh_from_bm('cane', bm)
    me.materials.append(m_cane)
    for p in me.polygons:
        p.use_smooth = True
    return me, (0.80, 0.18, 0.18)


slab_me, slab_n = build_slab()
gift_me, gift_n = build_gift()
mint_me, mint_n = build_mint()
orn_me = build_ornament()
coal_me = build_coal()
cane_me, cane_n = build_cane()

col = bpy.data.collections.new('Course')
scene.collection.children.link(col)

ORN_COLS = [(0.75, 0.03, 0.03), (0.9, 0.6, 0.12), (0.05, 0.45, 0.12), (0.75, 0.75, 0.8), (0.1, 0.25, 0.8)]
GIFT_COLS = [(0.55, 0.02, 0.03), (0.03, 0.30, 0.10), (0.85, 0.85, 0.85), (0.08, 0.12, 0.45)]


def set_fcurve_keys(idblock, path, index, frames, values, interp='LINEAR'):
    if idblock.animation_data is None:
        idblock.animation_data_create()
    act = idblock.animation_data.action
    if act is None:
        act = bpy.data.actions.new(idblock.name + '_act')
        idblock.animation_data.action = act
    fc = act.fcurves.find(path, index=index)
    if fc is None:
        fc = act.fcurves.new(path, index=index)
    fc.keyframe_points.add(len(frames))
    co = []
    for f, v in zip(frames, values):
        co += [f, v]
    fc.keyframe_points.foreach_set('co', co)
    ip = {'LINEAR': 1, 'CONSTANT': 0, 'BEZIER': 2}[interp]
    fc.keyframe_points.foreach_set('interpolation', [ip] * len(frames))
    fc.update()
    return fc


def glow_keys(hit_t, extra_before=True):
    f = hit_t * FPS
    fr = [f - 1.0, f, f + 3, f + 8, f + 16]
    vals = [0.0, 1.0, 0.45, 0.17, 0.08]
    return fr, vals


obstacles = []
t0 = time.time()
for i, o in enumerate(D['obstacles']):
    typ = o['type']
    R = Matrix([o['R'][0], o['R'][1], o['R'][2]])
    c = Vector(o['center'])
    if typ == 'slab':
        me, nom = slab_me, slab_n
        sc = Vector((o['size'][0] / nom[0], o['size'][1] / nom[1], o['size'][2] / nom[2]))
    elif typ == 'gift':
        me, nom = gift_me, gift_n
        sc = Vector((o['size'][0] / nom[0], o['size'][1] / nom[1], o['size'][2] / nom[2]))
    elif typ == 'mint':
        me, nom = mint_me, mint_n
        sc = Vector((o['size'][0] / nom[0], o['size'][1] / nom[1], 1.0))
    elif typ == 'cane':
        me, nom = cane_me, cane_n
        sc = Vector((1.0, o['size'][1] / nom[1], o['size'][2] / nom[2]))
    elif typ == 'ornament':
        me = orn_me
        r = o['radius']
        sc = Vector((r, r, r))
    else:
        me = coal_me
        r = o['radius']
        sc = Vector((r, r, r))
    ob = bpy.data.objects.new(f"{typ}_{o['k']}_{o['j']}{'_c' if o['copy'] else ''}", me)
    col.objects.link(ob)
    if typ == 'ornament':
        up = R.col[2]
        Rm = R.copy()
        ob.matrix_world = Matrix.Translation(c) @ Rm.to_4x4() @ Matrix.Diagonal((sc.x, sc.y, sc.z, 1.0))
    else:
        ob.matrix_world = Matrix.Translation(c) @ R.to_4x4() @ Matrix.Diagonal((sc.x, sc.y, sc.z, 1.0))
    ob['glow'] = 0.0
    ob['gcol'] = list(o['glow'])
    idx = (o['k'] * 7 + o['j'] * 3) % 5
    if typ == 'ornament':
        ob['base'] = list(ORN_COLS[idx])
    elif typ == 'gift':
        ob['base'] = list(GIFT_COLS[(o['j']) % 4])
    else:
        ob['base'] = [0.5, 0.5, 0.5]
    fr, vals = glow_keys(o['t'])
    set_fcurve_keys(ob, '["glow"]', 0, fr, vals)
    n = Vector((o['R'][0][2], o['R'][1][2], o['R'][2][2]))
    loc0 = ob.location.copy()
    f = o['t'] * FPS
    dips = [loc0, loc0 - n * 0.05, loc0 + n * 0.01, loc0]
    dfr = [f, f + 1.5, f + 4.5, f + 7]
    for ax in range(3):
        set_fcurve_keys(ob, 'location', ax, dfr, [p[ax] for p in dips])
    obstacles.append((ob, o))
print('obstacles built', len(obstacles), round(time.time() - t0, 1), flush=True)


# ---------------- rails ----------------
def tube_mesh(bm, pts, radius, seg=8):
    pts = [Vector(p) for p in pts]
    if len(pts) < 2:
        return
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2]).normalized()
        else:
            t = (pts[i + 1] - pts[i - 1]).normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(a).normalized()
        v = t.cross(u).normalized()
        ring = []
        for k in range(seg):
            ang = 2 * math.pi * k / seg
            ring.append(bm.verts.new(p + (u * math.cos(ang) + v * math.sin(ang)) * radius))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            a, b = rings[i][k], rings[i][(k + 1) % seg]
            c2, d2 = rings[i + 1][(k + 1) % seg], rings[i + 1][k]
            bm.faces.new((a, b, c2, d2))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


for ri, rr in enumerate(D['rails']):
    bm = bmesh.new()
    tube_mesh(bm, rr['L'], 0.022)
    tube_mesh(bm, rr['R'], 0.022)
    for arc in rr['cross']:
        tube_mesh(bm, arc, 0.012, seg=6)
    me = mesh_from_bm(f'rail_{ri}', bm)
    me.materials.append(m_rail)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(f'rail_{ri}_{rr["kind"]}', me)
    col.objects.link(ob)

# ---------------- marble ----------------
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=0.2)
me = mesh_from_bm('marble', bm)
me.materials.append(m_marble)
for p in me.polygons:
    p.use_smooth = True
marble = bpy.data.objects.new('Marble', me)
scene.collection.objects.link(marble)
frames = list(range(N))
for ax in range(3):
    set_fcurve_keys(marble, 'location', ax, frames, [D['marble'][f][ax] for f in frames])

# ---------------- camera ----------------
camd = bpy.data.cameras.new('Cam')
camd.lens = settings.LENS
camd.sensor_width = 36
camd.sensor_fit = 'AUTO'
camd.shift_y = settings.SHIFT_Y
camd.clip_start = 0.3
camd.clip_end = 400
camo = bpy.data.objects.new('Cam', camd)
scene.collection.objects.link(camo)
scene.camera = camo
camo.rotation_mode = 'QUATERNION'
for ax in range(3):
    set_fcurve_keys(camo, 'location', ax, frames, [D['cam'][f][ax] for f in frames])
for ax in range(4):
    set_fcurve_keys(camo, 'rotation_quaternion', ax, frames, [D['quat'][f][ax] for f in frames])

# ---------------- lights ----------------
sund = bpy.data.lights.new('Sun', 'SUN')
sund.angle = math.radians(7)
sund.energy = 3.0
sund.shadow_cascade_max_distance = 40
sund.shadow_cascade_count = 2
sund.shadow_cascade_fade = 0.15
sun = bpy.data.objects.new('Sun', sund)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(38), math.radians(-14), math.radians(160))

world = bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
wnt = world.node_tree
bg = wnt.nodes['Background']
wout = wnt.nodes['World Output']
wrgb = wnt.nodes.new('ShaderNodeRGB')
wrgb.name = 'RGB'
wnt.links.new(wrgb.outputs[0], bg.inputs[0])
brgb = wnt.nodes.new('ShaderNodeRGB'); brgb.name = 'Backdrop'
lp = wnt.nodes.new('ShaderNodeLightPath')
tcw = wnt.nodes.new('ShaderNodeTexCoord')
sepw = wnt.nodes.new('ShaderNodeSeparateXYZ')
wnt.links.new(tcw.outputs['Window'], sepw.inputs[0])
dx = wnt.nodes.new('ShaderNodeMath'); dx.operation = 'SUBTRACT'; dx.inputs[1].default_value = 0.5
wnt.links.new(sepw.outputs[0], dx.inputs[0])
dy = wnt.nodes.new('ShaderNodeMath'); dy.operation = 'SUBTRACT'; dy.inputs[1].default_value = 0.46
wnt.links.new(sepw.outputs[1], dy.inputs[0])
dxs = wnt.nodes.new('ShaderNodeMath'); dxs.operation = 'MULTIPLY'; dxs.inputs[1].default_value = 0.62
wnt.links.new(dx.outputs[0], dxs.inputs[0])
cmb = wnt.nodes.new('ShaderNodeCombineXYZ')
wnt.links.new(dxs.outputs[0], cmb.inputs[0]); wnt.links.new(dy.outputs[0], cmb.inputs[1])
dl = wnt.nodes.new('ShaderNodeVectorMath'); dl.operation = 'LENGTH'
wnt.links.new(cmb.outputs[0], dl.inputs[0])
vg = wnt.nodes.new('ShaderNodeMapRange'); vg.inputs[1].default_value = 0.0; vg.inputs[2].default_value = 0.62
vg.inputs[3].default_value = 1.35; vg.inputs[4].default_value = 0.45
wnt.links.new(dl.outputs['Value'], vg.inputs[0])
bmul = wnt.nodes.new('ShaderNodeVectorMath'); bmul.operation = 'SCALE'
wnt.links.new(brgb.outputs[0], bmul.inputs[0]); wnt.links.new(vg.outputs[0], bmul.inputs['Scale'])
tval = wnt.nodes.new('ShaderNodeValue'); tval.name = 'BokehT'
sx = wnt.nodes.new('ShaderNodeMath'); sx.operation = 'MULTIPLY'; sx.inputs[1].default_value = 0.5625 * 5.0
wnt.links.new(sepw.outputs[0], sx.inputs[0])
sy = wnt.nodes.new('ShaderNodeMath'); sy.operation = 'MULTIPLY'; sy.inputs[1].default_value = 5.0
wnt.links.new(sepw.outputs[1], sy.inputs[0])
sy2 = wnt.nodes.new('ShaderNodeMath'); sy2.operation = 'ADD'
wnt.links.new(sy.outputs[0], sy2.inputs[0]); wnt.links.new(tval.outputs[0], sy2.inputs[1])
cv = wnt.nodes.new('ShaderNodeCombineXYZ')
wnt.links.new(sx.outputs[0], cv.inputs[0]); wnt.links.new(sy2.outputs[0], cv.inputs[1]); wnt.links.new(tval.outputs[0], cv.inputs[2])
vor = wnt.nodes.new('ShaderNodeTexVoronoi'); vor.voronoi_dimensions = '3D'; vor.feature = 'F1'
vor.inputs['Scale'].default_value = 1.0; vor.inputs['Randomness'].default_value = 0.85
wnt.links.new(cv.outputs[0], vor.inputs['Vector'])
sepc = wnt.nodes.new('ShaderNodeSeparateColor')
wnt.links.new(vor.outputs['Color'], sepc.inputs[0])
rr0 = wnt.nodes.new('ShaderNodeMapRange'); rr0.inputs[3].default_value = 0.10; rr0.inputs[4].default_value = 0.26
wnt.links.new(sepc.outputs[0], rr0.inputs[0])
dd = wnt.nodes.new('ShaderNodeMath'); dd.operation = 'SUBTRACT'
wnt.links.new(rr0.outputs[0], dd.inputs[0]); wnt.links.new(vor.outputs['Distance'], dd.inputs[1])
msk = wnt.nodes.new('ShaderNodeMapRange'); msk.inputs[1].default_value = 0.0; msk.inputs[2].default_value = 0.035
wnt.links.new(dd.outputs[0], msk.inputs[0])
ramp = wnt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.interpolation = 'CONSTANT'
els = ramp.color_ramp.elements
els[0].position = 0.0; els[0].color = (1.0, 0.12, 0.10, 1)
els[1].position = 0.3; els[1].color = (1.0, 0.72, 0.25, 1)
e3 = els.new(0.55); e3.color = (0.15, 1.0, 0.35, 1)
e4 = els.new(0.8); e4.color = (1.0, 0.95, 0.85, 1)
wnt.links.new(sepc.outputs[1], ramp.inputs[0])
bri = wnt.nodes.new('ShaderNodeMath'); bri.operation = 'MULTIPLY'
wnt.links.new(msk.outputs[0], bri.inputs[0]); wnt.links.new(sepc.outputs[2], bri.inputs[1])
bri2 = wnt.nodes.new('ShaderNodeMath'); bri2.operation = 'MULTIPLY'; bri2.inputs[1].default_value = 0.16
wnt.links.new(bri.outputs[0], bri2.inputs[0])
bcol = wnt.nodes.new('ShaderNodeVectorMath'); bcol.operation = 'SCALE'
wnt.links.new(ramp.outputs[0], bcol.inputs[0]); wnt.links.new(bri2.outputs[0], bcol.inputs['Scale'])
badd = wnt.nodes.new('ShaderNodeVectorMath'); badd.operation = 'ADD'
wnt.links.new(bmul.outputs[0], badd.inputs[0]); wnt.links.new(bcol.outputs[0], badd.inputs[1])
bbg = wnt.nodes.new('ShaderNodeBackground')
wnt.links.new(badd.outputs[0], bbg.inputs[0])
wmix = wnt.nodes.new('ShaderNodeMixShader')
wnt.links.new(lp.outputs['Is Camera Ray'], wmix.inputs[0])
wnt.links.new(bg.outputs[0], wmix.inputs[1])
wnt.links.new(bbg.outputs[0], wmix.inputs[2])
wnt.links.new(wmix.outputs[0], wout.inputs['Surface'])
TT = D['T']
bf = list(range(0, N, 3)) + [N - 1]
set_fcurve_keys(wnt, 'nodes["BokehT"].outputs[0].default_value', 0, bf, [0.55 * math.sin(2 * math.pi * f / FPS / TT) for f in bf])

# mood keyframes
rounds = D['rounds']
mood_keys = []
mood_keys.append((0.0, settings.INTRO_MOOD))
for r in rounds:
    mood_keys.append((r['t_start'] - 0.45, None))
    mood_keys.append((r['t_start'] + 0.25, r['k']))
cur = settings.INTRO_MOOD
mk_frames, mk_moods = [], []
for t, mi in mood_keys:
    if mi is None:
        mi = cur
    mk_frames.append(max(0.0, t * FPS))
    mk_moods.append(mi)
    cur = mi
mk_frames.append(N - 1)
mk_moods.append(cur)
fog_tree = fog
for ch in range(3):
    set_fcurve_keys(fog_tree, 'nodes["FogRGB"].outputs[0].default_value', ch, mk_frames, [MOODS[m]['fog'][ch] for m in mk_moods])
    set_fcurve_keys(wnt, 'nodes["RGB"].outputs[0].default_value', ch, mk_frames, [MOODS[m]['fog'][ch] * MOODS[m]['amb'] for m in mk_moods])
    set_fcurve_keys(wnt, 'nodes["Backdrop"].outputs[0].default_value', ch, mk_frames, [MOODS[m]['fog'][ch] for m in mk_moods])
    set_fcurve_keys(sund, 'color', ch, mk_frames, [MOODS[m]['sun'][ch] for m in mk_moods])
set_fcurve_keys(sund, 'energy', 0, mk_frames, [MOODS[m]['sun_e'] for m in mk_moods])

# glow point lights
NL = 3
glights = []
for i in range(NL):
    ld = bpy.data.lights.new(f'Glow{i}', 'POINT')
    ld.shadow_soft_size = 0.25
    ld.use_shadow = False
    ld.energy = 0.0
    lo = bpy.data.objects.new(f'Glow{i}', ld)
    scene.collection.objects.link(lo)
    glights.append((lo, ld))
hits_sorted = sorted([o for o in D['obstacles'] if not o['copy']], key=lambda o: o['t'])
per = [dict(f=[], loc=[], e_f=[], e_v=[], c=[]) for _ in range(NL)]
for idx, o in enumerate(hits_sorted):
    li = idx % NL
    f = o['t'] * FPS
    n = Vector((o['R'][0][2], o['R'][1][2], o['R'][2][2]))
    p = Vector(o['center']) + n * 0.55
    per[li]['f'].append(f - 0.5)
    per[li]['loc'].append(p)
    per[li]['c'].append(o['glow'])
    peak = 90.0
    per[li]['e_f'] += [f - 0.6, f, f + 3, f + 8, f + 13]
    per[li]['e_v'] += [0.0, peak, peak * 0.4, peak * 0.1, 0.0]
for i, (lo, ld) in enumerate(glights):
    pr = per[i]
    for ax in range(3):
        set_fcurve_keys(lo, 'location', ax, pr['f'], [p[ax] for p in pr['loc']], interp='CONSTANT')
    for ch in range(3):
        set_fcurve_keys(ld, 'color', ch, pr['f'], [c[ch] for c in pr['c']], interp='CONSTANT')
    ef, evv = [], []
    for fr_, v in sorted(zip(pr['e_f'], pr['e_v'])):
        if ef and fr_ <= ef[-1] + 1e-3:
            fr_ = ef[-1] + 0.01
        ef.append(fr_)
        evv.append(v)
    set_fcurve_keys(ld, 'energy', 0, ef, evv)

print('scene ready', round(time.time() - t0, 1), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=settings.SCENE_BLEND)

if MODE == 'test':
    for f in FRAMES:
        scene.frame_set(f)
        scene.render.filepath = f'{OUTDIR}/test_{f:04d}.png'
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print('rendered', f, round(time.time() - t1, 2), flush=True)
elif MODE == 'full':
    start = int(argv[1]) if len(argv) > 1 else 0
    end = int(argv[2]) if len(argv) > 2 else N - 1
    scene.frame_start = start
    scene.frame_end = end
    scene.render.filepath = f'{OUTDIR}/f_'
    bpy.ops.render.render(animation=True)
    if start == 0 and end == N - 1:
        open(settings.RENDER_DONE, 'w').write('ok')
