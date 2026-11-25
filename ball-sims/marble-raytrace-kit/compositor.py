"""Paints glossy marbles onto a path-traced G-buffer, one frame at a time, in numpy.

The static set (stairs, spiral, tray, floor) is path-traced once by boxtrace/meshtrace at 2x size. Each frame only
redoes the small regions around marbles: the marbles cast analytic soft shadows and contact AO onto the set, are
ray-traced as spheres with an ambient cube, key highlight and sky reflection, hide behind the set by depth, sit
behind glass walls, and get colored light from glowing tiles. Glowing tiles/segments add emissive light plus a
bloom halo. Text (round titles, watermark) is drawn last. A frame takes 0.1-1 s on one core.

Usage (see the templates for complete adapters):
    import compositor as C
    C.configure(scene_module)                       # camera, light and look come from the scene module
    comp = C.Compositor(gprefix, pos, vis, colors_srgb, glows, titles=..., watermark=..., env_fn=..., spill_fn=...)
    img = comp.render(frame_index)                  # uint8 1080x1920x3
    C.render_video(comp, f0, f1, "part.mp4")
"""
import glob
import math
import os
import subprocess
import sys
import time

import numpy as np
import scipy.ndimage as ndi
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ===================================================================== SETTINGS (shipped values)
F0 = 0.05                 # marble specular reflectance at normal incidence
SH_MAXD = 10.0            # marble shadows fade out by this distance (marble radii)
AO_MAXD = 3.0             # marble contact AO reach
TITLE_Y = 0.118           # round title center, fraction of frame height
WATERMARK_Y = 0.868
TITLE_SIZE = 96           # px, Montserrat weight 800, white, soft shadow
WATERMARK_SIZE = 44       # px, weight 650, 150/255 alpha
FONT_NAME = "Montserrat[wght].ttf"
FONT_DIRS = [os.path.join(HERE, "fonts"), os.path.join(HERE, "..", "..", "shared", "fonts"),
             os.path.expanduser("~/.fonts"), os.path.expanduser("~/Library/Fonts"),
             "/usr/share/fonts/truetype/google-fonts/ofl/montserrat"]
# ================================================================= END SETTINGS

S = None


def configure(scene):
    """Reads camera, light and look from a scene module (see look.py) and precomputes per-camera tables."""
    global S, W, H, W2, H2, R, CAM, FWD, RIGHT, UP, TH, ASP, FOC2, L, LANG, LCOL, A_COL, B_ROW, ESKY, AMB_DIRS
    global CONE, _PB1, _PB2, FWD32, RIGHT32, UP32, CAM32, A32, B32, BOXES, BMN, BMX, BROT, BPIV, BALB
    S = scene
    W, H = S.W, S.H
    W2, H2 = 2 * W, 2 * H
    R = S.R
    CAM, FWD, RIGHT, UP = S.camera()
    TH = math.tan(S.CAM_FOVY / 2)
    ASP = W / H
    FOC2 = (H2 / 2) / TH
    L = S.light_dir()
    LANG = S.LIGHT_ANG
    LCOL = S.LIGHT_COL
    A_COL = ((np.arange(W2) + 0.5) / W2 * 2 - 1 + S.CAM_SHIFT[0]) * TH * ASP
    B_ROW = (1 - (np.arange(H2) + 0.5) / H2 * 2 + S.CAM_SHIFT[1]) * TH
    BOXES = S.boxes() if hasattr(S, "boxes") else []
    if BOXES:
        BMN = np.array([b["mn"] for b in BOXES])
        BMX = np.array([b["mx"] for b in BOXES])
        BROT = np.array([b["rot"] for b in BOXES])
        BPIV = np.array([b["piv"] for b in BOXES])
        BALB = np.array([b["alb"] for b in BOXES])
    ESKY = _esky_up()
    AMB_DIRS = fib_dirs(96)
    CONE = cone_dirs(36)
    _PB1 = np.cross(L, [0.0, 0.0, 1.0])
    _PB1 /= np.linalg.norm(_PB1)
    _PB2 = np.cross(L, _PB1)
    FWD32, RIGHT32, UP32, CAM32 = (v.astype(np.float32) for v in (FWD, RIGHT, UP, CAM))
    A32, B32 = A_COL.astype(np.float32), B_ROW.astype(np.float32)


def sky_rad(d):
    h = np.sqrt(np.clip(d[..., 1], 0, 1))[..., None]
    return S.SKY_H * (1 - h) + S.SKY_Z * h


def _esky_up():
    ct = (np.arange(200) + 0.5) / 200
    ph = 2 * np.pi * (np.arange(400) + 0.5) / 400
    C, P = np.meshgrid(ct, ph, indexing="ij")
    st = np.sqrt(1 - C * C)
    d = np.stack([st * np.cos(P), C, st * np.sin(P)], -1)
    return (sky_rad(d) * C[..., None]).mean((0, 1)) * 2 * np.pi


def trace_np(o, d, any_hit=False):
    """Rays against the scene's boxes and the floor (box scenes only). Returns t, box index (-1 floor, -2 miss), normal."""
    n = len(d)
    best = np.full(n, np.inf)
    idx = np.full(n, -2)
    nrm = np.zeros((n, 3))
    o = np.broadcast_to(o, d.shape)
    for i in range(len(BOXES)):
        if BROT[i] != 0:
            c, s = math.cos(BROT[i]), math.sin(BROT[i])
            ox, oy = o[:, 0] - BPIV[i, 0], o[:, 1] - BPIV[i, 1]
            ol = np.stack([c * ox + s * oy, -s * ox + c * oy, o[:, 2] - BPIV[i, 2]], 1)
            dl = np.stack([c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1], d[:, 2]], 1)
        else:
            ol, dl = o, d
        dd = np.where(np.abs(dl) < 1e-12, 1e-12, dl)
        inv = 1.0 / dd
        ta = (BMN[i] - ol) * inv
        tb = (BMX[i] - ol) * inv
        t0 = np.minimum(ta, tb)
        t1 = np.maximum(ta, tb)
        tn = t0.max(1)
        tf = t1.min(1)
        hit = (tn <= tf) & (tn > 1e-6) & (tn < best)
        if hit.any():
            best[hit] = tn[hit]
            idx[hit] = i
            ax = t0.argmax(1)
            sg = np.where(ta[np.arange(n), ax] > tb[np.arange(n), ax], 1.0, -1.0)
            nl = np.zeros((n, 3))
            nl[np.arange(n), ax] = sg
            if BROT[i] != 0:
                nw = np.stack([c * nl[:, 0] - s * nl[:, 1], s * nl[:, 0] + c * nl[:, 1], nl[:, 2]], 1)
            else:
                nw = nl
            nrm[hit] = nw[hit]
    fl = d[:, 1] < -1e-9
    tfl = np.where(fl, -o[:, 1] / np.where(fl, d[:, 1], -1), np.inf)
    hit = fl & (tfl > 1e-6) & (tfl < best)
    best[hit] = tfl[hit]
    idx[hit] = -1
    nrm[hit] = [0, 1, 0]
    return best, idx, nrm


def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], 1)


def cone_dirs(n):
    b1 = np.cross(L, [1.0, 0, 0])
    b1 /= np.linalg.norm(b1)
    b2 = np.cross(L, b1)
    k = int(round(math.sqrt(n)))
    u = (np.arange(k)[:, None] + 0.5 + 0 * np.arange(k)[None]) / k
    v = (np.arange(k)[None] + 0.5 + 0 * np.arange(k)[:, None]) / k
    u, v = u.ravel(), v.ravel()
    ct = 1 - u * (1 - math.cos(LANG))
    st = np.sqrt(1 - ct * ct)
    ph = 2 * np.pi * v
    return L[None] * ct[:, None] + b1[None] * (st * np.cos(ph))[:, None] + b2[None] * (st * np.sin(ph))[:, None]


AXES = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)


def ray_sphere_block(o, d, c):
    oc = o - c
    b = (oc * d).sum(-1)
    cc = (oc * oc).sum(-1) - R * R
    disc = b * b - cc
    return (disc > 0) & (-b - np.sqrt(np.maximum(disc, 0)) > 1e-4)


def shadow_reach(c):
    offs = np.array([[0, 0, 0], _PB1, -_PB1, _PB2, -_PB2]) * 0.98 * R
    o = c[None] + offs
    t, _, _ = trace_np(o, np.broadcast_to(-L, o.shape).copy())
    t = np.where(np.isfinite(t), t, SH_MAXD)
    return float(min(SH_MAXD, t.max() + 0.6))


def marble_env(c):
    """Lighting at a marble center in a box scene: (key visibility, 6x3 ambient cube, gap below, shadow reach)."""
    t, idx, nrm = trace_np(c[None], CONE)
    vis = float(np.isinf(t).mean())
    d = AMB_DIRS
    t, idx, nrm = trace_np(c[None], d)
    rad = np.zeros((len(d), 3))
    miss = idx == -2
    rad[miss] = sky_rad(d[miss])
    hitm = ~miss
    if hitm.any():
        q = c[None] + d[hitm] * t[hitm, None]
        nq = nrm[hitm]
        ii = idx[hitm]
        alb = np.where(ii[:, None] == -1, S.FLOOR_LIN[None], BALB[np.maximum(ii, 0)])
        qo = q + nq * 1e-3
        ts, _, _ = trace_np(qo, np.broadcast_to(L, qo.shape).copy())
        vq = np.isinf(ts).astype(float)
        vq *= ~ray_sphere_block(qo, L[None], c[None])
        ndl = np.clip(nq @ L, 0, None)
        rad[hitm] = alb / np.pi * (LCOL[None] * (ndl * vq)[:, None] + ESKY[None] * (0.5 + 0.5 * nq[:, 1:2]) * 0.8)
    cube = np.stack([(rad * np.clip(d @ a, 0, None)[:, None]).sum(0) * (4 * np.pi / len(d)) for a in AXES])
    td, _, _ = trace_np(c[None], np.array([[0.0, -1.0, 0.0]]))
    gap = float(td[0] - R) if np.isfinite(td[0]) else 99.0
    return vis, cube, gap, shadow_reach(c)


def overlap_frac(r1, r2, dd):
    out = np.zeros_like(dd)
    full = dd <= np.abs(r1 - r2)
    out[full] = np.minimum(r1, r2[full]) ** 2 / (r1 * r1)
    part = (~full) & (dd < r1 + r2)
    if part.any():
        d = dd[part]
        rr = r2[part]
        c1 = np.clip((d * d + r1 * r1 - rr * rr) / (2 * d * r1), -1, 1)
        c2 = np.clip((d * d + rr * rr - r1 * r1) / (2 * d * rr), -1, 1)
        k = (-d + r1 + rr) * (d + r1 - rr) * (d - r1 + rr) * (d + r1 + rr)
        out[part] = (r1 * r1 * np.arccos(c1) + rr * rr * np.arccos(c2) - 0.5 * np.sqrt(np.maximum(k, 0))) / (
                np.pi * r1 * r1)
    return out


def sphere_shadow(P, c, maxd=SH_MAXD):
    d = c[None] - P
    dist = np.sqrt((d * d).sum(-1))
    dist = np.maximum(dist, 1e-4)
    cg = (d @ L) / dist
    gam = np.arccos(np.clip(cg, -1, 1))
    asn = np.arcsin(np.clip(R / dist, 0, 1))
    fr = overlap_frac(LANG, asn, gam)
    fr *= np.clip((maxd - dist) / 3.0, 0, 1)
    return fr, d, dist


def sphere_ao(N, d, dist):
    occ = np.clip((N * d).sum(-1) / dist, 0, 1) * (R / np.maximum(dist, R)) ** 2
    return occ * np.clip((AO_MAXD - dist) / 0.9, 0, 1)


def proj(p):
    d = p - CAM
    zc = d @ FWD
    nx = (d @ RIGHT) / (zc * TH * ASP) - S.CAM_SHIFT[0]
    ny = (d @ UP) / (zc * TH) - S.CAM_SHIFT[1]
    return (nx + 1) * 0.5 * W2, (1 - ny) * 0.5 * H2, zc


def bbox_sphere(c, rad, margin=1.18):
    x, y, z = proj(c)
    if z <= 1:
        return None
    r = rad * FOC2 / z * margin + 3
    return [x - r, y - r, x + r, y + r]


def ubox(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def clipbox(b):
    if b is None:
        return None
    x0 = int(max(0, math.floor(b[0]))) // 2 * 2
    y0 = int(max(0, math.floor(b[1]))) // 2 * 2
    x1 = int(min(W2, math.ceil(b[2])))
    y1 = int(min(H2, math.ceil(b[3])))
    x1 = min(W2, (x1 + 1) // 2 * 2)
    y1 = min(H2, (y1 + 1) // 2 * 2)
    if x1 <= x0 or y1 <= y0:
        return None
    return [x0, y0, x1, y1]


def inter(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def merge_boxes(bs):
    bs = [list(b) for b in bs if b is not None]
    changed = True
    while changed:
        changed = False
        out = []
        while bs:
            a = bs.pop()
            i = 0
            while i < len(bs):
                if inter(a, bs[i]):
                    b = bs.pop(i)
                    a = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    changed = True
                    i = 0
                else:
                    i += 1
            out.append(a)
        bs = out
    return bs


def dirs_block(x0, y0, x1, y1):
    d = FWD32[None, None] + A32[x0:x1][None, :, None] * RIGHT32[None, None] + B32[y0:y1][:, None, None] * UP32[None, None]
    return d / np.sqrt((d * d).sum(-1, keepdims=True))


def down2(a):
    h, w = a.shape[:2]
    return a.reshape(h // 2, 2, w // 2, 2, *a.shape[2:]).mean((1, 3))


def tonemap(lin):
    x = np.maximum(lin, 0) * S.EXPOSURE
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    y = np.clip(y, 0, 1)
    return np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(y, 1 / 2.4) - 0.055)


def find_font():
    env = os.environ.get("MONTSERRAT_TTF")
    if env and os.path.exists(env):
        return env
    for d in FONT_DIRS:
        p = os.path.join(d, FONT_NAME)
        if os.path.exists(p):
            return p
    hits = glob.glob("/usr/share/fonts/**/Montserrat*wght*.ttf", recursive=True)
    if hits:
        return hits[0]
    raise SystemExit("Montserrat[wght].ttf not found: run ../marble-raytrace-kit/get_fonts.py or set MONTSERRAT_TTF")


class Compositor:
    """glows: one dict per glowing element (tile or spiral segment), in element order k:
         oid    object id in the G-buffer (_I.u8) whose pixels light up
         col    linear RGB glow color
         events [(t, amplitude, decay_s)]: 30 ms attack then exponential decay
         hold   [(t0, t1)] optional: stays lit at hold_level while a marble rolls over it (0.2 s release)
       env_fn(frame, marble, center) -> (vis, cube, gap, reach) or None to skip; default traces the box scene.
       hidden_fn(marble, center) -> True to skip a marble (e.g. inside a feeder tube).
       spill_fn(k, center) -> point on element k that lights a nearby marble, or None."""

    def __init__(self, gprefix, pos, vis, colors_srgb, glows, titles=(), watermark=None, env_fn=None,
                 hidden_fn=None, spill_fn=None, hold_level=0.30):
        t = time.time()
        self.D = np.fromfile(gprefix + "_D.f32", np.float32).reshape(H2, W2, 3)
        self.A = np.fromfile(gprefix + "_A.f32", np.float32).reshape(H2, W2, 3)
        self.O = np.fromfile(gprefix + "_O.f32", np.float32).reshape(H2, W2, 3)
        self.Z = np.fromfile(gprefix + "_Z.f32", np.float32).reshape(H2, W2)
        self.N = np.fromfile(gprefix + "_N.f32", np.float32).reshape(H2, W2, 3)
        self.I = np.fromfile(gprefix + "_I.u8", np.uint8).reshape(H2, W2)
        self.GA = None
        if os.path.exists(gprefix + "_GA.f32"):
            self.GA = np.fromfile(gprefix + "_GA.f32", np.float32).reshape(H2, W2)
            self.GC = np.fromfile(gprefix + "_GC.f32", np.float32).reshape(H2, W2, 3)
            self.GZ = np.fromfile(gprefix + "_GZ.f32", np.float32).reshape(H2, W2)
            self.L1 = down2((self.D + self.A + self.O) * (1 - self.GA[..., None]) + self.GC).astype(np.float32)
        else:
            self.L1 = down2(self.D + self.A + self.O).astype(np.float32)
        sy, sx = np.mgrid[0:H, 0:W]
        sx = (sx + 0.5) / W
        sy = (sy + 0.5) / H
        self.vig = S.vignette(sx, sy).astype(np.float32)[..., None]
        self.static8 = (tonemap(self.L1 * self.vig) * 255 + 0.5).astype(np.uint8)
        self.pos = np.asarray(pos).astype(np.float64)
        self.vis = np.asarray(vis)
        self.cols = np.array([S.srgb2lin(c) for c in colors_srgb])
        self.nm = len(self.cols)
        self.env_fn = env_fn
        self.hidden_fn = hidden_fn
        self.spill_fn = spill_fn
        self.hold_level = hold_level
        self.env_cache = {}
        self._glows(glows)
        self._text(titles, watermark)
        print(f"compositor init {time.time() - t:.1f}s", file=sys.stderr)

    def _glows(self, glows):
        self.tmask, self.tbox, self.halo, self.hbox = [], [], [], []
        self.glow_col = [np.asarray(g["col"], np.float64) for g in glows]
        self.gev = [list(g.get("events", [])) for g in glows]
        self.occ = [list(g.get("hold", [])) for g in glows]
        for g in glows:
            m2 = (self.I == g["oid"]).astype(np.float32)
            m1 = down2(m2)
            ys, xs = np.nonzero(m1 > 0)
            if len(ys) == 0:
                self.tbox.append(None)
                self.tmask.append(None)
                self.hbox.append(None)
                self.halo.append(None)
                continue
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            self.tbox.append((y0, y1, x0, x1))
            self.tmask.append(m1[y0:y1, x0:x1][..., None])
            pad = 70
            hy0, hy1, hx0, hx1 = max(0, y0 - pad), min(H, y1 + pad), max(0, x0 - pad), min(W, x1 + pad)
            sub = m1[hy0:hy1, hx0:hx1]
            hal = ndi.gaussian_filter(sub, 16) * 0.75 + ndi.gaussian_filter(sub, 5) * 0.35
            self.hbox.append((hy0, hy1, hx0, hx1))
            self.halo.append(hal[..., None].astype(np.float32))

    def glow(self, k, t):
        s = 0.0
        for (th, a, dec) in self.gev[k]:
            dt = t - th
            if dt < -0.001 or dt > 3.0:
                continue
            if dt < 0.03:
                s += a * max(dt, 0) / 0.03
            else:
                s += a * math.exp(-(dt - 0.03) / dec)
        for (a, b) in self.occ[k]:
            if a <= t <= b:
                s += self.hold_level * min(1.0, (t - a) / 0.03)
            elif b < t < b + 0.2:
                s += self.hold_level * (1 - (t - b) / 0.2)
        return min(s, 1.6)

    def _font(self, size, wght):
        f = ImageFont.truetype(find_font(), size)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        return f

    def _sprite(self, text, size, wght, fill, shadow_alpha, stroke, blur, offset):
        f = self._font(size, wght)
        bb = f.getbbox(text, stroke_width=stroke)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        pad = int(blur * 3 + 12 + abs(offset))
        cw, ch = tw + 2 * pad, th + 2 * pad
        sh = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(sh).text((pad - bb[0] + offset * 0.4, pad - bb[1] + offset), text, font=f, fill=255,
                                stroke_width=stroke + 1, stroke_fill=255)
        sh = sh.filter(ImageFilter.GaussianBlur(blur))
        fg = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        dr = ImageDraw.Draw(fg)
        dr.text((pad - bb[0], pad - bb[1]), text, font=f, fill=fill, stroke_width=stroke,
                stroke_fill=(28, 34, 44, 255) if stroke else None)
        out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        shimg = Image.new("RGBA", (cw, ch), (12, 18, 28, 0))
        shimg.putalpha(sh.point(lambda v: int(v * shadow_alpha)))
        out = Image.alpha_composite(out, shimg)
        out = Image.alpha_composite(out, fg)
        return np.asarray(out).astype(np.float32) / 255.0

    def _text(self, titles, watermark):
        self.titles = []
        for tt in titles:
            scales = {}
            for s in (0.70, 0.78, 0.86, 0.94, 1.00, 1.04, 1.08, 1.12):
                scales[s] = self._sprite(tt["text"], int(round(TITLE_SIZE * s)), 800, (255, 255, 255, 255), 0.75, 0,
                                         7 * s, 5 * s)
            self.titles.append((tt["t"], scales))
        self.wm = None
        if watermark:
            self.wm = self._sprite(watermark, WATERMARK_SIZE, 650, (236, 242, 250, 150), 0.45, 0, 3, 2)

    def blit(self, out, spr, cx, cy, alpha=1.0):
        h, w = spr.shape[:2]
        x0 = int(round(cx - w / 2))
        y0 = int(round(cy - h / 2))
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(W, x0 + w), min(H, y0 + h)
        if x1c <= x0c or y1c <= y0c:
            return
        s = spr[sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)]
        a = s[..., 3:4] * alpha
        reg = out[y0c:y1c, x0c:x1c].astype(np.float32)
        out[y0c:y1c, x0c:x1c] = (reg * (1 - a) + s[..., :3] * 255 * a + 0.5).astype(np.uint8)

    def title_sprite(self, t):
        cur = 0
        for i, (ts, _) in enumerate(self.titles):
            if t >= ts:
                cur = i
        ts, scales = self.titles[cur]
        dt = t - ts
        if cur == 0:
            return scales[1.00], 1.0
        keys = [(0.00, 0.70), (0.05, 0.86), (0.10, 1.04), (0.15, 1.12), (0.21, 1.08), (0.27, 1.00)]
        if dt >= keys[-1][0]:
            return scales[1.00], 1.0
        for (a, sa), (b, sb) in zip(keys[:-1], keys[1:]):
            if a <= dt < b:
                s = sa + (sb - sa) * (dt - a) / (b - a)
                break
        best = min(scales.keys(), key=lambda k: abs(k - s))
        return scales[best], min(1.0, 0.35 + dt / 0.08)

    def marble_state(self, f):
        t = f / S.FPS
        act = []
        for m in range(self.nm):
            if not self.vis[f, m]:
                continue
            c = self.pos[f, m]
            if c[0] < -45:
                continue
            if self.hidden_fn is not None and self.hidden_fn(m, c):
                continue
            if self.env_fn is not None:
                env = self.env_fn(f, m, c)
                if env is None:
                    continue
            else:
                key = (m, tuple(np.round(c, 4)))
                if key not in self.env_cache:
                    self.env_cache[key] = marble_env(c)
                env = self.env_cache[key]
            act.append((m, c, env))
        return t, act

    def render(self, f, title=True, watermark=True):
        t, act = self.marble_state(f)
        frame = self.L1.copy()
        alpha1 = None
        dirty = []
        infl = []
        disk = []
        aob, shb = [], []
        for (m, c, env) in act:
            reach = env[3]
            b_ao = clipbox(bbox_sphere(c, AO_MAXD))
            end = c - L * reach
            b_sh = clipbox(ubox(bbox_sphere(c, 1.3), bbox_sphere(end, reach * math.tan(LANG + 0.06) + R * 1.25)))
            aob.append(b_ao)
            shb.append(b_sh)
            infl.append(ubox(b_ao, b_sh))
            disk.append(clipbox(bbox_sphere(c, R)))
        rects = merge_boxes([ubox(a, b) for a, b in zip(infl, disk) if (a is not None or b is not None)])
        glows = [self.glow(k, t) for k in range(len(self.gev))]
        for rc in rects:
            x0, y0, x1, y1 = rc
            Zr = self.Z[y0:y1, x0:x1]
            valid = Zr < 1e29
            dirs = dirs_block(x0, y0, x1, y1)
            P = CAM32[None, None] + dirs * np.where(valid, Zr, 0)[..., None]
            Nr = self.N[y0:y1, x0:x1]
            Sf = np.ones(Zr.shape, np.float32)
            Af = np.ones(Zr.shape, np.float32)
            for i, (m, c, env) in enumerate(act):
                c32 = c.astype(np.float32)
                for kind, b in (("sh", shb[i]), ("ao", aob[i])):
                    if b is None or not inter(b, rc):
                        continue
                    bx0, by0, bx1, by1 = max(b[0], x0), max(b[1], y0), min(b[2], x1), min(b[3], y1)
                    if bx1 <= bx0 or by1 <= by0:
                        continue
                    sl = (slice(by0 - y0, by1 - y0), slice(bx0 - x0, bx1 - x0))
                    v = valid[sl]
                    if not v.any():
                        continue
                    Pp = P[sl][v]
                    if kind == "sh":
                        fr, d, dist = sphere_shadow(Pp, c32, env[3] + 3.0)
                        s_sub = Sf[sl]
                        s_sub[v] *= (1 - fr).astype(np.float32)
                    else:
                        d = c32[None] - Pp
                        dist = np.maximum(np.sqrt((d * d).sum(-1)), 1e-4)
                        occ = sphere_ao(Nr[sl][v], d, dist)
                        a_sub = Af[sl]
                        a_sub[v] *= (1 - 0.88 * occ).astype(np.float32)
            Lc = self.D[y0:y1, x0:x1] * Sf[..., None] + self.A[y0:y1, x0:x1] * Af[..., None] + self.O[y0:y1, x0:x1]
            zb = Zr.copy()
            acov = np.zeros(Zr.shape, np.float32)
            order = sorted(range(len(act)), key=lambda i: -proj(act[i][1])[2])
            for i in order:
                b = disk[i]
                if b is None or not inter(b, rc):
                    continue
                self.draw_marble(act, i, b, rc, dirs, Lc, zb, acov, glows)
            if self.GA is not None:
                gm = (self.GZ[y0:y1, x0:x1] < zb).astype(np.float32)
                ga = self.GA[y0:y1, x0:x1] * gm
                Lc = Lc * (1 - ga[..., None]) + self.GC[y0:y1, x0:x1] * gm[..., None]
            l1 = down2(Lc)
            frame[y0 // 2:y1 // 2, x0 // 2:x1 // 2] = l1
            if alpha1 is None:
                alpha1 = {}
            alpha1[tuple(rc)] = down2(acov)
            dirty.append((y0 // 2, y1 // 2, x0 // 2, x1 // 2))
        for k in range(len(glows)):
            g = glows[k]
            if g < 0.004 or self.tbox[k] is None:
                continue
            y0, y1, x0, x1 = self.tbox[k]
            m = self.tmask[k]
            if alpha1:
                cover = np.zeros((y1 - y0, x1 - x0), np.float32)
                for rc, a in alpha1.items():
                    ry0, ry1, rx0, rx1 = rc[1] // 2, rc[3] // 2, rc[0] // 2, rc[2] // 2
                    iy0, iy1, ix0, ix1 = max(y0, ry0), min(y1, ry1), max(x0, rx0), min(x1, rx1)
                    if iy1 > iy0 and ix1 > ix0:
                        cover[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = np.maximum(
                            cover[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0], a[iy0 - ry0:iy1 - ry0, ix0 - rx0:ix1 - rx0])
                m = m * (1 - cover[..., None])
            col = self.glow_col[k] * 1.6 + 0.04
            frame[y0:y1, x0:x1] += m * col * g
            hy0, hy1, hx0, hx1 = self.hbox[k]
            frame[hy0:hy1, hx0:hx1] += self.halo[k] * self.glow_col[k] * g * 0.95
            dirty.append((hy0, hy1, hx0, hx1))
        out = self.static8.copy()
        for (x0, y0, x1, y1) in merge_boxes([[d[2], d[0], d[3], d[1]] for d in dirty]):
            out[y0:y1, x0:x1] = (tonemap(frame[y0:y1, x0:x1] * self.vig[y0:y1, x0:x1]) * 255 + 0.5).astype(np.uint8)
        if title and self.titles:
            spr, a = self.title_sprite(t)
            self.blit(out, spr, W / 2, H * TITLE_Y, a)
        if watermark and self.wm is not None:
            self.blit(out, self.wm, W / 2, H * WATERMARK_Y, 1.0)
        return out

    def draw_marble(self, act, i, b, rc, dirs, Lc, zb, acov, glows):
        m, c, (vis_c, cube, gap, _reach) = act[i]
        x0, y0, x1, y1 = rc
        bx0, by0, bx1, by1 = max(b[0], x0), max(b[1], y0), min(b[2], x1), min(b[3], y1)
        if bx1 <= bx0 or by1 <= by0:
            return
        sl = (slice(by0 - y0, by1 - y0), slice(bx0 - x0, bx1 - x0))
        d = dirs[sl]
        oc = CAM - c
        bb = (d * oc).sum(-1)
        cc = oc @ oc
        q2 = np.maximum(cc - bb * bb, 0)
        q = np.sqrt(q2)
        tmid = -bb
        pxw = tmid * (2 * TH / H2)
        alpha = np.clip(0.5 + (R - q) / pxw, 0, 1)
        if alpha.max() <= 0:
            return
        thit = tmid - np.sqrt(np.maximum(R * R - q2, 0))
        vis = (thit < zb[sl]).astype(np.float32)
        a = alpha * vis
        sel = a > 0
        if not sel.any():
            return
        ds = d[sel]
        th = thit[sel]
        P = CAM[None] + ds * th[:, None]
        n = P - c[None]
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        alb = self.cols[m]
        Sv = np.full(len(P), vis_c)
        Av = np.ones(len(P))
        for j, (mj, cj, _) in enumerate(act):
            if j == i:
                continue
            dvec = cj - c
            dc = np.linalg.norm(dvec)
            near_ao = dc < AO_MAXD + 1.0
            can_sh = dc < SH_MAXD and (dvec @ L) > -0.2 * dc
            if not (near_ao or can_sh):
                continue
            dv = cj[None] - P
            dist = np.maximum(np.sqrt((dv * dv).sum(-1)), 1e-4)
            if can_sh:
                fr, _, _ = sphere_shadow(P, cj)
                Sv *= 1 - fr
            if near_ao:
                Av *= 1 - 0.85 * sphere_ao(n, dv, dist)
        ndl = np.clip(n @ L, 0, None)
        nn = n * n
        E = (nn[:, 0:1] * np.where(n[:, 0:1] > 0, cube[0], cube[1]) +
             nn[:, 1:2] * np.where(n[:, 1:2] > 0, cube[2], cube[3]) +
             nn[:, 2:3] * np.where(n[:, 2:3] > 0, cube[4], cube[5]))
        kdark = 1 - 0.55 * np.clip(-n[:, 1], 0, 1) ** 2 * math.exp(-max(gap, 0) / 0.7)
        diff = alb[None] / np.pi * (LCOL[None] * (ndl * Sv)[:, None] + E * (Av * kdark)[:, None])
        v = -ds
        hv = L[None] + v
        hv /= np.linalg.norm(hv, axis=1, keepdims=True)
        ndh = np.clip((n * hv).sum(1), 0, 1)
        ndv = np.clip((n * v).sum(1), 0, 1)
        Fr = F0 + (1 - F0) * (1 - ndv) ** 5
        spec = (0.85 * (420 + 8) / (8 * np.pi) * ndh ** 420 + 0.22 * (36 + 8) / (8 * np.pi) * ndh ** 36) * F0 * 1.0
        spec = spec * Sv * ndl
        r = ds - 2 * (ds * n).sum(1, keepdims=True) * n
        env = np.where(r[:, 1:2] >= 0, sky_rad(r), cube[3][None] / np.pi * 1.0)
        refl = Fr[:, None] * env * (0.35 + 0.65 * Av[:, None])
        col = diff + spec[:, None] * LCOL[None] + refl
        for k in range(len(glows)):
            g = glows[k]
            if g < 0.01 or self.spill_fn is None:
                continue
            qp = self.spill_fn(k, c)
            if qp is None:
                continue
            dv = qp[None] - P
            dist = np.linalg.norm(dv, axis=1)
            if dist.min() > 5.0:
                continue
            u = dv / dist[:, None]
            w = np.clip((n * u).sum(1), 0, 1) / (1 + (dist / 1.2) ** 2)
            col += alb[None] * self.glow_col[k][None] * (g * 1.6 * w)[:, None]
        sub = Lc[sl]
        aa = a[sel][:, None]
        sub[sel] = sub[sel] * (1 - aa) + col * aa
        zsub = zb[sl]
        upd = sel & (a > 0.5)
        zsub[upd] = thit[upd]
        asub = acov[sl]
        asub[sel] = np.maximum(asub[sel], a[sel])


def render_video(comp, f0, f1, outp, crf=17):
    """Renders frames [f0, f1) to an H.264 mp4 (written to a .part.mp4 first, renamed when ffmpeg exits 0)."""
    tmp = outp[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
           str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt",
           "yuv420p", "-g", "60", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        p.stdin.write(comp.render(f).tobytes())
        if (f - f0) % 60 == 0:
            print(f"[{f0}-{f1}] frame {f} elapsed {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    p.stdin.close()
    rc = p.wait()
    if rc == 0:
        os.replace(tmp, outp)
    print(f"done {outp} rc={rc} {time.time() - t0:.0f}s", file=sys.stderr)
    return rc
