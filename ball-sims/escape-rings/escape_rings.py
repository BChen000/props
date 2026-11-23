"""escape-rings: the Ring Escape board. Concentric neon rings, each with a rotating gap.

- The ring to escape next ("active") is brighter and thicker, and white dots mark its gap ends.
- Rings that have not been reached yet are dimmed.
- The last ring turns gold and pulses. On the win it flashes white and its gap closes.
- A broken ring shatters into 26 spinning fragments with a flash wave.
- In the loop reset, broken rings fade back in and every ring rotates back to its start angle.

Colours go from violet (inner) to cyan (outer). Drawing uses skia-python. Angles are in
radians, measured clockwise on screen from +x (y points down).
"""
import math
import os
import sys

import skia

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "neon-kit"))
from neon_kit import (ARENA, ARENA_GLOW, BG, W, H, clamp, col, ease_out, hrand, lerp, lerpc,  # noqa: E402
                      make_background)

# --------------------------------------------------------------------------- settings
N_RINGS = 10
R_INNER, R_OUTER = 110.0, 452.0            # ring radii in px (linear spacing)
GAPS_DEG = [32, 26, 23, 21, 20, 19, 19, 19, 19, 11]   # gap width per ring (inner -> outer)
RING_IN = (150, 110, 255)                  # innermost ring colour
RING_OUT = (60, 215, 255)                  # outermost ring colour
ACTIVE = dict(alpha=1.0, width=9.0, glow=1.0, core=0.35, dot_alpha=0.85)
IDLE = dict(alpha=0.5, width=7.0, glow=0.55, core=0.2)
LAST_RING_GOLD = (255, 190, 50)            # last ring, pulse mixes 25 % toward LAST_RING_HOT
LAST_RING_HOT = (255, 120, 60)
LAST_RING_WIDTH = 11.0
PULSE_HZ = 2.2
WIN_FLASH = (255, 255, 230)
GAP_DOT_R = 7.0
SHATTER_PIECES = 26
SHATTER_LIFE = 0.85                        # s (sim time) until fragments vanish
ARENA_PAD = 16.0                           # arena disc radius = outer ring + pad


def ring_radii(n=N_RINGS, r0=R_INNER, r1=R_OUTER):
    if n == 1:
        return [r1]
    return [r0 + (r1 - r0) * k / (n - 1) for k in range(n)]


def ring_color(k, n):
    if n <= 1:
        return RING_OUT
    return lerpc(RING_IN, RING_OUT, k / (n - 1))


def arc_path(cx, cy, R, start_rad, sweep_rad):
    p = skia.Path()
    if sweep_rad >= 2 * math.pi - 1e-3:
        p.addCircle(cx, cy, R)
        return p
    p.addArc(skia.Rect(cx - R, cy - R, cx + R, cy + R), math.degrees(start_rad), math.degrees(sweep_rad))
    return p


def stroke_glow(c, path, rgb, alpha, width, glow=1.0, core_white=0.35):
    """Neon stroke: blurred halo (3x width), solid core, thin whitish centre line."""
    if alpha <= 0.01:
        return
    if glow > 0:
        g = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width * 3.0,
                       StrokeCap=skia.Paint.kRound_Cap, Color4f=col(rgb, 0.42 * alpha * glow))
        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, width * 1.3))
        c.drawPath(path, g)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width,
                   StrokeCap=skia.Paint.kRound_Cap, Color4f=col(rgb, alpha))
    c.drawPath(path, p)
    if core_white > 0:
        p2 = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width * 0.36,
                        StrokeCap=skia.Paint.kRound_Cap,
                        Color4f=col(lerpc(rgb, (255, 255, 255), 0.7), alpha * core_white * 2))
        c.drawPath(path, p2)


def draw_arena_disc(c, cx, cy, r_outer=R_OUTER):
    """Dark arena disc under the rings, with a soft lighter centre."""
    R = r_outer + ARENA_PAD
    c.drawCircle(cx, cy, R, skia.Paint(AntiAlias=True, Color4f=col(ARENA)))
    sh = skia.GradientShader.MakeRadial(skia.Point(cx, cy), R,
                                        [col(ARENA_GLOW, 0.55).toColor(), col(ARENA, 0.0).toColor()], [0.0, 1.0])
    c.drawCircle(cx, cy, R, skia.Paint(AntiAlias=True, Shader=sh))


def draw_shatter(c, cx, cy, k, n, R, age, phase, gap):
    """Ring k breaking: fragments fly out and spin for SHATTER_LIFE s, plus a 0.35 s flash wave. age in s."""
    if age > 1.0:
        return
    d = age
    rgb = ring_color(k, n)
    sweep_tot = 2 * math.pi - gap
    seg = sweep_tot / SHATTER_PIECES
    for j in range(SHATTER_PIECES):
        a0 = phase + gap / 2 + j * seg
        mid = a0 + seg / 2
        sp = 260 + 420 * hrand(k, j, 1)
        tang = (hrand(k, j, 2) - 0.5) * 300
        drag = math.exp(-2.2 * d)
        dist = sp * (1 - drag) / 2.2
        tdist = tang * (1 - drag) / 2.2
        ux, uy = math.cos(mid), math.sin(mid)
        px = cx + (R + dist) * ux - tdist * uy
        py = cy + (R + dist) * uy + tdist * ux
        spin = (hrand(k, j, 3) - 0.5) * 9 * d
        alpha = clamp(1 - d / SHATTER_LIFE) ** 1.3
        L = R * seg * 0.42 * (1 - 0.45 * d)
        c.save()
        c.translate(px, py)
        c.rotate(math.degrees(mid + math.pi / 2 + spin))
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7, StrokeCap=skia.Paint.kRound_Cap,
                       Color4f=col(lerpc(rgb, (255, 255, 255), 0.35 * (1 - d)), alpha))
        c.drawLine(-L, 0, L, 0, p)
        c.restore()
    if d < 0.35:
        x = d / 0.35
        fp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=14 * (1 - x) + 2,
                        Color4f=col(lerpc(rgb, (255, 255, 255), 0.6), 0.8 * (1 - x)))
        fp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
        c.drawCircle(cx, cy, R + 70 * ease_out(x), fp)


def _gap_dots(c, cx, cy, R, phase, gap, alpha):
    for sgn in (-1, 1):
        ea = phase + sgn * gap / 2
        ex, ey = cx + R * math.cos(ea), cy + R * math.sin(ea)
        gp = skia.Paint(AntiAlias=True, Color4f=col((255, 255, 255), alpha))
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
        c.drawCircle(ex, ey, GAP_DOT_R, gp)


def draw_rings(c, cx, cy, radii, phases, gaps, broken_age, cur, final_active=False, pulse_tau=0.0,
               won_flash=None, reset=None):
    """Draw the whole ring set.

    radii, phases, gaps: per ring (px, rad, rad); phases/gaps are the current values.
    broken_age: per ring, None if intact, else seconds since it broke (it shatters).
    cur: index of the ring to escape next. final_active: the last ring is the active one (gold).
    pulse_tau: video time driving the gold pulse. won_flash: None, or 0..1 white flash on the last ring.
    reset: None during play. In the loop reset pass dict(u, ue, phases0, gaps0): u = 0..1 progress,
           ue = eased progress, phases0/gaps0 = start values. Broken rings fade back in.
    """
    n = len(radii)
    for k in range(n):
        R = radii[k]
        ph = phases[k]
        gap = gaps[k]
        broken = broken_age[k] is not None
        ring_scale = 1.0
        dot_a = 0.0
        if reset is None:
            if broken:
                draw_shatter(c, cx, cy, k, n, R, broken_age[k], ph, gap)
                continue
            active = k == cur
            rgb = ring_color(k, n)
            st = ACTIVE if active else IDLE
            a, width, glow, core = st["alpha"], st["width"], st["glow"], st["core"]
            dot_a = ACTIVE["dot_alpha"] if active else 0.0
            if k == n - 1 and final_active:
                pulse = 0.5 + 0.5 * math.sin(pulse_tau * 2 * math.pi * PULSE_HZ)
                rgb = lerpc(LAST_RING_GOLD, LAST_RING_HOT, 0.25 * pulse)
                width = LAST_RING_WIDTH
                glow = 1.0 + 0.6 * pulse
                if won_flash is not None:
                    fl = won_flash
                    rgb = lerpc(rgb, WIN_FLASH, fl)
                    glow += 1.5 * fl
        else:
            u, ue = reset["u"], reset["ue"]
            ph0 = reset["phases0"][k]
            dph = (ph0 - ph + math.pi) % (2 * math.pi) - math.pi
            ph = ph + dph * ue
            active0 = k == 0
            rgb = ring_color(k, n)
            st = ACTIVE if active0 else IDLE
            a, width, glow, core = st["alpha"], st["width"], st["glow"], st["core"]
            if k == n - 1:
                gap = gap + (reset["gaps0"][k] - gap) * ue
                rgb = lerpc(LAST_RING_GOLD, rgb, ue)
                width = lerp(LAST_RING_WIDTH, width, ue)
                glow = lerp(1.6, glow, ue)
                a = lerp(1.0, a, ue)
            fade = 1.0
            if broken:
                fade = ease_out((u - 0.05 - 0.035 * k) / 0.45)
                ring_scale = lerp(1.18, 1.0, fade)
            a *= fade
            dot_a = ACTIVE["dot_alpha"] * fade if active0 else 0.0
        if a <= 0.01:
            continue
        Rd = R * ring_scale
        stroke_glow(c, arc_path(cx, cy, Rd, ph + gap / 2, 2 * math.pi - gap), rgb, a, width, glow=glow,
                    core_white=core)
        if dot_a > 0 and gap > 0.01:
            _gap_dots(c, cx, cy, Rd, ph, gap, dot_a)


def _preview(path):
    """Two boards: a fresh start (left/top) and the last ring with ring 9 shattering (bottom)."""
    bg = make_background(center=(540.0, 960.0))
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    c.drawImage(bg, 0, 0)
    radii = ring_radii()
    gaps = [math.radians(g) for g in GAPS_DEG]
    phases = [0.6 + 1.7 * k for k in range(N_RINGS)]
    for (cy, broken, cur, final) in [(500.0, [None] * N_RINGS, 0, False),
                                     (1420.0, [9.0] * (N_RINGS - 2) + [0.12, None], N_RINGS - 1, True)]:
        c.save()
        c.translate(540, cy)
        c.scale(0.92, 0.92)
        c.translate(-540, -cy)
        draw_arena_disc(c, 540, cy)
        draw_rings(c, 540, cy, radii, phases, gaps, broken, cur, final_active=final, pulse_tau=0.1)
        c.restore()
    surf.makeImageSnapshot().save(path, skia.kPNG)


if __name__ == "__main__":
    _preview(os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.png"))
    print("wrote preview.png")
