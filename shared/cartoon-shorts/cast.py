"""cast: the people of the five cartoon looks, drawn with skia-python on the humanoid rig (humanoid.py's poses work).

  whatif  black round head with big white eyes, stick limbs, clothes and sneakers ("What if you..." Shorts)
  palace  big skin-tone head with a thick outline, rosy cheeks, headband or crown, a robe (palace history stories)
  castle  white round head, a peg body in a stitched tunic, curly hair or a kettle helmet (castle puzzle stories)
  desert  small skin-tone head, black hair or a head cloth, tunic and belt, thin stick limbs (desert explainers)
  pill    white round head with a black bowl cut, a pill-shaped body with buttons, thin stick limbs (town what-ifs)

  person(c, x, ground, s, look, pose=None, view='front', outfit=None, expr='open', gaze=None, blink=0.0, flip=False,
         lift=0.0, rot=0.0, pivot=None, hip_y=None, hold=None, alpha=1.0, sweat=False) -> joints
  head(c, x, y, s, look, outfit=None, expr='open', gaze=None, blink=0.0, flip=False, view='front', tilt=0.0)
  light(dir)  where the key light comes from, as a direction from the figure (default up and to the left)

outfit overrides the look's defaults (settings.LOOKS): top, trim, bottom, shoes, skin, hair (bowl, curly, spiky, cloth,
None), hair_col, hat (crown, headband, helmet, cap, hardhat, None), hat_col, beard (white, stubble, None), robe, sleeves
(short, long). A dark skin (the castle's executioner, every whatif head) gets big white eyes instead of dot eyes.
expr: open, smile, grin, smug, shock, angry, sad, tired, closed, worried, shout. gaze (x, y) in -1..1 moves the pupils.
Joints: hip, shoulder, head, la / ra / ll / rl = (elbow or knee, hand or foot), like humanoid.figure. Angles are
humanoid's: degrees, 0 points down, +90 forward; a limb can be ('ik', (x, y), bend) to reach a screen point.
"""
import math

import skia

import humanoid as hu
from settings import LOOKS
from storytime_kit import P, circ, oval, line, rrect, lgrad, rgrad, clamp, mix

LIGHT = [(-0.6, -0.8)]


def light(dir=(-0.6, -0.8)):
    n = math.hypot(*dir) or 1.0
    LIGHT[0] = (dir[0] / n, dir[1] / n)


def lum(h):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b


def dk(h, k):
    return mix(h, '#000000', k)


def lt(h, k):
    return mix(h, '#FFFFFF', k)


def _path(pts, close=False):
    q = skia.Path()
    q.moveTo(*pts[0])
    for p in pts[1:]:
        q.lineTo(*p)
    if close:
        q.close()
    return q


def _stroke(c, pts, w, col, ink=None, ow=0.0, a=1.0):
    """A round-capped stroke through pts, w wide, with an ink edge ow wide around it."""
    q = _path(pts)
    if ink and ow:
        c.drawPath(q, P(ink, a, sw=w + 2 * ow))
    c.drawPath(q, P(col, a, sw=w))


def _fill(c, q, col, ink=None, ow=0.0, shader=None, a=1.0):
    if ink and ow:
        c.drawPath(q, P(ink, a, sw=2 * ow))
    c.drawPath(q, P(col, a, shader=shader))


def _rr(x, y, w, h, r):
    q = skia.Path()
    q.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    return q


def _side_grad(x0, x1, col, k=0.22):
    """Lighter toward the light, darker away, across a body from x0 to x1 (local coordinates)."""
    lx = LIGHT[0][0]
    a, b = (lt(col, k * 0.6), dk(col, k)) if lx <= 0 else (dk(col, k), lt(col, k * 0.6))
    return lgrad(x0, 0, x1, 0, [a, col, b], [0, 0.45, 1])


# ---------------------------------------------------------------- heads
def _eyes_dark_head(c, x, y, r, f, view, expr, gaze, blink):
    """Big white eyes on a dark head (whatif, the executioner)."""
    gx, gy = gaze or ((0.0, 0.0) if view == 'front' else (0.7, 0.0))
    cx = x + (0.2 * r * f if view != 'front' else 0.0)
    sp = 0.29 * r if view == 'front' else 0.25 * r
    big = 1.25 if expr == 'shock' else 1.0
    for side in (-1, 1):
        ex, ey = cx + side * sp, y - 0.06 * r
        rx, ry = 0.25 * r * big, 0.3 * r * big
        if view != 'front' and side * f < 0:
            rx *= 0.8
        if expr == 'closed' or blink > 0.94:
            q = skia.Path()
            q.moveTo(ex - rx, ey + 0.05 * r)
            q.quadTo(ex, ey - ry * (0.9 if expr == 'closed' else 0.1), ex + rx, ey + 0.05 * r)
            c.drawPath(q, P('#FFFFFF', sw=0.075 * r))
            continue
        oval(c, ex, ey, rx, ry, '#FFFFFF')
        pr = 0.11 * r * (0.65 if expr == 'shock' else 1.0)
        circ(c, ex + gx * rx * 0.45 * f, ey + gy * ry * 0.4 + 0.03 * r, pr, '#0B0B0E')
        c.save()
        q = skia.Path()
        q.addOval(skia.Rect.MakeXYWH(ex - rx, ey - ry, 2 * rx, 2 * ry))
        c.clipPath(q, skia.ClipOp.kIntersect, True)
        lid = max(blink, dict(tired=0.5, smug=0.42).get(expr, 0.0))
        if lid > 0:
            c.drawRect(skia.Rect.MakeXYWH(ex - rx - 2, ey - ry - 2, 2 * rx + 4, 2 * ry * lid + 2), P('#0B0B0E'))
        if expr in ('angry', 'sad', 'worried'):
            right_low = (side < 0) if expr == 'angry' else (side > 0)    # angry: inner ends low; sad: outer ends
            q = skia.Path()
            q.moveTo(ex - rx - 4, ey - ry - 4)
            q.lineTo(ex + rx + 4, ey - ry - 4)
            hi, lo = ey - ry * 0.75, ey - ry * 0.05
            q.lineTo(ex + rx + 4, lo if right_low else hi)
            q.lineTo(ex - rx - 4, hi if right_low else lo)
            q.close()
            c.drawPath(q, P('#0B0B0E'))
        c.restore()
    my = y + 0.42 * r
    if expr == 'smile':
        q = skia.Path()
        q.moveTo(cx - 0.2 * r, my - 0.03 * r)
        q.quadTo(cx, my + 0.12 * r, cx + 0.2 * r, my - 0.03 * r)
        c.drawPath(q, P('#FFFFFF', sw=0.06 * r))
    elif expr in ('grin', 'shout'):
        q = skia.Path()
        if expr == 'grin':
            q.moveTo(cx - 0.24 * r, my - 0.06 * r)
            q.quadTo(cx, my + 0.26 * r, cx + 0.24 * r, my - 0.06 * r)
            q.close()
            c.drawPath(q, P('#FFFFFF'))
            line(c, cx - 0.2 * r, my + 0.02 * r, cx + 0.2 * r, my + 0.02 * r, '#0B0B0E', w=0.03 * r)
        else:
            oval(c, cx, my + 0.04 * r, 0.14 * r, 0.12 * r, '#7A1E24')
            oval(c, cx, my + 0.04 * r, 0.14 * r, 0.12 * r, '#FFFFFF', sw=0.04 * r)
    elif expr == 'shock':
        oval(c, cx, my + 0.02 * r, 0.06 * r, 0.075 * r, '#FFFFFF', sw=0.035 * r)


def _face_dots(c, x, y, r, f, view, expr, gaze, blink, ink, cheeks=None, brow_w=0.06):
    """Dot eyes, brows and a mouth on a light head (palace, castle, desert, pill)."""
    gx, gy = gaze or ((0.0, 0.0) if view == 'front' else (0.6, 0.0))
    cx = x + gx * 0.08 * r * f + (0.22 * r * f if view != 'front' else 0.0)
    cy = y + gy * 0.05 * r
    sp = 0.27 * r if view == 'front' else 0.22 * r
    ey = cy - 0.02 * r
    bw = brow_w * r
    for side in (-1, 1):
        ex = cx + side * sp
        sz = 1.0 if view == 'front' or side * f > 0 else 0.82
        if expr in ('shock', 'worried'):
            er = 0.15 * r * sz
            circ(c, ex, ey, er, '#FFFFFF')
            circ(c, ex, ey, er, ink, sw=0.035 * r)
            circ(c, ex + gx * er * 0.35 * f, ey + gy * er * 0.3, er * 0.36, ink)
        elif expr == 'closed' or blink > 0.94:
            q = skia.Path()
            q.moveTo(ex - 0.09 * r, ey + 0.02 * r)
            q.quadTo(ex, ey - 0.07 * r, ex + 0.09 * r, ey + 0.02 * r)
            c.drawPath(q, P(ink, sw=0.04 * r))
        elif expr in ('smug', 'tired'):
            oval(c, ex, ey + 0.03 * r, 0.075 * r * sz, 0.05 * r * sz, ink)
            line(c, ex - 0.11 * r, ey - 0.005 * r, ex + 0.11 * r, ey + (0.02 if expr == 'smug' else 0.0) * r * side * f,
                 ink, w=0.035 * r)
        else:
            k = 1 - blink
            oval(c, ex, ey, 0.065 * r * sz, 0.095 * r * sz * max(k, 0.1), ink)
            if k > 0.5:
                circ(c, ex - 0.022 * r, ey - 0.035 * r, 0.022 * r, '#FFFFFF')
        by = ey - 0.2 * r
        inner, outer = ex - side * 0.08 * r, ex + side * 0.11 * r
        yi, yo = dict(angry=(by + 0.07 * r, by - 0.04 * r), sad=(by - 0.05 * r, by + 0.03 * r),
                      worried=(by - 0.06 * r, by + 0.02 * r), shock=(by - 0.07 * r, by - 0.06 * r),
                      smug=(by + 0.02 * r, by - 0.02 * r)).get(expr, (by, by - 0.01 * r))
        if expr == 'smug' and side * f < 0:
            yi, yo = yi - 0.05 * r, yo - 0.05 * r
        c.drawPath(_path([(inner, yi), (outer, yo)]), P(ink, sw=bw))
    if cheeks:
        for side in (-1, 1):
            oval(c, cx + side * 0.42 * r, cy + 0.2 * r, 0.12 * r, 0.075 * r, cheeks, 0.45, blur=0.03 * r)
    mx, my = cx, cy + 0.3 * r
    mw = 0.035 * r
    if expr in ('smile', 'closed'):
        q = skia.Path()
        q.moveTo(mx - 0.13 * r, my - 0.02 * r)
        q.quadTo(mx, my + 0.1 * r, mx + 0.13 * r, my - 0.02 * r)
        c.drawPath(q, P(ink, sw=mw))
    elif expr == 'smug':
        q = skia.Path()
        q.moveTo(mx - 0.12 * r * f, my + 0.02 * r)
        q.quadTo(mx + 0.02 * r * f, my + 0.06 * r, mx + 0.14 * r * f, my - 0.05 * r)
        c.drawPath(q, P(ink, sw=mw))
    elif expr == 'grin':
        q = skia.Path()
        q.moveTo(mx - 0.2 * r, my - 0.04 * r)
        q.quadTo(mx, my + 0.24 * r, mx + 0.2 * r, my - 0.04 * r)
        q.close()
        c.drawPath(q, P('#FFFFFF'))
        c.drawPath(q, P(ink, sw=mw * 0.9))
        line(c, mx - 0.17 * r, my + 0.03 * r, mx + 0.17 * r, my + 0.03 * r, ink, w=mw * 0.6)
    elif expr == 'angry':
        rrect(c, mx - 0.15 * r, my - 0.04 * r, 0.3 * r, 0.11 * r, 0.03 * r, '#FFFFFF')
        rrect(c, mx - 0.15 * r, my - 0.04 * r, 0.3 * r, 0.11 * r, 0.03 * r, ink, sw=mw * 0.8)
        for k in (-1, 0, 1):
            line(c, mx + k * 0.06 * r, my - 0.04 * r, mx + k * 0.06 * r, my + 0.07 * r, ink, w=mw * 0.5)
    elif expr in ('shout', 'shock'):
        oval(c, mx, my + 0.04 * r, 0.09 * r, (0.11 if expr == 'shout' else 0.08) * r, '#5A1E22')
        oval(c, mx, my + 0.04 * r, 0.09 * r, (0.11 if expr == 'shout' else 0.08) * r, ink, sw=mw * 0.8)
    elif expr in ('sad', 'worried'):
        q = skia.Path()
        q.moveTo(mx - 0.11 * r, my + 0.04 * r)
        q.quadTo(mx - 0.04 * r, my - 0.02 * r, mx, my + 0.02 * r)
        q.quadTo(mx + 0.05 * r, my + 0.06 * r, mx + 0.11 * r, my)
        c.drawPath(q, P(ink, sw=mw))
    else:
        line(c, mx - 0.07 * r, my + 0.01 * r, mx + 0.07 * r, my + 0.01 * r, ink, w=mw)


def _crown(c, x, y, r, ink, ow, gold='#F2C14E'):
    base = y - 0.62 * r
    pts = [(x - 0.62 * r, base + 0.18 * r)]
    for k in range(5):
        u = -0.62 + 0.31 * k
        pts += [(x + (u + 0.0) * r, base - (0.55 if k % 2 == 0 else 0.42) * r), (x + (u + 0.155) * r, base)]
    pts[-1] = (x + 0.62 * r, base)
    pts.append((x + 0.62 * r, base + 0.18 * r))
    q = _path(pts, True)
    _fill(c, q, gold, ink, ow, shader=lgrad(x, base - 0.5 * r, x, base + 0.2 * r, ['#FFE6A0', gold, '#C8902E']))
    for k, gc in enumerate(('#D8344A', '#3C6BD8', '#D8344A')):
        circ(c, x + (k - 1) * 0.34 * r, base + 0.08 * r, 0.06 * r, gc)
    for k in range(0, 5, 2):
        circ(c, x + (-0.62 + 0.31 * k) * r, base - 0.57 * r, 0.05 * r, '#FFF4C8')


def head(c, x, y, s, look, outfit=None, expr='open', gaze=None, blink=0.0, flip=False, view='front', tilt=0.0,
         sweat=False):
    L = LOOKS[look]
    o = dict(L['outfit'], **(outfit or {}))
    r = L['seg']['head'] * s
    f = -1.0 if flip else 1.0
    ink, ow = L['ink'], L.get('ow', 0) * s
    skin = '#111114' if look == 'whatif' else o.get('skin', '#FBF7EF')
    dark = lum(skin) < 0.3
    lx, ly = LIGHT[0]
    hair, hc = o.get('hair'), o.get('hair_col', '#1E1712')
    # behind the head: curly hair, the spikes, a beard's back
    if hair == 'curly':
        for k in range(9):
            th = math.radians(200 + 140 * k / 8)
            px, py = x + math.cos(th) * 0.92 * r, y + math.sin(th) * 0.92 * r
            circ(c, px, py, 0.3 * r + ow, ink)
            circ(c, px, py, 0.3 * r, hc)
    if hair == 'spiky':
        pts = [(x, y)]
        for k in range(15):
            th = math.radians(196 + 148 * k / 14)
            rr_ = (1.36 if k % 2 else 0.86) * r
            pts.append((x + math.cos(th) * rr_, y + math.sin(th) * rr_))
        q = _path(pts, True)
        _fill(c, q, '#111114' if look == 'whatif' else hc, '#2C2C36' if look == 'whatif' else ink, max(ow, 1.5 * s))
    # the head
    q = skia.Path()
    q.addCircle(x, y, r)
    if dark:
        sh = rgrad(x + lx * 0.4 * r, y + ly * 0.4 * r, 1.4 * r, ['#34343E', '#141418', '#060608'], [0, 0.55, 1])
        _fill(c, q, skin, '#2C2C36' if look == 'whatif' else ink, max(ow, 1.5 * s), shader=sh)
    else:
        sh = rgrad(x + lx * 0.45 * r, y + ly * 0.45 * r, 1.5 * r, [lt(skin, 0.35), skin, dk(skin, 0.16)], [0, 0.5, 1])
        _fill(c, q, skin, ink, ow, shader=sh)
    # hair and hats on top
    if hair == 'bowl':
        c.save()
        c.clipPath(q, skia.ClipOp.kIntersect, True)
        hq = skia.Path()
        edge = y - 0.18 * r
        hq.moveTo(x - 1.1 * r, y + 0.02 * r)
        hq.quadTo(x, y - 0.36 * r, x + 1.1 * r, y + 0.02 * r)
        hq.lineTo(x + 1.1 * r, y - 1.2 * r)
        hq.lineTo(x - 1.1 * r, y - 1.2 * r)
        hq.close()
        c.drawPath(hq, P(hc, shader=lgrad(x, y - r, x, edge, [lt(hc, 0.12), hc])))
        c.drawPath(hq, P(ink, sw=max(ow, 1.5 * s)))
        c.restore()
    elif hair == 'cloth':
        c.save()
        c.clipPath(q, skia.ClipOp.kIntersect, True)
        c.drawRect(skia.Rect.MakeXYWH(x - 1.1 * r, y - 1.2 * r, 2.2 * r, 1.0 * r), P(o.get('hat_col', '#F1EEE4')))
        c.restore()
        line(c, x - 0.96 * r, y - 0.2 * r, x + 0.96 * r, y - 0.2 * r, o.get('trim', '#B8473A'), w=0.1 * r)
    elif hair == 'curly':
        for k in range(5):
            px = x + (k - 2) * 0.33 * r
            py = y - 0.78 * r + abs(k - 2) * 0.12 * r
            circ(c, px, py, 0.27 * r + ow, ink)
            circ(c, px, py, 0.27 * r, hc, shader=rgrad(px - 0.08 * r, py - 0.1 * r, 0.32 * r, [lt(hc, 0.25), hc]))
    # face
    if dark:
        _eyes_dark_head(c, x, y, r, f, view, expr, gaze, blink)
    else:
        _face_dots(c, x, y, r, f, view, expr, gaze, blink, ink, cheeks='#F0767A' if look == 'palace' else None,
                   brow_w=0.07 if look == 'palace' else 0.05)
    beard = o.get('beard')
    if beard == 'stubble':
        for k in range(14):
            th = math.radians(30 + 120 * k / 13)
            circ(c, x + math.cos(th) * 0.62 * r, y + math.sin(th) * 0.62 * r, 0.018 * r, dk(skin, 0.45), 0.7)
    elif beard == 'white':
        bq = skia.Path()
        bq.moveTo(x - 0.9 * r, y + 0.12 * r)
        for k in range(11):
            u = -0.9 + 0.18 * k
            bq.quadTo(x + (u + 0.09) * r, y + (0.62 + 0.62 * (1 - abs(u + 0.09) / 0.9) + 0.14) * r,
                      x + (u + 0.18) * r, y + (0.55 + 0.6 * (1 - abs(u + 0.18) / 0.9)) * r)
        bq.lineTo(x + 0.9 * r, y + 0.12 * r)
        bq.quadTo(x + 0.55 * r, y + 0.62 * r, x, y + 0.6 * r)
        bq.quadTo(x - 0.55 * r, y + 0.62 * r, x - 0.9 * r, y + 0.12 * r)
        bq.close()
        _fill(c, bq, '#F4F2EE', ink, ow, shader=lgrad(x, y, x, y + 1.3 * r, ['#FFFFFF', '#D9D6D0']))
        mq = skia.Path()
        mq.moveTo(x, y + 0.24 * r)
        mq.quadTo(x - 0.2 * r, y + 0.12 * r, x - 0.34 * r, y + 0.36 * r)
        mq.quadTo(x - 0.16 * r, y + 0.3 * r, x, y + 0.32 * r)
        mq.quadTo(x + 0.16 * r, y + 0.3 * r, x + 0.34 * r, y + 0.36 * r)
        mq.quadTo(x + 0.2 * r, y + 0.12 * r, x, y + 0.24 * r)
        _fill(c, mq, '#FFFFFF', ink, ow * 0.6)
    hat, hcol = o.get('hat'), o.get('hat_col')
    if hat == 'crown':
        _crown(c, x, y, r, ink, ow if ow else 2 * s)
    elif hat == 'headband':
        q = skia.Path()
        q.moveTo(x - 0.985 * r, y - 0.1 * r)
        q.quadTo(x, y - 0.38 * r, x + 0.985 * r, y - 0.1 * r)
        c.drawPath(q, P(ink, sw=0.13 * r + 2 * ow))
        c.drawPath(q, P(hcol or '#F2C14E', sw=0.13 * r))
        circ(c, x, y - 0.24 * r, 0.07 * r + ow * 0.6, ink)
        circ(c, x, y - 0.24 * r, 0.07 * r, '#7B3FC4')
    elif hat == 'helmet':
        hq = skia.Path()
        hq.addArc(skia.Rect.MakeXYWH(x - 1.04 * r, y - 1.12 * r, 2.08 * r, 1.7 * r), 180, 180)
        hq.close()
        _fill(c, hq, hcol or '#9EA3AB', ink, ow, shader=lgrad(x - r, 0, x + r, 0, ['#D3D7DD', hcol or '#9EA3AB', '#6E737C']))
        bq = _rr(x - 1.32 * r, y - 0.36 * r, 2.64 * r, 0.2 * r, 0.1 * r)
        _fill(c, bq, dk(hcol or '#9EA3AB', 0.1), ink, ow)
    elif hat == 'cap':
        cc = hcol or '#D8343A'
        hq = skia.Path()
        hq.addArc(skia.Rect.MakeXYWH(x - 1.0 * r, y - 1.1 * r, 2.0 * r, 1.6 * r), 180, 180)
        hq.close()
        _fill(c, hq, cc, ink, ow if ow else 2 * s, shader=lgrad(x - r, 0, x + r, 0, [lt(cc, 0.2), cc, dk(cc, 0.2)]))
        bq = skia.Path()
        if view == 'front':
            bq.moveTo(x - 0.8 * r, y - 0.36 * r)
            bq.quadTo(x, y - 0.02 * r, x + 0.8 * r, y - 0.36 * r)
            bq.quadTo(x, y - 0.24 * r, x - 0.8 * r, y - 0.36 * r)
        else:
            bq.addOval(skia.Rect.MakeXYWH(x + 0.78 * r * f - 0.5 * r, y - 0.44 * r, 1.0 * r, 0.2 * r))
        _fill(c, bq, dk(cc, 0.15), ink, ow if ow else 2 * s)
        circ(c, x, y - 1.08 * r, 0.07 * r, dk(cc, 0.25))
    elif hat == 'hardhat':
        cc = hcol or '#F2C230'
        hq = skia.Path()
        hq.addArc(skia.Rect.MakeXYWH(x - 1.0 * r, y - 1.12 * r, 2.0 * r, 1.64 * r), 180, 180)
        hq.close()
        _fill(c, hq, cc, ink, ow if ow else 2 * s, shader=lgrad(x - r, 0, x + r, 0, [lt(cc, 0.3), cc, dk(cc, 0.15)]))
        bq = _rr(x - 1.18 * r, y - 0.38 * r, 2.36 * r, 0.16 * r, 0.08 * r)
        _fill(c, bq, dk(cc, 0.08), ink, ow if ow else 2 * s)
        line(c, x, y - 1.04 * r, x, y - 0.42 * r, dk(cc, 0.18), w=0.1 * r)
    if sweat:
        sx, sy = x + 0.78 * r * f, y - 0.42 * r
        dq = skia.Path()
        dq.moveTo(sx, sy - 0.16 * r)
        dq.quadTo(sx + 0.1 * r, sy + 0.02 * r, sx, sy + 0.08 * r)
        dq.quadTo(sx - 0.1 * r, sy + 0.02 * r, sx, sy - 0.16 * r)
        _fill(c, dq, '#7FC8F8', ink if ow else None, ow * 0.6)


# ---------------------------------------------------------------- bodies
def _rig(x, ground, s, p, seg, view, f, lift, hip_y):
    def dv(a, ln):
        dx, dy = hu._d(a)
        return f * dx * ln * s, dy * ln * s

    def ext(spec):
        if spec[0] == 'ik':
            return seg['thigh'] + seg['shin']
        return math.cos(math.radians(spec[0])) * seg['thigh'] + math.cos(math.radians(spec[1])) * seg['shin']

    low = max(ext(p['ll']), ext(p['rl'])) + seg['foot']
    hip = (x, hip_y - lift) if hip_y is not None else (x, ground - low * s - lift)
    up = 180 - p['torso']
    dx, dy = dv(up, seg['torso'])
    sh = (hip[0] + dx, hip[1] + dy)
    dx, dy = dv(up - p['head'], seg['neck'] + seg['head'] * 0.98)
    hd = (sh[0] + dx, sh[1] + dy)
    return hip, sh, hd, up, dv


def person(c, x, ground, s=1.0, look='whatif', pose=None, view='front', outfit=None, expr='open', gaze=None, blink=0.0,
           flip=False, lift=0.0, rot=0.0, pivot=None, hip_y=None, hold=None, alpha=1.0, sweat=False, shadow=0.35):
    L = LOOKS[look]
    seg = L['seg']
    o = dict(L['outfit'], **(outfit or {}))
    p = pose or (hu.stand_front() if view == 'front' else hu.stand())
    f = -1.0 if flip else 1.0
    piv = pivot or (x, ground)
    ink, ow = L['ink'], L.get('ow', 0) * s
    if alpha < 1.0:
        c.saveLayerAlpha(None, int(255 * clamp(alpha)))
    if shadow and not rot:
        oval(c, x, ground + 4 * s, 70 * s, 13 * s, '#000000', shadow * (1 - clamp(lift / (220 * s))), blur=9 * s)
    if rot:
        c.save()
        c.rotate(rot, *piv)
    hip, sh, hd, up, dv = _rig(x, ground, s, p, seg, view, f, lift, hip_y)
    ux, uy = hu._d(up)
    ux *= f
    px_, py_ = -uy, ux                              # across the body
    tilt = f * p['torso']
    if view == 'front':
        ax = (seg['torso_w'] / 2 - dict(whatif=7, palace=14, castle=4, desert=6, pill=6)[look]) * s
        ay = dict(whatif=12, palace=24, castle=44, desert=10, pill=50)[look] * s
        aroot = {'la': (sh[0] - px_ * ax - ux * ay, sh[1] - py_ * ax - uy * ay),
                 'ra': (sh[0] + px_ * ax - ux * ay, sh[1] + py_ * ax - uy * ay)}
        lroot = {'ll': (hip[0] - px_ * seg['hip_w'] * s, hip[1] - py_ * seg['hip_w'] * s),
                 'rl': (hip[0] + px_ * seg['hip_w'] * s, hip[1] + py_ * seg['hip_w'] * s)}
    else:
        ay = dict(whatif=14, palace=26, castle=46, desert=12, pill=52)[look] * s
        r0 = (sh[0] - ux * ay, sh[1] - uy * ay)
        aroot, lroot = {'la': r0, 'ra': r0}, {'ll': hip, 'rl': hip}
    joints = dict(hip=hip, shoulder=sh, head=hd, aroot=aroot['ra'], aroot_l=aroot['la'])

    def solve(k, l1, l2):
        spec = p[k]
        root = aroot.get(k) or lroot[k]
        if spec[0] == 'ik':
            tgt = hu._rot(spec[1], -rot, piv) if rot else spec[1]
            el, end = hu.ik2(root, tgt, seg[l1] * s, seg[l2] * s, spec[2] * f)
        else:
            dx, dy = dv(spec[0], seg[l1])
            el = (root[0] + dx, root[1] + dy)
            dx, dy = dv(spec[1], seg[l2])
            end = (el[0] + dx, el[1] + dy)
        joints[k] = (el, end)
        return root, el, end

    legs = {k: solve(k, 'thigh', 'shin') for k in ('ll', 'rl')}
    arms = {k: solve(k, 'upper', 'fore') for k in ('la', 'ra')}
    W = dict(look=look, s=s, o=o, ink=ink, ow=ow, f=f, view=view, L=L, seg=seg)

    def leg(k, back=False):
        _leg(c, W, legs[k], back)

    def arm(k, back=False):
        _arm(c, W, arms[k], back)

    if view == 'front':
        leg('ll')
        leg('rl')
        _body(c, W, hip, sh, tilt)
        if look != 'palace':
            arm('la')
            arm('ra')
    else:
        arm('la', back=True)
        leg('ll', back=True)
        _body(c, W, hip, sh, tilt)
        leg('rl')
    if look == 'whatif':
        _stroke(c, [sh, (sh[0] + (hd[0] - sh[0]) * 0.5, sh[1] + (hd[1] - sh[1]) * 0.5)], L['limb'] * s * 1.1, '#111114')
    head(c, hd[0], hd[1], s, look, outfit, expr, gaze, blink, flip, view, f * (p['torso'] + p['head']), sweat)
    if view == 'front' and look == 'palace':
        arm('la')
        arm('ra')
    elif view != 'front':
        arm('ra')
    if hold:
        hold(c, joints)
    if rot:
        c.restore()
        joints = {k: (tuple(hu._rot(q, rot, piv) for q in v) if isinstance(v[0], tuple) else hu._rot(v, rot, piv))
                  for k, v in joints.items()}
    if alpha < 1.0:
        c.restore()
    return joints


def _leg(c, W, pts, back):
    look, s, o, ink, ow, L = W['look'], W['s'], W['o'], W['ink'], W['ow'], W['L']
    root, kn, ft = pts
    dkk = 0.25 if back else 0.0
    if look == 'whatif':
        pc = dk(o['bottom'], dkk)
        _stroke(c, [root, kn, ft], L['pants'] * s, pc, '#0C0C10', 2.5 * s)
        _shoe(c, W, ft, kn, dk(o['shoes'], dkk), '#0C0C10', 2.5 * s, 1.25)
    elif look == 'palace':
        _stroke(c, [root, kn, ft], L['limb'] * s * 0.8, dk(o['skin'], dkk), ink, ow)
        _shoe(c, W, ft, kn, dk('#8A5A33', dkk), ink, ow, 0.9)
    else:
        lc = dk('#141416', dkk * 0.5)
        _stroke(c, [root, kn, ft], L['limb'] * s, lc)
        _shoe(c, W, ft, kn, dk(o.get('shoes', '#2B2523'), dkk), ink, max(ow * 0.6, 1.5 * s), 0.7)


def _shoe(c, W, ft, kn, col, ink, ow, size):
    s, f, view = W['s'], W['f'], W['view']
    if view == 'front':
        out = -1 if ft[0] < kn[0] + 0.01 else 1
        cx, w = ft[0] + out * 6 * s * size, 30 * s * size
    else:
        cx, w = ft[0] + f * 12 * s * size, 36 * s * size
    q = skia.Path()
    q.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, ft[1] - 11 * s * size, w, 18 * s * size),
                                     9 * s * size, 9 * s * size))
    _fill(c, q, col, ink, ow)
    if W['look'] == 'whatif':
        line(c, cx - w / 2 + 3 * s, ft[1] + 4 * s, cx + w / 2 - 3 * s, ft[1] + 4 * s, '#B8BCC6', w=3 * s)


def _arm(c, W, pts, back):
    look, s, o, ink, ow, L = W['look'], W['s'], W['o'], W['ink'], W['ow'], W['L']
    root, el, hand = pts
    dkk = 0.22 if back else 0.0
    if look == 'whatif':
        k = 0.62 if o.get('sleeves', 'short') == 'short' else 1.0
        _stroke(c, [root, el, hand], L['limb'] * s, '#111114')
        circ(c, hand[0], hand[1], L['limb'] * 0.95 * s, '#111114')
        mid = (root[0] + (el[0] - root[0]) * k, root[1] + (el[1] - root[1]) * k)
        sl = [root, mid] if k < 1 else [root, el, hand]
        _stroke(c, sl, L['sleeve'] * s, dk(o['top'], dkk), '#0C0C10', 2.5 * s)
    elif look == 'palace':
        _stroke(c, [root, el, hand], L['limb'] * s, dk(o['skin'], dkk), ink, ow)
        _stroke(c, [root, (root[0] + (el[0] - root[0]) * 0.8, root[1] + (el[1] - root[1]) * 0.8)], L['limb'] * 1.45 * s,
                dk(o['top'], dkk), ink, ow)
        circ(c, hand[0], hand[1], L['limb'] * 0.62 * s + ow, ink)
        circ(c, hand[0], hand[1], L['limb'] * 0.62 * s, dk(o['skin'], dkk))
    elif look == 'castle':
        _stroke(c, [root, el, hand], 22 * s, dk(o['top'], dkk + 0.05), ink, ow)
        circ(c, hand[0], hand[1], 11 * s + ow, ink)
        circ(c, hand[0], hand[1], 11 * s, dk(o['skin'] if lum(o['skin']) > 0.3 else '#FBF7EF', dkk))
    else:
        _stroke(c, [root, el, hand], L['limb'] * s, '#141416')
        circ(c, hand[0], hand[1], L['limb'] * 0.9 * s, '#141416')


def _body(c, W, hip, sh, tilt):
    look, s, o, ink, ow, seg = W['look'], W['s'], W['o'], W['ink'], W['ow'], W['seg']
    tw_ = seg['torso_w'] * s
    ln = seg['torso'] * s
    c.save()
    c.translate(*hip)
    c.rotate(tilt)
    if look == 'whatif':
        col = o['top']
        rrect(c, -tw_ * 0.44, -10 * s, tw_ * 0.88, 34 * s, 12 * s, '#0C0C10')
        rrect(c, -tw_ * 0.44 + 2.5 * s, -10 * s + 2.5 * s, tw_ * 0.88 - 5 * s, 34 * s - 5 * s, 10 * s, o['bottom'])
        q = skia.Path()
        q.moveTo(-tw_ * 0.42, 8 * s)
        q.lineTo(-tw_ * 0.5, -ln + 22 * s)
        q.quadTo(-tw_ * 0.5, -ln - 4 * s, -tw_ * 0.3, -ln - 4 * s)
        q.lineTo(tw_ * 0.3, -ln - 4 * s)
        q.quadTo(tw_ * 0.5, -ln - 4 * s, tw_ * 0.5, -ln + 22 * s)
        q.lineTo(tw_ * 0.42, 8 * s)
        q.close()
        _fill(c, q, col, '#0C0C10', 2.5 * s, shader=_side_grad(-tw_ / 2, tw_ / 2, col, 0.18))
        line(c, -tw_ * 0.4, 0, tw_ * 0.4, 0, dk(col, 0.25), w=5 * s)
        q = skia.Path()
        q.moveTo(-13 * s, -ln - 3 * s)
        q.quadTo(0, -ln + 14 * s, 13 * s, -ln - 3 * s)
        c.drawPath(q, P(dk(col, 0.3), sw=4 * s))
    elif look == 'palace':
        col = o['top']
        bot = seg['thigh'] * 0.95 * s
        q = skia.Path()
        q.moveTo(-tw_ * 0.62, bot)
        q.lineTo(-tw_ * 0.5, -ln + 30 * s)
        q.quadTo(-tw_ * 0.5, -ln - 6 * s, -tw_ * 0.22, -ln - 6 * s)
        q.lineTo(tw_ * 0.22, -ln - 6 * s)
        q.quadTo(tw_ * 0.5, -ln - 6 * s, tw_ * 0.5, -ln + 30 * s)
        q.lineTo(tw_ * 0.62, bot)
        q.close()
        _fill(c, q, col, ink, ow, shader=_side_grad(-tw_ * 0.6, tw_ * 0.6, col, 0.2))
        c.save()
        c.clipPath(q, skia.ClipOp.kIntersect, True)
        if o.get('robe', True):
            sq = _path([(-tw_ * 0.55, -ln + 4 * s), (-tw_ * 0.3, -ln - 8 * s), (tw_ * 0.62, bot - 10 * s),
                        (tw_ * 0.3, bot + 10 * s)], True)
            c.drawPath(sq, P(o['trim']))
            c.drawPath(sq, P(ink, sw=ow))
            c.drawRect(skia.Rect.MakeXYWH(-tw_, bot - 16 * s, 2 * tw_, 20 * s), P(o['trim']))
        else:
            c.drawRect(skia.Rect.MakeXYWH(-tw_, -14 * s, 2 * tw_, 18 * s), P(o.get('trim', '#3B2A22')))
        c.restore()
        c.drawPath(q, P(ink, sw=ow * 2))
    elif look == 'castle':
        col = o['top']
        bot = 28 * s
        q = _rr(-tw_ / 2, -ln - 4 * s, tw_, ln + bot + 4 * s, tw_ * 0.32)
        _fill(c, q, col, ink, ow, shader=_side_grad(-tw_ / 2, tw_ / 2, col, 0.26))
        c.save()
        c.clipPath(q, skia.ClipOp.kIntersect, True)
        if o.get('trim') and o.get('stripe', True):
            c.drawRect(skia.Rect.MakeXYWH(tw_ * 0.12, -ln - 10 * s, tw_ * 0.14, ln + bot + 20 * s), P(o['trim']))
        yy = -ln + 18 * s
        while yy < bot - 8 * s:
            line(c, -tw_ * 0.12, yy, -tw_ * 0.12, yy + 9 * s, lt(col, 0.4), w=2.5 * s)
            yy += 17 * s
        c.restore()
    elif look == 'desert':
        col = o['top']
        bot = seg['thigh'] * 0.6 * s
        q = skia.Path()
        q.moveTo(-tw_ * 0.62, bot)
        q.lineTo(-tw_ * 0.5, -ln + 14 * s)
        q.quadTo(-tw_ * 0.5, -ln - 3 * s, -tw_ * 0.25, -ln - 3 * s)
        q.lineTo(tw_ * 0.25, -ln - 3 * s)
        q.quadTo(tw_ * 0.5, -ln - 3 * s, tw_ * 0.5, -ln + 14 * s)
        q.lineTo(tw_ * 0.62, bot)
        q.close()
        _fill(c, q, col, ink, ow, shader=_side_grad(-tw_ * 0.6, tw_ * 0.6, col, 0.2))
        rrect(c, -tw_ * 0.56, -8 * s, tw_ * 1.12, 12 * s, 5 * s, ink)
        rrect(c, -tw_ * 0.56 + ow * 0.6, -8 * s + ow * 0.6, tw_ * 1.12 - ow * 1.2, 12 * s - ow * 1.2, 4 * s, o['trim'])
    elif look == 'pill':
        col = o['top']
        bot = 22 * s
        q = _rr(-tw_ / 2, -ln - 10 * s, tw_, ln + bot + 10 * s, tw_ / 2)
        _fill(c, q, col, ink, ow, shader=_side_grad(-tw_ / 2, tw_ / 2, col, 0.24))
        for k in range(3):
            yy = -ln + 60 * s + k * 34 * s
            circ(c, 0, yy, 6.5 * s, ink)
            circ(c, 0, yy, 4.5 * s, '#F4F4F0')
    c.restore()
