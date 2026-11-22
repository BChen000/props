"""color-chips: the scoreboard row of six colour chips under the title.

Each chip: colour dot, name, HP bar with a white "damage trail", optional highlight
border, optional gold tag above it (e.g. "BIG SWORD"), and a red strike when OUT.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style-kit"))
from kit import (BALL_COLORS, GOLD, HIGHLIGHT, NAMES, PI, W, darken, paint_background,  # noqa: E402
                 rgb, rounded_rect, text, new_canvas)

# --------------------------------------------------------------------------- settings
CHIP_X0, CHIP_STEP, CHIP_Y = 42, 168, 285      # first chip x, spacing, top y
CHIP_W, CHIP_H, CHIP_RADIUS = 156, 66, 13
CHIP_BG = (56, 41, 72)                           # alpha 0.55 when OUT
LABEL = (240, 236, 250)                          # Poppins Bold 23 px (22 px for 6+ letters)
BAR_BG = (0.08, 0.04, 0.12, 0.85)                # float RGBA
STRIKE = (236, 72, 120)
TAG_TEXT = (45, 22, 0)
OUT_ALPHA = 0.42
TRAIL_HOLD, TRAIL_END, TRAIL_FALL = 0.18, 0.68, 0.5   # damage trail: hold 0.18 s, slide until 0.68 s


def hp_with_trail(hits, now, start_hp=100):
    """hits: list of (time, hp_before, hp_after). Returns (current_hp, trail_hp) at `now`."""
    cur, trail = start_hp, start_hp
    for (vh, before, after) in hits:
        if vh <= now:
            cur = after
            age = now - vh
            if age < TRAIL_HOLD:
                trail = before
            elif age < TRAIL_END:
                trail = before + (after - before) * (age - TRAIL_HOLD) / TRAIL_FALL
            else:
                trail = after
    return cur, max(trail, cur)


def draw_chips(ctx, chips, max_hp=100):
    """chips: list of dicts (left to right):
        name, color (RGB), hp, trail, dead (bool),
        border: None or (RGB, width)   e.g. ((255,255,255), 4) roulette pointer,
                                        (GOLD, 4) big-sword owner, ((255,214,80), 4.5) winner
        tag:    None or dict(text="BIG SWORD", scale=0..1.x, dim=bool)
    """
    for i, c in enumerate(chips):
        n = c["name"]
        x0, y0, cw, chh = CHIP_X0 + i * CHIP_STEP, CHIP_Y, CHIP_W, CHIP_H
        col = c["color"]
        dead = c.get("dead", False)
        a = OUT_ALPHA if dead else 1.0
        rounded_rect(ctx, x0, y0, cw, chh, CHIP_RADIUS)
        ctx.set_source_rgba(CHIP_BG[0] / 255, CHIP_BG[1] / 255, CHIP_BG[2] / 255, 0.55 if dead else 1.0)
        ctx.fill()
        ctx.arc(x0 + 26, y0 + 27, 14, 0, 2 * PI)
        ctx.set_source_rgba(*rgb(col if not dead else darken(col, 0.45)))
        ctx.fill()
        label_size = 23 if len(n) <= 5 else 22
        text(ctx, n, x0 + 48, y0 + 28, "b", label_size, LABEL, align="l", alpha=a)
        # hp bar
        bx, by, bw, bh = x0 + 12, y0 + 49, cw - 24, 7
        rounded_rect(ctx, bx, by, bw, bh, 3.5)
        ctx.set_source_rgba(*BAR_BG)
        ctx.fill()
        cur, trail = c.get("hp", max_hp), c.get("trail", c.get("hp", max_hp))
        if trail > cur:
            rounded_rect(ctx, bx, by, bw * trail / max_hp, bh, 3.5)
            ctx.set_source_rgba(1, 1, 1, 0.85)
            ctx.fill()
        if cur > 0:
            rounded_rect(ctx, bx, by, max(bh, bw * cur / max_hp), bh, 3.5)
            ctx.set_source_rgba(*rgb(col))
            ctx.fill()
        border = c.get("border")
        if border:
            rounded_rect(ctx, x0 + 1, y0 + 1, cw - 2, chh - 2, 12)
            ctx.set_source_rgba(*rgb(border[0]))
            ctx.set_line_width(border[1])
            ctx.stroke()
        tag = c.get("tag")
        if tag and tag["scale"] > 0.02:
            dim = tag.get("dim", False)
            ctx.save()
            ctx.translate(x0 + cw / 2, y0 - 6)
            ctx.scale(tag["scale"], tag["scale"])
            rounded_rect(ctx, -64, -15, 128, 30, 15)
            ctx.set_source_rgba(*rgb(GOLD, 0.45 if dim else 1.0))
            ctx.fill_preserve()
            ctx.set_source_rgba(0.12, 0.06, 0.02, 1)
            ctx.set_line_width(2.5)
            ctx.stroke()
            text(ctx, tag.get("text", "BIG SWORD"), 0, 0, "xb", 17, TAG_TEXT, alpha=0.6 if dim else 1.0)
            ctx.restore()
        if dead:
            ctx.set_source_rgba(*rgb(STRIKE, 0.95))
            ctx.set_line_width(4)
            ctx.move_to(x0 + 12, y0 + 14)
            ctx.line_to(x0 + cw - 12, y0 + 50)
            ctx.stroke()


def demo_chips():
    hp = [55, 100, 10, 0, 70, 0]
    chips = []
    for i, n in enumerate(NAMES):
        c = dict(name=n, color=BALL_COLORS[n], hp=hp[i], trail=hp[i], dead=hp[i] == 0)
        chips.append(c)
    chips[0]["tag"] = dict(text="BIG SWORD", scale=1.0, dim=False)
    chips[0]["border"] = (GOLD, 4)
    chips[1]["border"] = ((255, 255, 255), 4)
    chips[2]["border"] = (HIGHLIGHT, 4.5)
    chips[4]["trail"] = 85
    return chips


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    surf, ctx = new_canvas(W, 160)
    ctx.translate(0, -240)
    paint_background(ctx)
    draw_chips(ctx, demo_chips())
    surf.write_to_png(os.path.join(here, "preview.png"))
    print("wrote preview.png")
