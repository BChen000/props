import os
import bpy, bmesh, math, sys, random
import numpy as np
from mathutils import Vector, Matrix, Euler, noise
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, '..', 'griffin')):  # blib.py lives in ../griffin
    if _p not in sys.path:
        sys.path.insert(0, _p)
import blib


def mat_rock(name='rock', base=(0.30, 0.235, 0.18), dark=(0.06, 0.05, 0.04), lichen=True, scale=1.0):
    m, nt = blib.new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    mp = nt.node('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.link(tc.outputs['Object'], mp.inputs['Vector'])
    # macro tone variation (subtle)
    n1 = nt.node('ShaderNodeTexNoise', i_Scale=0.7, i_Detail=3.0, i_Roughness=0.5)
    nt.link(mp.outputs[0], n1.inputs['Vector'])
    r1 = nt.node('ShaderNodeValToRGB')
    r1.color_ramp.elements[0].position = 0.38; r1.color_ramp.elements[0].color = blib.rgb(tuple(c * 0.75 for c in base))
    r1.color_ramp.elements[1].position = 0.62; r1.color_ramp.elements[1].color = blib.rgb(tuple(min(1, c * 1.12) for c in base))
    nt.link(n1.outputs[0], r1.inputs[0])
    # granite grain
    g = nt.node('ShaderNodeTexNoise', i_Scale=55.0, i_Detail=2.0, i_Roughness=0.5)
    nt.link(mp.outputs[0], g.inputs['Vector'])
    gr = nt.node('ShaderNodeMapRange', i_From_Min=0.42, i_From_Max=0.62, i_To_Min=0.72, i_To_Max=1.15)
    nt.link(g.outputs[0], gr.inputs['Value'])
    gc = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(gr.outputs[0], gc.inputs[i])
    mul = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    nt.link(r1.outputs[0], mul.inputs['A']); nt.link(gc.outputs[0], mul.inputs['B'])
    col = mul.outputs['Result']
    # cracks
    if lichen:
        n2 = nt.node('ShaderNodeTexNoise', i_Scale=2.2, i_Detail=2.0, i_Roughness=0.65)
        nt.link(mp.outputs[0], n2.inputs['Vector'])
        lm = nt.node('ShaderNodeMapRange', i_From_Min=0.60, i_From_Max=0.68, i_To_Min=0.0, i_To_Max=0.55)
        nt.link(n2.outputs[0], lm.inputs['Value'])
        mx = nt.node('ShaderNodeMix', data_type='RGBA')
        mx.inputs['B'].default_value = blib.rgb((0.40, 0.40, 0.30))
        nt.link(col, mx.inputs['A']); nt.link(lm.outputs[0], mx.inputs['Factor'])
        col = mx.outputs['Result']
    # bump: cracks + mid + fine
    n4 = nt.node('ShaderNodeTexNoise', i_Scale=14.0, i_Detail=3.0, i_Roughness=0.6)
    nt.link(mp.outputs[0], n4.inputs['Vector'])
    add = nt.node('ShaderNodeMath', operation='MULTIPLY_ADD')
    add.inputs[1].default_value = 0.6
    nt.link(n4.outputs[0], add.inputs[0]); add.inputs[2].default_value = 0.0
    bump = nt.node('ShaderNodeBump', i_Strength=0.6, i_Distance=0.012)
    nt.link(add.outputs[0], bump.inputs['Height'])
    p = blib.principled(nt, rough=0.9, spec=0.3)
    nt.link(col, p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def rock_from_cube(name, loc, size, rot=(0, 0, 0), seed=0, level=5, disp1=0.35, disp2=0.08, tex_scale1=1.2, tex_scale2=0.35, mat=None, coll=None, apply=True):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    blib.link(ob, coll)
    ob.location = loc
    ob.scale = size
    ob.rotation_euler = rot
    sub = ob.modifiers.new('sub', 'SUBSURF'); sub.levels = level; sub.render_levels = level
    t1 = bpy.data.textures.new(name + '_t1', 'VORONOI'); t1.noise_scale = tex_scale1; t1.distance_metric = 'DISTANCE'
    t1.noise_intensity = 1.0
    d1 = ob.modifiers.new('d1', 'DISPLACE'); d1.texture = t1; d1.strength = disp1; d1.mid_level = 0.5
    d1.texture_coords = 'GLOBAL'
    t2 = bpy.data.textures.new(name + '_t2', 'CLOUDS'); t2.noise_scale = tex_scale2; t2.noise_depth = 4
    d2 = ob.modifiers.new('d2', 'DISPLACE'); d2.texture = t2; d2.strength = disp2; d2.mid_level = 0.5
    d2.texture_coords = 'GLOBAL'
    if mat:
        me.materials.append(mat)
    if apply:
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        nm = bpy.data.meshes.new_from_object(ev)
        ob.modifiers.clear()
        ob.data = nm
        nm.polygons.foreach_set('use_smooth', [True] * len(nm.polygons))
    return ob


def heightmap_sheet(name, nx, ny, sx, sy, height_fn, mat=None, coll=None):
    xs = np.linspace(-sx / 2, sx / 2, nx)
    ys = np.linspace(-sy / 2, sy / 2, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = height_fn(X, Y)
    v = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(nx * ny).reshape(nx, ny)
    a = idx[:-1, :-1].ravel(); b = idx[1:, :-1].ravel(); c = idx[1:, 1:].ravel(); d = idx[:-1, 1:].ravel()
    f = np.stack([a, b, c, d], 1)
    ob = blib.mesh_obj(name, v, f, coll=coll)
    if mat:
        ob.data.materials.append(mat)
    return ob


def fbm2(X, Y, octaves=6, seed=0, lac=2.0, gain=0.5, ridged=False):
    out = np.zeros_like(X)
    amp = 1.0; freq = 1.0
    for o in range(octaves):
        n = _vnoise(X * freq, Y * freq, seed + o * 17)
        if ridged:
            n = 1.0 - np.abs(n)
            n = n * n
        out += amp * n
        amp *= gain; freq *= lac
    return out


def _vnoise(X, Y, seed):
    """smooth value noise via random gradients (vectorised perlin-like)."""
    rng = np.random.default_rng(seed)
    perm = rng.permutation(256)
    perm = np.concatenate([perm, perm])
    ang = rng.random(256) * 2 * np.pi
    gx, gy = np.cos(ang), np.sin(ang)
    xi = np.floor(X).astype(int); yi = np.floor(Y).astype(int)
    xf = X - xi; yf = Y - yi
    xi &= 255; yi &= 255
    def grad(ix, iy, dx, dy):
        h = perm[perm[ix] + iy]
        return gx[h] * dx + gy[h] * dy
    u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
    w = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
    n00 = grad(xi, yi, xf, yf)
    n10 = grad((xi + 1) & 255, yi, xf - 1, yf)
    n01 = grad(xi, (yi + 1) & 255, xf, yf - 1)
    n11 = grad((xi + 1) & 255, (yi + 1) & 255, xf - 1, yf - 1)
    x1 = n00 + u * (n10 - n00)
    x2 = n01 + u * (n11 - n01)
    return (x1 + w * (x2 - x1)) * 1.4


def nest(name='nest', center=(0, 0, 0), r_out=0.55, r_in=0.24, height=0.20, n=420, seed=3, coll=None):
    rng = np.random.default_rng(seed)
    m_stick = mat_sticks(name + '_stick')
    verts = []; faces = []
    for i in range(n):
        layer = rng.random()
        ang = rng.random() * 2 * math.pi
        rr = r_in + (r_out - r_in) * (0.25 + 0.75 * rng.random() ** 0.7)
        z = height * (0.15 + 0.85 * layer) * (0.6 + 0.4 * (rr - r_in) / (r_out - r_in))
        z = z * (1.0 - 0.55 * max(0.0, (rr - r_in * 1.1)) / (r_out - r_in)) + 0.02
        L = 0.25 + 0.45 * rng.random()
        rad = 0.006 + 0.010 * rng.random() ** 2
        tang = Vector((-math.sin(ang), math.cos(ang), 0))
        radial = Vector((math.cos(ang), math.sin(ang), 0))
        d = (tang * math.cos(rng.normal(0, 0.45)) + radial * math.sin(rng.normal(0, 0.45))).normalized()
        d.z = rng.normal(0, 0.12)
        d.normalize()
        c = Vector(center) + radial * rr + Vector((0, 0, z))
        bend = rng.normal(0, 0.04)
        _stick(verts, faces, c - d * L / 2, c + d * L / 2, rad, bend, rng)
    me = bpy.data.meshes.new(name + '_sticks')
    me.from_pydata(verts, [], faces)
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name + '_sticks', me)
    blib.link(ob, coll)
    me.materials.append(m_stick)
    # inner lining (soft bowl)
    lining = bowl(name + '_lining', center, r_in * 1.35, height * 0.55, coll=coll)
    lining.data.materials.append(mat_lining(name + '_lin'))
    return ob, lining


def _stick(verts, faces, a, b, rad, bend, rng, seg=6, ring=5):
    d = (b - a)
    L = d.length
    dn = d.normalized()
    side = dn.cross(Vector((0, 0, 1)))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    up = side.cross(dn).normalized()
    base = len(verts)
    for i in range(seg + 1):
        t = i / seg
        c = a + d * t + up * (bend * math.sin(math.pi * t) * L) + side * (0.3 * bend * math.sin(2 * math.pi * t) * L)
        r = rad * (1.0 - 0.45 * t)
        for j in range(ring):
            an = 2 * math.pi * j / ring + 0.3 * i
            verts.append(tuple(c + (side * math.cos(an) + up * math.sin(an)) * r))
    for i in range(seg):
        for j in range(ring):
            p = base + i * ring + j
            q = base + i * ring + (j + 1) % ring
            faces.append((p, q, q + ring, p + ring))
    faces.append(tuple(base + j for j in range(ring))[::-1])
    faces.append(tuple(base + seg * ring + j for j in range(ring)))


def bowl(name, center, radius, depth, nr=24, na=48, coll=None):
    verts = []; faces = []
    for i in range(nr + 1):
        r = radius * i / nr
        z = -depth * (1 - (r / radius) ** 2) * 0.5 + depth * 0.5
        for j in range(na):
            a = 2 * math.pi * j / na
            nz = 0.004 * math.sin(a * 7 + i) + 0.004 * math.cos(a * 5 - 2 * i)
            verts.append((center[0] + r * math.cos(a), center[1] + r * math.sin(a), center[2] + z + nz + 0.03))
    for i in range(nr):
        for j in range(na):
            a = i * na + j; b = i * na + (j + 1) % na
            faces.append((a, b, b + na, a + na))
    ob = blib.mesh_obj(name, np.array(verts), np.array(faces), coll=coll)
    return ob


def mat_sticks(name):
    m, nt = blib.new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    n1 = nt.node('ShaderNodeTexNoise', i_Scale=9.0, i_Detail=3.0)
    nt.link(tc.outputs['Object'], n1.inputs['Vector'])
    ramp = nt.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[0].color = blib.rgb((0.10, 0.07, 0.045))
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = blib.rgb((0.42, 0.34, 0.25))
    nt.link(n1.outputs[0], ramp.inputs[0])
    w = nt.node('ShaderNodeTexWave', i_Scale=40.0, i_Distortion=6.0)
    nt.link(tc.outputs['Object'], w.inputs['Vector'])
    bump = nt.node('ShaderNodeBump', i_Strength=0.4, i_Distance=0.003)
    nt.link(w.outputs['Fac'], bump.inputs['Height'])
    p = blib.principled(nt, rough=0.85, spec=0.3)
    nt.link(ramp.outputs[0], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_lining(name):
    m, nt = blib.new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    w = nt.node('ShaderNodeTexWave', i_Scale=22.0, i_Distortion=14.0, i_Detail=4.0)
    nt.link(tc.outputs['Object'], w.inputs['Vector'])
    ramp = nt.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = blib.rgb((0.16, 0.12, 0.07))
    ramp.color_ramp.elements[1].color = blib.rgb((0.52, 0.44, 0.28))
    nt.link(w.outputs['Fac'], ramp.inputs[0])
    bump = nt.node('ShaderNodeBump', i_Strength=0.7, i_Distance=0.006)
    nt.link(w.outputs['Fac'], bump.inputs['Height'])
    p = blib.principled(nt, rough=0.9, spec=0.2, sheen=0.5)
    nt.link(ramp.outputs[0], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_shell(name='shell'):
    m, nt = blib.new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    vor = nt.node('ShaderNodeTexVoronoi', feature='F1', i_Scale=60.0)
    nt.link(tc.outputs['Object'], vor.inputs['Vector'])
    sm = nt.node('ShaderNodeMapRange', i_From_Min=0.08, i_From_Max=0.16, i_To_Min=1.0, i_To_Max=0.0)
    nt.link(vor.outputs['Distance'], sm.inputs['Value'])
    n = nt.node('ShaderNodeTexNoise', i_Scale=25.0)
    nt.link(tc.outputs['Object'], n.inputs['Vector'])
    mm = nt.node('ShaderNodeMath', operation='MULTIPLY')
    nt.link(sm.outputs[0], mm.inputs[0]); nt.link(n.outputs[0], mm.inputs[1])
    mx = nt.node('ShaderNodeMix', data_type='RGBA')
    mx.inputs['A'].default_value = blib.rgb((0.82, 0.76, 0.64)); mx.inputs['B'].default_value = blib.rgb((0.36, 0.22, 0.12))
    nt.link(mm.outputs[0], mx.inputs['Factor'])
    p = blib.principled(nt, rough=0.45, spec=0.4, sss=0.15)
    nt.link(mx.outputs['Result'], p.inputs['Base Color'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def egg_shell_pieces(name, center, size=0.10, seed=5, n=4, coll=None, mat=None):
    """broken shell fragments lying in a nest."""
    rng = np.random.default_rng(seed)
    mat = mat or mat_shell(name + '_m')
    obs = []
    for k in range(n):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
        # cut a cap-like patch with jagged edge
        axis = Vector((rng.normal(), rng.normal(), rng.normal())).normalized()
        lim = 0.15 + 0.35 * rng.random()
        rem = []
        for f in bm.faces:
            c = f.calc_center_median()
            jag = 0.10 * math.sin(c.x * 23 + k) * math.cos(c.y * 19 - k) + 0.05 * math.sin(c.z * 41)
            if c.normalized().dot(axis) < lim + jag:
                rem.append(f)
        bmesh.ops.delete(bm, geom=rem, context='FACES')
        for v in bm.verts:
            v.co.x *= size * 0.78; v.co.y *= size * 0.78; v.co.z *= size
        me = bpy.data.meshes.new(f'{name}_{k}')
        bm.to_mesh(me); bm.free()
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        ob = bpy.data.objects.new(f'{name}_{k}', me)
        blib.link(ob, coll)
        sol = ob.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0025; sol.offset = -1
        me.materials.append(mat)
        obs.append(ob)
    return obs
