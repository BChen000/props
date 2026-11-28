"""stickman-style: a bare black stick figure and a detailed island world, drawn with skia-python at 1080x1920.

  stick(c, x, ground, s, pose, ...)  the figure: feet on `ground`, hips placed so the lowest foot touches it
  poses: stand(), walk(phase), shrug(), push(t), crouch(t), wave(t), salute()  -> dicts of joint angles
  sky / sea / island / palm / campfire / ship / fin  the world, in a few times of day (settings.TOD)

Angles are in degrees in screen space: 0 points straight down, +90 to the right, 180 up. A pose faces right;
flip=True mirrors it. Drawing helpers (P, line, circ, glow, ease, ...) come from ../../kids-songs/storytime-kit.
"""
import math
import os
import sys

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kids-songs', 'storytime-kit'))
sys.path.insert(0, HERE)
from storytime_kit import (W, H, P, R, rect, circ, oval, line, path, poly, grect, glow, ease, eout, ramp, clamp,  # noqa: E402
                           mix, lgrad, rgrad)
from settings import STICK as S_, HORIZON, GROUND, ISLAND as IS, TOD  # noqa: E402


# ---------------------------------------------------------------- the figure
def _d(a):
    r = math.radians(a)
    return math.sin(r), math.cos(r)


def lerp_pose(a, b, u):
    u = clamp(u)
    out = {}
    for k in a:
        va, vb = a[k], b.get(k, a[k])
        out[k] = tuple(x + (y - x) * u for x, y in zip(va, vb)) if isinstance(va, tuple) else va + (vb - va) * u
    return out


def stand():
    return dict(torso=0.0, head=0.0, la=(-8.0, -4.0), ra=(8.0, 4.0), ll=(-5.0, -3.0), rl=(5.0, 3.0))


def walk(p, amp=26.0):
    lt, rt = amp * math.sin(p), -amp * math.sin(p)
    return dict(torso=6.0, head=-4.0,
                la=(-22 * math.sin(p), -22 * math.sin(p) + 22), ra=(22 * math.sin(p), 22 * math.sin(p) + 22),
                ll=(lt, lt - 42 * max(0.0, math.cos(p))), rl=(rt, rt - 42 * max(0.0, -math.cos(p))))


def shrug():
    return dict(torso=0.0, head=9.0, la=(-36.0, -104.0), ra=(36.0, 104.0), ll=(-7.0, -4.0), rl=(7.0, 4.0))


def push(t, shake=1.0):
    o = 9 * math.sin(2 * math.pi * 6 * t) * shake
    return dict(torso=14.0, head=-6.0, la=(118.0 + o, 128.0 + o), ra=(108.0 + o, 120.0 + o), ll=(24.0, 8.0), rl=(-30.0, -14.0))


def crouch(t, rub=1.0):
    o = 16 * math.sin(2 * math.pi * 7 * t) * rub
    return dict(torso=38.0, head=-14.0, la=(64.0 + o, 96.0 + o), ra=(56.0 - o, 104.0 - o), ll=(78.0, -12.0), rl=(20.0, -80.0))


def wave(t):
    a, b = math.sin(2 * math.pi * 2.6 * t), math.sin(2 * math.pi * 2.6 * t + 1.2)
    return dict(torso=0.0, head=-10.0, la=(-128.0 + 18 * a, -140.0 + 26 * b), ra=(128.0 - 18 * a, 140.0 - 26 * b),
                ll=(-9.0, -5.0), rl=(9.0, 5.0))


def salute():
    return dict(torso=4.0, head=-6.0, la=(-10.0, -6.0), ra=(120.0, -114.0), ll=(-6.0, -3.0), rl=(8.0, 3.0))


def stick(c, x, ground, s=1.0, pose=None, flip=False, lift=0.0, cl=None, hold=None, shadow=0.35):
    """Draws the figure; returns its joints (screen coordinates) for attaching props. hold(c, hand_l, hand_r)."""
    p = pose or stand()
    f = -1.0 if flip else 1.0
    cl = cl or S_['color']
    w = S_['width'] * s

    def d(a, ln):
        dx, dy = _d(a)
        return f * dx * ln * s, dy * ln * s

    low = max(math.cos(math.radians(p[k][0])) * S_['thigh'] + math.cos(math.radians(p[k][1])) * S_['shin'] for k in ('ll', 'rl'))
    hip = (x, ground - low * s - lift)
    up = 180 - p['torso']
    dx, dy = d(up, S_['torso'])
    sh = (hip[0] + dx, hip[1] + dy)
    dx, dy = d(up - p['head'], S_['neck'])
    nk = (sh[0] + dx, sh[1] + dy)
    dx, dy = d(up - p['head'], S_['head'])
    hd = (nk[0] + dx, nk[1] + dy)
    if shadow:
        oval(c, x, ground + 4 * s, 70 * s, 11 * s, '#000000', shadow * (1 - clamp(lift / (160 * s))), blur=6 * s)
    joints = {}
    for k, root, (l1, l2) in (('ll', hip, ('thigh', 'shin')), ('rl', hip, ('thigh', 'shin')),
                              ('la', sh, ('upper', 'fore')), ('ra', sh, ('upper', 'fore'))):
        a1, a2 = p[k]
        dx, dy = d(a1, S_[l1])
        mid = (root[0] + dx, root[1] + dy)
        dx, dy = d(a2, S_[l2])
        end = (mid[0] + dx, mid[1] + dy)
        pp = skia.Path()
        pp.moveTo(*root)
        pp.lineTo(*mid)
        pp.lineTo(*end)
        c.drawPath(pp, P(cl, sw=w))
        joints[k] = (mid, end)
    line(c, hip[0], hip[1], sh[0], sh[1], cl, w=w)
    line(c, sh[0], sh[1], nk[0], nk[1], cl, w=w)
    circ(c, hd[0], hd[1], S_['head'] * s, cl)
    joints.update(hip=hip, shoulder=sh, head=hd)
    if hold:
        hold(c, joints['la'][1], joints['ra'][1])
    return joints


# ---------------------------------------------------------------- the world
def sky(c, tod, t):
    T = TOD[tod]
    grect(c, -500, -600, W + 1000, HORIZON + 600, T['sky'], [0, 0.42, 0.8, 1][:len(T['sky'])] if len(T['sky']) == 4 else None)
    kind, colr, bx, by, br = T['body']
    if kind == 'moon':
        rng = np.random.default_rng(5)
        for _ in range(110):
            sx, sy = rng.random() * 1600 - 260, rng.random() * (HORIZON - 120) - 100
            tw_ = 0.5 + 0.5 * math.sin(t * (1.5 + rng.random() * 3) + rng.random() * 6)
            circ(c, sx, sy, 1.2 + rng.random() * 2.4, '#FFFFFF', 0.25 + 0.6 * tw_ * (1 - sy / HORIZON))
        glow(c, bx, by, br * 5, colr, 0.22)
        circ(c, bx, by, br, colr)
        circ(c, bx - 14, by - 10, br * 0.25, '#C9D2DE', 0.5)
        circ(c, bx + 16, by + 14, br * 0.16, '#C9D2DE', 0.45)
    else:
        glow(c, bx, by, br * 7, colr, 0.45 if tod == 'dawn' else 0.32)
        circ(c, bx, by, br, colr)
        rng = np.random.default_rng(8)
        for i in range(5):
            cx = (rng.random() * 1700 - 300 + t * (8 + 4 * i)) % 1900 - 400
            cy = 150 + rng.random() * (HORIZON - 420)
            ca = 0.55 if tod != 'dawn' else 0.35
            ccol = '#FFFFFF' if tod != 'dawn' else '#F3C3A6'
            for k in range(4):
                oval(c, cx + (k - 1.5) * 55, cy - (18 if k in (1, 2) else 0), 80, 34, ccol, ca, blur=10)


def sea(c, tod, t):
    T = TOD[tod]
    grect(c, -500, HORIZON, W + 1000, H + 700 - HORIZON, T['sea'])
    kind, colr, bx, by, br = T['body']
    for i in range(26):                                   # reflection column under the sun or moon
        yy = HORIZON + 8 + i * 22
        wd = (40 + i * 9) * (0.6 + 0.4 * math.sin(t * 3 + i * 1.7))
        line(c, bx - wd / 2, yy, bx + wd / 2, yy, colr, w=4 + i * 0.15, a=0.45 * (1 - i / 26))
    for i in range(16):
        y0 = HORIZON + 10 + 16 * i ** 1.45
        amp, k = 2 + i * 0.7, 0.012 - i * 0.0004
        ph = t * (0.8 + 0.07 * i) + i * 1.3
        pts = [(xx, y0 + amp * math.sin(k * xx + ph)) for xx in range(-500, W + 520, 24)]
        c.drawPath(path(pts, close=False), P('#FFFFFF', 0.06 + 0.012 * i, sw=1.5 + 0.35 * i))
    line(c, -500, HORIZON, W + 500, HORIZON, mix(T['sky'][-1], '#FFFFFF', 0.3), w=2, a=0.6)


def island(c, tod, t):
    T = TOD[tod]
    cx, cy, rx, ry = IS['cx'], IS['cy'], IS['rx'], IS['ry']
    foam = 0.5 + 0.5 * math.sin(2 * math.pi * 0.35 * t)
    oval(c, cx, cy + 22, rx + 70 + 10 * foam, ry + 34 + 4 * foam, '#FFFFFF', 0.35 * TOD[tod]['light'] + 0.05)
    oval(c, cx, cy + 18, rx + 50, ry + 26, T['wet'])
    oval(c, cx, cy + 8, rx + 12, ry + 10, mix(T['sand'], T['wet'], 0.5))
    oval(c, cx, cy, rx, ry, T['sand'])
    oval(c, cx - 60, cy - 18, rx * 0.72, ry * 0.5, mix(T['sand'], '#FFFFFF', 0.18), 0.6, blur=14)
    rng = np.random.default_rng(2)
    for _ in range(40):
        a, r = rng.random() * 2 * math.pi, rng.random() ** 0.5
        circ(c, cx + math.cos(a) * rx * 0.9 * r, cy + math.sin(a) * ry * 0.8 * r, 2 + rng.random() * 2, mix(T['sand'], T['wet'], 0.7), 0.6)


def palm(c, x, y, s=1.0, t=0.0, sway=0.0, tod='day', coconuts=3):
    """Base at (x, y); the trunk leans left. Returns the crown point. sway: degrees about the base."""
    dark = 1 - TOD[tod]['light']
    trunk, leaf, rib = mix('#8B6A47', '#1A1C28', dark * 0.8), mix('#2F8150', '#0E1C22', dark * 0.85), mix('#1E5A36', '#0A141A', dark * 0.85)
    c.save()
    c.rotate(sway, x, y)
    pts_l, pts_r, n = [], [], 12
    top = (x - 70 * s, y - 560 * s)
    for i in range(n + 1):
        u = i / n
        px = x + (top[0] - x) * u - 40 * s * math.sin(math.pi * u)
        py = y + (top[1] - y) * u
        wd = (24 - 11 * u) * s
        pts_l.append((px - wd, py))
        pts_r.append((px + wd, py))
    poly(c, pts_l + pts_r[::-1], trunk)
    for i in range(1, n):
        (lx, ly), (rx_, ry_) = pts_l[i], pts_r[i]
        line(c, lx, ly, rx_, ry_ + 6 * s, mix(trunk, '#000000', 0.3), w=3 * s)
    for k in range(coconuts):
        circ(c, top[0] - 22 * s + k * 22 * s, top[1] + 22 * s + (k % 2) * 8 * s, 19 * s, mix('#5A3A22', '#120C10', dark * 0.7))
    for ang in (-168, -140, -110, -76, -42, -12, 14):
        a = math.radians(ang + 3 * math.sin(t * 1.3 + ang))
        ln = (250 + 30 * math.cos(ang)) * s
        tip = (top[0] + math.cos(a) * ln, top[1] + math.sin(a) * ln * 0.55 + 150 * s)
        mid = (top[0] + math.cos(a) * ln * 0.5, top[1] + math.sin(a) * ln * 0.35 - 30 * s)
        nx, ny = -math.sin(a), math.cos(a)
        wd = 34 * s
        pp = skia.Path()
        pp.moveTo(*top)
        pp.quadTo(mid[0] + nx * wd, mid[1] + ny * wd, *tip)
        pp.quadTo(mid[0] - nx * wd * 0.4, mid[1] - ny * wd * 0.4 + 18 * s, *top)
        pp.close()
        c.drawPath(pp, P(leaf))
        q = skia.Path()
        q.moveTo(*top)
        q.quadTo(mid[0], mid[1] + 6 * s, *tip)
        c.drawPath(q, P(rib, sw=4 * s))
    c.restore()
    return top


def campfire(c, x, y, t, fire=1.0, smoke=0.0, s=1.0):
    for k in range(7):
        a = math.pi * (0.1 + 0.8 * k / 6)
        oval(c, x + math.cos(a) * 62 * s, y + 6 * s - math.sin(a) * 8 * s, 16 * s, 10 * s, '#6B6B72')
    line(c, x - 55 * s, y + 4 * s, x + 50 * s, y - 14 * s, '#5B3A22', w=16 * s)
    line(c, x - 50 * s, y - 14 * s, x + 55 * s, y + 4 * s, '#4A2E1B', w=16 * s)
    if fire > 0:
        glow(c, x, y - 40 * s, 520 * s * fire, '#FF8A3A', 0.38 * fire)
        for k, (colr, hh, ww) in enumerate((('#E2512A', 150, 58), ('#F39A2C', 110, 42), ('#FFE07A', 66, 24))):
            h_ = hh * s * fire * (1 + 0.12 * math.sin(t * 17 + k * 2) + 0.08 * math.sin(t * 29 + k))
            sw_ = 10 * s * math.sin(t * 9 + k)
            pp = skia.Path()
            pp.moveTo(x - ww * s * fire, y)
            pp.cubicTo(x - ww * s * fire, y - h_ * 0.5, x + sw_ - 6 * s, y - h_ * 0.7, x + sw_, y - h_)
            pp.cubicTo(x + sw_ + 6 * s, y - h_ * 0.7, x + ww * s * fire, y - h_ * 0.5, x + ww * s * fire, y)
            pp.close()
            c.drawPath(pp, P(colr, 0.95))
        rng = np.random.default_rng(4)
        for _ in range(16):
            ph = (t * (0.6 + rng.random() * 0.8) + rng.random()) % 1.0
            sx = x + (rng.random() - 0.5) * 70 * s + 30 * s * math.sin(ph * 6 + rng.random() * 6)
            sy = y - 60 * s - ph * 320 * s
            circ(c, sx, sy, 3.5 * s * (1 - ph), '#FFD27A', fire * (1 - ph))
    if smoke > 0:
        for i in range(14):
            ph = (t * 0.25 + i / 14) % 1.0
            sx = x + 40 * s * math.sin(ph * 5 + i) + ph * 60 * s
            sy = y - 30 * s - ph * 640 * s
            circ(c, sx, sy, (18 + 60 * ph) * s, '#D9DCE0', 0.28 * smoke * (1 - ph), blur=8 * s)


def ship(c, x, y, s=1.0, a=1.0):
    """A small sailing ship on the horizon line y."""
    if a <= 0:
        return
    poly(c, [(x - 70 * s, y - 8 * s), (x + 76 * s, y - 8 * s), (x + 56 * s, y + 10 * s), (x - 56 * s, y + 10 * s)], '#2B3036', a)
    for mx_, mh in ((-20, 92), (24, 108)):
        line(c, x + mx_ * s, y - 8 * s, x + mx_ * s, y - mh * s, '#2B3036', w=4 * s, a=a)
        poly(c, [(x + (mx_ - 30) * s, y - (mh - 10) * s), (x + (mx_ + 30) * s, y - (mh - 14) * s),
                 (x + (mx_ + 34) * s, y - 30 * s), (x + (mx_ - 34) * s, y - 26 * s)], '#ECE6D8', a)
    poly(c, [(x + 24 * s, y - 108 * s), (x + 50 * s, y - 102 * s), (x + 24 * s, y - 96 * s)], '#C0392B', a)


def fin(c, x, y, t, s=1.0, a=1.0, dirn=1):
    """A shark fin cutting the water line y, moving in dirn (+1 right)."""
    if a <= 0:
        return
    bob = 4 * s * math.sin(t * 5)
    for k in range(4):
        wx = x - dirn * (40 + 46 * k) * s
        line(c, wx - 26 * s, y + (3 + 3 * k) * s, wx + 26 * s, y + (3 + 3 * k) * s, '#FFFFFF', w=(5 - k) * s, a=a * (0.7 - 0.15 * k))
    pp = skia.Path()
    pp.moveTo(x - dirn * 44 * s, y + bob)
    pp.quadTo(x - dirn * 8 * s, y - 48 * s + bob, x + dirn * 14 * s, y - 92 * s + bob)
    pp.quadTo(x + dirn * 20 * s, y - 40 * s + bob, x + dirn * 42 * s, y + bob)
    pp.close()
    c.drawPath(pp, P('#56636E', a))
    c.drawPath(pp, P('#8A98A3', a * 0.7, sw=3 * s))
    oval(c, x, y + 6 * s + bob, 56 * s, 8 * s, '#FFFFFF', 0.5 * a)


def coconut(c, x, y, s=1.0, rot=0.0):
    circ(c, x, y, 19 * s, '#5A3A22')
    circ(c, x - 6 * s, y - 6 * s, 6 * s, '#7A5232', 0.6)
