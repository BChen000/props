#!/usr/bin/env python3
"""One command for a rainbow marble hourglass Short: "WHICH COLOR FALLS LAST? PICK YOUR COLOR!".

  python3 make_video.py                          # -> build/Marble_Hourglass.mp4 + build/thumbnail.png
  python3 make_video.py --stills 40,330,480      # PNG stills only
  PREVIEW=1 python3 make_video.py --stills 330   # half-size set and frames in build_preview/
  python3 make_video.py --thumb-only [--thumb-frame N]
Steps: path-trace the static hourglass once (cached by scene hash) -> physics (sim.py, cached per seed) -> frames
in WORKERS processes (marbles composited onto the board, the red gate pin, counters and text drawn on top) ->
soundtrack (audio.py) -> mux at -13 LUFS -> thumbnail (no text).
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "marble-raytrace-kit")
sys.path.insert(0, HERE)
sys.path.insert(0, KIT)

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import settings as C
import scene as S
import sim
import tracers
import compositor as CO
import pipeline as P

ap = argparse.ArgumentParser()
ap.add_argument("--stills", default="")
ap.add_argument("--thumb-only", action="store_true")
ap.add_argument("--thumb-frame", type=int, default=None)
ap.add_argument("--no-thumb", action="store_true")
ap.add_argument("--max-frames", type=int, default=None)
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()
log = P.log
GPREFIX = os.path.join(C.BUILD, "g")
WIN_COL = (255, 205, 70)
WHITE = (255, 255, 255)


def static_render():
    os.makedirs(C.BUILD, exist_ok=True)
    scene_txt = os.path.join(C.BUILD, "scene.txt")
    S.write_scene(scene_txt, 2 * C.W, 2 * C.H, *C.STATIC_SAMPLES)
    binary = tracers.build("boxtrace", C.BUILD)
    if tracers.render_static(binary, scene_txt, GPREFIX, GPREFIX + ".log"):
        log("static set rendered")


def timeline():
    """Frames, marble positions and colours, how many of each colour are still up top, when each colour runs out
    and the winner, from the physics. Video time 0 is LEAD_S before the gate opens."""
    path = sim.sim_path()
    if not os.path.exists(path):
        log(f"physics (seed {C.SEED})...")
        sim.run()
    d = np.load(path)
    rec, ev, passed, col = d["rec"], d["ev"].copy(), d["passed"], d["colours"]
    t0, rec_hz = float(d["t_rec0"]), float(d["rec_hz"])
    outs = [(t - t0, int(k)) for t, k in sim.outs(passed, col)]
    if not all(math.isfinite(t) for t, _ in outs):
        sys.exit(f"seed {C.SEED} jams at the neck: pick another with sim.py --search")
    t_go = C.FILL_S - t0
    t_win = outs[-1][0] + 0.35
    n_frames = int(math.ceil((t_win + C.HOLD_S) * C.FPS))
    if args.max_frames:
        n_frames = min(n_frames, args.max_frames)
    ft = np.arange(n_frames) / C.FPS
    fi = np.clip(ft * rec_hz, 0, len(rec) - 1)
    i0 = np.floor(fi).astype(int)
    i1 = np.minimum(i0 + 1, len(rec) - 1)
    a = (fi - i0)[:, None, None]
    xy = rec[i0] * (1 - a) + rec[i1] * a
    pos = np.concatenate([xy, np.full(xy.shape[:2] + (1,), C.Z_MARBLE)], 2)
    vis = np.ones(pos.shape[:2], bool)
    colors = [list(C.COLOURS[int(k)][1]) for k in col]
    nc = len(C.COLOURS)
    pt = passed - t0
    left = np.zeros((n_frames, nc), int)
    passes = []
    for k in range(nc):
        p = np.sort(pt[col == k])
        left[:, k] = len(p) - np.searchsorted(p, ft, side="right")
        passes.append(p.tolist())
    ev[:, 0] -= t0
    out_at = [0.0] * nc
    for t, k in outs:
        out_at[k] = t
    return dict(n_frames=n_frames, pos=pos, vis=vis, colors=colors, col=col, left=left, passes=passes, outs=outs,
                out_at=out_at, t_go=t_go, t_win=t_win, winner=outs[-1][1], runner_up=outs[-2][1], ev=ev)


_FONTS = {}
_CROWN = []


def crown_sprite():
    """The channel's gold crown (../crown-icon, drawn with skia) as a PIL RGBA image, 5x the base size."""
    if not _CROWN:
        import skia
        sys.path.append(os.path.join(HERE, "..", "crown-icon"))
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
    x, y = int(round(x)), int(round(y))
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(spr.width, dst.width - x), min(spr.height, dst.height - y)
    if sx1 > sx0 and sy1 > sy0:
        dst.alpha_composite(spr, (x + sx0, y + sy0), (sx0, sy0, sx1, sy1))


def font(px, wght=800):
    if (px, wght) not in _FONTS:
        f = ImageFont.truetype(CO.find_font(), px)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        _FONTS[(px, wght)] = f
    return _FONTS[(px, wght)]


def pop_scale(dt):
    keys = [(0.00, 0.55), (0.06, 0.9), (0.12, 1.12), (0.19, 1.06), (0.27, 1.0)]
    if dt <= 0:
        return 0.55
    for (a, sa), (b, sb) in zip(keys[:-1], keys[1:]):
        if dt < b:
            return sa + (sb - sa) * (dt - a) / (b - a)
    return 1.0


def grey(rgb):
    g = 0.3 * rgb[0] + 0.59 * rgb[1] + 0.11 * rgb[2]
    return tuple(int(0.35 * g + 0.15 * c + 20) for c in rgb)


class Frames:
    """The compositor plus the red gate pin and the HUD: title, a status line (pick your color, 3-2-1-GO, "X IS
    OUT!", the final duel), one counter disc per colour beside the top half (3 left, 3 right), the winner box, crown
    and confetti. render(f) is what the kit's render_video calls."""

    def __init__(self, tl, comp, hud=True):
        self.tl, self.comp, self.hud = tl, comp, hud
        self.k = C.W / 1080.0
        rng = np.random.default_rng(9)
        n = 150
        self.conf = dict(x=rng.uniform(0, C.W, n), y0=rng.uniform(-0.6, -0.02, n) * C.H,
                         vy=rng.uniform(0.35, 0.6, n) * C.H, vx=rng.uniform(-60, 60, n) * self.k,
                         rot=rng.uniform(0, 6.3, n), vr=rng.uniform(-7, 7, n),
                         col=[C.COLOURS[i][1] for i in rng.integers(0, len(C.COLOURS), n)],
                         w=rng.uniform(10, 18, n) * self.k)
        nc = len(C.COLOURS)
        half = (nc + 1) // 2
        self.chip_xy = [((C.CHIP_X if k < half else 1.0 - C.CHIP_X) * C.W,
                         (C.CHIP_Y0 + C.CHIP_DY * (k % half)) * C.H) for k in range(nc)]

    def px(self, p):
        x, y, _ = S.project(p)
        return x, y

    def text(self, dr, s, cx, cy, px, fill, scale=1.0, alpha=255, stroke=None, maxw=None):
        px = max(4, int(round(px * self.k * scale)))
        f = font(px)
        sw = max(1, int(round(stroke if stroke is not None else 0.11 * px)))
        bb = dr.textbbox((0, 0), s, font=f, stroke_width=sw)
        if maxw and bb[2] - bb[0] > maxw * self.k * scale:
            px = max(4, int(px * maxw * self.k * scale / (bb[2] - bb[0])))
            f = font(px)
            sw = max(1, int(round(stroke if stroke is not None else 0.11 * px)))
            bb = dr.textbbox((0, 0), s, font=f, stroke_width=sw)
        dr.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), s, font=f, fill=(*fill, alpha),
                stroke_width=sw, stroke_fill=(16, 12, 24, alpha))

    def segments(self, dr, segs, cx, cy, px, scale=1.0):
        """One line of text in several colours, centred on (cx, cy)."""
        px = max(4, int(round(px * self.k * scale)))
        f = font(px)
        sw = max(1, int(round(0.11 * px)))
        ws = [dr.textlength(s, font=f) for s, _ in segs]
        if sum(ws) > 1000 * self.k * scale:
            px = max(4, int(px * 1000 * self.k * scale / sum(ws)))
            f = font(px)
            sw = max(1, int(round(0.11 * px)))
            ws = [dr.textlength(s, font=f) for s, _ in segs]
        bb = dr.textbbox((0, 0), "".join(s for s, _ in segs), font=f, stroke_width=sw)
        x = cx - sum(ws) / 2
        for (s, col), w in zip(segs, ws):
            dr.text((x, cy - (bb[1] + bb[3]) / 2), s, font=f, fill=(*col, 255), stroke_width=sw,
                    stroke_fill=(16, 12, 24, 255))
            x += w

    def status(self, t):
        """(text or segments, px, colour, time it appeared) for the line under the title, or None."""
        tl = self.tl
        tg = tl["t_go"]
        if t >= tl["t_win"]:
            return None
        if t < tg - 1.8:
            return (C.SUBTITLE, 64, WIN_COL, 0.0)
        if t < tg:
            n = 3 - int((t - (tg - 1.8)) / 0.6)
            return (str(n), 116, WHITE, tg - 1.8 + (3 - n) * 0.6)
        if t < tg + 0.9:
            return ("GO!", 116, (120, 232, 120), tg)
        done = [(tt, k) for tt, k in tl["outs"][:-1] if tt <= t]
        if done and t - done[-1][0] < 1.4:
            tt, k = done[-1]
            name, rgb = C.COLOURS[k]
            return (f"{name} IS OUT!", 66, rgb, tt)
        alive = [k for k in range(len(C.COLOURS)) if tl["out_at"][k] > t]
        if len(alive) == 2:
            a, b = sorted(alive, key=lambda k: tl["out_at"][k])
            t3 = tl["outs"][-3][0]
            return ([(C.COLOURS[a][0], C.COLOURS[a][1]), (" VS ", WHITE), (C.COLOURS[b][0], C.COLOURS[b][1])], 66,
                    None, t3 + 1.4)
        return (f"{len(alive)} COLORS LEFT", 56, WHITE, tg + 0.9 if not done else done[-1][0] + 1.4)

    def gate(self, dr, t):
        """The red pin that holds the marbles up until GO: it slides out to the right in the last 0.2 s."""
        tg = self.tl["t_go"]
        s = min(1.0, max(0.0, (t - (tg - 0.2)) / 0.2))
        if s >= 1.0:
            return
        e = s * s * (3 - 2 * s)
        dx = e * 9.0
        al = int(255 * (1 - max(0.0, (s - 0.4) / 0.6)))
        hw = C.NECK_HALF + 1.2
        y0, y1 = C.NECK_Y - 0.15, C.NECK_Y + 0.6
        z = C.DEPTH + 0.05
        pts = [self.px((x, y, z)) for x, y in ((-hw + dx, y0), (hw + dx, y0), (hw + dx, y1), (-hw + dx, y1))]
        dr.polygon(pts, fill=(206, 50, 46, al), outline=(96, 22, 20, al))
        p0, p1 = self.px((-hw + dx + 0.2, y1 - 0.14, z)), self.px((hw + dx - 0.2, y1 - 0.14, z))
        dr.line([p0, p1], fill=(255, 160, 150, al // 2), width=max(1, int(round(3 * self.k))))

    def chip(self, im, dr, f, k, t):
        tl = self.tl
        x, y = self.chip_xy[k]
        name, rgb = C.COLOURS[k]
        out_t = tl["out_at"][k]
        is_out = t >= out_t and k != tl["winner"]
        win = t >= tl["t_win"] and k == tl["winner"]
        r = C.CHIP_R * self.k
        sc = 1.0
        last = [tt for tt in tl["passes"][k] if tt <= t]
        if last and not is_out:
            sc = 1.0 + 0.12 * max(0.0, 1.0 - (t - last[-1]) / 0.15)
        if is_out and t - out_t < 0.3:
            sc = pop_scale(t - out_t)
        if win:
            sc = pop_scale(t - tl["t_win"]) * (1.0 + 0.07 * math.sin((t - tl["t_win"]) * 7))
        rr = r * sc
        fill = grey(rgb) if is_out else rgb
        ring = WIN_COL if win else (24, 18, 30)
        dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(*fill, 255), outline=(*ring, 255),
                   width=max(2, int(round((8 if win else 4) * self.k * sc))))
        dr.ellipse([x - rr * 0.62, y - rr * 0.74, x - rr * 0.22, y - rr * 0.46], fill=(255, 255, 255, 45 if is_out else 70))
        if is_out:
            self.text(dr, "OUT", x, y + 2 * self.k, 38, (236, 236, 236), sc)
        elif win:
            self.text(dr, "WIN", x, y + 2 * self.k, 40, WIN_COL, sc)
        else:
            self.text(dr, str(int(tl["left"][f, k])), x, y + 2 * self.k, 52, WHITE, sc)
        self.text(dr, name, x, y + r + 28 * self.k, 29, (150, 150, 150) if is_out else rgb)
        if win:
            dt = t - tl["t_win"]
            s = pop_scale(dt - 0.15) if dt > 0.15 else 0.0
            if s > 0:
                spr = crown_sprite()
                w = 2.3 * r * s
                h = w * spr.height / spr.width
                spr = spr.resize((max(2, int(w)), max(2, int(h))), Image.LANCZOS)
                paste_rgba(im, spr, x - spr.width / 2, y - rr - spr.height * 0.62 - 4 * self.k * math.sin(dt * 5.0))

    def render(self, f, title=True, watermark=True):
        img = self.comp.render(f, title=False, watermark=False)
        t = f / C.FPS
        tl = self.tl
        im = Image.fromarray(img).convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        self.gate(dr, t)
        if not self.hud:
            return np.asarray(Image.alpha_composite(im, lay).convert("RGB"))
        W, H = C.W, C.H
        self.text(dr, C.TITLE, W / 2, H * 0.112, 84, WHITE, maxw=1000)
        st = self.status(t)
        if st:
            s, px, col, t0 = st
            if isinstance(s, list):
                self.segments(dr, s, W / 2, H * 0.158, px, pop_scale(t - t0))
            else:
                self.text(dr, s, W / 2, H * 0.158, px, col, pop_scale(t - t0), maxw=1000)
        crowns = Image.new("RGBA", im.size, (0, 0, 0, 0))
        for k in range(len(C.COLOURS)):
            self.chip(crowns, dr, f, k, t)
        if watermark:
            self.text(dr, C.WATERMARK, W / 2, H * 0.988, 30, (236, 242, 250), alpha=150, stroke=0)
        win = t >= tl["t_win"]
        if win:
            dt = t - tl["t_win"]
            s = pop_scale(dt)
            bw, bh = 600 * self.k * s, 116 * self.k * s
            cx, cy = W / 2, H * 0.165
            name, rgb = C.COLOURS[tl["winner"]]
            dr.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=22 * self.k * s,
                                 fill=(28, 24, 34, 225), outline=(*WIN_COL, 255), width=max(2, int(4 * self.k * s)))
            self.text(dr, C.WIN_TEXT.format(c=name), cx, cy, 80, rgb, s, stroke=5 * self.k * s)
            self.confetti(dr, dt)
        out = Image.alpha_composite(Image.alpha_composite(im, lay), crowns)
        return np.asarray(out.convert("RGB"))

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


def make_frames(tl, hud=True):
    CO.configure(S)
    comp = CO.Compositor(GPREFIX, tl["pos"], tl["vis"], tl["colors"], [], titles=[], watermark=None)
    return Frames(tl, comp, hud)


def main():
    os.makedirs(C.BUILD, exist_ok=True)
    tl = timeline()
    if args.worker:                        # the main process has rendered the static set already
        fr = make_frames(tl)
        sys.exit(CO.render_video(fr, int(args.worker[0]), int(args.worker[1]), args.worker[2], C.CRF))
    order = ", ".join(f"{C.COLOURS[k][0]} {t - tl['t_go']:.2f}" for t, k in tl["outs"])
    log(f"timeline: {tl['n_frames']} frames ({tl['n_frames'] / C.FPS:.2f} s), out after GO: {order}; "
        f"winner {C.COLOURS[tl['winner']][0]}")
    static_render()
    if args.stills:
        fr = make_frames(tl)
        for fs in args.stills.split(","):
            p = os.path.join(C.BUILD, f"still_{int(fs):04d}.png")
            Image.fromarray(fr.render(int(fs))).save(p)
            log(p)
        return
    if args.thumb_only:
        thumbnail(tl)
        return
    import audio
    wav = os.path.join(C.BUILD, "soundtrack.wav")
    audio.build(tl, wav)
    parts = P.run_workers([sys.executable, __file__] + (["--max-frames", str(args.max_frames)] if args.max_frames
                                                          else []), tl["n_frames"], C.WORKERS, C.BUILD,
                          P.frame_costs(tl["pos"], tl["vis"]))
    out = os.path.join(C.BUILD, C.FILE + ".mp4")
    P.mux(parts, wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        thumbnail(tl)


def thumbnail(tl):
    """No text: the hourglass THUMB_AFTER_GO s after the gate opens, still full of rainbow patches up top, a stream
    through the neck and a pile growing below."""
    fr = make_frames(tl, hud=False)
    f = args.thumb_frame if args.thumb_frame is not None else int((tl["t_go"] + C.THUMB_AFTER_GO) * C.FPS)
    out = os.path.join(C.BUILD, "thumbnail.png")
    Image.fromarray(fr.render(f)).save(out)
    log(f"thumbnail (frame {f}) -> {out}")


if __name__ == "__main__":
    main()
