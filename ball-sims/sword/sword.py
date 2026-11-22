"""sword: the orbiting sword prop (small and BIG variants) plus its swoosh trail.

A sword is drawn in a frame that rotates with angle `th` around a ball centre (cx, cy):
pommel at r_off - 8, grip, crossguard at r_off + grip, blade out to r_off + grip + blade.
Use r_off = ball_r - 2 to attach it to a ball.
"""
import math
import os
import sys

import cairo

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style-kit"))
from kit import (BALL_COLORS, GOLD, NAMES, PI, W, lighten, new_canvas, paint_background, rgb,  # noqa: E402
                 rounded_rect, text)

# --------------------------------------------------------------------------- settings
SMALL = dict(grip=18.0, blade=100.0, width=18.0)   # px; same numbers drive the physics hitbox
BIG = dict(grip=28.0, blade=200.0, width=34.0)
GRIP_FILL = (0.30, 0.19, 0.14)                     # float RGB (= #4d3024)
INK = (0.10, 0.07, 0.18)                           # blade outline
GUARD_INK = (0.10, 0.06, 0.14)
BLADE_STOPS = [(0.0, (0.97, 0.98, 1.0)), (0.48, (0.84, 0.87, 0.94)),
               (0.52, (0.70, 0.74, 0.84)), (1.0, (0.56, 0.60, 0.72))]
FULLER = (0.55, 0.60, 0.74, 0.9)
AURA = (1.0, 0.85, 0.35)                           # big sword glow, 3 strokes
AURA_STROKES = ((34, 0.07), (22, 0.11), (12, 0.18))
TRAIL_SMALL = (200, 225, 255)
TRAIL_BIG = (255, 214, 110)
TRAIL_SAMPLES, TRAIL_DT = 9, 0.014                 # 9 past poses, 0.014 s apart (sim time)


def sword_outline_path(ctx, sw, r_off, big):
    g, L, w = sw["grip"], sw["blade"], sw["width"]
    xg = r_off + g
    sh = xg + L * (0.8 if big else 0.76)
    tip = xg + L
    ctx.move_to(xg, -w / 2)
    ctx.line_to(sh, -w / 2)
    ctx.line_to(tip, 0)
    ctx.line_to(sh, w / 2)
    ctx.line_to(xg, w / 2)
    ctx.close_path()


def draw_sword(ctx, cx, cy, th, r_off, big, col, scale=1.0, alpha=1.0, dims=None):
    """col: owner colour (small: crossguard + pommel; big: gem). dims overrides SMALL/BIG."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    sw = dims or (BIG if big else SMALL)
    g, L, w = sw["grip"], sw["blade"], sw["width"]
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(th)
    ctx.scale(scale, scale)
    if alpha < 1:
        ctx.push_group()
    xg = r_off + g
    gw = w * (0.5 if big else 0.62)
    # aura for the big sword
    if big:
        sword_outline_path(ctx, sw, r_off, big)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for lw, a in AURA_STROKES:
            ctx.set_source_rgba(AURA[0], AURA[1], AURA[2], a)
            ctx.set_line_width(lw)
            ctx.stroke_preserve()
        ctx.new_path()
    # grip
    rounded_rect(ctx, r_off - 8, -gw / 2, g + 10, gw, gw / 2.4)
    ctx.set_source_rgb(*GRIP_FILL)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.05, 0.12, 1)
    ctx.set_line_width(2.2)
    ctx.stroke()
    ctx.set_source_rgba(0.12, 0.07, 0.05, 0.9)
    ctx.set_line_width(1.6)
    xx = r_off - 2
    while xx < xg - 3:
        ctx.move_to(xx, -gw / 2 + 1)
        ctx.line_to(xx + 4, gw / 2 - 1)
        xx += 6 if not big else 7
    ctx.stroke()
    # blade
    sword_outline_path(ctx, sw, r_off, big)
    lg = cairo.LinearGradient(0, -w / 2, 0, w / 2)
    for off, c in BLADE_STOPS:
        lg.add_color_stop_rgb(off, *c)
    ctx.set_source(lg)
    ctx.fill_preserve()
    ctx.set_source_rgba(INK[0], INK[1], INK[2], 1)
    ctx.set_line_width(3.0 if big else 2.4)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    # fuller
    ctx.set_source_rgba(*FULLER)
    ctx.set_line_width(w * 0.16)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(xg + 8, 0)
    ctx.line_to(xg + L * (0.62 if big else 0.55), 0)
    ctx.stroke()
    # crossguard
    gh = w * (1.3 if big else 1.15)
    gt = 11 if big else 8
    rounded_rect(ctx, xg - gt / 2, -gh, gt, gh * 2, gt / 2)
    gcol = GOLD if big else lighten(col, 0.1)
    ctx.set_source_rgba(*rgb(gcol))
    ctx.fill_preserve()
    ctx.set_source_rgba(GUARD_INK[0], GUARD_INK[1], GUARD_INK[2], 1)
    ctx.set_line_width(2.4)
    ctx.stroke()
    if big:
        ctx.arc(xg, 0, 7.5, 0, 2 * PI)
        ctx.set_source_rgba(*rgb(col))
        ctx.fill_preserve()
        ctx.set_source_rgba(GUARD_INK[0], GUARD_INK[1], GUARD_INK[2], 1)
        ctx.set_line_width(2)
        ctx.stroke()
    # pommel
    ctx.arc(r_off - 8, 0, gw * 0.62, 0, 2 * PI)
    ctx.set_source_rgba(*rgb(GOLD if big else lighten(col, 0.1)))
    ctx.fill_preserve()
    ctx.set_source_rgba(GUARD_INK[0], GUARD_INK[1], GUARD_INK[2], 1)
    ctx.set_line_width(2)
    ctx.stroke()
    if alpha < 1:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)
    ctx.restore()


def draw_trail(ctx, samples, big, ball_r=40.0, dims=None):
    """Swoosh behind a spinning sword.

    samples: [(x, y, th), ...] ball centre + sword angle, newest first, TRAIL_DT apart
             (stop the list early at sim start or when the ball died).
    """
    sw = dims or (BIG if big else SMALL)
    r_in = ball_r + sw["grip"] + sw["blade"] * 0.45
    r_out = ball_r + sw["grip"] + sw["blade"] - 2
    pts = []
    for (x, y, th) in samples:
        c, sn = math.cos(th), math.sin(th)
        pts.append(((x + c * r_in, y + sn * r_in), (x + c * r_out, y + sn * r_out)))
    if len(pts) < 2:
        return
    tc = TRAIL_BIG if big else TRAIL_SMALL
    n = len(pts) - 1
    for k in range(n):
        (a_in, a_out), (b_in, b_out) = pts[k], pts[k + 1]
        ctx.move_to(*a_in)
        ctx.line_to(*a_out)
        ctx.line_to(*b_out)
        ctx.line_to(*b_in)
        ctx.close_path()
        ctx.set_source_rgba(*rgb(tc, (0.30 if big else 0.22) * (1 - k / n) ** 1.5))
        ctx.fill()
    # bright edge along the tip path
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(n):
        ctx.move_to(*pts[k][1])
        ctx.line_to(*pts[k + 1][1])
        ctx.set_source_rgba(*rgb((255, 255, 255), 0.55 * (1 - k / n) ** 1.3))
        ctx.set_line_width((5 if big else 3.5) * (1 - 0.6 * k / n))
        ctx.stroke()


def export_sprites(folder, scale=2.0):
    """Transparent PNGs pointing right (pommel on the left), 2x video size."""
    os.makedirs(folder, exist_ok=True)
    for big in (False, True):
        sw = BIG if big else SMALL
        length = sw["grip"] + sw["blade"] + 24
        height = sw["width"] * (2.9 if big else 2.5) + (40 if big else 0)
        wpx, hpx = int(length * scale + 40), int(height * scale + 20)
        for n in NAMES:
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, wpx, hpx)
            ctx = cairo.Context(surf)
            ctx.translate(20 + 16 * scale, hpx / 2)
            ctx.scale(scale, scale)
            draw_sword(ctx, 0, 0, 0, 0, big, BALL_COLORS[n])
            kind = "big" if big else "small"
            surf.write_to_png(os.path.join(folder, f"sword_{kind}_{n.lower()}.png"))


def preview(path):
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "glossy-ball"))
    from glossy_ball import draw_ball
    surf, ctx = new_canvas(W, 760)
    ctx.translate(0, -640)
    paint_background(ctx)
    ctx.identity_matrix()
    draw_sword(ctx, 120, 120, 0, 0, True, BALL_COLORS["RED"])
    text(ctx, "BIG sword", 900, 120, "xb", 40, (255, 214, 80))
    for i, n in enumerate(NAMES):
        draw_sword(ctx, 60 + (i % 3) * 330, 250 + (i // 3) * 70, 0, 0, False, BALL_COLORS[n])
    # spinning examples with trails (a sword sweeping clockwise)
    for (bx, by, big, col, th0) in ((300, 560, True, BALL_COLORS["RED"], -0.4),
                                    (780, 560, False, BALL_COLORS["GREEN"], -0.9)):
        samples = [(bx, by, th0 - k * 0.014 * (2.4 if big else 4.2)) for k in range(TRAIL_SAMPLES)]
        draw_trail(ctx, samples, big)
        draw_sword(ctx, bx, by, th0, 38.0, big, col)
        draw_ball(ctx, bx, by, 40.0, col, "100")
    surf.write_to_png(path)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    preview(os.path.join(here, "preview.png"))
    export_sprites(os.path.join(here, "assets"))
    print("wrote preview.png and assets/")
