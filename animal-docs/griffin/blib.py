import bpy, bmesh, math, json, os, sys, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
# Generated meshes and rigs (build_chick.py / build_adult.py) live here; they are built on first use.
ASSETS = os.path.join(os.environ.get('GRIFFIN_CACHE', os.path.join(HERE, 'build')), '')
_NEEDS = {'chick': ('chick_mesh.npz', 'chick_rig.json'),
          'adult': ('adult_body.npz', 'adult_rig.json', 'adult_wingtube_L.npz', 'adult_wingtube_R.npz')}


def ensure_assets(kind):
    """Run build_chick.py / build_adult.py once if their outputs are not in ASSETS yet."""
    if all(os.path.exists(ASSETS + f) for f in _NEEDS[kind]):
        return
    import runpy
    os.makedirs(ASSETS, exist_ok=True)
    print('griffin: building', kind, 'mesh into', ASSETS, flush=True)
    runpy.run_path(os.path.join(HERE, 'build_%s.py' % kind), run_name='__main__')


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    return sc


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, v, f, smooth=True, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in np.asarray(v, float)], [], [tuple(x) for x in np.asarray(f, int)])
    me.update()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    return ob


def set_uv(me, name, uv_per_vertex):
    uvl = me.uv_layers.new(name=name)
    li = np.zeros(len(me.loops), dtype=np.int64)
    me.loops.foreach_get('vertex_index', li)
    uvl.data.foreach_set('uv', np.asarray(uv_per_vertex, np.float32)[li].ravel())
    return uvl


def set_color_attr(me, name, rgb):
    a = me.color_attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
    rgba = np.ones((len(me.vertices), 4), np.float32)
    rgba[:, :3] = rgb
    a.data.foreach_set('color', rgba.ravel())
    return a


# ---------------------------------------------------------------- nodes
class NT:
    def __init__(self, mat):
        self.mat = mat
        self.nt = mat.node_tree
        self.n = self.nt.nodes
        self.l = self.nt.links
        for nd in list(self.n):
            self.n.remove(nd)
        self.out = self.n.new('ShaderNodeOutputMaterial')

    def node(self, typ, **kw):
        nd = self.n.new(typ)
        for k, v in kw.items():
            if k.startswith('i_'):
                key = k[2:].replace('_', ' ')
                nd.inputs[key].default_value = v
            else:
                setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.l.new(a, b)


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, NT(m)


def principled(nt, **kw):
    p = nt.node('ShaderNodeBsdfPrincipled')
    names = {'base': 'Base Color', 'rough': 'Roughness', 'metal': 'Metallic', 'spec': 'Specular IOR Level',
             'sss': 'Subsurface Weight', 'sss_r': 'Subsurface Radius', 'sss_s': 'Subsurface Scale',
             'coat': 'Coat Weight', 'coat_r': 'Coat Roughness', 'sheen': 'Sheen Weight', 'sheen_r': 'Sheen Roughness',
             'sheen_c': 'Sheen Tint', 'alpha': 'Alpha', 'normal': 'Normal', 'trans': 'Transmission Weight'}
    for k, v in kw.items():
        p.inputs[names[k]].default_value = v
    return p


def rgb(c):
    return (c[0], c[1], c[2], 1.0)


# ---------------------------------------------------------------- materials
def mat_simple(name, color, rough=0.5, spec=0.5, sss=0.0, coat=0.0):
    m, nt = new_mat(name)
    p = principled(nt, base=rgb(color), rough=rough, spec=spec, sss=sss, coat=coat)
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_claw(name='claw'):
    m, nt = new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    sep = nt.node('ShaderNodeSeparateXYZ')
    nt.link(tc.outputs['UV'], sep.inputs[0])
    ramp = nt.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.10, 0.09, 0.08, 1)
    ramp.color_ramp.elements[1].color = (0.018, 0.016, 0.016, 1)
    nt.link(sep.outputs[0], ramp.inputs[0])
    p = principled(nt, rough=0.22, spec=0.6, coat=0.4)
    nt.link(ramp.outputs[0], p.inputs['Base Color'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_beak(name, base_col, mid_col, tip_col, rough=0.3):
    m, nt = new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    sep = nt.node('ShaderNodeSeparateXYZ')
    nt.link(tc.outputs['UV'], sep.inputs[0])
    ramp = nt.node('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = rgb(base_col)
    cr.elements[1].position = 1.0; cr.elements[1].color = rgb(tip_col)
    e = cr.elements.new(0.12); e.color = rgb(mid_col)
    e = cr.elements.new(0.62); e.color = rgb(mid_col)
    nt.link(sep.outputs[0], ramp.inputs[0])
    noise = nt.node('ShaderNodeTexNoise', i_Scale=60.0, i_Detail=4.0)
    bump = nt.node('ShaderNodeBump', i_Strength=0.08, i_Distance=0.002)
    nt.link(noise.outputs[0], bump.inputs['Height'])
    p = principled(nt, rough=rough, spec=0.5, sss=0.08, coat=0.25)
    p.inputs['Subsurface Radius'].default_value = (0.01, 0.006, 0.004)
    nt.link(ramp.outputs[0], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_eye(name, iris_in, iris_out, p=0.10, i=0.30, ring=(0.02, 0.015, 0.01)):
    """eye sphere UV.x = angle from gaze axis / pi."""
    m, nt = new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    sep = nt.node('ShaderNodeSeparateXYZ')
    nt.link(tc.outputs['UV'], sep.inputs[0])
    ramp = nt.node('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.002, 0.002, 0.002, 1)
    cr.elements[1].position = 1.0; cr.elements[1].color = rgb((0.02, 0.016, 0.012))
    for pos, col in ((p, (0.002, 0.002, 0.002)), (p + 0.012, iris_in), (i * 0.82, iris_out), (i, ring), (i + 0.05, (0.03, 0.025, 0.02))):
        e = cr.elements.new(pos); e.color = rgb(col)
    nt.link(sep.outputs[0], ramp.inputs[0])
    noise = nt.node('ShaderNodeTexNoise', i_Scale=40.0, i_Detail=6.0)
    nt.link(tc.outputs['Object'], noise.inputs['Vector'])
    vr = nt.node('ShaderNodeMapRange', i_From_Min=0.35, i_From_Max=0.65, i_To_Min=0.75, i_To_Max=1.2)
    nt.link(noise.outputs[0], vr.inputs['Value'])
    cm = nt.node('ShaderNodeCombineColor')
    for k in range(3):
        nt.link(vr.outputs[0], cm.inputs[k])
    mul = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    nt.link(ramp.outputs[0], mul.inputs['A']); nt.link(cm.outputs[0], mul.inputs['B'])
    pr = principled(nt, rough=0.12, spec=0.5, coat=0.45, coat_r=0.02)
    nt.link(mul.outputs['Result'], pr.inputs['Base Color'])
    nt.link(pr.outputs[0], nt.out.inputs[0])
    return m


def _attr_uv_vector(nt, uvname_a='rest_xy', uvname_b='rest_z'):
    uva = nt.node('ShaderNodeUVMap', uv_map=uvname_a)
    uvb = nt.node('ShaderNodeUVMap', uv_map=uvname_b)
    sa = nt.node('ShaderNodeSeparateXYZ'); sb = nt.node('ShaderNodeSeparateXYZ')
    nt.link(uva.outputs[0], sa.inputs[0]); nt.link(uvb.outputs[0], sb.inputs[0])
    cmb = nt.node('ShaderNodeCombineXYZ')
    nt.link(sa.outputs[0], cmb.inputs[0]); nt.link(sa.outputs[1], cmb.inputs[1]); nt.link(sb.outputs[0], cmb.inputs[2])
    return cmb.outputs[0]


def down_color_tree(nt, cream, tawny, dark, spot, spot_scale=None):
    """colour from uv 'attr' (u=tawny, v=dark) and 'attr2' (u=spot, v=brightness)."""
    uv = nt.node('ShaderNodeUVMap', uv_map='attr')
    sep = nt.node('ShaderNodeSeparateXYZ')
    nt.link(uv.outputs[0], sep.inputs[0])
    uv2 = nt.node('ShaderNodeUVMap', uv_map='attr2')
    sep2 = nt.node('ShaderNodeSeparateXYZ')
    nt.link(uv2.outputs[0], sep2.inputs[0])
    mix1 = nt.node('ShaderNodeMix', data_type='RGBA')
    mix1.inputs['A'].default_value = rgb(cream); mix1.inputs['B'].default_value = rgb(tawny)
    nt.link(sep.outputs[0], mix1.inputs['Factor'])
    mix2 = nt.node('ShaderNodeMix', data_type='RGBA')
    mix2.inputs['B'].default_value = rgb(spot)
    nt.link(mix1.outputs['Result'], mix2.inputs['A'])
    sm = nt.node('ShaderNodeMath', operation='MULTIPLY', i_Value=0.55)
    sm.inputs[1].default_value = 0.55
    nt.link(sep2.outputs[0], sm.inputs[0])
    nt.link(sm.outputs[0], mix2.inputs['Factor'])
    mix3 = nt.node('ShaderNodeMix', data_type='RGBA')
    mix3.inputs['B'].default_value = rgb(dark)
    nt.link(mix2.outputs['Result'], mix3.inputs['A'])
    nt.link(sep.outputs[1], mix3.inputs['Factor'])
    mulc = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mulc.inputs['Factor'].default_value = 1.0
    nt.link(mix3.outputs['Result'], mulc.inputs['A'])
    cmb = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(sep2.outputs[1], cmb.inputs[i])
    nt.link(cmb.outputs[0], mulc.inputs['B'])
    return mulc.outputs['Result']


def mat_down_hair(name, cream, tawny, dark, spot):
    m, nt = new_mat(name)
    col = down_color_tree(nt, cream, tawny, dark, spot)
    hi = nt.node('ShaderNodeHairInfo')
    rr = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=1.0, i_To_Min=0.78, i_To_Max=1.04)
    nt.link(hi.outputs['Intercept'], rr.inputs['Value'])
    cm = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(rr.outputs[0], cm.inputs[i])
    shade = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    shade.inputs['Factor'].default_value = 1.0
    nt.link(col, shade.inputs['A']); nt.link(cm.outputs[0], shade.inputs['B'])
    dif = nt.node('ShaderNodeBsdfDiffuse')
    nt.link(shade.outputs['Result'], dif.inputs['Color'])
    tr = nt.node('ShaderNodeBsdfTranslucent')
    nt.link(shade.outputs['Result'], tr.inputs['Color'])
    mx = nt.node('ShaderNodeMixShader', i_Fac=0.32)
    nt.link(dif.outputs[0], mx.inputs[1]); nt.link(tr.outputs[0], mx.inputs[2])
    gl = nt.node('ShaderNodeBsdfAnisotropic') if hasattr(bpy.types, 'ShaderNodeBsdfAnisotropic') else nt.node('ShaderNodeBsdfGlossy')
    try:
        gl.inputs['Roughness'].default_value = 0.45
    except Exception:
        pass
    mx2 = nt.node('ShaderNodeMixShader', i_Fac=0.05)
    nt.link(mx.outputs[0], mx2.inputs[1]); nt.link(gl.outputs[0], mx2.inputs[2])
    nt.link(mx2.outputs[0], nt.out.inputs[0])
    return m


def mat_down_skin(name, cream, tawny, dark, spot, darken=0.78):
    m, nt = new_mat(name)
    col = down_color_tree(nt, cream, tawny, dark, spot)
    mul = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    mul.inputs['B'].default_value = (darken, darken, darken, 1)
    nt.link(col, mul.inputs['A'])
    p = principled(nt, rough=0.9, spec=0.25, sheen=0.8, sheen_r=0.5)
    nt.link(mul.outputs['Result'], p.inputs['Base Color'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_toes(name, col=(0.80, 0.66, 0.30)):
    m, nt = new_mat(name)
    vor = nt.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=420.0)
    bump = nt.node('ShaderNodeBump', i_Strength=0.6, i_Distance=0.0015, invert=True)
    nt.link(vor.outputs['Distance'], bump.inputs['Height'])
    rr = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=0.08, i_To_Min=0.65, i_To_Max=1.0)
    nt.link(vor.outputs['Distance'], rr.inputs['Value'])
    mul = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    mul.inputs['A'].default_value = rgb(col)
    cm = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(rr.outputs[0], cm.inputs[i])
    nt.link(cm.outputs[0], mul.inputs['B'])
    p = principled(nt, rough=0.5, spec=0.5, sss=0.1)
    p.inputs['Subsurface Radius'].default_value = (0.006, 0.003, 0.002)
    nt.link(mul.outputs['Result'], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ---------------------------------------------------------------- procedural meshes
def frame_from_dir(d, up=(0, 0, 1)):
    d = Vector(d).normalized()
    up = Vector(up)
    if abs(d.dot(up)) > 0.98:
        up = Vector((0, 1, 0))
    x = up.cross(d).normalized()
    y = d.cross(x).normalized()
    return x, y, d


def beak_mesh(name, base, direction, L, W, H, hook=0.55, lower=False, segs=28, ring=20, side_up=(0, 0, 1)):
    """hooked beak (upper mandible) or lower mandible. local frame: f=forward, u=up, s=side."""
    f = Vector(direction).normalized()
    s = f.cross(Vector(side_up)).normalized()
    u = s.cross(f).normalized()
    verts = []
    uvs = []
    for i in range(segs + 1):
        t = i / segs
        if not lower:
            x = L * t
            y = -L * (0.10 * t * t + hook * max(0.0, t - 0.55) ** 2 * 2.2)
            w = W * (1 - t) ** 0.75 + W * 0.04
            hh = H * (1 - 0.82 * t ** 1.2) + H * 0.03
        else:
            x = L * 0.78 * t
            y = -L * 0.10 * t - H * 0.45
            w = W * 0.88 * (1 - t) ** 0.8 + W * 0.04
            hh = H * 0.42 * (1 - 0.8 * t) + H * 0.03
        c = Vector(base) + f * x + u * y
        for j in range(ring):
            a = 2 * math.pi * j / ring
            ca, sa = math.cos(a), math.sin(a)
            if not lower:
                vz = hh * (0.62 * sa if sa > 0 else 0.38 * sa)
                vy = w * ca * (1.0 if sa > -0.2 else 0.92)
            else:
                vz = hh * (0.35 * sa if sa > 0 else 0.65 * sa)
                vy = w * ca
            verts.append(c + s * vy + u * vz)
            uvs.append((t, j / ring))
    faces = []
    for i in range(segs):
        for j in range(ring):
            a = i * ring + j
            b = i * ring + (j + 1) % ring
            faces.append((a, b, b + ring, a + ring))
    tip = len(verts)
    tipc = Vector(base) + f * (L if not lower else L * 0.78)
    if not lower:
        tipc = tipc + u * (-L * (0.10 + hook * 0.45 ** 2 * 2.2))
    else:
        tipc = tipc + u * (-L * 0.10 - H * 0.45)
    verts.append(tipc)
    uvs.append((1.0, 0.5))
    last = segs * ring
    for j in range(ring):
        faces.append((last + j, last + (j + 1) % ring, tip))
    cap = len(verts)
    verts.append(Vector(base))
    uvs.append((0.0, 0.5))
    for j in range(ring):
        faces.append(((j + 1) % ring, j, cap))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            uvl.data[li].uv = uvs[vi]
    ob = bpy.data.objects.new(name, me)
    link(ob)
    return ob


def sphere_mesh(name, center, radius, direction, seg=40, rings=24):
    """uv sphere whose local +Z points along direction; UV.x = angle from +Z / pi"""
    x, y, z = frame_from_dir(direction)
    verts, uvs = [], []
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            lv = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
            verts.append(Vector(center) + (x * lv.x + y * lv.y + z * lv.z) * radius)
            uvs.append((th / math.pi, j / seg))
    faces = []
    for i in range(rings):
        for j in range(seg):
            a = i * seg + j
            b = i * seg + (j + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            uvl.data[li].uv = uvs[vi]
    ob = bpy.data.objects.new(name, me)
    link(ob)
    return ob


def lid_mesh(name, center, radius, direction, upper=True, seg=28, rings=10):
    """quarter spherical shell: closed it covers the upper (or lower) front of the eye.
    local frame x=side, y=up, z=gaze. margin lies on the x-z great circle. rotate about local x to open."""
    x, y, z = frame_from_dir(direction)
    verts = []
    sgn = 1.0 if upper else -1.0
    for i in range(rings + 1):
        th = sgn * math.pi * 0.5 * i / rings
        for j in range(seg + 1):
            ph = -math.pi * 0.5 + math.pi * j / seg
            verts.append(Vector((math.sin(ph), math.cos(ph) * math.sin(th), math.cos(ph) * math.cos(th))))
    faces = []
    W = seg + 1
    for i in range(rings):
        for j in range(seg):
            a = i * W + j
            faces.append((a, a + W, a + W + 1, a + 1) if upper else (a, a + 1, a + W + 1, a + W))
    out = [Vector(center) + (x * p.x + y * p.y + z * p.z) * radius for p in verts]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in out], [], faces)
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    link(ob)
    return ob, (x, y, z)


# ---------------------------------------------------------------- rig
class Rig:
    def __init__(self, arm_ob):
        self.ob = arm_ob
        self.bones = arm_ob.data.bones
        self.rest = {b.name: b.matrix_local.copy() for b in self.bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in self.bones}
        self.order = [b.name for b in self.bones]
        self.length = {b.name: b.length for b in self.bones}
        for pb in arm_ob.pose.bones:
            pb.rotation_mode = 'QUATERNION'

    def local_from_creature(self, bname, Q):
        B = self.rest[bname].to_3x3()
        return (B.inverted() @ Q @ B)

    def fk(self, local_rot, root_loc=Vector((0, 0, 0))):
        pm = {}
        for b in self.order:
            L = Matrix.Identity(4)
            if b in local_rot:
                L = local_rot[b].to_4x4()
            if self.parent[b] is None:
                L = Matrix.Translation(root_loc) @ L if b == self.order[0] else L
                pm[b] = self.rest[b] @ L
            else:
                p = self.parent[b]
                pm[b] = pm[p] @ (self.rest[p].inverted() @ self.rest[b]) @ L
        return pm

    def ik2(self, local_rot, upper, lower, target, pole, end=None, end_world_rot=None, root_loc=Vector((0, 0, 0))):
        """target/pole in armature space. modifies local_rot for upper/lower (and end)."""
        pm = self.fk(local_rot, root_loc)
        H = pm[upper].to_translation()
        L1 = self.length[upper]; L2 = self.length[lower]
        T = Vector(target)
        d = T - H
        dist = max(min(d.length, (L1 + L2) * 0.999), abs(L1 - L2) * 1.01 + 1e-5)
        dn = d.normalized()
        pv = Vector(pole) - H
        pn = (pv - dn * pv.dot(dn))
        if pn.length < 1e-8:
            pn = Vector((0, -1, 0))
        pn.normalize()
        ca = (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist)
        ca = max(-1.0, min(1.0, ca))
        a = math.acos(ca)
        K = H + (dn * math.cos(a) + pn * math.sin(a)) * L1
        Tc = H + dn * dist
        for bname, want in ((upper, (K - H).normalized()), (lower, (Tc - K).normalized())):
            pm = self.fk(local_rot, root_loc)
            p = self.parent[bname]
            R0 = (pm[p] @ (self.rest[p].inverted() @ self.rest[bname])).to_3x3() if p else self.rest[bname].to_3x3()
            cur = R0 @ Vector((0, 1, 0))
            dq = cur.rotation_difference(want).to_matrix()
            R1 = dq @ R0
            local_rot[bname] = (R0.inverted() @ R1)
        if end is not None:
            pm = self.fk(local_rot, root_loc)
            p = self.parent[end]
            R0 = (pm[p] @ (self.rest[p].inverted() @ self.rest[end])).to_3x3()
            Rw = end_world_rot if end_world_rot is not None else self.rest[end].to_3x3()
            local_rot[end] = R0.inverted() @ Rw
        return local_rot

    def key(self, frame, local_rot, root_loc=None):
        for b in self.order:
            pb = self.ob.pose.bones[b]
            q = local_rot.get(b, Matrix.Identity(3)).to_quaternion()
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            if b == self.order[0] and root_loc is not None:
                pb.location = root_loc
                pb.keyframe_insert('location', frame=frame)


def creature_rot(rx=0.0, ry=0.0, rz=0.0, order='XYZ'):
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), order).to_matrix()


def build_armature(name, bones, coll=None):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    link(ob, coll)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for (bn, h, t, parent, zdir) in bones:
        eb = arm.edit_bones.new(bn)
        eb.head = Vector(h)
        eb.tail = Vector(t)
        eb.align_roll(Vector(zdir))
        eb.use_deform = True
    for (bn, h, t, parent, zdir) in bones:
        if parent:
            arm.edit_bones[bn].parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def bind(mesh_ob, arm_ob, W, bone_names):
    for bi, bn in enumerate(bone_names):
        w = W[:, bi]
        idx = np.where(w > 0.002)[0]
        if len(idx) == 0:
            continue
        vg = mesh_ob.vertex_groups.new(name=bn)
        q = np.round(w[idx] * 200) / 200
        for val in np.unique(q):
            sel = idx[q == val]
            vg.add(sel.tolist(), float(val), 'REPLACE')
    mod = mesh_ob.modifiers.new('arm', 'ARMATURE')
    mod.object = arm_ob
    mesh_ob.parent = arm_ob


def parent_to_bone(ob, arm_ob, bone):
    mw = ob.matrix_world.copy()
    ob.parent = arm_ob
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw


def add_weight_group(ob, name, values):
    vg = ob.vertex_groups.new(name=name)
    q = np.round(np.clip(values, 0, 1) * 100) / 100
    for val in np.unique(q):
        if val <= 0:
            continue
        sel = np.where(q == val)[0]
        vg.add(sel.tolist(), float(val), 'REPLACE')
    return vg


def sky_world(sun_elev=22.0, sun_rot=60.0, strength=1.0, air=1.0, dust=1.0, ozone=1.0, name='sky'):
    w = bpy.data.worlds.new(name)
    bpy.context.scene.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(sun_elev)
    sky.sun_rotation = math.radians(-sun_rot)
    for attr, val in (('air_density', air), ('aerosol_density', dust), ('dust_density', dust), ('ozone_density', ozone)):
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    sky.sun_disc = False
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    return w, sky, bg


def sun_light(direction_elev, direction_rot, strength=4.0, color=(1.0, 0.92, 0.82), angle=1.5, name='sun'):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(angle)
    ob = bpy.data.objects.new(name, ld)
    link(ob)
    # sun points along -Z of object; build rotation so light comes FROM (elev, rot)
    el = math.radians(direction_elev); rt = math.radians(direction_rot)
    to_sun = Vector((math.cos(el) * math.sin(rt), -math.cos(el) * math.cos(rt), math.sin(el)))
    ob.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()
    return ob, to_sun


def camera(name, loc, look_at, lens=50.0, sensor=36.0, fstop=None, focus=None, clip_end=20000):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = sensor
    cd.clip_start = 0.01
    cd.clip_end = clip_end
    ob = bpy.data.objects.new(name, cd)
    link(ob)
    ob.location = loc
    d = Vector(look_at) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = focus if focus else d.length
    bpy.context.scene.camera = ob
    return ob


def render_settings(res=(720, 1280), spp=16, denoise=True, bounces=(4, 2, 1, 2, 8), transparent=False, fps=24,
                    quality='FAST', persistent=True, curves='RIBBONS'):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    c = sc.cycles
    c.device = 'CPU'
    c.samples = spp
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.03
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces, c.transparent_max_bounces = bounces
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 6.0
    c.use_denoising = denoise
    if denoise:
        c.denoiser = 'OPENIMAGEDENOISE'
        c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        c.denoising_prefilter = 'ACCURATE' if quality == 'HIGH' else 'FAST'
        try:
            c.denoising_quality = quality
        except Exception:
            pass
    try:
        c.use_light_tree = False
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.fps = fps
    sc.render.use_persistent_data = persistent
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.exposure = -0.9
    try:
        sc.view_settings.look = 'AgX - Base Contrast'
    except Exception:
        pass
    sc.cycles_curves.shape = curves
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.image_settings.color_depth = '8'
    return sc
