"""wildlore-2d-comp / layers.py: shot-level helpers built on comp.py and bgs.py, as used by every shot of
"The Two Dragons" (../two-dragons-episode/shots2d.py imports them from here).

  dragon(shot, i)              frame i of a Blender render sequence (clamped to the last frame), upscaled to W x H
  sprite(loop, i, x, y, s)     frame i % len of a sprite loop, placed and rotated; SPRITE_RES scales small renders
  plate(shot)                  the shot's static rock plate, with hot lava pixels pushed orange
  west_frame(shot, i, t, hz)   volcano backdrop + plate + contact shadow + render + light wrap + fire hook + embers
  fire_for(shot, i, t, s, e)   a fire-breath function placed from the render's meta.json mouth points, on from s to e
  gold_sky / volc / mist_bg / bright_sky   cached backdrops; cached() keeps at most ~10 of them in memory
  embers / mist_over / rain_over          animated overlays, one particle system per key
  label_layer(a, b)            the species label (name + italic Latin name) on a soft dark band
  panel(...)                   one half of a split screen with its own slow push; push(), fade(), hz_from(), mpos()
"""
import math, os
import numpy as np, cv2
from comp import *
from bgs import *

def hz_from(cam, tgt, lens):
    d = np.array(tgt, float) - np.array(cam, float)
    el = math.atan2(d[2], math.hypot(d[0], d[1]))
    return 0.5 - math.tan(el) / (2 * 18.0 / lens) * -1 if False else 0.5 + math.tan(el) / (2 * 18.0 / lens)


_BG = {}


def cached(key, fn):
    if key not in _BG:
        if len(_BG) > 10:
            for k in list(_BG.keys())[:len(_BG) - 6]:
                del _BG[k]
        _BG[key] = fn()
    return _BG[key]


def gold_sky(t, hz=0.56, sun=(0.7, 0.49), seed=5, peaks=True, drift=0.004):
    sx, sy = sun[0] * W, sun[1] * H

    def static():
        img = sky_gradient(hz, (0.15, 0.19, 0.36), (0.76, 0.48, 0.45), (1.0, 0.8, 0.58))
        img = sun_glow(img, sx, sy)
        img = cirrus(img, hz, 3, (1.0, 0.72, 0.6), amt=0.45, sx=sx, sy=sy)
        if peaks:
            img = peak_layer(img, hz, 7, [0.1 * W, 0.33 * W, 0.93 * W], [0.13 * H, 0.07 * H, 0.1 * H],
                             [0.32 * W, 0.2 * W, 0.28 * W], (0.17, 0.15, 0.25), sun_x=sx, haze=(0.95, 0.72, 0.6), haze_amt=0.42, jag=0.04)
        return img
    img = cached(("gold", hz, sun, seed, peaks), static)
    sea = cached(("goldsea", hz, sun), lambda: cloud_sea_puffs(img, hz, sx, seed=5))
    z = 1.0 + 0.0025 * t
    if z < 1.0005:
        return sea
    yh = int(hz * H)
    out = sea.copy()
    hh = H - yh
    M2 = np.array([[z, 0, (1 - z) * W / 2], [0, z, 0]], np.float32)
    out[yh:] = cv2.warpAffine(sea[yh:], M2, (W, hh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


def cloud_sea_soft(img, hz, sun_x, t, seed, drift):
    return cloud_sea(img, hz, sun_x, t, seed=seed, lit=(1.0, 0.9, 0.78), shade=(0.62, 0.55, 0.68), haze=(1.0, 0.84, 0.68),
                     drift=(0.0, drift), gaps=True, deep=(0.5, 0.42, 0.55))


def push(i, n, z0=1.0, z1=1.05):
    return z0 + (z1 - z0) * (i / max(1, n - 1))


def dragon(name, i, haze=None, k=0.0, gain=None):
    fs = seq(name)
    if not fs:
        return np.zeros((H, W, 4), np.float32)
    im = full_frame(load_rgba(fs[min(i, len(fs) - 1)]))
    if gain is not None:
        im = grade_layer(im, gain=gain)
    if haze is not None and k > 0:
        im = haze_layer(im, haze, k)
    return im


SPRITE_RES = {}   # loop name -> scale factor for renders made smaller than the frame (the episode fills it)


def sprite(name, i, cx, cy, scale, ang=0.0, flip=False, haze=None, k=0.0, gain=None, sat=1.0):
    scale = scale * SPRITE_RES.get(name, 1.0)
    fs = seq(name)
    if not fs:
        return np.zeros((H, W, 4), np.float32)
    im = load_rgba(fs[i % len(fs)])
    if flip:
        im = im[:, ::-1].copy()
    if gain is not None or sat != 1.0:
        im = grade_layer(im, gain=gain or (1, 1, 1), sat=sat)
    if haze is not None and k > 0:
        im = haze_layer(im, haze, k)
    return place(im, cx, cy, scale, ang)


def plate(name, haze=None, k=0.0):
    p = os.path.join(R, name, "plate.png")
    im = full_frame(load_rgba(p)).copy()
    lum = im[..., :3].mean(axis=2)
    hot = ss(0.45, 0.8, lum)[..., None]
    im[..., :3] = im[..., :3] * (1 - hot) + im[..., :3] * col((1.0, 0.5, 0.18)) * hot * 1.1
    if haze is not None:
        im = haze_layer(im, haze, k)
    return im


def mpos(m, key, i):
    d = m.get(str(i)) or m.get(str(min(int(x) for x in m.keys()))) if m else None
    if d is None or key not in d:
        return None
    return d[key][0] * W, d[key][1] * H


def contact_shadow(img, drg, strength=0.45, dy=8, size=10):
    a = drg[..., 3]
    sh = blur(np.roll(a, dy, axis=0), size) * strength
    return img * (1 - sh[..., None])


_EMB = {}


def embers(key, t, n=120, seed=3, speed=70, size=(1.0, 3.0), tint=(1.0, 0.5, 0.12), amt=1.0):
    if key not in _EMB:
        _EMB[key] = Embers(n=n, seed=seed, speed=speed, size=size)
    e = _EMB[key].draw(t)
    return col(tint) * e[..., None] * amt


_MIST = {}


def mist_over(img, key, t, y0, y1, amt, speed=10, colr=(0.9, 0.92, 0.92), seed=9):
    if key not in _MIST:
        _MIST[key] = Mist(seed=seed)
    a, c = _MIST[key].layer(t, y0, y1, amt, speed=speed, colr=colr)
    return apply_mist(img, a, c)


_RAIN = {}


def rain_over(img, key, t, amt=1.0, n=900, speed=2200, angle=0.12, colr=(0.8, 0.85, 0.9)):
    if key not in _RAIN:
        _RAIN[key] = Rain(n=n, speed=speed, angle=angle)
    L = _RAIN[key].draw(t) * amt
    return img * (1 - L[..., None] * 0.5) + col(colr) * L[..., None]


def _label(a, b, strength=0.34):
    L = text_layer([(a, 0.19 * H, 54, False, 4, 1.0), (b, 0.19 * H + 58, 40, True, 1, 0.92)])
    y = np.arange(H, dtype=np.float32)[:, None]
    band = np.exp(-((y - (0.19 * H + 30)) / 75.0) ** 2) * strength
    x = np.arange(W, dtype=np.float32)[None, :]
    band = band * np.exp(-((x - W / 2) / (W * 0.36)) ** 2)
    ba = band[..., None]
    out = L.copy()
    out[..., 3:4] = L[..., 3:4] + ba * (1 - L[..., 3:4])
    return out


def label_layer(a, b, strength=0.34):
    return cached(("lab", a, strength), lambda: _label(a, b, strength))


def fade(i, n, fin=6, fout=6, i0=0):
    x = i - i0
    return ssf(0, fin, x) * (1 - ssf(n - fout, n, x))


VHAZE = (0.75, 0.32, 0.16)


def volc(t, hz, sun=(0.18, 0.62), blur_px=0, vx=0.66, vh=0.3, vw=0.55, seed=21):
    key = ("volc", hz, sun, blur_px, vx, vh, vw, seed, round(t, 4))
    def mk():
        return volcano_bg(t, hz=hz, vx=vx, vh=vh, vw=vw, sun=sun, blur_px=blur_px, seed=seed)
    return cached(key, mk)


def west_frame(shot, i, t, hz, fire=None, zoom=1.0, sun=(0.18, 0.62), blur_px=0, emb=1.0, gain=(0.96, 0.8, 0.8), plate_name=None):
    img = volc(t, hz, sun=sun, blur_px=blur_px).copy()
    if plate_name:
        pl = plate(plate_name)
        img = over(img, pl)
    drg = dragon(shot, i, gain=gain)
    if plate_name:
        img = contact_shadow(img, drg, 0.35, 6, 8)
    img = over(img, drg)
    img = img + light_wrap(volc(t, hz, sun=sun, blur_px=blur_px), drg, 0.35)
    if fire is not None:
        img = fire(img)
    if emb > 0:
        img = img + embers(("w", shot), t, amt=emb)
    return img


def mist_bg(t, hz=0.6, blur_px=0, river=False, mood="mist", layers=4, shift=0.0):
    key = ("karst", hz, blur_px, river, mood, layers, int(t * 6) if shift else 0)
    return cached(key, lambda: karst_bg(t, hz=hz, blur_px=blur_px, river=river, mood=mood, layers=layers, x_shift_rate=shift))


def mouth_gap(p, q, back=0.15, down=0.28):
    dx, dy = q[0] - p[0], q[1] - p[1]
    d = math.hypot(dx, dy)
    ppm = d / 1.02
    ux, uy = dx / d, dy / d
    px_, py_ = -uy, ux
    if py_ < 0:
        px_, py_ = -px_, -py_
    return p[0] - ux * back * ppm + px_ * down * ppm, p[1] - uy * back * ppm + py_ * down * ppm, ppm


def fire_for(shot, i, t, start, end, Lm=13.0, w1m=2.8, ign=None, bias=-22.0):
    m = meta(shot)
    p = mpos(m, "mouth", i); q = mpos(m, "mouth_fwd", i)
    if p is None or q is None:
        return None
    dx, dy = q[0] - p[0], q[1] - p[1]
    ox, oy, ppm = mouth_gap(p, q)
    ang = -math.degrees(math.atan2(dy, dx)) + bias
    grow = 1.0 if start <= 0 else ssf(start, start + 7, i)
    inten = (1.0 if start <= 0 else ssf(start, start + 3, i)) * (1 - ssf(end - 8, end, i))
    def fn(img):
        out = fire_jet(img, ox, oy, ang, Lm * ppm, t, intensity=inten * 1.1,
                       w0=0.16 * ppm, w1=w1m * ppm, grow=grow)
        if inten > 0:
            g = radial(p[0] + dx * 3, p[1] + dy * 3, 5 * ppm, power=1.0) * inten
            out = screen(out, col((1.0, 0.45, 0.12)) * g[..., None] * 0.55)
            out = sparks(out, p[0] + dx * 0.5, p[1] + dy * 0.5, ang, t, n=50, seed=7, intensity=inten, speed=4 * ppm)
        return out
    return fn


def bright_sky(t, seed=12):
    def mk():
        img = vgrad((0.42, 0.58, 0.78), (0.88, 0.9, 0.9), gamma=0.9)
        img = sun_glow(img, 0.8 * W, 0.12 * H, core=(1, 0.98, 0.92), halo=(1, 0.93, 0.8), strength=0.8)
        return img
    img = cached(("bright", seed), mk).copy()
    n1 = scroll(220, seed, -t * 90 + 400, 0, octaves=7)
    a = ss(0.1, 1.2, n1) * 0.85
    lit = ss(-0.6, 1.2, n1 - np.roll(n1, 10, axis=0))
    c = col((0.78, 0.8, 0.86)) * (1 - lit[..., None]) + col((1.0, 0.99, 0.97)) * lit[..., None]
    return img * (1 - a[..., None]) + c * a[..., None]


def panel(name, focus, z, bg, i, n, gain=None):
    im = over(bg, dragon(name, 0, gain=gain))
    zz = max(1.0, z * push(i, n, 1.0, 1.06))
    ph = H // 2 - 2
    fx = min(max(focus[0] * W, W / (2 * zz)), W - W / (2 * zz))
    fy = min(max(focus[1] * H, ph / (2 * zz)), H - ph / (2 * zz))
    M = np.array([[zz, 0, W / 2 - fx * zz], [0, zz, (H / 2 - 2) / 2 - fy * zz]], np.float32)
    return cv2.warpAffine(im, M, (W, H // 2 - 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
