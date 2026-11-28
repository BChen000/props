#!/usr/bin/env python3
"""One command for a marble peg-board challenge Short: "WHICH BIN WINS? PICK 1 TO 7".

  python3 make_video.py                          # -> build/Marble_Peg_Board.mp4 + build/thumbnail.png
  python3 make_video.py --stills 150,400,700     # PNG stills only
  PREVIEW=1 python3 make_video.py --stills 400   # half-size set and frames in build_preview/
  python3 make_video.py --thumb-only [--thumb-frame N]
Steps: path-trace the static board once (cached by scene hash) -> physics (sim.py, cached per seed) -> frames in
WORKERS processes (marbles composited onto the board, pegs flash on hits, counters and text drawn on top) ->
soundtrack (audio.py) -> mux at -13 LUFS -> thumbnail (no text).
"""
import argparse
import json
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


def static_render():
    os.makedirs(C.BUILD, exist_ok=True)
    scene_txt = os.path.join(C.BUILD, "scene.txt")
    S.write_scene(scene_txt, 2 * C.W, 2 * C.H, *C.STATIC_SAMPLES)
    binary = tracers.build("boxtrace", C.BUILD)
    if tracers.render_static(binary, scene_txt, GPREFIX, GPREFIX + ".log"):
        log("static set rendered")


def timeline():
    """Frames, marble positions, colours, peg flashes, counters, lead changes and the winner, from the physics."""
    path = sim.sim_path()
    if not os.path.exists(path):
        log(f"physics (seed {C.SEED})...")
        sim.run()
    d = np.load(path)
    rec, act, ev, in_bin = d["rec"], d["act"], d["ev"], d["in_bin"]
    land = ev[ev[:, 1] == 1]
    land = land[np.argsort(land[:, 0])]
    t_last = float(land[-1, 0]) if len(land) else float(d["t_end"])
    t_win = t_last + 0.55
    n_frames = int(math.ceil((t_win + C.HOLD_S) * C.FPS))
    if args.max_frames:
        n_frames = min(n_frames, args.max_frames)
    ft = np.arange(n_frames) / C.FPS
    fi = np.clip(ft * C.REC_HZ, 0, len(rec) - 1)
    i0 = np.floor(fi).astype(int)
    i1 = np.minimum(i0 + 1, len(rec) - 1)
    a = (fi - i0)[:, None, None]
    xy = rec[i0] * (1 - a) + rec[i1] * a
    pos = np.concatenate([xy, np.full(xy.shape[:2] + (1,), C.Z_MARBLE)], 2)
    vis = act[i1].astype(bool)
    rng = np.random.default_rng(C.SEED + 100)
    pal = [C.MARBLE_SRGB[k % len(C.MARBLE_SRGB)] for k in range(C.N)]
    order = rng.permutation(C.N)
    colors = [list(pal[k]) for k in order]
    counts = np.zeros((n_frames, C.BINS), int)
    for t, _, b, *_ in land:
        counts[ft >= t, int(b)] += 1
    final = np.bincount(in_bin[in_bin >= 0], minlength=C.BINS)
    winner = int(np.argmax(final))
    leads = []
    c = np.zeros(C.BINS, int)
    leader = -1
    for t, _, b, *_ in land:
        c[int(b)] += 1
        top = np.flatnonzero(c == c.max())
        now = int(top[0]) if len(top) == 1 else -1
        if now != leader:
            leads.append((float(t), now))
            leader = now
    hits = ev[ev[:, 1] == 0]
    sp = np.zeros(vis.shape)
    sp[1:] = np.linalg.norm(pos[1:] - pos[:-1], axis=2) * C.FPS
    tops = np.full((n_frames, C.BINS), C.BIN_FLOOR_Y)
    for b in range(C.BINS):
        x0, x1 = S.WALL_X[b], S.WALL_X[b + 1]
        m = vis & (pos[..., 0] > x0) & (pos[..., 0] < x1) & (pos[..., 1] < S.BIN_TOP) & (sp < 4.0)
        y = np.where(m, pos[..., 1] + 1.0, C.BIN_FLOOR_Y)
        tops[:, b] = np.maximum.accumulate(y.max(1))
    return dict(n_frames=n_frames, pos=pos, vis=vis, colors=colors, counts=counts, final=final.tolist(), tops=tops,
                winner=winner, t_win=t_win, t_last=t_last, leads=leads, hits=hits, ev=ev, land=land)


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


class Frames:
    """The compositor plus the HUD: title, status line, a count over each bin's pile, bin numbers, the crown and
    winner box, confetti. render(f) is what the kit's render_video calls."""

    def __init__(self, tl, comp, hud=True):
        self.tl, self.comp, self.hud = tl, comp, hud
        self.k = C.W / 1080.0
        rng = np.random.default_rng(9)
        n = 150
        self.conf = dict(x=rng.uniform(0, C.W, n), y0=rng.uniform(-0.6, -0.02, n) * C.H,
                         vy=rng.uniform(0.35, 0.6, n) * C.H, vx=rng.uniform(-60, 60, n) * self.k,
                         rot=rng.uniform(0, 6.3, n), vr=rng.uniform(-7, 7, n),
                         col=[C.MARBLE_SRGB[i] for i in rng.integers(0, len(C.MARBLE_SRGB), n)],
                         w=rng.uniform(10, 18, n) * self.k)
        self.bump = {}
        land = tl["land"]
        for t, _, b, *_ in land:
            self.bump.setdefault(int(b), []).append(float(t))

    def px(self, p):
        x, y, _ = S.project(p)
        return x, y

    def text(self, dr, s, cx, cy, px, fill, scale=1.0, alpha=255, stroke=None):
        px = max(4, int(round(px * self.k * scale)))
        f = font(px)
        sw = max(1, int(round(stroke if stroke is not None else 0.11 * px)))
        bb = dr.textbbox((0, 0), s, font=f, stroke_width=sw)
        dr.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), s, font=f, fill=(*fill, alpha),
                stroke_width=sw, stroke_fill=(16, 12, 24, alpha))

    def status(self, t):
        tl = self.tl
        if t >= tl["t_win"]:
            return None
        cur = [(tt, b) for tt, b in tl["leads"] if tt <= t]
        if not cur:
            return (C.SUBTITLE, 64, (255, 205, 70), 0.0)
        tt, b = cur[-1]
        if t - tt < 1.6:
            return ("TIED!" if b < 0 else f"BIN {b + 1} TAKES THE LEAD!", 64, (255, 255, 255), tt)
        if b < 0:
            return ("IT'S A TIE!", 60, (255, 255, 255), tt + 1.6)
        return (f"BIN {b + 1} IS WINNING", 56, (255, 255, 255), tt + 1.6)

    def pile_top(self, f, b):
        return float(self.tl["tops"][f, b])

    def render(self, f, title=True, watermark=True):
        img = self.comp.render(f, title=False, watermark=False)
        if not self.hud:
            return img
        t = f / C.FPS
        tl = self.tl
        im = Image.fromarray(img).convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        W, H = C.W, C.H
        self.text(dr, C.TITLE, W / 2, H * 0.112, 86, (255, 255, 255))
        st = self.status(t)
        if st:
            s, px, col, t0 = st
            self.text(dr, s, W / 2, H * 0.158, px, col, pop_scale(t - t0))
        win = t >= tl["t_win"]
        for b in range(C.BINS):
            n = int(tl["counts"][f, b])
            xb = S.BIN_X[b]
            x, y = self.px((xb, self.pile_top(f, b) + 1.9, C.PEG_DEPTH))
            last = [tt for tt in self.bump.get(b, []) if tt <= t]
            sc = pop_scale(t - last[-1]) if last else 1.0
            gold = win and b == tl["winner"]
            if gold:
                sc *= 1.0 + 0.08 * math.sin((t - tl["t_win"]) * 7)
            self.text(dr, str(n), x, y, 66 if gold else 54, WIN_COL if gold else (255, 255, 255), sc)
            xl, yl = self.px((xb, C.BIN_FLOOR_Y - 1.4, C.PEG_DEPTH + 1.6))
            r = 34 * self.k
            dr.ellipse([xl - r, yl - r, xl + r, yl + r], fill=(*(WIN_COL if gold else (24, 18, 30)), 235))
            self.text(dr, str(b + 1), xl, yl + 1, 46, (24, 18, 30) if gold else (255, 255, 255), stroke=0)
        if watermark:
            self.text(dr, C.WATERMARK, W / 2, H * 0.988, 30, (236, 242, 250), alpha=150, stroke=0)
        if win:
            dt = t - tl["t_win"]
            self.crown(im, f, dt)
            s = pop_scale(dt)
            bw, bh = 560 * self.k * s, 112 * self.k * s
            cx, cy = W / 2, H * 0.205
            dr.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=22 * self.k * s,
                                 fill=(28, 24, 34, 225))
            self.text(dr, C.WIN_TEXT.format(n=tl["winner"] + 1), cx, cy, 80, WIN_COL, s, stroke=5 * self.k * s)
            self.confetti(dr, dt)
        return np.asarray(Image.alpha_composite(im, lay).convert("RGB"))

    def crown(self, im, f, dt):
        b = self.tl["winner"]
        top = self.pile_top(f, b)
        x0, y0 = self.px((S.BIN_X[b], top + 5.6, C.PEG_DEPTH))
        x1, _ = self.px((S.BIN_X[b] + 1.0, top + 5.6, C.PEG_DEPTH))
        pr = abs(x1 - x0)
        s = pop_scale(dt - 0.15) if dt > 0.15 else 0.0
        if s <= 0:
            return
        spr = crown_sprite()
        w = 6.0 * pr * s
        h = w * spr.height / spr.width
        spr = spr.resize((max(2, int(w)), max(2, int(h))), Image.LANCZOS)
        paste_rgba(im, spr, x0 - spr.width / 2, y0 - pr * 0.15 * math.sin(dt * 5.0) - spr.height / 2)

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
    glows = []
    peg_glow = np.clip(S.PEG_GLOW_LIN * 1.6, 0, None)
    for p in range(len(S.PEGS)):
        h = tl["hits"][tl["hits"][:, 2] == p]
        evs = [(float(t), float(min(1.0, sp / 14.0) * 0.9 + 0.1), 0.22) for t, _, _, _, sp, _ in h]
        glows.append(dict(oid=S.OID_PEG0 + p, col=peg_glow, events=evs))
    comp = CO.Compositor(GPREFIX, tl["pos"], tl["vis"], tl["colors"], glows, titles=[], watermark=None)
    return Frames(tl, comp, hud)


def pick_thumb_frame(tl):
    """Late in the drop: the frame with the most marbles among the pegs, while the bins are well filled."""
    pos, vis = tl["pos"], tl["vis"]
    in_pegs = (vis & (pos[..., 1] > S.BIN_TOP) & (pos[..., 1] < S.MOUTH_Y - 1.5)).sum(1)
    filled = tl["counts"].sum(1)
    score = np.where(filled > 0.55 * C.N, in_pegs, -1)
    return int(np.argmax(score))


def main():
    os.makedirs(C.BUILD, exist_ok=True)
    tl = timeline()
    if args.worker:                        # the main process has rendered the static set already
        fr = make_frames(tl)
        sys.exit(CO.render_video(fr, int(args.worker[0]), int(args.worker[1]), args.worker[2], C.CRF))
    log(f"timeline: {tl['n_frames']} frames ({tl['n_frames'] / C.FPS:.2f} s), final counts {tl['final']}, "
        f"winner bin {tl['winner'] + 1}, last landing {tl['t_last']:.2f} s, lead changes {len(tl['leads'])}")
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
    fr = make_frames(tl, hud=False)
    f = args.thumb_frame if args.thumb_frame is not None else pick_thumb_frame(tl)
    out = os.path.join(C.BUILD, "thumbnail.png")
    Image.fromarray(fr.render(f)).save(out)
    log(f"thumbnail (frame {f}) -> {out}")


if __name__ == "__main__":
    main()
