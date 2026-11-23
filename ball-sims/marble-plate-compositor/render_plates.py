"""Renders the still "plates" the compositor paints marbles onto (Cycles, CPU).

Run:  python3 render_plates.py                 (all stages, full quality)
      python3 render_plates.py gbuf,probes     (only some stages)
      python3 render_plates.py all --quick     (fast low-quality test)
  or: blender --background --python render_plates.py -- all

Stages and outputs (in build/plate/):
  beauty      beauty.npy        full frame, all lights, linear RGB
  key, top    key_direct.npy / top_direct.npy   direct light of one lamp, half size
  gbuf        g_pos.npy (2x size), g_nrm.npy, g_id.npy   world position, normal, object id
  probes      probe<i>_<face>.npy + probes.json  cube-map lighting probes at params.probe_positions()
Then run probes.py to turn the probe faces into build/probes_proc.npz.
"""
import os, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from settings import *
sys.path.insert(0, SET_DIR)
from params import probe_positions

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
quick = '--quick' in argv
argv = [a for a in argv if not a.startswith('--')]
stages = (argv[0] if argv else 'all').split(',')
if stages == ['all']:
    stages = ['gbuf', 'probes', 'key', 'top', 'beauty']
if quick:
    BEAUTY_SPP, LIGHT_SPP, PROBE_SPP = 16, 16, 16

OUT = PLATE_DIR
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
vl = bpy.context.view_layer
bg = sc.world.node_tree.nodes['Background']
WSTR = bg.inputs['Strength'].default_value


def exr_settings():
    s = sc.render.image_settings
    s.file_format = 'OPEN_EXR'
    s.color_depth = '32'
    s.exr_codec = 'ZIP'
    s.color_mode = 'RGB'


def render_to_npy(name):
    exr_settings()
    p = os.path.join(OUT, name + '.exr')
    sc.render.filepath = p
    t = time.time()
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    np.save(os.path.join(OUT, name + '.npy'), a)
    os.remove(p)
    print(name, a.shape, 'time %.1f' % (time.time() - t), 'mean', a.mean(axis=(0, 1)), flush=True)
    return a


def lights_only(names, world=True):
    sc.camera = bpy.data.objects['cam']
    for n in LIGHT_NAMES:
        bpy.data.objects[n].visible_camera = False
    for n in LIGHT_NAMES:
        bpy.data.objects[n].hide_render = n not in names
    bg.inputs['Strength'].default_value = WSTR if world else 0.0


def base(pct, spp, denoise=True, bounces=8, fw=1.5):
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = pct
    sc.cycles.samples = spp
    sc.cycles.use_denoising = denoise
    sc.cycles.max_bounces = bounces
    sc.cycles.filter_width = fw
    sc.cycles.use_adaptive_sampling = True


def override(kind):
    m = bpy.data.materials.new('ovr_' + kind)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    if kind == 'pos':
        g = nt.nodes.new('ShaderNodeNewGeometry')
        add = nt.nodes.new('ShaderNodeVectorMath'); add.operation = 'ADD'
        add.inputs[1].default_value = (2.0, 2.0, 1.0)
        nt.links.new(g.outputs['Position'], add.inputs[0])
        nt.links.new(add.outputs['Vector'], em.inputs['Color'])
    elif kind == 'nrm':
        g = nt.nodes.new('ShaderNodeNewGeometry')
        ma = nt.nodes.new('ShaderNodeVectorMath'); ma.operation = 'MULTIPLY_ADD'
        ma.inputs[1].default_value = (0.5, 0.5, 0.5)
        ma.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(g.outputs['Normal'], ma.inputs[0])
        nt.links.new(ma.outputs['Vector'], em.inputs['Color'])
    elif kind == 'id':
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'
        dv.inputs[1].default_value = 16.0
        nt.links.new(oi.outputs['Object Index'], dv.inputs[0])
        nt.links.new(dv.outputs[0], em.inputs['Color'])
    return m


def stage_beauty():
    lights_only(LIGHT_NAMES, True)
    base(100, BEAUTY_SPP)
    render_to_npy('beauty')


def stage_key():
    lights_only(['key'], False)
    base(50, LIGHT_SPP, bounces=0)
    render_to_npy('key_direct')


def stage_top():
    lights_only(['top'], False)
    base(50, LIGHT_SPP, bounces=0)
    render_to_npy('top_direct')


def stage_gbuf():
    lights_only([], False)
    for kind, pct in (('pos', 200), ('nrm', 100), ('id', 100)):
        vl.material_override = override(kind)
        base(pct, 1, denoise=False, bounces=0, fw=0.01)
        sc.cycles.use_adaptive_sampling = False
        render_to_npy('g_' + kind)
    vl.material_override = None


def stage_probes():
    lights_only(LIGHT_NAMES, True)
    sc.render.resolution_percentage = 100
    for n in LIGHT_NAMES:
        bpy.data.objects[n].visible_camera = True
    cd = bpy.data.cameras.new('probe')
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36.0
    cd.lens = 18.0
    cd.clip_start = 0.001
    pc = bpy.data.objects.new('probe', cd)
    sc.collection.objects.link(pc)
    sc.camera = pc
    probes = probe_positions()
    faces = {'px': ((1, 0, 0), (0, 0, 1)), 'nx': ((-1, 0, 0), (0, 0, 1)), 'py': ((0, 1, 0), (0, 0, 1)),
             'ny': ((0, -1, 0), (0, 0, 1)), 'pz': ((0, 0, 1), (0, -1, 0)), 'nz': ((0, 0, -1), (0, 1, 0))}
    sc.render.resolution_x = PROBE_RES
    sc.render.resolution_y = PROBE_RES
    sc.render.resolution_percentage = 100
    sc.cycles.samples = PROBE_SPP
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.filter_width = 1.5
    json.dump([list(map(float, p)) for p in probes], open(os.path.join(OUT, 'probes.json'), 'w'))
    for i, p in enumerate(probes):
        for fn, (fwd, up) in faces.items():
            fwd = np.array(fwd, float); up = np.array(up, float)
            right = np.cross(fwd, up)
            M = Matrix.Identity(4)
            for r in range(3):
                M[r][0] = right[r]; M[r][1] = up[r]; M[r][2] = -fwd[r]
            M.translation = Vector(p)
            pc.matrix_world = M
            render_to_npy(f'probe{i}_{fn}')


for st in stages:
    globals()['stage_' + st]()
print('DONE', stages, '(quick)' if quick else '')
