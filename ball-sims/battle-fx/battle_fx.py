"""battle-fx: hit / clash / KO particle bursts, floating damage numbers, screen shake,
final-blow camera zoom, slow-motion vignette and the flying sword of a KO'd ball.

Particles are pre-generated per event from a fixed seed, so every render is identical.
"""
import math
import os
import random
import sys

import cairo

_HERE = os.path.dirname(os.path.abspath(__file__))
for _dep in ("style-kit", "sword"):
    sys.path.append(os.path.join(_HERE, "..", _dep))
from kit import PI, WHITE, clamp, ease_in_out, ease_out, lighten, rgb, text  # noqa: E402
from sword import draw_sword  # noqa: E402

# --------------------------------------------------------------------------- settings
SPARK = (255, 236, 150)           # clash spark colour (60 %), rest white
CLASH_FLASH = (1, 0.95, 0.7)      # float RGB
BIG_HIT_RING = (1, 0.9, 0.5)      # float RGB
DMG_BIG = (255, 214, 80)          # "-30"  ExtraBold 52, outline (40,10,10)
DMG_SMALL = (255, 255, 255)       # "-15"  ExtraBold 38, outline (30,10,40)
PARTICLE_SEED = 1000              # random.Random(PARTICLE_SEED + event_index)
HORIZON = 1.2                     # seconds an event can still draw


def make_particles(kind, index, big=False, color=None):
    """kind: "hit" (color = victim), "clash", or "kill" (color = victim)."""
    rng = random.Random(PARTICLE_SEED + index)
    parts = []
    if kind == "hit":
        n = 16 if big else 10
        for _ in range(n):
            a = rng.uniform(0, 2 * PI)
            parts.append((a, rng.uniform(250, 620 if big else 460), rng.uniform(0.25, 0.5),
                          rng.uniform(4, 8 if big else 6),
                          color if rng.random() < 0.7 else (255, 255, 255)))
    elif kind == "clash":
        for _ in range(14 if big else 10):
            a = rng.uniform(0, 2 * PI)
            parts.append((a, rng.uniform(300, 750), rng.uniform(0.15, 0.32), rng.uniform(2.5, 4.5),
                          SPARK if rng.random() < 0.6 else (255, 255, 255)))
    elif kind == "kill":
        for _ in range(46):
            a = rng.uniform(0, 2 * PI)
            parts.append((a, rng.uniform(150, 820), rng.uniform(0.45, 0.95), rng.uniform(5, 12),
                          color if rng.random() < 0.75 else lighten(color, 0.6)))
    return parts


def particle_pos(x, y, a, sp, age, drag=5.0):
    d = sp * (1 - math.exp(-drag * age)) / drag
    return x + math.cos(a) * d, y + math.sin(a) * d


def draw_burst(ctx, kind, x, y, age, parts, big=False, color=None, ball_r=40.0):
    """Draw one event's effect `age` seconds after it happened (sim time -> slows in slow-mo)."""
    if kind == "clash":
        if age < 0.14:
            rr = 10 + 46 * ease_out(age / 0.14)
            ctx.arc(x, y, rr, 0, 2 * PI)
            ctx.set_source_rgba(CLASH_FLASH[0], CLASH_FLASH[1], CLASH_FLASH[2], 0.85 * (1 - age / 0.14))
            ctx.fill()
        for (a, sp, life, sz, col) in parts:
            if age < life:
                p1 = particle_pos(x, y, a, sp, age, 7)
                p0 = particle_pos(x, y, a, sp, max(0, age - 0.035), 7)
                ctx.move_to(*p0)
                ctx.line_to(*p1)
                ctx.set_source_rgba(*rgb(col, 1 - age / life))
                ctx.set_line_width(sz)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
    elif kind == "hit":
        if age < 0.2 and big:
            rr = 20 + 90 * ease_out(age / 0.2)
            ctx.arc(x, y, rr, 0, 2 * PI)
            ctx.set_source_rgba(BIG_HIT_RING[0], BIG_HIT_RING[1], BIG_HIT_RING[2], 0.75 * (1 - age / 0.2))
            ctx.set_line_width(6)
            ctx.stroke()
        for (a, sp, life, sz, col) in parts:
            if age < life:
                px, py = particle_pos(x, y, a, sp, age, 6)
                ctx.arc(px, py, sz * (1 - age / life), 0, 2 * PI)
                ctx.set_source_rgba(*rgb(col, 1.0))
                ctx.fill()
    elif kind == "kill":
        if age < 0.6:
            rr = ball_r + 230 * ease_out(age / 0.6)
            ctx.arc(x, y, rr, 0, 2 * PI)
            ctx.set_source_rgba(*rgb(lighten(color, 0.4), 0.8 * (1 - age / 0.6)))
            ctx.set_line_width(10 * (1 - age / 0.6) + 2)
            ctx.stroke()
        if age < 0.18:
            ctx.arc(x, y, ball_r * (1 + 1.6 * age / 0.18), 0, 2 * PI)
            ctx.set_source_rgba(1, 1, 1, 0.9 * (1 - age / 0.18))
            ctx.fill()
        for (a, sp, life, sz, c2) in parts:
            if age < life:
                px, py = particle_pos(x, y, a, sp, age, 3.2)
                py += 160 * age * age
                ctx.arc(px, py, sz * (1 - 0.7 * age / life), 0, 2 * PI)
                ctx.set_source_rgba(*rgb(c2, 1 - (age / life) ** 2))
                ctx.fill()


def draw_damage_number(ctx, x, y, dmg, age, big):
    """Floating "-30"/"-15" above the hit point; age in VIDEO seconds (stays readable in slow-mo)."""
    if not (0 <= age < 0.75):
        return
    rise = 70 * ease_out(age / 0.75)
    sc = 1.0 + 0.5 * (1 - ease_out(age / 0.12))
    a = clamp(1 - ((age - 0.45) / 0.3) if age > 0.45 else 1)
    if big:
        text(ctx, f"-{dmg}", x, y - 30 - rise, "xb", 52, DMG_BIG, outline=(40, 10, 10), ow=5, scale=sc, alpha=a)
    else:
        text(ctx, f"-{dmg}", x, y - 26 - rise, "xb", 38, DMG_SMALL, outline=(30, 10, 40), ow=4, scale=sc, alpha=a)


def shake_offset(v, events, fps=30):
    """Camera shake (dx, dy) at video time v from events with keys v, type, big."""
    amp = 0.0
    for e in events:
        age_v = v - e["v"]
        if age_v < 0 or age_v > 0.5:
            continue
        if e["type"] == "kill":
            amp += 13 * max(0, 1 - age_v / 0.45)
        elif e["type"] == "hit":
            amp += (7 if e["big"] else 2.5) * max(0, 1 - age_v / 0.2)
    if amp <= 0.05:
        return 0.0, 0.0
    f = v * fps
    return amp * math.sin(f * 2.1 + 0.3), amp * math.cos(f * 2.7 + 1.1)


def zoom_cam(v, v_slow, v_final, focus, zoom=1.18, rest=(540.0, 1010.0)):
    """Final-blow zoom of the whole arena about `focus` (x, y).

    Eases 1 -> zoom from v_slow to v_final, bumps +0.05 during the 0.42 s hit-stop, eases
    back to 1 over 0.85 s. Returns (z, px, py); apply translate(px,py) scale(z) translate(-px,-py).
    """
    if v < v_slow or v > v_final + 1.3:
        return 1.0, rest[0], rest[1]
    px, py = focus
    if v < v_final:
        z = 1 + (zoom - 1) * ease_in_out((v - v_slow) / max(0.01, v_final - v_slow))
    elif v < v_final + 0.42:
        z = zoom + 0.05 * math.sin(PI * clamp((v - v_final) / 0.42))
    else:
        z = zoom - (zoom - 1) * ease_in_out((v - v_final - 0.42) / 0.85)
    return z, px, py


def draw_slowmo_vignette(ctx, cx=540.0, cy=1010.0, r=445.0):
    ctx.arc(cx, cy, r, 0, 2 * PI)
    vg = cairo.RadialGradient(cx, cy, r * 0.35, cx, cy, r)
    vg.add_color_stop_rgba(0, 0, 0, 0, 0)
    vg.add_color_stop_rgba(1, 0.0, 0.0, 0.0, 0.6)
    ctx.set_source(vg)
    ctx.fill()


def draw_sword_flyoff(ctx, kill_x, kill_y, th0, age, big, color, ball_r=40.0, center=(540.0, 1010.0)):
    """A KO'd ball's sword flies outward, spins and falls for 0.9 s (sim seconds)."""
    if not (0 <= age < 0.9):
        return
    dirx, diry = kill_x - center[0], kill_y - center[1]
    dl = math.hypot(dirx, diry) or 1
    px = kill_x + dirx / dl * 140 * age
    py = kill_y + diry / dl * 140 * age - 260 * age + 420 * age * age
    draw_sword(ctx, px, py, th0 + 9 * age, ball_r - 2, big, color,
               alpha=clamp(1 - age / 0.9), scale=1 - 0.3 * age)


if __name__ == "__main__":
    sys.path.append(os.path.join(_HERE, "..", "glossy-ball"))
    sys.path.append(os.path.join(_HERE, "..", "arena-board"))
    from glossy_ball import draw_ball
    import arena_board as board
    from kit import BALL_COLORS, new_canvas, paint_background
    surf, ctx = new_canvas(1080, 900)
    ctx.translate(0, -560)
    paint_background(ctx)
    ctx.set_source_surface(board.make_floor(), 0, 0)
    ctx.paint()
    board.draw_rim(ctx, board.RIM_FIGHT)
    # clash sparks
    draw_burst(ctx, "clash", 300, 800, 0.10, make_particles("clash", 3, big=True), big=True)
    text(ctx, "clash", 300, 900, "b", 30, WHITE)
    # big hit
    blue = BALL_COLORS["BLUE"]
    draw_ball(ctx, 760, 790, 40.0, blue, "70", flash=0.5)
    draw_burst(ctx, "hit", 735, 760, 0.09, make_particles("hit", 5, big=True, color=blue), big=True)
    draw_damage_number(ctx, 735, 760, 30, 0.2, True)
    text(ctx, "big hit", 760, 900, "b", 30, WHITE)
    # KO explosion + flying sword
    purple = BALL_COLORS["PURPLE"]
    draw_burst(ctx, "kill", 540, 1190, 0.16, make_particles("kill", 9, color=purple), color=purple)
    draw_sword_flyoff(ctx, 540, 1190, -2.4, 0.3, False, purple)
    text(ctx, "KO", 540, 1405, "b", 30, WHITE)
    surf.write_to_png(os.path.join(_HERE, "preview.png"))
    print("wrote preview.png")
