import os
import bpy, math, sys
import numpy as np
from mathutils import Vector
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, '..', 'griffin')):  # blib.py lives in ../griffin
    if _p not in sys.path:
        sys.path.insert(0, _p)
import blib
from env import _vnoise


def fbm(X, Y, oct=6, seed=0, ridged=False, gain=0.5, lac=2.0):
    out = np.zeros_like(X); amp = 1.0; fr = 1.0; norm = 0.0
    for o in range(oct):
        n = _vnoise(X * fr, Y * fr, seed + 31 * o)
        if ridged:
            n = (1.0 - np.abs(n)) ** 2
        out += amp * n; norm += amp; amp *= gain; fr *= lac
    return out / norm


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def height_field(X, Y):
    yc = -4600.0 + 700.0 * np.sin(X / 5200.0)
    ridge = fbm(X / 2600.0, Y / 2600.0, 7, seed=4, ridged=True)
    base = fbm(X / 9000.0, Y / 9000.0, 3, seed=8)
    far_m = smoothstep(0, 2600, (yc - 1300.0) - Y) ** 1.2
    H = -950.0 + 200.0 * base + far_m * (700.0 + 2100.0 * ridge + 500.0 * base)
    for (sx, sy, sh, sr) in ((-2600, -9000, 1500, 650), (1800, -9800, 1800, 800), (5200, -8000, 1250, 600), (-6800, -7400, 1150, 700),
                             (9000, -5200, 900, 900), (-9500, -4600, 1000, 800)):
        d = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
        H += sh * np.exp(-(d / sr) ** 2) * (0.85 + 0.3 * ridge)
    # our side: valley floor rising to a high massif behind the nest cliff (north)
    ours = smoothstep(-2600, -900, Y)
    massif = -950.0 + 890.0 * smoothstep(-120, -5, Y) + 1500.0 * smoothstep(-40, 3200, Y) + 600.0 * ridge * smoothstep(200, 2500, Y)
    sides = 1.0 + 0.0 * X
    H = H * (1 - ours) + massif * ours
    return H


def mat_terrain(name='terrain', haze=(0.62, 0.70, 0.82), haze_dist=9000.0):
    m, nt = blib.new_mat(name)
    geo = nt.node('ShaderNodeNewGeometry')
    tc = nt.node('ShaderNodeTexCoord')
    sep = nt.node('ShaderNodeSeparateXYZ')
    nt.link(geo.outputs['Normal'], sep.inputs[0])
    pz = nt.node('ShaderNodeSeparateXYZ')
    nt.link(geo.outputs['Position'], pz.inputs[0])
    n1 = nt.node('ShaderNodeTexNoise', i_Scale=0.004, i_Detail=8.0, i_Roughness=0.62)
    nt.link(geo.outputs['Position'], n1.inputs['Vector'])
    rock = nt.node('ShaderNodeValToRGB')
    rock.color_ramp.elements[0].position = 0.35; rock.color_ramp.elements[0].color = (0.035, 0.03, 0.027, 1)
    rock.color_ramp.elements[1].position = 0.7; rock.color_ramp.elements[1].color = (0.16, 0.13, 0.105, 1)
    nt.link(n1.outputs[0], rock.inputs[0])
    # snow mask: high & flat-ish
    hz = nt.node('ShaderNodeMapRange', i_From_Min=150.0, i_From_Max=650.0, i_To_Min=0.0, i_To_Max=1.0)
    nt.link(pz.outputs[2], hz.inputs['Value'])
    sl = nt.node('ShaderNodeMapRange', i_From_Min=0.55, i_From_Max=0.75, i_To_Min=0.0, i_To_Max=1.0)
    nt.link(sep.outputs[2], sl.inputs['Value'])
    n2 = nt.node('ShaderNodeTexNoise', i_Scale=0.02, i_Detail=4.0)
    nt.link(geo.outputs['Position'], n2.inputs['Vector'])
    nm = nt.node('ShaderNodeMapRange', i_From_Min=0.3, i_From_Max=0.7, i_To_Min=0.6, i_To_Max=1.4)
    nt.link(n2.outputs[0], nm.inputs['Value'])
    m1 = nt.node('ShaderNodeMath', operation='MULTIPLY'); nt.link(hz.outputs[0], m1.inputs[0]); nt.link(sl.outputs[0], m1.inputs[1])
    m2 = nt.node('ShaderNodeMath', operation='MULTIPLY', use_clamp=True); nt.link(m1.outputs[0], m2.inputs[0]); nt.link(nm.outputs[0], m2.inputs[1])
    mix = nt.node('ShaderNodeMix', data_type='RGBA')
    mix.inputs['B'].default_value = (0.80, 0.82, 0.86, 1)
    nt.link(rock.outputs[0], mix.inputs['A']); nt.link(m2.outputs[0], mix.inputs['Factor'])
    bump = nt.node('ShaderNodeBump', i_Strength=0.6, i_Distance=4.0)
    n3 = nt.node('ShaderNodeTexNoise', i_Scale=0.05, i_Detail=8.0, i_Roughness=0.7)
    nt.link(geo.outputs['Position'], n3.inputs['Vector'])
    nt.link(n3.outputs[0], bump.inputs['Height'])
    p = blib.principled(nt, rough=0.85, spec=0.3)
    nt.link(mix.outputs['Result'], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    # aerial perspective: mix toward haze emission by camera distance
    cd = nt.node('ShaderNodeCameraData')
    hzf = nt.node('ShaderNodeMath', operation='DIVIDE'); hzf.inputs[1].default_value = -haze_dist
    nt.link(cd.outputs['View Distance'], hzf.inputs[0])
    ex = nt.node('ShaderNodeMath', operation='EXPONENT'); nt.link(hzf.outputs[0], ex.inputs[0])
    inv = nt.node('ShaderNodeMath', operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    nt.link(ex.outputs[0], inv.inputs[1])
    em = nt.node('ShaderNodeEmission'); em.inputs[0].default_value = blib.rgb(haze); em.inputs[1].default_value = 1.0
    ms = nt.node('ShaderNodeMixShader')
    nt.link(inv.outputs[0], ms.inputs[0]); nt.link(p.outputs[0], ms.inputs[1]); nt.link(em.outputs[0], ms.inputs[2])
    m.node_tree.nodes['hz_strength'] if False else None
    nt.link(ms.outputs[0], nt.out.inputs[0])
    m['haze_node'] = em.name
    return m


def build_terrain(n=640, size=26000.0, coll=None, haze=(0.62, 0.70, 0.82)):
    xs = np.linspace(-size / 2, size / 2, n)
    ys = np.linspace(-size * 0.75, size * 0.25, n)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    H = height_field(X, Y)
    v = np.stack([X.ravel(), Y.ravel(), H.ravel()], 1)
    idx = np.arange(n * n).reshape(n, n)
    a = idx[:-1, :-1].ravel(); b = idx[1:, :-1].ravel(); c = idx[1:, 1:].ravel(); d = idx[:-1, 1:].ravel()
    f = np.stack([a, b, c, d], 1)
    ob = blib.mesh_obj('terrain', v, f, coll=coll)
    ob.data.materials.append(mat_terrain(haze=haze))
    return ob


def mat_clouds(name='clouds', haze=(0.55, 0.62, 0.74), haze_dist=7000.0):
    m, nt = blib.new_mat(name)
    geo = nt.node('ShaderNodeNewGeometry')
    n1 = nt.node('ShaderNodeTexNoise', i_Scale=0.01, i_Detail=4.0)
    nt.link(geo.outputs['Position'], n1.inputs['Vector'])
    br = nt.node('ShaderNodeMapRange', i_From_Min=0.3, i_From_Max=0.7, i_To_Min=0.80, i_To_Max=0.95)
    nt.link(n1.outputs[0], br.inputs['Value'])
    cc = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(br.outputs[0], cc.inputs[i])
    d = nt.node('ShaderNodeBsdfDiffuse'); nt.link(cc.outputs[0], d.inputs['Color'])
    tr = nt.node('ShaderNodeBsdfTranslucent'); nt.link(cc.outputs[0], tr.inputs['Color'])
    ms = nt.node('ShaderNodeMixShader', i_Fac=0.45)
    nt.link(d.outputs[0], ms.inputs[1]); nt.link(tr.outputs[0], ms.inputs[2])
    em = nt.node('ShaderNodeEmission'); em.inputs[0].default_value = (0.45, 0.48, 0.58, 1); em.inputs[1].default_value = 0.30
    add = nt.node('ShaderNodeAddShader'); nt.link(ms.outputs[0], add.inputs[0]); nt.link(em.outputs[0], add.inputs[1])
    cd = nt.node('ShaderNodeCameraData')
    hzf = nt.node('ShaderNodeMath', operation='DIVIDE'); hzf.inputs[1].default_value = -haze_dist
    nt.link(cd.outputs['View Distance'], hzf.inputs[0])
    ex = nt.node('ShaderNodeMath', operation='EXPONENT'); nt.link(hzf.outputs[0], ex.inputs[0])
    inv = nt.node('ShaderNodeMath', operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    nt.link(ex.outputs[0], inv.inputs[1])
    hem = nt.node('ShaderNodeEmission'); hem.inputs[0].default_value = blib.rgb(haze)
    ms2 = nt.node('ShaderNodeMixShader')
    nt.link(inv.outputs[0], ms2.inputs[0]); nt.link(add.outputs[0], ms2.inputs[1]); nt.link(hem.outputs[0], ms2.inputs[2])
    nt.link(ms2.outputs[0], nt.out.inputs[0])
    return m


def build_clouds(coll=None, z=-360.0, size=36000.0, n=800, amp=240.0, haze=(0.55, 0.62, 0.74)):
    xs = np.linspace(-size / 2, size / 2, n)
    ys = np.linspace(-size * 0.8, size * 0.2, n)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    b1 = fbm(X / 2600.0, Y / 2600.0, 5, seed=41)
    puffs = 1.0 - np.abs(fbm(X / 900.0, Y / 900.0, 5, seed=43))
    H = z + amp * (0.7 * b1 + 0.6 * puffs ** 2.5)
    v = np.stack([X.ravel(), Y.ravel(), H.ravel()], 1)
    idx = np.arange(n * n).reshape(n, n)
    a = idx[:-1, :-1].ravel(); b = idx[1:, :-1].ravel(); c = idx[1:, 1:].ravel(); d = idx[:-1, 1:].ravel()
    f = np.stack([a, b, c, d], 1)
    ob = blib.mesh_obj('clouds', v, f, coll=coll)
    ob.data.materials.append(mat_clouds(haze=haze))
    ob.visible_shadow = False
    return ob


def build_far(sun_elev=22.0, sun_rot=70.0, sun_strength=3.4, sky_strength=0.2, clouds=True, sun_color=(1.0, 0.82, 0.62), haze=None):
    w, sky, bg = blib.sky_world(sun_elev=sun_elev, sun_rot=sun_rot, strength=sky_strength)
    sky.sun_disc = True
    if hasattr(sky, 'sun_intensity'):
        sky.sun_intensity = 0.25
    sun, to_sun = blib.sun_light(sun_elev, sun_rot, strength=sun_strength, color=sun_color)
    hz = haze or (0.55 * sky_strength / 0.2, 0.62 * sky_strength / 0.2, 0.74 * sky_strength / 0.2)
    terr = build_terrain(haze=hz)
    cl = build_clouds(haze=hz) if clouds else None
    return dict(world=w, sky=sky, sun=sun, terrain=terr, clouds=cl, to_sun=to_sun)
