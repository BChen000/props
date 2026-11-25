"""Post: turns the transparent 864x1536 renders into finished 1080x1920 frames and encodes the Short.

Per frame: mood backdrop (display colours from build/lut.json) with drifting bokeh, the render on top
(premultiplied, Lanczos upscale), bloom from the bright pixels, a glow halo and 5-frame trail on the
marble (projected from the camera path), vignette, falling snow, then the HUD: title, team and song
labels that pop in at each round, and 3-vs-3 score dots (current round enlarged, pulsing on every hit).
The HUD resets on the last frame so the loop is seamless. All motion is periodic in the video length.

  python3 post.py test 45,1100          # build/test/post_XXXX.jpg
  python3 post.py watch                 # encode build/chunks/ as the render finishes frames (run niced)
  python3 post.py all                   # encode every chunk now
  python3 post.py concat                # join chunks + audio -> build/out/short.mp4
"""
import json
import math
import os
import subprocess
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import settings

W, H = settings.WIDTH, settings.HEIGHT
FPS = settings.FPS
D = json.load(open(settings.PLAN_JSON))
LUT = np.array(json.load(open(settings.LUT_JSON)), np.float32)
FACT = np.array([0.3, 0.45, 0.6, 0.8, 1.0, 1.2, 1.35, 1.6], np.float32)
T = D['T']
N = D['N']
rounds = D['rounds']
TEAM_COL = settings.TEAMS
rng = np.random.default_rng(5)


def font(size, wght):
    for path, kind in settings.FONT_CANDIDATES:
        if kind == 'static':
            p = path.format(w={700: 'Bold', 800: 'ExtraBold', 900: 'Black'}.get(wght, 'Bold'))
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        elif os.path.exists(path):
            f = ImageFont.truetype(path, size)
            try:
                f.set_variation_by_axes([wght])
            except Exception:
                pass
            return f
    raise SystemExit('No HUD font found: install Montserrat, or Poppins with ../style-kit/get_fonts.py')


# ---------------- mood timeline ----------------
keys = [(0.0, settings.INTRO_MOOD)]
cur = settings.INTRO_MOOD
for r in rounds:
    keys.append((r['t_start'] - 0.45, cur))
    keys.append((r['t_start'] + 0.25, r['k']))
    cur = r['k']
keys.append((T + 1, cur))


def mood_weights(t):
    for (t0, m0), (t1, m1) in zip(keys[:-1], keys[1:]):
        if t0 <= t <= t1:
            a = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return m0, m1, a
    return cur, cur, 0.0


# ---------------- backdrop per mood ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dist = np.sqrt(((xx / W - 0.5) * 0.62) ** 2 + ((yy / H - 0.54) * 1.0) ** 2)
vf = np.clip(1.35 + (0.45 - 1.35) * dist / 0.62, 0.3, 1.6)
idx = np.interp(vf, FACT, np.arange(len(FACT))).astype(np.float32)
i0 = np.floor(idx).astype(int)
i1 = np.minimum(i0 + 1, len(FACT) - 1)
fr = (idx - i0)[..., None]
BG = []
for m in range(6):
    BG.append(LUT[m][i0] * (1 - fr) + LUT[m][i1] * fr)
VIG = (1.0 - 0.22 * np.clip(((xx / W - 0.5) * 1.1) ** 2 + ((yy / H - 0.5) * 0.9) ** 2, 0, 1) * 2.2).clip(0.55, 1)[..., None]
del yy, xx, dist, vf, idx, i0, i1, fr

# ---------------- bokeh ----------------
BOKEH_COLS = [(255, 70, 60), (255, 190, 90), (80, 255, 130), (255, 240, 220)]
bok = []
for i in range(17):
    bok.append(dict(x=rng.uniform(0.02, 0.98) * W, y=rng.uniform(0.0, 1.0) * H, r=rng.uniform(40, 125),
                    c=BOKEH_COLS[i % 4], k1=int(rng.integers(1, 3)), k2=int(rng.integers(1, 3)), k3=int(rng.integers(2, 6)),
                    p1=rng.uniform(0, 6.28), p2=rng.uniform(0, 6.28), p3=rng.uniform(0, 6.28),
                    ax=rng.uniform(30, 90), ay=rng.uniform(40, 120), s=rng.uniform(0.10, 0.22)))
SPR = {}


def disc_sprite(r, soft):
    key = (int(r), soft)
    if key in SPR:
        return SPR[key]
    R = int(r) + 3
    y, x = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    d = np.sqrt(x * x + y * y)
    a = np.clip((r - d) / soft + 0.5, 0, 1)
    if soft > 3:
        a = a * (0.75 + 0.25 * np.clip(d / r, 0, 1) ** 2)
    SPR[key] = a
    return a


def blit_add(canvas, spr, cx, cy, col, amt):
    R = spr.shape[0] // 2
    x0, y0 = int(cx) - R, int(cy) - R
    x1, y1 = x0 + spr.shape[1], y0 + spr.shape[0]
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(canvas.shape[1], x1), min(canvas.shape[0], y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    s = spr[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0][..., None]
    canvas[cy0:cy1, cx0:cx1] += s * (np.array(col, np.float32) * amt)


def blit_over(canvas, spr, cx, cy, col, amt):
    R = spr.shape[0] // 2
    x0, y0 = int(round(cx)) - R, int(round(cy)) - R
    x1, y1 = x0 + spr.shape[1], y0 + spr.shape[0]
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(canvas.shape[1], x1), min(canvas.shape[0], y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    s = spr[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0][..., None] * amt
    canvas[cy0:cy1, cx0:cx1] = canvas[cy0:cy1, cx0:cx1] * (1 - s) + np.array(col, np.float32) * s


# ---------------- snow ----------------
snow = []
for i in range(120):
    sz = rng.uniform(1.4, 5.2)
    n = int(np.clip(round(1 + sz * 0.9 + rng.uniform(-0.5, 0.5)), 2, 7))
    snow.append(dict(x=rng.uniform(0, W), y=rng.uniform(0, H), r=sz, n=n, m=int(rng.integers(2, 8)),
                     ax=rng.uniform(8, 30), p=rng.uniform(0, 6.28), a=rng.uniform(0.35, 0.85) * min(1, sz / 3.5 + 0.35)))

# ---------------- HUD assets ----------------
F_TITLE = font(78, 800)
F_TEAM = font(70, 800)
F_SONG = font(42, 700)
F_VS = font(34, 800)


def text_img(txt, f, col, shadow=True, glow=None):
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = 40
    img = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if glow is not None:
        g = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=glow + (150,))
        g = g.filter(ImageFilter.GaussianBlur(14))
        img.alpha_composite(g)
    if shadow:
        s = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).text((pad - bb[0], pad - bb[1] + 5), txt, font=f, fill=(0, 0, 0, 170))
        s = s.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(s)
        s2 = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(s2).text((pad - bb[0], pad - bb[1] + 2), txt, font=f, fill=(0, 0, 0, 120))
        img.alpha_composite(s2)
    ImageDraw.Draw(img).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=col + (255,))
    return img


TITLE = text_img(settings.TITLE, F_TITLE, (255, 255, 255))
TEAMS = {t: text_img(t, F_TEAM, c, glow=c) for t, c in TEAM_COL.items()}
SONGS = [text_img(r['name'], F_SONG, (255, 255, 255)) for r in rounds]
VS = text_img('vs', F_VS, (255, 255, 255))
Y_TITLE, Y_TEAM, Y_SONG, Y_DOTS = 330, 420, 482, 552
DOT_X = settings.DOT_X
DOT_R = 19

hits_by_round = {}
for o in D['obstacles']:
    if not o['copy']:
        hits_by_round.setdefault(o['k'], []).append(o['t'])
for k in hits_by_round:
    hits_by_round[k].sort()
RESET1 = T - 1.0 / FPS
RESET0 = RESET1 - 0.22


def ease_out_back(x):
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def paste_center(canvas, img, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.02:
        return
    if abs(scale - 1) > 0.01:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        a = img.getchannel('A').point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    canvas.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def draw_hud(t):
    hud = Image.new('RGBA', (W, 680), (0, 0, 0, 0))
    paste_center(hud, TITLE, W / 2, Y_TITLE)
    reset = 0.0 if t < RESET0 else min(1.0, (t - RESET0) / (RESET1 - RESET0))
    cur = None
    for r in rounds:
        if t >= r['t_start'] - 0.04:
            cur = r
    if cur is not None and reset < 1:
        dt = t - (cur['t_start'] - 0.04)
        sc = 0.72 + 0.28 * ease_out_back(dt / 0.24)
        al = min(1.0, dt / 0.09) * (1 - reset)
        paste_center(hud, TEAMS[cur['team']], W / 2, Y_TEAM, sc, al)
        paste_center(hud, SONGS[cur['k']], W / 2, Y_SONG, 0.85 + 0.15 * ease_out_back(dt / 0.28), al)
    paste_center(hud, VS, W / 2, Y_DOTS - 2)
    d = ImageDraw.Draw(hud)
    glow_layer = Image.new('RGBA', (W, 680), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for r in rounds:
        k = r['k']
        x = DOT_X[k]
        col = TEAM_COL[r['team']]
        started = t >= r['t_start'] - 0.04
        is_cur = cur is not None and cur['k'] == k
        fill_a = 0.0
        scale = 1.0
        if started:
            fill_a = 1.0 - reset
            dt = t - (r['t_start'] - 0.04)
            if is_cur:
                scale = 1.38 + 0.5 * math.exp(-dt / 0.09) * (dt < 1.0)
                pulse = 0.0
                for ht in hits_by_round.get(k, []):
                    if 0 <= t - ht < 0.4:
                        pulse = max(pulse, math.exp(-(t - ht) / 0.11))
                scale += 0.14 * pulse
            else:
                nxt = [q for q in rounds if q['k'] == k + 1]
                if nxt:
                    de = t - (nxt[0]['t_start'] - 0.04)
                    scale = 1.0 + 0.38 * max(0.0, 1 - de / 0.2)
            scale = scale * (1 - reset) + 1.0 * reset
        rr = DOT_R * scale
        cy = Y_DOTS
        d.ellipse([x - DOT_R - 2, cy - DOT_R - 2, x + DOT_R + 2, cy + DOT_R + 2], fill=(10, 10, 14, 120), outline=(255, 255, 255, 110), width=2)
        if fill_a > 0.01:
            if is_cur:
                gd.ellipse([x - rr - 14, cy - rr - 14, x + rr + 14, cy + rr + 14], fill=col + (int(150 * fill_a),))
            d.ellipse([x - rr, cy - rr, x + rr, cy + rr], fill=col + (int(255 * fill_a),), outline=(255, 255, 255, int(230 * fill_a)), width=3 if is_cur else 2)
            hl = rr * 0.45
            d.ellipse([x - rr * 0.55, cy - rr * 0.62, x - rr * 0.55 + hl, cy - rr * 0.62 + hl * 0.75], fill=(255, 255, 255, int(90 * fill_a)))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(10))
    out = Image.new('RGBA', (W, 680), (0, 0, 0, 0))
    out.alpha_composite(glow_layer)
    out.alpha_composite(hud)
    return out


DELTA = np.array(D['delta'])
MARB = np.array(D['marble'])
CAMS = np.array(D['cam'])
QUATS = np.array(D['quat'])
KPX = (settings.LENS / 18.0) * (H / 2)


def cam_rot(fc):
    w, x, y, z = QUATS[fc]
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def marble_world(f):
    if f < 0:
        return MARB[f + N] - DELTA
    return MARB[f]


def project(p, fc):
    v = cam_rot(fc).T @ (p - CAMS[fc])
    d = -v[2]
    if d < 0.2:
        return None
    return W / 2 + v[0] / d * KPX, H / 2 - v[1] / d * KPX + settings.SHIFT_Y * H, 0.2 / d * KPX


HALO = {}


def halo_sprite(r):
    key = int(round(r))
    if key in HALO:
        return HALO[key]
    R = int(r * 5.5) + 2
    y, x = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    d = np.sqrt(x * x + y * y)
    a = np.exp(-(d / (r * 1.5)) ** 2) * 0.85 + np.exp(-(d / (r * 2.6)) ** 2) * 0.25
    a *= np.clip((d - r * 0.55) / (r * 0.5), 0.25, 1.0)
    a *= np.clip(1 - (d / R) ** 2, 0, 1) ** 2
    HALO[key] = a
    return a


def draw_marble_glow(img, f):
    for k, amt in ((5, 0.05), (4, 0.07), (3, 0.09), (2, 0.12), (1, 0.15)):
        pr = project(marble_world(f - k), f)
        if pr:
            blit_add(img, halo_sprite(pr[2] * (1 - 0.06 * k)), pr[0], pr[1], (255, 214, 140), amt)
    pr = project(marble_world(f), f)
    if pr:
        blit_add(img, halo_sprite(pr[2]), pr[0], pr[1], (255, 226, 165), 0.34)


def frame_image(f):
    t = f / FPS
    m0, m1, a = mood_weights(t)
    bg = BG[m0] * (1 - a) + BG[m1] * a
    bk = np.zeros((H // 2, W // 2, 3), np.float32)
    for b in bok:
        x = (b['x'] + b['ax'] * math.sin(2 * math.pi * b['k1'] * t / T + b['p1'])) / 2
        y = (b['y'] + b['ay'] * math.sin(2 * math.pi * b['k2'] * t / T + b['p2'])) / 2
        br = 0.55 + 0.45 * math.sin(2 * math.pi * b['k3'] * t / T + b['p3'])
        blit_add(bk, disc_sprite(b['r'] / 2, 2.5), x, y, b['c'], b['s'] * br)
    bk = np.asarray(Image.fromarray(np.clip(bk, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
    bg = 255 - (255 - bg) * (255 - bk) / 255.0
    src = Image.open(os.path.join(settings.FRAMES, f'f_{f:04d}.png')).convert('RGBa').resize((W, H), Image.LANCZOS)
    arr = np.asarray(src, np.float32)
    A = arr[..., 3:4] / 255.0
    img = arr[..., :3] + bg * (1 - A)
    mx = img.max(axis=2, keepdims=True)
    bright = img * np.clip((mx - 168) / 87.0, 0, 1) ** 1.3
    small = Image.fromarray(np.clip(bright, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BOX)
    b1 = np.asarray(small.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), np.float32)
    b2 = np.asarray(small.filter(ImageFilter.GaussianBlur(16)).resize((W, H), Image.BILINEAR), np.float32)
    img = img + 0.75 * b1 + 0.55 * b2
    draw_marble_glow(img, f)
    img = img * VIG
    for s in snow:
        y = (s['y'] + s['n'] * H * t / T) % (H + 20) - 10
        x = s['x'] + s['ax'] * math.sin(2 * math.pi * s['m'] * t / T + s['p'])
        x %= W
        blit_over(img, disc_sprite(s['r'], 1.6), x, y, (255, 255, 255), s['a'])
    img = np.clip(img, 0, 255).astype(np.uint8)
    out = Image.fromarray(img)
    hud = draw_hud(t)
    base = out.crop((0, 0, W, 680)).convert('RGBA')
    base.alpha_composite(hud)
    out.paste(base.convert('RGB'), (0, 0))
    return out


def frame_ready(f):
    p = os.path.join(settings.FRAMES, f'f_{f:04d}.png')
    return os.path.exists(p) and os.path.getsize(p) > 0


def encode_chunk(a, b, out):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS), out + '.tmp.mp4']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(a, b):
        p.stdin.write(frame_image(f).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode == 0:
        os.replace(out + '.tmp.mp4', out)
    print('chunk done', a, b, p.returncode, flush=True)


def chunk_ranges():
    for a in range(0, N, settings.CHUNK):
        yield a, min(N, a + settings.CHUNK), os.path.join(settings.CHUNKS, f'c_{a:04d}.mp4')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'test':
        os.makedirs(settings.TEST, exist_ok=True)
        for f in [int(x) for x in sys.argv[2].split(',')]:
            frame_image(f).save(os.path.join(settings.TEST, f'post_{f:04d}.jpg'), quality=90)
            print('ok', f, flush=True)
    elif mode == 'chunk':
        os.makedirs(settings.CHUNKS, exist_ok=True)
        encode_chunk(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif mode in ('watch', 'all'):
        os.makedirs(settings.CHUNKS, exist_ok=True)
        seen, since = -1, time.time()
        for a, b, out in chunk_ranges():
            if os.path.exists(out):
                continue
            while mode == 'watch' and not all(frame_ready(f) for f in range(a, b)):
                n = sum(frame_ready(f) for f in range(N))
                if n != seen:
                    seen, since = n, time.time()
                elif time.time() - since > 900:
                    raise SystemExit('no new frames for 15 min: is the render still running?')
                time.sleep(20)
            encode_chunk(a, b, out)
    elif mode == 'concat':
        os.makedirs(settings.OUT, exist_ok=True)
        parts = [out for _, _, out in chunk_ranges()]
        missing = [p for p in parts if not os.path.exists(p)]
        if missing:
            raise SystemExit(f'missing chunks: {missing}')
        lst = os.path.join(settings.CHUNKS, 'list.txt')
        with open(lst, 'w') as fh:
            fh.writelines(f"file '{p}'\n" for p in parts)
        final = os.path.join(settings.OUT, 'short.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', settings.AUDIO,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                        '-movflags', '+faststart', final + '.tmp.mp4'], check=True)
        os.replace(final + '.tmp.mp4', final)
        print('wrote', final)
