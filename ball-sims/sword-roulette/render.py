"""Sword Roulette renderer: composes the ball-sims props into 1080x1920 frames.

  python render.py still 2.0 12.1 33.2        -> stills/fNNNNN.png at those video seconds
  python render.py range 0 300 out/s1.mp4     -> encode frames [0, 300) with ffmpeg
"""
import os
import subprocess
import sys

import cairo

_HERE = os.path.dirname(os.path.abspath(__file__))
for _dep in ("style-kit", "arena-board", "color-chips", "glossy-ball", "sword", "roulette-spinner",
             "battle-fx", "winner-card", "subscribe-cta"):
    sys.path.append(os.path.join(_HERE, "..", _dep))

import settings as S  # noqa: E402
import sim  # noqa: E402
import timeline as T  # noqa: E402
import arena_board as board  # noqa: E402
import battle_fx as fx  # noqa: E402
import color_chips as chips  # noqa: E402
import subscribe_cta as cta  # noqa: E402
import winner_card as wc  # noqa: E402
from glossy_ball import draw_ball  # noqa: E402
from kit import GOLD, HIGHLIGHT, check_fonts, clamp, ease_out_back  # noqa: E402
from sword import draw_sword, draw_trail  # noqa: E402

W, H, FPS = S.W, S.H, S.FPS
CX, CY, R = sim.CX, sim.CY, sim.ARENA_R
BR = sim.DEFAULT["ball_r"]
COLORS, NAMES = S.COLORS, S.NAMES
V_FIGHT = T.V_FIGHT
SMALL, BIG = sim.DEFAULT["small"], sim.DEFAULT["big"]


class Renderer:
    def __init__(self, tl):
        self.tl = tl
        self.base = board.make_background(S.TITLE, S.SUBTITLE)
        self.floor = board.make_floor(CX, CY, R)
        self.parts = []
        for idx, e in enumerate(tl.events):
            col = COLORS[NAMES[e["j"]]] if e["type"] in ("hit", "kill") else None
            self.parts.append(fx.make_particles(e["type"], idx, big=e["big"], color=col))
        self.hp_ev = {i: [] for i in range(tl.n)}
        for e in tl.events:
            if e["type"] == "hit":
                self.hp_ev[e["j"]].append((e["v"], e["hp"] + e["dmg"], e["hp"]))
        self.kill_v = {e["j"]: e["v"] for e in tl.kills}
        self.kill_ev = {e["j"]: e for e in tl.kills}
        self.confetti = wc.make_confetti(wc.default_palette())

    def is_dead(self, i, v):
        return i in self.kill_v and v >= self.kill_v[i]

    # ---- chips row
    def draw_chips(self, ctx, v, pointed=None):
        tl = self.tl
        specs = []
        for i, n in enumerate(NAMES):
            dead = self.is_dead(i, v)
            cur, trail = chips.hp_with_trail(self.hp_ev[i], v, tl.P["hp"])
            border = None
            if v >= tl.v_reveal and i == tl.winner:
                border = ((255, 214, 80), 4.5)
            elif i == pointed:
                border = ((255, 255, 255), 4)
            elif v >= T.FLY_END and i == tl.chosen and not dead:
                border = (GOLD, 4)
            tag = None
            if v >= T.FLY_END and i == tl.chosen:
                tag = dict(text=S.BIG_TAG, scale=ease_out_back((v - T.FLY_END) / 0.35, 2.0), dim=dead)
            specs.append(dict(name=n, color=COLORS[n], hp=cur, trail=trail, dead=dead, border=border, tag=tag))
        chips.draw_chips(ctx, specs, max_hp=tl.P["hp"])

    def draw_bottom(self, ctx, v):
        m = self.tl.bottom_text(v)
        if not m:
            return
        v0, v1, kind, payload = m
        board.draw_message(ctx, kind, payload, v - v0, v1 - v, v, first=v0 <= 0)

    # ---- fight arena
    def trail_samples(self, s, i):
        out = []
        for k in range(0, 9):
            sk = s - k * 0.014
            if sk < 0:
                break
            xs, ys, ts, hp, al = self.tl.state(sk)
            if not al[i]:
                break
            out.append((xs[i], ys[i], ts[i]))
        return out

    def draw_fight_arena(self, ctx, v):
        tl = self.tl
        s = tl.s_of_v(v)
        xs, ys, ts, hp, al = tl.state(s)
        reveal = v >= tl.v_reveal
        # sword fly-off for knocked-out balls
        for j, e in self.kill_ev.items():
            age = s - e["t"]
            if 0 <= age < 0.9:
                th0 = tl.state(max(0, e["t"] - tl.dt))[2][j]
                fx.draw_sword_flyoff(ctx, e["x"], e["y"], th0, age, j == tl.chosen, COLORS[NAMES[j]],
                                     ball_r=BR, center=(CX, CY))
        # trails + swords
        for i in range(tl.n):
            if not al[i] or (reveal and i == tl.winner):
                continue
            big = i == tl.chosen
            draw_trail(ctx, self.trail_samples(s, i), big, ball_r=BR, dims=BIG if big else SMALL)
        for i in range(tl.n):
            if not al[i]:
                continue
            big = i == tl.chosen
            a = 1.0
            if i == tl.winner and v >= tl.v_reveal:
                a = clamp(1 - (v - tl.v_reveal) / 0.25)
                if a <= 0:
                    continue
            draw_sword(ctx, xs[i], ys[i], ts[i], BR - 2, big, COLORS[NAMES[i]], alpha=a, dims=BIG if big else SMALL)
        # balls
        for i in range(tl.n):
            if not al[i] or (reveal and i == tl.winner):
                continue
            flash = 0.0
            for (vh, b, a_) in self.hp_ev[i]:
                if 0 <= v - vh < 0.16:
                    flash = max(flash, 1 - (v - vh) / 0.16)
            cur, _ = chips.hp_with_trail(self.hp_ev[i], v, tl.P["hp"])
            draw_ball(ctx, xs[i], ys[i], BR, COLORS[NAMES[i]], str(cur), flash=flash)
        # particles (sim time -> they slow down in slow motion)
        for idx, e in enumerate(tl.events):
            if e["t"] <= s < e["t"] + fx.HORIZON:
                col = COLORS[NAMES[e["j"]]] if e["type"] == "kill" else None
                fx.draw_burst(ctx, e["type"], e["x"], e["y"], s - e["t"], self.parts[idx],
                              big=e["big"], color=col, ball_r=BR)
        # damage numbers (video time so they stay readable in slow motion)
        for e in tl.events:
            if e["type"] == "hit":
                fx.draw_damage_number(ctx, e["x"], e["y"], e["dmg"], v - e["v"], e["big"])
        if T.FIGHT_TXT <= v < T.FIGHT_TXT + 1.0:
            board.draw_banner(ctx, S.BANNER_FIGHT, v - T.FIGHT_TXT, 1.0, HIGHLIGHT, cx=CX, cy=CY)
        dl = S.DUEL_BANNER_DELAY
        if tl.v_duel and tl.v_duel + dl <= v < tl.v_duel + dl + 1.1:
            board.draw_banner(ctx, S.BANNER_DUEL, v - tl.v_duel - dl, 1.1, HIGHLIGHT, size=104, cx=CX, cy=CY)

    # ---- winner / outro
    def draw_winner(self, ctx, v):
        tl = self.tl
        w = tl.winner
        xs, ys, ts, hp, al = tl.state(tl.s_of_v(tl.v_reveal))
        wc.draw_winner_reveal(ctx, v - tl.v_reveal, xs[w], ys[w], COLORS[NAMES[w]], NAMES[w], str(hp[w]),
                              start_r=BR)

    def draw_outro_ui(self, ctx, v):
        tl = self.tl
        w = tl.winner
        age = v - tl.v_reveal
        wc.draw_winner_box(ctx, age, S.WIN_TITLE.format(name=NAMES[w]), COLORS[NAMES[w]], tl.win_subtitle())
        cta.draw_subscribe_cta(ctx, age, label=S.SUBSCRIBE_LABEL, next_lines=S.NEXT_LINES)

    # ---- full frame
    def frame(self, ctx, f):
        tl = self.tl
        v = f / FPS
        ctx.set_source_surface(self.base, 0, 0)
        ctx.paint()
        pointed = None
        ctx.save()
        z, px, py = (fx.zoom_cam(v, tl.v_slow, tl.v_final, (tl.kills[-1]["x"], tl.kills[-1]["y"]),
                                 S.FINAL_ZOOM, rest=(CX, CY)) if v >= V_FIGHT else (1.0, CX, CY))
        if z > 1.0005:
            ctx.translate(px, py)
            ctx.scale(z, z)
            ctx.translate(-px, -py)
        ctx.set_source_surface(self.floor, 0, 0)
        ctx.paint()
        fighting = V_FIGHT <= v < tl.v_reveal
        slow = fighting and tl.rate_at_v(v) < 0.5
        if slow:
            fx.draw_slowmo_vignette(ctx, CX, CY, R)
        # rim under the action: swords may poke out over it
        if fighting:
            board.draw_rim(ctx, board.RIM_FIGHT, glow=1.5 if slow else 1.0, cx=CX, cy=CY, r=R)
        else:
            board.draw_rim(ctx, board.RIM_CALM, cx=CX, cy=CY, r=R)
        if v < V_FIGHT:
            pointed = tl.roulette.draw(ctx, v)
            if T.FIGHT_TXT <= v:
                board.draw_banner(ctx, S.BANNER_FIGHT, v - T.FIGHT_TXT, 1.0, HIGHLIGHT, cx=CX, cy=CY)
        else:
            ctx.save()
            dx, dy = fx.shake_offset(v, tl.events, FPS)
            ctx.translate(dx, dy)
            self.draw_fight_arena(ctx, v)
            ctx.restore()
        ctx.restore()
        if v >= tl.v_reveal:
            self.draw_winner(ctx, v)
        self.draw_chips(ctx, v, pointed)
        left, (rt, rc) = tl.status(v)
        board.draw_status(ctx, left, rt, rc)
        self.draw_bottom(ctx, v)
        if v >= tl.v_reveal:
            wc.draw_confetti(ctx, v - tl.v_reveal, self.confetti)
            self.draw_outro_ui(ctx, v)


def render_range(f0, f1, out_path):
    tl = T.Timeline()
    rd = Renderer(tl)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    tmp = out_path[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", "-r", str(FPS), tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        ctx.save()
        rd.frame(ctx, f)
        ctx.restore()
        surf.flush()
        p.stdin.write(surf.get_data())
    p.stdin.close()
    if p.wait() == 0:
        os.replace(tmp, out_path)
    else:
        raise SystemExit(f"ffmpeg failed for {out_path}")


def still(frames, outdir="stills"):
    os.makedirs(outdir, exist_ok=True)
    tl = T.Timeline()
    rd = Renderer(tl)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    for f in frames:
        ctx.save()
        rd.frame(ctx, f)
        ctx.restore()
        surf.write_to_png(os.path.join(outdir, f"f{f:05d}.png"))


if __name__ == "__main__":
    check_fonts()
    if sys.argv[1] == "still":
        still([int(round(float(a) * FPS)) for a in sys.argv[2:]])
    else:
        render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
