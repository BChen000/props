"""neon-fx: the particle and camera effects of Ring Escape (navy-and-neon look).

Every effect is stateless: give it the event position, the age of the event (seconds) and a seed,
and it draws that moment. So any frame can be rendered on its own, in any order or in parallel.
Randomness comes from neon_kit.hrand(seed, i, k).

- burst(): 18 coloured particles when a marble breaks a ring (0.7 s)
- sparks(): 5 white sparks on a hard marble-marble hit (0.3 s)
- edge_sparks(): 9 gold sparks plus a glow when a marble clips the gap edge, i.e. a near miss (0.45 s)
- shockwave(): expanding gold ring on the win (0.6 s)
- confetti(): 150 spinning confetti pieces with gravity from the winner (2.6 s)
- start_ring(): white ring that bursts out of the centre on frame 0 (0.5 s)
- shake(): screen-shake offset from recent hits

The slow-motion vignette is shared with Sword Roulette: ../battle-fx draw_slowmo_vignette_skia().
"""
import math
import os
import sys

import skia

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "neon-kit"))
from neon_kit import BALL_COLORS, NAMES, W, H, clamp, col, ease_out, hrand, lerpc  # noqa: E402

# --------------------------------------------------------------------------- settings
BURST_LIFE, SPARK_LIFE, EDGE_LIFE, WAVE_LIFE, CONFETTI_LIFE = 0.7, 0.3, 0.45, 0.6, 2.6
SPARK_MIN_SPEED = 160.0                  # only hits faster than this (px/s) make sparks
EDGE_GOLD = (255, 220, 120)
EDGE_GLOW = (255, 240, 180)
WAVE_GOLD = (255, 230, 140)
CONFETTI_EXTRA = [(255, 255, 255), (255, 214, 70)]
SHAKE_BREAK = (7.0, 0.35)                # amplitude px, duration s
SHAKE_WIN = (11.0, 0.5)


def burst(c, x, y, rgb, age, seed):
    """Ring break: 18 particles in the breaker's colour."""
    d = age
    if not (0 <= d < BURST_LIFE):
        return
    for j in range(18):
        ang = hrand(seed, j, 7) * 2 * math.pi
        sp = 180 + 380 * hrand(seed, j, 8)
        dist = sp * (1 - math.exp(-3.5 * d)) / 3.5
        a = clamp(1 - d / BURST_LIFE)
        c.drawCircle(x + math.cos(ang) * dist, y + math.sin(ang) * dist, 5.5 * a + 1,
                     skia.Paint(AntiAlias=True, Color4f=col(lerpc(rgb, (255, 255, 255), 0.3), a)))


def sparks(c, x, y, age, seed):
    """Marble-marble hit: 5 small white sparks."""
    d = age
    if not (0 <= d <= SPARK_LIFE):
        return
    for q in range(5):
        ang = hrand(seed, q, 11) * 2 * math.pi
        v = 120 + 260 * hrand(seed, q, 12)
        dist = v * (1 - math.exp(-6 * d)) / 6
        a = clamp(1 - d / SPARK_LIFE)
        c.drawCircle(x + math.cos(ang) * dist, y + math.sin(ang) * dist, 2.6 * a + 0.6,
                     skia.Paint(AntiAlias=True, Color4f=col((255, 255, 255), 0.9 * a)))


def edge_sparks(c, x, y, age, seed):
    """Near miss on a gap edge: 9 gold sparks + a soft glow."""
    d = age
    if not (0 <= d < EDGE_LIFE):
        return
    a = clamp(1 - d / EDGE_LIFE)
    for q in range(9):
        ang = hrand(seed, q, 21) * 2 * math.pi
        v = 160 + 330 * hrand(seed, q, 22)
        dist = v * (1 - math.exp(-5 * d)) / 5
        c.drawCircle(x + math.cos(ang) * dist, y + math.sin(ang) * dist, 3.4 * a + 0.6,
                     skia.Paint(AntiAlias=True, Color4f=col(EDGE_GOLD, a)))
    gp = skia.Paint(AntiAlias=True, Color4f=col(EDGE_GLOW, 0.75 * a))
    gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
    c.drawCircle(x, y, 22 * a + 4, gp)


def shockwave(c, x, y, age):
    d = age
    if not (0 <= d < WAVE_LIFE):
        return
    k = d / WAVE_LIFE
    sp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=16 * (1 - k) + 2,
                    Color4f=col(WAVE_GOLD, 0.9 * (1 - k)))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
    c.drawCircle(x, y, 30 + 260 * ease_out(k), sp)


def confetti(c, x, y, age, colors=None, count=150):
    """Burst of confetti from (x, y), falling with gravity, fading from 1.4 s to 2.6 s."""
    d = age
    if not (0 <= d < CONFETTI_LIFE):
        return
    cols = (colors if colors is not None else [BALL_COLORS[n] for n in NAMES]) + CONFETTI_EXTRA
    for q in range(count):
        ang = hrand(q, 31) * 2 * math.pi
        v = 300 + 900 * hrand(q, 32)
        dist = v * (1 - math.exp(-2.6 * d)) / 2.6
        gy = 260 * d * d
        px = x + math.cos(ang) * dist
        py = y + math.sin(ang) * dist + gy
        a = clamp(1 - (d - 1.4) / 1.2)
        if a <= 0:
            continue
        rgb = cols[int(hrand(q, 33) * len(cols)) % len(cols)]
        c.save()
        c.translate(px, py)
        c.rotate(hrand(q, 34) * 360 + d * 400 * (hrand(q, 35) - 0.5))
        c.drawRect(skia.Rect(-6, -3, 6, 3), skia.Paint(AntiAlias=True, Color4f=col(rgb, a)))
        c.restore()


def start_ring(c, cx, cy, tau, r0=62.0):
    """Frame-0 burst: a white ring grows from r0 to r0+200 px over 0.5 s of video."""
    if not (0 <= tau < 0.5):
        return
    x = tau / 0.5
    sp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10 * (1 - x) + 1,
                    Color4f=col((255, 255, 255), 0.7 * (1 - x) ** 1.5))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
    c.drawCircle(cx, cy, r0 + 200 * ease_out(x), sp)


def shake(break_ages_and_seeds, win_age=None):
    """Offset (dx, dy) in px. break_ages_and_seeds: [(age_s, seed)] of recent ring breaks."""
    sx = sy = 0.0
    amp, life = SHAKE_BREAK
    for d, seed in break_ages_and_seeds:
        if 0 <= d < life:
            a = amp * (1 - d / life) ** 2
            sx += a * math.sin(d * 90 + seed * 7)
            sy += a * math.cos(d * 77 + seed * 3)
    if win_age is not None:
        amp, life = SHAKE_WIN
        d = win_age
        if 0 <= d < life:
            a = amp * (1 - d / life) ** 2
            sx += a * math.sin(d * 70)
            sy += a * math.cos(d * 63)
    return sx, sy


def _preview(path):
    from neon_kit import SMALLCAP, draw_text, make_background
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    c.drawImage(make_background(center=(540.0, 960.0)), 0, 0)
    cells = [("burst() 0.12 s", lambda x, y: burst(c, x, y, BALL_COLORS["PURPLE"], 0.12, 0.8)),
             ("sparks() 0.08 s", lambda x, y: sparks(c, x, y, 0.08, 3.1)),
             ("edge_sparks() 0.1 s", lambda x, y: edge_sparks(c, x, y, 0.1, 2.2)),
             ("shockwave() 0.2 s", lambda x, y: shockwave(c, x, y, 0.2)),
             ("start_ring() 0.15 s", lambda x, y: start_ring(c, x, y, 0.15)),
             ("confetti() 0.5 s", lambda x, y: confetti(c, x, y - 60, 0.5))]
    for i, (label, fn) in enumerate(cells):
        x = 270 + (i % 2) * 540
        y = 330 + (i // 2) * 560
        c.save()
        c.clipRect(skia.Rect(x - 265, y - 260, x + 265, y + 230))
        fn(x, y)
        c.restore()
        draw_text(c, label, x, y + 250, 28, SMALLCAP)
    surf.makeImageSnapshot().save(path, skia.kPNG)


if __name__ == "__main__":
    _preview(os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.png"))
    print("wrote preview.png")
