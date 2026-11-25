"""Measures each mood's fog colour through the AgX - Punchy view transform -> build/lut.json.

post.py paints the 2D backdrop with these display colours, so it matches the fogged objects in the
transparent renders. Run with Blender 4.0:  blender -b --python mood_lut.py   (~5 s)
"""
import bpy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings

MOODS = [m['fog'] for m in settings.MOODS]
FACT = [0.3, 0.45, 0.6, 0.8, 1.0, 1.2, 1.35, 1.6]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 1
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Punchy'
except Exception:
    pass
sc.render.resolution_x = len(FACT) * 8
sc.render.resolution_y = len(MOODS) * 8
cd = bpy.data.cameras.new('c')
cd.type = 'ORTHO'
cd.ortho_scale = len(FACT)
co = bpy.data.objects.new('c', cd)
sc.collection.objects.link(co)
sc.camera = co
co.location = (len(FACT) / 2, -len(MOODS) / 2, 10)
for i, m in enumerate(MOODS):
    for j, f in enumerate(FACT):
        me = bpy.data.meshes.new('p')
        me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new('p', me)
        sc.collection.objects.link(ob)
        ob.location = (j, -i - 1, 0)
        mat = bpy.data.materials.new('m')
        mat.use_nodes = True
        nt = mat.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs[0].default_value = (m[0] * f, m[1] * f, m[2] * f, 1)
        em.inputs[1].default_value = 1
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], out.inputs[0])
        me.materials.append(mat)
os.makedirs(settings.BUILD, exist_ok=True)
png = os.path.join(settings.BUILD, 'lut.png')
sc.render.filepath = png
sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(png)
w, h = img.size
px = list(img.pixels)
lut = []
for i in range(len(MOODS)):
    row = []
    for j in range(len(FACT)):
        x, y = j * 8 + 4, h - 1 - (i * 8 + 4)
        k = (y * w + x) * 4
        row.append([int(round(px[k + c] * 255)) for c in range(3)])
    lut.append(row)
json.dump(lut, open(settings.LUT_JSON, 'w'))
print('lut', lut[0][4], lut[-1][4])
