"""Text and HUD over each frame (PIL, Montserrat ExtraBold from ../marble-raytrace-kit/fonts): the two-line title,
a counter over each basket (a marble icon and "12/30"), callouts at the bottom (PICK A SIDE!, STEEL LEADS!,
SO CLOSE!, ALL 30 GLASS ARE IN!, LAST STEEL BALL...), the winner box with a crown and confetti, and the fun fact
that explains it.
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


class Overlay:
    def __init__(self, tl, project):
        self.tl = tl
        self.project = project
        self.k = C.W / 1080.0
        ev = tl["events"]
        self.lands = [(t, v[0], v[2]) for t, kind, v in ev if kind == "land"]
        self.callouts = []
        for t, kind, v in ev:
            if kind == "flip" and t < tl["t_tip"] - 0.05:
                nm = C.RIGHT["name"] if v == "R" else C.LEFT["name"]
                col = C.TEXT_FILL if v == "R" else self.team_col("L")
                if C.LEFT["metal"] and v == "L":
                    col = C.TEXT_FILL
                self.callouts.append((t, 1.6, f"{nm} LEADS!", 84, col))
            elif kind == "close":
                self.callouts.append((t, 1.3, "SO CLOSE!", 84, C.HIGHLIGHT))
            elif kind == "all_left":
                self.callouts.append((t, 1.9, f"ALL {C.LEFT['n']} {C.LEFT['name']} ARE IN!", 66, self.team_col("L")))
            elif kind == "last_one":
                self.callouts.append((t, tl["t_tip"] - t, f"LAST {C.RIGHT['name']} BALL...", 72, C.TEXT_FILL))
        self.callouts.sort(key=lambda c: c[0])
        self.t_win = tl["t_tip"]
        self.winner = tl["winner"]
        rng = np.random.default_rng(5)
        n = 150
        pal = [C.LEFT["srgb"], (190, 196, 206), (255, 214, 80), (255, 255, 255), (64, 120, 226)]
        self.conf = dict(x=rng.uniform(0, C.W, n), y0=rng.uniform(-0.6, -0.02, n) * C.H, vy=rng.uniform(0.35, 0.6, n) * C.H,
                         vx=rng.uniform(-60, 60, n) * self.k, rot=rng.uniform(0, 6.3, n), vr=rng.uniform(-7, 7, n),
                         col=[pal[i] for i in rng.integers(0, len(pal), n)], w=rng.uniform(10, 18, n) * self.k)

    @staticmethod
    def team_col(side):
        c = C.LEFT["srgb"] if side == "L" else C.RIGHT["srgb"]
        return tuple(int(v) for v in c)

    def text(self, dr, s, cx, cy, px, fill, scale=1.0, stroke=None, alpha=255, anchor="mm"):
        px = max(4, int(round(px * self.k * scale)))
        f = font(px)
        sw = max(1, int(round(stroke if stroke is not None else 0.11 * px)))
        bb = dr.textbbox((0, 0), s, font=f, stroke_width=sw)
        x = cx - (bb[0] + bb[2]) / 2 if anchor == "mm" else cx - bb[0]
        dr.text((x, cy - (bb[1] + bb[3]) / 2), s, font=f, fill=(*fill, alpha), stroke_width=sw,
                stroke_fill=(16, 12, 24, alpha))
        return bb[2] - bb[0]

    def icon(self, dr, cx, cy, r, side):
        """A marble icon: red glass, or a silver steel ball with a bright highlight."""
        o = 3 * self.k
        dr.ellipse([cx - r - o, cy - r - o, cx + r + o, cy + r + o], fill=(16, 12, 24, 255))
        if side == "R" and C.RIGHT["metal"] or side == "L" and C.LEFT["metal"]:
            for k in range(10, 0, -1):
                rr = r * k / 10
                v = int(120 + 120 * (1 - k / 10) ** 0.7)
                dr.ellipse([cx - rr, cy - rr - (1 - k / 10) * r * 0.25, cx + rr, cy + rr - (1 - k / 10) * r * 0.25],
                           fill=(v, v + 3, v + 8, 255))
        else:
            col = self.team_col(side)
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, 255))
        hl = 0.42 * r
        dr.ellipse([cx - r * 0.5 - hl / 2, cy - r * 0.5 - hl / 2, cx - r * 0.5 + hl / 2, cy - r * 0.5 + hl / 2],
                   fill=(255, 255, 255, 170))

    def counters(self, dr, im, t):
        cy = C.H * C.COUNT_Y
        for side, team, cx in (("L", C.LEFT, C.W * 0.27), ("R", C.RIGHT, C.W * 0.73)):
            got = [(tt, n) for tt, s, n in self.lands if s == side and tt <= t]
            n = got[-1][1] if got else 0
            dt = t - got[-1][0] if got else 9.0
            sc = 1.0 + 0.22 * math.sin(math.pi * dt / 0.22) if dt < 0.22 else 1.0    # a bump, even when they pour in
            won = t >= self.t_win and self.winner == side
            r = 30 * self.k
            s = f"{n}/{team['n']}"
            tw = font(int(64 * self.k)).getlength(s)
            x_icon = cx - (2 * r + 18 * self.k + tw) / 2 + r
            if won:
                gw = 8 * self.k * (1 + 0.15 * math.sin((t - self.t_win) * 8))
                dr.rounded_rectangle([x_icon - r - 14 * self.k - gw, cy - r - 12 * self.k - gw,
                                      x_icon + r + 18 * self.k + tw + 14 * self.k + gw, cy + r + 12 * self.k + gw],
                                     radius=24 * self.k, fill=(255, 205, 70, 255))
                dr.rounded_rectangle([x_icon - r - 14 * self.k, cy - r - 12 * self.k,
                                      x_icon + r + 18 * self.k + tw + 14 * self.k, cy + r + 12 * self.k],
                                     radius=20 * self.k, fill=(28, 24, 34, 235))
            self.icon(dr, x_icon, cy, r, side)
            self.text(dr, s, x_icon + r + 18 * self.k, cy, 64, (255, 255, 255), sc, anchor="lm")

    def crown(self, im, f, dt):
        """The gold crown pops in over the winning basket and bobs there."""
        s = pop_scale(dt - 0.25) if dt > 0.25 else 0.0
        if s <= 0:
            return
        side = 1 if self.winner == "R" else -1
        th = math.radians(float(self.tl["theta_q"][f]))
        lx, ly = side * C.ARM, 0.5 * C.BEAM_T + C.BASKET_WALL + C.BASKET_H + 4.2
        p = np.array([C.PIVOT[0] + math.cos(th) * lx - math.sin(th) * ly,
                      C.PIVOT[1] + math.sin(th) * lx + math.cos(th) * ly, 0.0])
        x, y = self.project(p)
        spr = crown_sprite()
        w = 300 * self.k * s
        spr = spr.resize((max(2, int(w)), max(2, int(w * spr.height / spr.width))), Image.LANCZOS)
        y += 8 * self.k * math.sin(dt * 5)
        x0, y0 = int(x - spr.width / 2), int(y - spr.height / 2)
        sx0, sy0 = max(0, -x0), max(0, -y0)
        sx1, sy1 = min(spr.width, im.width - x0), min(spr.height, im.height - y0)
        if sx1 > sx0 and sy1 > sy0:
            im.alpha_composite(spr, (x0 + sx0, y0 + sy0), (sx0, sy0, sx1, sy1))

    def draw(self, img, f):
        t = f / C.FPS
        im = Image.fromarray(img).convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        W, H = C.W, C.H
        self.text(dr, C.TITLE1, W / 2, H * C.TITLE_Y, 80, C.TEXT_FILL)
        self.text(dr, C.TITLE2, W / 2, H * (C.TITLE_Y + 0.043), 66, C.HIGHLIGHT)
        self.counters(dr, im, t)
        if t < self.t_win:
            cur = [c for c in self.callouts if c[0] <= t < c[0] + c[1]]
            if cur:
                t0, _, s, px, col = cur[-1]
                self.text(dr, s, W / 2, H * C.STATUS_Y, px, col, pop_scale(t - t0))
            elif not any(tt <= t for tt, _, _ in self.lands):
                self.text(dr, "PICK A SIDE!", W / 2, H * C.STATUS_Y, 84, C.HIGHLIGHT, pop_scale(t))
        else:
            dt = t - self.t_win
            self.crown(im, f, dt)
            self.win_box(dr, dt)
            if dt > 1.0:
                a = int(255 * min(1.0, (dt - 1.0) / 0.25))
                ratio = C.RIGHT["mass"] / C.LEFT["mass"]
                heavy, light = (C.RIGHT, C.LEFT) if ratio >= 1 else (C.LEFT, C.RIGHT)
                k = max(ratio, 1 / ratio)
                self.text(dr, f"1 {heavy['name']} BALL WEIGHS AS MUCH", W / 2, H * (C.STATUS_Y - 0.012), 50,
                          C.TEXT_FILL, pop_scale(dt - 1.0), alpha=a)
                self.text(dr, f"AS {k:.0f} {light['name']} MARBLES!", W / 2, H * (C.STATUS_Y + 0.03), 50,
                          C.HIGHLIGHT, pop_scale(dt - 1.0), alpha=a)
            self.confetti(dr, dt)
        return np.asarray(Image.alpha_composite(im, lay).convert("RGB"))

    def win_box(self, dr, dt):
        side = self.winner
        nm = (C.RIGHT if side == "R" else C.LEFT)["name"]
        s = pop_scale(dt)
        bw, bh = 640 * self.k * s, 112 * self.k * s
        cx, cy = C.W / 2, C.H * (C.COUNT_Y + 0.075)
        dr.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=22 * self.k * s,
                             fill=(28, 24, 34, 230))
        col = (255, 255, 255) if (C.RIGHT if side == "R" else C.LEFT)["metal"] else self.team_col(side)
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
