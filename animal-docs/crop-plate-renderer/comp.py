"""crop-plate-renderer / comp.py: the composite side. For each frame: the plate (warped by a homography when the
camera turned), the static base, the cropped foreground with feathered edges; optical-flow in-betweens for frames
rendered every 2nd; then zoom/pan, sharpen, grade, grain and fades, piped to ffmpeg (libx264 CRF 17).

Settings (shipped values; environment overrides):
  CPR_SHOTS   the same shots folder as drv.py (default ./build/shots)
  CPR_OUT     output size WxH (default 1080x1920)
"""
import numpy as np, cv2, json, os, sys, subprocess

SHOTS = os.path.join(os.environ.get('CPR_SHOTS', os.path.join(os.getcwd(), 'build', 'shots')), '')
OUT_W, OUT_H = (int(x) for x in os.environ.get('CPR_OUT', '1080x1920').split('x'))


def load_rgba(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    if im.shape[2] == 3:
        a = np.ones(im.shape[:2] + (1,), np.float32)
        return np.concatenate([im[:, :, ::-1].astype(np.float32) / 255.0, a], 2)
    rgb = im[:, :, 2::-1].astype(np.float32) / 255.0
    a = im[:, :, 3:4].astype(np.float32) / 255.0
    return np.concatenate([rgb, a], 2)


def cam_A(rec, W, H):
    f = rec['lens'] / rec['sensor'] * W
    return np.array([[f, 0, W / 2.0], [0, -f, H / 2.0], [0, 0, 1.0]])


def homography(rec_plate, rec_f, Wp, Hp, W, H):
    Rp = np.array(rec_plate['mw'])[:3, :3]
    Rf = np.array(rec_f['mw'])[:3, :3]
    D = np.diag([1.0, 1.0, -1.0])
    Ap = cam_A(rec_plate, Wp, Hp)
    Af = cam_A(rec_f, W, H)
    return Ap @ D @ Rp.T @ Rf @ D @ np.linalg.inv(Af)


def over(dst, src):
    a = src[:, :, 3:4]
    dst[:, :, :3] = src[:, :, :3] * a + dst[:, :, :3] * (1 - a)
    return dst


def grade(img, warmth=0.0, contrast=1.04, sat=1.05, vignette=0.22, lift=0.0):
    x = img
    if warmth:
        x = x * np.array([1 + warmth, 1 + warmth * 0.35, 1 - warmth * 0.6], np.float32)
    m = x.mean(axis=2, keepdims=True)
    x = m + (x - m) * sat
    x = (x - 0.5) * contrast + 0.5 + lift
    h, w = x.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.55 + ((yy - h / 2) / (h / 2)) ** 2 * 0.45)
    x = x * (1 - vignette * np.clip(r - 0.35, 0, 1) ** 1.5)[:, :, None]
    return np.clip(x, 0, 1)


_dis = None


def interp(A, B, t):
    global _dis
    if _dis is None:
        _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ga = cv2.cvtColor((np.clip(A, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor((np.clip(B, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    F = _dis.calc(ga, gb, None)
    h, w = ga.shape
    xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    ax = xx - t * F[:, :, 0]; ay = yy - t * F[:, :, 1]
    bx = xx + (1 - t) * F[:, :, 0]; by = yy + (1 - t) * F[:, :, 1]
    wa = cv2.remap(A.astype(np.float32), ax, ay, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wb = cv2.remap(B.astype(np.float32), bx, by, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return wa * (1 - t) + wb * t


class ShotData:
    def __init__(self, name, bg_blur=0.0, plate_name='plate.png', plate_cam='plate_cam.json', fg_dir='fg'):
        d = SHOTS + name + '/'
        self.d = d
        self.meta = json.load(open(d + 'meta.json')) if os.path.exists(d + 'meta.json') else {'frames': {}, 'res': [720, 1280]}
        self.W, self.H = self.meta['res']
        self.plate = load_rgba(d + plate_name) if os.path.exists(d + plate_name) else None
        self.pcam = json.load(open(d + plate_cam)) if os.path.exists(d + plate_cam) else None
        if self.plate is not None and bg_blur > 0:
            self.plate[:, :, :3] = cv2.GaussianBlur(self.plate[:, :, :3], (0, 0), bg_blur)
        self.base = load_rgba(d + 'base.png') if os.path.exists(d + 'base.png') else None
        self.fg_dir = fg_dir


def make_frame(S, f, extra_layers=None):
    W, H = S.W, S.H
    rec = S.meta['frames'].get(str(f))
    img = np.zeros((H, W, 4), np.float32); img[:, :, 3] = 1
    plate, pcam = S.plate, S.pcam
    if plate is not None:
        if pcam is not None and rec is not None and pcam != rec['cam']:
            Hm = homography(pcam, rec['cam'], plate.shape[1], plate.shape[0], W, H)
            bg = cv2.warpPerspective(plate, Hm, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        else:
            bg = plate if plate.shape[:2] == (H, W) else cv2.resize(plate, (W, H), interpolation=cv2.INTER_AREA)
        img[:, :, :3] = bg[:, :, :3]
    bgimg = img[:, :, :3].copy()
    if S.base is not None:
        img = over(img, S.base)
    fp = S.d + S.fg_dir + '/%04d.png' % f
    if os.path.exists(fp) and rec is not None:
        fg = load_rgba(fp)
        if rec.get('bbox'):
            x0, y0, x1, y1 = rec['bbox']
            fg = fg[:y1 - y0, :x1 - x0]
            hh, ww = fg.shape[:2]
            x1, y1 = x0 + ww, y0 + hh
            m = np.ones((hh, ww), np.float32)
            fe = 22
            ramp = np.clip(np.arange(max(hh, ww)) / fe, 0, 1)
            if x0 > 0: m *= ramp[None, :ww]
            if x1 < W: m *= ramp[None, :ww][:, ::-1]
            if y0 > 0: m *= ramp[:hh, None]
            if y1 < H: m *= ramp[:hh, None][::-1, :]
            region = np.zeros((hh, ww, 4), np.float32)
            region[:, :, :3] = bgimg[y0:y1, x0:x1]
            region[:, :, 3] = 1
            region = over(region, fg)
            sub = img[y0:y1, x0:x1, :3]
            img[y0:y1, x0:x1, :3] = region[:, :, :3] * m[:, :, None] + sub * (1 - m[:, :, None])
        else:
            img = over(img, fg)
    if extra_layers:
        for lay in extra_layers:
            lp = S.d + lay + '/%04d.png' % f
            if os.path.exists(lp):
                img = over(img, load_rgba(lp))
    return img[:, :, :3]


def finish(S, rgb, i, n, zoom=(1.0, 1.0), pan=((0, 0), (0, 0)), shake=0.0, warmth=0.03, grain=0.012, rng=None, fade_in=0, fade_out=0):
    W, H = S.W, S.H
    t = i / max(1, n - 1)
    z = zoom[0] + (zoom[1] - zoom[0]) * (t * t * (3 - 2 * t))
    px = pan[0][0] + (pan[1][0] - pan[0][0]) * t
    py = pan[0][1] + (pan[1][1] - pan[0][1]) * t
    if shake:
        px += shake * (np.sin(i * 0.37) + 0.5 * np.sin(i * 0.91 + 1)); py += shake * (np.cos(i * 0.29) + 0.5 * np.sin(i * 0.73))
    sx = OUT_W / W
    Mo = np.array([[z * sx, 0, ((1 - z) * W / 2 + px) * sx], [0, z * sx, ((1 - z) * H / 2 + py) * sx]], np.float32)
    out = cv2.warpAffine(rgb, Mo, (OUT_W, OUT_H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    bl = cv2.GaussianBlur(out, (0, 0), 1.2)
    out = np.clip(out + 0.35 * (out - bl), 0, 1)
    out = grade(out, warmth=warmth)
    if grain and rng is not None:
        out = out + rng.normal(0, grain, (OUT_H // 2, OUT_W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
    a = 1.0
    if fade_in and i < fade_in:
        a = (i + 1) / fade_in
    if fade_out and i >= n - fade_out:
        a = min(a, (n - 1 - i) / fade_out)
    return np.clip(out * a, 0, 1)


def compose_shot(name, f0, f1, out_path, bg_blur=0.0, zoom=(1.0, 1.0), pan=((0, 0), (0, 0)), fade_in=0, fade_out=0,
                 warmth=0.03, grain=0.012, shake=0.0, hold_last=0, extra_layers=None, post=None, plate_name='plate.png',
                 prepend=None, prepend_dissolve=0):
    S = ShotData(name, bg_blur=bg_blur, plate_name=plate_name)
    tmp = out_path[:-4] + '.part.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OUT_W}x{OUT_H}', '-r', '24',
           '-i', '-', '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rng = np.random.default_rng(1)
    frames = list(range(f0, f1 + 1))
    n = len(frames)
    last = None
    cache = {}
    have = sorted(int(k) for k in S.meta['frames'].keys())
    def get(fr):
        if fr not in cache:
            cache[fr] = make_frame(S, fr, extra_layers)
            for k in list(cache.keys()):
                if k < fr - 4:
                    del cache[k]
        return cache[fr]
    for i, f in enumerate(frames):
        if S.meta['frames'] and str(f) not in S.meta['frames'] and have:
            prev = max([h for h in have if h < f], default=None)
            nxt = min([h for h in have if h > f], default=None)
            if prev is None or nxt is None:
                rgb = get(prev if prev is not None else nxt)
            else:
                rgb = interp(get(prev), get(nxt), (f - prev) / (nxt - prev))
        else:
            rgb = get(f)
        if post:
            rgb = post(rgb, i, n)
        out = finish(S, rgb, i, n, zoom=zoom, pan=pan, shake=shake, warmth=warmth, grain=grain, rng=rng, fade_in=fade_in, fade_out=fade_out)
        if prepend is not None and i < prepend_dissolve:
            a = (i + 1) / (prepend_dissolve + 1)
            out = prepend[i] * (1 - a) + out * a
        proc.stdin.write((out * 255 + 0.5).astype(np.uint8).tobytes())
        last = out
    for _ in range(hold_last):
        proc.stdin.write((last * 255 + 0.5).astype(np.uint8).tobytes())
    proc.stdin.close()
    rc = proc.wait()
    if rc == 0:
        os.replace(tmp, out_path)
        print('ENCODED', out_path, n + hold_last, 'frames')
    else:
        print('FFMPEG FAILED', rc)
    return last


def preview(name, frames, out_png, **kw):
    S = ShotData(name, bg_blur=kw.pop('bg_blur', 0.0))
    ims = []
    for f in frames:
        rgb = make_frame(S, f)
        out = finish(S, rgb, 0, 1, **kw)
        ims.append(cv2.resize(out, (OUT_W // 3, OUT_H // 3), interpolation=cv2.INTER_AREA))
    sheet = np.concatenate(ims, 1)
    cv2.imwrite(out_png, (sheet[:, :, ::-1] * 255).astype(np.uint8))
