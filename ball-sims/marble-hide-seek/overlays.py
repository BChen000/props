"""Text and HUD drawn over each rendered frame (PIL, Montserrat ExtraBold from ../marble-raytrace-kit/fonts):
the title, the status line (countdown, READY OR NOT!, how many are still hiding, TIME'S UP!, the winner box), a row
of colour chips that get an X when that marble is found, FOUND! pops above found marbles, a ? over the seeker when
a spot is empty, and confetti for the winner.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import settings as C

HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS = {}


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
    def __init__(self, story, project):
        self.s = story
        self.project = project             # world point -> (x, y) pixels
        self.k = C.W / 1080.0
        ev = story["events"]
        self.counts = [(t, v) for t, kind, v in ev if kind == "count"]
        self.t_ready = next(t for t, kind, _ in ev if kind == "ready")
        self.found = [(t, v) for t, kind, v in ev if kind == "found"]
        self.empty = [t for t, kind, _ in ev if kind == "empty"]
        self.where = [t for t, kind, _ in ev if kind == "where"]
        self.t_up = next(t for t, kind, _ in ev if kind == "timesup")
        self.t_win, self.winner = next((t, v) for t, kind, v in ev if kind == "winner")
        rng = np.random.default_rng(5)
        n = 140
        self.conf = dict(x=rng.uniform(0, C.W, n), y0=rng.uniform(-0.6, -0.02, n) * C.H, vy=rng.uniform(0.35, 0.6, n) * C.H,
                         vx=rng.uniform(-60, 60, n) * self.k, rot=rng.uniform(0, 6.3, n), vr=rng.uniform(-7, 7, n),
                         col=[C.HIDERS[i % 6][1] for i in rng.integers(0, 6, n)], w=rng.uniform(10, 18, n) * self.k)

    def text(self, dr, s, cx, cy, px, fill, scale=1.0, stroke=None, alpha=255):
        px = max(4, int(round(px * self.k * scale)))
        f = font(px)
        sw = max(1, int(round((stroke if stroke is not None else 0.11 * px))))
        bb = dr.textbbox((0, 0), s, font=f, stroke_width=sw)
        x = cx - (bb[0] + bb[2]) / 2
        y = cy - (bb[1] + bb[3]) / 2
        dr.text((x, y), s, font=f, fill=(*fill, alpha), stroke_width=sw, stroke_fill=(16, 12, 24, alpha))

    def status(self, t):
        """(text, size, colour, start time) of the status line at time t."""
        if t < self.counts[0][0]:
            return ("PICK YOUR COLOR!", 64, C.HIGHLIGHT, 0.0)
        if t < self.t_ready:
            k = max(i for i, (tc, _) in enumerate(self.counts) if tc <= t)
            return (str(self.counts[k][1]), 150, C.HIGHLIGHT, self.counts[k][0])
        if t < self.t_ready + 1.6:
            return ("READY OR NOT!", 76, C.HIGHLIGHT, self.t_ready)
        if t >= self.t_win:
            return None
        if t >= self.t_up:
            return ("TIME'S UP!", 92, (255, 96, 96), self.t_up)
        nfound = sum(1 for tf, _ in self.found if tf <= t)
        last = max([self.t_ready + 1.6] + [tf for tf, _ in self.found if tf <= t])
        left = len(C.HIDERS) - nfound
        if self.where and t >= self.where[0]:
            return ("1 LEFT... WHERE?", 70, C.TEXT_FILL, self.where[0])
        return (f"{left} STILL HIDING", 66, C.TEXT_FILL, last)

    def draw(self, img, f, pos):
        t = f / C.FPS
        im = Image.fromarray(img).convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        W, H = C.W, C.H
        self.text(dr, C.TITLE, W / 2, H * C.TITLE_Y, 84, C.TEXT_FILL)
        st = self.status(t)
        if st:
            s, px, col, t0 = st
            self.text(dr, s, W / 2, H * C.STATUS_Y, px, col, pop_scale(t - t0))
        self.chips(dr, t)
        for tf, nm in self.found:
            dt = t - tf
            if 0 <= dt < 1.3:
                k = 1 + C.HIDERS.index(next(h for h in C.HIDERS if h[0] == nm))
                x, y = self.project(pos[f, k] + np.array([0, 2.8, 0]))
                a = 255 if dt < 1.0 else int(255 * (1.3 - dt) / 0.3)
                self.text(dr, "FOUND!", x, y - 18 * self.k, 50, (255, 255, 255), pop_scale(dt), alpha=a)
        for te in self.empty + self.where:
            dt = t - te
            if 0 <= dt < 1.5:
                x, y = self.project(pos[f, 0] + np.array([0, 2.9, 0]))
                a = 255 if dt < 1.2 else int(255 * (1.5 - dt) / 0.3)
                self.text(dr, "?", x, y - 20 * self.k, 74, C.HIGHLIGHT, pop_scale(dt), alpha=a)
        if t >= self.t_win:
            self.win_box(dr, t - self.t_win)
            self.confetti(dr, t - self.t_win)
        im = Image.alpha_composite(im, lay)
        return np.asarray(im.convert("RGB"))

    def chips(self, dr, t):
        n = len(C.HIDERS)
        r = 34 * self.k
        step = 96 * self.k
        cy = C.H * C.CHIPS_Y
        x0 = C.W / 2 - step * (n - 1) / 2
        found = {nm: tf for tf, nm in self.found}
        for i, (nm, col) in enumerate(C.HIDERS):
            cx = x0 + i * step
            out = nm in found and t >= found[nm]
            win = nm == self.winner and t >= self.t_win
            if win:
                gw = 6 * self.k * (1 + 0.15 * math.sin((t - self.t_win) * 8))
                dr.ellipse([cx - r - gw, cy - r - gw, cx + r + gw, cy + r + gw], fill=(255, 205, 70, 255))
            dr.ellipse([cx - r - 3 * self.k, cy - r - 3 * self.k, cx + r + 3 * self.k, cy + r + 3 * self.k],
                       fill=(16, 12, 24, 255))
            fill = tuple(int(v * 0.45 + 30) for v in col) if out else col
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*fill, 255))
            hl = 0.45 * r
            dr.ellipse([cx - r * 0.55 - hl / 2, cy - r * 0.55 - hl / 2, cx - r * 0.55 + hl / 2, cy - r * 0.55 + hl / 2],
                       fill=(255, 255, 255, 110 if not out else 50))
            if out:
                s = pop_scale(t - found[nm])
                a = 0.5 * r * s
                w = max(2, int(7 * self.k))
                dr.line([cx - a, cy - a, cx + a, cy + a], fill=(255, 255, 255, 255), width=w)
                dr.line([cx - a, cy + a, cx + a, cy - a], fill=(255, 255, 255, 255), width=w)

    def win_box(self, dr, dt):
        nm = self.winner
        col = dict(C.HIDERS)[nm]
        s = pop_scale(dt)
        bw, bh = 640 * self.k * s, 118 * self.k * s
        cx, cy = C.W / 2, C.H * C.STATUS_Y + 6 * self.k
        dr.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=22 * self.k * s,
                             fill=(28, 24, 34, 225))
        self.text(dr, f"{nm} WINS!", cx, cy, 86, col, s, stroke=5 * self.k * s)

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
