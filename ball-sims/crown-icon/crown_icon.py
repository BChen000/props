"""crown-icon: the gold crown of the Marble Pop Shorts, one design with two backends.

Three-point crown with a vertical gold gradient, a dark-gold outline, a band, red/blue/red jewels
and an optional soft glow. Scale s=1.0 is about 56 px wide and 35 px tall.
- draw_crown(c, ...): skia-python canvas (Ring Escape, neon-hud, question-thumbnail)
- draw_crown_cairo(ctx, ...): pycairo context (winner-card, so Sword Roulette too)
Both use the same geometry and colours. The only difference is the glow: skia blurs a disc,
while cairo uses a radial gradient with the same profile.

  python crown_icon.py   -> preview.png
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- settings
GOLD_TOP = (255, 236, 120)      # gradient top (y = -22 s)
GOLD_BOTTOM = (246, 168, 20)    # gradient bottom (y = 14 s)
BAND = (255, 214, 70)
OUTLINE = (150, 90, 10)         # drawn at alpha 0.9
GLOW = (255, 210, 70)           # halo colour, alpha 0.55 * glow
JEWELS = [(-24.5, -12, (255, 80, 90)), (0, -17.6, (80, 170, 255)), (24.5, -12, (255, 80, 90))]
JEWEL_R = 3.6
OUTLINE_W, BAND_OUTLINE_W = 2.2, 2.0
GLOW_R, GLOW_SIGMA = 30.0, 14.0  # halo: disc of radius 30 s blurred with sigma 14 s


def _points(s):
    w, hgt = 24 * s, 22 * s
    return [(-w, hgt * 0.45), (-w * 1.02, -hgt * 0.55), (-w * 0.5, -hgt * 0.02), (0, -hgt * 0.8),
            (w * 0.5, -hgt * 0.02), (w * 1.02, -hgt * 0.55), (w, hgt * 0.45)]


# --------------------------------------------------------------------------- skia backend
def _col(c, a=1.0):
    import skia
    return skia.Color4f(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, max(0.0, min(1.0, a)))


def crown_path(s=1.0):
    import skia
    p = skia.Path()
    pts = _points(s)
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def draw_crown(c, x, y, s=1.0, alpha=1.0, glow=0.0):
    """skia: crown centred at (x, y). s: scale. glow: 0..2 soft halo."""
    import skia
    if alpha <= 0.01:
        return
    c.save()
    c.translate(x, y)
    if glow > 0:
        gp = skia.Paint(AntiAlias=True, Color4f=_col(GLOW, 0.55 * glow * alpha))
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, GLOW_SIGMA * s))
        c.drawCircle(0, 0, GLOW_R * s, gp)
    path = crown_path(s)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, -22 * s), skia.Point(0, 14 * s)],
                                        [_col(GOLD_TOP, alpha).toColor(), _col(GOLD_BOTTOM, alpha).toColor()])
    c.drawPath(path, skia.Paint(AntiAlias=True, Shader=sh))
    c.drawPath(path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=OUTLINE_W * s,
                                Color4f=_col(OUTLINE, 0.9 * alpha), StrokeJoin=skia.Paint.kRound_Join))
    band = skia.Rect(-24 * s, 7 * s, 24 * s, 13 * s)
    c.drawRoundRect(band, 2 * s, 2 * s, skia.Paint(AntiAlias=True, Color4f=_col(BAND, alpha)))
    c.drawRoundRect(band, 2 * s, 2 * s, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                                   StrokeWidth=BAND_OUTLINE_W * s, Color4f=_col(OUTLINE, 0.9 * alpha)))
    for jx, jy, jc in JEWELS:
        c.drawCircle(jx * s, jy * s, JEWEL_R * s, skia.Paint(AntiAlias=True, Color4f=_col(jc, alpha)))
    c.restore()


# --------------------------------------------------------------------------- pycairo backend
def _rgba(c, a=1.0):
    return (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, max(0.0, min(1.0, a)))


def _round_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def draw_crown_cairo(ctx, x, y, s=1.0, alpha=1.0, glow=0.0):
    """pycairo: same crown centred at (x, y)."""
    import cairo
    if alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    if glow > 0:
        R, sig = GLOW_R * s, GLOW_SIGMA * s
        g = cairo.RadialGradient(0, 0, 0, 0, 0, R + 3 * sig)
        a = 0.55 * glow * alpha
        for k in range(9):
            r = (R + 3 * sig) * k / 8
            prof = 0.5 * (math.erf((R - r) / (math.sqrt(2) * sig)) + math.erf((R + r) / (math.sqrt(2) * sig)))
            g.add_color_stop_rgba(k / 8, *_rgba(GLOW, a * prof))
        ctx.set_source(g)
        ctx.arc(0, 0, R + 3 * sig, 0, 2 * math.pi)
        ctx.fill()
    pts = _points(s)
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.close_path()
    lg = cairo.LinearGradient(0, -22 * s, 0, 14 * s)
    lg.add_color_stop_rgba(0, *_rgba(GOLD_TOP, alpha))
    lg.add_color_stop_rgba(1, *_rgba(GOLD_BOTTOM, alpha))
    ctx.set_source(lg)
    ctx.fill_preserve()
    ctx.set_source_rgba(*_rgba(OUTLINE, 0.9 * alpha))
    ctx.set_line_width(OUTLINE_W * s)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    _round_rect(ctx, -24 * s, 7 * s, 48 * s, 6 * s, 2 * s)
    ctx.set_source_rgba(*_rgba(BAND, alpha))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_rgba(OUTLINE, 0.9 * alpha))
    ctx.set_line_width(BAND_OUTLINE_W * s)
    ctx.stroke()
    for jx, jy, jc in JEWELS:
        ctx.arc(jx * s, jy * s, JEWEL_R * s, 0, 2 * math.pi)
        ctx.set_source_rgba(*_rgba(jc, alpha))
        ctx.fill()
    ctx.restore()


def _preview(path):
    """Top: skia at the sizes the videos use. Bottom: the cairo backend at the same sizes."""
    import skia
    sys.path.append(os.path.join(_HERE, "..", "neon-kit"))
    from neon_kit import SMALLCAP, W, draw_text, make_background
    import cairo
    surf = skia.Surface(W, 1460)
    c = surf.getCanvas()
    c.drawImage(make_background(center=(540.0, 730.0)), 0, 0)
    sizes = [(0.55, 0.0, "0.55 chip"), (1.0, 0.6, "1.0 + glow, holder"), (1.9, 0.0, "1.9 winner-card"),
             (3.0, 1.6, "3.0 + glow, thumbnail")]
    xs = [120, 330, 600, 900]
    draw_text(c, "SKIA  draw_crown()", 540, 150, 34, SMALLCAP, spacing=2)
    for (s, g, label), x in zip(sizes, xs):
        draw_crown(c, x, 420, s, 1.0, glow=g)
        draw_text(c, label, x, 620, 22, SMALLCAP)
    cs = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, 700)
    ctx = cairo.Context(cs)
    for (s, g, label), x in zip(sizes, xs):
        draw_crown_cairo(ctx, x, 260, s, 1.0, glow=g)
    arr = __import__("numpy").ndarray(shape=(700, W, 4), dtype="uint8", buffer=cs.get_data())
    img = skia.Image.fromarray(arr.copy(), colorType=skia.kBGRA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    draw_text(c, "PYCAIRO  draw_crown_cairo()", 540, 900, 34, SMALLCAP, spacing=2)
    c.drawImage(img, 0, 900)
    for (s, g, label), x in zip(sizes, xs):
        draw_text(c, label, x, 1360, 22, SMALLCAP)
    surf.makeImageSnapshot().save(path, skia.kPNG)


if __name__ == "__main__":
    _preview(os.path.join(_HERE, "preview.png"))
    print("wrote preview.png")
