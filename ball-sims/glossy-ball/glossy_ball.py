"""glossy-ball: the ball character of the Marble Pop ball-sim Shorts.

A glossy sphere (radial gradient), white rim, soft drop shadow, specular highlight,
a centred label (HP number or colour name) and an optional white hit flash.
"""
import os
import sys

import cairo

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style-kit"))
from kit import BALL_COLORS, NAMES, PI, W, WHITE, darken, lighten, new_canvas, paint_background, rgb, text  # noqa: E402

# --------------------------------------------------------------------------- settings
BALL_R = 40.0                 # radius used in the videos (px at 1080x1920)
LABEL_OUTLINE = (30, 14, 40)  # label = Poppins ExtraBold, outline width 0.13 * size
LIGHTEN_CORE = 0.55           # gradient: lighten(colour, .55) -> colour at .45 -> darken(colour, .38)
DARKEN_EDGE = 0.38
FLASH_ALPHA = 0.85            # white overlay on a hit, scaled by flash 0..1


def draw_ball(ctx, x, y, r, col, label, label_size=30, flash=0.0, alpha=1.0, shadow=True):
    """Draw one ball centred at (x, y). label: str or None. flash: 0..1 white hit flash."""
    if alpha <= 0.01:
        return
    if alpha < 1:
        ctx.push_group()
    if shadow:
        ctx.save()
        ctx.translate(x, y + r * 0.22)
        ctx.scale(1.0, 0.9)
        rg = cairo.RadialGradient(0, 0, r * 0.6, 0, 0, r * 1.25)
        rg.add_color_stop_rgba(0, 0, 0, 0, 0.45)
        rg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(rg)
        ctx.arc(0, 0, r * 1.25, 0, 2 * PI)
        ctx.fill()
        ctx.restore()
    rg = cairo.RadialGradient(x - r * 0.32, y - r * 0.38, r * 0.05, x, y, r * 1.05)
    rg.add_color_stop_rgba(0.0, *rgb(lighten(col, LIGHTEN_CORE)))
    rg.add_color_stop_rgba(0.45, *rgb(col))
    rg.add_color_stop_rgba(1.0, *rgb(darken(col, DARKEN_EDGE)))
    ctx.arc(x, y, r, 0, 2 * PI)
    ctx.set_source(rg)
    ctx.fill()
    if flash > 0:
        ctx.arc(x, y, r, 0, 2 * PI)
        ctx.set_source_rgba(1, 1, 1, FLASH_ALPHA * flash)
        ctx.fill()
    ctx.arc(x, y, r - 1.5, 0, 2 * PI)
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(max(2.5, r * 0.075))
    ctx.stroke()
    # specular
    ctx.save()
    ctx.translate(x - r * 0.33, y - r * 0.45)
    ctx.scale(1.0, 0.6)
    sg = cairo.RadialGradient(0, 0, 0, 0, 0, r * 0.42)
    sg.add_color_stop_rgba(0, 1, 1, 1, 0.55)
    sg.add_color_stop_rgba(1, 1, 1, 1, 0.0)
    ctx.set_source(sg)
    ctx.arc(0, 0, r * 0.42, 0, 2 * PI)
    ctx.fill()
    ctx.restore()
    if label:
        text(ctx, label, x, y + 1, "xb", label_size, WHITE, outline=LABEL_OUTLINE, ow=label_size * 0.13)
    if alpha < 1:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)


def export_sprites(folder, r=80):
    """Transparent PNG per colour (no label), 2x the video size, for Manim/Algodoo/other tools."""
    os.makedirs(folder, exist_ok=True)
    size = int(r * 2.7)
    for n in NAMES:
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surf)
        draw_ball(ctx, size / 2, size / 2 - r * 0.12, r, BALL_COLORS[n], None)
        surf.write_to_png(os.path.join(folder, f"ball_{n.lower()}.png"))


def preview(path):
    surf, ctx = new_canvas(W, 520)
    ctx.translate(0, -700)
    paint_background(ctx)
    ctx.identity_matrix()
    for i, n in enumerate(NAMES):
        draw_ball(ctx, 110 + i * 172, 110, BALL_R, BALL_COLORS[n], "100")
    draw_ball(ctx, 200, 340, BALL_R, BALL_COLORS["BLUE"], "55", flash=0.6)
    text(ctx, "hit flash", 200, 430, "b", 26, (239, 228, 251))
    draw_ball(ctx, 540, 330, 100, BALL_COLORS["GREEN"], "GREEN", label_size=48)
    text(ctx, "winner size r=100", 540, 480, "b", 26, (239, 228, 251))
    draw_ball(ctx, 880, 340, BALL_R, BALL_COLORS["ORANGE"], "10")
    text(ctx, "fight size r=40", 880, 430, "b", 26, (239, 228, 251))
    surf.write_to_png(path)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    preview(os.path.join(here, "preview.png"))
    export_sprites(os.path.join(here, "assets"))
    print("wrote preview.png and assets/")
