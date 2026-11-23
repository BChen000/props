"""neon-hud: the Ring Escape overlay in the navy-and-neon look (the counterpart of color-chips & co.).

- Colour chips: a 2x4 grid of pills with a colour dot, the name, a gold count badge, a crown
  over the leader's chip, a pop when that colour scores, and grey chips for the losers.
- Headline: the big centre text ("PICK YOUR COLOR!", a countdown number, "LAST RING!",
  "<NAME> WINS!"), with a back-out pop.
- Status line: "7 RINGS LEFT  •  RED HAS THE CROWN", with the name in its colour.
- Bottom caption + small caption, with a pop.
- Progress bar.

Every function takes plain values (texts, colours, 0..1 animation amounts), so any game can drive it.
Drawing uses skia-python and neon-kit's DejaVu Sans Bold text helper.
"""
import math
import os
import sys

import skia

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "..", "neon-kit"))
sys.path.append(os.path.join(_HERE, "..", "crown-icon"))
from neon_kit import (BALL_COLORS, CAPTION, CHIP_FILL, DIM, DIM_TEXT, GOLD, NAMES, PICK_YELLOW, SMALLCAP,  # noqa: E402
                      W, WHITE, YELLOW, back_out, clamp, col, draw_text, lerp, lerpc, text_w)
from crown_icon import draw_crown  # noqa: E402

# --------------------------------------------------------------------------- layout (px at 1080x1920)
CHIP_XS = [133, 403, 673, 943]     # chip centres, 4 per row
CHIP_YS = [258, 328]               # two rows
CHIP_W, CHIP_H, CHIP_RADIUS = 186, 52, 13
HEADLINE_Y = 432                   # big centre text
STATUS_Y = 512                     # line under it
CAPTION_Y, SMALLCAP_Y = 1515, 1640
BAR_X0, BAR_X1, BAR_Y = 104, 976, 1580
BAR_TRACK = (30, 38, 62)
HOLDER_GOLD = (255, 210, 70)
BADGE_TEXT = (40, 25, 5)


def draw_chip(c, cx, cy, name, rgb, count=0, holder=False, winner=False, dim=False, pop=0.0, crown=True):
    """One chip. pop: 0..1 (1 right after this colour scored). holder: leader (gold outline + crown)."""
    a = 0.35 if dim else 1.0
    outline = DIM if dim else rgb
    rect = skia.Rect(cx - CHIP_W / 2, cy - CHIP_H / 2, cx + CHIP_W / 2, cy + CHIP_H / 2)
    c.save()
    if pop > 0:
        c.translate(cx, cy)
        c.scale(1 + 0.12 * pop, 1 + 0.12 * pop)
        c.translate(-cx, -cy)
    if holder or winner:
        gp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10, Color4f=col(GOLD, 0.55))
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 7))
        c.drawRoundRect(rect, CHIP_RADIUS, CHIP_RADIUS, gp)
    c.drawRoundRect(rect, CHIP_RADIUS, CHIP_RADIUS, skia.Paint(AntiAlias=True, Color4f=col(CHIP_FILL, 0.92)))
    if pop > 0:
        c.drawRoundRect(rect, CHIP_RADIUS, CHIP_RADIUS, skia.Paint(AntiAlias=True, Color4f=col(rgb, 0.35 * pop)))
    oc = HOLDER_GOLD if (holder or winner) else outline
    c.drawRoundRect(rect, CHIP_RADIUS, CHIP_RADIUS,
                    skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.2,
                               Color4f=col(oc, 1.0 if not dim else 0.6)))
    c.drawCircle(cx - 68, cy, 9, skia.Paint(AntiAlias=True, Color4f=col(rgb if not dim else DIM, 1.0)))
    draw_text(c, name, cx - 50, cy + 1, 21, (255, 255, 255) if not dim else DIM_TEXT, align="left", spacing=0.3)
    if count > 0:
        bx = cx + 73
        c.drawCircle(bx, cy, 13, skia.Paint(AntiAlias=True, Color4f=col(GOLD, a)))
        draw_text(c, str(count), bx, cy + 1, 18, BADGE_TEXT, alpha=a)
    if crown and holder and not winner:
        draw_crown(c, cx + 82, cy - 30, 0.55, 1.0)
    if crown and winner:
        draw_crown(c, cx + 82, cy - 30, 0.6, 1.0, glow=0.8)
    c.restore()


def draw_chips(c, names, colors, counts, holder=None, winner=None, pops=None):
    """All chips. holder/winner: index or None. After a win pass winner=i (others are dimmed)."""
    for idx, name in enumerate(names):
        won = winner is not None
        draw_chip(c, CHIP_XS[idx % 4], CHIP_YS[idx // 4], name, colors[name], count=counts[idx],
                  holder=(holder == idx) and not won, winner=won and idx == winner,
                  dim=won and idx != winner, pop=(pops[idx] if pops else 0.0))


def pop_scale(age, length, start):
    """Back-out pop: scale `start` -> 1.0 over `length` seconds of video time."""
    x = age / length
    return lerp(start, 1.0, back_out(x)) if x < 1 else 1.0


def draw_intro(c, line1="PICK YOUR COLOR!", line2="THE FIRST ONE OUT WINS THE CROWN", alpha=1.0):
    draw_text(c, line1, W / 2, HEADLINE_Y, 76, PICK_YELLOW, alpha=alpha, maxw=1010)
    draw_text(c, line2, W / 2, STATUS_Y, 33, WHITE, alpha=alpha, spacing=1.0, maxw=1000)


def draw_count(c, number, scale=1.0):
    draw_text(c, str(number), W / 2, HEADLINE_Y, 104, WHITE, scale=scale)


def draw_last_ring(c, tau, scale=1.0, text="LAST RING!"):
    pulse = 0.5 + 0.5 * math.sin(tau * 2 * math.pi * 2.2)
    draw_text(c, text, W / 2, HEADLINE_Y - 2, 92, lerpc(GOLD, (255, 150, 60), 0.3 * pulse), scale=scale, maxw=1000)


def draw_status(c, left_text, name, name_color, tail=" HAS THE CROWN"):
    """Yellow left_text, then the name + tail in the name's colour, centred as one line."""
    s1, s2 = left_text, f"{name}{tail}"
    f1 = text_w(s1, 34, 1.0)
    f2 = text_w(s2, 34, 1.0)
    x0 = W / 2 - (f1 + f2) / 2
    draw_text(c, s1, x0, STATUS_Y, 34, YELLOW, align="left", spacing=1.0)
    draw_text(c, s2, x0 + f1 + 1.0, STATUS_Y, 34, name_color, align="left", spacing=1.0)


def draw_win(c, name, rgb, scale=1.0, alpha=1.0, sub="LIKE & SUBSCRIBE!", sub_alpha=1.0):
    draw_text(c, f"{name} WINS!", W / 2, HEADLINE_Y - 2, 100, rgb, alpha=alpha, scale=scale, maxw=1010, shadow=1.0)
    draw_text(c, sub, W / 2, STATUS_Y, 40, WHITE, alpha=alpha * sub_alpha, spacing=1.5)


def draw_captions(c, big, big_rgb, small, small_rgb, scale=1.0, alpha=1.0):
    draw_text(c, big, W / 2, CAPTION_Y, 46, big_rgb, alpha=alpha, scale=scale, spacing=1.2, maxw=1000)
    draw_text(c, small, W / 2, SMALLCAP_Y, 28, small_rgb, alpha=alpha, spacing=2.0, maxw=1000)


def draw_bar(c, progress):
    """progress 0..1 (yellow fill with glow)."""
    c.drawRoundRect(skia.Rect(BAR_X0, BAR_Y - 8, BAR_X1, BAR_Y + 8), 8, 8,
                    skia.Paint(AntiAlias=True, Color4f=col(BAR_TRACK, 1.0)))
    if progress > 0.002:
        gl = skia.Paint(AntiAlias=True, Color4f=col(YELLOW, 0.5))
        gl.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
        xe = BAR_X0 + (BAR_X1 - BAR_X0) * progress
        c.drawRoundRect(skia.Rect(BAR_X0, BAR_Y - 8, xe, BAR_Y + 8), 8, 8, gl)
        c.drawRoundRect(skia.Rect(BAR_X0, BAR_Y - 8, xe, BAR_Y + 8), 8, 8,
                        skia.Paint(AntiAlias=True, Color4f=col(YELLOW, 1.0)))


def _preview(path):
    """Mid-race state: RED holds the crown and just scored, 7 rings left."""
    from neon_kit import make_background
    surf = skia.Surface(W, 1920)
    c = surf.getCanvas()
    c.drawImage(make_background(title="RING ESCAPE", subtitle="FIRST ONE OUT WINS"), 0, 0)
    counts = [1, 0, 1, 0, 1, 0, 0, 0]
    draw_chips(c, NAMES, BALL_COLORS, counts, holder=0, pops=[0.6, 0, 0, 0, 0, 0, 0, 0])
    draw_count(c, 7)
    draw_status(c, "7 RINGS LEFT  •  ", "RED", BALL_COLORS["RED"])
    draw_captions(c, "RED BREAKS OUT!", BALL_COLORS["RED"], "BREAK A RING = TAKE THE CROWN", SMALLCAP)
    draw_bar(c, 0.3)
    draw_text(c, "(arena goes here)", W / 2, 990, 34, (70, 90, 140))
    surf.makeImageSnapshot().save(path, skia.kPNG)


if __name__ == "__main__":
    _preview(os.path.join(_HERE, "preview.png"))
    print("wrote preview.png")
