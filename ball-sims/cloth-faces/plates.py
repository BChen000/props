"""Static plates (no hero, no cloth): base = floor + sky; stack = base + stack with sheets 0..s removed.
Run:  python3 plates.py -- base 256      then      python3 plates.py -- stack 96 0,1,2,3,4,5"""
import sys, time, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, OpenEXR
import scene as S

P = S.CFG.PLATES
os.makedirs(P, exist_ok=True)
W, H = 1080, 1920


def read_exr(path, key=None):
    with OpenEXR.File(path) as f:
        ch = f.channels()
        if key is None:
            k = 'RGBA' if 'RGBA' in ch else 'RGB'
            return ch[k].pixels.astype(np.float32), list(ch.keys())
        return ch[key].pixels.astype(np.float32), list(ch.keys())


def exr_settings(sc, rgba=True):
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.image_settings.color_mode = 'RGBA' if rgba else 'RGB'
    sc.render.image_settings.exr_codec = 'ZIP'


def base(spp):
    sc = S.reset()
    plat, shaft, hero = S.build_set()
    for o in list(bpy.data.objects):
        if o.name.startswith(('Vane', 'Hero')) or o.name == 'Marble':
            bpy.data.objects.remove(o)
    plat['bgmix'] = 0.0
    shaft['bgmix'] = 0.0
    S.add_camera(); S.add_lights()
    S.setup_cycles(sc, W, H, spp=spp)
    sc.cycles.adaptive_threshold = 0.01
    sc.render.film_transparent = True
    exr_settings(sc)
    sc.render.filepath = f'{P}/floor.exr'
    t = time.time(); bpy.ops.render.render(write_still=True); print("base T", time.time() - t, flush=True)
    rgba, _ = read_exr(f'{P}/floor.exr')
    sky = np.load(f'{P}/sky_lin.npy')
    a = rgba[..., 3:4]
    out = rgba[..., :3] + (1 - a) * sky
    np.save(f'{P}/base.npy', out.astype(np.float32))
    np.save(f'{P}/floor_mask.npy', a[..., 0].astype(np.float32))


def stacks(spp, which):
    sc = S.reset()
    plat, shaft, hero = S.build_set()
    for o in list(bpy.data.objects):
        if o.name.startswith(('Vane', 'Hero')) or o.name == 'Marble':
            bpy.data.objects.remove(o)
    plat['bgmix'] = 1.0
    shaft['bgmix'] = 1.0
    S.add_camera(); S.add_lights()
    base_img = np.load(f'{P}/base.npy')
    img = S.bg_image("BG", W, H)
    S.set_bg_pixels(img, base_img)
    for ob in (plat, shaft):
        for m in ob.data.materials:
            S.wrap_with_bg(m.node_tree)
    S.wrap_with_bg(sc.world.node_tree, True)
    mats = S.stage_materials()
    st = S.build_stack(mats)
    S.setup_cycles(sc, W, H, spp=spp)
    sc.render.film_transparent = False
    exr_settings(sc, rgba=False)
    for s in which:
        for i, ob in enumerate(st):
            ob.hide_render = not (i > s)
        sc.render.filepath = f'{P}/stack{s}.exr'
        t = time.time(); bpy.ops.render.render(write_still=True); print("stack", s, "T", time.time() - t, flush=True)
        rgb, _ = read_exr(sc.render.filepath)
        np.save(f'{P}/plate{s}.npy', rgb[..., :3].astype(np.float32))


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    if args[0] == 'base':
        base(int(args[1]))
    else:
        stacks(int(args[1]), [int(x) for x in args[2].split(',')])
