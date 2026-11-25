import os
import bpy, math, sys
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
import blib
from sdf import Prim, build_mesh, taubin


def mat_meat(name='meat'):
    m, nt = blib.new_mat(name)
    tc = nt.node('ShaderNodeTexCoord')
    w = nt.node('ShaderNodeTexWave', i_Scale=5.0, i_Distortion=12.0, i_Detail=4.0)
    nt.link(tc.outputs['Object'], w.inputs['Vector'])
    ramp = nt.node('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.10, 0.008, 0.008, 1)
    cr.elements[1].position = 1.0; cr.elements[1].color = (0.42, 0.20, 0.15, 1)
    e = cr.elements.new(0.45); e.color = (0.22, 0.018, 0.015, 1)
    e = cr.elements.new(0.90); e.color = (0.30, 0.04, 0.03, 1)
    nt.link(w.outputs['Fac'], ramp.inputs[0])
    n = nt.node('ShaderNodeTexNoise', i_Scale=40.0, i_Detail=4.0)
    nt.link(tc.outputs['Object'], n.inputs['Vector'])
    bump = nt.node('ShaderNodeBump', i_Strength=0.4, i_Distance=0.004)
    nt.link(n.outputs[0], bump.inputs['Height'])
    p = blib.principled(nt, rough=0.28, spec=0.6, sss=0.25, coat=0.3, coat_r=0.15)
    p.inputs['Subsurface Radius'].default_value = (0.02, 0.004, 0.003)
    nt.link(ramp.outputs[0], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def meat(name='meat', size=0.11, seed=2):
    rng = np.random.default_rng(seed)
    P = [Prim('ell', 'm', k=0.0, c=(0, 0, 0), r=(size * 0.55, size * 0.8, size * 0.32))]
    for i in range(7):
        c = (rng.normal(0, size * 0.25), rng.normal(0, size * 0.35), rng.normal(0, size * 0.1))
        r = tuple(size * (0.18 + 0.15 * rng.random()) for _ in range(3))
        P.append(Prim('ell', 'm', k=size * 0.15, c=c, r=r))
    v, f = build_mesh(P, h=size / 45.0, margin=size * 0.1)
    v = taubin(v, f, iters=6)
    ob = blib.mesh_obj(name, v, f)
    ob.data.materials.append(mat_meat(name + '_m'))
    return ob


def pebble(name='pebble', size=0.025, mat=None):
    P = [Prim('ell', 'p', k=0.0, c=(0, 0, 0), r=(size, size * 0.8, size * 0.6)),
         Prim('ell', 'p', k=size * 0.3, c=(size * 0.3, 0.1 * size, 0.1 * size), r=(size * 0.6, size * 0.6, size * 0.5))]
    v, f = build_mesh(P, h=size / 12, margin=size * 0.2)
    ob = blib.mesh_obj(name, v, f)
    if mat:
        ob.data.materials.append(mat)
    return ob
