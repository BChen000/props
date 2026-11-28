"""cast_props: hand props and set props for the five cartoon looks, drawn with skia-python in each look's outline and
shading (thin edges for whatif, thick brown for palace...). Every prop is a function
  name(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0, **options)
(x, y) is where a hand grips it (hand props) or the middle of its base on the ground (door, barrel, palm, block_sled,
candle). rot turns it about (x, y), in degrees clockwise; t (seconds) drives flames, steam, bobbing and bubbles.
KITS lists six props per look, in the order the look reels show them; HAND marks the ones a hand can hold.
To put one in a hand: cast.person(..., hold=lambda c, j: goblet(c, *j['ra'][1], s, 'palace')).
"""
import math

import skia

from settings import LOOKS
from storytime_kit import P, circ, oval, line, rrect, lgrad, rgrad, clamp
from cast import _fill, _stroke, _rr, _path, lt, dk

OW = dict(whatif=2.5, palace=5.0, castle=4.0, desert=3.5, pill=5.5)


def _st(look, s):
    return LOOKS[look]['ink'], OW[look] * s


def _flame(c, x, y, h, t, seed=0.0, a=1.0):
    """A flickering flame with its base at (x, y), h tall."""
    k = math.sin(t * 17 + seed) * 0.08 + math.sin(t * 29 + seed * 2) * 0.05
    for sc_, cl in ((1.0, '#FF7A1A'), (0.72, '#FFB31F'), (0.45, '#FFF3B0')):
        hh, ww = h * sc_ * (1 + k), h * 0.42 * sc_
        q = skia.Path()
        q.moveTo(x, y - hh)
        q.cubicTo(x + ww * (0.9 + k), y - hh * 0.45, x + ww, y, x, y)
        q.cubicTo(x - ww, y, x - ww * (0.9 - k), y - hh * 0.45, x, y - hh)
        c.drawPath(q, P(cl, a))
    circ(c, x, y - h * 0.4, h * 1.6, '#FFB040', 0.16 * a, blur=h * 0.6)


def _rot(c, x, y, rot):
    c.save()
    if rot:
        c.rotate(rot, x, y)


# ---------------------------------------------------------------- what if
def dumbbell(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    _stroke(c, [(x - 62 * s, y), (x + 62 * s, y)], 12 * s, '#B8BEC8', ink, ow)
    for side in (-1, 1):
        for k, (w, h) in enumerate(((22, 78), (16, 58))):
            px = x + side * (44 + 20 * k) * s - w * s / 2
            q = _rr(px, y - h * s / 2, w * s, h * s, 6 * s)
            _fill(c, q, '#3A3F4A', ink, ow, shader=lgrad(px, 0, px + w * s, 0, ['#5B6270', '#2A2E36']))
    c.restore()


def phone(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    w, h = 56 * s, 104 * s
    _fill(c, _rr(x - w / 2, y - h / 2, w, h, 11 * s), '#17181D', ink, ow)
    sx, sy, sw, sh = x - w / 2 + 5 * s, y - h / 2 + 9 * s, w - 10 * s, h - 18 * s
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(sx, sy, sw, sh), 6 * s, 6 * s),
                P('#ffffff', shader=lgrad(sx, sy, sx + sw, sy + sh, ['#6C8CFF', '#B45CFF', '#FF7EB3'])))
    for k in range(3):
        rrect(c, sx + 6 * s, sy + (10 + 22 * k) * s + (t * 30 * s) % (22 * s), sw - 12 * s, 14 * s, 4 * s, '#FFFFFF', 0.55)
    rrect(c, x - 10 * s, y - h / 2 + 3 * s, 20 * s, 4 * s, 2 * s, '#000000')
    c.restore()


def backpack(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0, col='#E0533D'):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    q = skia.Path()
    q.addArc(skia.Rect.MakeXYWH(x - 22 * s, y - 14 * s, 44 * s, 30 * s), 180, 180)
    c.drawPath(q, P(ink, sw=8 * s + 2 * ow))
    c.drawPath(q, P(dk(col, 0.3), sw=8 * s))
    w, h = 112 * s, 136 * s
    _fill(c, _rr(x - w / 2, y, w, h, 30 * s), col, ink, ow, shader=lgrad(x - w / 2, 0, x + w / 2, 0, [lt(col, 0.2), col, dk(col, 0.2)]))
    _fill(c, _rr(x - w / 2 + 6 * s, y + 4 * s, w - 12 * s, 44 * s, 20 * s), dk(col, 0.12), ink, ow * 0.8)
    _fill(c, _rr(x - 34 * s, y + 70 * s, 68 * s, 50 * s, 12 * s), dk(col, 0.1), ink, ow * 0.8)
    line(c, x - 26 * s, y + 80 * s, x + 26 * s, y + 80 * s, '#F2D35B', w=4 * s)
    c.restore()


def trophy(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    gold = lgrad(x - 50 * s, 0, x + 50 * s, 0, ['#FFE9A0', '#F2C14E', '#C08A24'])
    for side in (-1, 1):
        q = skia.Path()
        q.addArc(skia.Rect.MakeXYWH(x + side * 40 * s - 22 * s, y - 92 * s, 44 * s, 46 * s), 90 - side * 90, 180 * side)
        c.drawPath(q, P(ink, sw=9 * s + 2 * ow))
        c.drawPath(q, P('#E8B23E', sw=9 * s))
    q = skia.Path()
    q.moveTo(x - 50 * s, y - 104 * s)
    q.lineTo(x + 50 * s, y - 104 * s)
    q.cubicTo(x + 50 * s, y - 40 * s, x + 20 * s, y - 22 * s, x, y - 20 * s)
    q.cubicTo(x - 20 * s, y - 22 * s, x - 50 * s, y - 40 * s, x - 50 * s, y - 104 * s)
    q.close()
    _fill(c, q, '#F2C14E', ink, ow, shader=gold)
    _fill(c, _rr(x - 8 * s, y - 22 * s, 16 * s, 30 * s, 3 * s), '#E0A93A', ink, ow)
    _fill(c, _rr(x - 40 * s, y + 8 * s, 80 * s, 30 * s, 6 * s), '#5A3A26', ink, ow)
    star = [(x + math.cos(math.radians(-90 + 36 * k)) * (16 if k % 2 == 0 else 7) * s,
             y - 70 * s + math.sin(math.radians(-90 + 36 * k)) * (16 if k % 2 == 0 else 7) * s) for k in range(10)]
    c.drawPath(_path(star, True), P('#FFF6D0'))
    c.restore()


def basketball(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    r = 42 * s
    q = skia.Path()
    q.addCircle(x, y, r)
    _fill(c, q, '#E8792E', ink, ow, shader=rgrad(x - 0.35 * r, y - 0.35 * r, 1.4 * r, ['#FFB070', '#E8792E', '#B4521C']))
    c.save()
    c.clipPath(q, skia.ClipOp.kIntersect, True)
    c.rotate(rot + t * 160, x, y)
    sw = 3.5 * s
    line(c, x - r, y, x + r, y, '#2A1A10', w=sw)
    line(c, x, y - r, x, y + r, '#2A1A10', w=sw)
    for side in (-1, 1):
        a = skia.Path()
        a.addArc(skia.Rect.MakeXYWH(x + side * 0.55 * r - 0.9 * r, y - 1.1 * r, 1.8 * r, 2.2 * r), 90 + side * 90 - 50, 100)
        c.drawPath(a, P('#2A1A10', sw=sw))
    c.restore()


def water_bottle(c, x, y, s=1.0, look='whatif', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    w, h = 40 * s, 104 * s
    _fill(c, _rr(x - w / 2, y - h / 2, w, h, 12 * s), '#8FD3F5', ink, ow,
          shader=lgrad(x - w / 2, 0, x + w / 2, 0, ['#D6F1FF', '#8FD3F5', '#4FA7D6']))
    c.drawRect(skia.Rect.MakeXYWH(x - w / 2 + 2, y - 6 * s, w - 4, 30 * s), P('#2BB5A4'))
    _fill(c, _rr(x - 14 * s, y - h / 2 - 16 * s, 28 * s, 20 * s, 5 * s), '#2B2F38', ink, ow)
    line(c, x - 9 * s, y - h / 2 + 12 * s, x - 9 * s, y + 24 * s, '#FFFFFF', w=4 * s, a=0.6)
    c.restore()


# ---------------------------------------------------------------- palace
def goblet(c, x, y, s=1.0, look='palace', rot=0.0, t=0.0, wine=True):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    gold = lgrad(x - 40 * s, 0, x + 40 * s, 0, ['#FFE9A0', '#E8B23E', '#B07A1E'])
    q = skia.Path()
    q.moveTo(x - 40 * s, y - 86 * s)
    q.cubicTo(x - 42 * s, y - 40 * s, x - 18 * s, y - 24 * s, x, y - 22 * s)
    q.cubicTo(x + 18 * s, y - 24 * s, x + 42 * s, y - 40 * s, x + 40 * s, y - 86 * s)
    q.close()
    _fill(c, q, '#E8B23E', ink, ow, shader=gold)
    if wine:
        oval(c, x, y - 86 * s, 38 * s, 9 * s, '#7A1424')
    oval(c, x, y - 86 * s, 40 * s, 10 * s, ink, sw=ow * 1.4)
    _stroke(c, [(x, y - 24 * s), (x, y + 22 * s)], 10 * s, '#E0A93A', ink, ow)
    _fill(c, _path([(x - 30 * s, y + 30 * s), (x + 30 * s, y + 30 * s), (x + 12 * s, y + 18 * s), (x - 12 * s, y + 18 * s)], True),
          '#E8B23E', ink, ow, shader=gold)
    for k, gc in enumerate(('#D8344A', '#2F8F6A', '#3C6BD8')):
        circ(c, x + (k - 1) * 20 * s, y - 52 * s, 5.5 * s, gc)
    c.restore()


def sword(c, x, y, s=1.0, look='palace', rot=0.0, t=0.0):
    """Held at the grip (x, y), blade pointing up before rot."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    q = skia.Path()
    q.moveTo(x - 9 * s, y - 26 * s)
    q.lineTo(x - 11 * s, y - 190 * s)
    q.quadTo(x - 6 * s, y - 236 * s, x + 14 * s, y - 262 * s)
    q.quadTo(x + 12 * s, y - 200 * s, x + 9 * s, y - 26 * s)
    q.close()
    _fill(c, q, '#D7DDE6', ink, ow, shader=lgrad(x - 10 * s, 0, x + 10 * s, 0, ['#FFFFFF', '#C4CCD8', '#8E98A8']))
    line(c, x, y - 40 * s, x - 2 * s, y - 200 * s, '#FFFFFF', w=2.5 * s, a=0.7)
    _stroke(c, [(x - 40 * s, y - 24 * s), (x + 40 * s, y - 24 * s)], 12 * s, '#E8B23E', ink, ow)
    _stroke(c, [(x, y - 18 * s), (x, y + 30 * s)], 15 * s, '#6B3A22', ink, ow)
    for k in range(3):
        line(c, x - 7 * s, y - 8 * s + k * 13 * s, x + 7 * s, y - 2 * s + k * 13 * s, '#3E2213', w=2.5 * s)
    circ(c, x, y + 38 * s, 10 * s + ow, ink)
    circ(c, x, y + 38 * s, 10 * s, '#E8B23E')
    c.restore()


def scroll(c, x, y, s=1.0, look='palace', rot=0.0, t=0.0, open_=1.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    h = (40 + 130 * clamp(open_)) * s
    w = 120 * s
    _fill(c, skia.Path().addRect(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h)), '#F3E2B8', ink, ow,
          shader=lgrad(x - w / 2, 0, x + w / 2, 0, ['#FFF2D2', '#F0DCAA', '#DDC28A']))
    for k in range(int(h / s / 22) - 1):
        yy = y - h / 2 + (20 + 20 * k) * s
        line(c, x - 40 * s, yy, x + (40 - 18 * (k % 2)) * s, yy, '#8A6B48', w=3 * s, a=0.6)
    for side in (-1, 1):
        _fill(c, _rr(x - w / 2 - 10 * s, y + side * h / 2 - 12 * s, w + 20 * s, 24 * s, 12 * s), '#E7CF98', ink, ow)
        for e in (-1, 1):
            circ(c, x + e * (w / 2 + 14 * s), y + side * h / 2, 8 * s + ow, ink)
            circ(c, x + e * (w / 2 + 14 * s), y + side * h / 2, 8 * s, '#8A4B2A')
    if open_ > 0.6:
        circ(c, x + 30 * s, y + h / 2 - 34 * s, 15 * s + ow * 0.6, ink)
        circ(c, x + 30 * s, y + h / 2 - 34 * s, 15 * s, '#B8262E')
    c.restore()


def torch(c, x, y, s=1.0, look='palace', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    _stroke(c, [(x, y + 60 * s), (x, y - 70 * s)], 16 * s, '#7A4A2A', ink, ow)
    q = _path([(x - 30 * s, y - 96 * s), (x + 30 * s, y - 96 * s), (x + 16 * s, y - 64 * s), (x - 16 * s, y - 64 * s)], True)
    _fill(c, q, '#5C5F68', ink, ow, shader=lgrad(x - 30 * s, 0, x + 30 * s, 0, ['#9AA0AA', '#5C5F68', '#3A3D44']))
    c.restore()
    hx, hy = x + math.sin(math.radians(rot)) * 96 * s, y - math.cos(math.radians(rot)) * 96 * s
    _flame(c, hx, hy + 6 * s, 82 * s, t, x * 0.01)


def potion(c, x, y, s=1.0, look='palace', rot=0.0, t=0.0, col='#3BFF6A'):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    circ(c, x, y + 52 * s, 80 * s, col, 0.18, blur=30 * s)
    _fill(c, _rr(x - 12 * s, y - 20 * s, 24 * s, 40 * s, 5 * s), '#CFE9F5', ink, ow)
    _fill(c, _rr(x - 14 * s, y - 34 * s, 28 * s, 18 * s, 5 * s), '#9A6A3F', ink, ow)
    q = skia.Path()
    q.addCircle(x, y + 52 * s, 42 * s)
    _fill(c, q, '#CFE9F5', ink, ow)
    c.save()
    c.clipPath(q, skia.ClipOp.kIntersect, True)
    lv = y + 34 * s + 4 * s * math.sin(t * 3)
    c.drawRect(skia.Rect.MakeXYWH(x - 50 * s, lv, 100 * s, 70 * s), P(col, shader=lgrad(0, lv, 0, lv + 60 * s, [lt(col, 0.3), dk(col, 0.35)])))
    for k in range(5):
        ph = (t * (0.6 + 0.13 * k) + k * 0.23) % 1.0
        circ(c, x + (k - 2) * 14 * s, y + 90 * s - ph * 50 * s, (3 + k % 3) * s, '#FFFFFF', 0.7 * (1 - ph))
    c.restore()
    circ(c, x - 16 * s, y + 38 * s, 7 * s, '#FFFFFF', 0.8)
    c.restore()


def coin_pouch(c, x, y, s=1.0, look='palace', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    q = skia.Path()
    q.moveTo(x - 14 * s, y + 8 * s)
    q.cubicTo(x - 70 * s, y + 30 * s, x - 70 * s, y + 120 * s, x, y + 122 * s)
    q.cubicTo(x + 70 * s, y + 120 * s, x + 70 * s, y + 30 * s, x + 14 * s, y + 8 * s)
    q.close()
    _fill(c, q, '#9A6A3F', ink, ow, shader=rgrad(x - 20 * s, y + 50 * s, 90 * s, ['#C08A58', '#9A6A3F', '#6E4626']))
    q = _path([(x - 14 * s, y + 8 * s), (x - 30 * s, y - 16 * s), (x + 30 * s, y - 16 * s), (x + 14 * s, y + 8 * s)], True)
    _fill(c, q, '#B07A4A', ink, ow)
    _stroke(c, [(x - 18 * s, y + 6 * s), (x + 18 * s, y + 6 * s)], 6 * s, '#E2C46A', ink, ow * 0.6)
    for k, (dx, dy) in enumerate(((-60, 120), (-30, 128), (40, 124), (70, 116))):
        oval(c, x + dx * s, y + dy * s, 16 * s + ow, 7 * s + ow, ink)
        oval(c, x + dx * s, y + dy * s, 16 * s, 7 * s, '#F2C14E')
    c.restore()


# ---------------------------------------------------------------- castle
def door(c, x, y, s=1.0, look='castle', rot=0.0, t=0.0, open_=0.0, glow_col='#FFE9B0'):
    """A tall wooden door standing on (x, y); open_ 0..1 swings it, with light behind."""
    ink, ow = _st(look, s)
    w, h = 220 * s, 380 * s
    frame = skia.Path()
    frame.moveTo(x - w / 2 - 18 * s, y)
    frame.lineTo(x - w / 2 - 18 * s, y - h + w / 2)
    frame.arcTo(skia.Rect.MakeXYWH(x - w / 2 - 18 * s, y - h - 18 * s, w + 36 * s, w + 36 * s), 180, 180, False)
    frame.lineTo(x + w / 2 + 18 * s, y)
    frame.close()
    _fill(c, frame, '#6E6A66', ink, ow, shader=lgrad(x - w / 2, 0, x + w / 2, 0, ['#8E8984', '#6E6A66', '#55514E']))
    hole = skia.Path()
    hole.moveTo(x - w / 2, y)
    hole.lineTo(x - w / 2, y - h + w / 2)
    hole.arcTo(skia.Rect.MakeXYWH(x - w / 2, y - h, w, w), 180, 180, False)
    hole.lineTo(x + w / 2, y)
    hole.close()
    c.drawPath(hole, P('#FFFFFF', shader=lgrad(x, y - h, x, y, [glow_col, lt(glow_col, 0.3)])))
    if open_ > 0:
        circ(c, x, y - h / 2, 260 * s, glow_col, 0.35 * open_, blur=60 * s)
    c.save()
    c.clipPath(hole, skia.ClipOp.kIntersect, True)
    k = math.cos(math.radians(80 * clamp(open_)))
    c.translate(x - w / 2, 0)
    c.scale(k, 1.0)
    c.translate(-(x - w / 2), 0)
    _fill(c, hole, '#7A4A2A', ink, ow, shader=lgrad(x - w / 2, 0, x + w / 2, 0, ['#9A6236', '#7A4A2A', '#5E361C']))
    for i in range(1, 4):
        line(c, x - w / 2 + i * w / 4, y - h + 30 * s, x - w / 2 + i * w / 4, y, '#4E2C16', w=3 * s)
    for yy in (y - h * 0.72, y - h * 0.25):
        _fill(c, skia.Path().addRect(skia.Rect.MakeXYWH(x - w / 2, yy - 14 * s, w, 28 * s)), '#3A3A40', ink, ow * 0.6)
        for i in range(5):
            circ(c, x - w / 2 + (18 + i * 46) * s, yy, 4.5 * s, '#8A8D96')
    circ(c, x + w * 0.32, y - h * 0.45, 18 * s, '#2E2E34', sw=6 * s)
    c.restore()
    c.drawPath(hole, P(ink, sw=ow * 2))


def bowl(c, x, y, s=1.0, look='castle', rot=0.0, t=0.0, papers=2):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    for k in range(papers):
        px = x + (k - (papers - 1) / 2) * 34 * s
        c.save()
        c.rotate(-14 + 28 * k, px, y - 58 * s)
        _fill(c, skia.Path().addRect(skia.Rect.MakeXYWH(px - 20 * s, y - 84 * s, 40 * s, 52 * s)), '#F6F1E4', ink, ow * 0.7)
        circ(c, px, y - 64 * s, 4 * s, '#B8262E')
        c.restore()
    q = skia.Path()
    q.moveTo(x - 92 * s, y - 52 * s)
    q.cubicTo(x - 86 * s, y - 2 * s, x - 40 * s, y + 10 * s, x, y + 10 * s)
    q.cubicTo(x + 40 * s, y + 10 * s, x + 86 * s, y - 2 * s, x + 92 * s, y - 52 * s)
    q.close()
    _fill(c, q, '#E8B23E', ink, ow, shader=lgrad(x - 92 * s, 0, x + 92 * s, 0, ['#FFE9A0', '#E8B23E', '#A8721C']))
    oval(c, x, y - 52 * s, 92 * s, 14 * s, ink, sw=ow * 1.6)
    oval(c, x, y - 52 * s, 92 * s, 14 * s, '#F2C14E', sw=ow * 0.7)
    for k, gc in enumerate(('#D8344A', '#2F8F6A', '#3C6BD8', '#D8344A')):
        circ(c, x + (k - 1.5) * 34 * s, y - 28 * s, 6 * s, gc)
    _fill(c, _rr(x - 34 * s, y + 6 * s, 68 * s, 18 * s, 6 * s), '#C8902E', ink, ow)
    c.restore()


def axe(c, x, y, s=1.0, look='castle', rot=0.0, t=0.0):
    """Gripped low on the handle; the head is up before rot."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    _stroke(c, [(x, y + 60 * s), (x, y - 190 * s)], 16 * s, '#7A4A2A', ink, ow)
    q = skia.Path()
    q.moveTo(x + 6 * s, y - 176 * s)
    q.lineTo(x + 50 * s, y - 196 * s)
    q.quadTo(x + 96 * s, y - 150 * s, x + 50 * s, y - 104 * s)
    q.lineTo(x + 6 * s, y - 124 * s)
    q.close()
    _fill(c, q, '#AAB0BA', ink, ow, shader=lgrad(x, 0, x + 90 * s, 0, ['#6E737C', '#AAB0BA', '#E6EAF0']))
    _fill(c, _rr(x - 12 * s, y - 186 * s, 24 * s, 74 * s, 6 * s), '#55595F', ink, ow)
    c.restore()


def candle(c, x, y, s=1.0, look='castle', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    oval(c, x, y, 40 * s + ow, 10 * s + ow, ink)
    oval(c, x, y, 40 * s, 10 * s, '#C8902E')
    q = _rr(x - 20 * s, y - 96 * s, 40 * s, 96 * s, 8 * s)
    _fill(c, q, '#F6EBD2', ink, ow, shader=lgrad(x - 20 * s, 0, x + 20 * s, 0, ['#FFF8E8', '#F2E2C0', '#D8C49C']))
    q = skia.Path()
    q.moveTo(x - 20 * s, y - 92 * s)
    q.quadTo(x - 22 * s, y - 60 * s, x - 14 * s, y - 56 * s)
    q.quadTo(x - 8 * s, y - 70 * s, x - 6 * s, y - 92 * s)
    c.drawPath(q, P('#FFF8E8'))
    line(c, x, y - 96 * s, x, y - 108 * s, '#2A2020', w=3 * s)
    _flame(c, x, y - 104 * s, 44 * s, t, x * 0.013)


def barrel(c, x, y, s=1.0, look='castle', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    w, h = 140 * s, 180 * s
    q = skia.Path()
    q.moveTo(x - w * 0.42, y)
    q.cubicTo(x - w * 0.56, y - h * 0.35, x - w * 0.56, y - h * 0.65, x - w * 0.42, y - h)
    q.lineTo(x + w * 0.42, y - h)
    q.cubicTo(x + w * 0.56, y - h * 0.65, x + w * 0.56, y - h * 0.35, x + w * 0.42, y)
    q.close()
    _fill(c, q, '#A0683A', ink, ow, shader=lgrad(x - w / 2, 0, x + w / 2, 0, ['#C88A52', '#A0683A', '#6E4222']))
    c.save()
    c.clipPath(q, skia.ClipOp.kIntersect, True)
    for i in range(1, 5):
        u = -0.5 + i * 0.2
        line(c, x + u * w * 0.9, y - h, x + u * w * 1.1, y - h / 2, '#6E4222', w=2.5 * s)
        line(c, x + u * w * 1.1, y - h / 2, x + u * w * 0.9, y, '#6E4222', w=2.5 * s)
    for yy in (y - h * 0.18, y - h * 0.82):
        c.drawRect(skia.Rect.MakeXYWH(x - w, yy - 9 * s, 2 * w, 18 * s), P('#4A4C52'))
    c.restore()
    oval(c, x, y - h, w * 0.42, 14 * s, ink, sw=ow * 2)
    oval(c, x, y - h, w * 0.42, 14 * s, '#B8804C')


def key(c, x, y, s=1.0, look='castle', rot=0.0, t=0.0):
    """Gripped at the bow; the shaft points right before rot."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    gold = '#E8B23E'
    circ(c, x, y, 19 * s, ink, sw=15 * s + 2 * ow)
    circ(c, x, y, 19 * s, gold, sw=15 * s)
    _stroke(c, [(x + 24 * s, y), (x + 120 * s, y)], 12 * s, gold, ink, ow)
    for dx, dh in ((96, 26), (112, 20)):
        _fill(c, _rr(x + dx * s - 6 * s, y, 12 * s, dh * s, 2 * s), gold, ink, ow)
    c.restore()


# ---------------------------------------------------------------- desert
def block_sled(c, x, y, s=1.0, look='desert', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    w, h, d = 230 * s, 130 * s, 60 * s
    q = skia.Path()
    q.moveTo(x - w * 0.62, y - 8 * s)
    q.lineTo(x + w * 0.5, y - 8 * s)
    q.quadTo(x + w * 0.7, y - 8 * s, x + w * 0.72, y - 34 * s)
    q.lineTo(x + w * 0.62, y - 34 * s)
    q.lineTo(x - w * 0.62, y - 34 * s)
    q.close()
    _fill(c, q, '#8A5A33', ink, ow, shader=lgrad(0, y - 34 * s, 0, y, ['#B07A4A', '#7A4A2A']))
    top = y - 34 * s
    front = _path([(x - w / 2, top), (x + w / 2, top), (x + w / 2, top - h), (x - w / 2, top - h)], True)
    lid = _path([(x - w / 2, top - h), (x + w / 2, top - h), (x + w / 2 + d * 0.6, top - h - d * 0.45),
                 (x - w / 2 + d * 0.6, top - h - d * 0.45)], True)
    side = _path([(x + w / 2, top), (x + w / 2 + d * 0.6, top - d * 0.45), (x + w / 2 + d * 0.6, top - h - d * 0.45),
                  (x + w / 2, top - h)], True)
    _fill(c, front, '#E9E3D3', ink, ow, shader=lgrad(0, top - h, 0, top, ['#F4EFE2', '#D9D0BA']))
    _fill(c, lid, '#F7F3E8', ink, ow)
    _fill(c, side, '#C9BFA6', ink, ow)
    for k in (0.33, 0.66):
        line(c, x - w / 2 + w * k, top - h + 6 * s, x - w / 2 + w * k, top - 6 * s, '#B7AC92', w=3 * s)
    line(c, x + w * 0.66, y - 22 * s, x + w * 1.1, y - 40 * s, '#C9A46A', w=6 * s)


def jug(c, x, y, s=1.0, look='desert', rot=0.0, t=0.0, pour=0.0):
    """Gripped at the handle; pour 0..1 tips it and spills water."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot + 70 * clamp(pour))
    bx = x + 44 * s
    q = skia.Path()
    q.moveTo(bx - 16 * s, y - 70 * s)
    q.lineTo(bx - 18 * s, y - 52 * s)
    q.cubicTo(bx - 64 * s, y - 40 * s, bx - 64 * s, y + 50 * s, bx, y + 56 * s)
    q.cubicTo(bx + 64 * s, y + 50 * s, bx + 64 * s, y - 40 * s, bx + 18 * s, y - 52 * s)
    q.lineTo(bx + 16 * s, y - 70 * s)
    q.close()
    _fill(c, q, '#C8683A', ink, ow, shader=rgrad(bx - 20 * s, y - 10 * s, 80 * s, ['#E8925E', '#C8683A', '#8E4422']))
    oval(c, bx, y - 70 * s, 24 * s + ow, 7 * s + ow, ink)
    oval(c, bx, y - 70 * s, 24 * s, 7 * s, '#7A3A1C')
    for k in range(2):
        line(c, bx - 40 * s, y - 4 * s + k * 14 * s, bx + 40 * s, y - 4 * s + k * 14 * s, '#F2D9A8', w=3.5 * s)
    h = skia.Path()
    h.moveTo(bx - 30 * s, y - 40 * s)
    h.cubicTo(x - 18 * s, y - 40 * s, x - 18 * s, y + 10 * s, bx - 44 * s, y + 10 * s)
    c.drawPath(h, P(ink, sw=10 * s + 2 * ow))
    c.drawPath(h, P('#B05A30', sw=10 * s))
    c.restore()
    if pour > 0.4:
        a = math.radians(rot + 70 * clamp(pour))
        mx, my = x + math.cos(a) * 44 * s - math.sin(a) * -70 * s, y + math.sin(a) * 44 * s + math.cos(a) * -70 * s
        for k in range(9):
            ph = (t * 1.8 + k / 9) % 1.0
            circ(c, mx + 30 * s * ph, my + 260 * s * ph * ph, (7 - 3 * ph) * s, '#7FC8F8', 0.9)


def palm(c, x, y, s=1.0, look='desert', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    sway = math.sin(t * 1.3) * 4
    pts = [(x + 40 * s * (k / 8) ** 2 + sway * s * k / 8, y - 360 * s * k / 8) for k in range(9)]
    _stroke(c, pts, 26 * s, '#8A5E36', ink, ow)
    for k in range(1, 8):
        a = pts[k]
        line(c, a[0] - 12 * s, a[1], a[0] + 12 * s, a[1] - 6 * s, '#5E3E22', w=3 * s)
    tx, ty = pts[-1]
    for k in range(7):
        ang = math.radians(-170 + k * 27 + sway)
        ln = (150 + 30 * (k % 2)) * s
        ex, ey = tx + math.cos(ang) * ln, ty + math.sin(ang) * ln * 0.55 + 40 * s
        q = skia.Path()
        q.moveTo(tx, ty)
        q.quadTo((tx + ex) / 2, ty - 50 * s + (ey - ty) * 0.2, ex, ey)
        q.quadTo((tx + ex) / 2, ty - 10 * s + (ey - ty) * 0.5, tx, ty)
        _fill(c, q, '#3E9A4A', ink, ow * 0.8, shader=lgrad(tx, ty - 40 * s, ex, ey, ['#62C46A', '#2E7A3A']))
    for k in range(3):
        circ(c, tx + (k - 1) * 16 * s, ty + 16 * s, 13 * s + ow * 0.6, ink)
        circ(c, tx + (k - 1) * 16 * s, ty + 16 * s, 13 * s, '#6B4423')


def basket(c, x, y, s=1.0, look='desert', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    for k, (dx, cl) in enumerate(((-26, '#D8344A'), (8, '#F2A33A'), (34, '#6BBF59'))):
        circ(c, x + dx * s, y - 4 * s, 24 * s + ow, ink)
        circ(c, x + dx * s, y - 4 * s, 24 * s, cl, shader=rgrad(x + dx * s - 8 * s, y - 12 * s, 30 * s, [lt(cl, 0.35), cl]))
    q = skia.Path()
    q.moveTo(x - 76 * s, y)
    q.lineTo(x + 76 * s, y)
    q.lineTo(x + 56 * s, y + 86 * s)
    q.lineTo(x - 56 * s, y + 86 * s)
    q.close()
    _fill(c, q, '#D2A464', ink, ow, shader=lgrad(x - 70 * s, 0, x + 70 * s, 0, ['#E6BE80', '#D2A464', '#A87A40']))
    c.save()
    c.clipPath(q, skia.ClipOp.kIntersect, True)
    for k in range(5):
        line(c, x - 80 * s, y + (12 + 17 * k) * s, x + 80 * s, y + (12 + 17 * k) * s, '#9E7038', w=3 * s)
    for k in range(-4, 5):
        line(c, x + k * 18 * s, y, x + k * 14 * s, y + 90 * s, '#B98A4E', w=2 * s)
    c.restore()
    _stroke(c, [(x - 80 * s, y), (x + 80 * s, y)], 12 * s, '#B98A4E', ink, ow)
    c.restore()


def rope(c, x, y, s=1.0, look='desert', rot=0.0, t=0.0):
    """A coil of rope lying on (x, y)."""
    ink, ow = _st(look, s)
    for k in range(4):
        rx, ry = (70 - 14 * k) * s, (22 - 3 * k) * s
        yy = y - k * 16 * s
        oval(c, x, yy - ry, rx, ry, ink, sw=14 * s + 2 * ow)
        oval(c, x, yy - ry, rx, ry, '#C9A46A', sw=14 * s)
        for j in range(12):
            a = 2 * math.pi * j / 12
            px, py = x + math.cos(a) * rx, yy - ry + math.sin(a) * ry
            line(c, px - 4 * s, py - 5 * s, px + 4 * s, py + 5 * s, '#9E7A44', w=2 * s)
    q = skia.Path()
    q.moveTo(x + 56 * s, y - 70 * s)
    q.quadTo(x + 120 * s, y - 60 * s, x + 130 * s, y)
    c.drawPath(q, P(ink, sw=14 * s + 2 * ow))
    c.drawPath(q, P('#C9A46A', sw=14 * s))


def oil_lamp(c, x, y, s=1.0, look='desert', rot=0.0, t=0.0):
    """Gripped at the handle on its left; the flame burns at the spout on the right."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    h = skia.Path()
    h.addArc(skia.Rect.MakeXYWH(x - 6 * s, y - 22 * s, 36 * s, 40 * s), 90, 180)
    c.drawPath(h, P(ink, sw=9 * s + 2 * ow))
    c.drawPath(h, P('#B86A3A', sw=9 * s))
    q = skia.Path()
    q.moveTo(x + 20 * s, y - 16 * s)
    q.cubicTo(x + 30 * s, y - 40 * s, x + 110 * s, y - 40 * s, x + 120 * s, y - 16 * s)
    q.lineTo(x + 160 * s, y - 24 * s)
    q.quadTo(x + 160 * s, y - 6 * s, x + 120 * s, y + 4 * s)
    q.cubicTo(x + 110 * s, y + 24 * s, x + 30 * s, y + 24 * s, x + 20 * s, y - 16 * s)
    q.close()
    _fill(c, q, '#C8683A', ink, ow, shader=lgrad(x, y - 40 * s, x, y + 24 * s, ['#E8925E', '#C8683A', '#8E4422']))
    circ(c, x + 70 * s, y - 24 * s, 9 * s + ow * 0.6, ink)
    circ(c, x + 70 * s, y - 24 * s, 9 * s, '#3A1C0C')
    c.restore()
    a = math.radians(rot)
    fx_, fy_ = x + math.cos(a) * 158 * s - math.sin(a) * -26 * s, y + math.sin(a) * 158 * s + math.cos(a) * -26 * s
    _flame(c, fx_, fy_, 40 * s, t, 3.0)


# ---------------------------------------------------------------- pill
def mug(c, x, y, s=1.0, look='pill', rot=0.0, t=0.0, col='#F2F2EE'):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    h = skia.Path()
    h.addArc(skia.Rect.MakeXYWH(x + 28 * s, y - 34 * s, 40 * s, 46 * s), -90, 180)
    c.drawPath(h, P(ink, sw=10 * s + 2 * ow))
    c.drawPath(h, P(col, sw=10 * s))
    q = _rr(x - 40 * s, y - 50 * s, 80 * s, 92 * s, 12 * s)
    _fill(c, q, col, ink, ow, shader=lgrad(x - 40 * s, 0, x + 40 * s, 0, [lt(col, 0.3), col, dk(col, 0.15)]))
    oval(c, x, y - 48 * s, 36 * s, 8 * s, '#5A3420')
    q = skia.Path()
    q.moveTo(x, y + 4 * s)
    q.cubicTo(x - 22 * s, y - 14 * s, x - 8 * s, y - 30 * s, x, y - 18 * s)
    q.cubicTo(x + 8 * s, y - 30 * s, x + 22 * s, y - 14 * s, x, y + 4 * s)
    c.drawPath(q, P('#E8505A'))
    c.restore()
    for k in range(3):
        ph = (t * 0.7 + k / 3) % 1.0
        sx = x + (k - 1) * 14 * s + math.sin(ph * 6 + k) * 8 * s
        circ(c, sx, y - 64 * s - ph * 80 * s, (8 + 10 * ph) * s, '#FFFFFF', 0.45 * math.sin(math.pi * ph), blur=4 * s)


def umbrella(c, x, y, s=1.0, look='pill', rot=0.0, t=0.0, col='#E8505A'):
    """Gripped at the handle; the canopy is up before rot."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    h = skia.Path()
    h.moveTo(x, y - 20 * s)
    h.lineTo(x, y + 20 * s)
    h.addArc(skia.Rect.MakeXYWH(x - 30 * s, y + 4 * s, 30 * s, 32 * s), 0, 180)
    c.drawPath(h, P(ink, sw=8 * s + 2 * ow))
    c.drawPath(h, P('#5A3A26', sw=8 * s))
    _stroke(c, [(x, y), (x, y - 220 * s)], 7 * s, '#4A4C52', ink, ow * 0.6)
    top = y - 220 * s
    q = skia.Path()
    q.moveTo(x - 150 * s, top + 60 * s)
    q.cubicTo(x - 140 * s, top - 60 * s, x + 140 * s, top - 60 * s, x + 150 * s, top + 60 * s)
    for k in range(5, 0, -1):
        x1, x0 = x - 150 * s + 60 * s * k, x - 150 * s + 60 * s * (k - 1)
        q.quadTo((x0 + x1) / 2, top + 36 * s, x0, top + 60 * s)
    q.close()
    _fill(c, q, col, ink, ow, shader=lgrad(x - 150 * s, 0, x + 150 * s, 0, [lt(col, 0.25), col, dk(col, 0.2)]))
    c.save()
    c.clipPath(q, skia.ClipOp.kIntersect, True)
    for k in (-1, 1):
        q2 = skia.Path()
        q2.moveTo(x, top - 30 * s)
        q2.quadTo(x + k * 40 * s, top, x + k * 90 * s, top + 70 * s)
        q2.lineTo(x + k * 30 * s, top + 70 * s)
        q2.close()
        c.drawPath(q2, P('#FFFFFF', 0.85))
    c.restore()
    circ(c, x, top - 34 * s, 7 * s, '#4A4C52')
    c.restore()


def balloon(c, x, y, s=1.0, look='pill', rot=0.0, t=0.0, col='#E8505A'):
    """Held at the end of its string; floats about 230 px above (x, y)."""
    ink, ow = _st(look, s)
    bx = x + math.sin(t * 1.4) * 16 * s
    by = y - 230 * s + math.sin(t * 2.1) * 6 * s
    q = skia.Path()
    q.moveTo(x, y)
    for k in range(1, 9):
        u = k / 8
        q.lineTo(x + (bx - x) * u + math.sin(u * 9 + t * 3) * 6 * s, y + (by + 62 * s - y) * u)
    c.drawPath(q, P(ink, sw=2.5 * s))
    q = skia.Path()
    q.addOval(skia.Rect.MakeXYWH(bx - 50 * s, by - 62 * s, 100 * s, 124 * s))
    _fill(c, q, col, ink, ow, shader=rgrad(bx - 18 * s, by - 26 * s, 90 * s, [lt(col, 0.45), col, dk(col, 0.25)]))
    _fill(c, _path([(bx - 9 * s, by + 70 * s), (bx + 9 * s, by + 70 * s), (bx, by + 58 * s)], True), dk(col, 0.1), ink, ow * 0.6)
    oval(c, bx - 20 * s, by - 28 * s, 9 * s, 16 * s, '#FFFFFF', 0.7)


def newspaper(c, x, y, s=1.0, look='pill', rot=0.0, t=0.0):
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    w, h = 150 * s, 190 * s
    _fill(c, skia.Path().addRect(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h)), '#F2F0E8', ink, ow,
          shader=lgrad(x - w / 2, 0, x + w / 2, 0, ['#FFFFFF', '#ECE8DC']))
    c.drawRect(skia.Rect.MakeXYWH(x - w / 2 + 12 * s, y - h / 2 + 14 * s, w - 24 * s, 24 * s), P('#2A2A30'))
    c.drawRect(skia.Rect.MakeXYWH(x - w / 2 + 12 * s, y - h / 2 + 48 * s, 60 * s, 50 * s), P('#9AA6B8'))
    for k in range(8):
        yy = y - h / 2 + (52 + 14 * k) * s
        x0 = x - w / 2 + (80 if k < 4 else 12) * s
        line(c, x0, yy, x + w / 2 - 12 * s, yy, '#8C8C96', w=4 * s)
    line(c, x, y - h / 2, x, y + h / 2, '#C9C5B8', w=2 * s)
    c.restore()


def ice_cream(c, x, y, s=1.0, look='pill', rot=0.0, t=0.0):
    """Gripped at the cone's tip-end; scoops on top."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    q = _path([(x - 40 * s, y - 70 * s), (x + 40 * s, y - 70 * s), (x, y + 40 * s)], True)
    _fill(c, q, '#E3A85E', ink, ow)
    c.save()
    c.clipPath(q, skia.ClipOp.kIntersect, True)
    for k in range(-4, 5):
        line(c, x + k * 16 * s - 40 * s, y - 70 * s, x + k * 16 * s + 40 * s, y + 40 * s, '#B87A3A', w=2.5 * s)
        line(c, x + k * 16 * s + 40 * s, y - 70 * s, x + k * 16 * s - 40 * s, y + 40 * s, '#B87A3A', w=2.5 * s)
    c.restore()
    for (dx, dy, cl) in ((0, -96, '#8FE0C0'), (0, -140, '#FF9EC2')):
        circ(c, x + dx * s, y + dy * s, 42 * s + ow, ink)
        circ(c, x + dx * s, y + dy * s, 42 * s, cl, shader=rgrad(x - 12 * s, y + (dy - 14) * s, 52 * s, [lt(cl, 0.4), cl, dk(cl, 0.1)]))
    circ(c, x + 6 * s, y - 188 * s, 11 * s + ow, ink)
    circ(c, x + 6 * s, y - 188 * s, 11 * s, '#D8243A')
    c.restore()


def briefcase(c, x, y, s=1.0, look='pill', rot=0.0, t=0.0, col='#7A4A2A'):
    """Gripped at the handle on top."""
    ink, ow = _st(look, s)
    _rot(c, x, y, rot)
    h = skia.Path()
    h.addArc(skia.Rect.MakeXYWH(x - 26 * s, y - 10 * s, 52 * s, 36 * s), 180, 180)
    c.drawPath(h, P(ink, sw=9 * s + 2 * ow))
    c.drawPath(h, P(dk(col, 0.25), sw=9 * s))
    q = _rr(x - 90 * s, y + 8 * s, 180 * s, 124 * s, 14 * s)
    _fill(c, q, col, ink, ow, shader=lgrad(x - 90 * s, 0, x + 90 * s, 0, [lt(col, 0.2), col, dk(col, 0.2)]))
    line(c, x - 90 * s, y + 48 * s, x + 90 * s, y + 48 * s, dk(col, 0.3), w=4 * s)
    for side in (-1, 1):
        _fill(c, _rr(x + side * 46 * s - 9 * s, y + 40 * s, 18 * s, 18 * s, 3 * s), '#E8B23E', ink, ow * 0.6)
    c.restore()


KITS = dict(
    whatif=['dumbbell', 'phone', 'backpack', 'trophy', 'basketball', 'water_bottle'],
    palace=['goblet', 'sword', 'scroll', 'torch', 'potion', 'coin_pouch'],
    castle=['door', 'bowl', 'axe', 'candle', 'barrel', 'key'],
    desert=['block_sled', 'jug', 'palm', 'basket', 'rope', 'oil_lamp'],
    pill=['mug', 'umbrella', 'balloon', 'newspaper', 'ice_cream', 'briefcase'],
)
HAND = {'dumbbell', 'phone', 'backpack', 'trophy', 'basketball', 'water_bottle', 'goblet', 'sword', 'scroll', 'torch',
        'potion', 'coin_pouch', 'bowl', 'axe', 'key', 'jug', 'basket', 'oil_lamp', 'mug', 'umbrella', 'balloon',
        'newspaper', 'ice_cream', 'briefcase'}
