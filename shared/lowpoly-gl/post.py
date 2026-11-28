"""Post pass for lowpoly-gl frames: depth of field, bloom, ACES tone map, grade, vignette, grain, glitch, fades."""
import numpy as np
import cv2


def blur(img, sigma):
    if sigma < 0.6:
        return img
    if sigma > 5:
        f = 4 if sigma > 14 else 2
        h, w = img.shape[:2]
        small = cv2.resize(img, (w // f, h // f), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / f)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(img, (0, 0), sigma)


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


_VIG = {}


def vignette_mask(h, w, amt, cy=0.45):
    k = (h, w, round(amt, 3), cy)
    if k not in _VIG:
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        r2 = ((x - w / 2) / (w * 0.62)) ** 2 + ((y - h * cy) / (h * 0.62)) ** 2
        _VIG[k] = np.clip(1 - amt * r2, 0, 1)[..., None]
    return _VIG[k]


def dof(rgb, depth, focus, amount, levels=(1.5, 3.5, 7.0, 13.0)):
    """amount: blur radius (sigma, px) for very far objects. Background blur ignores pixels in front of the focus.
    The blur levels are made at half size and blended back at full size."""
    if amount <= 0:
        return rgb
    h, w = depth.shape
    coc = np.clip(amount * np.abs(depth - focus) / np.maximum(depth, 1e-3), 0, levels[-1]).astype(np.float32)
    hs, ws = h // 2, w // 2
    rs = cv2.resize(rgb, (ws, hs), interpolation=cv2.INTER_AREA)
    ds = cv2.resize(depth, (ws, hs), interpolation=cv2.INTER_NEAREST)
    w2 = (ds > focus * 1.04).astype(np.float32)
    fg = (ds <= focus * 1.04)[..., None]
    out = rgb
    prev_s = 0.0
    for s in levels:
        sh = s / 2
        num = cv2.GaussianBlur(rs * w2[..., None], (0, 0), sh); den = cv2.GaussianBlur(w2, (0, 0), sh)[..., None]
        full = cv2.GaussianBlur(rs, (0, 0), sh)
        lvl = np.where(den > 1e-3, num / np.maximum(den, 1e-3), full)
        lvl = np.where(fg, full, lvl)
        lvl = cv2.resize(lvl, (w, h), interpolation=cv2.INTER_LINEAR)
        t = np.clip((coc - prev_s) / (s - prev_s), 0, 1)[..., None]
        out = out + (lvl - out) * t
        prev_s = s
    return out


def bloom(rgb, thresh=1.0, strength=0.5):
    lum = rgb.max(axis=2, keepdims=True)
    bright = rgb * np.clip((lum - thresh) / np.maximum(lum, 1e-4), 0, None)
    h, w = rgb.shape[:2]
    b1 = cv2.resize(bright, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(b1, (0, 0), 4)
    g2 = cv2.GaussianBlur(cv2.resize(b1, (w // 16, h // 16), interpolation=cv2.INTER_AREA), (0, 0), 4)
    g = cv2.resize(g1, (w, h)) * 0.6 + cv2.resize(g2, (w, h)) * 0.8
    return rgb + strength * g


def glitch(img, amt, rng):
    """img uint8 HxWx3. Channel split, sliced horizontal offsets, occasional colour blocks."""
    if amt <= 0:
        return img
    h, w = img.shape[:2]
    out = img.copy()
    k = int(4 + 26 * amt)
    out[..., 0] = np.roll(img[..., 0], k, axis=1)
    out[..., 2] = np.roll(img[..., 2], -k, axis=1)
    for _ in range(int(3 + 14 * amt)):
        y0 = rng.integers(0, h - 10); hh = int(rng.integers(6, int(20 + 140 * amt)))
        dx = int(rng.normal(0, 60 * amt))
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], dx, axis=1)
    if amt > 0.4:
        for _ in range(int(2 + 4 * amt)):
            y0 = rng.integers(0, h - 40); x0 = rng.integers(0, w - 200)
            out[y0:y0 + int(rng.integers(4, 30)), x0:x0 + int(rng.integers(60, 400))] = rng.choice(
                [[255, 0, 60], [0, 255, 200], [255, 255, 255], [0, 0, 0]])
    return out


_LUT = (np.linspace(0, 1, 4096) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)
_GR = {}


def _grain(h, w, frame):
    if (h, w) not in _GR:
        r = np.random.default_rng(77)
        _GR[(h, w)] = [cv2.resize(r.standard_normal((h // 2, w // 2)).astype(np.float32) * 5.0, (w, h)) for _ in range(12)]
    g = _GR[(h, w)][frame % 12]
    return np.roll(g, (frame * 37) % h, axis=0)


def finish(img, cfg, frame=0):
    rgb, depth = img[..., :3], img[..., 3]
    rgb = np.maximum(rgb, 0)
    if cfg.get('dof', 0) > 0:
        rgb = dof(rgb, depth, cfg['focus'], cfg['dof'])
    rgb = bloom(rgb, cfg.get('bloom_t', 1.0), cfg.get('bloom', 0.35))
    rgb = rgb * cfg.get('exposure', 1.0)
    rgb = aces(rgb)
    lum = rgb.mean(axis=2, keepdims=True)
    rgb = lum + (rgb - lum) * cfg.get('sat', 1.0)
    sh = np.array(cfg.get('shadow_tint', (0.94, 1.0, 1.08)), np.float32)
    hi = np.array(cfg.get('high_tint', (1.05, 1.0, 0.93)), np.float32)
    rgb = rgb * (sh + (hi - sh) * np.clip(lum * 1.4, 0, 1))
    h, w = rgb.shape[:2]
    rgb = rgb * vignette_mask(h, w, cfg.get('vignette', 0.5))
    rgb = rgb * cfg.get('fade', 1.0)
    idx = (np.clip(rgb, 0, 1) * 4095 + 0.5).astype(np.int16)
    out = _LUT[idx]
    rng = np.random.default_rng(1000 + frame)
    g = cfg.get('grain', 0.02)
    if g:
        n = _grain(h, w, frame)
        out = np.clip(out.astype(np.int16) + (n * (g / 0.02)).astype(np.int16)[..., None], 0, 255).astype(np.uint8)
    if cfg.get('glitch', 0) > 0:
        out = glitch(out, cfg['glitch'], rng)
    return out
