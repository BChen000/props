"""Renders video frames to build/frames/f_NNNN.png (two passes per frame: low-res shadow catcher, then a region render).
Run:  python3 render_frames.py -- --start 0 --end 588 [--stride 2 --threads 1]    or    -- --list 24,405"""
import sys, time, os, json, math, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as CFG
import bpy, OpenEXR
import scene as S
from PIL import Image, ImageFilter
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ap = argparse.ArgumentParser()
ap.add_argument('--start', type=int, default=0)
ap.add_argument('--end', type=int, default=0)
ap.add_argument('--list', default='')
ap.add_argument('--spp', type=int, default=CFG.SPP)
ap.add_argument('--cspp', type=int, default=CFG.CATCHER_SPP)
ap.add_argument('--scale', type=float, default=1.0)
ap.add_argument('--cdiv', type=int, default=CFG.CATCHER_DIV)
ap.add_argument('--out', default=CFG.FRAMES)
ap.add_argument('--timeline', default=CFG.TIMELINE)
ap.add_argument('--keep', type=int, default=0)
ap.add_argument('--skip', type=int, default=1)
ap.add_argument('--mscale', type=float, default=CFG.MAIN_SCALE)
ap.add_argument('--threads', type=int, default=0)
ap.add_argument('--stride', type=int, default=1)
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])

P = CFG.PLATES
TL = json.load(open(a.timeline))
W, H = int(round(1080 * a.scale)), int(round(1920 * a.scale))
CW, CH = W // a.cdiv, H // a.cdiv
MW, MH = int(round(W * a.mscale)), int(round(H * a.mscale))
SNAP = 4 if abs(a.mscale - 0.8) < 1e-6 else 1
os.makedirs(a.out, exist_ok=True)


def rs(x, w, h, mode=Image.BILINEAR):
    if x.shape[0] == h and x.shape[1] == w:
        return x
    if x.ndim == 2:
        return np.asarray(Image.fromarray(x.astype(np.float32)).resize((w, h), mode), np.float32)
    return np.stack([np.asarray(Image.fromarray(x[..., c].astype(np.float32)).resize((w, h), mode), np.float32) for c in range(x.shape[2])], -1)


sc = S.reset()
sc.render.dither_intensity = 0.0
sc.render.filter_size = 1.0
plat, shaft, hero = S.build_set()
mb = hero[0]
vanes = [o for o in bpy.data.objects if o.name.startswith('Vane')] + hero[1:]
cam = S.add_camera()
S.add_lights()
img = S.bg_image("BG", MW, MH, world=False)
wimg = S.bg_image("BGW", MW, MH, world=True)
for ob in (plat, shaft):
    ob['bgmix'] = 1.0
    ob['cheap'] = 0.0
    for m in ob.data.materials:
        S.wrap_with_bg(m.node_tree)
S.wrap_with_bg(sc.world.node_tree, True)
mats = S.stage_materials()
stack = S.build_stack(mats)
for ob in stack:
    ob['bgmix'] = 1.0
    for m in ob.data.materials:
        S.wrap_with_bg(m.node_tree)

stage_mats = S.stage_materials()
sims, cloths = {}, {}
for si, st in enumerate(S.STAGES):
    if os.path.exists(TL['sims'][si]):
        d = np.load(TL['sims'][si])
        pos0, faces, uvs = d['pos'], d['faces'], d['uv']
    else:
        v, faces, uvs = S.grid(min(st['n'], 8))
        pos0 = v[None].astype(np.float32)
    sims[si] = pos0
    ob = S.mesh_obj(f'Cloth{si}', pos0[0], faces, smooth=st['n'] >= 64)
    S.set_uv(ob.data, uvs)
    ob.data.materials.append(stage_mats[si])
    if st.get('subdiv'):
        md = ob.modifiers.new('Sub', 'SUBSURF')
        md.levels = 0
        md.render_levels = st['subdiv']
        md.quality = 1
    ob.hide_render = True
    cloths[si] = ob

refill = []
for i, st in enumerate(S.STAGES):
    ob = S.sheet_object(f'Refill{i}', max(1, min(st['n'], 16)), stage_mats[i], z=0.0)
    ob.visible_shadow = False
    ob.hide_render = True
    refill.append(ob)

S.no_emission_sampling()
S.setup_cycles(sc, W, H, spp=a.spp)
try:
    sc.cycles.denoising_prefilter = 'FAST'
    sc.cycles.denoising_quality = 'BALANCED'
except Exception as ex:
    print('denoise opts', ex)
sc.render.use_persistent_data = True
if a.threads:
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = a.threads
sc.render.film_transparent = False
sc.view_layers[0].cycles.use_pass_shadow_catcher = True

mask = rs(np.load(f'{P}/floor_mask.npy'), W, H)
plate_cache = {}


def plate(s):
    if s not in plate_cache:
        p = f'{P}/plate{s}.npy'
        x = np.load(p) if (os.path.exists(p) and s < 6) else np.load(f'{P}/base.npy')
        plate_cache.clear()
        plate_cache[s] = rs(x, W, H)
        S.set_bg_pixels(wimg, rs(plate_cache[s], MW, MH, Image.BOX))
    return plate_cache[s]


def frame_info(g):
    acc = 0
    for si, L in enumerate(TL['stage_len']):
        if g < acc + L:
            return si, g - acc
        acc += L
    return 7, g - acc


def read_catcher(path):
    with OpenEXR.File(path, separate_channels=True) as f:
        for p in f.parts:
            if p.name().endswith('.Shadow Catcher'):
                ch = p.channels
                pre = p.name()
                return np.stack([np.array(ch[f'{pre}.{c}'].pixels, dtype=np.float32) for c in 'RGB'], -1)
    raise RuntimeError('no catcher pass')


def set_mode(catcher, s):
    for ob in (plat, shaft):
        ob.is_shadow_catcher = catcher
        ob['bgmix'] = 0.0 if catcher else 1.0
        ob['cheap'] = 1.0 if catcher else 0.0
    for ob in [mb] + vanes + list(cloths.values()) + refill:
        ob.visible_camera = not catcher
    for i, ob in enumerate(stack):
        ob.hide_render = catcher or not (s < 7 and i > s)
    c6 = cloths[6]
    if 'Sub' in c6.modifiers:
        c6.modifiers['Sub'].show_render = not catcher
    sc.cycles.diffuse_bounces = 0 if catcher else 2
    if catcher:
        sc.render.use_border = False
        sc.render.resolution_x, sc.render.resolution_y = CW, CH
        sc.cycles.samples = a.cspp
        sc.render.image_settings.media_type = 'MULTI_LAYER_IMAGE'
        sc.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
        sc.render.image_settings.color_depth = '16'
    else:
        sc.render.resolution_x, sc.render.resolution_y = MW, MH
        sc.cycles.samples = a.spp
        sc.render.image_settings.media_type = 'IMAGE'
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGBA'
        sc.render.image_settings.color_depth = '8'


def refill_pose(f):
    n = len(S.STAGES)
    T = TL['refill_len']
    stg = TL.get('refill_stagger', 1.5)
    for i, ob in enumerate(refill):
        delay = i * stg
        u = np.clip((f + 1 - delay) / max(1.0, T - (n - 1) * stg), 0, 1)
        e = 1 - (1 - u) ** 3
        z_end = S.STACK_Z0 + S.STACK_GAP * i
        ob.location = (0, 0, z_end + (1 - e) * 3.0)
        ob.hide_render = bool(u <= 0)


def proj_bbox(points):
    xs, ys = [], []
    for p in points:
        v = world_to_camera_view(sc, cam, Vector(p))
        xs.append(v.x); ys.append(v.y)
    return min(xs), max(xs), min(ys), max(ys)


def region(s, f):
    m = 0.03
    def pad(b):
        x0, x1, y0, y1 = b
        return (max(0, x0 - m), min(1, x1 + m), max(0, y0 - m * 0.6), min(1, y1 + m * 0.6))
    mpts = []
    for o in hero:
        for c in o.bound_box:
            mpts.append(tuple(o.matrix_world @ Vector(c)))
    mbox = pad(proj_bbox(mpts))
    cpts = []
    if s < 7:
        me = cloths[s].data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0)
        for x in (lo[0], hi[0]):
            for y in (lo[1], hi[1]):
                for z in (max(lo[2], -3.0), hi[2]):
                    cpts.append((x, y, z))
    else:
        h = S.SHEET / 2
        for ob in refill:
            if not ob.hide_render:
                for x in (-h, h):
                    for y in (-h, h):
                        cpts.append((x, y, ob.location.z))
    if not cpts:
        return [mbox]
    cbox = pad(proj_bbox(cpts))
    ubox = (min(mbox[0], cbox[0]), max(mbox[1], cbox[1]), min(mbox[2], cbox[2]), max(mbox[3], cbox[3]))
    area = lambda b: max(0, b[1] - b[0]) * max(0, b[3] - b[2])
    ov = (max(mbox[0], cbox[0]), min(mbox[1], cbox[1]), max(mbox[2], cbox[2]), min(mbox[3], cbox[3]))
    if cbox[1] - cbox[0] < 0.02 or cbox[3] - cbox[2] < 0.02:
        return [mbox]
    if area(ov) == 0 and area(ubox) > 1.3 * (area(mbox) + area(cbox)):
        return [cbox, mbox]
    return [ubox]


def to_srgb8(lin):
    x = np.clip(lin, 0, 1)
    s = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return np.clip(s * 255 + 0.5, 0, 255).astype(np.uint8)


frames = list(range(a.start, a.end, a.stride)) if not a.list else [int(x) for x in a.list.split(',')]
for g in frames:
    outp = f'{a.out}/f_{g:04d}.png'
    if a.skip and os.path.exists(outp) and not a.list:
        continue
    t0 = time.time()
    s, f = frame_info(g)
    for ob in cloths.values():
        ob.hide_render = True
    for ob in refill:
        ob.hide_render = True
    if s < 7:
        ob = cloths[s]
        kf = min(TL['maps'][s][f], len(sims[s]) - 1)
        k0 = int(math.floor(kf)); k1 = min(k0 + 1, len(sims[s]) - 1); w = kf - k0
        co = sims[s][k0] * (1 - w) + sims[s][k1] * w if w > 1e-6 else sims[s][k0]
        ob.data.vertices.foreach_set('co', co.astype(np.float32).ravel())
        ob.data.update()
        ob.hide_render = False
    else:
        refill_pose(f)
    pl = plate(min(s, 6))
    set_mode(True, s)
    cpath = f'/tmp/catch_{os.getpid()}.exr'
    sc.render.filepath = cpath
    bpy.ops.render.render(write_still=True)
    t1 = time.time()
    M = np.clip(read_catcher(cpath), 0, 1.5)
    Mu = rs(M, W, H, Image.BICUBIC)
    Mu = 1.0 + mask[..., None] * (Mu - 1.0)
    bg = pl * Mu
    bg_low = rs(bg, MW, MH, Image.BOX)
    S.set_bg_pixels(img, bg_low)
    t2 = time.time()
    set_mode(False, s)
    if s >= 7:
        refill_pose(f)
    boxes = region(s, f)
    out = to_srgb8(bg)
    for bi, (x0, x1, y0, y1) in enumerate(boxes):
        sc.render.use_border = True
        sc.render.use_crop_to_border = False
        sc.render.border_min_x, sc.render.border_max_x = x0, x1
        sc.render.border_min_y, sc.render.border_max_y = y0, y1
        rpath = f'/tmp/main_{os.getpid()}_{bi}.png'
        sc.render.filepath = rpath
        bpy.ops.render.render(write_still=True)
        rim = np.asarray(Image.open(rpath).convert('RGBA'))
        lx0 = int(math.floor(x0 * MW / SNAP)) * SNAP
        lx1 = min(MW, int(math.ceil(x1 * MW / SNAP)) * SNAP)
        ly0 = int(math.floor((1 - y1) * MH / SNAP)) * SNAP
        ly1 = min(MH, int(math.ceil((1 - y0) * MH / SNAP)) * SNAP)
        R = rim[ly0:ly1, lx0:lx1, :3]
        A = np.asarray(Image.fromarray(((rim[ly0:ly1, lx0:lx1, 3] == 255) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(7)), np.float32) / 255.0
        B = to_srgb8(bg_low[ly0:ly1, lx0:lx1])
        D = np.abs(R.astype(np.int16) - B.astype(np.int16)).max(-1).astype(np.float32)
        m = np.clip((D - 2.0) / 5.0, 0, 1) * A
        mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
        fx0, fx1 = int(round(lx0 / a.mscale)), int(round(lx1 / a.mscale))
        fy0, fy1 = int(round(ly0 / a.mscale)), int(round(ly1 / a.mscale))
        fw, fh = fx1 - fx0, fy1 - fy0
        Rup = np.asarray(Image.fromarray(R).resize((fw, fh), Image.LANCZOS), np.float32)
        mup = (np.asarray(mi.resize((fw, fh), Image.BILINEAR), np.float32) / 255.0)[..., None]
        base_reg = out[fy0:fy1, fx0:fx1].astype(np.float32)
        out[fy0:fy1, fx0:fx1] = np.clip(Rup * mup + base_reg * (1 - mup) + 0.5, 0, 255).astype(np.uint8)
    t3 = time.time()
    x0, x1, y0, y1 = boxes[0]
    Image.fromarray(out).save(outp)
    if a.keep:
        np.save(f'{a.out}/M_{g:04d}.npy', M)
    print(f"frame {g} stage {s} local {f}: catcher {t1 - t0:.1f}s bg {t2 - t1:.1f}s main {t3 - t2:.1f}s total {time.time() - t0:.1f}s boxes {len(boxes)} region {x1-x0:.2f}x{y1-y0:.2f}", flush=True)
