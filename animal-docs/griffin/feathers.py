import os
import bpy, math, sys
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blib


def feather_geom(length, width, curve=0.10, bend=0.06, asym=0.25, emarg=0.0, nx=10, ny=4, asym_side=-1):
    """local frame: +X base->tip, +Y across, +Z dorsal. returns verts, faces, uvs"""
    verts, uvs = [], []
    for i in range(nx + 1):
        t = i / nx
        prof = (1.0 - t ** 3.2) ** 0.55 * (0.40 + 0.60 * min(1.0, t / 0.22))
        if emarg > 0 and t > 0.45:
            prof *= 1.0 - emarg * min(1.0, (t - 0.45) / 0.2)
        prof = max(prof, 0.02)
        for j in range(ny + 1):
            s = -1.0 + 2.0 * j / ny
            half = width * 0.5 * prof * ((1.0 - asym) if s * asym_side > 0 else 1.0)
            y = s * half
            z = curve * width * prof * (1.0 - s * s) * 0.5 - bend * length * t * t
            verts.append((length * t, y, z))
            uvs.append((t, (s + 1.0) * 0.5))
    faces = []
    W = ny + 1
    for i in range(nx):
        for j in range(ny):
            a = i * W + j
            faces.append((a, a + W, a + W + 1, a + 1))
    return verts, faces, uvs


def mat_feather(name, base_col, tip_col, rachis_col=(0.55, 0.48, 0.40), stripe=0.10, trans=0.12, edge_col=None):
    m, nt = blib.new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    sep = nt.node('ShaderNodeSeparateXYZ')
    nt.link(tc.outputs['UV'], sep.inputs[0])
    ramp = nt.node('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = blib.rgb(base_col)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = blib.rgb(tip_col)
    nt.link(sep.outputs[0], ramp.inputs[0])
    col = ramp.outputs[0]
    if edge_col is not None:
        dv = nt.node('ShaderNodeMath', operation='SUBTRACT'); dv.inputs[1].default_value = 0.5
        nt.link(sep.outputs[1], dv.inputs[0])
        ab = nt.node('ShaderNodeMath', operation='ABSOLUTE'); nt.link(dv.outputs[0], ab.inputs[0])
        em = nt.node('ShaderNodeMapRange', i_From_Min=0.36, i_From_Max=0.5, i_To_Min=0.0, i_To_Max=0.8)
        nt.link(ab.outputs[0], em.inputs['Value'])
        mxe = nt.node('ShaderNodeMix', data_type='RGBA')
        mxe.inputs['B'].default_value = blib.rgb(edge_col)
        nt.link(col, mxe.inputs['A']); nt.link(em.outputs[0], mxe.inputs['Factor'])
        col = mxe.outputs['Result']
    # rachis line
    dv2 = nt.node('ShaderNodeMath', operation='SUBTRACT'); dv2.inputs[1].default_value = 0.5
    nt.link(sep.outputs[1], dv2.inputs[0])
    ab2 = nt.node('ShaderNodeMath', operation='ABSOLUTE'); nt.link(dv2.outputs[0], ab2.inputs[0])
    rm = nt.node('ShaderNodeMapRange', i_From_Min=0.012, i_From_Max=0.03, i_To_Min=1.0, i_To_Max=0.0)
    nt.link(ab2.outputs[0], rm.inputs['Value'])
    tt = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=0.95, i_To_Min=1.0, i_To_Max=0.2)
    nt.link(sep.outputs[0], tt.inputs['Value'])
    rmm = nt.node('ShaderNodeMath', operation='MULTIPLY')
    nt.link(rm.outputs[0], rmm.inputs[0]); nt.link(tt.outputs[0], rmm.inputs[1])
    mxr = nt.node('ShaderNodeMix', data_type='RGBA')
    mxr.inputs['B'].default_value = blib.rgb(rachis_col)
    nt.link(col, mxr.inputs['A']); nt.link(rmm.outputs[0], mxr.inputs['Factor'])
    col = mxr.outputs['Result']
    # barbs: diagonal stripes
    mp = nt.node('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(35))
    mp.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    nt.link(tc.outputs['UV'], mp.inputs['Vector'])
    wv = nt.node('ShaderNodeTexWave', i_Scale=60.0, i_Distortion=1.5, i_Detail=2.0)
    wv.bands_direction = 'X'
    nt.link(mp.outputs[0], wv.inputs['Vector'])
    br = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=1.0, i_To_Min=1.0 - stripe, i_To_Max=1.0)
    nt.link(wv.outputs['Fac'], br.inputs['Value'])
    bc = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(br.outputs[0], bc.inputs[i])
    mul = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    nt.link(col, mul.inputs['A']); nt.link(bc.outputs[0], mul.inputs['B'])
    col = mul.outputs['Result']
    # per-object random tint
    oi = nt.node('ShaderNodeObjectInfo')
    rr = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=1.0, i_To_Min=0.86, i_To_Max=1.12)
    nt.link(oi.outputs['Random'], rr.inputs['Value'])
    rc = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(rr.outputs[0], rc.inputs[i])
    mul2 = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul2.inputs['Factor'].default_value = 1.0
    nt.link(col, mul2.inputs['A']); nt.link(rc.outputs[0], mul2.inputs['B'])
    col = mul2.outputs['Result']
    bump = nt.node('ShaderNodeBump', i_Strength=0.25, i_Distance=0.002)
    nt.link(wv.outputs['Fac'], bump.inputs['Height'])
    p = blib.principled(nt, rough=0.55, spec=0.3)
    nt.link(col, p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    if trans > 0:
        tr = nt.node('ShaderNodeBsdfTranslucent')
        nt.link(col, tr.inputs['Color'])
        mx = nt.node('ShaderNodeMixShader', i_Fac=trans)
        nt.link(p.outputs[0], mx.inputs[1]); nt.link(tr.outputs[0], mx.inputs[2])
        nt.link(mx.outputs[0], nt.out.inputs[0])
    else:
        nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def make_feather_object(name, geom, mat, M_world, coll=None):
    v, f, uv = geom
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            uvl.data[li].uv = uv[vi]
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    blib.link(ob, coll)
    ob.matrix_world = M_world
    return ob


def frame_matrix(p, d, n):
    d = Vector(d).normalized()
    n = Vector(n)
    n = (n - d * n.dot(d)).normalized()
    y = n.cross(d).normalized()
    M = Matrix((d, y, n)).transposed().to_4x4()
    M.translation = Vector(p)
    return M
