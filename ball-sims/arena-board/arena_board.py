"""arena-board: the game board of the Marble Pop ball-sim Shorts.

Background gradient + big title + rule line, the round grid arena with its glowing rim,
the status row under the chips, the bottom message slot and the big centre banner.
"""
import math
import os
import sys

import cairo

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style-kit"))
from kit import (W, H, PI, HIGHLIGHT, STATUS_BLUE, STATUS_PINK, SUBTITLE, TEXT_OUTLINE,  # noqa: E402
                 TITLE_OUTLINE, TITLE_PINK, TITLE_SHADOW, WHITE, clamp, ease_out, paint_background,
                 rgb, rich_text, text, text_w)

# --------------------------------------------------------------------------- settings
ARENA_CX, ARENA_CY, ARENA_R = 540.0, 1010.0, 445.0
FLOOR = (28, 22, 43)
GRID_CELL = 74
GRID_LINE = (15, 6, 28)          # 4 px dark grout lines
GRID_HILITE = (60, 54, 86)       # 1.2 px light edge, alpha 0.25, offset 2.6 px
FLOOR_VIGNETTE = (8, 3, 18)      # alpha 0.55 at the rim
RIM_CALM = (145, 130, 190)       # intro / roulette / winner
RIM_FIGHT = (240, 110, 200)      # during the fight

TITLE_Y, TITLE_SIZE, TITLE_MAX_W = 128, 112, 860
SUBTITLE_Y, SUBTITLE_SIZE = 218, 40
STATUS_Y, STATUS_LEFT_X, STATUS_RIGHT_X, STATUS_SIZE = 405, 320, 680, 40
MSG_Y = 1575                     # bottom message slot (centre line)
BANNER_SIZE = 140


# --------------------------------------------------------------------------- static layers
def make_background(title, subtitle):
    """Full-frame static layer: gradient, title (auto-shrinks to 860 px), rule line."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    paint_background(ctx)
    size = TITLE_SIZE
    while text_w(ctx, title, "xb", size) > TITLE_MAX_W:
        size -= 2
    text(ctx, title, W / 2, TITLE_Y, "xb", size, TITLE_PINK, outline=TITLE_OUTLINE, ow=5,
         shadow=(0, 7, TITLE_SHADOW, 0.85))
    text(ctx, subtitle, W / 2, SUBTITLE_Y, "r", SUBTITLE_SIZE, SUBTITLE)
    return surf


def make_floor(cx=ARENA_CX, cy=ARENA_CY, r=ARENA_R):
    """Full-frame layer with only the round grid floor painted (transparent elsewhere)."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.save()
    ctx.arc(cx, cy, r, 0, 2 * PI)
    ctx.clip()
    ctx.set_source_rgb(FLOOR[0] / 255, FLOOR[1] / 255, FLOOR[2] / 255)
    ctx.paint()
    cell = GRID_CELL
    ctx.set_line_width(4)
    start_x = cx - cell / 2 - cell * 7
    start_y = cy - cell / 2 - cell * 7
    for k in range(16):
        xx = start_x + k * cell
        yy = start_y + k * cell
        ctx.set_source_rgba(*rgb(GRID_LINE))
        ctx.move_to(xx, cy - r)
        ctx.line_to(xx, cy + r)
        ctx.move_to(cx - r, yy)
        ctx.line_to(cx + r, yy)
        ctx.stroke()
        ctx.set_source_rgba(*rgb(GRID_HILITE, 0.25))
        ctx.set_line_width(1.2)
        ctx.move_to(xx + 2.6, cy - r)
        ctx.line_to(xx + 2.6, cy + r)
        ctx.move_to(cx - r, yy + 2.6)
        ctx.line_to(cx + r, yy + 2.6)
        ctx.stroke()
        ctx.set_line_width(4)
    vg = cairo.RadialGradient(cx, cy - 60, 60, cx, cy, r)
    vg.add_color_stop_rgba(0.0, 1, 1, 1, 0.035)
    vg.add_color_stop_rgba(0.55, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, FLOOR_VIGNETTE[0] / 255, FLOOR_VIGNETTE[1] / 255,
                           FLOOR_VIGNETTE[2] / 255, 0.55)
    ctx.set_source(vg)
    ctx.paint()
    ctx.restore()
    return surf


# --------------------------------------------------------------------------- per-frame pieces
def draw_rim(ctx, col, glow=1.0, cx=ARENA_CX, cy=ARENA_CY, r=ARENA_R):
    """Glowing arena rim. col = RIM_CALM or RIM_FIGHT; glow 1.5 during slow motion."""
    for w_, a in ((30, 0.05), (20, 0.08), (12, 0.14)):
        ctx.set_source_rgba(*rgb(col, a * glow))
        ctx.set_line_width(w_)
        ctx.arc(cx, cy, r, 0, 2 * PI)
        ctx.stroke()
    ctx.set_source_rgba(*rgb(col, 1.0))
    ctx.set_line_width(5)
    ctx.arc(cx, cy, r, 0, 2 * PI)
    ctx.stroke()


def draw_status(ctx, left, right, right_color=STATUS_PINK, left_color=STATUS_BLUE):
    """Status row under the chips, e.g. ("6 LEFT", "FIGHT!")."""
    text(ctx, left, STATUS_LEFT_X, STATUS_Y, "xb", STATUS_SIZE, left_color)
    text(ctx, right, STATUS_RIGHT_X, STATUS_Y, "xb", STATUS_SIZE, right_color)


def draw_message(ctx, kind, payload, age, remaining, clock, first=False, y=MSG_Y):
    """Bottom message slot.

    kind "plain": payload (text, RGB). Bold, gentle pulse, 0.15 s fade-in (none if first).
    kind "pop":   payload (text, RGB). ExtraBold, pops in, fades out over the last 0.12 s.
    kind "duel":  payload ((name_a, RGB_a), (name_b, RGB_b)) -> "RED  vs  GREEN".
    age = seconds since the message started, remaining = seconds until it ends,
    clock = absolute video time (drives the pulse).
    """
    fade = clamp(remaining / 0.12) if kind != "plain" else 1.0
    if kind == "plain":
        s, col = payload
        pulse = 1.0 + 0.025 * math.sin(clock * 2 * PI * 1.2)
        size = 50
        while text_w(ctx, s, "b", size) > 960:
            size -= 2
        text(ctx, s, W / 2, y, "b", size, col, outline=TEXT_OUTLINE, ow=4, scale=pulse,
             alpha=1.0 if first else clamp(age / 0.15))
    elif kind == "pop":
        s, col = payload
        size = 62
        while text_w(ctx, s, "xb", size) * 1.12 > 1010:
            size -= 2
        sc = 1.0 + 0.12 * (1 - ease_out(age / 0.18))
        text(ctx, s, W / 2, y, "xb", size, col, outline=TEXT_OUTLINE, ow=5, scale=sc, alpha=fade)
    elif kind == "duel":
        (a, ca), (b, cb) = payload
        sc = 1.0 + 0.12 * (1 - ease_out(age / 0.2))
        rich_text(ctx, [(a, ca), ("  vs  ", WHITE), (b, cb)], W / 2, y, "xb", 62,
                  outline=TEXT_OUTLINE, ow=5, scale=sc)


def draw_banner(ctx, s, age, dur, col=HIGHLIGHT, size=BANNER_SIZE, cx=ARENA_CX, cy=ARENA_CY):
    """Big centre announcement ("FIGHT!", "FINAL DUEL!"): slams in, fades over the last 0.25 s."""
    sc = 1.0 + 0.6 * (1 - ease_out(age / 0.16))
    a = clamp((dur - age) / 0.25)
    text(ctx, s, cx, cy, "blk", size, col, outline=(20, 6, 30), ow=9, scale=sc, alpha=a,
         shadow=(0, 8, (0, 0, 0), 0.5))


# --------------------------------------------------------------------------- preview / assets
def render_board(title="SWORD ROULETTE", subtitle="One random ball gets the BIG sword!",
                 rim=RIM_FIGHT, status=("6 LEFT", "FIGHT!"), message="Comment your color!",
                 banner=None):
    bg = make_background(title, subtitle) if title is not None else None
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    if bg is not None:
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
    else:
        paint_background(ctx)
    ctx.set_source_surface(make_floor(), 0, 0)
    ctx.paint()
    draw_rim(ctx, rim)
    if status:
        draw_status(ctx, status[0], status[1])
    if message:
        draw_message(ctx, "plain", (message, WHITE), 1.0, 1.0, 0.0, first=True)
    if banner:
        draw_banner(ctx, banner, 0.5, 1.0)
    return surf


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    render_board(banner="FIGHT!").write_to_png(os.path.join(here, "preview.png"))
    os.makedirs(os.path.join(here, "assets"), exist_ok=True)
    render_board(title=None, rim=RIM_CALM, status=None, message=None).write_to_png(
        os.path.join(here, "assets", "board_blank_calm.png"))
    render_board(title=None, rim=RIM_FIGHT, status=None, message=None).write_to_png(
        os.path.join(here, "assets", "board_blank_fight.png"))
    print("wrote preview.png and assets/")
