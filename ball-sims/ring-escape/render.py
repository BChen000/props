"""Ring Escape frames: composes the props into 1080x1920 frames.

  python render.py still 0 330 712        -> out/stills/f0000.png ... (any frame indices)
  python render.py range 0 200 out/a.mp4  -> encode frames [0, 200) with libx264
  python render.py preview                -> preview.png (frame 330, mid-race)

Draw order per frame: background (with title), then the arena layer (shaken on hits): disc,
rings, slow-mo vignette, particles, frame-0 burst ring, marbles, crown, win effects. Then the HUD:
chips, headline, status, captions, bar.
"""
import math
import os
import subprocess
import sys

import numpy as np
import skia

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ("neon-kit", "escape-rings", "neon-marble", "crown-icon", "neon-hud", "neon-fx", "battle-fx"):
    sys.path.append(os.path.join(_HERE, "..", _p))
import neon_fx as fx  # noqa: E402
import neon_hud as hud  # noqa: E402
from battle_fx import draw_slowmo_vignette_skia  # noqa: E402
from crown_icon import draw_crown  # noqa: E402
from escape_rings import draw_arena_disc, draw_rings  # noqa: E402
from neon_marble import TRAIL_DT, TRAIL_STEPS, draw_holder_ring, draw_marble, draw_trail, marble_sprite  # noqa: E402
from neon_kit import (CAPTION, CTA_CYAN, GOLD, SMALLCAP, YELLOW, back_out, clamp, ease_io, ease_out, lerp,  # noqa: E402
                      make_background, to_bgra)

import settings as S  # noqa: E402
from timeline import Race  # noqa: E402

W, H, FPS, CX, CY = S.W, S.H, S.FPS, S.CX, S.CY
NAMES, COLORS = S.NAMES, S.COLORS


class Scene:
    def __init__(self, race):
        self.r = race
        self.sprites = {name: marble_sprite(COLORS[name], r=S.MARBLE_R) for name in NAMES}
        self.bg = make_background(center=(CX, CY), title=S.TITLE, subtitle=S.SUBTITLE)
        self.show_crown = True
        self.show_holder = True

    # ------------------------------------------------------------------ frame
    def draw(self, fi):
        r = self.r
        st = r.frame_state(fi)
        reset = st["phase"] == "reset"
        surf = skia.Surface(W, H)
        c = surf.getCanvas()
        c.drawImage(self.bg, 0, 0)
        ue = ease_io(st["u"]) if reset else 0.0
        sx, sy = (0.0, 0.0) if reset else fx.shake([(st["t"] - bt, bt) for bt in r.break_t[:-1]],
                                                     st["tau"] - r.tau_of(r.Tw))
        c.save()
        c.translate(CX + sx, CY + sy)
        c.scale(1.0, 1.0)
        c.translate(-CX, -CY)
        self.draw_arena(c, st, ue)
        c.restore()
        self.draw_hud(c, st, ue)
        return surf.makeImageSnapshot()

    # ------------------------------------------------------------------ arena layer
    def draw_arena(self, c, st, ue):
        r = self.r
        t, tau = st["t"], st["tau"]
        reset = st["phase"] == "reset"
        NR = r.NR
        draw_arena_disc(c, CX, CY, r.radii[-1])
        nb = r.n_broken(t)
        cur = min(nb, NR - 1)
        won = t >= r.Tw
        gaps = [r.gaps[k] for k in range(NR - 1)] + [r.final_gap(t)]
        broken_age = [(t - r.break_t[k]) if (k < NR - 1 and r.break_t[k] <= t) else None for k in range(NR)]
        won_flash = clamp(1 - (tau - r.tau_of(r.Tw)) / 0.8) if won else None
        reset_info = dict(u=st["u"], ue=ue, phases0=r.phi0, gaps0=r.gaps) if reset else None
        draw_rings(c, CX, CY, r.radii, r.phi(t), gaps, broken_age, cur, final_active=nb >= NR - 1,
                   pulse_tau=tau, won_flash=won_flash, reset=reset_info)
        if not reset and st["rate"] < 0.999:
            ex, ey = r.pos(r.Tw)[r.winner]
            draw_slowmo_vignette_skia(c, CX + ex * 0.8, CY + ey * 0.8, clamp((1 - st["rate"]) / (1 - S.SLOWMO_RATE)))
        if not reset:
            for (bt, i, k, xy) in r.breaks[:-1]:
                fx.burst(c, CX + xy[0], CY + xy[1], COLORS[NAMES[i]], t - bt, bt)
            for (et, xy, sp, i, j) in r.mm:
                if sp >= fx.SPARK_MIN_SPEED and et >= t - 0.3 and et <= t:
                    fx.sparks(c, CX + xy[0], CY + xy[1], t - et, et)
            for (et, i, k, sp, xy) in r.ends:
                if k == NR - 1:
                    fx.edge_sparks(c, CX + xy[0], CY + xy[1], t - et, et)
        if st["phase"] == "race":
            fx.start_ring(c, CX, CY, tau)
        self.draw_marbles(c, st, ue)
        if self.show_crown:
            p, s = self.crown_pos(st, ue)
            draw_crown(c, CX + p[0], CY + p[1], s, 1.0, glow=0.6)
        if not reset:
            d = tau - r.tau_of(r.Tw)
            if d >= 0:
                ex, ey = r.pos(r.Tw)[r.winner]
                fx.shockwave(c, CX + ex, CY + ey, d)
                fx.confetti(c, CX + ex, CY + ey, d, colors=[COLORS[n] for n in NAMES])

    def marble_positions(self, st, ue):
        p = self.r.pos(st["t"])
        if st["phase"] == "reset":
            p0 = self.r.P[0]
            return p + (p0 - p) * ue
        return p

    def draw_marbles(self, c, st, ue):
        r = self.r
        t = st["t"]
        reset = st["phase"] == "reset"
        pos = self.marble_positions(st, ue)
        won = (t >= r.Tw) and not reset
        if not reset:
            for i in range(S.N_MARBLES):
                pts = []
                for j in range(1, TRAIL_STEPS + 1):
                    tt = t - j * TRAIL_DT
                    if tt < 0:
                        break
                    q = r.pos(tt)[i]
                    pts.append((CX + q[0], CY + q[1]))
                draw_trail(c, pts, COLORS[NAMES[i]], r=S.MARBLE_R, dim=won and i != r.winner)
        h = r.holder(t) if (not reset and self.show_holder) else None
        for i in range(S.N_MARBLES):
            x, y = CX + pos[i][0], CY + pos[i][1]
            if h is not None and h[1] == i:
                draw_holder_ring(c, x, y, st["tau"], r=S.MARBLE_R, winner_glow=won and i == r.winner)
            draw_marble(c, self.sprites[NAMES[i]], x, y, dim=won and i != r.winner)

    def crown_pos(self, st, ue):
        """Crown position relative to the arena centre, and its scale."""
        r = self.r
        t = st["t"]
        pos = self.marble_positions(st, ue)
        off = S.MARBLE_R + 19
        if st["phase"] == "reset":
            w = pos[r.winner]
            start = np.array([w[0], w[1] - off])
            return start * (1 - ue), lerp(1.15, 1.35, ue)
        hist = [b for b in r.breaks if b[0] <= t]
        if not hist:
            return np.array([0.0, 0.0]), 1.35
        b = hist[-1]
        target = pos[b[1]] + np.array([0.0, -off])
        if len(hist) == 1:
            src = np.array([0.0, 0.0])
        else:
            pb = hist[-2]
            src = r.pos(b[0])[pb[1]] + np.array([0.0, -off])
        x = ease_io((st["tau"] - r.tau_of(b[0])) / 0.3)
        s = 1.0 + (0.35 * (1 - x) if len(hist) == 1 else 0.0)
        if t >= r.Tw:
            s = 1.0 + 0.2 * ease_out((st["tau"] - r.tau_of(r.Tw)) / 0.3)
        return src + (target - src) * x, s

    # ------------------------------------------------------------------ HUD
    def draw_hud(self, c, st, ue):
        r = self.r
        t, tau = st["t"], st["tau"]
        reset = st["phase"] == "reset"
        won_sim = t >= r.Tw and not reset
        pops = [0.0] * S.N_MARBLES
        if not reset:
            for b in r.breaks:
                dd = t - b[0]
                if 0 <= dd < 0.45:
                    pops[b[1]] = max(pops[b[1]], 1 - dd / 0.45)
        h = r.holder(t) if not reset else None
        hud.draw_chips(c, NAMES, COLORS, r.counts(t) if not reset else [0] * S.N_MARBLES,
                       holder=(h[1] if h is not None else None), winner=(r.winner if won_sim else None), pops=pops)
        nb = r.n_broken(t)
        left = r.NR - nb
        tw_tau = r.tau_of(r.Tw)
        won = tau >= tw_tau and not reset
        if reset:
            fade = ease_io((st["u"] - 0.25) / 0.6)
            self.headline_win(c, tau, tw_tau, alpha=1 - fade)
            hud.draw_intro(c, S.INTRO_1, S.INTRO_2, alpha=fade)
            hud.draw_captions(c, S.CAP_START[0], CAPTION, S.CAP_START[1], SMALLCAP, alpha=fade)
            hud.draw_captions(c, S.CAP_WIN[0], YELLOW, S.CAP_WIN[1], CTA_CYAN, alpha=1 - fade)
            hud.draw_bar(c, self.progress(t) * (1 - ue))
            return
        if nb == 0:
            hud.draw_intro(c, S.INTRO_1, S.INTRO_2, alpha=1.0)
        elif won:
            self.headline_win(c, tau, tw_tau, 1.0)
        else:
            sc = hud.pop_scale(tau - r.tau_of(r.breaks[nb - 1][0]), 0.28, 1.45)
            if left == 1:
                hud.draw_last_ring(c, tau, scale=sc, text=S.LAST_RING)
            else:
                hud.draw_count(c, left, scale=sc)
            hname = NAMES[h[1]]
            hud.draw_status(c, S.RINGS_LEFT.format(n=left) if left > 1 else S.ONE_RING_LEFT, hname, COLORS[hname],
                            tail=S.HAS_CROWN)
        self.captions(c, st)
        hud.draw_bar(c, self.progress(t))

    def headline_win(self, c, tau, tw_tau, alpha):
        name = NAMES[self.r.winner]
        hud.draw_win(c, name, COLORS[name], scale=hud.pop_scale(tau - tw_tau, 0.35, 1.6), alpha=alpha,
                     sub=S.WIN_SUB, sub_alpha=clamp((tau - tw_tau - 0.25) / 0.2))

    def progress(self, t):
        prog = 0.0
        for bt in self.r.break_t:
            prog += ease_out((t - bt) / 0.3) / self.r.NR
        return prog

    def captions(self, c, st):
        r = self.r
        t, tau = st["t"], st["tau"]
        tw_tau = r.tau_of(r.Tw)
        if tau >= tw_tau:
            hud.draw_captions(c, S.CAP_WIN[0], YELLOW, S.CAP_WIN[1], CTA_CYAN, alpha=clamp((tau - tw_tau - 0.3) / 0.25))
            return
        nb = r.n_broken(t)
        (big, small), bigc, smallc = S.CAP_START, CAPTION, SMALLCAP
        if nb >= 1:
            big, small = S.CAP_RACE
        if nb >= r.NR - 1:
            big, small = S.CAP_FINAL
        pop = None
        for (bt, i, k, xy) in r.breaks[:-1]:
            bt_tau = r.tau_of(bt)
            if 0 <= tau - bt_tau < S.CAP_BREAK_SECONDS:
                big, bigc = S.CAP_BREAK.format(name=NAMES[i]), COLORS[NAMES[i]]
                pop = tau - bt_tau
                if k == r.NR - 2:
                    big, bigc = S.CAP_FINAL_RING, GOLD
        for (nt, i, xy) in r.near:
            nt_tau = r.tau_of(nt)
            if 0 <= tau - nt_tau < S.CAP_NEAR_SECONDS:
                big, bigc = S.CAP_NEAR.format(name=NAMES[i]), COLORS[NAMES[i]]
                pop = tau - nt_tau
        sc = lerp(1.3, 1.0, back_out(pop / 0.22)) if (pop is not None and pop < 0.22) else 1.0
        hud.draw_captions(c, big, bigc, small, smallc, scale=sc)


def render_range(a, b, out):
    scene = Scene(Race())
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", S.PRESET, "-crf", str(S.CRF), "-pix_fmt", "yuv420p",
           "-g", "60", "-bf", "0", "-movflags", "+faststart", tmp]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(a, b):
        pr.stdin.write(to_bgra(scene.draw(fi)).tobytes())
    pr.stdin.close()
    if pr.wait() != 0:
        raise SystemExit("ffmpeg failed")
    os.replace(tmp, out)


def preview(path, frame=330):
    """One full-size still: frame 330 (11 s), mid-race, GREEN has the crown, 4 rings left."""
    Scene(Race()).draw(frame).save(path, skia.kPNG)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "still":
        scene = Scene(Race())
        d = os.path.join(S.OUT_DIR, "stills")
        os.makedirs(d, exist_ok=True)
        for fs in sys.argv[2:]:
            scene.draw(int(fs)).save(os.path.join(d, f"f{int(fs):04d}.png"), skia.kPNG)
        print("wrote", len(sys.argv) - 2, "stills to", os.path.relpath(d, _HERE))
    elif cmd == "range":
        render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == "preview":
        preview(os.path.join(_HERE, "preview.png"))
        print("wrote preview.png")
