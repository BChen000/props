"""roulette-spinner: a BIG sword spins like a roulette needle in the arena centre, slows down
(cubic ease-out), stops on the chosen ball, then flies onto it while every other ball gets
a small sword. Gives the tick times for the sound track and the ball under the needle.
"""
import math
import os
import sys

import cairo

_HERE = os.path.dirname(os.path.abspath(__file__))
for _dep in ("style-kit", "glossy-ball", "sword"):
    sys.path.append(os.path.join(_HERE, "..", _dep))
from kit import GOLD, PI, BALL_COLORS, NAMES, ease_in_out, ease_out, ease_out_back, rgb  # noqa: E402
from glossy_ball import draw_ball  # noqa: E402
from sword import BIG, SMALL, draw_sword  # noqa: E402

# --------------------------------------------------------------------------- settings
CENTER = (540.0, 1010.0)          # arena centre = needle pivot
RING_R = 250.0                    # balls sit on this ring, first ball at the top, clockwise
START_ANGLE = -math.pi / 2 + 0.55  # needle rest angle (between two balls, so it looks fair)
TURNS = 4                         # full turns before the final stop
SPIN_START, SPIN_END = 0.75, 4.55  # video seconds
FLY_START, FLY_END = 4.85, 5.35   # needle flies onto the chosen ball
POP_START, POP_STEP = 5.35, 0.06  # small swords pop onto the others, one by one
GLOW_UNTIL = 6.3                  # chosen ball keeps pulsing until here
BALL_R = 40.0
HUB_INK = (0.1, 0.06, 0.14)
POINTER_GLOW = (255, 255, 255)    # ring + halo on the ball under the needle while spinning
LANDED_GLOW = (255, 214, 80)      # ring + halo on the chosen ball after the stop


class Roulette:
    def __init__(self, chosen, colors, center=CENTER, ring_r=RING_R, start_angle=START_ANGLE,
                 turns=TURNS, spin_start=SPIN_START, spin_end=SPIN_END, fly_start=FLY_START,
                 fly_end=FLY_END, pop_start=POP_START, pop_step=POP_STEP, glow_until=GLOW_UNTIL,
                 ball_r=BALL_R, small_dims=None, big_dims=None, label="100"):
        """chosen: index of the winner of the spin. colors: RGB per ball, in ring order."""
        self.chosen = chosen
        self.colors = colors
        self.n = len(colors)
        self.cx, self.cy = center
        self.ring_r = ring_r
        self.th0 = start_angle
        self.spin_start, self.spin_end = spin_start, spin_end
        self.fly_start, self.fly_end = fly_start, fly_end
        self.pop_start, self.pop_step = pop_start, pop_step
        self.glow_until = glow_until
        self.ball_r = ball_r
        self.small = small_dims or SMALL
        self.big = big_dims or BIG
        self.label = label
        self.a0 = -math.pi / 2
        self.step = 2 * math.pi / self.n
        target = self.ring_angle(chosen)
        self.spin_delta = (target - self.th0) % (2 * math.pi) + 2 * math.pi * turns
        self.ticks = self._ticks()

    # ---- geometry / timing
    def ring_angle(self, i):
        return self.a0 + i * self.step

    def ring_pos(self, i):
        a = self.ring_angle(i)
        return self.cx + self.ring_r * math.cos(a), self.cy + self.ring_r * math.sin(a), a

    def pointer_angle(self, v):
        if v < self.spin_start:
            return self.th0 + 0.12 * math.sin(v * 2 * math.pi * 0.9) * (1 - v / self.spin_start)
        u = (v - self.spin_start) / (self.spin_end - self.spin_start)
        return self.th0 + self.spin_delta * ease_out(u)

    def pointed_ball(self, v):
        a = self.pointer_angle(v)
        return int(round((a - self.a0) / self.step) % self.n)

    def _ticks(self):
        """Video times when the needle passes a gap between two balls (one click each)."""
        ticks = []
        prev = self.pointer_angle(self.spin_start)
        v = self.spin_start
        while v < self.spin_end + 0.01:
            v += 1.0 / 600
            cur = self.pointer_angle(v)
            b0 = math.floor((prev - self.a0 + self.step / 2) / self.step)
            b1 = math.floor((cur - self.a0 + self.step / 2) / self.step)
            if b1 != b0:
                ticks.append(v)
            prev = cur
        return ticks

    # ---- drawing
    def draw(self, ctx, v):
        """Draw balls + needle at video time v. Returns the ball index to highlight (or None)."""
        BR = self.ball_r
        spinning = self.spin_start <= v < self.spin_end
        pointed = self.pointed_ball(v) if v < self.fly_start else None
        landed = v >= self.spin_end
        # small swords pop in
        order = [k for k in range(self.n) if k != self.chosen]
        for n_, k in enumerate(order):
            t0 = self.pop_start + n_ * self.pop_step
            if v >= t0:
                bx, by, a = self.ring_pos(k)
                sc = ease_out_back((v - t0) / 0.28)
                draw_sword(ctx, bx, by, a, BR - 2, False, self.colors[k], scale=sc, dims=self.small)
        # balls
        for k in range(self.n):
            bx, by, a = self.ring_pos(k)
            col = self.colors[k]
            r = BR
            glow = 0.0
            if spinning and k == pointed:
                r = BR * 1.12
                glow = 1.0
            if landed and k == self.chosen and v < self.glow_until:
                pul = 0.5 + 0.5 * math.sin((v - self.spin_end) * 2 * PI * 2.2)
                r = BR * (1.12 + 0.05 * pul) if v < self.fly_end + 0.2 else BR
                glow = 0.65 + 0.35 * pul
            if glow > 0:
                gc = POINTER_GLOW if not landed else LANDED_GLOW
                rg = cairo.RadialGradient(bx, by, r * 0.8, bx, by, r * 2.1)
                rg.add_color_stop_rgba(0, *rgb(gc, 0.55 * glow))
                rg.add_color_stop_rgba(1, *rgb(gc, 0.0))
                ctx.set_source(rg)
                ctx.arc(bx, by, r * 2.1, 0, 2 * PI)
                ctx.fill()
                ctx.arc(bx, by, r + 9, 0, 2 * PI)
                ctx.set_source_rgba(*rgb(gc, 0.9 * glow))
                ctx.set_line_width(4)
                ctx.stroke()
            draw_ball(ctx, bx, by, r, col, self.label, label_size=int(30 * r / BR))
        # needle / flying big sword
        ccol = self.colors[self.chosen]
        g = self.big["grip"]
        CX, CY = self.cx, self.cy
        if v < self.fly_start:
            th = self.pointer_angle(v)
            if spinning:  # motion-blur ghosts
                for k in range(6, 0, -1):
                    thk = self.pointer_angle(v - k * 0.011)
                    if abs(th - thk) > 0.02:
                        draw_sword(ctx, CX, CY, thk, -g - 6, True, ccol, alpha=0.10 * (7 - k) / 6,
                                   dims=self.big)
            draw_sword(ctx, CX, CY, th, -g - 6, True, ccol, dims=self.big)
            ctx.arc(CX, CY, 11, 0, 2 * PI)
            ctx.set_source_rgba(*rgb(GOLD))
            ctx.fill_preserve()
            ctx.set_source_rgba(HUB_INK[0], HUB_INK[1], HUB_INK[2], 1)
            ctx.set_line_width(3)
            ctx.stroke()
        else:
            u = ease_in_out((v - self.fly_start) / (self.fly_end - self.fly_start))
            bx, by, a = self.ring_pos(self.chosen)
            px = CX + (bx - CX) * u
            py = CY + (by - CY) * u
            th = a + (PI + 2 * PI) * u
            r_off = (-g - 6) + (BR - 2 - (-g - 6)) * u
            if v < self.fly_end:
                for k in range(4, 0, -1):
                    uk = ease_in_out((v - k * 0.02 - self.fly_start) / (self.fly_end - self.fly_start))
                    draw_sword(ctx, CX + (bx - CX) * uk, CY + (by - CY) * uk, a + 3 * PI * uk,
                               (-g - 6) + (BR - 2 + g + 6) * uk, True, ccol, alpha=0.12 * (5 - k) / 4,
                               dims=self.big)
            draw_sword(ctx, px, py, th, r_off, True, ccol, dims=self.big)
            # redraw chosen ball on top of its sword hilt
            draw_ball(ctx, bx, by, BR, ccol, self.label, shadow=False)
            # attach flash
            age = v - self.fly_end
            if 0 <= age < 0.45:
                rr = BR + 160 * ease_out(age / 0.45)
                ctx.arc(bx, by, rr, 0, 2 * PI)
                ctx.set_source_rgba(1, 0.86, 0.4, 0.8 * (1 - age / 0.45))
                ctx.set_line_width(8 * (1 - age / 0.45) + 1)
                ctx.stroke()
                ctx.arc(bx, by, BR * 1.6, 0, 2 * PI)
                ctx.set_source_rgba(1, 1, 1, 0.5 * (1 - age / 0.2) if age < 0.2 else 0)
                ctx.fill()
        return pointed if (spinning or (v >= self.spin_end and v < self.fly_start)) else None


if __name__ == "__main__":
    sys.path.append(os.path.join(_HERE, "..", "arena-board"))
    import arena_board as board
    rl = Roulette(chosen=0, colors=[BALL_COLORS[n] for n in NAMES])
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1080, 1920)
    ctx = cairo.Context(surf)
    ctx.set_source_surface(board.make_background("SWORD ROULETTE", "One random ball gets the BIG sword!"), 0, 0)
    ctx.paint()
    ctx.set_source_surface(board.make_floor(), 0, 0)
    ctx.paint()
    board.draw_rim(ctx, board.RIM_CALM)
    v = 2.2
    rl.draw(ctx, v)
    board.draw_status(ctx, "6 LEFT", "SPINNING...", (255, 214, 80))
    board.draw_message(ctx, "plain", ("Comment who you think will win!", (255, 255, 255)), v, 2, v, first=True)
    surf.write_to_png(os.path.join(_HERE, "preview.png"))
    print("wrote preview.png;", len(rl.ticks), "ticks")
