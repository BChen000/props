import sys, time, os, json, math, argparse, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, OpenEXR
import settings as C
import glass_scene as G
from PIL import Image, ImageFilter
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ap = argparse.ArgumentParser()
ap.add_argument('--start', type=int, default=0)
ap.add_argument('--end', type=int, default=0)
ap.add_argument('--stride', type=int, default=1)
ap.add_argument('--list', default='')
ap.add_argument('--spp', type=int, default=C.SPP)
ap.add_argument('--cspp', type=int, default=C.CATCHER_SPP)
ap.add_argument('--cdiv', type=int, default=C.CATCHER_DIV)
ap.add_argument('--mscale', type=float, default=C.MAIN_SCALE)
ap.add_argument('--threads', type=int, default=0)
ap.add_argument('--out', default=C.FRAMES)
ap.add_argument('--timeline', default=C.TIMELINE)
ap.add_argument('--skip', type=int, default=1)
ap.add_argument('--reuse', type=int, default=1)
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])

P = C.PLATES
TL = json.load(open(a.timeline))
W, H = 1080, 1920
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


sc = G.reset()
sc.render.dither_intensity = 0.0
sc.render.filter_size = 1.0
studio, mats, panes, ball, cam = G.build()
studio['bgmix'] = 1.0
import bgemit as SC
img = SC.bg_image("BG", MW, MH, world=False)
for m in studio.data.materials:
    SC.wrap_with_bg(m.node_tree)
SC.no_emission_sampling()

sims, shards = {}, {}


def load_stage(s):
    if s in sims:
        return
    for k in list(sims.keys()):
        del sims[k]
    for k, sh in list(shards.items()):
        bpy.data.objects.remove(sh.ob)
        del shards[k]
    d = np.load(TL['sims'][s])
    sims[s] = {k: d[k] for k in ('ball_pos', 'ball_quat', 'sh_pos', 'sh_quat', 'intact', 'r')}
    info = json.loads(str(d['shards']))
    shards[s] = G.Shards(info, mats, name=f"Shards{s}")


G.setup_cycles(sc, W, H, spp=a.spp)
sc.render.use_persistent_data = True
if a.threads:
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = a.threads
sc.render.film_transparent = False
sc.view_layers[0].cycles.use_pass_shadow_catcher = True
base = np.load(f'{P}/base.npy')


def frame_info(g):
    acc = 0
    for si, L in enumerate(TL['stage_len']):
        if g < acc + L:
            return si, g - acc
        acc += L
    return len(TL['stage_len']) - 1, TL['stage_len'][-1] - 1


def lerp_quat(q0, q1, w):
    q1 = np.where((np.sum(q0 * q1, -1, keepdims=True) < 0), -q1, q1)
    q = q0 * (1 - w) + q1 * w
    return q / np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1e-9)


def state(s, f):
    d = sims[s]
    kf = min(TL['maps'][s][f], len(d['ball_pos']) - 1)
    k0 = int(math.floor(kf)); k1 = min(k0 + 1, len(d['ball_pos']) - 1); w = kf - k0
    bp = d['ball_pos'][k0] * (1 - w) + d['ball_pos'][k1] * w
    bq = lerp_quat(d['ball_quat'][k0], d['ball_quat'][k1], w)
    sp0, sp1 = d['sh_pos'][k0], d['sh_pos'][k1]
    sp = np.where(np.isnan(sp1) | np.isnan(sp0), sp0 if w < 0.5 else sp1, sp0 * (1 - w) + sp1 * w)
    sq = lerp_quat(d['sh_quat'][k0], d['sh_quat'][k1], w)
    intact = d['intact'][k0 if w < 0.5 else k1]
    return bp, bq, sp, sq, intact, (k0 if w < 0.5 else k1)


def apply_state(s, f):
    bp, bq, sp, sq, intact, kk = state(s, f)
    r = float(sims[s]['r'])
    ball.scale = (r, r, r)
    ball.location = tuple(bp)
    ball.rotation_mode = 'QUATERNION'
    ball.rotation_quaternion = (bq[3], bq[0], bq[1], bq[2])
    for k in range(C.N_P):
        panes[k].hide_render = not bool(intact[k])
    shards[s].pose(sp, sq, kk)
    return bp, sp, intact, kk, r


def read_catcher(path):
    with OpenEXR.File(path, separate_channels=True) as fexr:
        for prt in fexr.parts:
            if prt.name().endswith('.Shadow Catcher'):
                ch = prt.channels
                pre = prt.name()
                return np.stack([np.array(ch[f'{pre}.{c}'].pixels, dtype=np.float32) for c in 'RGB'], -1)
    raise RuntimeError('no catcher pass')


dyn = lambda: [ball, shards[cur_stage].ob] + panes


def set_mode(catcher):
    studio.is_shadow_catcher = catcher
    studio['bgmix'] = 0.0 if catcher else 1.0
    for ob in dyn():
        ob.visible_camera = not catcher
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


def proj_box(pts):
    xs, ys = [], []
    for p_ in pts:
        v = world_to_camera_view(sc, cam, Vector(p_))
        xs.append(v.x); ys.append(v.y)
    return min(xs), max(xs), min(ys), max(ys)


def region(bp, sp, intact, kk, r):
    pts = []
    for dx in (-r, r):
        for dy in (-r, r):
            for dz in (-r, r):
                pts.append((bp[0] + dx, bp[1] + dy, bp[2] + dz))
    for k in range(C.N_P):
        if intact[k]:
            z = C.pane_z(k)
            for x in (-C.HALF, C.HALF):
                for y in (-C.HALF, C.HALF):
                    for dz in (-C.T, C.T):
                        pts.append((x, y, z + dz))
    vis = shards[cur_stage].spawn <= kk
    if vis.any():
        q = sp[vis]
        q = q[~np.isnan(q[:, 0])]
        if len(q):
            lo, hi = q.min(0) - 0.06, q.max(0) + 0.06
            for x in (lo[0], hi[0]):
                for y in (lo[1], hi[1]):
                    for z in (lo[2], hi[2]):
                        pts.append((x, y, z))
    x0, x1, y0, y1 = proj_box(pts)
    m = 0.025
    return max(0, x0 - m), min(1, x1 + m), max(0, y0 - m * 0.6), min(1, y1 + m * 0.6)


def to_srgb8(lin):
    x = np.clip(lin, 0, 1)
    s_ = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return np.clip(s_ * 255 + 0.5, 0, 255).astype(np.uint8)


frames = list(range(a.start, a.end, a.stride)) if not a.list else [int(x) for x in a.list.split(',')]
prev_sig = None
cur_stage = None
for g in frames:
    outp = f'{a.out}/f_{g:04d}.png'
    if a.skip and os.path.exists(outp) and not a.list:
        prev_sig = None
        continue
    t0 = time.time()
    s, f = frame_info(g)
    if s != cur_stage:
        load_stage(s)
        cur_stage = s
        prev_sig = None
    bp, sp, intact, kk, r = apply_state(s, f)
    sig = np.concatenate([np.asarray(bp, np.float32), np.nan_to_num(sp, nan=-50).ravel(), np.asarray(intact, np.float32)])
    if a.reuse and prev_sig is not None and prev_sig[0] == s and len(prev_sig[1]) == len(sig) and np.abs(prev_sig[1] - sig).max() < 1e-3 and os.path.exists(prev_sig[2]):
        shutil.copyfile(prev_sig[2], outp)
        print(f"frame {g} stage {s} local {f}: reused", flush=True)
        continue
    set_mode(True)
    cpath = f'/tmp/gcatch_{os.getpid()}.exr'
    sc.render.filepath = cpath
    bpy.ops.render.render(write_still=True)
    t1 = time.time()
    M = np.clip(read_catcher(cpath), 0, 1.6)
    bg = base * rs(M, W, H, Image.BICUBIC)
    bg_low = rs(bg, MW, MH, Image.BOX)
    SC.set_bg_pixels(img, bg_low)
    set_mode(False)
    x0, x1, y0, y1 = region(bp, sp, intact, kk, r)
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_max_x = x0, x1
    sc.render.border_min_y, sc.render.border_max_y = y0, y1
    rpath = f'/tmp/gmain_{os.getpid()}.png'
    sc.render.filepath = rpath
    bpy.ops.render.render(write_still=True)
    t2 = time.time()
    out = to_srgb8(bg)
    rim = np.asarray(Image.open(rpath).convert('RGBA'))
    lx0 = int(math.floor(x0 * MW / SNAP)) * SNAP
    lx1 = min(MW, int(math.ceil(x1 * MW / SNAP)) * SNAP)
    ly0 = int(math.floor((1 - y1) * MH / SNAP)) * SNAP
    ly1 = min(MH, int(math.ceil((1 - y0) * MH / SNAP)) * SNAP)
    R = rim[ly0:ly1, lx0:lx1, :3]
    A = np.asarray(Image.fromarray(((rim[ly0:ly1, lx0:lx1, 3] == 255) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(7)), np.float32) / 255.0
    B = to_srgb8(bg_low[ly0:ly1, lx0:lx1])
    D = np.abs(R.astype(np.int16) - B.astype(np.int16)).max(-1).astype(np.float32)
    mk = np.clip((D - 2.0) / 5.0, 0, 1) * A
    mi = Image.fromarray((mk * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    fx0, fx1 = int(round(lx0 / a.mscale)), int(round(lx1 / a.mscale))
    fy0, fy1 = int(round(ly0 / a.mscale)), int(round(ly1 / a.mscale))
    fw, fh = fx1 - fx0, fy1 - fy0
    Rup = np.asarray(Image.fromarray(R).resize((fw, fh), Image.LANCZOS), np.float32)
    mup = (np.asarray(mi.resize((fw, fh), Image.BILINEAR), np.float32) / 255.0)[..., None]
    base_reg = out[fy0:fy1, fx0:fx1].astype(np.float32)
    out[fy0:fy1, fx0:fx1] = np.clip(Rup * mup + base_reg * (1 - mup) + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(outp)
    prev_sig = (s, sig, outp)
    print(f"frame {g} stage {s} local {f}: catcher {t1 - t0:.1f}s main {t2 - t1:.1f}s total {time.time() - t0:.1f}s region {x1 - x0:.2f}x{y1 - y0:.2f}", flush=True)
