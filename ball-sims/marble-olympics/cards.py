"""The Marble Olympics look at 1920x1080: cards, the broadcast frame around each event, standings and transitions.

Drawn with pycairo in the style-kit look (purple-to-black background, Poppins, pink titles) with the glossy-ball,
crown-icon and subscribe-cta props. Every card is a function of (ctx, t, ...) where t is seconds into the card.
"""
import math
import os
import sys

import cairo
import numpy as np

import settings as S

for _dep in ("style-kit", "glossy-ball", "crown-icon", "subscribe-cta"):
    sys.path.append(os.path.join(S.BALL_SIMS, _dep))
from crown_icon import draw_crown_cairo  # noqa: E402
from glossy_ball import draw_ball  # noqa: E402
from kit import (GOLD, HIGHLIGHT, STATUS_PINK, SUBTITLE, TITLE_OUTLINE, TITLE_PINK, TITLE_SHADOW, WHITE, clamp,  # noqa: E402
                 ease_in_out, ease_out, ease_out_back, rgb, rounded_rect, text)
from subscribe_cta import draw_subscribe_cta  # noqa: E402

W, H = S.W, S.H
CX = W / 2
PI = math.pi
DIM = (176, 160, 204)
ORD = ["1st", "2nd", "3rd", "4th"]
PANEL_X = (W - S.PANEL_W) // 2


def col(team):
    return S.TEAM_COLORS[team]


def kit_hex(c):
    return "#%02x%02x%02x" % tuple(c)


def pop(t, t0, d=0.38):
    return ease_out_back(clamp((t - t0) / d), 1.9)


def fade(t, t0, d=0.3):
    return ease_out(clamp((t - t0) / d))


def new_surface():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    return surf, cairo.Context(surf)


def background(ctx, glow=True):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0.0, 30 / 255, 12 / 255, 51 / 255)
    g.add_color_stop_rgb(0.45, 25 / 255, 10 / 255, 43 / 255)
    g.add_color_stop_rgb(1.0, 9 / 255, 4 / 255, 20 / 255)
    ctx.set_source(g)
    ctx.paint()
    if glow:
        r = cairo.RadialGradient(CX, H * 0.42, 40, CX, H * 0.42, W * 0.55)
        r.add_color_stop_rgba(0, 0.62, 0.25, 0.75, 0.22)
        r.add_color_stop_rgba(1, 0.62, 0.25, 0.75, 0.0)
        ctx.set_source(r)
        ctx.paint()


def title(ctx, s, x, y, size, color=TITLE_PINK, scale=1.0, alpha=1.0, font="blk"):
    if scale <= 0.01:
        return
    text(ctx, s, x, y, font, size, color, outline=TITLE_OUTLINE, ow=size * 0.07, alpha=alpha, scale=scale,
         shadow=(0, size * 0.07, TITLE_SHADOW, 0.85))


def line(ctx, s, x, y, size, color=SUBTITLE, alpha=1.0, font="sb", align="c", scale=1.0):
    if scale <= 0.01:
        return
    text(ctx, s, x, y, font, size, color, align=align, outline=TITLE_OUTLINE, ow=size * 0.05, alpha=alpha, scale=scale)


def ball(ctx, x, y, r, team, scale=1.0, alpha=1.0, label=None):
    if scale <= 0.02 or alpha <= 0.01:
        return
    draw_ball(ctx, x, y, r * scale, col(team), label, label_size=r * scale * 0.75, alpha=alpha)


def medal(ctx, x, y, r, place, scale=1.0):
    m = S.MEDALS[place]
    if m is None or scale <= 0.02:
        return
    r *= scale
    ctx.save()
    ctx.arc(x, y + r * 0.12, r, 0, 2 * PI)
    ctx.set_source_rgba(0, 0, 0, 0.35)
    ctx.fill()
    g = cairo.LinearGradient(x, y - r, x, y + r)
    g.add_color_stop_rgb(0, *[min(1.0, c / 255 * 1.18) for c in m])
    g.add_color_stop_rgb(1, *[c / 255 * 0.72 for c in m])
    ctx.arc(x, y, r, 0, 2 * PI)
    ctx.set_source(g)
    ctx.fill()
    ctx.arc(x, y, r * 0.78, 0, 2 * PI)
    ctx.set_source_rgba(1, 1, 1, 0.25)
    ctx.set_line_width(r * 0.08)
    ctx.stroke()
    ctx.restore()
    text(ctx, str(place + 1), x, y, "blk", r * 1.05, (60, 36, 10) if place == 0 else (40, 40, 52))


def pill(ctx, x, y, w, h, fill, alpha=1.0):
    rounded_rect(ctx, x - w / 2, y - h / 2, w, h, h / 2)
    ctx.set_source_rgba(*rgb(fill, alpha))
    ctx.fill()


def team_row(ctx, y, r, t0, t, gap=None):
    gap = gap or r * 3.3
    x0 = CX - 1.5 * gap
    for i, team in enumerate(S.TEAMS):
        ball(ctx, x0 + i * gap, y, r, team, scale=pop(t, t0 + 0.08 * i))


# --------------------------------------------------------------------------- full-screen cards
def hero(ctx, img, t, dur, dark=0.5, shift=0.395):
    """The 500-marble milestone render as a slowly zooming 16:9 background."""
    s = 1.0 + 0.06 * t / max(dur, 1e-6)
    ih, iw = img.get_height(), img.get_width()
    k = W / iw * s
    ctx.save()
    ctx.translate(CX, H / 2)
    ctx.scale(k, k)
    ctx.translate(-iw / 2, -ih * shift)
    ctx.set_source_surface(img, 0, 0)
    ctx.paint()
    ctx.restore()
    ctx.set_source_rgba(0.04, 0.015, 0.08, dark)
    ctx.paint()


def card_title(ctx, t, dur, img):
    hero(ctx, img, t, dur, dark=0.28, shift=0.37)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgba(0, 0.05, 0.02, 0.1, 0.75)
    g.add_color_stop_rgba(0.3, 0.05, 0.02, 0.1, 0.0)
    g.add_color_stop_rgba(0.72, 0.05, 0.02, 0.1, 0.0)
    g.add_color_stop_rgba(1, 0.05, 0.02, 0.1, 0.8)
    ctx.set_source(g)
    ctx.paint()
    title(ctx, S.SHOW, CX, 150, 150, scale=pop(t, 0.25, 0.5))
    title(ctx, S.SPECIAL, CX, 948, 76, color=GOLD, scale=pop(t, 0.9, 0.45))


def card_thanks(ctx, t, dur, img):
    hero(ctx, img, t + 7.0, dur + 7.0, dark=0.72)
    title(ctx, S.THANKS[0], CX, 470, 96, color=WHITE, scale=pop(t, 0.1))
    line(ctx, S.THANKS[1], CX, 600, 50, alpha=fade(t, 0.7))


def card_teams(ctx, t, dur):
    background(ctx)
    title(ctx, "MEET THE TEAMS", CX, 150, 96, scale=pop(t, 0.05))
    gap = 400
    x0 = CX - 1.5 * gap
    for i, team in enumerate(S.TEAMS):
        t0 = 0.55 + 0.45 * i
        x = x0 + i * gap
        ball(ctx, x, 480, 125, team, scale=pop(t, t0, 0.45))
        line(ctx, "TEAM " + team, x, 680, 54, color=col(team), font="blk", scale=pop(t, t0 + 0.12))
    title(ctx, S.PICK[0], CX, 870, 84, color=STATUS_PINK, scale=pop(t, 2.7))
    line(ctx, S.PICK[1], CX, 965, 44, alpha=fade(t, 3.1))


def card_rules(ctx, t, dur):
    background(ctx)
    title(ctx, "HOW TO WIN", CX, 130, 92, scale=pop(t, 0.05))
    for i in range(3):
        y = 330 + i * 150
        medal(ctx, 330, y, 52, i, scale=pop(t, 0.45 + 0.25 * i))
        line(ctx, "%s PLACE" % ORD[i].upper(), 420, y, 52, color=WHITE, font="blk", align="l",
             alpha=fade(t, 0.5 + 0.25 * i))
        line(ctx, "+%d" % S.POINTS[i], 860, y, 62, color=S.MEDALS[i], font="blk", align="r",
             alpha=fade(t, 0.5 + 0.25 * i))
    pill(ctx, 595, 800, 720, 96, GOLD, alpha=fade(t, 1.5))
    text(ctx, "GRAND FINAL = DOUBLE POINTS", 595, 800, "blk", 38, (60, 30, 6), alpha=fade(t, 1.5))
    line(ctx, "THE EVENTS", 1390, 250, 48, color=STATUS_PINK, font="blk", alpha=fade(t, 0.9))
    for i, ev in enumerate(S.EVENTS):
        y = 360 + i * 105
        a = fade(t, 1.1 + 0.22 * i)
        pill(ctx, 1110, y, 70, 70, GOLD if ev.get("double") else (78, 46, 120), alpha=a)
        text(ctx, str(i + 1), 1110, y, "blk", 40, (60, 30, 6) if ev.get("double") else WHITE, alpha=a)
        line(ctx, ev["name"], 1170, y, 46, color=GOLD if ev.get("double") else WHITE, font="xb", align="l", alpha=a)


def card_intro(ctx, t, dur, k):
    ev = S.EVENTS[k]
    background(ctx)
    final = ev.get("double")
    line(ctx, "THE FINAL EVENT" if final else "EVENT %d OF %d" % (k + 1, len(S.EVENTS)), CX, 255, 54,
         color=STATUS_PINK, font="blk", scale=pop(t, 0.05))
    title(ctx, ev["name"], CX, 430, 150 if final else 140, color=GOLD if final else WHITE, scale=pop(t, 0.3, 0.45))
    if final:
        line(ctx, "500 MARBLES: ONE FOR EVERY SUBSCRIBER", CX, 580, 52, color=WHITE, font="xb", alpha=fade(t, 0.8))
        line(ctx, "Last color left WINS", CX, 660, 46, alpha=fade(t, 1.1))
        pill(ctx, CX, 790, 460, 90, GOLD, alpha=fade(t, 1.5))
        text(ctx, "DOUBLE POINTS", CX, 790, "blk", 46, (60, 30, 6), alpha=fade(t, 1.5))
    else:
        line(ctx, ev["rule"], CX, 590, 54, alpha=fade(t, 0.8))
        team_row(ctx, 790, 58, 1.1, t)


def podium(ctx, t, k, places):
    ev = S.EVENTS[k]
    mult = 2 if ev.get("double") else 1
    background(ctx)
    line(ctx, "%s RESULTS" % ("GRAND FINAL" if ev.get("double") else "EVENT %d" % (k + 1)), CX, 95, 50,
         color=STATUS_PINK, font="blk", scale=pop(t, 0.0))
    title(ctx, ev["name"], CX, 190, 86, color=GOLD if ev.get("double") else WHITE, scale=pop(t, 0.12))
    spots = [(CX, 300, 1), (CX - 380, 220, 0), (CX + 380, 150, 2)]   # (x, block height, place) 1st, 2nd, 3rd
    base = 960
    rise = ease_out(clamp(t / 0.6))
    for x, h, _ in [(CX - 380, 220, 1), (CX, 300, 0), (CX + 380, 150, 2)]:
        hh = h * rise
        rounded_rect(ctx, x - 165, base - hh, 330, hh + 40, 18)
        ctx.set_source_rgba(0.33, 0.19, 0.52, 0.95)
        ctx.fill()
    order = [2, 1, 0]                                      # reveal 3rd, then 2nd, then 1st
    xs = {0: CX, 1: CX - 380, 2: CX + 380}
    hs = {0: 300, 1: 220, 2: 150}
    for n, place in enumerate(order):
        t0 = 0.7 + 0.75 * n
        x, h = xs[place], hs[place]
        team = places[place]
        top = base - h
        medal(ctx, x, top + 62, 42, place, scale=pop(t, t0 - 0.1))
        drop = ease_out_back(clamp((t - t0) / 0.45), 1.6)
        if t >= t0:
            ball(ctx, x, top - 95 - 220 * (1 - drop), 92, team)
        line(ctx, "+%d" % (S.POINTS[place] * mult), x, top + 150, 66, color=WHITE, font="blk", scale=pop(t, t0 + 0.35))
        line(ctx, "TEAM " + team, x, top - 230, 40, color=col(team), font="blk", alpha=fade(t, t0 + 0.3))
    t4 = 3.05
    ball(ctx, 1700, 900, 48, places[3], scale=pop(t, t4))
    line(ctx, "4th  +0", 1700, 990, 38, color=DIM, font="xb", alpha=fade(t, t4 + 0.1))
    if mult == 2:
        pill(ctx, 230, 900, 250, 80, GOLD, alpha=fade(t, 0.4))
        text(ctx, "x2 POINTS", 230, 900, "blk", 38, (60, 30, 6), alpha=fade(t, 0.4))


def ranks(totals):
    """1-based rank with ties sharing a rank, in team order for equal totals."""
    order = sorted(S.TEAMS, key=lambda tm: (-totals[tm], S.TEAMS.index(tm)))
    return order, {tm: 1 + sum(1 for o in S.TEAMS if totals[o] > totals[tm]) for tm in S.TEAMS}


def standings_table(ctx, x, y, w, row_h, prev, new, u, title_txt=None, alpha=1.0, bar_max=None):
    """Bars that grow from prev to new totals (u = 0..1), sorted by the new totals."""
    order, rk = ranks(new)
    bar_max = bar_max or max(12, max(new.values()))
    tied_top = sum(1 for tm in S.TEAMS if rk[tm] == 1) > 1
    if title_txt:
        line(ctx, title_txt, x + w / 2, y - row_h * 0.75, row_h * 0.42, color=STATUS_PINK, font="blk", alpha=alpha)
    for i, tm in enumerate(order):
        yy = y + i * row_h
        val = prev[tm] + (new[tm] - prev[tm]) * u
        lab = ORD[rk[tm] - 1]
        line(ctx, lab, x + row_h * 0.55, yy, row_h * 0.3, color=WHITE if rk[tm] == 1 else DIM, font="blk",
             alpha=alpha)
        ball(ctx, x + row_h * 1.45, yy, row_h * 0.33, tm, alpha=alpha)
        bx, bw, bh = x + row_h * 2.05, w - row_h * 2.05, row_h * 0.46
        rounded_rect(ctx, bx, yy - bh / 2, bw, bh, bh / 2)
        ctx.set_source_rgba(1, 1, 1, 0.08 * alpha)
        ctx.fill()
        fw = max(bh, bw * min(1.0, val / bar_max))
        rounded_rect(ctx, bx, yy - bh / 2, fw, bh, bh / 2)
        ctx.set_source_rgba(*rgb(col(tm), 0.95 * alpha))
        ctx.fill()
        text(ctx, "%d" % round(val), bx + fw - bh * 0.55, yy, "blk", bh * 0.62, WHITE, align="r",
             outline=TITLE_OUTLINE, ow=2, alpha=alpha)
        if rk[tm] == 1 and not tied_top and u >= 1.0:
            draw_crown_cairo(ctx, x + row_h * 1.45, yy - row_h * 0.43, s=row_h * 0.006, alpha=alpha)
    return order, rk


def card_standings(ctx, t, dur, k, prev, new):
    background(ctx)
    title(ctx, "STANDINGS", CX, 120, 92, scale=pop(t, 0.0))
    last = k == len(S.EVENTS) - 1
    line(ctx, "FINAL SCORES" if last else "after event %d of %d" % (k + 1, len(S.EVENTS)), CX, 215, 44,
         alpha=fade(t, 0.2))
    u = ease_in_out(clamp((t - 0.6) / 1.4))
    standings_table(ctx, 360, 380, 1200, 150, prev, new, u)


def card_tied(ctx, t, dur, totals):
    background(ctx)
    title(ctx, S.TIED[0], CX, 210, 104, color=GOLD, scale=pop(t, 0.05, 0.45))
    gap = 400
    x0 = CX - 1.5 * gap
    for i, tm in enumerate(S.TEAMS):
        t0 = 0.6 + 0.18 * i
        ball(ctx, x0 + i * gap, 520, 110, tm, scale=pop(t, t0), label=str(totals[tm]))
    line(ctx, "%d POINTS EACH" % totals[S.TEAMS[0]], CX, 720, 56, color=WHITE, font="blk", alpha=fade(t, 1.4))
    line(ctx, S.TIED[1], CX, 840, 52, alpha=fade(t, 2.0))
    pill(ctx, CX, 950, 460, 86, GOLD, alpha=fade(t, 2.6))
    text(ctx, "DOUBLE POINTS", CX, 950, "blk", 44, (60, 30, 6), alpha=fade(t, 2.6))


def confetti(ctx, t, seed=5, n=170):
    rng = np.random.default_rng(seed)
    cols = [col(tm) for tm in S.TEAMS] + [GOLD, WHITE]
    for i in range(n):
        x0 = rng.uniform(-50, W + 50)
        sp = rng.uniform(220, 420)
        y = -60 + (t - rng.uniform(0, 1.2)) * sp
        if y < -60 or y > H + 60:
            continue
        x = x0 + 40 * math.sin(t * rng.uniform(1.5, 3.5) + i)
        a = t * rng.uniform(2, 6) + i
        c = cols[i % len(cols)]
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(a)
        ctx.scale(1.0, abs(math.cos(a * 0.7)) + 0.2)
        ctx.rectangle(-9, -5, 18, 10)
        ctx.set_source_rgba(*rgb(c, 0.95))
        ctx.fill()
        ctx.restore()


def card_champion(ctx, t, dur, champ, totals, story):
    background(ctx)
    c = col(champ)
    r = cairo.RadialGradient(CX, 470, 30, CX, 470, 560)
    r.add_color_stop_rgba(0, c[0] / 255, c[1] / 255, c[2] / 255, 0.45 * fade(t, 0.8, 0.8))
    r.add_color_stop_rgba(1, c[0] / 255, c[1] / 255, c[2] / 255, 0.0)
    ctx.set_source(r)
    ctx.paint()
    line(ctx, S.SHOW + " CHAMPION", CX, 95, 52, color=GOLD, font="blk", scale=pop(t, 0.1))
    s = pop(t, 0.7, 0.6)
    ball(ctx, CX, 470, 175, champ, scale=s)
    drop = ease_out_back(clamp((t - 1.5) / 0.5), 1.5)
    if t >= 1.5:
        draw_crown_cairo(ctx, CX, 255 - 160 * (1 - drop), s=1.55, glow=1.0)
    title(ctx, "TEAM " + champ, CX, 735, 128, color=c, scale=pop(t, 1.9, 0.45))
    if story:
        line(ctx, story, CX, 845, 48, color=WHITE, font="xb", alpha=fade(t, 2.6))
    order, rk = ranks(totals)
    for i, tm in enumerate(order):
        x = CX + (i - 1.5) * 330
        a = fade(t, 3.3 + 0.15 * i)
        ball(ctx, x - 70, 975, 30, tm, alpha=a)
        line(ctx, "%s  %d" % (ORD[rk[tm] - 1], totals[tm]), x + 20, 975, 38, color=WHITE if tm == champ else DIM,
             font="blk", alpha=a)
    if t >= 1.5:
        confetti(ctx, t - 1.5)


def card_outro(ctx, t, dur, img):
    hero(ctx, img, t, dur, dark=0.74)
    title(ctx, S.OUTRO[0], CX, 210, 92, color=WHITE, scale=pop(t, 0.05))
    title(ctx, S.OUTRO[1], CX, 360, 120, color=GOLD, scale=pop(t, 0.6, 0.45))
    line(ctx, S.OUTRO[2], CX, 500, 52, color=WHITE, font="xb", alpha=fade(t, 1.2))
    if t >= 1.8:
        ctx.save()
        ctx.translate(CX - 540, 0)                # the CTA centres its prompt on the Shorts' x = 540
        draw_subscribe_cta(ctx, t - 1.8, center=(540, 720), size=(560, 120),
                           next_lines=("What should the next special be?", "Tell me in the comments!"), next_y=(880, 950))
        ctx.restore()


# --------------------------------------------------------------------------- the broadcast frame around an event
def event_frame(k, totals, results_so_far):
    """Static 1920x1080 frame for event k: show and event info on the left, standings on the right."""
    surf, ctx = new_surface()
    background(ctx, glow=False)
    ev = S.EVENTS[k]
    final = ev.get("double")
    lx = PANEL_X / 2
    title(ctx, "MARBLE", lx, 120, 70)
    title(ctx, "OLYMPICS", lx, 200, 70)
    line(ctx, S.SPECIAL, lx, 275, 30, color=GOLD, font="blk")
    line(ctx, "THE FINAL EVENT" if final else "EVENT %d OF %d" % (k + 1, len(S.EVENTS)), lx, 420, 36,
         color=STATUS_PINK, font="blk")
    words = ev["name"].split()
    if final:
        title(ctx, "GRAND", lx, 505, 82, color=GOLD)
        title(ctx, "FINAL", lx, 590, 82, color=GOLD)
        rule = ["500 marbles,", "one per subscriber.", "Last color left WINS"]
    else:
        title(ctx, " ".join(words[:-1]) or words[0], lx, 505, 72, color=WHITE)
        if len(words) > 1:
            title(ctx, words[-1], lx, 585, 72, color=WHITE)
        rule = _wrap(ev["rule"], 22)
    for i, s in enumerate(rule):
        line(ctx, s, lx, 690 + i * 52, 36)
    if final:
        pill(ctx, lx, 900, 380, 72, GOLD)
        text(ctx, "DOUBLE POINTS", lx, 900, "blk", 36, (60, 30, 6))
    else:
        for i in range(3):
            x = lx - 190 + i * 190
            medal(ctx, x - 38, 905, 26, i)
            line(ctx, "+%d" % S.POINTS[i], x + 22, 905, 38, color=WHITE, font="blk")
    rx = PANEL_X + S.PANEL_W + (W - PANEL_X - S.PANEL_W) / 2
    line(ctx, "STANDINGS", rx, 150, 52, color=STATUS_PINK, font="blk")
    tied = len(set(totals.values())) == 1 and k > 0
    line(ctx, "ALL TIED!" if tied else ("before event %d" % (k + 1) if k else "everyone starts at 0"), rx, 215, 32,
         color=GOLD if tied else DIM, font="xb")
    standings_table(ctx, PANEL_X + S.PANEL_W + 40, 340, W - PANEL_X - S.PANEL_W - 90, 140, totals, totals, 1.0)
    if results_so_far:
        line(ctx, "WINNERS SO FAR", rx, 900, 30, color=DIM, font="blk")
        n = len(results_so_far)
        for i, (ek, w) in enumerate(results_so_far):
            ball(ctx, rx + (i - (n - 1) / 2) * 92, 975, 30, w, label=str(ek + 1))
    for x in (PANEL_X - 6, PANEL_X + S.PANEL_W + 6):     # soft shadow either side of the video
        g = cairo.LinearGradient(x - 40, 0, x + 40, 0)
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(0.5, 0, 0, 0, 0.55)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.rectangle(x - 40, 0, 80, H)
        ctx.set_source(g)
        ctx.fill()
    return surf


def _wrap(s, n):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return out + [cur]


# --------------------------------------------------------------------------- transition
def wipe(ctx, u):
    """Four slanted team-colour bands sweep left to right: fully covered at u = 0.5, so a cut there is hidden."""
    if u <= 0 or u >= 1:
        return
    band, slant = 0.36 * W, 0.18 * W
    total = 4 * band
    x0 = (-total - slant) + (W + total + 2 * slant) * ease_in_out(u)
    for i, tm in enumerate(S.TEAMS[::-1]):
        a = x0 + i * band
        ctx.move_to(a + slant, 0)
        ctx.line_to(a + band + slant + 1, 0)
        ctx.line_to(a + band + 1, H)
        ctx.line_to(a, H)
        ctx.close_path()
        ctx.set_source_rgba(*rgb(col(tm), 1.0))
        ctx.fill()
