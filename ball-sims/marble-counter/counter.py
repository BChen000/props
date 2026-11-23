"""Pop-in round counter overlay ("x1", "x2", ... "x40!") from the 40 marbles video.

Three ways to use it:
  python3 counter.py --video IN.mp4 --out OUT.mp4            burn it into a finished video (audio is copied)
  python3 counter.py --png FRAME.png --t 8.0 --out OUT.png    draw it on one frame at time t
  render_video.py ... --overlay ../marble-counter/counter.py  (marble-plate-compositor) draws it while rendering
Needs the Archivo Black font (see README).
"""
import os, sys, argparse, glob, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ======================================================================= SETTINGS
# (start time s, text, font size px, rainbow fill?)
EVENTS = [(0.0, '×1', 150, False), (1.85, '×2', 150, False), (3.70, '×3', 150, False),
          (5.55, '×4', 150, False), (7.40, '×40!', 165, True)]
CENTER = (200, 250)                 # pixel center of the label on a 1080x1920 frame
FONT_FILE = 'ArchivoBlack-Regular.ttf'
FONT_DIRS = ['fonts', '../../shared/fonts']   # searched relative to this file, then installed system fonts
RAINBOW = [(255, 59, 48), (255, 149, 0), (255, 214, 10), (52, 199, 89), (0, 199, 190), (10, 132, 255), (175, 82, 222), (255, 55, 145)]
FILL = (255, 255, 255)
STROKE = (28, 28, 34)
SHADOW_ALPHA = 0.45
POP_TIME = 0.28        # seconds to pop to full size (ease-out-back)
POP_START = 0.35       # starting scale
POP_OVERSHOOT = 1.9
FADE_IN = 0.07
CROSSFADE = 0.12       # old label grows and fades out while the new one pops in
FPS = 30
CRF = 17
# ===================================================================== END SETTINGS


def find_font(name, dirs=FONT_DIRS):
    for d in dirs:
        hits = glob.glob(os.path.join(HERE, d, '**', name), recursive=True)
        if hits:
            return hits[0]
    try:
        from matplotlib import font_manager
        for f in font_manager.findSystemFonts():
            if os.path.basename(f) == name:
                return f
    except Exception:
        pass
    raise SystemExit(f'Font {name} not found. Put it in {os.path.join(HERE, "fonts")} (see README).')


FONT = None


def label_image(text, size, rainbow=False, stroke=None):
    global FONT
    FONT = FONT or find_font(FONT_FILE)
    font = ImageFont.truetype(FONT, size)
    stroke = stroke or max(6, size // 14)
    tmp = Image.new('L', (10, 10))
    bb = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=font, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    ox, oy = 30 - bb[0], 30 - bb[1]
    mask_fill = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask_fill).text((ox, oy), text, font=font, fill=255)
    mask_all = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask_all).text((ox, oy), text, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    if rainbow:
        xs = np.linspace(0, 1, w)
        cols = np.array(RAINBOW, float)
        pos = np.linspace(0, 1, len(cols))
        grad = np.stack([np.interp(xs, pos, cols[:, c]) for c in range(3)], -1)
        fill_rgb = np.broadcast_to(grad[None], (h, w, 3)).astype(np.uint8)
    else:
        fill_rgb = np.full((h, w, 3), FILL, np.uint8)
    out = np.zeros((h, w, 4), np.float32)
    shadow = np.asarray(mask_all.filter(ImageFilter.GaussianBlur(size / 18)), np.float32) / 255
    sh = np.zeros_like(shadow)
    d = max(3, size // 28)
    sh[d:, d:] = shadow[:-d, :-d]
    out[..., 3] = sh * SHADOW_ALPHA
    a_all = np.asarray(mask_all, np.float32) / 255
    a_fill = np.asarray(mask_fill, np.float32) / 255
    stroke_col = np.array(STROKE, np.float32)
    rgb = stroke_col[None, None] * (1 - a_fill[..., None]) + fill_rgb * a_fill[..., None]
    alpha = np.maximum(a_all, out[..., 3])
    out_rgb = rgb * a_all[..., None]
    out[..., :3] = np.where(alpha[..., None] > 0, out_rgb / np.maximum(alpha[..., None], 1e-6), 0)
    out[..., 3] = alpha
    return out


def ease_out_back(x, s=POP_OVERSHOOT):
    x = np.clip(x, 0, 1)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


class Counter:
    def __init__(self, events=EVENTS, center=CENTER):
        self.events = events
        self.center = center
        self.imgs = [label_image(txt, size, rb) for (_, txt, size, rb) in events]

    def apply(self, frame, t):
        cur = None
        for k, (t0, *_rest) in enumerate(self.events):
            if t >= t0:
                cur = k
        if cur is None:
            return frame
        layers = [(cur, t - self.events[cur][0], 1.0)]
        if cur > 0:
            dt_prev = t - self.events[cur][0]
            if dt_prev < CROSSFADE:
                layers.insert(0, (cur - 1, 10.0, 1 - dt_prev / CROSSFADE))
        out = frame.astype(np.float32)
        for k, age, fade in layers:
            img = self.imgs[k]
            sc = POP_START + (1 - POP_START) * ease_out_back(age / POP_TIME)
            if age >= 10:
                sc = 1.0 + 0.25 * (1 - fade)
            alpha_t = min(1.0, age / FADE_IN) * fade
            h, w = img.shape[:2]
            nw, nh = max(2, int(w * sc)), max(2, int(h * sc))
            im = np.asarray(Image.fromarray((img * [1, 1, 1, 255]).clip(0, 255).astype(np.uint8), 'RGBA').resize((nw, nh), Image.LANCZOS), np.float32)
            cx, cy = self.center
            x0, y0 = int(cx - nw / 2), int(cy - nh / 2)
            fx0, fy0 = max(0, x0), max(0, y0)
            fx1, fy1 = min(frame.shape[1], x0 + nw), min(frame.shape[0], y0 + nh)
            if fx1 <= fx0 or fy1 <= fy0:
                continue
            sub = im[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
            a = sub[..., 3:4] / 255 * alpha_t
            out[fy0:fy1, fx0:fx1] = out[fy0:fy1, fx0:fx1] * (1 - a) + sub[..., :3] * a
        return out.clip(0, 255).astype(np.uint8)


_counter = None


def apply_overlay(frame, t):
    """Hook used by marble-plate-compositor/render_video.py --overlay."""
    global _counter
    _counter = _counter or Counter()
    return _counter.apply(frame, t)


def burn_video(src, dst):
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                            '-of', 'csv=p=0', src], capture_output=True, text=True, check=True).stdout.strip().split(',')
    w, h = int(probe[0]), int(probe[1])
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    tmp = dst[:-4] + '.tmp.mp4'
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-',
                            '-i', src, '-map', '0:v', '-map', '1:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(CRF),
                            '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    cn = Counter()
    f = 0
    while True:
        buf = dec.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        enc.stdin.write(cn.apply(frame, f / FPS).tobytes())
        f += 1
    enc.stdin.close()
    if enc.wait() != 0 or dec.wait() != 0:
        raise SystemExit('ffmpeg failed')
    os.replace(tmp, dst)
    print('saved', dst, f, 'frames')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--video'); ap.add_argument('--png'); ap.add_argument('--t', type=float, default=8.0)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.video:
        burn_video(a.video, a.out)
    elif a.png:
        frame = np.asarray(Image.open(a.png).convert('RGB'))
        Image.fromarray(Counter().apply(frame, a.t)).save(a.out)
        print('saved', a.out)
    else:
        ap.error('give --video or --png')
