"""Text and HUD over each frame (PIL, Montserrat ExtraBold from ../marble-raytrace-kit/fonts): the two-line title,
a row of colour chips that get an X when that marble drops, "<COLOUR> IS OUT!" (DOUBLE/TRIPLE when they come in a
burst), SO CLOSE! next to a marble that skims the hole, FINAL 2!, and the winner box with confetti.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import settings as C

HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS = {}
_CROWN = []


def crown_sprite():
    """The channel's gold crown (../crown-icon, drawn with skia) as a PIL RGBA image, 5x the base size."""
    if not _CROWN:
        import skia
        sys.path.insert(0, os.path.join(HERE, "..", "crown-icon"))
        from crown_icon import draw_crown
        s = 5.0
        w, h = int(112 * s), int(86 * s)
        surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        cv = surf.getCanvas()
        cv.clear(skia.ColorTRANSPARENT)
        draw_crown(cv, w / 2, h / 2 + 4 * s, s=s, glow=1.0)
        a = surf.makeImageSnapshot().toarray().astype(np.float32)
        al = a[..., 3:4]
        a[..., :3] = np.where(al > 0, a[..., :3] * 255.0 / np.maximum(al, 1), 0)
        _CROWN.append(Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8), "RGBA"))
    return _CROWN[0]


def paste_rgba(dst, spr, x, y):
    """Alpha-composite spr onto dst with its top-left at (x, y), clipped to dst."""
    x, y = int(round(x)), int(round(y))
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(spr.width, dst.width - x), min(spr.height, dst.height - y)
    if sx1 > sx0 and sy1 > sy0:
        dst.alpha_composite(spr, (x + sx0, y + sy0), (sx0, sy0, sx1, sy1))


def font(px, wght=800):
    key = (px, wght)
    if key not in _FONTS:
        import compositor as CO
        f = ImageFont.truetype(CO.find_font(), px)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        _FONTS[key] = f
    return _FONTS[key]


def pop_scale(dt):
    keys = [(0.00, 0.55), (0.06, 0.9), (0.12, 1.12), (0.19, 1.06), (0.27, 1.0)]
    if dt <= 0:
        return 0.55
    for (a, sa), (b, sb) in zip(keys[:-1], keys[1:]):
        if dt < b:
            return sa + (sb - sa) * (dt - a) / (b - a)
    return 1.0


class Overlay:
    def __init__(self, tl, project):
        self.tl = tl
        self.project = project                 # world point -> (x, y) pixels for this process's camera
        self.k = C.W / 1080.0
        ev = tl["events"]
        self.outs = [(t, v) for t, kind, v in ev if kind == "out"]
        self.close = [(t, v) for t, kind, v in ev if kind == "close"]
        self.t_final2 = next((t for t, kind, _ in ev if kind == "final2"), None)
        self.t_win, self.winner = next((t, v) for t, kind, v in ev if kind == "winner")
        self.col = dict(C.MARBLES)
        rng = np.random.default_rng(5)
        n = 150
        self.conf = dict(x=rng.uniform(0, C.W, n), y0=rng.uniform(-0.6, -0.02, n) * C.H, vy=rng.uniform(0.35, 0.6, n) * C.H,
                         vx=rng.uniform(-60, 60, n) * self.k, rot=rng.uniform(0, 6.3, n), vr=rng.uniform(-7, 7, n),
                         col=[C.MARBLES[i][1] for i in rng.integers(0, len(C.MARBLES), n)],
                         w=rng.uniform(10, 18, n) * self.k)

    def text(self, dr, s, cx, cy, px, fill, scale=1.0, stroke=None, alpha=255):
        px = max(4, int(round(px * self.k * scale)))
        f = font(px)
        sw = max(1, int(round(stroke if stroke is not None else 0.11 * px)))
        bb = dr.textbbox((0, 0), s, font=f, stroke_width=sw)
        dr.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), s, font=f, fill=(*fill, alpha),
                stroke_width=sw, stroke_fill=(16, 12, 24, alpha))

    def status(self, t):
        if t >= self.t_win:
            return None
        if self.t_final2 is not None and t >= self.t_final2:
            if t - self.t_final2 < 1.8:
                return ("FINAL 2!", 92, C.HIGHLIGHT, self.t_final2)
            return ("WHO WILL WIN?", 70, C.TEXT_FILL, self.t_final2 + 1.8)
        recent = [(tt, v) for tt, v in self.outs if tt <= t]
        if recent and t - recent[-1][0] < 1.7:
            tt, nm = recent[-1]
            burst = sum(1 for t2, _ in recent if tt - t2 < 1.6)
            if burst == 3:
                return ("TRIPLE KNOCKOUT!", 70, C.HIGHLIGHT, tt)
            if burst == 2:
                return ("DOUBLE KNOCKOUT!", 70, C.HIGHLIGHT, tt)
            return (f"{nm} IS OUT!", 76, self.col[nm], tt)
        if not recent:
            return ("PICK YOUR COLOR!", 70, C.HIGHLIGHT, 0.0)
        left = len(C.MARBLES) - len(recent)
        return (f"{left} STILL SPINNING", 64, C.TEXT_FILL, recent[-1][0] + 1.7)

    def draw(self, img, f, pos):
        t = f / C.FPS
        im = Image.fromarray(img).convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        W, H = C.W, C.H
        self.text(dr, C.TITLE1, W / 2, H * C.TITLE_Y, 78, C.TEXT_FILL)
        self.text(dr, C.TITLE2, W / 2, H * (C.TITLE_Y + 0.042), 78, C.HIGHLIGHT)
        self.chips(dr, t)
        st = self.status(t)
        if st:
            s, px, col, t0 = st
            self.text(dr, s, W / 2, H * C.STATUS_Y, px, col, pop_scale(t - t0))
        for tc, (nm, i) in self.close:
            dt = t - tc
            if 0 <= dt < 1.1 and t < self.t_win:
                x, y = self.project(pos[f, i] + np.array([0, 2.6, 0]))
                a = 255 if dt < 0.8 else int(255 * (1.1 - dt) / 0.3)
                self.text(dr, "SO CLOSE!", x, y - 16 * self.k, 46, (255, 255, 255), pop_scale(dt), alpha=a)
        if t >= self.t_win:
            self.crown(im, f, pos, t - self.t_win)
            self.win_box(dr, t - self.t_win)
            self.confetti(dr, t - self.t_win)
        return np.asarray(Image.alpha_composite(im, lay).convert("RGB"))

    def crown(self, im, f, pos, dt):
        """The gold crown pops in above the winner and bobs while it keeps circling."""
        i = [m[0] for m in C.MARBLES].index(self.winner)
        c = np.asarray(pos[f, i], float)
        x0, y0 = self.project(c)
        x1, _ = self.project(c + np.array([C.R, 0.0, 0.0]))
        pr = abs(x1 - x0)                                   # the marble's radius on screen
        s = pop_scale(dt - 0.15) if dt > 0.15 else 0.0
        if s <= 0:
            return
        spr = crown_sprite()
        w = 5.6 * pr * s                                    # the sprite is twice the crown's width (room for the glow)
        h = w * spr.height / spr.width
        spr = spr.resize((max(2, int(w)), max(2, int(h))), Image.LANCZOS)
        cy = y0 - pr * (2.4 + 0.15 * math.sin(dt * 5.0))
        paste_rgba(im, spr, x0 - spr.width / 2, cy - spr.height / 2)

    def chips(self, dr, t):
        n = len(C.MARBLES)
        r = 30 * self.k
        step = 84 * self.k
        cy = C.H * C.CHIPS_Y
        x0 = C.W / 2 - step * (n - 1) / 2
        outs = {nm: tt for tt, nm in self.outs}
        for i, (nm, col) in enumerate(C.MARBLES):
            cx = x0 + i * step
            out = nm in outs and t >= outs[nm]
            if nm == self.winner and t >= self.t_win:
                gw = 6 * self.k * (1 + 0.15 * math.sin((t - self.t_win) * 8))
                dr.ellipse([cx - r - gw, cy - r - gw, cx + r + gw, cy + r + gw], fill=(255, 205, 70, 255))
            o = 3 * self.k
            dr.ellipse([cx - r - o, cy - r - o, cx + r + o, cy + r + o], fill=(16, 12, 24, 255))
            fill = tuple(int(v * 0.42 + 28) for v in col) if out else col
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*fill, 255))
            hl = 0.45 * r
            dr.ellipse([cx - r * 0.55 - hl / 2, cy - r * 0.55 - hl / 2, cx - r * 0.55 + hl / 2, cy - r * 0.55 + hl / 2],
                       fill=(255, 255, 255, 50 if out else 110))
            if out:
                s = pop_scale(t - outs[nm])
                a = 0.5 * r * s
                w = max(2, int(6 * self.k))
                dr.line([cx - a, cy - a, cx + a, cy + a], fill=(255, 255, 255, 255), width=w)
                dr.line([cx - a, cy + a, cx + a, cy - a], fill=(255, 255, 255, 255), width=w)

    def win_box(self, dr, dt):
        nm = self.winner
        s = pop_scale(dt)
        bw, bh = 620 * self.k * s, 112 * self.k * s
        cx, cy = C.W / 2, C.H * (C.CHIPS_Y + 0.072)
        dr.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=22 * self.k * s,
                             fill=(28, 24, 34, 225))
        self.text(dr, f"{nm} WINS!", cx, cy, 84, self.col[nm], s, stroke=5 * self.k * s)

    def confetti(self, dr, dt):
        c = self.conf
        y = c["y0"] + c["vy"] * dt
        x = c["x"] + c["vx"] * dt + 22 * self.k * np.sin(dt * 3 + c["rot"])
        for i in range(len(y)):
            if y[i] < -20 or y[i] > C.H + 20:
                continue
            a = c["rot"][i] + c["vr"][i] * dt
            w, h = c["w"][i], c["w"][i] * 0.55 * (0.35 + 0.65 * abs(math.cos(a * 1.3)))
            ca, sa = math.cos(a), math.sin(a)
            pts = [(x[i] + ca * px - sa * py, y[i] + sa * px + ca * py) for px, py in
                   ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
            dr.polygon(pts, fill=(*c["col"][i], 255))
