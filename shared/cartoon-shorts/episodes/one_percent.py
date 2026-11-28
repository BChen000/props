"""1% BETTER. - a numbers explainer: 1.01^365 = 37.8 and 0.99^365 = 0.03, drawn as two curves. He climbs the gold one;
the shadow rides him down the red one. Zoomed in on day 10 they look the same; zoomed out to day 365 they don't."""
import math

import numpy as np
import skia

from motivation import (kit, hu, music, W, H, R, P, rect, rrect, line, circ, oval, glow, grect, poly, ease, eout, ramp,
                        clamp, mix, text, tw, spaced, dust, noise_hit, wind, thump, piano, riser, put, SR, env, TEXT_ON)

NAME = 'one_percent'
RED = '#FF3B3B'
GOLD = '#FFC93C'
X0, X1, YB, YTOP, YLOW = 150, 930, 1240, 400, 1560
FULL = (365.0, 22.0, 300.0)
ZOOM = (10.0, 140 / (1.01 ** 10 - 1), 140 / (1 - 0.99 ** 10))

SCRIPT = [
    dict(scene='up', v='nar', text='Get 1% better | every day.', key=['better'], pre=0.5),
    dict(scene='up', v='nar', text='For one year.', key=['year'], pre=0.1),
    dict(scene='up', v='nar', text="And you're | 37 times | better.", key=['37'], pre=0.9),
    dict(scene='down', v='nar', text='Get 1% worse | every day.', key=['worse'], pre=0.6),
    dict(scene='down', v='nar', text="And you're | almost | nothing.", key=['nothing'], pre=1.0),
    dict(scene='tiny', v='nar', text='One day, | the difference | is tiny.', key=['tiny'], pre=0.6),
    dict(scene='year', v='nar', text="A year later, | it's | everything.", key=['everything'], pre=1.2),
    dict(scene='end', v='nar', text='Start | at 1%.', key=['1%'], pre=0.6),
    dict(scene='end', text='1% today.', dur=2.4, style='word', pre=0.3, pos=(540, 760)),
]


# ---------------------------------------------------------------- the graph
def view_lerp(a, b, u):
    u = ease(clamp(u))
    return tuple(math.exp(math.log(p) + (math.log(q) - math.log(p)) * u) for p, q in zip(a, b))


def gx(d, view):
    return X0 + (X1 - X0) * d / view[0]


def gy(v, view, up):
    return YB - (v - 1) * view[1] if up else YB + (1 - v) * view[2]


def board(c, t):
    grect(c, -500, -500, W + 1000, H + 1000, ['#141938', '#0A0C1E'])
    for k in range(-6, 20):
        line(c, -500, k * 100, W + 500, k * 100, '#FFFFFF', w=1, a=0.04, cap='butt')
        line(c, k * 100, -500, k * 100, H + 500, '#FFFFFF', w=1, a=0.04, cap='butt')
    dust(c, t, (0, 300, W, 1700), cl='#C9D3FF', a=0.3, seed=41, n=30)


def axes(c, view):
    for k in range(int((X1 - X0) / 30)):
        xx = X0 + k * 30
        line(c, xx, YB, xx + 14, YB, '#FFFFFF', w=3, a=0.35, cap='butt')
    line(c, X0, YTOP - 20, X0, YLOW + 20, '#FFFFFF', w=3, a=0.35, cap='butt')
    if TEXT_ON[0]:
        text(c, '×1', X0 - 60, YB + 14, 36, '#FFFFFF', 0.6, tf='pop')
        text(c, 'DAY 0', X0, YLOW + 80, 34, '#FFFFFF', 0.5, tf='pop')
        text(c, f'DAY {int(round(view[0]))}', X1, YLOW + 80, 34, '#FFFFFF', 0.5, tf='pop')


def curve(c, view, D, up, a=1.0):
    """The 1.01^d (up) or 0.99^d curve from day 0 to D; returns its tip and value."""
    D = max(0.0, min(D, view[0]))
    n = 160
    pts = []
    for i in range(n + 1):
        d = D * i / n
        v = 1.01 ** d if up else 0.99 ** d
        pts.append((gx(d, view), max(YTOP - 40, min(YLOW + 40, gy(v, view, up)))))
    cl = GOLD if up else RED
    pp = kit.path(pts) if False else _pl(pts)
    c.drawPath(pp, P(cl, 0.35 * a, sw=24, blur=12))
    c.drawPath(pp, P(cl, a, sw=9))
    v = 1.01 ** D if up else 0.99 ** D
    return pts[-1], v


def _pl(pts):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    return p


def tip_label(c, tip, v, up, a=1.0):
    if not TEXT_ON[0] or a <= 0:
        return
    s = f'×{v:.1f}' if up else f'×{v:.2f}'
    x, y = tip
    x = min(x, X1 - 10)
    text(c, s, x - 120, y + 16 if up else y - 60, 48, GOLD if up else RED, a, tf='pop')


def power(c, base, ex, rhs, x, y, size, a, rhs_col):
    """Draws base^ex = rhs centred on x, y (the middle of the line)."""
    if not TEXT_ON[0] or a <= 0:
        return
    f, fs = kit.font('pop', size), kit.font('pop', size * 0.5)
    parts = [(base, f, 0.0, '#FFFFFF'), (ex, fs, -size * 0.42, '#FFFFFF'), ('  =  ', f, 0.0, '#FFFFFF'), (rhs, f, 0.0, rhs_col)]
    total = sum(fn.measureText(s) for s, fn, _, _ in parts)
    xx, by = x - total / 2, y + size * 0.36
    sc = 0.85 + 0.15 * eout(clamp(a * 3))
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    c.translate(-x, -y)
    for s, fn, dy, cl in parts:
        c.drawString(s, xx + 3, by + dy + 6, fn, P('#000000', 0.5 * a, blur=8))
        if cl != '#FFFFFF':
            c.drawString(s, xx, by + dy, fn, P(cl, 0.5 * a, blur=size * 0.15))
        c.drawString(s, xx, by + dy, fn, P(cl, a))
        xx += fn.measureText(s)
    c.restore()


def climber(c, tip, t, s=0.5):
    hu.light(dir=(0.0, -1.0), lit='#FFF6E8', shade='#9A97C0', rim=GOLD, rim_a=0.4, glow=0.12)
    p = 2 * math.pi * 1.3 * t
    hu.figure(c, tip[0] - 6, tip[1] + 2, s, hu.walk(p, amp=24), brows=0.7, ground_shadow=0)


def dragged(c, tip, t, s=0.5):
    hu.light(dir=(0.0, -1.0), lit='#E6E4F2', shade='#8A88AE', rim=RED, rim_a=0.4, glow=0.06)
    p = 2 * math.pi * 0.7 * t
    j = hu.figure(c, tip[0] - 6, tip[1] + 2, s, hu.walk(p, amp=14, droop=1.0), expr='tired', look=(0.4, 0.7), ground_shadow=0)
    shx, shy = j['shoulder']
    hdx, hdy = j['head']
    sp = dict(torso=18.0, head=26.0, ll=(72.0, 12.0), rl=(60.0, 4.0),
              la=('ik', (hdx + 46 * s / 0.74, hdy + 18 * s / 0.74), 1), ra=('ik', (hdx + 58 * s / 0.74, hdy + 40 * s / 0.74), 1))
    js = hu.figure(c, shx - 80 * s, 0, 0.74 * s, sp, hip_y=shy - 24 * s, scheme='shadow', ground_shadow=0, glow_a=0.4)
    hu.wisps(c, js, t, 0.74 * s, a=0.6, n=8)


def day_label(D):
    return lambda t, x: f'DAY {int(D(t, x))}'


# ---------------------------------------------------------------- scenes
def up_D(t, x):
    return 365 * clamp((t - x.T[0] + 0.1) / max(x.E[1] - x.T[0] + 0.1, 0.5)) ** 1.0


def sc_up(c, t, x):
    board(c, t)
    axes(c, FULL)
    tip, v = curve(c, FULL, up_D(t, x), True)
    glow(c, tip[0], tip[1], 160, GOLD, 0.35)
    climber(c, tip, t)
    tip_label(c, tip, v, True)
    power(c, '1.01', '365', '37.8', 470, 720, 92, ramp(t, x.E[1] + 0.25, 0.3), GOLD)


def down_D(t, x):
    return 365 * clamp((t - x.T[0] + 0.1) / max(x.E[0] + 0.6 - x.T[0] + 0.1, 0.5))


def sc_down(c, t, x):
    board(c, t)
    axes(c, FULL)
    line(c, X0, YLOW - 26, X1, YLOW - 26, RED, w=2, a=0.25, cap='butt')
    tip, v = curve(c, FULL, down_D(t, x), False)
    glow(c, tip[0], tip[1], 160, RED, 0.3)
    dragged(c, tip, t)
    tip_label(c, tip, v, False)
    power(c, '0.99', '365', '0.03', 540, 800, 92, ramp(t, x.E[0] + 0.7, 0.3), RED)


def sc_tiny(c, t, x):
    board(c, t)
    axes(c, ZOOM)
    D = 10 * ease(clamp(t / 0.9))
    tu, vu = curve(c, ZOOM, D, True)
    td, vd = curve(c, ZOOM, D, False)
    climber(c, tu, t)
    dragged(c, td, t)
    tip_label(c, tu, vu, True)
    tip_label(c, td, vd, False)


def sc_year(c, t, x):
    board(c, t)
    u = ramp(t, 0.15, 1.4)
    view = view_lerp(ZOOM, FULL, u)
    axes(c, view)
    tu, vu = curve(c, view, view[0], True)
    td, vd = curve(c, view, view[0], False)
    glow(c, tu[0], tu[1], 200, GOLD, 0.4 * u)
    hu.light(dir=(0.0, -1.0), lit='#FFF6E8', shade='#9A97C0', rim=GOLD, rim_a=0.4, glow=0.14)
    pose = hu.lerp_pose(hu.stand(), dict(hu.arms_up(), head=-16.0), ramp(t, 1.4, 0.4))
    hu.figure(c, tu[0] - 6, tu[1] + 2, 0.5, pose, expr='smile', brows=0.3, look=(0.0, -0.4), ground_shadow=0)
    dragged(c, td, t)
    tip_label(c, tu, vu, True, ramp(t, 1.4, 0.3))
    tip_label(c, td, vd, False, ramp(t, 1.4, 0.3))
    if TEXT_ON[0]:
        gap = ramp(t, 1.6, 0.5)
        if gap > 0:
            line(c, X1 + 40, tu[1], X1 + 40, td[1], '#FFFFFF', w=3, a=0.5 * gap)


def sc_end(c, t, x):
    board(c, t)
    axes(c, FULL)
    D = 14 * ease(ramp(t, x.T[0] + 0.3, 2.5))
    tip, v = curve(c, FULL, D, True)
    glow(c, tip[0], tip[1], 160, GOLD, 0.35)
    climber(c, tip, t, 0.62)


SCENES = {
    'up': dict(draw=sc_up, cam=(1.0, 1.04, 540, 1000), cap_y=340, vig=0.6, day=day_label(up_D)),
    'down': dict(draw=sc_down, cam=(1.0, 1.04, 540, 1200), cap_y=340, vig=0.6, day=day_label(down_D)),
    'tiny': dict(draw=sc_tiny, cam=(1.0, 1.0, 540, 1240), cap_y=340, vig=0.6, day=10),
    'year': dict(draw=sc_year, cam=(1.0, 1.0, 540, 960), cap_y=340, vig=0.6, day=365),
    'end': dict(draw=sc_end, cam=(1.0, 1.08, 300, 1240), cap_y=340, vig=0.6, day=1),
}

SCORE = dict(root=52.0, dark_notes=[64, 71, 67, 64, 71, 69], dark_every=1.2, turn='tiny', title='year', end='end',
             bpm=120, chords=[(52, 55, 59), (48, 52, 55), (55, 59, 62), (50, 54, 57)], end_chord=[52, 55, 59, 64],
             end_melody=[76, 71, 67], duck=0.6)


def tone(f0, f1, dur, a=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.05, dur * 0.4) * a


def ding(m=84):
    return piano(m, 1.6, 0.9) + piano(m + 7, 1.6, 0.6) * 0.5


def SFX(tl, spans, rng):
    out = []
    L = lambda name: [ln for ln in tl['lines'] if ln['scene'] == name]
    up, dn = spans['up'], spans['down']
    lu, ld = L('up'), L('down')
    t0, t1 = lu[0]['start'], lu[1]['end']
    out.append((t0, tone(220, 880, t1 - t0 + 0.2), 0.5))
    out.append((lu[1]['end'] + 0.25, ding(), 0.5))
    t0, t1 = ld[0]['start'], ld[0]['end'] + 0.6
    out.append((t0, tone(440, 110, t1 - t0 + 0.2), 0.5))
    out.append((ld[0]['end'] + 0.7, ding(72), 0.45))
    for name in ('down', 'tiny', 'year', 'end'):
        out.append((spans[name]['start'] - 0.3, music.sfx('whoosh'), 0.3))
    return out


def THUMB_T(tl):
    y = [ln for ln in tl['lines'] if ln['scene'] == 'year']
    return y[0]['end'] + 0.3
