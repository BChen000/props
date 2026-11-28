"""blob-style: the minimal white-blob look, drawn with skia-python at 1080x1920.

  blob(c, x, y, s, ...)      the character: a soft white gumdrop with two black eyes; (x, y) is where it sits
  shadow(c, x, y, s, t, ...) the inner voice: a wobbling near-black blob with a red rim and red slit eyes
  bedroom / desk_lamp / book / calendar / dawn  the sets of the demo
  whisper / title_text       the on-screen text: italic serif whispers, letter-spaced bold titles
  grain(c)                   film grain, one of GRAIN_FRAMES noise plates per frame

Drawing helpers (P, oval, poly, text, glow, ease, ...) come from ../../kids-songs/storytime-kit.
"""
import math
import os
import sys

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kids-songs', 'storytime-kit'))
sys.path.insert(0, HERE)
from storytime_kit import (W, H, P, R, rect, rrect, circ, oval, line, path, poly, grect, glow, text, tw, ease, eout,  # noqa: E402
                           ramp, clamp, mix, lgrad, rgrad)
from settings import COLORS as K, GRAIN_ALPHA, GRAIN_FRAMES  # noqa: E402

BLOB_RX, BLOB_RY = 120.0, 135.0             # half-width and half-height at s = 1 (about 250 px tall)


def blob_pts(x, y, rx, ry, n=2.6, wob=0.0, t=0.0, seed=0.0, k=96):
    """Outline of a gumdrop sitting on (x, y): a superellipse, narrower on top and flattened underneath."""
    cy = y - ry * 0.86
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k
        ca, sa = math.cos(a), math.sin(a)
        px = rx * math.copysign(abs(ca) ** (2 / n), ca)
        py = ry * math.copysign(abs(sa) ** (2 / n), sa)
        if py < 0:
            px *= 1 - 0.12 * (-py / ry)
        else:
            py *= 0.86
        r = 1.0
        if wob:
            r += wob * (0.5 * math.sin(3 * a + 2.1 * t + seed) + 0.3 * math.sin(5 * a - 3.3 * t + 2 * seed)
                        + 0.2 * math.sin(9 * a + 5.1 * t))
        pts.append((x + px * r, cy + py * r))
    return pts


def blob(c, x, y, s=1.0, squash=1.0, expr='open', look=(0.0, 0.0), blink=0.0, legs=None, rot=0.0, shade=True,
         ground_shadow=True, brows=0.0):
    """The character. squash < 1 flattens it (keeping its volume); expr: open, closed, tired; look: eye offset (-1..1);
    blink 0..1; legs: None, or a run phase in radians for two stubby legs; rot: degrees about (x, y); brows 0..1."""
    rx = BLOB_RX * s / math.sqrt(max(squash, 0.3))
    ry = BLOB_RY * s * squash
    c.save()
    if rot:
        c.rotate(rot, x, y)
    if ground_shadow:
        oval(c, x, y + 4 * s, rx * 0.95, 14 * s, '#000000', 0.55, blur=10 * s)
    if legs is not None:
        for side, ph in ((-1, legs), (1, legs + math.pi)):
            a = math.radians(38 * math.sin(ph))
            hx, hy = x + side * rx * 0.32, y - 14 * s
            ln = 44 * s
            line(c, hx, hy, hx + ln * math.sin(a), hy + ln * math.cos(a) * 0.9, K['blob_bot'], w=20 * s)
    pts = blob_pts(x, y, rx, ry)
    sh = lgrad(x, y - 2 * ry, x, y, [K['blob_top'], K['blob_top'], K['blob_bot']], [0, 0.45, 1]) if shade else None
    c.drawPath(path(pts), P(K['blob_top'], shader=sh))
    ex, ey = 0.30 * rx, y - ry * 0.86 - 0.42 * ry
    lx, ly = look[0] * 0.10 * rx, look[1] * 0.08 * ry
    for side in (-1, 1):
        cx, cy = x + side * ex + lx, ey + ly
        erx, ery = 0.085 * rx * math.sqrt(squash), 0.13 * ry
        if expr == 'closed' or blink >= 0.95:
            p = skia.Path()
            p.moveTo(cx - erx * 1.3, cy)
            p.quadTo(cx, cy + ery * 0.55, cx + erx * 1.3, cy)
            c.drawPath(p, P(K['eye'], sw=max(3.0, 5 * s)))
        else:
            k_ = 1 - blink
            if expr == 'tired':
                k_ *= 0.55
            oval(c, cx, cy + ery * (1 - k_) * 0.5, erx, ery * k_, K['eye'])
            if expr == 'tired':
                line(c, cx - erx * 1.4, cy - ery * 0.1, cx + erx * 1.4, cy - ery * 0.1, K['eye'], w=max(3.0, 4 * s))
        if brows > 0:
            bx_in, bx_out = cx - side * erx * 1.5, cx + side * erx * 1.3      # inner end low, outer end high: determined
            by_in, by_out = cy - ery * 1.3, cy - ery * 1.75 - 6 * s * brows
            line(c, bx_in, by_in, bx_out, by_out, K['eye'], w=max(3.0, 6 * s), a=brows)
    c.restore()


def shadow(c, x, y, s, t, grow=1.0, lean=0.0, eyes=1.0, alpha=1.0, dissolve=0.0, seed=1.3):
    """The inner voice: (x, y) is where its base would sit (usually hidden behind furniture)."""
    rx, ry = 150 * s * grow, 230 * s * grow
    a = alpha * (1 - ease(dissolve * 1.6))
    c.save()
    c.rotate(lean, x, y)
    if a > 0:
        pts = blob_pts(x, y, rx, ry, n=2.2, wob=0.05, t=t, seed=seed)
        pp = path(pts)
        c.drawPath(pp, P(K['shadow_rim'], 0.45 * a, sw=26 * s, blur=26 * s))
        c.drawPath(pp, P(K['shadow'], 0.98 * a))
        c.drawPath(pp, P(K['shadow_rim'], 0.85 * a, sw=3.5 * s))
        ey = y - ry * 0.86 - 0.42 * ry
        for side in (-1, 1):
            ex = x + side * rx * 0.30
            p = path([(ex - side * 30 * s, ey - 10 * s), (ex + side * 26 * s, ey + 6 * s), (ex + side * 22 * s, ey + 16 * s),
                      (ex - side * 30 * s, ey + 2 * s)])
            c.drawPath(p, P(K['shadow_eye'], 0.6 * a * eyes, blur=14 * s))
            c.drawPath(p, P(K['shadow_eye'], a * eyes))
    if dissolve > 0:
        rng = np.random.default_rng(11)
        for i in range(140):
            u, v = rng.random(), rng.random()
            px = x + (u - 0.5) * 2 * rx * 0.9
            py = y - v * 1.8 * ry
            d = clamp(dissolve * 1.3 - rng.random() * 0.3)
            if d <= 0 or d >= 1:
                continue
            px += (rng.random() - 0.5) * 240 * s * d
            py -= (180 + rng.random() * 380) * s * d
            r = (6 + rng.random() * 16) * s * (1 - d * 0.6)
            circ(c, px, py, r, K['shadow'], 0.9 * (1 - d))
            circ(c, px, py, r, K['shadow_rim'], 0.5 * (1 - d), sw=2)
    c.restore()


# ---------------------------------------------------------------- sets
def bedroom(c, t, alarm=0.0, moon=1.0):
    """Wide bedroom: wall, window and moonlight on the right, floor, nightstand with a 5:00 alarm clock (blinks while
    alarm > 0). Draw the shadow next, then bed(), pillow(), the blob and bed_front()."""
    rect(c, -500, -500, W + 1000, H + 1000, K['wall'])
    rect(c, -500, 1480, W + 1000, H, K['floor'])
    line(c, -500, 1480, W + 500, 1480, '#16161B', w=3)
    wx, wy, ww, wh = 610, 380, 300, 400
    rect(c, wx - 14, wy - 14, ww + 28, wh + 28, K['window'])
    grect(c, wx, wy, ww, wh, [mix(K['moon'], K['bg'], 0.55), mix(K['moon'], K['bg'], 0.8)])
    line(c, wx + ww / 2, wy, wx + ww / 2, wy + wh, K['window'], w=12)
    line(c, wx, wy + wh / 2, wx + ww, wy + wh / 2, K['window'], w=12)
    beam = path([(wx, wy + 40), (wx + ww, wy + 60), (wx + ww - 40, 1330), (wx - 380, 1300)])
    c.drawPath(beam, P('#ffffff', shader=lgrad(wx, wy, wx - 200, 1300, [(K['moon'], 0.12 * moon), (K['moon'], 0.0)]), blur=18))
    rect(c, 40, 1205, 170, 275, K['stand'])
    rect(c, 40, 1205, 170, 14, '#1C1C22')
    rrect(c, 62, 1120, 128, 86, 14, K['clock'])
    blink_on = (alarm <= 0) or (math.sin(2 * math.pi * 2.0 * t) > -0.2)
    if blink_on:
        glow(c, 126, 1163, 120, K['digits'], 0.22 + 0.18 * alarm)
        text(c, '5:00', 126, 1186, 58, K['digits'], 1.0, tf='mono', blur=6)
        text(c, '5:00', 126, 1186, 58, K['digits'], 1.0, tf='mono')


def bed(c):
    rect(c, 222, 1060, 34, 420, K['bed'])
    rrect(c, 232, 1290, 760, 120, 18, K['bed'])
    rrect(c, 240, 1360, 740, 120, 10, '#141419')


def bed_front(c, t, breathe=0.0):
    """Pillow is drawn with the blob; this draws the blanket over it (with a breathing rise)."""
    b = 6 * math.sin(2 * math.pi * 0.35 * t) * breathe
    p = skia.Path()
    p.moveTo(445, 1300)
    p.cubicTo(500, 1226 - b, 660, 1216 - b, 770, 1236 - b * 0.6)
    p.cubicTo(860, 1250, 950, 1262, 985, 1300)
    p.lineTo(985, 1395)
    p.lineTo(437, 1395)
    p.close()
    c.drawPath(p, P(K['blanket']))
    c.drawPath(p, P('#ffffff', shader=lgrad(0, 1220, 0, 1395, [(K['blanket_hi'], 0.9), (K['blanket'], 0.0)])))
    line(c, 450, 1300, 985, 1300, K['blanket_hi'], w=3, a=0.5)


def pillow(c):
    rrect(c, 250, 1225, 190, 88, 40, K['pillow'])
    rrect(c, 258, 1232, 174, 30, 20, '#465060', 0.7)


def dawn(c, t, horizon=1180, sun_y=1185, sun_r=120, sun_x=720, warm=1.0):
    grect(c, -500, -500, W + 1000, horizon + 500, [K['dawn_top'], K['dawn_top'], K['dawn_mid'], mix(K['dawn_low'], K['dawn_mid'], 1 - warm)],
          [0, 0.45, 0.82, 1])
    glow(c, sun_x, sun_y, sun_r * 4.2, K['sun'], 0.35 * warm)
    c.save()
    c.clipRect(R(-500, -500, W + 1000, horizon + 500))
    circ(c, sun_x, sun_y, sun_r, K['sun'])
    c.restore()
    rect(c, -500, horizon, W + 1000, H + 600, K['ground'])


def hills(c, offset, horizon=1180, col_='#130E0F'):
    pts = [(-500, horizon + 2)]
    for i in range(0, 41):
        xx = -500 + i * 60
        pts.append((xx, horizon - 40 - 34 * math.sin((xx + offset) * 0.006) - 18 * math.sin((xx + offset) * 0.017 + 1)))
    pts.append((W + 500, horizon + 2))
    poly(c, pts, col_)


def desk_lamp(c, on=1.0):
    rect(c, 90, 1330, 900, 34, K['desk'])
    rect(c, 110, 1364, 860, 300, '#121216')
    c.drawPath(path([(735, 860), (900, 860), (1000, 1330), (560, 1330)]),
               P('#ffffff', shader=lgrad(0, 860, 0, 1330, [(K['lamp'], 0.20 * on), (K['lamp'], 0.05 * on)]), blur=16))
    glow(c, 780, 1330, 300, K['lamp'], 0.22 * on)
    rect(c, 860, 1300, 90, 30, '#1E1E24')
    line(c, 905, 1300, 930, 1040, '#26262D', w=12)
    line(c, 930, 1040, 860, 900, '#26262D', w=12)
    poly(c, [(770, 830), (890, 860), (870, 905), (742, 878)], '#2A2A32')
    glow(c, 812, 885, 60, K['lamp'], 0.8 * on)


def book(c, x, y, t, flip_every=0.55):
    """An open book lying on the desk at (x, y) = spine bottom; a page turns every flip_every seconds."""
    lp = [(x, y), (x - 210, y + 8), (x - 196, y - 50), (x, y - 58)]
    rp = [(x, y), (x + 210, y + 8), (x + 196, y - 50), (x, y - 58)]
    poly(c, lp, K['page'])
    poly(c, rp, K['page'])
    for i in range(4):
        f = 0.25 + 0.17 * i
        line(c, x - 180, y - 44 + 46 * f, x - 22, y - 50 + 46 * f, K['page_line'], w=3)
        line(c, x + 22, y - 50 + 46 * f, x + 180, y - 44 + 46 * f, K['page_line'], w=3)
    ph = (t % flip_every) / flip_every
    if ph < 0.6:
        u = ease(ph / 0.6)
        tipx = x + 205 * math.cos(math.pi * u)
        lift = 60 * math.sin(math.pi * u)
        poly(c, [(x, y), (tipx, y + 8 - lift * 0.3), (tipx - 10 * math.cos(math.pi * u), y - 50 - lift), (x, y - 58)],
             mix(K['page'], '#ffffff', 0.4))
    line(c, x, y, x, y - 58, '#8E897F', w=3)


def calendar(c, x, y, w, h, n_x, t, draw_t):
    """A month grid; n_x squares crossed, the last one being drawn for draw_t (0..1)."""
    rect(c, x + 10, y + 14, w, h, '#000000', 0.5, blur=18)
    rect(c, x, y, w, h, K['cal_paper'])
    rect(c, x, y, w, 90, K['cal_bar'])
    for i in range(6):
        rx = x + 70 + i * (w - 140) / 5
        rrect(c, rx - 8, y - 26, 16, 52, 8, '#2A2A30')
    cols, rows = 7, 5
    gx, gy, cw, ch = x + 30, y + 120, (w - 60) / cols, (h - 150) / rows
    for r in range(rows + 1):
        line(c, gx, gy + r * ch, gx + cols * cw, gy + r * ch, K['cal_grid'], w=3)
    for k in range(cols + 1):
        line(c, gx + k * cw, gy, gx + k * cw, gy + rows * ch, K['cal_grid'], w=3)
    for i in range(min(n_x, cols * rows)):
        cx, cy = gx + (i % cols) * cw + cw / 2, gy + (i // cols) * ch + ch / 2
        d = 1.0 if i < n_x - 1 else draw_t
        a1, a2 = clamp(d * 2), clamp(d * 2 - 1)
        hx, hy = cw * 0.32, ch * 0.30
        if a1 > 0:
            line(c, cx - hx, cy - hy, cx - hx + 2 * hx * a1, cy - hy + 2 * hy * a1, K['cal_x'], w=11)
        if a2 > 0:
            line(c, cx + hx, cy - hy, cx + hx - 2 * hx * a2, cy - hy + 2 * hy * a2, K['cal_x'], w=11)


# ---------------------------------------------------------------- text
def whisper(c, s, x, y, age, out=1.0, size=58, cl=None):
    """Italic serif whisper: fades in over 0.25 s and drifts up; out (1 -> 0) fades it away."""
    a = clamp(age / 0.25) * clamp(out)
    if a <= 0:
        return
    yy = y - 14 * eout(age / 1.4)
    text(c, s, x, yy, size, K['shadow_rim'], 0.45 * a, tf='serifi', blur=10)
    text(c, s, x, yy, size, cl or K['text_red'], a, tf='serifi')


def title_text(c, s, x, y, size, age, cl=None, spacing=0.18, tf='bold', a=1.0):
    """Letter-spaced title that settles from 1.08x to 1x over 0.4 s."""
    if age < 0:
        return
    k = 1.08 - 0.08 * eout(age / 0.4)
    al = clamp(age / 0.12) * a
    sp = size * spacing
    widths = [tw(ch, size, tf) for ch in s]
    total = sum(widths) + sp * (len(s) - 1)
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    xx = -total / 2
    for ch, wd in zip(s, widths):
        text(c, ch, xx, 0, size, cl or K['text'], al, tf=tf, align='left')
        xx += wd + sp
    c.restore()


# ---------------------------------------------------------------- grain
_GRAIN, _FRAME = [], [0]


def grain(c, alpha=GRAIN_ALPHA):
    if not _GRAIN:
        rng = np.random.default_rng(3)
        for _ in range(GRAIN_FRAMES):
            g = rng.normal(128, 46, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
            rgba = np.dstack([g, g, g, np.full_like(g, 255)])
            _GRAIN.append(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType))
    p = skia.Paint()
    p.setAlphaf(alpha)
    c.drawImageRect(_GRAIN[_FRAME[0] % len(_GRAIN)], R(0, 0, W, H), skia.SamplingOptions(), p)
    _FRAME[0] += 1
