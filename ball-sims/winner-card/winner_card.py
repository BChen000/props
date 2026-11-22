"""winner-card: the end-of-video winner reveal.

The winning ball glides to the arena centre and grows (r 40 -> 100) inside a colour glow,
its label switches to the colour name, a gold crown drops on top, confetti rains, and the
"<COLOR> WINS!" box pops up in the bottom slot with a one-line story subtitle.
"""
import math
import os
import random
import sys

import cairo

_HERE = os.path.dirname(os.path.abspath(__file__))
for _dep in ("style-kit", "glossy-ball"):
    sys.path.append(os.path.join(_HERE, "..", _dep))
from kit import (BALL_COLORS, HIGHLIGHT, NAMES, PI, W, WHITE, clamp, ease_out, ease_out_back,  # noqa: E402
                 rgb, rounded_rect, text)
from glossy_ball import draw_ball  # noqa: E402

# --------------------------------------------------------------------------- settings
TARGET = (540, 875, 100)          # winner ball centre x, y and final radius
GROW_TIME = 0.55                  # seconds to glide + grow
NAME_AT = 0.3                     # label switches from HP to the colour name
CROWN_AT, CROWN_DROP = 0.35, 0.4  # crown starts dropping / drop duration
CROWN_FILL = (255, 211, 60)
CROWN_INK = (120, 70, 0)
CROWN_GEMS = (255, 235, 140)
BOX_CENTER_Y = 1620               # bottom box: 960 x 180, radius 28, 5 px border in winner colour
BOX_FILL = (0.0, 0.0, 0.02, 0.92)
CONFETTI_SEED, CONFETTI_COUNT = 77, 150
CONFETTI_GRAVITY = 520
CONFETTI_FLOOR_Y = 1500           # pieces below this are not drawn


def draw_crown(ctx, x, y, s, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    pts = [(-44, 22), (-50, -26), (-22, 0), (0, -38), (22, 0), (50, -26), (44, 22)]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*rgb(CROWN_FILL, alpha))
    ctx.fill_preserve()
    ctx.set_source_rgba(*rgb(CROWN_INK, alpha))
    ctx.set_line_width(4)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    for px, py in ((-50, -26), (0, -38), (50, -26)):
        ctx.arc(px, py - 4, 6, 0, 2 * PI)
        ctx.set_source_rgba(*rgb(CROWN_GEMS, alpha))
        ctx.fill_preserve()
        ctx.set_source_rgba(*rgb(CROWN_INK, alpha))
        ctx.set_line_width(2.5)
        ctx.stroke()
    ctx.restore()


def draw_winner_reveal(ctx, age, start_x, start_y, color, name, start_label, start_r=40.0, target=TARGET):
    """Glow + growing ball + crown. age = seconds since the reveal started."""
    tx, ty, tr = target
    u = ease_out(age / GROW_TIME)
    x = start_x + (tx - start_x) * u
    y = start_y + (ty - start_y) * u
    r = start_r + (tr - start_r) * u
    rg = cairo.RadialGradient(x, y, r * 0.5, x, y, r * 3.6)
    rg.add_color_stop_rgba(0, *rgb(color, 0.6 * u))
    rg.add_color_stop_rgba(1, *rgb(color, 0.0))
    ctx.set_source(rg)
    ctx.arc(x, y, r * 3.6, 0, 2 * PI)
    ctx.fill()
    draw_ball(ctx, x, y, r, color, name if age > NAME_AT else start_label,
              label_size=int(30 + 18 * u) if age > NAME_AT else 30)
    ca = age - CROWN_AT
    if ca > 0:
        cy_ = y - r - 34 - 90 * (1 - ease_out_back(ca / CROWN_DROP, 2.2))
        draw_crown(ctx, x, cy_, 0.95, alpha=clamp(ca / 0.12))


def make_confetti(palette, seed=CONFETTI_SEED, count=CONFETTI_COUNT):
    """palette: list of RGB. Returns pre-rolled pieces (x0, y0, vx, vy, rot, vr, col, delay, size)."""
    rng = random.Random(seed)
    return [(rng.uniform(80, 1000), rng.uniform(470, 640), rng.uniform(-160, 160),
             rng.uniform(-260, 60), rng.uniform(0, 2 * PI), rng.uniform(-9, 9),
             rng.choice(palette), rng.uniform(0.0, 0.5), rng.uniform(9, 16)) for _ in range(count)]


def default_palette():
    return [BALL_COLORS[n] for n in NAMES] + [(255, 255, 255), HIGHLIGHT]


def draw_confetti(ctx, age, pieces):
    if age < 0:
        return
    for (x0, y0, vx, vy, rot, vr, col, delay, sz) in pieces:
        a = age - delay
        if a < 0:
            continue
        x = x0 + vx * a
        y = y0 + vy * a + 0.5 * CONFETTI_GRAVITY * a * a
        if y > CONFETTI_FLOOR_Y:
            continue
        al = clamp((4.6 - a) / 0.6)
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rot + vr * a)
        ctx.scale(1.0, 0.35 + 0.65 * abs(math.cos(a * 6 + rot)))
        ctx.rectangle(-sz * 0.3, -sz * 0.7, sz * 0.6, sz * 1.4)
        ctx.set_source_rgba(*rgb(col, al))
        ctx.fill()
        ctx.restore()


def draw_winner_box(ctx, age, title, color, subtitle):
    """Bottom box: title e.g. "GREEN WINS!" (ExtraBold 84, winner colour) + subtitle (Bold 44)."""
    sc = ease_out_back(age / 0.35, 1.6)
    ctx.save()
    ctx.translate(W / 2, BOX_CENTER_Y)
    ctx.scale(sc, sc)
    rounded_rect(ctx, -480, -90, 960, 180, 28)
    ctx.set_source_rgba(*BOX_FILL)
    ctx.fill_preserve()
    ctx.set_source_rgba(*rgb(color))
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.restore()
    if sc > 0.05:
        text(ctx, title, W / 2, BOX_CENTER_Y - 30 * sc, "xb", 84, color, scale=sc)
        text(ctx, subtitle, W / 2, BOX_CENTER_Y + 45 * sc, "b", 44, WHITE, scale=sc)


if __name__ == "__main__":
    sys.path.append(os.path.join(_HERE, "..", "arena-board"))
    import arena_board as board
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1080, 1920)
    ctx = cairo.Context(surf)
    ctx.set_source_surface(board.make_background("SWORD ROULETTE", "One random ball gets the BIG sword!"), 0, 0)
    ctx.paint()
    ctx.set_source_surface(board.make_floor(), 0, 0)
    ctx.paint()
    board.draw_rim(ctx, board.RIM_CALM)
    green = BALL_COLORS["GREEN"]
    age = 1.6
    draw_winner_reveal(ctx, age, 600, 1100, green, "GREEN", "10")
    board.draw_status(ctx, "1 LEFT", "WINNER!", HIGHLIGHT)
    draw_confetti(ctx, age, make_confetti(default_palette()))
    draw_winner_box(ctx, age, "GREEN WINS!", green, "Took down the BIG sword!")
    surf.write_to_png(os.path.join(_HERE, "preview.png"))
    os.makedirs(os.path.join(_HERE, "assets"), exist_ok=True)
    cs = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 180)
    cc = cairo.Context(cs)
    draw_crown(cc, 120, 100, 2.0)
    cs.write_to_png(os.path.join(_HERE, "assets", "crown.png"))
    print("wrote preview.png and assets/crown.png")
