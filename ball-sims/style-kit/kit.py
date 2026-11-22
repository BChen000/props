"""style-kit: the shared look of the Marble Pop (ex Fun House 67) ball-sim Shorts.

Canvas, ball palette, UI colours, Poppins text helpers, easing and shape helpers.
Every other ball-sims prop imports this file. Drawing is done with pycairo.

Change colours / fonts here and every prop follows.
"""
import math

import cairo

# --------------------------------------------------------------------------- canvas
W, H = 1080, 1920          # YouTube Shorts, portrait
FPS = 30
PI = math.pi

# --------------------------------------------------------------------------- ball palette
# Order matters: chip order (left -> right) and roulette order (clockwise from top).
NAMES = ["RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE"]
BALL_COLORS = {
    "RED": (236, 65, 68),
    "BLUE": (61, 131, 247),
    "GREEN": (50, 198, 100),
    "YELLOW": (251, 201, 50),
    "PURPLE": (167, 91, 237),
    "ORANGE": (247, 139, 44),
}

# --------------------------------------------------------------------------- UI colours
BG_TOP = (30, 12, 51)          # background gradient stop 0.0
BG_MID = (25, 10, 43)          # background gradient stop 0.3
BG_BOTTOM = (9, 4, 20)         # background gradient stop 1.0
TITLE_PINK = (251, 127, 211)   # big title fill
TITLE_OUTLINE = (27, 9, 48)    # big title outline
TITLE_SHADOW = (8, 2, 18)      # big title drop shadow
SUBTITLE = (239, 228, 251)     # rule line under the title
STATUS_BLUE = (155, 217, 251)  # "6 LEFT"
STATUS_PINK = (244, 114, 208)  # "PICK YOUR COLOR" / "FIGHT!"
HIGHLIGHT = (255, 214, 80)     # yellow highlight text ("SPINNING...", banners, "What next?")
GOLD = (255, 205, 70)          # big sword guard, BIG SWORD tag, roulette hub
WHITE = (255, 255, 255)
TEXT_OUTLINE = (10, 4, 20)     # outline of bottom messages

# --------------------------------------------------------------------------- fonts
# Poppins (Google Fonts, SIL OFL 1.1). Install with:  python get_fonts.py
FONTS = {
    "xb": ("Poppins ExtraBold", cairo.FONT_WEIGHT_NORMAL),   # weight 800
    "blk": ("Poppins Black", cairo.FONT_WEIGHT_NORMAL),      # weight 900
    "b": ("Poppins", cairo.FONT_WEIGHT_BOLD),                # weight 700
    "sb": ("Poppins SemiBold", cairo.FONT_WEIGHT_NORMAL),    # weight 600
    "r": ("Poppins", cairo.FONT_WEIGHT_NORMAL),              # weight 400
}
# advance width of "SWORD ROULETTE" at 100 px with the right font installed (Linux/fontconfig)
FONT_FINGERPRINT = {"xb": 903.0, "blk": 915.0, "b": 894.0, "sb": 883.0, "r": 868.0}


# --------------------------------------------------------------------------- colour + easing helpers
def rgb(c, a=1.0):
    return (c[0] / 255, c[1] / 255, c[2] / 255, a)


def lighten(c, k):
    return tuple(int(v + (255 - v) * k) for v in c)


def darken(c, k):
    return tuple(int(v * (1 - k)) for v in c)


def hexstr(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def ease_out_back(u, s=1.9):
    u = clamp(u)
    u -= 1
    return u * u * ((s + 1) * u + s) + 1


def ease_in_out(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


# --------------------------------------------------------------------------- text
_cap_cache = {}


def set_font(ctx, font, size):
    fam, wt = FONTS[font]
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, wt)
    ctx.set_font_size(size)


def cap_h(ctx, font, size):
    k = (font, size)
    if k not in _cap_cache:
        set_font(ctx, font, size)
        _cap_cache[k] = -ctx.text_extents("H")[1]
    return _cap_cache[k]


def text_w(ctx, s, font, size):
    set_font(ctx, font, size)
    return ctx.text_extents(s)[4]


def text(ctx, s, x, y, font, size, color, align="c", outline=None, ow=0.0, alpha=1.0,
         scale=1.0, shadow=None):
    """Draw text with its cap height centred on y.

    font: key of FONTS. align: "c" centre, "l" left, "r" right.
    outline: RGB tuple, ow: outline width (px, drawn outside the glyph).
    shadow: (dx, dy, RGB, alpha) or None. scale: zoom about (x, y) for pop animations.
    """
    if alpha <= 0.003:
        return
    ch = cap_h(ctx, font, size)
    ctx.save()
    set_font(ctx, font, size)
    xb, yb, tw, th_, xa, ya = ctx.text_extents(s)
    if align == "c":
        x0 = -xa / 2
    elif align == "l":
        x0 = 0
    else:
        x0 = -xa
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    if shadow:
        dx, dy, sc, sa = shadow
        ctx.move_to(x0 + dx, ch / 2 + dy)
        ctx.text_path(s)
        if outline:
            ctx.set_line_width(ow * 2)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_source_rgba(*rgb(sc, sa * alpha))
            ctx.stroke_preserve()
        ctx.set_source_rgba(*rgb(sc, sa * alpha))
        ctx.fill()
    ctx.move_to(x0, ch / 2)
    ctx.text_path(s)
    if outline:
        ctx.set_line_width(ow * 2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*rgb(outline, alpha))
        ctx.stroke_preserve()
    ctx.set_source_rgba(*rgb(color, alpha))
    ctx.fill()
    ctx.restore()


def rich_text(ctx, parts, x, y, font, size, outline=None, ow=0.0, alpha=1.0, scale=1.0):
    """parts: list of (string, RGB); the whole line is centred on x."""
    ch = cap_h(ctx, font, size)
    set_font(ctx, font, size)
    widths = [ctx.text_extents(p[0])[4] for p in parts]
    total = sum(widths)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    xx = -total / 2
    for (s, col), w_ in zip(parts, widths):
        set_font(ctx, font, size)
        ctx.move_to(xx, ch / 2)
        ctx.text_path(s)
        if outline:
            ctx.set_line_width(ow * 2)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_source_rgba(*rgb(outline, alpha))
            ctx.stroke_preserve()
        ctx.set_source_rgba(*rgb(col, alpha))
        ctx.fill()
        xx += w_
    ctx.restore()


# --------------------------------------------------------------------------- shapes
def rounded_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -PI / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, PI / 2)
    ctx.arc(x + r, y + h - r, r, PI / 2, PI)
    ctx.arc(x + r, y + r, r, PI, 1.5 * PI)
    ctx.close_path()


def new_canvas(w=W, h=H):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return surf, cairo.Context(surf)


def paint_background(ctx, w=W, h=H):
    """The channel's purple-to-black vertical gradient."""
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgb(0.0, BG_TOP[0] / 255, BG_TOP[1] / 255, BG_TOP[2] / 255)
    g.add_color_stop_rgb(0.3, BG_MID[0] / 255, BG_MID[1] / 255, BG_MID[2] / 255)
    g.add_color_stop_rgb(1.0, BG_BOTTOM[0] / 255, BG_BOTTOM[1] / 255, BG_BOTTOM[2] / 255)
    ctx.set_source(g)
    ctx.paint()


def check_fonts(strict=False):
    """Warn (or raise) when a Poppins weight is missing and cairo fell back to another font."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
    ctx = cairo.Context(surf)
    bad = []
    for k, ref in FONT_FINGERPRINT.items():
        if abs(text_w(ctx, "SWORD ROULETTE", k, 100) - ref) > 0.5:
            bad.append(FONTS[k][0] + (" Bold" if FONTS[k][1] == cairo.FONT_WEIGHT_BOLD else ""))
    if bad:
        msg = ("Poppins weights not found: %s. Run: python ball-sims/style-kit/get_fonts.py "
               "(text would render in a fallback font)" % ", ".join(bad))
        if strict:
            raise RuntimeError(msg)
        print("WARNING:", msg)
    return not bad


def style_sheet(path):
    """Render the palette + type specimen used as this kit's preview.png."""
    surf, ctx = new_canvas(1080, 1350)
    paint_background(ctx, 1080, 1350)
    text(ctx, "STYLE KIT", W / 2, 90, "xb", 96, TITLE_PINK, outline=TITLE_OUTLINE, ow=5,
         shadow=(0, 7, TITLE_SHADOW, 0.85))
    text(ctx, "Marble Pop ball-sim Shorts", W / 2, 170, "r", 40, SUBTITLE)
    for i, n in enumerate(NAMES):
        x = 110 + i * 172
        c = BALL_COLORS[n]
        ctx.arc(x, 300, 58, 0, 2 * PI)
        ctx.set_source_rgba(*rgb(c))
        ctx.fill()
        text(ctx, n, x, 395, "b", 24, WHITE)
        text(ctx, hexstr(c), x, 432, "r", 22, SUBTITLE)
    ui = [("title", TITLE_PINK), ("status", STATUS_BLUE), ("status 2", STATUS_PINK),
          ("highlight", HIGHLIGHT), ("gold", GOLD), ("subtitle", SUBTITLE)]
    for i, (nm, c) in enumerate(ui):
        x = 110 + i * 172
        rounded_rect(ctx, x - 62, 480, 124, 70, 14)
        ctx.set_source_rgba(*rgb(c))
        ctx.fill()
        text(ctx, nm, x, 580, "b", 22, WHITE)
        text(ctx, hexstr(c), x, 614, "r", 22, SUBTITLE)
    rows = [("xb", 72, "Title / ExtraBold 800", TITLE_PINK),
            ("blk", 64, "FIGHT! / Black 900", HIGHLIGHT),
            ("xb", 40, "6 LEFT / ExtraBold status", STATUS_BLUE),
            ("b", 50, "Comment your color! / Bold 700", WHITE),
            ("sb", 40, "SemiBold 600 (spare weight)", SUBTITLE),
            ("r", 40, "One random ball... / Regular 400", SUBTITLE)]
    y = 720
    for f, s, label, c in rows:
        text(ctx, label, W / 2, y, f, s, c, outline=TEXT_OUTLINE, ow=4 if f != "r" else 0)
        y += 105
    surf.write_to_png(path)


if __name__ == "__main__":
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    check_fonts()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "preview.png")
    style_sheet(out)
    print("wrote", out)
