import sys, time
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import settings as C
import bpy, OpenEXR
import glass_scene as G
spp = int(sys.argv[-1])
sc = G.reset()
studio, mats, panes, ball, cam = G.build()
for o in panes + [ball]:
    o.hide_render = True
G.setup_cycles(sc, 1080, 1920, spp=spp)
sc.cycles.adaptive_threshold = 0.008
sc.render.film_transparent = False
sc.render.dither_intensity = 0.0
sc.render.image_settings.file_format = 'OPEN_EXR'
sc.render.image_settings.color_depth = '32'
sc.render.image_settings.color_mode = 'RGB'
__import__('os').makedirs(C.PLATES, exist_ok=True)
sc.render.filepath = C.PLATES + '/base.exr'
t = time.time(); bpy.ops.render.render(write_still=True); print("base T", time.time() - t, flush=True)
with OpenEXR.File(C.PLATES + '/base.exr') as f:
    ch = f.channels()
    k = 'RGB' if 'RGB' in ch else 'RGBA'
    x = np.array(ch[k].pixels, np.float32)[..., :3]
np.save(C.PLATES + '/base.npy', x)
print('saved', x.shape, x.min(), x.max())
