"""Close-up hero renders for the thumbnail (Blender 4.0), from build/scene.blend.

For each of settings.THUMB 'top' and 'bottom' it picks a hit (round, hit index), goes `after_frames`
past it so the block's glow has its colour back (at the peak it bloom-whites out), moves the camera
`zoom` of the way towards the marble, aims at the marble and renders at full size.
  blender -b build/scene.blend --python thumb_render.py     -> build/thumb/hero_top.png, hero_bottom.png
"""
import bpy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings

D = json.load(open(settings.PLAN_JSON))
sc = bpy.context.scene
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = settings.THUMB['samples']
sc.render.use_overwrite = True
sc.render.use_placeholder = False
cam = sc.camera
os.makedirs(settings.THUMBS, exist_ok=True)
for name in ('top', 'bottom'):
    spec = settings.THUMB[name]
    hits = sorted(o['t'] for o in D['obstacles'] if o['k'] == spec['round'] and not o['copy'])
    f = int(round(hits[spec['hit']] * settings.FPS)) + settings.THUMB['after_frames']
    sc.frame_set(f)
    m = bpy.data.objects['Marble'].matrix_world.translation.copy()
    c = cam.matrix_world.translation.copy()
    for fc in cam.animation_data.action.fcurves:
        fc.mute = True
    newc = m + (c - m) * settings.THUMB['zoom']
    cam.location = newc
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (m - newc).normalized().to_track_quat('-Z', 'Y')
    cam.data.shift_y = 0.0
    sc.render.filepath = os.path.join(settings.THUMBS, f'hero_{name}.png')
    bpy.ops.render.render(write_still=True)
    for fc in cam.animation_data.action.fcurves:
        fc.mute = False
    print('hero', name, 'frame', f, flush=True)
