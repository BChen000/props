"""Renders preview.png of the empty set from xylophone-ramp.blend (Cycles, CPU).

Run:  python3 render_preview.py            (bpy module)
  or: blender --background --python render_preview.py
Uses the same exposure and tone curve as the finished videos (see marble-plate-compositor).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))

# ======================================================================= SETTINGS
SCALE_PERCENT = 50          # 50 -> 540x960
SAMPLES = 64
EXPOSURE = 1.1
BLEND = os.path.join(HERE, 'xylophone-ramp.blend')
OUT = os.path.join(HERE, 'preview.png')
# ===================================================================== END SETTINGS

import bpy
import numpy as np
from PIL import Image


def tonemap(x, exposure=1.0):
    x = np.maximum(x * exposure, 0)
    k = 0.8
    y = np.where(x < k, x, k + (1 - k) * np.tanh((x - k) / (1 - k)))
    y = np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(np.maximum(y, 1e-8), 1 / 2.4) - 0.055)
    return np.clip(y * 255 + 0.5, 0, 255).astype(np.uint8)


bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
sc.render.resolution_percentage = SCALE_PERCENT
sc.cycles.samples = SAMPLES
s = sc.render.image_settings
s.file_format = 'OPEN_EXR'
s.color_depth = '32'
s.color_mode = 'RGB'
tmp = os.path.join(HERE, 'build', 'preview_tmp.exr')
os.makedirs(os.path.dirname(tmp), exist_ok=True)
sc.render.filepath = tmp
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(tmp)
w, h = img.size
a = np.empty(w * h * 4, np.float32)
img.pixels.foreach_get(a)
a = a.reshape(h, w, 4)[::-1, :, :3]
Image.fromarray(tonemap(a, EXPOSURE)).save(OUT)
os.remove(tmp)
print('saved', OUT, w, h)
