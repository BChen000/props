import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nest_common import *
NAME = 's27'; N = 46
CAM = (0.26, 0.58, 0.56)
sc, F, N_, _ = nest_setup(sun_elev=30, sun_rot=sun_from_cam(CAM, (0, -0.35, 0), 40), chick=False, shells=False)
lin = N_['lining']
C = nest_scene.NEST_C
mw = lin.matrix_world.copy()
for v in lin.data.vertices:
    w = mw @ v.co
    w.x = C.x + (w.x - C.x) * 1.09; w.y = C.y + (w.y - C.y) * 1.09
    v.co = mw.inverted() @ w
lin.data.update()
cam = blib.camera('cam', CAM, (0, -0.36, 0.14), lens=42, fstop=5.6, focus=0.98)
add_fill((0.8, 1.6, 0.9), (0, -0.35, 0.15), power=18)
sc.frame_set(1)
far_objs = drv.far_objects(F)
drv.set_visible(far_objs, False)
blib.render_settings(res=drv.RES, spp=24, transparent=True, bounces=(3, 1, 1, 1, 4), quality='HIGH')
sc.render.filepath = drv.shot_dir(NAME) + 'base.png'
bpy.ops.render.render(write_still=True)
import shutil
shutil.copy(drv.SHOTS + 's06/plate.png', drv.shot_dir(NAME) + 'plate.png')
json.dump({'res': list(drv.RES), 'frames': {}}, open(drv.shot_dir(NAME) + 'meta.json', 'w'))
print('DONE s27')
