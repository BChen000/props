"""wildlore-2d-comp / bgs.py: painted backgrounds and effects (skies, cloud sea, peaks, volcano, karst, river, mist,
storm, lightning, rain, embers, fire breath, sparks). Everything is numpy/OpenCV; see the README for the list.
"""
import numpy as np, cv2, math
from comp import *

# ================= SKY / CLOUD SEA =================
_TEX = {}


def tex(seed, size=2048, beta=2.5):
    k = (seed, size, beta)
    if k not in _TEX:
        _TEX[k] = fft_noise(size, beta=beta, seed=seed, lowcut=6)
    return _TEX[k]


def sky_gradient(hz, top, mid, hor, h=H, w=W, below=None):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    yh = hz
    t1 = np.clip(y / (0.62 * yh), 0, 1)
    t2 = np.clip((y - 0.62 * yh) / (0.38 * yh + 1e-6), 0, 1)
    c = np.where(y < 0.62 * yh, col(top)[0] * (1 - t1) + col(mid)[0] * t1, col(mid)[0] * (1 - t2 ** 1.3) + col(hor)[0] * t2 ** 1.3)
    c = np.repeat(c[:, None, :], w, axis=1) if c.ndim == 2 else c
    c = c.reshape(h, 1, 3) if c.shape[1] != w else c
    img = np.repeat(c, w, axis=1) if c.shape[1] == 1 else c
    if below is not None:
        img[int(hz * h):] = col(below)
    return img.astype(np.float32)


def sun_glow(img, sx, sy, core=(1.0, 0.95, 0.85), halo=(1.0, 0.7, 0.42), strength=1.0, r_core=28, r_halo=230, r_wide=900):
    g1 = radial(sx, sy, r_core, power=2.0)
    g2 = radial(sx, sy, r_halo, power=1.0)
    g3 = radial(sx, sy, r_wide, power=0.75)
    add = col(core) * g1[..., None] * 1.6 + col(halo) * (g2[..., None] * 0.55 + g3[..., None] * 0.3)
    return screen(img, add * strength)


def cirrus(img, hz, seed, color, amt=0.55, t=0.0, sx=None, sy=None):
    sh = t * 6
    n = scroll(120, seed, 0, sh, aniso=5.0)
    n2 = scroll(40, seed + 1, 0, sh, octaves=4, aniso=3.0)
    a = ss(0.5, 2.0, n + 0.35 * n2)
    y = np.linspace(0, 1, H)[:, None]
    a *= ss(hz - 0.02, hz - 0.25, y) * amt
    c = col(color)
    if sx is not None:
        g = radial(sx, sy, 500, power=1.0)[..., None]
        c = c * (0.7 + 0.8 * g)
    return img * (1 - a[..., None]) + c * a[..., None]


def cloud_sea(img, hz, sun_x, t, seed=5, lit=(1.0, 0.82, 0.62), shade=(0.48, 0.42, 0.55), haze=(1.0, 0.8, 0.62),
              drift=(0.0, 0.004), height=1.0, scale_tex=1.0, gaps=True, deep=(0.25, 0.22, 0.32), f=900.0, cam_h=60.0):
    yh = int(hz * H)
    rows = H - yh
    T = tex(seed)
    S = T.shape[0]
    yy, xx = np.mgrid[yh:H, 0:W].astype(np.float32)
    dy = (yy - yh) + 1.5
    Z = cam_h * f / dy
    X = (xx - W / 2) * Z / f
    u = (X * 0.9 * scale_tex + drift[0] * t * 400 + S / 2) % S
    v = (Z * 0.9 * scale_tex + drift[1] * t * 4000) % S
    f32 = lambda a: np.ascontiguousarray(a, dtype=np.float32)
    n = cv2.remap(T, f32(u), f32(v), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    n_far = cv2.remap(T, f32(u), f32((v + 18) % S), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    n_side = cv2.remap(T, f32((u + 14 * float(np.sign(sun_x - W / 2))) % S), f32(v), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    pb = 1.0 - np.abs(n) * 0.9
    pf = 1.0 - np.abs(n_far) * 0.9
    ps = 1.0 - np.abs(n_side) * 0.9
    slope = (pf - pb) * 1.6 + (ps - pb) * 0.4
    light = ss(-1.0, 1.0, slope * 2.2 + (pb - 0.55) * 1.2)
    base = col(shade)[0] * (1 - light[..., None]) + col(lit)[0] * light[..., None]
    crease = ss(0.25, 0.0, np.abs(n))
    base = base * (1 - 0.18 * crease[..., None])
    if gaps:
        cov = ss(-2.4, -1.5, n)
        base = base * cov[..., None] + col(deep)[0] * (1 - cov[..., None])
    hz_amt = np.exp(-dy / (rows * 0.22))
    hz_amt = np.clip(hz_amt * 1.15, 0, 1)
    sun_band = radial(sun_x, yh, 420, h=rows + yh, power=1.2)[yh:]
    hc = col(haze)[0] * (1 + 0.6 * sun_band[..., None])
    out = base * (1 - hz_amt[..., None]) + hc * hz_amt[..., None]
    shim = ss(0.15, 0.6, slope) * sun_band * 0.5
    out = out + col(lit)[0] * shim[..., None]
    img = img.copy()
    img[yh:] = out
    # soften horizon line
    band = slice(max(0, yh - 6), min(H, yh + 6))
    img[band] = blur(img[band], 3)
    return img


def peak_layer(img, hz, seed, xs, heights, widths, color, rim=(1.0, 0.75, 0.5), sun_x=None, haze=None, haze_amt=0.0, jag=0.18):
    mask = np.zeros((H, W), np.float32)
    rimm = np.zeros((H, W), np.float32)
    xr = np.arange(W, dtype=np.float32)
    prof = np.full(W, 1e9, np.float32)
    r = np.random.default_rng(seed)
    nz = noise(1, W * 4, 30, seed, octaves=6)[0]
    for x0, hgt, wd in zip(xs, heights, widths):
        d = np.abs(xr - x0) / wd
        top = hz * H - hgt * np.clip(1 - d, 0, 1) ** 1.3
        top = top - hgt * jag * nz[(xr * 3).astype(int) % len(nz)] * np.clip(1 - d, 0, 1)
        prof = np.minimum(prof, np.where(d < 1, top, 1e9))
    yy = np.arange(H, dtype=np.float32)[:, None]
    mask = ss(-1.0, 1.0, yy - prof[None, :]) * (yy < hz * H + 4)
    mask = np.maximum(mask, ((yy >= hz * H) & (yy < hz * H + 6) & (prof[None, :] < hz * H)).astype(np.float32))
    edge = np.clip(1 - (yy - prof[None, :]) / 5.0, 0, 1) * (yy >= prof[None, :])
    c = col(color)
    if haze is not None:
        c = c * (1 - haze_amt) + col(haze) * haze_amt
    tx = noise(H, W, 160, seed + 3, octaves=4)
    shade = (0.9 + 0.1 * tx)[..., None]
    lay = c * shade
    if sun_x is not None:
        side = np.clip((sun_x - xr) / W * 2, -1, 1)[None, :]
        lay = lay + col(rim) * (edge * (0.5 + 0.5 * np.abs(side)))[..., None] * 0.8
    m = mask[..., None]
    return img * (1 - m) + lay * m


# ================= VOLCANO =================
def volcano_bg(t, hz=0.72, vx=0.62, vh=0.33, vw=0.55, seed=21, smoke=True, sun=(0.18, 0.62), blur_px=0, lava_glow=1.0,
               ridge=True):
    img = sky_gradient(hz, (0.07, 0.035, 0.05), (0.42, 0.12, 0.07), (0.98, 0.46, 0.18))
    img = sun_glow(img, sun[0] * W, sun[1] * H, core=(1.0, 0.85, 0.6), halo=(1.0, 0.45, 0.18), strength=0.9, r_halo=180)
    # ash clouds in sky
    n = scroll(220, seed, 0, t * 10, octaves=7, aniso=2.2)
    a = ss(-0.2, 1.4, n) * 0.75
    y = np.linspace(0, 1, H)[:, None]
    a *= ss(hz + 0.02, hz - 0.35, y)
    under = radial(vx * W, hz * H - vh * H, 700, power=1.0)
    ash = col((0.12, 0.06, 0.06)) * (1 - under[..., None]) + col((0.65, 0.2, 0.07)) * under[..., None]
    img = img * (1 - a[..., None]) + ash * a[..., None]
    # far ridge
    img = peak_layer(img, hz, seed + 1, [0.05 * W, 0.3 * W, 0.95 * W], [0.1 * H, 0.14 * H, 0.12 * H], [0.35 * W, 0.3 * W, 0.4 * W],
                     (0.22, 0.08, 0.07), rim=(1.0, 0.5, 0.2), sun_x=sun[0] * W, haze=(0.85, 0.35, 0.15), haze_amt=0.45)
    # volcano cone
    xr = np.arange(W, dtype=np.float32)
    nz = noise(1, W * 2, 18, seed + 5, octaves=6)[0]
    d = np.abs(xr - vx * W) / (vw * W)
    crater_w = 0.06
    nz2 = noise(1, W * 2, 90, seed + 15, octaves=4)[0]
    taper = np.clip(1 - d, 0, 1) ** 0.7
    top = hz * H - vh * H * np.clip(1 - np.maximum(d, crater_w), 0, 1) ** 1.35 / (1 - crater_w) ** 1.35 - (10 * nz[(xr * 2).astype(int) % len(nz)] + 22 * nz2[(xr * 2).astype(int) % len(nz2)] * np.clip(d * 3, 0, 1)) * taper
    top = np.where(d < 1.0, top, hz * H + 10)
    yy = np.arange(H, dtype=np.float32)[:, None]
    m = ss(-1.0, 1.0, yy - top[None, :]) * (yy < hz * H + 3)
    tx = noise(H, W, 40, seed + 6, octaves=6)
    cone = col((0.07, 0.035, 0.03)) * (0.8 + 0.2 * tx[..., None])
    # lava streams
    lava = np.zeros((H, W), np.float32)
    r = np.random.default_rng(seed)
    cx = vx * W; cy = hz * H - vh * H
    for k in range(5):
        ang = r.uniform(-0.9, 0.9)
        pts = []
        x, yv = cx + r.uniform(-20, 20), cy + 4
        for s_ in range(60):
            pts.append((x, yv))
            yv += 6
            x += math.sin(ang) * 6 * (1 + 0.3 * math.sin(s_ * 0.4 + k)) + r.normal(0, 1.2)
            if yv > hz * H:
                break
        pts = np.array(pts, np.int32)
        cv2.polylines(lava, [pts], False, 1.0, thickness=int(r.integers(2, 5)), lineType=cv2.LINE_AA)
    lava *= m
    flick = 0.85 + 0.15 * math.sin(t * 7.0) * math.sin(t * 3.1)
    glow = blur(lava, 2) * 1.4 + blur(lava, 10) * 0.9 + blur(lava, 35) * 0.5
    crater = radial(cx, cy + 6, 26, power=1.5) * 1.6 + radial(cx, cy, 120, power=1.0) * 0.6
    em = (glow + crater) * flick * lava_glow
    lavacol = col((1.0, 0.42, 0.08))
    img = img * (1 - m[..., None]) + cone * m[..., None]
    img = img + lavacol * em[..., None]
    if smoke:
        sm = scroll(90, seed + 9, t * 40, 0)
        yrel = (cy - yy) / H
        xx = xr[None, :]
        cxs = cx + yrel * 0.9 * W * 0.5 + 40 * np.sin(yrel * 9 + t * 0.5)
        width = 30 + yrel * W * 0.45
        col_m = np.exp(-((xx - cxs) / np.maximum(width, 10)) ** 2)
        sa = col_m * ss(-0.05, 0.08, yrel) * ss(0.0, 1.5, sm + 0.8) * 0.85 * (yy < cy + 5)
        smc = col((0.1, 0.07, 0.07)) * (1 - ss(0.0, 0.15, yrel)[..., None] * 0) + col((0.6, 0.18, 0.05)) * ss(0.12, 0.0, yrel)[..., None]
        img = img * (1 - sa[..., None]) + smc * sa[..., None]
    if ridge:
        hb = int(hz * H)
        if hb < H:
            gtx0 = noise(H - hb, W, 40, seed + 16, octaves=5)
            band = col((0.09, 0.035, 0.03)) * (0.8 + 0.2 * gtx0[..., None])
            fadeb = np.clip(1 - np.arange(H - hb, dtype=np.float32) / (0.05 * H), 0, 1)[:, None, None]
            band = band + col((0.55, 0.18, 0.06)) * fadeb * 0.35
            img[hb:] = band
        img = peak_layer(img, hz + 0.04, seed + 2, [0.0, 0.25 * W, 0.6 * W, 1.0 * W], [0.05 * H, 0.08 * H, 0.04 * H, 0.09 * H],
                         [0.3 * W, 0.25 * W, 0.3 * W, 0.3 * W], (0.05, 0.025, 0.025), rim=(1.0, 0.45, 0.15), sun_x=sun[0] * W)
        bot = int((hz + 0.04) * H)
        if bot < H:
            gtx = noise(H - bot, W, 30, seed + 12, octaves=6)
            g = col((0.05, 0.025, 0.025)) * (0.75 + 0.25 * gtx[..., None])
            crk = ss(0.06, 0.0, np.abs(noise(H - bot, W, 60, seed + 13, octaves=5))) * ss(0.2, 1.2, noise(H - bot, W, 120, seed + 14, octaves=3))
            g = g + col((1.0, 0.35, 0.06)) * (blur(crk, 1.5) * 0.9 + blur(crk, 8) * 0.5)[..., None]
            img[bot:] = g
    if blur_px:
        img = blur(img, blur_px)
    return img


class Embers:
    def __init__(self, n=140, seed=3, speed=60, size=(1.0, 3.5), area=(0, W, 0, H)):
        r = np.random.default_rng(seed)
        self.p = np.stack([r.uniform(area[0], area[1], n), r.uniform(area[2], area[3], n)], 1)
        self.v = np.stack([r.normal(8, 12, n), -r.uniform(0.4, 1.0, n) * speed], 1)
        self.s = r.uniform(*size, n); self.ph = r.uniform(0, 6.28, n); self.area = area

    def draw(self, t):
        L = np.zeros((H, W), np.float32)
        p = self.p + self.v * t + np.stack([20 * np.sin(t * 1.3 + self.ph), np.zeros_like(self.ph)], 1)
        p[:, 0] = (p[:, 0] - self.area[0]) % (self.area[1] - self.area[0]) + self.area[0]
        p[:, 1] = (p[:, 1] - self.area[2]) % (self.area[3] - self.area[2]) + self.area[2]
        for (x, y), s_, ph in zip(p, self.s, self.ph):
            a = 0.55 + 0.45 * math.sin(t * 6 + ph)
            cv2.circle(L, (int(x), int(y)), max(1, int(s_)), a, -1, lineType=cv2.LINE_AA)
        return blur(L, 1.2) * 1.2 + blur(L, 6) * 0.8


# ================= KARST / MIST =================
def karst_layer(img, base_y, seed, n, hmin, hmax, wmin, wmax, color, haze, haze_amt, t=0.0, x_shift=0.0,
                veg=(0.1, 0.2, 0.12), rim_side=-1, mist=0.6, mist_h=0.12, mist_col=(0.9, 0.92, 0.9), xs=None):
    r = np.random.default_rng(seed)
    xr = np.arange(W, dtype=np.float32) + x_shift
    prof = np.full(W, 1e9, np.float32)
    if xs is None:
        xs = np.sort(r.uniform(-0.1 * W, 1.1 * W, n))
    big = noise(1, W * 4, 70, seed + 2, octaves=3)[0]
    fine = noise(1, W * 4, 4, seed + 3, octaves=2)[0]
    for i, x0 in enumerate(xs):
        hgt = r.uniform(hmin, hmax) * H; wd = r.uniform(wmin, wmax) * W
        d = (xr - x0) / (wd / 2)
        sk = r.uniform(-0.2, 0.2)
        dd = np.clip(np.abs(d - sk * (1 - np.abs(d))), 0, 1.5)
        p = r.uniform(1.8, 3.0); q = r.uniform(0.28, 0.5)
        dome = np.clip(1 - dd ** p, 0, 1) ** q
        idx = ((xr + i * 97) * 2).astype(int) % len(big)
        top = base_y * H - hgt * dome - (0.035 * hgt * big[idx] + 3.0 * np.abs(fine[idx])) * (dd < 1)
        prof = np.minimum(prof, np.where(dd < 1, top, 1e9))
    yy = np.arange(H, dtype=np.float32)[:, None]
    m = ss(-1.2, 1.2, yy - prof[None, :])
    tx = noise(H, W, 26, seed + 4, octaves=5, aniso=0.35)
    vegm = ss(-0.2, 1.0, noise(H, W, 22, seed + 5, octaves=5)) * ss(70, 5, yy - prof[None, :])
    ledge = ss(0.6, 1.6, noise(H, W, 14, seed + 6, octaves=4, aniso=2.5)) * 0.5
    vegm = np.clip(vegm + ledge * ss(10, 40, yy - prof[None, :]), 0, 1)
    c = col(color) * (0.88 + 0.12 * tx[..., None])
    c = c * (1 - vegm[..., None] * 0.7) + col(veg) * vegm[..., None] * 0.7
    shade_x = np.clip((xr[None, :] % W) / W, 0, 1)
    c = c * (0.92 + 0.08 * (1 - shade_x))[..., None]
    c = c * (1 - haze_amt) + col(haze) * haze_amt
    out = img * (1 - m[..., None]) + c * m[..., None]
    if mist > 0:
        mn = scroll(160, seed + 7, 0, t * 14 - 300, aniso=3.0)
        y = np.linspace(0, 1, H)[:, None]
        band = ss(base_y - mist_h * 1.6, base_y - mist_h * 0.2, y) * ss(base_y + 0.1, base_y - 0.02, y)
        ma = np.clip(band * (0.65 + 0.35 * ss(-1.0, 1.0, mn)) * mist, 0, 1)
        out = out * (1 - ma[..., None]) + col(mist_col) * ma[..., None]
    return out


def karst_bg(t, hz=0.62, sun=(0.25, 0.18), seed=40, river=False, blur_px=0, layers=4, mood="mist", x_shift_rate=0.0):
    if mood == "mist":
        img = sky_gradient(hz, (0.55, 0.66, 0.76), (0.78, 0.84, 0.86), (0.93, 0.93, 0.88))
        img = sun_glow(img, sun[0] * W, sun[1] * H, core=(1.0, 0.98, 0.92), halo=(1.0, 0.92, 0.75), strength=0.45, r_core=60, r_halo=320)
        haze = (0.88, 0.9, 0.88); mc = (0.92, 0.94, 0.92)
        cols = [(0.5, 0.6, 0.62), (0.32, 0.42, 0.42), (0.18, 0.28, 0.26), (0.08, 0.15, 0.12)]
        vegs = [(0.4, 0.52, 0.5), (0.22, 0.34, 0.3), (0.1, 0.22, 0.14), (0.05, 0.14, 0.07)]
    else:  # rain / overcast
        img = sky_gradient(hz, (0.32, 0.37, 0.42), (0.5, 0.55, 0.58), (0.66, 0.7, 0.7))
        haze = (0.6, 0.65, 0.66); mc = (0.68, 0.72, 0.72)
        cols = [(0.38, 0.44, 0.46), (0.25, 0.32, 0.33), (0.14, 0.21, 0.2), (0.06, 0.11, 0.1)]
        vegs = [(0.3, 0.38, 0.38), (0.17, 0.26, 0.23), (0.08, 0.17, 0.11), (0.04, 0.1, 0.06)]
    specs = [(hz + 0.0, 9, 0.06, 0.16, 0.1, 0.2, 0.72), (hz + 0.07, 8, 0.09, 0.22, 0.12, 0.24, 0.52),
             (hz + 0.15, 6, 0.13, 0.3, 0.16, 0.3, 0.32), (hz + 0.26, 4, 0.2, 0.4, 0.22, 0.36, 0.12)]
    for i in range(layers):
        by, n, h0, h1, w0, w1, ha = specs[i]
        xsft = x_shift_rate * t * (0.3 + 0.7 * i / 3)
        img = karst_layer(img, by, seed + i * 11, n, h0, h1, w0, w1, cols[i], haze, ha, t=t, x_shift=xsft, veg=vegs[i],
                          mist=0.85 - 0.12 * i, mist_h=0.07 + 0.03 * i, mist_col=mc)
    if river:
        img = add_river(img, hz + 0.3, t, mood)
    if blur_px:
        img = blur(img, blur_px)
    return img


def add_river(img, y0, t, mood="mist"):
    y0p = int(y0 * H)
    out = img.copy()
    yy, xx = np.mgrid[y0p:H, 0:W].astype(np.float32)
    rel = (yy - y0p) / (H - y0p)
    cxr = W * 0.5 + W * 0.18 * np.sin(rel * 3.0 + 0.6)
    half = W * (0.12 + 0.6 * rel ** 1.3)
    m = ss(1.0, 0.8, np.abs(xx - cxr) / half)
    src_y = np.clip(2 * y0p - yy - 4, 0, H - 1)
    rip = scroll(6, 77, -t * 30, 0, octaves=3, aniso=6.0, pad=600)[y0p:H]
    refl = cv2.remap(img, np.ascontiguousarray(xx + rip * (2 + 10 * rel), np.float32), np.ascontiguousarray(src_y + rip * 2, np.float32), cv2.INTER_LINEAR)
    wc = col((0.5, 0.58, 0.58)) if mood == "mist" else col((0.35, 0.42, 0.44))
    water = refl * 0.65 + wc * 0.35
    water = blur(water, 1.5)
    bc = (0.13, 0.2, 0.14) if mood == "mist" else (0.1, 0.15, 0.12)
    hzc = (0.82, 0.86, 0.84) if mood == "mist" else (0.6, 0.65, 0.66)
    gtx = noise(H - y0p, W, 10, 88, octaves=4)
    bank = col(bc)[0] * (0.8 + 0.25 * gtx[..., None])
    hk = np.exp(-rel * 3.0)[..., None] * 0.85
    bank = bank * (1 - hk) + col(hzc)[0] * hk
    bm = ss(0.0, 0.5, rel)[..., None]
    region = out[y0p:H] * (1 - bm) + bank * bm
    region = region * (1 - m[..., None]) + water * m[..., None]
    out[y0p:H] = region
    return out


class Mist:
    def __init__(self, seed=9, scale=200, aniso=2.5):
        self.seed, self.scale, self.aniso = seed, scale, aniso

    def layer(self, t, y0, y1, amt, speed=12.0, colr=(0.9, 0.92, 0.92), lo=-0.6, hi=1.4):
        n = scroll(self.scale, self.seed, 0, t * speed - 400, aniso=self.aniso)
        y = np.linspace(0, 1, H)[:, None]
        band = ss(y0 - 0.08, y0 + 0.05, y) * ss(y1 + 0.08, y1 - 0.05, y)
        a = ss(lo, hi, n) * band * amt
        return a, col(colr)


def apply_mist(img, a, c):
    return img * (1 - a[..., None]) + c * a[..., None]


# ================= STORM =================
def storm_bg(t, seed=60, flash=0.0, flash_xy=(0.6, 0.3)):
    img = vgrad((0.04, 0.05, 0.07), (0.16, 0.18, 0.22), gamma=0.8)
    n1 = scroll(260, seed, 0, t * 18 - 400, octaves=7, aniso=1.6)
    n2 = scroll(90, seed + 1, 0, t * 9 - 400)
    dens = ss(-0.8, 1.2, n1 + 0.4 * n2)
    lit = ss(-0.5, 1.5, n1 - np.roll(n1, 6, axis=0))
    cl = col((0.1, 0.11, 0.14)) * (1 - lit[..., None]) + col((0.3, 0.32, 0.38)) * lit[..., None]
    img = img * (1 - dens[..., None] * 0.9) + cl * dens[..., None] * 0.9
    if flash > 0:
        g = radial(flash_xy[0] * W, flash_xy[1] * H, 600, power=0.9)
        illum = (0.35 + 0.65 * dens) * g * flash
        img = img + col((0.75, 0.82, 1.0)) * illum[..., None] * 1.2
    return img


def bolt(seed, x0, y0, x1, y1, w=W, h=H):
    r = np.random.default_rng(seed)
    L = np.zeros((h, w), np.float32)
    def seg(a, b, d, th):
        if d == 0:
            cv2.line(L, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 1.0, th, cv2.LINE_AA); return
        m = (a + b) / 2 + np.array([r.normal(0, np.linalg.norm(b - a) * 0.12), 0])
        seg(a, m, d - 1, th); seg(m, b, d - 1, th)
        if r.random() < 0.25 and d > 2:
            br = m + np.array([r.normal(0, 60), abs(r.normal(80, 40))])
            seg(m, br, d - 2, max(1, th - 1))
    seg(np.array([x0, y0], float), np.array([x1, y1], float), 7, 2)
    return L


class Rain:
    def __init__(self, n=900, seed=4, speed=2200, length=(18, 46), angle=0.12, alpha=0.22):
        r = np.random.default_rng(seed)
        self.x = r.uniform(0, W, n); self.y = r.uniform(0, H, n)
        self.l = r.uniform(*length, n); self.sp = speed * r.uniform(0.8, 1.2, n)
        self.a = alpha * r.uniform(0.4, 1.0, n); self.ang = angle

    def draw(self, t):
        L = np.zeros((H, W), np.float32)
        y = (self.y + self.sp * t) % (H + 100) - 50
        x = (self.x + self.sp * t * self.ang) % W
        dx = self.l * self.ang; dy = self.l
        for xi, yi, dxi, dyi, ai in zip(x, y, dx, dy, self.a):
            cv2.line(L, (int(xi), int(yi)), (int(xi + dxi), int(yi + dyi)), float(ai), 1, cv2.LINE_AA)
        return blur(L, 0.7)


# ================= FIRE =================
_FT = None


def fire_tex():
    global _FT
    if _FT is None:
        _FT = (noise(512, 2048, 60, 91, octaves=6), noise(512, 2048, 22, 92, octaves=5))
    return _FT


def fire_jet(img, ox, oy, ang_deg, L, t, intensity=1.0, w0=10, w1=170, grow=1.0, smoke=True):
    """ox,oy origin px; ang direction (deg, 0 = +x, ccw positive in image coords uses -y); L length px."""
    if intensity <= 0.01 or grow <= 0.01:
        return img
    A, B = fire_tex()
    Lc = int(L * 1.25) + 40; Hc = int(w1 * 2.4) + 40
    xs = np.arange(Lc, dtype=np.float32)[None, :]
    ys = (np.arange(Hc, dtype=np.float32) - Hc / 2)[:, None]
    s = xs / L
    Lg = grow
    hw = w0 + (w1 - w0) * np.clip(s, 0, 1.3) ** 0.85
    u1 = (xs * 0.9 - t * 900) % A.shape[1]; v1 = (ys * 0.9 + 256) % A.shape[0]
    n1 = cv2.remap(A, np.broadcast_to(u1, (Hc, Lc)).astype(np.float32), np.broadcast_to(v1, (Hc, Lc)).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    u2 = (xs * 1.3 - t * 1400) % B.shape[1]; v2 = (ys * 1.3 + 128 + t * 60) % B.shape[0]
    n2 = cv2.remap(B, np.broadcast_to(u2, (Hc, Lc)).astype(np.float32), np.broadcast_to(v2, (Hc, Lc)).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    turb = 0.6 * n1 + 0.4 * n2
    d = np.abs(ys + 0.25 * hw * n1) / hw + 0.28 * turb
    dens = ss(1.05, 0.35, d) * ss(-0.002, 0.006, s)
    front = Lg + 0.12 * n1
    dens *= ss(front, front - 0.18, s)
    temp = dens * np.clip(1.15 - 0.85 * s, 0, 1) * (0.85 + 0.3 * n2)
    core = ss(0.55, 1.0, temp)
    mid = ss(0.25, 0.65, temp)
    low = ss(0.05, 0.3, temp)
    em = (col((1.0, 0.95, 0.75))[0] * core[..., None] * 2.0 + col((1.0, 0.55, 0.12))[0] * mid[..., None] * 1.4
          + col((0.9, 0.2, 0.03))[0] * low[..., None] * 0.8) * intensity
    sm_a = (ss(0.1, 0.6, dens * (0.6 + 0.4 * n1)) * ss(0.45, 1.0, s) * 0.55 * intensity) if smoke else None
    M = cv2.getRotationMatrix2D((0, Hc / 2), ang_deg, 1.0)
    M[0, 2] += ox; M[1, 2] += oy - Hc / 2
    emw = cv2.warpAffine(em, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    out = img
    if sm_a is not None:
        smw = cv2.warpAffine(sm_a, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        smw = blur(smw, 4)
        out = out * (1 - smw[..., None]) + col((0.08, 0.06, 0.06)) * smw[..., None]
    glow = blur(emw, 10) * 0.6 + blur(emw, 40) * 0.45 + blur(emw, 120) * 0.35
    out = out + emw + glow
    return out


def sparks(img, ox, oy, ang_deg, t, n=40, seed=5, spread=0.5, speed=600, life=0.6, intensity=1.0):
    r = np.random.default_rng(seed)
    L = np.zeros((H, W), np.float32)
    a0 = math.radians(-ang_deg)
    for i in range(n):
        birth = r.uniform(0, life)
        age = (t - birth) % life
        a = a0 + r.normal(0, spread)
        v = speed * r.uniform(0.4, 1.0)
        x = ox + math.cos(a) * v * age; y = oy + math.sin(a) * v * age + 300 * age * age
        b = (1 - age / life) * intensity
        cv2.circle(L, (int(x), int(y)), 2, b, -1, cv2.LINE_AA)
    g = blur(L, 1.0) * 1.5 + blur(L, 5) * 0.8
    return img + col((1.0, 0.65, 0.2)) * g[..., None]


# ================= PUFFY CLOUD SEA (painted) =================
_PUFFS = {}


def puff_sprites(seed=0, nvar=8, w=320, h=200, lit=(1.0, 0.88, 0.74), shade=(0.5, 0.45, 0.58), rim=(1.0, 0.86, 0.66)):
    key = (seed, nvar, lit, shade, rim)
    if key in _PUFFS:
        return _PUFFS[key]
    out = []
    for v in range(nvar):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2, h * 0.64
        d = np.sqrt(((xx - cx) / (w * 0.47)) ** 2 + ((yy - cy) / (h * 0.52)) ** 2)
        n1 = noise(h, w, 70, seed * 31 + v, octaves=3)
        n2 = noise(h, w, 26, seed * 31 + v + 100, octaves=2)
        top_bias = np.clip((cy - yy) / h, 0, 1)
        field = 1 - d + 0.2 * n1 * (0.3 + top_bias) + 0.05 * n2
        flat = ss(-0.05, 0.12, (h * 0.92 - yy) / h)
        a = ss(0.0, 0.18, field) * flat
        vert = np.clip(1 - yy / (h * 0.9), 0, 1)
        bright = np.clip(0.18 + 0.75 * vert ** 1.4 + 0.12 * n1, 0, 1)
        c = col(shade)[0] * (1 - bright[..., None]) + col(lit)[0] * bright[..., None]
        topedge = np.clip(a - np.roll(a, 5, axis=0), 0, 1)
        topedge = cv2.GaussianBlur(topedge, (0, 0), 2.0) * vert
        c = c + col(rim)[0] * topedge[..., None] * 0.35
        rgba = np.dstack([c * a[..., None], a]).astype(np.float32)
        out.append(rgba)
    _PUFFS[key] = out
    return out


def cloud_sea_puffs(img, hz, sun_x, seed=1, density=1.0, lit=(1.0, 0.88, 0.74), shade=(0.5, 0.45, 0.58),
                    haze=(1.0, 0.84, 0.68), deep=(0.42, 0.38, 0.5), drift=0.0, count=650):
    r = np.random.default_rng(seed)
    yh = hz * H
    canvas = img.copy()
    under = vgrad(haze, deep, h=H - int(yh), w=W, gamma=0.6)
    canvas[int(yh):] = under
    sprites = puff_sprites(seed, lit=lit, shade=shade)
    items = []
    for k in range(int(count * density)):
        u = r.uniform(0, 1) ** 1.6
        y = yh + 4 + u * (H - yh) * 1.15
        depth = (y - yh) / (H - yh)
        sz = 50 + 1300 * depth ** 1.3
        x = r.uniform(-0.3 * W, 1.3 * W) + drift * (20 + 200 * depth)
        items.append((y, x, sz, r.integers(0, len(sprites)), depth))
    items.sort(key=lambda t: t[0])
    for y, x, sz, vi, depth in items:
        sp = sprites[vi]
        w_ = max(4, int(sz)); h_ = max(3, int(sz * 0.55))
        s = cv2.resize(sp, (w_, h_), interpolation=cv2.INTER_AREA if w_ < sp.shape[1] else cv2.INTER_LINEAR)
        hk = float(np.clip(1 - depth * 3.2, 0, 1)) ** 1.5 * 0.85
        sunb = math.exp(-((x - sun_x) / (W * 0.35)) ** 2) * (1 - depth) ** 2
        tint = col(haze)[0] * hk
        s = s.copy()
        s[..., :3] = s[..., :3] * (1 - hk) + tint * s[..., 3:4] + col((1.0, 0.85, 0.6))[0] * s[..., 3:4] * sunb * 0.25
        x0 = int(x - w_ / 2); y0 = int(y - h_ * 0.62)
        xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w_), min(H, y0 + h_)
        if xb <= xa or yb <= ya:
            continue
        sub = s[ya - y0:yb - y0, xa - x0:xb - x0]
        reg = canvas[ya:yb, xa:xb]
        canvas[ya:yb, xa:xb] = sub[..., :3] + reg * (1 - sub[..., 3:4])
    band = slice(max(0, int(yh) - 5), min(H, int(yh) + 5))
    canvas[band] = blur(canvas[band], 2.5)
    return canvas
