"""wildlore-2d-comp / comp.py: the numpy compositing core.

Frames are float32 RGB in 0..1 at W x H; layers are premultiplied RGBA. Settings:
  W, H, FPS   1080 x 1920 at 24 fps (the Wildlore format)
  R           folder of Blender renders <shot>/####.png + meta.json: env RENDERS, default ../dragons/out/renders
  FONT_R/I    EB Garamond 12 Regular / Italic: env WILDLORE_SERIF / WILDLORE_SERIF_ITALIC, else fonts/ (get_fonts.py),
              else the Ubuntu fonts-ebgaramond files in /usr/share/fonts/opentype/ebgaramond/
"""
import numpy as np, cv2, os, json, math, glob, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
FPS = 24
R = os.environ.get("RENDERS") or os.path.join(HERE, "..", "dragons", "out", "renders")
cv2.setNumThreads(2)


# ---------------- basics ----------------
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def ssf(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0 + 1e-9), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def col(c):
    return np.array(c, np.float32).reshape(1, 1, 3)


_NCACHE = {}


def noise(h, w, scale, seed, octaves=6, persist=0.5, aniso=1.0):
    key = (h, w, scale, seed, octaves, persist, aniso)
    if key in _NCACHE:
        return _NCACHE[key]
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    sx, sy = scale * aniso, scale
    for o in range(octaves):
        gh = int(h / sy) + 4; gw = int(w / sx) + 4
        g = r.standard_normal((gh, gw)).astype(np.float32)
        up = cv2.resize(g, (int(gw * sx), int(gh * sy)), interpolation=cv2.INTER_CUBIC)
        oy = r.integers(0, max(1, up.shape[0] - h)); ox = r.integers(0, max(1, up.shape[1] - w))
        out += amp * up[oy:oy + h, ox:ox + w]
        tot += amp; amp *= persist; sx /= 2; sy /= 2
        if sy < 1.2:
            break
    out /= tot
    out = (out - out.mean()) / (out.std() + 1e-6)
    _NCACHE[key] = out
    return out


def blur(img, s):
    if s <= 0.3:
        return img
    if s > 10:
        k = s / 5.0
        h, w = img.shape[:2]
        sm = cv2.resize(img, (max(2, int(w / k)), max(2, int(h / k))), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), 5.0)
        return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(img, (0, 0), s)


def fft_noise(size, beta=2.4, seed=0, lowcut=3, aniso=1.0):
    r = np.random.default_rng(seed)
    kx = np.fft.fftfreq(size)[None, :] * aniso
    ky = np.fft.fftfreq(size)[:, None]
    k = np.sqrt(kx ** 2 + ky ** 2)
    k[0, 0] = 1.0
    amp = np.maximum(k, lowcut / size) ** (-beta / 2)
    amp[0, 0] = 0
    ph = r.uniform(0, 2 * np.pi, (size, size))
    n = np.real(np.fft.ifft2(amp * np.exp(1j * ph))).astype(np.float32)
    return (n - n.mean()) / (n.std() + 1e-6)


def vgrad(c_top, c_bot, h=H, w=W, gamma=1.0, y0=0.0, y1=1.0):
    y = np.linspace(0, 1, h, dtype=np.float32)
    t = np.clip((y - y0) / (y1 - y0), 0, 1) ** gamma
    g = col(c_top) * (1 - t[:, None, None]) + col(c_bot) * t[:, None, None]
    return np.repeat(g, w, axis=1)


def radial(cx, cy, r, h=H, w=W, power=1.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return np.exp(-d ** power)


def over(bg, rgba_pm):
    a = rgba_pm[..., 3:4]
    return rgba_pm[..., :3] + bg * (1 - a)


def screen(bg, c):
    return 1 - (1 - bg) * (1 - np.clip(c, 0, 1))


# ---------------- sprite / render loading ----------------
_ICACHE = {}


def load_rgba(path):
    if path in _ICACHE:
        return _ICACHE[path]
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    im = im[..., [2, 1, 0, 3]].astype(np.float32) / 255.0
    im[..., :3] *= im[..., 3:4]
    if len(_ICACHE) > 400:
        _ICACHE.clear()
    _ICACHE[path] = im
    return im


def seq(name):
    return sorted(glob.glob(os.path.join(R, name, "[0-9][0-9][0-9][0-9].png")))


def meta(name):
    p = os.path.join(R, name, "meta.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def place(rgba, cx, cy, scale, ang=0.0, anchor=None, out_hw=(H, W)):
    """warp premultiplied rgba so that anchor (default center) lands on (cx, cy)."""
    h, w = rgba.shape[:2]
    ax, ay = anchor if anchor is not None else (w / 2, h / 2)
    M = cv2.getRotationMatrix2D((ax, ay), ang, scale)
    M[0, 2] += cx - ax; M[1, 2] += cy - ay
    return cv2.warpAffine(rgba, M, (out_hw[1], out_hw[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def full_frame(rgba):
    """720x1280 render -> 1080x1920."""
    if rgba.shape[0] == H:
        return rgba
    return cv2.resize(rgba, (W, H), interpolation=cv2.INTER_CUBIC).clip(0, 1)


def haze_layer(rgba, hcol, k):
    out = rgba.copy()
    out[..., :3] = rgba[..., :3] * (1 - k) + col(hcol) * rgba[..., 3:4] * k
    return out


def grade_layer(rgba, gain=(1, 1, 1), lift=0.0, sat=1.0):
    out = rgba.copy()
    rgb = out[..., :3]
    if sat != 1.0:
        l = rgb.mean(axis=2, keepdims=True)
        rgb = l + (rgb - l) * sat
    out[..., :3] = np.clip(rgb * col(gain) + lift * out[..., 3:4], 0, None)
    return out


def light_wrap(bg, rgba, amt=0.5, size=6):
    a = rgba[..., 3]
    inner = cv2.erode(a, np.ones((3, 3), np.uint8), iterations=2)
    edge = np.clip(a - blur(inner, size * 0.5), 0, 1)
    return blur(bg, size) * edge[..., None] * amt


# ---------------- final touches ----------------
def vignette(img, amt=0.35):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    v = 1 - amt * np.clip(d - 0.35, 0, 1) ** 1.6
    return img * v[..., None]


_VIG = None


def finish(img, f, grain=0.018, vig=0.32, zoom=1.0, pan=(0.0, 0.0), contrast=1.0, sat=1.0):
    global _VIG
    if zoom != 1.0 or pan != (0.0, 0.0):
        M = np.array([[zoom, 0, (1 - zoom) * W / 2 + pan[0]], [0, zoom, (1 - zoom) * H / 2 + pan[1]]], np.float32)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if sat != 1.0:
        l = img.mean(axis=2, keepdims=True); img = l + (img - l) * sat
    if contrast != 1.0:
        img = (img - 0.5) * contrast + 0.5
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        _VIG = (1 - np.clip(d - 0.35, 0, 1) ** 1.6)[..., None]
    img = img * (1 - vig * (1 - _VIG))
    r = np.random.default_rng(f * 7919 + 13)
    g = r.standard_normal((H // 2, W // 2)).astype(np.float32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    img = img + g[..., None] * grain
    return np.clip(img, 0, 1)


# ---------------- text ----------------
def _font(env, name):
    for p in (os.environ.get(env), os.path.join(HERE, "fonts", name), os.path.join("/usr/share/fonts/opentype/ebgaramond", name)):
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError(name + ": run python get_fonts.py (or set %s)" % env)


FONT_R = _font("WILDLORE_SERIF", "EBGaramond12-Regular.otf")
FONT_I = _font("WILDLORE_SERIF_ITALIC", "EBGaramond12-Italic.otf")


def text_layer(lines, h=H, w=W):
    """lines: list of (text, y_center_px, size, italic, tracking_px, alpha_scale). returns RGBA float premult."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for text, y, size, italic, track, a in lines:
        font = ImageFont.truetype(FONT_I if italic else FONT_R, size)
        widths = [d.textlength(ch, font=font) for ch in text]
        total = sum(widths) + track * (len(text) - 1)
        x = (w - total) / 2
        for ch, cw in zip(text, widths):
            d.text((x, y), ch, font=font, fill=(255, 255, 255, int(255 * a)), anchor="lm")
            x += cw + track
    arr = np.asarray(im).astype(np.float32) / 255.0
    # soft shadow for legibility
    sh = blur(arr[..., 3], 6) * 0.55
    out = np.zeros_like(arr)
    out[..., 3] = np.clip(arr[..., 3] + sh * (1 - arr[..., 3]), 0, 1)
    out[..., :3] = arr[..., :3] * arr[..., 3:4]
    return out


def add_text(img, layer, alpha):
    if alpha <= 0.001:
        return img
    l = layer * alpha
    return l[..., :3] + img * (1 - l[..., 3:4])


# ---------------- encoding ----------------
class Writer:
    def __init__(self, path):
        self.path = path
        self.tmp = path.replace(".mp4", ".tmp.mp4")
        self.p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
                                   "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
                                   "-pix_fmt", "yuv420p", "-r", str(FPS), self.tmp], stdin=subprocess.PIPE)

    def write(self, img):
        self.p.stdin.write((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())

    def close(self):
        self.p.stdin.close(); rc = self.p.wait()
        if rc == 0:
            os.replace(self.tmp, self.path)
        return rc


_T2 = {}


def tex2(seed, scale, aniso=1.0, beta=3.8):
    k = (seed, scale, aniso, beta)
    if k not in _T2:
        _T2[k] = fft_noise(2048, beta=beta, seed=seed, lowcut=max(1.0, 2048.0 / scale), aniso=aniso)
    return _T2[k]


def rolled(T, dy=0, dx=0, h=None, w=None):
    h = h or H; w = w or W
    return np.roll(T, (int(dy) % T.shape[0], int(dx) % T.shape[1]), axis=(0, 1))[:h, :w]


def scroll(scale, seed, dy=0.0, dx=0.0, octaves=6, persist=0.5, aniso=1.0, pad=1000, h=None, w=None):
    h = h or H; w = w or W
    N_ = noise(h + pad, w + pad, scale, seed, octaves=octaves, persist=persist, aniso=aniso)
    ox = int(np.clip(pad / 2 + dx, 0, pad)); oy = int(np.clip(pad / 2 + dy, 0, pad))
    return N_[oy:oy + h, ox:ox + w]
