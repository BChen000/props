"""subscribe-cta: end-screen call to action.

A red SUBSCRIBE pill with a bell pops in (at the same moment as the winner, so viewers who
swipe away right after the result still see it), a mouse cursor glides in and taps it
(button squish, ripple, bell wobble + ring lines), then a two-line comment prompt
("What do you want to see next?" / "Tell me in the comments!") fades in.
All times are seconds since the CTA started (age).
"""
import math
import os
import sys

import cairo

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "..", "style-kit"))
from kit import HIGHLIGHT, PI, TEXT_OUTLINE, W, WHITE, clamp, ease_out, ease_out_back, rounded_rect, text  # noqa: E402

# --------------------------------------------------------------------------- settings
BUTTON_CENTER = (W / 2, 1090)
BUTTON_SIZE = (480, 104)
BUTTON_LABEL = "SUBSCRIBE"            # Poppins ExtraBold 50, white
BUTTON_TOP = (1.0, 0.22, 0.22)        # float RGB gradient top  (= #ff3838)
BUTTON_BOTTOM = (0.82, 0.0, 0.05)     # float RGB gradient bottom (= #d1000d)
TAP_AT = 1.05                         # cursor click time
CURSOR_FROM = (860, 1330)             # cursor starts here, glides to the button
CURSOR_IN_AT = 0.55
NEXT_AT = 1.35                        # comment prompt fades in
NEXT_LINES = ("What do you want to see next?", "Tell me in the comments!")
NEXT_Y = (1222, 1282)                 # ExtraBold 44 yellow / Bold 40 white


def draw_bell(ctx, x, y, s, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    ctx.move_to(-16, 10)
    ctx.curve_to(-14, 4, -14, -2, -14, -6)
    ctx.curve_to(-14, -16, -8, -20, 0, -20)
    ctx.curve_to(8, -20, 14, -16, 14, -6)
    ctx.curve_to(14, -2, 14, 4, 16, 10)
    ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.arc(0, -22, 3.2, 0, 2 * PI)
    ctx.fill()
    ctx.arc(0, 14, 4.6, 0, 2 * PI)
    ctx.fill()
    ctx.restore()


def draw_cursor(ctx, x, y, s, alpha=1.0):
    pts = [(0, 0), (0, 36), (9, 28), (15.5, 42), (21.5, 39.5), (15, 26), (26.5, 26)]
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(0, 0, 0, 0.35 * alpha)
    ctx.save()
    ctx.translate(2, 3)
    ctx.fill_preserve()
    ctx.restore()
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.05, 0.05, 0.08, alpha)
    ctx.set_line_width(2.4)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.restore()


def draw_subscribe_cta(ctx, age, center=BUTTON_CENTER, size=BUTTON_SIZE, label=BUTTON_LABEL,
                       next_lines=NEXT_LINES, next_y=NEXT_Y):
    """Button + ripple, cursor, then the comment prompt (in that draw order)."""
    bx, by = center
    bw, bh = size
    bsc = ease_out_back(age / 0.4, 2.0)
    tap = age - TAP_AT
    if 0 <= tap < 0.22:
        bsc *= 1 - 0.08 * math.sin(PI * tap / 0.22)
    if age > 0.5:
        bsc *= 1 + 0.025 * math.sin((age - 0.5) * 2 * PI * 1.4)
    if bsc > 0.02:
        ctx.save()
        ctx.translate(bx, by)
        ctx.scale(bsc, bsc)
        rounded_rect(ctx, -bw / 2 + 4, -bh / 2 + 9, bw, bh, bh / 2)
        ctx.set_source_rgba(0, 0, 0, 0.45)
        ctx.fill()
        rounded_rect(ctx, -bw / 2, -bh / 2, bw, bh, bh / 2)
        lg = cairo.LinearGradient(0, -bh / 2, 0, bh / 2)
        lg.add_color_stop_rgb(0, *BUTTON_TOP)
        lg.add_color_stop_rgb(1, *BUTTON_BOTTOM)
        ctx.set_source(lg)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(3)
        ctx.stroke()
        wob = 0.0
        if tap > 0:
            wob = 0.45 * math.sin(tap * 26) * math.exp(-tap * 3.2)
        draw_bell(ctx, -150, 2, 1.55, wob)
        if 0 < tap < 0.9:
            ra = 1 - tap / 0.9
            for sgn in (-1, 1):
                ctx.arc(-150, 0, 40 + 10 * tap, -PI / 2 + sgn * 0.75 - 0.35, -PI / 2 + sgn * 0.75 + 0.35)
                ctx.set_source_rgba(1, 1, 1, ra)
                ctx.set_line_width(4)
                ctx.stroke()
        text(ctx, label, 38, 2, "xb", 50, WHITE)
        ctx.restore()
        if 0 <= tap < 0.5:
            rr = 20 + 140 * ease_out(tap / 0.5)
            ctx.arc(bx + 120, by + 18, rr, 0, 2 * PI)
            ctx.set_source_rgba(1, 1, 1, 0.6 * (1 - tap / 0.5))
            ctx.set_line_width(5)
            ctx.stroke()
    # cursor
    ca = age - CURSOR_IN_AT
    if ca > 0:
        u = ease_out(ca / 0.5)
        cx_ = CURSOR_FROM[0] + (bx + 120 - CURSOR_FROM[0]) * u
        cy_ = CURSOR_FROM[1] + (by + 18 - CURSOR_FROM[1]) * u
        press = 0.9 if 0 <= tap < 0.18 else 1.0
        draw_cursor(ctx, cx_, cy_, 2.0 * press, alpha=clamp((3.2 - ca) / 0.3))
    # comment prompt
    na = age - NEXT_AT
    if na > 0 and next_lines:
        a = clamp(na / 0.25)
        sc2 = 1 + 0.2 * (1 - ease_out(na / 0.25))
        text(ctx, next_lines[0], W / 2, next_y[0], "xb", 44, HIGHLIGHT, outline=TEXT_OUTLINE, ow=4,
             alpha=a, scale=sc2)
        text(ctx, next_lines[1], W / 2, next_y[1], "b", 40, WHITE, outline=TEXT_OUTLINE, ow=4,
             alpha=a, scale=sc2)


def export_assets(folder):
    os.makedirs(folder, exist_ok=True)
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 520, 140)
    c = cairo.Context(s)
    draw_subscribe_cta(c, 0.4, center=(260, 62), next_lines=None)
    s.write_to_png(os.path.join(folder, "subscribe_button.png"))
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 80, 110)
    c = cairo.Context(s)
    draw_cursor(c, 8, 6, 2.0)
    s.write_to_png(os.path.join(folder, "cursor.png"))
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 80, 90)
    c = cairo.Context(s)
    draw_bell(c, 40, 46, 1.55)
    s.write_to_png(os.path.join(folder, "bell.png"))


if __name__ == "__main__":
    from kit import new_canvas, paint_background
    surf, ctx = new_canvas(1080, 460)
    ctx.translate(0, -950)
    paint_background(ctx)
    draw_subscribe_cta(ctx, 1.8)
    surf.write_to_png(os.path.join(_HERE, "preview.png"))
    export_assets(os.path.join(_HERE, "assets"))
    print("wrote preview.png and assets/")
