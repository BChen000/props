"""5 MORE MINUTES. - the 5 a.m. alarm and the shadow's excuses, the years they cost, the morning he says no, then the
first 100 days: running, studying, push-ups, the heavy bag, up before the alarm, the summit."""
import math

import numpy as np

from motivation import (kit, hu, music, W, H, R, P, rect, rrect, line, circ, oval, glow, grect, poly, ease, eout, ramp,
                        clamp, mix, text, room, beam, dust, window, poster, hanging_lamp, bed, blanket, sleeper, nightstand,
                        sky, ridge, city, houses, trees, streetlamp, tear_calendar, grr, desk, desk_lamp, books, open_book,
                        chair, punching_bag, desk_room, desk_shadow, seated, BOOK, season_window, cobweb, beep, thump, noise_hit, wind, put, SR, env,
                        NIGHT, WARM, DUSK, DAWN)

NAME = 'five_more_minutes'
RED = '#FF3B3B'

SCRIPT = [
    dict(scene='bed', v='sha', text='just five more minutes...', pre=1.7, pos=(640, 790)),
    dict(scene='bed', v='sha', text="you're tired.", pos=(640, 790)),
    dict(scene='bed', v='sha', text='start tomorrow.', pos=(640, 790)),
    dict(scene='bed', v='nar', text='Every morning, | the same voice.', key=['voice'], pre=0.2),
    dict(scene='bed', v='nar', text='And every morning, | you listen.', key=['listen']),
    dict(scene='seasons', v='nar', text='Five minutes | become | hours.', key=['hours'], pre=0.5),
    dict(scene='seasons', v='nar', text='Hours | become | years.', key=['years'], pre=0.1),
    dict(scene='desk_fail', v='sha', text='do it later.', pre=0.6, pos=(560, 830)),
    dict(scene='desk_fail', v='nar', text='It talks you | out of | everything.', key=['everything'], pre=0.15),
    dict(scene='wake', v='nar', text='Until | one day...', key=['one', 'day'], pre=0.5),
    dict(scene='wake', text='no.', dur=1.5, style='no', pos=(540, 560)),
    dict(scene='day1', text='DAY 1', dur=1.3, style='title', pos=(540, 900)),
    dict(scene='run', v='nar', text="It won't | feel good.", key=['good'], pre=0.35),
    dict(scene='study', v='nar', text="It won't | make sense.", key=['sense'], pre=0.35),
    dict(scene='study', v='sha', text="you're not smart enough.", pos=(560, 830)),
    dict(scene='pushup', v='nar', text="It won't | be fast.", key=['fast'], pre=0.5),
    dict(scene='pushup', v='sha', text='just quit.', pos=(800, 820)),
    dict(scene='pushup', v='nar', text='Do it | anyway.', key=['anyway']),
    dict(scene='boxing', text=' ', dur=0.9, style='none', pre=0.3),
    dict(scene='boxing', v='sha', text="you'll never change.", pre=0.2, pos=(700, 700)),
    dict(scene='boxing', v='nar', text='Every hit | proves it | wrong.', key=['wrong']),
    dict(scene='early', v='nar', text="Now you're up | before | the alarm.", key=['before'], pre=0.6),
    dict(scene='calendar', v='nar', text='One day | at a time.', key=['one', 'day'], pre=0.4),
    dict(scene='summit', v='nar', text='The voice | never leaves.', key=['never'], pre=0.7),
    dict(scene='summit', v='nar', text='You just | stop listening.', key=['stop']),
    dict(scene='summit', text='not today.', dur=2.6, style='word', pre=0.3, pos=(540, 620)),
]


# ---------------------------------------------------------------- 5:00 a.m.
def bedroom(c, t, sky_pal=NIGHT, moon=(0.68, 0.3), stars=22, clock='5:00', ring=0.0, beam_a=0.13):
    room(c, NIGHT, 1600)
    window(c, 60, 380, 300, 400, sky_pal, t, moon=moon, stars=stars)
    poster(c, 780, 470, 190, 240, NIGHT)
    beam(c, [(80, 400), (360, 400), (960, 1600), (360, 1600)], NIGHT['beam'], beam_a)
    nightstand(c, 86, 1600, NIGHT, clock=clock, ring=ring, t=t, w=180, h=230)


def sc_bed(c, t, x):
    bedroom(c, t, ring=1.0 if t < x.T[0] - 0.25 else 0.0)
    dust(c, t, (100, 420, 960, 1560), cl=NIGHT['dust'], a=0.45, seed=2)
    rise = ease((t - (x.T[0] - 1.1)) / 1.2)
    al = clamp(rise * 1.4) * (1 - 0.35 * ease((t - x.T[4]) / 1.0))
    s = 1.45 * (1 + 0.03 * ramp(t, x.T[1], 0.5) + 0.03 * ramp(t, x.T[2], 0.5))
    if rise > 0:
        glow(c, 720, 1150, 620, RED, 0.17 * al)
        c.save()
        c.clipRect(R(-500, -500, W + 1000, 2050))
        pose = dict(torso=30.0, head=18.0, la=(24.0, 60.0), ra=('ik', (560 + 8 * math.sin(1.7 * t), 1280), -1),
                    ll=(0.0, 0.0), rl=(0.0, 0.0))
        j = hu.figure(c, 780, 1600 + 700 * (1 - rise), s, pose, flip=True, scheme='shadow', alpha=al, ground_shadow=0)
        hu.wisps(c, j, t, s, a=al)
        c.restore()
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    hu.light(dir=(-0.5, -0.86), lit=NIGHT['lit'], shade=NIGHT['shade'], rim=RED, rim_a=0.45 * al, glow=0.08)
    sleeper(c, 442, 1320, 0.95, t, expr='closed')
    blanket(c, t, NIGHT, cover=ramp(t, x.T[4] + 0.2, 0.8), x0=540, x1=1110, top=1360)


# ---------------------------------------------------------------- the years slip by
CLOCKS = ['7:42', '11:05', '2:30', '9:17', '4:48', '12:00', '6:23', '10:51', '3:36', '8:09', '1:14', '5:55']


def sc_seasons(c, t, x):
    clock = CLOCKS[int(t * 9) % len(CLOCKS)]
    room(c, NIGHT, 1600)
    poster(c, 780, 470, 190, 240, NIGHT)
    nightstand(c, 86, 1600, NIGHT, clock=clock, t=t, w=180, h=230)
    lt, day = season_window(c, 60, 380, 300, 400, t)
    beam(c, [(80, 400), (360, 400), (960, 1600), (360, 1600)], lt, 0.06 + 0.16 * day)
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    hu.light(dir=(-0.5, -0.86), lit=NIGHT['lit'], shade=NIGHT['shade'], glow=0.0)
    sleeper(c, 442, 1320, 0.95, t, expr='closed')
    blanket(c, t, NIGHT, cover=1.0, breathe=1.0, x0=540, x1=1110, top=1360)
    rect(c, -500, -500, W + 1000, H + 1000, lt, 0.08 * day)
    cobweb(c, 42, 362, ramp(t, 0.3, x.dur * 0.85))
    cobweb(c, 1038, 452, ramp(t, 1.5, x.dur * 0.7), size=120)


# ---------------------------------------------------------------- the desk, at night
def sc_desk_fail(c, t, x):
    desk_room(c, t)
    on = 1 - ramp(t, x.E[1] - 0.05, 0.12)
    u = ramp(t, x.T[1] + 0.15, 0.7)
    a = ramp(t, x.T[0] - 0.5, 0.5) * (1 - 0.6 * ramp(t, x.E[1] - 0.3, 0.4))
    desk_shadow(c, t, a)
    open_book(c, BOOK[0], BOOK[1], 0.9, cover='#3F6FB0')
    lap = (500, 1336)
    la = ('ik', (560 + (lap[0] - 560) * ease(u), 1244 + (lap[1] - 1244) * ease(u)), -1)
    ra = ('ik', (626 + (lap[0] + 26 - 626) * ease(u), 1244 + (lap[1] + 4 - 1244) * ease(u)), -1)
    pose = dict(torso=12.0 - 28.0 * ease(u), head=34.0 - 6.0 * ease(u), la=la, ra=ra, ll=(88.0, 2.0), rl=(84.0, -4.0))
    hu.light(dir=(0.9, -0.45), lit='#FFF0DA', shade=NIGHT['shade'], rim=RED, rim_a=0.35 * a, glow=0.06)
    seated(c, t, pose, expr='tired', look=(0.5, 0.9 - 0.6 * ease(u)))
    desk_lamp(c, 860, 1250, on=on)
    rect(c, -500, -500, W + 1000, H + 1000, '#05060F', 0.35 * (1 - on))


def sc_study(c, t, x):
    desk_room(c, t)
    a = ramp(t, x.T[1] - 0.35, 0.35) * (1 - ramp(t, x.E[1] + 0.25, 0.3))
    desk_shadow(c, t, a, sc=ramp(t, x.E[1] + 0.3, 0.9))
    fl = (t % 1.7) / 0.5
    open_book(c, BOOK[0], BOOK[1], 0.9, flip=fl if fl < 1 else None, cover='#3F6FB0')
    for k in range(min(5, int(t / 0.7))):
        rrect(c, 760 + 4 * k, 1236 - 6 * k, 120, 10, 3, '#FFF4E4', 0.95)
    wx = 628 + 14 * math.sin(2 * math.pi * 3.0 * t)
    pose = dict(torso=10.0, head=30.0, la=('ik', (560, 1244), -1), ra=('ik', (wx, 1240 + 3 * math.sin(2 * math.pi * 6 * t)), -1),
                ll=(88.0, 2.0), rl=(84.0, -4.0))
    hu.light(dir=(0.9, -0.45), lit='#FFF3E0', shade=NIGHT['shade'], rim=RED, rim_a=0.3 * a, glow=0.08)
    j = seated(c, t, pose, brows=0.85, look=(0.5, 0.9))
    hx, hy = j['ra'][1]
    line(c, hx + 4, hy - 4, hx + 30, hy - 40, '#E8B04A', w=6)
    desk_lamp(c, 860, 1250, on=1.0)
    dust(c, t, (480, 1000, 860, 1240), cl=WARM['dust'], a=0.5, seed=13, n=20)


# ---------------------------------------------------------------- the turn
def sc_wake(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#252A58', '#141632'])
    glow(c, 120, 300, 900, NIGHT['beam'], 0.18)
    dust(c, t, (0, 200, W, 1400), cl=NIGHT['dust'], a=0.35, seed=5)
    t_open, t_no = x.E[0] + 0.05, x.T[1]
    u = ramp(t, t_no, 0.9)
    glow(c, 610, 900, 620, RED, 0.22 * (1 - ease(u * 1.4)))
    pose = dict(hu.stand_front(), torso=-6.0, head=-8.0, la=(-24.0, -12.0), ra=(26.0, 14.0))
    j = hu.figure(c, 610, 0, 2.4, pose, view='front', hip_y=1430, legs=False, scheme='shadow', alpha=1 - ease(u * 1.6),
                  ground_shadow=0)
    hu.wisps(c, j, t, 2.4, a=1 - ease(u * 1.6))
    hu.scatter(c, j, 2.4, u)
    blink = 1 - ramp(t, t_open, 0.08)
    expr = 'closed' if blink > 0.95 else ('wide' if t < t_no else 'grit')
    hu.light(dir=(-0.7, -0.7), lit=NIGHT['lit'], shade=NIGHT['shade'], rim=RED, rim_a=0.5 * (1 - u), glow=0.1)
    hu.figure(c, 520, 0, 2.0, dict(hu.stand_front(), la=(-14.0, 18.0), ra=(14.0, -18.0)), view='front', hip_y=1760, legs=False,
              expr=expr, blink=blink, brows=ramp(t, t_no - 0.1, 0.15), look=(0.0, -0.25), ground_shadow=0)
    p = kit.path([(-500, 1620), (W + 500, 1600), (W + 500, H + 600), (-500, H + 600)])
    c.drawPath(p, P('#ffffff', shader=kit.lgrad(0, 1580, 0, 1920, list(NIGHT['blanket']))))


def sc_day1(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#0C0E22', '#121430', '#2A1F3A'], [0, 0.6, 1])
    glow(c, 540, 2000, 1000, DAWN['sun'], 0.3 * ramp(t, 0.05, 0.8))
    dust(c, t, (60, 400, 1020, 1700), cl=DAWN['sun'], a=0.4, seed=8)


# ---------------------------------------------------------------- the first hundred days
RUN_HZ = 1.45


def sc_run(c, t, x):
    sky(c, -500, 1470, DUSK['sky'], [0, 0.42, 0.78, 1])
    glow(c, 760, 1260, 760, DUSK['sun'], 0.5)
    city(c, -t * 110, 1300, DUSK['far'], DUSK['win'])
    houses(c, -t * 330, 1462, DUSK['mid'], DUSK['win'])
    trees(c, -t * 560 + 300, 1470, DUSK['near'])
    grect(c, -500, 1460, W + 1000, H + 600 - 1460, list(DUSK['ground']))
    for k in range(3):
        streetlamp(c, (k * 820 - t * 900) % 2460 - 560, 1470, DUSK)
    for i in range(12):
        xx = (i * 170 - t * 1000) % 2040 - 480
        line(c, xx, 1560, xx + 70, 1560, '#2C2950', w=6)
    for k, (yy, ln) in enumerate(((1150, 160), (1220, 230), (1290, 130))):
        xx = 330 - ((t * 900 + k * 120) % 260)
        line(c, xx - ln, yy, xx, yy, '#FFFFFF', w=5, a=0.18)
    p = 2 * math.pi * RUN_HZ * t
    hu.light(dir=(0.75, -0.66), lit=DUSK['lit'], shade=DUSK['shade'], rim='#8E86FF', rim_a=0.3, glow=0.1)
    hu.figure(c, 470, 1462, 0.95, hu.run(p), lift=16 * abs(math.sin(p)), brows=0.75, ground_shadow=0.5)
    dust(c, t, (0, 900, W, 1500), cl=DUSK['dust'], a=0.35, seed=4)


PUSH_T = 1.15


def sc_pushup(c, t, x):
    room(c, WARM, 1500)
    grr(c, 150, 1478, 640, 34, 14, WARM['mat'])
    hanging_lamp(c, 470, 640, 230, WARM, floor_y=1500)
    dust(c, t, (180, 700, 860, 1480), cl=WARM['dust'], a=0.5, seed=6)
    u = 0.5 - 0.5 * math.cos(2 * math.pi * t / PUSH_T)
    s, fx, g = 1.0, 250, 1496
    body = (hu.SEG['thigh'] + hu.SEG['shin'] + hu.SEG['leg_w'] / 2 + hu.SEG['torso']) * s
    hx = fx + body * math.sin(math.radians(66)) + 6
    a = ramp(t, x.T[1] - 0.25, 0.4)
    sc = ramp(t, x.T[2] + 0.35, 0.9)
    al = a * (1 - ease(sc * 1.6))
    if al > 0:
        glow(c, 860, 1150, 520, RED, 0.2 * al)
    hu.light(dir=(0.1, -1.0), lit=WARM['lit'], shade=WARM['shade'], rim=RED, rim_a=0.5 * al, glow=0.12)
    pose = dict(torso=0.0, head=-30.0, la=('ik', (hx - 8, g), -1), ra=('ik', (hx + 10, g), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
    j = hu.figure(c, fx, g, s, pose, rot=66 + 13 * u, ground_shadow=0, brows=0.9, expr='grit' if u > 0.55 else 'open',
                  look=(0.6, 0.5))
    hx_, hy_ = j['head']
    for k in range(3):
        ph = (t * 0.9 + k / 3) % 1
        circ(c, hx_ - 30 + 50 * ph, hy_ - 50 + 220 * ph * ph, 6, '#CFE3F5', 0.7 * (1 - ph))
    if a > 0:
        pose = dict(torso=24.0, head=22.0, la=(18.0, 30.0), ra=(30.0, 70.0), ll=(-4.0, -2.0), rl=(4.0, 2.0))
        js = hu.figure(c, 860, g, 1.25, pose, flip=True, scheme='shadow', alpha=al, ground_shadow=0)
        hu.wisps(c, js, t, 1.25, a=al)
        hu.scatter(c, js, 1.25, sc)


# ---------------------------------------------------------------- the heavy bag
GYM = dict(wall=('#3B3447', '#221E2B'), floor=('#1E1A24', '#0E0C12'), trim='#2D2838', lamp='#FFD28A', dome='#BFC2D2',
           lit='#FFF5E8', shade='#A796A4', rim='#FFB36B', dust='#FFE2B0')
BAG_X, BAG_Y, FLOOR_G = 620, 760, 1560
HIT_DT = 0.07


def punches(x):
    """(time, arm, power): jab and cross while he warms up, a pause while the shadow talks, a flurry on the
    narration and one big cross on its last word. x.T / x.E: 0 the silent beat, 1 the taunt, 2 the narration."""
    out, t, k = [], 0.2, 0
    while t < x.T[1] - 0.25:
        out.append((t, 'la' if k % 2 == 0 else 'ra', 1.0 if k % 2 == 0 else 1.4))
        t += 0.34
        k += 1
    t, t_end = x.E[1] + 0.1, x.E[2] - 0.42
    while t < t_end - 0.26:
        out.append((t, 'la' if k % 2 == 0 else 'ra', 1.1 if k % 2 == 0 else 1.5))
        t += 0.28
        k += 1
    out.append((t_end, 'ra', 3.2))
    return out


def bag_angle(t, ps):
    a = 0.0
    for tk, _, pw in ps:
        dt = t - tk - HIT_DT
        if dt > 0:
            a += 5.0 * pw * math.exp(-dt / 0.55) * math.sin(2 * math.pi * 0.85 * dt)
    return a


def ext(dt):
    if dt < 0:
        return 0.0
    if dt < HIT_DT:
        return eout(dt / HIT_DT)
    if dt < HIT_DT + 0.05:
        return 1.0
    return 1 - ease((dt - HIT_DT - 0.05) / 0.16)


def contact(ang, y):
    r = math.radians(ang)
    ly = y - BAG_Y - 140
    return BAG_X - 75 * math.cos(r) + (140 + ly) * math.sin(r) - 4, BAG_Y + 75 * math.sin(r) + (140 + ly) * math.cos(r)


def sc_boxing(c, t, x):
    ps = punches(x)
    shake = 0.0
    for tk, _, pw in ps:
        dt = t - tk - HIT_DT
        if 0 <= dt < 0.2:
            shake += 3.0 * pw * math.exp(-dt / 0.05)
    c.translate(shake * math.sin(t * 91), shake * math.cos(t * 77))
    room(c, GYM, FLOOR_G)
    rect(c, -500, 1100, W + 1000, 30, '#4A4258', 0.55)
    cone = kit.path([(BAG_X - 160, -300), (BAG_X + 40, -300), (BAG_X + 420, FLOOR_G + 40), (BAG_X - 520, FLOOR_G + 40)])
    c.drawPath(cone, P('#ffffff', shader=kit.lgrad(0, 0, 0, FLOOR_G, [(GYM['lamp'], 0.05), (GYM['lamp'], 0.2)]), blur=30))
    oval(c, BAG_X - 60, FLOOR_G + 20, 460, 60, GYM['lamp'], 0.22, blur=30)
    dust(c, t, (300, 400, 960, 1500), cl=GYM['dust'], a=0.45, seed=15)
    ang = bag_angle(t, ps)
    t_big = ps[-1][0] + HIT_DT
    a = ramp(t, x.T[1] - 0.45, 0.4)
    sc = ramp(t, t_big, 0.8)
    al = a * (1 - ease(sc * 1.6))
    if al > 0 or 0 < sc < 1:
        glow(c, 820, 1080, 480, RED, 0.18 * al)
        pose = dict(torso=14.0, head=18.0, la=(16.0, 30.0), ra=(26.0, 60.0), ll=(-4.0, -2.0), rl=(4.0, 2.0))
        js = hu.figure(c, 830, FLOOR_G, 1.2, pose, flip=True, scheme='shadow', alpha=max(al, 0.0), ground_shadow=0)
        hu.wisps(c, js, t, 1.2, a=al)
        hu.scatter(c, js, 1.2, sc)
    line(c, BAG_X, -500, BAG_X, BAG_Y, '#8C90AA', w=5)
    punching_bag(c, BAG_X, BAG_Y, ang)
    # the fighter: jab with the far arm, cross with the near one, guard up between punches
    e = {'la': 0.0, 'ra': 0.0}
    for tk, arm_, pw in ps:
        e[arm_] = max(e[arm_], ext(t - tk))
    hu.light(dir=(0.2, -0.98), lit=GYM['lit'], shade=GYM['shade'], rim=RED, rim_a=0.35 * al, glow=0.1)
    bob = 6 * abs(math.sin(2 * math.pi * 1.4 * t))
    lean = 8.0 + 6.0 * max(e.values())
    hip_x = 410 + 10 * max(e.values())
    # first pass for the head position (guard points depend on it)
    pose0 = dict(torso=lean, head=-6.0, la=(30.0, 150.0), ra=(30.0, 150.0), ll=(-24.0, -12.0), rl=(22.0, 6.0))
    c.save()
    c.clipRect(R(0, 0, 0, 0))
    j0 = hu.figure(c, hip_x, FLOOR_G, 1.0, pose0, lift=bob, ground_shadow=0)
    c.restore()
    hx, hy = j0['head']
    guard = {'la': (hx + 36, hy + 56), 'ra': (hx + 18, hy + 74)}
    tgt = {}
    for arm_, yy in (('la', 1160), ('ra', 1190)):
        cx, cy = contact(ang, yy)
        gx, gy = guard[arm_]
        k = e[arm_]
        tgt[arm_] = ('ik', (gx + (cx - gx) * k, gy + (cy - gy) * k), -1)
    pose = dict(pose0, la=tgt['la'], ra=tgt['ra'])
    j = hu.figure(c, hip_x, FLOOR_G, 1.0, pose, lift=bob, brows=1.0, expr='grit' if max(e.values()) > 0.3 else 'open',
                  look=(0.7, 0.1), ground_shadow=0.5)
    for tk, arm_, pw in ps:
        dt = t - tk - HIT_DT
        if 0 <= dt < 0.3:
            v = dt / 0.3
            cx, cy = j[arm_][1]
            circ(c, cx + 10, cy, 18 + 120 * eout(v) * (0.7 + 0.3 * pw), '#FFFFFF', 0.55 * (1 - v), sw=4 + 3 * pw)
            glow(c, cx + 10, cy, 90 * pw, '#FFF3DA', 0.5 * (1 - v))
            for q in range(6):
                an = -1.1 + 0.45 * q
                dd = 30 + 150 * eout(v) * (0.6 + 0.4 * pw)
                circ(c, cx + 10 + dd * math.cos(an), cy + dd * math.sin(an), 4, '#FFF3DA', 0.8 * (1 - v))
    hx, hy = j['head']
    for k in range(2):
        ph = (t * 1.1 + k / 2) % 1
        circ(c, hx - 40 - 60 * ph, hy - 30 + 160 * ph * ph, 6, '#CFE3F5', 0.7 * (1 - ph))


# ---------------------------------------------------------------- up before the alarm
PREDAWN = dict(NIGHT, sky=('#1A2456', '#6A5A8E'))


def sc_early(c, t, x):
    t_ring = x.E[0] + 0.3
    ring = 1.0 if t >= t_ring else 0.0
    bedroom(c, t, sky_pal=PREDAWN, moon=(0.3, 0.25), stars=10, clock='5:00' if ring else '4:59', ring=ring, beam_a=0.1)
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    jolt = 6 * ring * math.sin(t * 40) * math.exp(-(t - t_ring) / 0.5) if ring else 0.0
    hu.head(c, 442 + jolt, 1320, 0.95, scheme='shadow', glow_a=0.35)
    blanket(c, t, NIGHT, x0=540, x1=1110, top=1360, breathe=1.0)
    for k in range(3):
        ph = (t * 0.45 + k / 3) % 1
        text(c, 'z', 520 + 60 * ph + 20 * k, 1220 - 150 * ph, 44 + 20 * ph, RED, 0.7 * (1 - ph) * (1 - ring), tf='brush')
    hu.light(dir=(-0.6, -0.8), lit='#EEF0FF', shade=NIGHT['shade'], rim='#B9A6FF', rim_a=0.3, glow=0.08)
    t_walk = x.T[0] + 0.55
    if t < t_walk:
        st = ease(clamp(t / 0.7))
        pose = hu.lerp_pose(hu.stand(), dict(hu.arms_up(), head=-20.0), st * (1 - ramp(t, t_walk - 0.35, 0.35)))
        hu.figure(c, 700, 1700, 1.0, pose, expr='smile', look=(0.4, -0.2))
    else:
        tw_ = t - t_walk
        p = 2 * math.pi * 1.1 * tw_
        hu.figure(c, 700 + 330 * tw_, 1700, 1.0, hu.walk(p), expr='smile', brows=0.3, look=(0.6, 0.0))


# ---------------------------------------------------------------- day 100
CAL_T0, CAL_FROM, CAL_TO = 0.25, 60, 100


def cal_schedule(dur):
    span = max(dur - 0.7, 0.5)
    k = CAL_TO - CAL_FROM

    def f(t):
        u = clamp((t - CAL_T0) / span)
        n = CAL_FROM + int(k * u ** 1.5)
        t_n = CAL_T0 + span * ((n - CAL_FROM) / k) ** (1 / 1.5)
        return n, t - t_n
    return f


def sc_calendar(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, list(WARM['wall']))
    glow(c, 540, 700, 900, WARM['lamp'], 0.25)
    dust(c, t, (0, 300, W, 1600), cl=WARM['dust'], a=0.4, seed=7)
    tear_calendar(c, 540, 960, t, cal_schedule(x.dur))


def sc_summit(c, t, x):
    sy = 1250 - 110 * ease(t / x.dur)
    sky(c, -500, 1300, DAWN['sky'], [0, 0.45, 0.8, 1])
    glow(c, 560, sy, 900, DAWN['sun'], 0.55)
    circ(c, 560, sy, 150, mix(DAWN['sun'], '#FFFFFF', 0.4))
    for k, (yy, a) in enumerate(((1030, 0.16), (1120, 0.12))):
        oval(c, 300 + 500 * k + 40 * math.sin(0.2 * t + k), yy, 520, 26, DAWN['mist'], a, blur=18)
    ridge(c, 1260, 80, 0.004, 300, DAWN['ridges'][0])
    ridge(c, 1330, 90, 0.006, 900, DAWN['ridges'][1], seed=2.0)
    ridge(c, 1430, 110, 0.005, 200, DAWN['ridges'][2], seed=4.0)
    poly(c, [(-500, H + 600), (-500, 1720), (120, 1500), (330, 1400), (470, 1300), (540, 1258), (610, 1300), (760, 1390),
             (980, 1480), (W + 500, 1640), (W + 500, H + 600)], DAWN['ridges'][3])
    dust(c, t, (0, 500, W, 1300), cl=DAWN['sun'], a=0.35, seed=9)
    hu.light(dir=(0.1, -1.0), lit=DAWN['lit'], shade=DAWN['shade'], rim=DAWN['rim'], rim_a=0.5, glow=0.16)
    hu.figure(c, 540, 1262, 0.62, dict(hu.stand_front(), head=-6.0), view='front', brows=0.35, expr='smile',
              look=(0.0, -0.3), ground_shadow=0)
    a = ramp(t, x.T[0], 0.5) * (1 - ramp(t, x.T[1] + 0.4, 0.6))
    sc = ramp(t, x.T[1] + 0.4, 1.0)
    if a > 0 or 0 < sc < 1:
        js = hu.figure(c, 330, 1430, 0.36, dict(hu.slump(), head=-10.0), scheme='shadow', alpha=max(a, 0.0), ground_shadow=0,
                       glow_a=0.4)
        hu.scatter(c, js, 0.36, sc)


SCENES = {
    'bed': dict(draw=sc_bed, cam=(1.06, 1.14, 450, 1300), cap_y=600, vig=0.7),
    'seasons': dict(draw=sc_seasons, cam=(1.1, 1.16, 450, 1300), cap_y=880, vig=0.7),
    'desk_fail': dict(draw=sc_desk_fail, cam=(1.04, 1.12, 560, 1200), cap_y=640, vig=0.7),
    'wake': dict(draw=sc_wake, cam=(1.0, 1.05, 540, 1150), cap_y=420, vig=0.72),
    'day1': dict(draw=sc_day1, cam=(1.0, 1.0, 540, 960), cap_y=900, vig=0.7),
    'run': dict(draw=sc_run, cam=(1.0, 1.0, 540, 960), cap_y=620, vig=0.55, day=3),
    'study': dict(draw=sc_study, cam=(1.04, 1.1, 560, 1200), cap_y=640, vig=0.66, day=9),
    'pushup': dict(draw=sc_pushup, cam=(1.12, 1.2, 560, 1300), cap_y=420, vig=0.66, day=12),
    'boxing': dict(draw=sc_boxing, cam=(1.1, 1.18, 560, 1250), cap_y=470, vig=0.66, day=30),
    'early': dict(draw=sc_early, cam=(1.06, 1.1, 500, 1300), cap_y=880, vig=0.7, day=60),
    'calendar': dict(draw=sc_calendar, cam=(1.0, 1.04, 540, 960), cap_y=1480, vig=0.66),
    'summit': dict(draw=sc_summit, cam=(1.12, 1.0, 540, 1250), cap_y=560, vig=0.55, day=100),
}

SCORE = dict(root=55.0, dark_notes=[57, 64, 60, 57, 64, 62], dark_every=1.6, turn='wake', title='day1', end='summit',
             bpm=120, chords=[(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)], end_chord=[57, 60, 64, 69],
             end_melody=[76, 72, 69])


def tick():
    n = int(0.03 * SR)
    return music.hp(np.random.default_rng(3).standard_normal(n), 3000) * env(n, 0.0005, 0.006)


def SFX(tl, spans, rng):
    out = []
    first = tl['lines'][0]['start']
    tt = 0.2
    while tt < first - 0.35:
        out += [(tt + k * 0.13, beep(), 1.0) for k in range(3)]
        tt += 0.62
    se = spans['seasons']
    tt, gap = se['start'], 0.3
    while tt < se['end'] - 0.05:
        out.append((tt, tick(), 0.5))
        tt += gap
        gap = max(0.06, gap * 0.93)
    out.append((se['start'], wind(se['end'] - se['start'], rng), 0.12))
    df = spans['desk_fail']
    dl = [ln for ln in tl['lines'] if ln['scene'] == 'desk_fail']
    out.append((dl[1]['end'] - 0.05, noise_hit(rng, 1500, 5000, 0.05, 0.01), 0.6))
    wk = [ln for ln in tl['lines'] if ln['scene'] == 'wake']
    t_open = wk[0]['end'] + 0.05
    out += [(t_open, thump(), 0.9), (t_open + 0.26, thump(52, 0.12), 0.6), (wk[1]['start'], music.sfx('boom'), 0.7)]
    for name in ('run', 'study', 'pushup', 'boxing', 'early', 'calendar', 'summit'):
        out.append((spans[name]['start'] - 0.35, music.sfx('whoosh'), 0.3))
    r = spans['run']
    k = 0
    while r['start'] + k / (2 * RUN_HZ) < r['end']:
        out.append((r['start'] + k / (2 * RUN_HZ), noise_hit(rng, 80, 500, 0.15, 0.04), 0.35))
        k += 1
    st = spans['study']
    tt = st['start'] + 0.2
    while tt < st['end'] - 0.1:
        out.append((tt, noise_hit(rng, 2500, 7000, 0.09, 0.03), 0.12))
        tt += 0.17
    bx = spans['boxing']
    bl = [ln for ln in tl['lines'] if ln['scene'] == 'boxing']

    class X:
        T = [ln['start'] - bx['start'] for ln in bl]
        E = [ln['end'] - bx['start'] for ln in bl]
    for tk, arm_, pw in punches(X):
        th = bx['start'] + tk + HIT_DT
        out += [(th, thump(70 if pw < 2 else 48, 0.08 if pw < 2 else 0.2), 0.45 * min(pw, 2.0)),
                (th, noise_hit(rng, 300, 3000, 0.08, 0.02), 0.35 * min(pw, 2.0))]
        if pw > 2:
            out.append((th, music.sfx('boom'), 0.8))
    ea = spans['early']
    el = [ln for ln in tl['lines'] if ln['scene'] == 'early']
    t_ring = el[0]['end'] + 0.3
    tt = t_ring
    while tt < ea['end'] - 0.2:
        out += [(tt + k * 0.13, beep(), 0.6) for k in range(3)]
        tt += 0.62
    cal = spans['calendar']
    f = cal_schedule(cal['end'] - cal['start'])
    seen, tt = CAL_FROM, 0.0
    while tt < cal['end'] - cal['start']:
        n, _ = f(tt)
        if n != seen:
            out.append((cal['start'] + tt, noise_hit(rng, 1500, 6500, 0.08, 0.02), 0.3 * (1 - (n - 50) / 80)))
            seen = n
        tt += 1 / 30
    sm = spans['summit']
    out.append((sm['start'], wind(sm['end'] - sm['start'], rng), 0.22))
    return out


def THUMB_T(tl):
    bed_ = [ln for ln in tl['lines'] if ln['scene'] == 'bed']
    return bed_[2]['start'] + 0.6
