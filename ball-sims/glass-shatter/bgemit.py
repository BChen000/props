"""Window-mapped plate emission for Cycles: camera rays that hit static objects (or the world) show a
precomputed background image instead of being shaded, so only moving objects cost render time.
Shared with ../cloth-faces/scene.py."""
import bpy
import numpy as np


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
