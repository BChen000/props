"""neon-marble: the glossy marble of the navy-and-neon Shorts (Ring Escape), drawn with skia-python.

A glossy sphere: soft offset drop shadow, radial gradient (light top-left -> base -> dark rim),
a faint light arc on the lower right, a tilted specular highlight and a small sparkle.
No white rim (that's the look of ../glossy-ball, the purple-theme ball). Optional centred label
(HP or name) and white hit flash. Also draws the motion trail, the gold crown-holder ring, the
winner glow and the dimmed-loser state.
"""
import math
import os
import sys

import skia

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "neon-kit"))
from neon_kit import BALL_COLORS, NAMES, col, draw_text, lerpc  # noqa: E402

# --------------------------------------------------------------------------- settings
MARBLE_R = 22.0               # radius in the video (px at 1080x1920)
LIGHTEN = 0.45                # gradient: lighten 45 % -> 86 % base at 0.42 -> 42 % dark at 1.0
BASE_K = 0.86
DARK_K = 0.42
SHADOW_ALPHA = 0.55           # drop shadow offset (0.16 r, 0.26 r), blur 0.22 r
TRAIL_STEPS = 8               # trail circles, sampled every TRAIL_DT seconds back
TRAIL_DT = 0.011
TRAIL_ALPHA = 0.30
HOLDER_RING = (255, 210, 70)  # gold ring around the crown holder
WIN_GLOW = (255, 215, 80)
DIM_ALPHA = 0.55              # losers after the win
FLASH_ALPHA = 0.85            # white overlay on a hit, scaled by flash 0..1
LABEL_RGB = (255, 255, 255)   # label: DejaVu Sans Bold with a soft dark shadow
SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear)


def marble_sprite(rgb, r=MARBLE_R, big=1.0, pad=None):
    """Returns (skia.Image, half_size). Draw it at (x - half_size, y - half_size).

    pad: transparent margin for the shadow. Default 15 px up to the video size (r <= 22, so Ring
    Escape renders exactly as posted) and 0.9 r above it, so big sprites don't clip their shadow."""
    r = r * big
    if pad is None:
        pad = 15 if r <= MARBLE_R else int(math.ceil(0.9 * r))
    size = int(r * 2 + 2 * pad)
    surf = skia.Surface(size, size)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 0))
    m = size / 2
    sp = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), SHADOW_ALPHA))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r * 0.22))
    c.drawCircle(m + r * 0.16, m + r * 0.26, r * 0.98, sp)
    light = lerpc(rgb, (255, 255, 255), LIGHTEN)
    base = tuple(v * BASE_K for v in rgb)
    dark = tuple(v * DARK_K for v in rgb)
    sh = skia.GradientShader.MakeRadial(skia.Point(m - r * 0.38, m - r * 0.42), r * 1.75,
                                        [skia.Color4f(*[v / 255 for v in light], 1).toColor(),
                                         skia.Color4f(*[v / 255 for v in base], 1).toColor(),
                                         skia.Color4f(*[v / 255 for v in dark], 1).toColor()],
                                        [0.0, 0.42, 1.0])
    c.drawCircle(m, m, r, skia.Paint(AntiAlias=True, Shader=sh))
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=r * 0.08,
                     Color4f=col(lerpc(rgb, (255, 255, 255), 0.25), 0.35))
    path = skia.Path()
    path.addArc(skia.Rect(m - r * 0.86, m - r * 0.86, m + r * 0.86, m + r * 0.86), 20, 80)
    c.drawPath(path, rim)
    hp = skia.Paint(AntiAlias=True, Color4f=col((255, 255, 255), 0.92))
    hp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r * 0.07))
    c.save()
    c.translate(m - r * 0.36, m - r * 0.42)
    c.rotate(-35)
    c.drawOval(skia.Rect(-r * 0.27, -r * 0.17, r * 0.27, r * 0.17), hp)
    c.restore()
    hp2 = skia.Paint(AntiAlias=True, Color4f=col((255, 255, 255), 0.55))
    c.drawCircle(m - r * 0.08, m - r * 0.55, r * 0.06, hp2)
    return surf.makeImageSnapshot(), m


def draw_trail(c, points, rgb, r=MARBLE_R, dim=False):
    """points: past centres, newest first (j = 1..TRAIL_STEPS, every TRAIL_DT s)."""
    for j, (x, y) in enumerate(points, start=1):
        a = TRAIL_ALPHA * (1 - j / (TRAIL_STEPS + 1.0))
        if dim:
            a *= 0.5
        c.drawCircle(x, y, r * (0.92 - 0.05 * j), skia.Paint(AntiAlias=True, Color4f=col(rgb, a)))


def draw_holder_ring(c, x, y, tau, r=MARBLE_R, winner_glow=False):
    """Pulsing gold ring around the crown holder; winner_glow adds a soft gold halo."""
    pulse = 0.5 + 0.5 * math.sin(tau * 9)
    hp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.5, Color4f=col(HOLDER_RING, 0.85))
    c.drawCircle(x, y, r + 6 + 1.5 * pulse, hp)
    if winner_glow:
        gp = skia.Paint(AntiAlias=True, Color4f=col(WIN_GLOW, 0.45 + 0.2 * pulse))
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
        c.drawCircle(x, y, r + 16, gp)


def draw_marble(c, sprite, x, y, dim=False, label=None, label_size=None, flash=0.0, r=MARBLE_R):
    """Draw a sprite from marble_sprite(). label: e.g. HP; flash: 0..1 white hit flash; r: sprite radius."""
    img, m = sprite
    paint = skia.Paint(Color4f=skia.Color4f(1, 1, 1, DIM_ALPHA)) if dim else None
    c.drawImage(img, x - m, y - m, SAMPLING, paint)
    if flash > 0:
        c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Color4f=col((255, 255, 255), FLASH_ALPHA * flash)))
    if label:
        draw_text(c, str(label), x, y, label_size or round(0.8 * r), LABEL_RGB, maxw=1.7 * r, shadow=1.0)


def _preview(path):
    from neon_kit import W, H, SMALLCAP, draw_text, make_background
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    c.drawImage(make_background(center=(540.0, 960.0)), 0, 0)
    for i, name in enumerate(NAMES):
        x = 135 + (i % 4) * 270
        y = 330 + (i // 4) * 300
        draw_marble(c, marble_sprite(BALL_COLORS[name], big=3.0), x, y)
        draw_text(c, name, x, y + 105, 28, SMALLCAP)
    y = 1150
    draw_text(c, "VIDEO SIZE  r = 22", 540, y - 80, 30, SMALLCAP)
    for i, name in enumerate(NAMES):
        x = 190 + i * 100
        pts = [(x - 16 * j, y + 6 * j) for j in range(1, TRAIL_STEPS + 1)]
        draw_trail(c, pts, BALL_COLORS[name])
        draw_marble(c, marble_sprite(BALL_COLORS[name]), x, y)
    y = 1420
    draw_text(c, "CROWN HOLDER  /  WINNER  /  DIMMED LOSER", 540, y - 90, 30, SMALLCAP)
    draw_holder_ring(c, 340, y, 0.0)
    draw_marble(c, marble_sprite(BALL_COLORS["RED"]), 340, y)
    draw_holder_ring(c, 540, y, 0.0, winner_glow=True)
    draw_marble(c, marble_sprite(BALL_COLORS["CYAN"]), 540, y)
    draw_marble(c, marble_sprite(BALL_COLORS["PINK"]), 740, y, dim=True)
    y = 1700
    draw_text(c, "LABEL  /  HIT FLASH  (r = 40)", 540, y - 100, 30, SMALLCAP)
    draw_marble(c, marble_sprite(BALL_COLORS["BLUE"], r=40), 420, y, label="85", r=40)
    draw_marble(c, marble_sprite(BALL_COLORS["ORANGE"], r=40), 660, y, label="85", flash=0.6, r=40)
    surf.makeImageSnapshot().save(path, skia.kPNG)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, "assets"), exist_ok=True)
    for name in NAMES:
        img, m = marble_sprite(BALL_COLORS[name], big=4.0)
        img.save(os.path.join(here, "assets", f"marble_{name.lower()}.png"), skia.kPNG)
    _preview(os.path.join(here, "preview.png"))
    print("wrote preview.png and assets/marble_<color>.png")
