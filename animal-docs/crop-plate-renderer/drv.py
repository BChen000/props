"""crop-plate-renderer / drv.py: the render side. Plates, a static base, per-frame foreground (optionally cropped
to the moving subject), camera records and meta.json for comp.py.

Settings (shipped values; environment overrides):
  CPR_SHOTS  folder that gets one sub-folder per shot (default: ./build/shots under the current directory)
  CPR_RES    render size, WxH (default 608x1080; comp.py upscales to 1080x1920)
"""
import bpy, os, sys, json, math, time
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, '..', 'griffin')):  # blib.py lives in ../griffin
    if _p not in sys.path:
        sys.path.insert(0, _p)
import blib

SHOTS = os.path.join(os.environ.get('CPR_SHOTS', os.path.join(os.getcwd(), 'build', 'shots')), '')
RES = tuple(int(x) for x in os.environ.get('CPR_RES', '608x1080').split('x'))


def shot_dir(name):
    d = SHOTS + name + '/'
    os.makedirs(d + 'fg', exist_ok=True)
    return d


def set_visible(objs, vis):
    for o in objs:
        o.hide_render = not vis


def far_objects(F):
    return [o for o in (F.get('terrain'), F.get('clouds')) if o is not None]


def render_plate(name, F, hide, cam=None, spp=24, res=None, lens=None, out='plate.png'):
    """render far scenery only through camera (or given cam) at frame 1."""
    sc = bpy.context.scene
    d = shot_dir(name)
    set_visible(hide, False)
    set_visible(far_objects(F), True)
    old_cam = sc.camera
    if cam is not None:
        sc.camera = cam
    dof_was = sc.camera.data.dof.use_dof
    sc.camera.data.dof.use_dof = False
    res = res or RES
    blib.render_settings(res=res, spp=spp, transparent=False, bounces=(4, 2, 1, 1, 4), quality='HIGH')
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.filepath = d + out
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print('PLATE', name, out, round(time.time() - t, 1), 's')
    sc.camera.data.dof.use_dof = dof_was
    sc.camera = old_cam
    set_visible(hide, True)
    set_visible(far_objects(F), False)
    return d + out


def cam_record(cam):
    cd = cam.data
    return {'mw': [list(r) for r in cam.matrix_world], 'lens': cd.lens, 'sensor': cd.sensor_width}


def obj_screen_bbox(objs, cam, sc, extra_pts=None, margin_px=24):
    dg = bpy.context.evaluated_depsgraph_get()
    W, H = sc.render.resolution_x, sc.render.resolution_y
    xs, ys = [], []
    pts = []
    for o in objs:
        if o.hide_render or o.type not in ('MESH',):
            continue
        ev = o.evaluated_get(dg)
        mw = ev.matrix_world
        for c in ev.bound_box:
            pts.append(mw @ Vector(c))
    if extra_pts:
        pts += extra_pts
    for p in pts:
        v = world_to_camera_view(sc, cam, p)
        if v.z <= 0:
            continue
        xs.append(v.x * W); ys.append(v.y * H)
    if not xs:
        return None
    x0 = max(0, int(min(xs)) - margin_px); x1 = min(W, int(max(xs)) + margin_px)
    y0 = max(0, int(min(ys)) - margin_px); y1 = min(H, int(max(ys)) + margin_px)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return x0, y0, x1, y1


def shadow_pts(objs, to_sun, ground_z):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    ts = Vector(to_sun).normalized()
    if ts.z <= 0.05:
        return pts
    for o in objs:
        if o.hide_render or o.type != 'MESH':
            continue
        ev = o.evaluated_get(dg)
        me = ev.data
        nv = len(me.vertices)
        step = max(1, nv // 400)
        mw = ev.matrix_world
        for i in range(0, nv, step):
            p = mw @ me.vertices[i].co
            t = (p.z - ground_z) / ts.z
            pts.append(p - ts * t)
    return pts


def render_frames(name, f0, f1, spp=4, dynamic=None, static=None, crop=False, to_sun=None, ground_z=0.0,
                  base_spp=16, margin_px=30, step=1, quality='FAST', bounces=(3, 1, 1, 1, 4), only=None, motion_blur=None):
    """renders frames f0..f1 inclusive (every `step`th, or exactly `only`). Writes fg/%04d.png and meta.json.
    crop: render only the screen box around `dynamic` (+ its shadow toward `to_sun` on `ground_z`), over a
    static base.png when `static` is given; boxes grow and re-render when they cut the subject.
    motion_blur: None follows 'mblur' on the command line (shutter 0.35)."""
    sc = bpy.context.scene
    d = shot_dir(name)
    cam = sc.camera
    meta = {'res': list(RES), 'frames': {}, 'crop': crop}
    if crop and static is not None:
        # base: static scene without dynamic objects
        set_visible(dynamic, False)
        blib.render_settings(res=RES, spp=base_spp, transparent=True, bounces=bounces, quality='HIGH')
        sc.frame_set(f0)
        sc.render.use_border = False
        sc.render.filepath = d + 'base.png'
        bpy.ops.render.render(write_still=True)
        set_visible(dynamic, True)
    blib.render_settings(res=RES, spp=spp, transparent=True, bounces=bounces, quality=quality)
    if motion_blur if motion_blur is not None else ('mblur' in sys.argv):
        sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.35
    t_all = time.time()
    frames = list(range(f0, f1 + 1, step))
    if step > 1 and frames[-1] != f1:
        frames.append(f1)
    meta['step'] = step
    if only:
        frames = [f for f in sorted(set(only)) if f0 <= f <= f1]
    base_img = None
    if crop and os.path.exists(d + 'base.png'):
        import cv2
        b = cv2.imread(d + 'base.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
        base_img = b[:, :, :3] * b[:, :, 3:4] + 0.5 * (1 - b[:, :, 3:4])
    for f in frames:
        sc.frame_set(f)
        rec = cam_record(cam)
        if crop:
            extra = shadow_pts(dynamic, to_sun, ground_z) if to_sun is not None else None
            bb = obj_screen_bbox(dynamic, cam, sc, extra_pts=extra, margin_px=margin_px)
            if bb is None:
                meta['frames'][str(f)] = dict(cam=rec, bbox=None)
                continue
            x0, y0, x1, y1 = bb
            t = time.time()
            for attempt in range(4):
                sc.render.use_border = True
                sc.render.use_crop_to_border = True
                sc.render.border_min_x = x0 / RES[0]; sc.render.border_max_x = x1 / RES[0]
                sc.render.border_min_y = y0 / RES[1]; sc.render.border_max_y = y1 / RES[1]
                sc.render.filepath = d + 'fg/%04d.png' % f
                bpy.ops.render.render(write_still=True)
                import cv2
                im = cv2.imread(d + 'fg/%04d.png' % f, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
                if base_img is None:
                    grow = {}
                    if im.shape[2] == 4:
                        a_ = im[:, :, 3]
                        if x0 > 0 and a_[:, 0].max() > 0.15: grow['l'] = True
                        if x1 < RES[0] and a_[:, -1].max() > 0.15: grow['r'] = True
                        if RES[1] - y1 > 0 and a_[0, :].max() > 0.15: grow['t'] = True
                        if y0 > 0 and a_[-1, :].max() > 0.15: grow['b'] = True
                    if not grow or attempt == 3:
                        break
                    gx = max(40, int((x1 - x0) * 0.25)); gy = max(40, int((y1 - y0) * 0.25))
                    if 'l' in grow: x0 = max(0, x0 - gx)
                    if 'r' in grow: x1 = min(RES[0], x1 + gx)
                    if 't' in grow: y1 = min(RES[1], y1 + gy)
                    if 'b' in grow: y0 = max(0, y0 - gy)
                    print('AGROW', name, f, sorted(grow), flush=True)
                    continue
                ty0, ty1 = RES[1] - y1, RES[1] - y0
                hh, ww = min(im.shape[0], ty1 - ty0), min(im.shape[1], x1 - x0)
                cimg = im[:hh, :ww, :3] * im[:hh, :ww, 3:4] + 0.5 * (1 - im[:hh, :ww, 3:4])
                bimg = base_img[ty0:ty0 + hh, x0:x0 + ww]
                D = cv2.GaussianBlur(np.abs(cimg - bimg).mean(axis=2), (0, 0), 3)
                grow = {}
                s_ = 7
                if x0 > 0 and np.percentile(D[:, :s_], 98) > 0.03: grow['l'] = True
                if x1 < RES[0] and np.percentile(D[:, -s_:], 98) > 0.03: grow['r'] = True
                if ty0 > 0 and np.percentile(D[:s_, :], 98) > 0.03: grow['t'] = True
                if ty1 < RES[1] and np.percentile(D[-s_:, :], 98) > 0.03: grow['b'] = True
                if not grow or attempt == 3:
                    break
                gx = max(60, int((x1 - x0) * 0.3)); gy = max(60, int((y1 - y0) * 0.3))
                if 'l' in grow: x0 = max(0, x0 - gx)
                if 'r' in grow: x1 = min(RES[0], x1 + gx)
                if 't' in grow: y1 = min(RES[1], y1 + gy)
                if 'b' in grow: y0 = max(0, y0 - gy)
                print('GROW', name, f, sorted(grow), flush=True)
            rec_bb = [x0, RES[1] - y1, x1, RES[1] - y0]
        else:
            sc.render.use_border = False
            rec_bb = None
            sc.render.filepath = d + 'fg/%04d.png' % f
            t = time.time()
            bpy.ops.render.render(write_still=True)
        meta['frames'][str(f)] = dict(cam=rec, bbox=rec_bb, t=round(time.time() - t, 2))
        print('FRAME', name, f, round(time.time() - t, 2), flush=True)
    sc.render.use_border = False
    old = {}
    if os.path.exists(d + 'meta.json') and only:
        old = json.load(open(d + 'meta.json'))
        old['frames'].update(meta['frames'])
        meta = old
    json.dump(meta, open(d + 'meta.json', 'w'))
    print('DONE', name, len(frames), 'frames', round(time.time() - t_all, 1), 's', flush=True)


def save_plate_cam(name, cam, fname='plate_cam.json'):
    json.dump(cam_record(cam), open(shot_dir(name) + fname, 'w'))
