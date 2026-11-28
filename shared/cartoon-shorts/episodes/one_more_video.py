"""ONE MORE VIDEO. - 2 a.m. scrolling with the shadow, hours gone, a grey morning carrying it, a buzz that always wins,
a dinner he isn't really at, the phone shut in a drawer, then the first two months: reading, guitar, walks, sleep,
the same dinner again, the sunrise."""
import math

import numpy as np
import skia

from motivation import (kit, hu, music, W, H, R, P, rect, rrect, line, circ, oval, glow, grect, poly, ease, eout, ramp,
                        clamp, mix, text, room, beam, dust, window, poster, hanging_lamp, bed, blanket, sleeper, nightstand,
                        sky, ridge, city, houses, trees, grr, desk, books, open_book, desk_lamp, chair, seated, desk_shadow,
                        DESK_N, CHAIR_N, FLOOR_D, BOOK, big_phone, noise_hit, wind, thump, piano, put, SR, env, NIGHT, WARM, DAWN, GREY)

NAME = 'one_more_video'
RED = '#FF3B3B'
PHONE_BLUE = '#5E9BFF'

SCRIPT = [
    dict(scene='phone', v='sha', text='one more video.', pre=1.4, pos=(640, 790)),
    dict(scene='phone', v='sha', text='you deserve this.', pos=(640, 790)),
    dict(scene='phone', v='nar', text="You're not | resting.", key=['resting'], pre=0.25),
    dict(scene='phone', v='nar', text="You're | numbing.", key=['numbing']),
    dict(scene='scroll', v='nar', text='Hours | disappear.', key=['disappear'], pre=0.7),
    dict(scene='drag', v='nar', text='Every cheap thrill | costs you | tomorrow.', key=['tomorrow'], pre=0.6),
    dict(scene='buzz', v='sha', text='just check it.', pre=0.6, pos=(520, 700)),
    dict(scene='buzz', v='nar', text='Every buzz | pulls you | back.', key=['back'], pre=0.2),
    dict(scene='dinner', v='nar', text="You're there, | but you're | not there.", key=['not'], pre=0.6),
    dict(scene='drawer', v='nar', text='So take | it back.', key=['back'], pre=0.6),
    dict(scene='drawer', text=' ', dur=1.0, style='none'),
    dict(scene='day1', text='DAY 1', dur=1.3, style='title', pos=(540, 900)),
    dict(scene='read', v='nar', text='Boredom | first.', key=['boredom'], pre=0.35),
    dict(scene='read', v='sha', text="you're missing out.", pos=(560, 700)),
    dict(scene='guitar', v='nar', text='Then | focus.', key=['focus'], pre=0.6),
    dict(scene='walk', v='nar', text='Then | you notice | things again.', key=['notice'], pre=0.5),
    dict(scene='sleep', v='nar', text='Then | peace.', key=['peace'], pre=0.5),
    dict(scene='dinner2', v='nar', text="Then you're | actually | there.", key=['actually'], pre=0.5),
    dict(scene='window', v='nar', text='Stop chasing | dopamine.', key=['dopamine'], pre=0.7),
    dict(scene='window', v='nar', text='Work | for it.', key=['work']),
    dict(scene='window', text='log off.', dur=2.6, style='word', pre=0.3, pos=(540, 600)),
]


# ---------------------------------------------------------------- 2 a.m.
def phone_at(t):
    return 566 + 3 * math.sin(1.3 * t), 1176 + 4 * math.sin(0.9 * t)


def sc_phone(c, t, x):
    room(c, NIGHT, 1600)
    window(c, 60, 380, 300, 400, NIGHT, t, light=0.7)
    poster(c, 780, 470, 190, 240, NIGHT)
    nightstand(c, 86, 1600, NIGHT, clock='2:13', t=t, w=180, h=230)
    px, py = phone_at(t)
    glow(c, px, py - 60, 620, PHONE_BLUE, 0.2)
    rise = ease((t - (x.T[0] - 1.0)) / 1.1)
    al = clamp(rise * 1.4)
    if rise > 0:
        glow(c, 740, 1150, 600, RED, 0.15 * al)
        c.save()
        c.clipRect(R(-500, -500, W + 1000, 2050))
        pose = dict(torso=30.0, head=20.0, la=(24.0, 60.0), ra=('ik', (px + 46, py - 40), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
        j = hu.figure(c, 790, 1600 + 700 * (1 - rise), 1.45, pose, flip=True, scheme='shadow', alpha=al, ground_shadow=0)
        hu.wisps(c, j, t, 1.45, a=al)
        c.restore()
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    hu.light(dir=(0.55, -0.83), lit='#E2EBFF', shade=NIGHT['shade'], rim=RED, rim_a=0.4 * al, glow=0.08)
    sleeper(c, 442, 1320, 0.95, t, expr='tired', look=(0.55, -0.6))
    blanket(c, t, NIGHT, breathe=0.4, x0=540, x1=1110, top=1360)
    hu.arm(c, (604, 1378), (px + 2, py + 34), 0.95, bend=1)
    hu.phone(c, px, py, 0.95, rot=-18, t=t)


# ---------------------------------------------------------------- grey morning
def sc_drag(c, t, x):
    sky(c, -500, 1500, GREY['sky'])
    city(c, -t * 20, 1420, GREY['far'], mix(GREY['win'], GREY['far'], 0.45), seed=3)
    houses(c, -t * 60, 1492, GREY['mid'], mix(GREY['win'], GREY['mid'], 0.3), seed=5)
    grect(c, -500, 1490, W + 1000, H + 600 - 1490, list(GREY['ground']))
    rect(c, -500, 1490, W + 1000, 10, mix(GREY['ground'][0], '#FFFFFF', 0.1))
    for i in range(10):
        xx = (i * 230 - t * 160) % 2300 - 600
        line(c, xx, 1610, xx + 110, 1610, mix(GREY['ground'][0], '#FFFFFF', 0.06), w=8)
    p = 2 * math.pi * 0.62 * t
    hu.light(dir=(-0.3, -0.95), lit=GREY['lit'], shade=GREY['shade'], rim=RED, rim_a=0.25, glow=0.05)
    j = hu.figure(c, 470, 1520, 0.95, hu.walk(p, amp=15, droop=1.0), expr='tired', look=(0.45, 0.7))
    shx, shy = j['shoulder']
    hdx, hdy = j['head']
    sp = dict(torso=18.0, head=26.0, ll=(72.0, 12.0), rl=(60.0, 4.0),
              la=('ik', (hdx + 46, hdy + 18), 1), ra=('ik', (hdx + 58, hdy + 40), 1))
    js = hu.figure(c, shx - 80, 0, 0.74, sp, hip_y=shy - 24 + 4 * math.sin(p * 2), scheme='shadow', ground_shadow=0, glow_a=0.45)
    hu.wisps(c, js, t, 0.74, a=0.7, n=10)
    rng = np.random.default_rng(1)
    for i in range(90):
        rx, ry = rng.random() * 1600 - 260, rng.random() * 2100
        yy = (ry + t * 1400) % 2100 - 100
        xx = rx - (yy * 0.18)
        line(c, xx, yy, xx - 10, yy + 46, '#C9D3E0', w=2, a=0.16)


# ---------------------------------------------------------------- the drawer
DAWN_WIN = dict(NIGHT, sky=('#4A5AA0', '#D9A08E'))
DESK = dict(top=('#655C86', '#4C4570'), body=('#3C365C', '#2A2645'), front=('#6E6696', '#4E4774'), knob='#B1AADB')


def sc_drawer(c, t, x):
    room(c, NIGHT, 1500)
    window(c, 620, 300, 360, 430, DAWN_WIN, t, moon=None, stars=0)
    beam(c, [(640, 330), (980, 330), (900, 1500), (300, 1500)], '#F2B9A0', 0.1)
    dust(c, t, (300, 400, 1000, 1480), cl='#F7D9CC', a=0.4, seed=11)
    t_drop = x.E[0] + 0.05
    t_slam = t_drop + 0.28
    o = 1 - ease((t - t_slam) / 0.12)
    dx = 190 * o
    grr(c, 560, 1240, 560, 30, 8, DESK['top'])
    grr(c, 590, 1270, 500, 150, 6, DESK['body'])
    rect(c, 1060, 1270, 26, 230, DESK['body'][1])
    rect(c, 590, 1420, 20, 80, DESK['body'][1])
    bx0 = 600 - dx
    rect(c, bx0 + 4, 1274, 236, 22, '#07070C')
    sc = ramp(t, t_slam + 0.05, 0.8)
    rise = ramp(t, x.T[0] + 0.1, 0.5)
    if o > 0.02:
        c.save()
        c.clipRect(R(bx0 + 6, 900, 228, 384))
        hu.head(c, bx0 + 120, 1296 - 70 * rise, 0.55, scheme='shadow')
        c.restore()
        if rise > 0.3:
            hu.arm(c, (bx0 + 160, 1304), (bx0 + 215, 1150 - 40 * math.sin(t * 4)), 0.4, bend=-1, scheme='shadow')
    if 0 < sc < 1:
        hu.scatter(c, {'head': (720, 1170), 'hip': (720, 1280)}, 0.5, sc)
    grr(c, bx0, 1272, 240, 110, 6, DESK['front'])
    rrect(c, bx0 + 90, 1316, 60, 12, 6, DESK['knob'])
    if t < t_drop:
        u = ease(t / max(t_drop, 0.1))
        tx, ty = 430 + (bx0 + 70 - 430) * u, 1080 + (1250 - 1080) * u
    else:
        tx, ty = bx0 - 6, 1330
    hu.light(dir=(0.7, -0.7), lit='#F4EEF6', shade=NIGHT['shade'], rim='#F2B9A0', rim_a=0.3, glow=0.08)
    pose = dict(hu.stand(), torso=10.0, head=16.0, ra=('ik', (tx, ty), -1))
    j = hu.figure(c, 300, 1500, 1.0, pose, expr='open', brows=ramp(t, t_drop - 0.2, 0.2), look=(0.6, 0.5))
    if t < t_drop:
        hu.phone(c, j['ra'][1][0] + 10, j['ra'][1][1] - 30, 0.85, rot=10, t=t, glow_a=0.6)


# ---------------------------------------------------------------- hours gone
def sc_scroll(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#0B0E22', '#05060F'])
    u = clamp(t / x.dur)
    m = int(133 + (292 - 133) * u)
    big_phone(c, 540, 1010, t, 420 * t + 700 * t * t, f'{m // 60}:{m % 60:02d}')
    ph = (t / 0.42) % 1.0
    tip_y = 1300 - 360 * eout(ph / 0.35) if ph < 0.35 else 940 + 360 * ease((ph - 0.35) / 0.65)
    hu.light(dir=(-0.3, -0.95), lit='#DCE8FF', shade='#6E78A8', glow=0.0)
    hu.tube(c, [(1180, 1900), (900, 1560), (700 + 20 * math.sin(ph * 6.28), tip_y)], 84, cast=True)


# ---------------------------------------------------------------- the buzz
def lying_phone(c, x, y, lit, t, shake=0.0):
    dx = shake * 3 * math.sin(t * 190)
    if lit:
        glow(c, x + dx, y - 10, 160, PHONE_BLUE, 0.4 * lit)
    rrect(c, x - 40 + dx, y - 12, 80, 12, 4, '#0B0B10')
    if lit:
        line(c, x - 34 + dx, y - 13, x + 34 + dx, y - 13, mix('#0B0B10', '#9CC2FF', lit), w=3)
        for k in (1, 2):
            a = 0.6 * lit * shake
            line(c, x - 52 - 10 * k + dx, y - 30 - 6 * k, x - 46 - 10 * k + dx, y - 18 - 2 * k, '#CFE0FF', w=3, a=a)
            line(c, x + 52 + 10 * k + dx, y - 30 - 6 * k, x + 46 + 10 * k + dx, y - 18 - 2 * k, '#CFE0FF', w=3, a=a)


def sc_buzz(c, t, x):
    room(c, NIGHT, FLOOR_D)
    window(c, 790, 250, 220, 290, NIGHT, t, moon=(0.62, 0.34), stars=12)
    t_push0, t_push1, t_grab = x.T[0] - 0.2, x.E[0], x.T[1] + 0.25
    px = 800 - 150 * ease((t - t_push0) / max(t_push1 - t_push0, 0.1))
    a = ramp(t, x.T[0] - 0.6, 0.4) * (1 - ramp(t, x.E[1] - 0.1, 0.4))
    if a > 0:
        glow(c, 900, 1100, 460, RED, 0.16 * a)
        pose = dict(torso=30.0, head=24.0, la=(20.0, 50.0), ra=('ik', (px + 30, 1232), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
        js = hu.figure(c, 900, FLOOR_D, 1.4, pose, flip=True, scheme='shadow', alpha=a, ground_shadow=0)
        hu.wisps(c, js, t, 1.4, a=a, n=10)
    desk(c, 500, 1060, 1250, FLOOR_D, DESK_N)
    open_book(c, BOOK[0], BOOK[1], 0.9, cover='#3F6FB0')
    glow(c, 640, 1180, 520, '#FFD28A', 0.1)
    g = ramp(t, t_grab, 0.35)
    if g <= 0:
        lying_phone(c, px, 1250, 1.0, t, shake=1.0 if (t % 0.9) < 0.45 else 0.0)
        pose = dict(torso=10.0, head=30.0, la=('ik', (560, 1244), -1), ra=('ik', (628 + 10 * math.sin(2 * math.pi * 3 * t), 1240), -1),
                    ll=(88.0, 2.0), rl=(84.0, -4.0))
        expr, look, glow_face = 'open', (0.5, 0.9), 0.0
    else:
        hx = px + (560 - px) * ease(g)
        hy = 1244 + (1120 - 1244) * ease(g)
        pose = dict(torso=10.0 - 6 * g, head=30.0 - 4 * g, la=('ik', (560, 1244), -1), ra=('ik', (hx, hy), -1),
                    ll=(88.0, 2.0), rl=(84.0, -4.0))
        expr, look, glow_face = 'tired', (0.55, 0.2), g
    hu.light(dir=(0.9, -0.45), lit=mix('#FFF0DA', '#DCE8FF', glow_face), shade=NIGHT['shade'], rim=RED, rim_a=0.3 * a, glow=0.06)
    j = seated(c, t, pose, expr=expr, look=look)
    if g > 0:
        hx, hy = j['ra'][1]
        hu.phone(c, hx + 6, hy - 34, 0.85, rot=-14, t=t, glow_a=g)


# ---------------------------------------------------------------- dinner
TABLE = ('#8A5A3C', '#5E3A27')


def dinner_set(c, t):
    room(c, WARM, 1500)
    window(c, 70, 330, 260, 330, dict(WARM, frame='#4E3123', sky=('#2B2F5E', '#6E5A8E')), t, moon=None, stars=8)
    hanging_lamp(c, 540, 700, 210, WARM, floor_y=1500)
    dust(c, t, (300, 760, 800, 1250), cl=WARM['dust'], a=0.45, seed=16, n=24)


def table(c, phone_down=False):
    grr(c, 250, 1262, 580, 30, 10, TABLE)
    for lx in (280, 780):
        rect(c, lx, 1292, 22, 208, TABLE[1])
    for px in (380, 540, 700):
        oval(c, px, 1258, 62, 9, '#F4EFE6')
        oval(c, px, 1256, 40, 5, '#D8C9B4')
    for gx in (450, 630):
        rrect(c, gx - 14, 1200, 28, 58, 6, '#CFE6F2', 0.55)
        rect(c, gx - 11, 1226, 22, 30, '#E9A64B', 0.6)
    if phone_down:
        rrect(c, 330, 1250, 70, 10, 4, '#0B0B10')


def friends(c, t, laugh=0.0):
    """Two friends: one across the table (front view, a bun), one at the far end (facing left, a ponytail)."""
    talk = (t % 1.6) < 0.8
    m_b = 'shout' if laugh > 0.5 and (t % 0.5) < 0.25 else ('smile' if talk else 'small')
    hu.figure(c, 540, 0, 0.92, dict(hu.stand_front(), la=('ik', (470, 1258), 1), ra=('ik', (610, 1258), -1)), view='front',
              hip_y=1350, legs=False, expr='closed' if laugh > 0.5 else 'smile', mouth=m_b, tuft='bun', ground_shadow=0)
    return talk


def friend_end(c, t, laugh=0.0):
    g = math.sin(2 * math.pi * 1.2 * t)
    pose = dict(hu.sit(), torso=6.0, head=6.0 - 10 * laugh, la=('ik', (760, 1258), -1), ra=('ik', (720 - 30 * g, 1190 + 20 * g), -1))
    m = 'shout' if laugh > 0.5 and ((t + 0.2) % 0.5) < 0.25 else ('small' if (t % 1.6) < 0.8 else 'smile')
    rect(c, 830, 1350, 140, 26, '#5E3A27')
    hu.figure(c, 880, 0, 0.95, pose, flip=True, hip_y=1342, expr='closed' if laugh > 0.5 else 'smile', mouth=m, tuft='pony',
              ground_shadow=0)


def sc_dinner(c, t, x):
    dinner_set(c, t)
    hu.light(dir=(0.0, -1.0), lit=WARM['lit'], shade=WARM['shade'], rim=WARM['rim'], rim_a=0.3, glow=0.08)
    friends(c, t)
    table(c)
    friend_end(c, t)
    a = ramp(t, 0.1, 0.4)
    glow(c, 170, 1080, 380, RED, 0.14 * a)
    pose = dict(torso=30.0, head=22.0, la=(20.0, 50.0), ra=('ik', (232, 1196), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
    js = hu.figure(c, 90, 1500, 1.2, pose, scheme='shadow', alpha=a, ground_shadow=0)
    hu.wisps(c, js, t, 1.2, a=a, n=10)
    rect(c, 130, 1350, 150, 26, '#5E3A27')
    hu.light(dir=(0.3, -0.95), lit='#DCE8FF', shade=WARM['shade'], rim=RED, rim_a=0.3, glow=0.06)
    pose = dict(hu.sit(), torso=16.0, head=34.0, la=('ik', (292, 1236), -1), ra=('ik', (306, 1240), -1))
    j = hu.figure(c, 200, 0, 0.95, pose, hip_y=1342, expr='tired', look=(0.5, 0.9), ground_shadow=0)
    hx, hy = j['ra'][1]
    hu.phone(c, hx + 6, hy - 26, 0.8, rot=30, t=t, glow_a=0.9)


def sc_dinner2(c, t, x):
    dinner_set(c, t)
    laugh = ramp(t, x.T[0] + 0.2, 0.3)
    hu.light(dir=(0.0, -1.0), lit=WARM['lit'], shade=WARM['shade'], rim=WARM['rim'], rim_a=0.3, glow=0.1)
    friends(c, t, laugh)
    table(c, phone_down=True)
    friend_end(c, t, laugh)
    rect(c, 130, 1350, 150, 26, '#5E3A27')
    bounce = 5 * laugh * abs(math.sin(2 * math.pi * 2.0 * t))
    pose = dict(hu.sit(), torso=2.0, head=-10.0 * laugh, la=('ik', (300, 1256), -1), ra=('ik', (360, 1254), -1))
    m = 'shout' if laugh > 0.5 and (t % 0.5) < 0.25 else 'smile'
    hu.figure(c, 200, 0, 0.95, pose, hip_y=1342 - bounce, expr='closed' if laugh > 0.5 else 'smile', mouth=m,
              look=(0.6, 0.0), ground_shadow=0)


# ---------------------------------------------------------------- guitar, walks
def guitar(c, gx, gy, ang, s=0.8):
    """An acoustic guitar with its body at (gx, gy) and its neck at ang degrees (negative: up to the right)."""
    c.save()
    c.translate(gx, gy)
    c.rotate(ang)
    c.scale(s, s)
    rect(c, 80, -13, 190, 26, '#5A3A22')
    rrect(c, 262, -20, 56, 40, 8, '#4A2E1A')
    for k in range(1, 7):
        line(c, 90 + 30 * k, -13, 90 + 30 * k, 13, '#C9B48A', w=2)
    oval(c, -40, 0, 92, 84, '#7A4A22')
    oval(c, 46, 0, 72, 64, '#7A4A22')
    oval(c, -40, 0, 86, 78, '#C8833F')
    oval(c, 46, 0, 66, 58, '#C8833F')
    oval(c, -30, -26, 60, 30, '#E0A35E', 0.5)
    circ(c, 22, 0, 22, '#2A160C')
    rect(c, -96, -14, 12, 28, '#4A2E1A')
    for v in (-8, -3, 3, 8):
        line(c, -90, v, 318, v * 0.6, '#EDE3CC', w=1.4)
    c.restore()


def sc_guitar(c, t, x):
    room(c, dict(WARM, wall=('#7A4A44', '#4A2C2C')), 1460)
    window(c, 640, 300, 300, 380, dict(WARM, frame='#4E3123', sky=('#3E3A7A', '#D9866A')), t, moon=None, stars=6)
    glow(c, 160, 900, 520, WARM['lamp'], 0.28)
    grr(c, 340, 1350, 200, 26, 10, ('#5E3B2A', '#3E2619'))
    for lx in (356, 506):
        rect(c, lx, 1376, 18, 84, '#3E2619')
    hu.light(dir=(-0.7, -0.7), lit=WARM['lit'], shade=WARM['shade'], rim='#FFB36B', rim_a=0.35, glow=0.1)
    gx, gy, ang, gs = 480, 1300, -20.0, 0.8
    r_ = math.radians(ang)
    fret = (gx + 140 * gs * math.cos(r_) + 4, gy + 140 * gs * math.sin(r_) - 6)
    sv = 22 * math.sin(2 * math.pi * 3.0 * t)
    strum = (gx + 4 + sv * math.sin(r_), gy - 4 - sv * math.cos(r_))
    pose = dict(hu.sit(), torso=6.0, head=26.0, la=('ik', fret, -1), ra=('ik', strum, -1))
    j = hu.figure(c, 440, 0, 1.0, pose, hip_y=1338, expr='open', brows=0.5, look=(0.4, 0.9), ground_shadow=0)
    guitar(c, gx, gy, ang, gs)
    hu.arm(c, j['aroot'], strum, 1.0, bend=-1)
    for k in range(4):
        ph = (t * 0.6 + k / 4) % 1
        text(c, '♪' if k % 2 else '♫', 560 + 140 * ph + 30 * k, 1180 - 380 * ph, 54, '#FFD27A', 0.9 * (1 - ph), tf='bold')


def sc_walk(c, t, x):
    sky(c, -500, 1460, ('#3A3F86', '#9A6AA0', '#F2A26C', '#FFD39A'), [0, 0.4, 0.78, 1])
    glow(c, 820, 1260, 700, '#FFD9A0', 0.5)
    circ(c, 820, 1260, 92, '#FFE9C2')
    ridge(c, 1340, 60, 0.004, t * 40, '#8A6A9E')
    trees(c, -t * 90, 1390, '#6A5290', seed=2, s=0.65)
    trees(c, -t * 260, 1464, '#33285A', seed=5)
    grect(c, -500, 1450, W + 1000, H + 600 - 1450, ['#2A2148', '#120E22'])
    for i in range(10):
        xx = (i * 230 - t * 300) % 2300 - 600
        oval(c, xx, 1520, 50, 8, '#3C3264')
    for k in range(5):
        bx = (k * 260 + t * (120 + 20 * k)) % 1500 - 200
        by = 560 + 90 * k + 20 * math.sin(t * 2 + k)
        fl = 14 * math.sin(t * 12 + k * 1.7)
        line(c, bx - 16, by - fl, bx, by, '#2A2148', w=4)
        line(c, bx, by, bx + 16, by - fl, '#2A2148', w=4)
    rng = np.random.default_rng(4)
    for i in range(10):
        ph = (t * 0.35 + rng.random()) % 1
        lx, ly = rng.random() * W + 60 * math.sin(ph * 6 + i), 500 + ph * 1000
        c.save()
        c.rotate(ph * 400, lx, ly)
        oval(c, lx, ly, 10, 5, ['#E0662F', '#F0A23B'][i % 2], 0.85 * (1 - ph))
        c.restore()
    p = 2 * math.pi * 0.9 * t
    hu.light(dir=(0.8, -0.6), lit='#FFF3E6', shade='#A894B8', rim='#FFC080', rim_a=0.45, glow=0.12)
    hu.figure(c, 470, 1466, 0.95, hu.walk(p, amp=18), expr='smile', look=(0.5, -0.5))


def sc_day1(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#0C0E22', '#121430', '#2A1F3A'], [0, 0.6, 1])
    glow(c, 540, 2000, 1000, DAWN['sun'], 0.3 * ramp(t, 0.05, 0.8))
    dust(c, t, (60, 400, 1020, 1700), cl=DAWN['sun'], a=0.4, seed=8)


SUN_WIN = dict(WARM, frame='#4E3123', sky=('#F7D7A0', '#EC9E60'))
WOOD = ('#5E3B2A', '#3E2619')


def sc_read(c, t, x):
    room(c, WARM, 1445)
    window(c, 640, 250, 340, 400, SUN_WIN, t, moon=None, stars=0)
    beam(c, [(640, 290), (640, 650), (140, 1445), (560, 1445)], '#FFE2B0', 0.2)
    dust(c, t, (160, 500, 900, 1420), cl=WARM['dust'], a=0.55, seed=12)
    grr(c, 292, 1060, 34, 385, 12, WOOD)
    grr(c, 292, 1326, 214, 34, 10, WOOD)
    rect(c, 476, 1356, 22, 89, WOOD[1])
    bkx, bky = 534, 1160
    a = ramp(t, x.T[1] - 0.4, 0.35) * (1 - ramp(t, x.E[1] + 0.25, 0.3))
    sc = ramp(t, x.E[1] + 0.3, 0.9)
    if a > 0 or 0 < sc < 1:
        glow(c, 300, 1050, 420, RED, 0.16 * a)
        sp = dict(torso=30.0, head=20.0, la=(20.0, 50.0), ra=('ik', (410, 1172), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
        js = hu.figure(c, 170, 1445, 1.2, sp, scheme='shadow', alpha=max(a, 0.0), ground_shadow=0)
        hu.wisps(c, js, t, 1.2, a=a, n=10)
        hu.scatter(c, js, 1.2, sc)
    hu.light(dir=(0.7, -0.7), lit=WARM['lit'], shade=WARM['shade'], rim=RED, rim_a=0.3 * a, glow=0.1)
    pose = dict(hu.sit(), torso=-2.0, head=26.0, la=('ik', (bkx - 30, bky + 16), -1), ra=('ik', (bkx + 24, bky + 22), -1))
    hu.figure(c, 404, 0, 1.0, pose, hip_y=1316, look=(0.55, 0.9), expr='open', ground_shadow=0)
    poly(c, [(bkx, bky + 16), (bkx - 102, bky), (bkx - 96, bky - 72), (bkx, bky - 56), (bkx + 96, bky - 72),
             (bkx + 102, bky), (bkx, bky + 16)], '#B23A36')
    for side in (-1, 1):
        poly(c, [(bkx, bky + 10), (bkx + side * 94, bky - 4), (bkx + side * 88, bky - 66), (bkx, bky - 52)], '#FFF4E4')
        for k in range(3):
            f = 0.3 + 0.2 * k
            line(c, bkx + side * 12, bky - 50 + 56 * f, bkx + side * 80, bky - 58 + 56 * f, '#CDBBA2', w=3)
    ph = (t % 1.4) / 1.4
    if ph < 0.35:
        u = ease(ph / 0.35)
        tipx = bkx + 92 * math.cos(math.pi * u)
        poly(c, [(bkx, bky + 10), (tipx, bky - 6 - 30 * math.sin(math.pi * u)), (tipx, bky - 70 - 30 * math.sin(math.pi * u)),
                 (bkx, bky - 54)], '#FFFBF4')


def sc_sleep(c, t, x):
    room(c, NIGHT, 1600)
    window(c, 60, 380, 300, 400, NIGHT, t)
    poster(c, 780, 470, 190, 240, NIGHT)
    beam(c, [(80, 400), (360, 400), (960, 1600), (360, 1600)], NIGHT['beam'], 0.1)
    nightstand(c, 86, 1600, NIGHT, clock='10:30', t=t, w=180, h=230)
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    hu.light(dir=(-0.5, -0.86), lit=NIGHT['lit'], shade=NIGHT['shade'], glow=0.08)
    sleeper(c, 442, 1320, 0.95, t, expr='closed', mouth='smile' if t > x.T[0] else 'small')
    blanket(c, t, NIGHT, breathe=1.0, x0=540, x1=1110, top=1360)
    for k in range(3):
        ph = (t * 0.45 + k / 3) % 1
        text(c, 'z', 520 + 60 * ph + 20 * k, 1220 - 150 * ph, 44 + 20 * ph, '#C9D3FF', 0.6 * (1 - ph), tf='brush')


DARK_WARM = dict(WARM, wall=('#4A3030', '#2A1C1C'), floor=('#241616', '#120B0B'), trim='#3A2626')


def sc_window(c, t, x):
    room(c, DARK_WARM, 1500)
    wx, wy, ww, wh = 500, 300, 540, 980
    sy = 1080 - 120 * ease(t / x.dur)
    rect(c, wx - 20, wy - 20, ww + 40, wh + 40, '#2B1D17')
    c.save()
    c.clipRect(R(wx, wy, ww, wh))
    grect(c, wx, wy, ww, wh, list(DAWN['sky']), [0, 0.45, 0.8, 1])
    glow(c, wx + 300, sy, 460, DAWN['sun'], 0.55)
    circ(c, wx + 300, sy, 90, mix(DAWN['sun'], '#FFFFFF', 0.4))
    ridge(c, wy + wh - 140, 60, 0.008, 200, DAWN['ridges'][1], base=wy + wh + 10)
    ridge(c, wy + wh - 70, 50, 0.011, 700, DAWN['ridges'][2], base=wy + wh + 10, seed=1.0)
    c.restore()
    line(c, wx + ww / 2, wy, wx + ww / 2, wy + wh, '#2B1D17', w=14, cap='butt')
    line(c, wx, wy + wh / 2, wx + ww, wy + wh / 2, '#2B1D17', w=14, cap='butt')
    rrect(c, wx - 40, wy + wh + 14, ww + 80, 24, 6, '#3A2820')
    beam(c, [(wx, wy + 60), (wx, wy + wh), (60, 1560), (420, 1560)], '#F7C98A', 0.2)
    dust(c, t, (100, 500, 1000, 1480), cl=DAWN['sun'], a=0.5, seed=14)
    hu.light(dir=(0.85, -0.5), lit='#FFF3E6', shade=DARK_WARM['shade'], rim='#FFC080', rim_a=0.5, glow=0.14)
    hu.figure(c, 330, 1500, 1.05, dict(hu.stand(), head=-8.0, ra=(14.0, 40.0)), look=(0.7, -0.3), expr='smile', brows=0.2)


SCENES = {
    'phone': dict(draw=sc_phone, cam=(1.06, 1.14, 450, 1300), cap_y=600, vig=0.72),
    'scroll': dict(draw=sc_scroll, cam=(1.0, 1.08, 540, 1010), cap_y=430, vig=0.7),
    'drag': dict(draw=sc_drag, cam=(1.0, 1.04, 540, 1200), cap_y=560, vig=0.6),
    'buzz': dict(draw=sc_buzz, cam=(1.04, 1.12, 560, 1200), cap_y=640, vig=0.7),
    'dinner': dict(draw=sc_dinner, cam=(1.14, 1.22, 540, 1250), cap_y=470, vig=0.66),
    'drawer': dict(draw=sc_drawer, cam=(1.02, 1.1, 520, 1300), cap_y=560, vig=0.65),
    'day1': dict(draw=sc_day1, cam=(1.0, 1.0, 540, 960), cap_y=900, vig=0.7),
    'read': dict(draw=sc_read, cam=(1.0, 1.06, 520, 1200), cap_y=800, vig=0.6, day=4),
    'guitar': dict(draw=sc_guitar, cam=(1.06, 1.12, 520, 1250), cap_y=780, vig=0.6, day=9),
    'walk': dict(draw=sc_walk, cam=(1.0, 1.0, 540, 960), cap_y=600, vig=0.55, day=14),
    'sleep': dict(draw=sc_sleep, cam=(1.06, 1.12, 450, 1300), cap_y=600, vig=0.7, day=21),
    'dinner2': dict(draw=sc_dinner2, cam=(1.14, 1.22, 540, 1250), cap_y=470, vig=0.62, day=40),
    'window': dict(draw=sc_window, cam=(1.12, 1.0, 520, 1100), cap_y=600, vig=0.55, day=60),
}

SCORE = dict(root=41.2, dark_notes=[64, 71, 67, 64, 71, 69], dark_every=1.7, turn='drawer', title='day1', end='window',
             bpm=116, chords=[(52, 55, 59), (48, 52, 55), (55, 59, 62), (50, 54, 57)], end_chord=[55, 59, 62, 67],
             end_melody=[71, 74, 79], duck=0.6)


def ping():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1760 * t) + 0.5 * np.sin(2 * np.pi * 2640 * t)) * env(n, 0.003, 0.09) * 0.5


def vib():
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 170 * t) * (np.sin(2 * np.pi * 25 * t) > 0) * env(n, 0.005, 0.3) * 0.6


def murmur(dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    am = 0.6 + 0.4 * np.sin(2 * np.pi * 3.1 * t) * np.sin(2 * np.pi * 0.7 * t + 1)
    return music.bp(rng.standard_normal(n), 300, 1400) * am


def chirp(rng):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f0 = 3000 + 1500 * rng.random()
    return np.sin(2 * np.pi * np.cumsum(f0 + 1800 * t / t[-1]) / SR) * env(n, 0.005, 0.04) * 0.5


def SFX(tl, spans, rng):
    out = []
    L = lambda name: [ln for ln in tl['lines'] if ln['scene'] == name]
    ph = spans['phone']
    tt = 0.4
    while tt < ph['end'] - 0.3:
        out.append((tt, noise_hit(rng, 2000, 7000, 0.12, 0.03), 0.18))
        tt += 0.75 + 0.3 * rng.random()
    out += [(0.9, ping(), 0.5), (ph['end'] - 2.2, ping(), 0.35)]
    sr_ = spans['scroll']
    tt = sr_['start']
    while tt < sr_['end'] - 0.1:
        out.append((tt + 0.05, noise_hit(rng, 1500, 6000, 0.12, 0.04), 0.22))
        tt += 0.42
    dg = spans['drag']
    n = int((dg['end'] - dg['start']) * SR)
    rain = music.bp(rng.standard_normal(n), 1500, 7000) * 0.35 + music.lp(rng.standard_normal(n), 400) * 0.2
    out.append((dg['start'], rain, 0.22))
    k = 0
    while dg['start'] + k / 1.24 < dg['end']:
        out.append((dg['start'] + k / 1.24, noise_hit(rng, 200, 2200, 0.25, 0.08), 0.2))
        k += 1
    bz = spans['buzz']
    t_grab = L('buzz')[1]['start'] + 0.25
    tt = bz['start'] + 0.1
    while tt < min(t_grab, bz['end']):
        out.append((tt, vib(), 0.5))
        tt += 0.9
    for name in ('dinner', 'dinner2'):
        d = spans[name]
        out.append((d['start'], murmur(d['end'] - d['start'], rng), 0.14))
    dr = L('drawer')
    t_slam = dr[0]['end'] + 0.05 + 0.28
    out += [(t_slam - 0.12, noise_hit(rng, 300, 2500, 0.2, 0.08), 0.5), (t_slam, music.sfx('gavel'), 1.0),
            (t_slam, thump(48, 0.2), 0.8)]
    for name in ('read', 'guitar', 'walk', 'sleep', 'dinner2', 'window'):
        out.append((spans[name]['start'] - 0.35, music.sfx('whoosh'), 0.3))
    rd = spans['read']
    tt = 0.0
    while tt < rd['end'] - rd['start']:
        out.append((rd['start'] + tt + 0.05, noise_hit(rng, 1200, 6000, 0.18, 0.05), 0.25))
        tt += 1.4
    gt = spans['guitar']
    tt, k = gt['start'] + 1 / 12, 0
    chords = [(55, 59, 62, 67), (52, 55, 59, 64), (48, 52, 55, 60), (50, 54, 57, 62)]
    while tt < gt['end'] - 0.1:
        ch = chords[(k // 4) % len(chords)]
        for i, m in enumerate(ch if k % 2 == 0 else ch[::-1]):
            out.append((tt + 0.012 * i, piano(m, 1.0, 0.5), 0.2))
        tt += 1 / 3
        k += 1
    wk = spans['walk']
    tt = wk['start'] + 0.3
    while tt < wk['end']:
        out.append((tt, chirp(rng), 0.14))
        tt += 0.35 + 0.5 * rng.random()
    out.append((wk['start'], wind(wk['end'] - wk['start'], rng), 0.08))
    w = spans['window']
    out.append((w['start'], wind(w['end'] - w['start'], rng), 0.15))
    return out


def THUMB_T(tl):
    ph = [ln for ln in tl['lines'] if ln['scene'] == 'phone']
    return ph[1]['start'] + 0.6
