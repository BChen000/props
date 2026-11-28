"""WHEN I'M READY. - a blank canvas and the shadow's 'not yet', the years it gathers dust, the day he decides, then
100 days of bad paintings getting better, the first post, the wall of paintings."""
import math

import numpy as np
import skia

from motivation import (kit, hu, music, W, H, R, P, rect, rrect, line, circ, oval, glow, grect, poly, ease, eout, ramp,
                        clamp, mix, text, room, beam, dust, window, grr, painting, easel, couch, tv, big_phone,
                        season_window, cobweb, noise_hit, wind, thump, piano, put, SR, env, NIGHT, WARM, DAWN)

NAME = 'when_im_ready'
RED = '#FF3B3B'
FLOOR_R = 1560
EASEL_X = 300
EASEL_TOP = FLOOR_R - 520
COUCH = ('#4A4070', '#352E56')
STUDIO = dict(NIGHT, wall=('#B78E78', '#8A6656'), floor=('#5C4034', '#3A2820'), trim='#6E4C3E', frame='#5A3C30',
              sky=('#9CC8EE', '#F6D9C0'), beam='#FFE7C0', lit='#FFF6EA', shade='#B4917E', rim='#FFC890', dust='#FFE9C8')

SCRIPT = [
    dict(scene='dream', v='sha', text='not yet.', pre=1.6, pos=(640, 760)),
    dict(scene='dream', v='sha', text="you're not ready.", pos=(640, 760)),
    dict(scene='dream', v='nar', text='So you | wait.', key=['wait'], pre=0.3),
    dict(scene='dust', v='nar', text='For the | right time.', key=['time'], pre=0.5),
    dict(scene='dust', v='nar', text='The right | feeling.', key=['feeling'], pre=0.1),
    dict(scene='compare', v='sha', text="they're better than you.", pre=0.6, pos=(540, 470)),
    dict(scene='compare', v='nar', text='The right | everything.', key=['everything'], pre=0.15),
    dict(scene='covered', v='nar', text='But ready | never comes.', key=['never'], pre=0.6),
    dict(scene='turn', v='nar', text='Until | you decide...', key=['decide'], pre=0.5),
    dict(scene='turn', text='now.', dur=1.5, style='no', pos=(540, 560)),
    dict(scene='day1', text='DAY 1', dur=1.3, style='title', pos=(540, 900)),
    dict(scene='first', v='sha', text="that's terrible.", pre=1.2, pos=(560, 700)),
    dict(scene='first', v='nar', text='It will be | bad.', key=['bad'], pre=0.2),
    dict(scene='again', v='nar', text='Keep | painting.', key=['painting'], pre=0.5),
    dict(scene='sketch', v='nar', text='Bad | turns into | better.', key=['better'], pre=0.5),
    dict(scene='share', v='sha', text="they'll laugh at you.", pre=0.6, pos=(540, 470)),
    dict(scene='share', v='nar', text='Let them.', key=['them'], pre=0.2),
    dict(scene='gallery', v='nar', text="You don't | get ready.", key=['ready'], pre=0.8),
    dict(scene='gallery', v='nar', text='You get | going.', key=['going']),
    dict(scene='gallery', text='start now.', dur=2.6, style='word', pre=0.3, pos=(540, 470)),
]


def brush(c, j, arm='ra', tip='#E8604A', ln=74, toward=None):
    """A paintbrush in the hand, pointing at `toward` (a screen point) or else along the forearm."""
    (ex, ey), (hx, hy) = j[arm]
    tx, ty = toward if toward else (2 * hx - ex, 2 * hy - ey)
    d = math.hypot(tx - hx, ty - hy) or 1.0
    ux, uy = (tx - hx) / d, (ty - hy) / d
    line(c, hx - ux * 14, hy - uy * 14, hx + ux * ln, hy + uy * ln, '#8A5A34', w=7)
    line(c, hx + ux * (ln - 4), hy + uy * (ln - 4), hx + ux * (ln + 14), hy + uy * (ln + 14), tip, w=11)


def night_room(c, t, seasons=False):
    room(c, NIGHT, FLOOR_R)
    if seasons:
        lt, day = season_window(c, 60, 300, 300, 400, t, rate=0.7)
    else:
        window(c, 60, 300, 300, 400, NIGHT, t)
        lt, day = NIGHT['beam'], 0.0
    beam(c, [(80, 320), (360, 320), (600, FLOOR_R), (40, FLOOR_R)], lt, 0.12 + 0.12 * day)
    return lt, day


# ---------------------------------------------------------------- not yet
def sc_dream(c, t, x):
    night_room(c, t)
    dust(c, t, (60, 400, 640, 1500), cl=NIGHT['dust'], a=0.5, seed=21)
    couch(c, 640, 960, 1400, FLOOR_R, COUCH)
    rise = ease((t - (x.T[0] - 1.1)) / 1.2)
    al = clamp(rise * 1.4) * (1 - 0.3 * ease((t - x.T[2]) / 0.8))
    if rise > 0:
        glow(c, 260, 1000, 560, RED, 0.17 * al)
        c.save()
        c.clipRect(R(-500, -500, W + 1000, FLOOR_R + 500))
        sp = dict(torso=12.0, head=14.0, la=(16.0, 40.0), ra=('ik', (400, EASEL_TOP + 14), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
        js = hu.figure(c, 140, FLOOR_R + 700 * (1 - rise), 1.7, sp, scheme='shadow', alpha=al, ground_shadow=0)
        hu.wisps(c, js, t, 1.7, a=al)
        c.restore()
    easel(c, EASEL_X, FLOOR_R, top=EASEL_TOP)
    glow(c, EASEL_X, EASEL_TOP + 115, 260, '#FFFFFF', 0.12 * (1 - al))
    u = ease(ramp(t, x.T[0] + 0.2, 1.0))
    hand = (470 + (560 - 470) * u, 1262 + (1400 - 1262) * u)
    hu.light(dir=(-0.8, -0.6), lit=NIGHT['lit'], shade=NIGHT['shade'], rim=RED, rim_a=0.4 * al, glow=0.08)
    pose = dict(hu.stand(), torso=6.0 + 10 * u, head=-4.0 + 26 * u, ra=('ik', hand, 1))
    j = hu.figure(c, 590, FLOOR_R + 60, 1.0, pose, flip=True, expr='smile' if u < 0.4 else 'sad', brows=0.0,
                  look=(0.6, -0.1 + 0.8 * u))
    brush(c, j, toward=(330, 1160) if u < 0.5 else None)


def sc_dust(c, t, x):
    lt, day = night_room(c, t, seasons=True)
    couch(c, 640, 960, 1400, FLOOR_R, COUCH)
    easel(c, EASEL_X, FLOOR_R, top=EASEL_TOP, dusty=ramp(t, 0.1, x.dur * 0.85))
    cobweb(c, EASEL_X - 150, EASEL_TOP, ramp(t, 0.4, x.dur * 0.8), size=130)
    hu.light(dir=(0.3, -0.95), lit='#DCE8FF', shade=NIGHT['shade'], glow=0.06)
    pose = dict(hu.sit_slump(), la=('ik', (790, 1306), -1), ra=('ik', (806, 1310), -1))
    j = hu.figure(c, 720, 0, 1.0, pose, hip_y=1388, expr='tired', look=(0.6, 0.8), ground_shadow=0)
    hx, hy = j['ra'][1]
    hu.phone(c, hx + 4, hy - 24, 0.85, rot=30, t=t, glow_a=0.9)
    rect(c, -500, -500, W + 1000, H + 1000, lt, 0.07 * day)


def art_card(c, x, y, w, h, i):
    painting(c, x, y, w, h, 1.0, seed=3 * i + 1)


def sc_compare(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#0B0E22', '#05060F'])
    a = ramp(t, x.T[0] - 0.3, 0.4) * (1 - ramp(t, x.E[0] + 0.3, 0.5))
    big_phone(c, 540, 1010, t, 260 * t + 220 * t * t, '1:47', feed=art_card, reflect=0.16 + 0.4 * a)
    ph = (t / 0.5) % 1.0
    tip_y = 1300 - 360 * eout(ph / 0.35) if ph < 0.35 else 940 + 360 * ease((ph - 0.35) / 0.65)
    hu.light(dir=(-0.3, -0.95), lit='#DCE8FF', shade='#6E78A8', glow=0.0)
    hu.tube(c, [(1180, 1900), (900, 1560), (700 + 20 * math.sin(ph * 6.28), tip_y)], 84, cast=True)


def sc_covered(c, t, x):
    night_room(c, t)
    easel(c, EASEL_X, FLOOR_R, top=EASEL_TOP, cover=ramp(t, 0.15, 0.9))
    couch(c, 600, 920, 1400, FLOOR_R, COUCH)
    fl = tv(c, 960, 1170, 220, 140, t)
    sp = dict(hu.sit(), torso=-14.0, head=10.0, la=(20.0, 60.0), ra=('ik', (742, 1196), -1))
    js = hu.figure(c, 650, 0, 1.0, sp, hip_y=1388, scheme='shadow', ground_shadow=0, glow_a=0.4)
    hu.wisps(c, js, t, 1.0, a=0.7, n=10)
    hu.light(dir=(1.0, -0.2), lit=mix(NIGHT['shade'], '#DCE8FF', fl), shade=NIGHT['shade'], rim=RED, rim_a=0.3, glow=0.05)
    hu.figure(c, 740, 0, 1.0, dict(hu.sit_slump(), head=20.0), hip_y=1388, expr='tired', look=(0.6, 0.0), ground_shadow=0)


# ---------------------------------------------------------------- the decision
def sc_turn(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#252A58', '#141632'])
    fl = 0.75 + 0.25 * math.sin(t * 23) * math.sin(t * 7.3 + 1)
    t_open, t_now = x.E[0] + 0.05, x.T[1]
    u = ramp(t, t_now, 0.9)
    glow(c, 1100, 1000, 900, '#8FB6FF', 0.22 * fl * (1 - u))
    glow(c, 540, 2100, 1100, DAWN['sun'], 0.35 * u)
    dust(c, t, (0, 200, W, 1400), cl=NIGHT['dust'], a=0.35, seed=5)
    glow(c, 610, 900, 620, RED, 0.22 * (1 - ease(u * 1.4)))
    pose = dict(hu.stand_front(), torso=-6.0, head=-8.0, la=(-24.0, -12.0), ra=(26.0, 14.0))
    j = hu.figure(c, 610, 0, 2.4, pose, view='front', hip_y=1430, legs=False, scheme='shadow', alpha=1 - ease(u * 1.6),
                  ground_shadow=0)
    hu.wisps(c, j, t, 2.4, a=1 - ease(u * 1.6))
    hu.scatter(c, j, 2.4, u)
    expr = 'tired' if t < t_open else ('wide' if t < t_now else 'grit')
    hu.light(dir=(0.9, -0.4) if u < 0.5 else (0.0, -1.0), lit=mix('#DCE8FF', '#FFF3E6', u), shade=NIGHT['shade'], rim=RED,
             rim_a=0.5 * (1 - u), glow=0.1)
    hu.figure(c, 520, 0, 2.0, dict(hu.stand_front(), la=(-14.0, 18.0), ra=(14.0, -18.0)), view='front',
              hip_y=1760 - 70 * eout(u), legs=False, expr=expr, brows=ramp(t, t_now - 0.1, 0.15), look=(0.0, -0.25),
              ground_shadow=0)


def sc_day1(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#0C0E22', '#121430', '#2A1F3A'], [0, 0.6, 1])
    glow(c, 540, 2000, 1000, DAWN['sun'], 0.3 * ramp(t, 0.05, 0.8))
    dust(c, t, (60, 400, 1020, 1700), cl=DAWN['sun'], a=0.4, seed=8)


# ---------------------------------------------------------------- 100 days of painting
def studio(c, t):
    room(c, STUDIO, FLOOR_R)
    window(c, 60, 300, 300, 400, STUDIO, t, moon=None, stars=0)
    beam(c, [(80, 320), (360, 320), (640, FLOOR_R), (60, FLOOR_R)], STUDIO['beam'], 0.2)
    dust(c, t, (60, 400, 700, 1500), cl=STUDIO['dust'], a=0.55, seed=22)


def painter(c, t, stroke, energy=1.0, expr='open', brows=0.4, tip='#E8604A'):
    """Him at the easel, facing left, the brush working over the canvas around `stroke`."""
    sx, sy = stroke
    hand = (sx + 30 * energy * math.sin(2 * math.pi * 1.6 * t), sy + 22 * energy * math.sin(2 * math.pi * 2.3 * t))
    pose = dict(hu.stand(), torso=8.0, head=4.0, ra=('ik', hand, 1), la=(10.0, 30.0))
    j = hu.figure(c, 560, FLOOR_R + 60, 1.0, pose, flip=True, expr=expr, brows=brows, look=(0.6, 0.1))
    brush(c, j, tip=tip, toward=(hand[0] - 130, hand[1] - 75))
    return j


def sc_first(c, t, x):
    studio(c, t)
    a = ramp(t, x.T[0] - 0.45, 0.4) * (1 - ramp(t, x.E[1] + 0.2, 0.4))
    if a > 0:
        glow(c, 240, 900, 520, RED, 0.16 * a)
        bounce = 10 * abs(math.sin(2 * math.pi * 3.0 * t)) * ramp(t, x.T[0], 0.2) * (1 - ramp(t, x.E[0], 0.3))
        sp = dict(torso=6.0, head=-16.0, la=(30.0, 120.0), ra=(-20.0, -100.0), ll=(0.0, 0.0), rl=(0.0, 0.0))
        js = hu.figure(c, 140, FLOOR_R - bounce, 1.7, sp, scheme='shadow', alpha=a, ground_shadow=0)
        hu.wisps(c, js, t, 1.7, a=a, n=10)
    easel(c, EASEL_X, FLOOR_R, top=EASEL_TOP, q=0.02, seed=7, reveal=ramp(t, 0.2, max(x.T[0], 0.5)))
    hu.light(dir=(-0.8, -0.6), lit=STUDIO['lit'], shade=STUDIO['shade'], rim=RED, rim_a=0.3 * a, glow=0.1)
    painter(c, t, (440, 1272), energy=0.8, expr='open' if t < x.T[0] else 'sad', brows=0.2)


def sc_again(c, t, x):
    studio(c, t)
    easel(c, EASEL_X, FLOOR_R, top=EASEL_TOP, q=0.38, seed=11, reveal=ramp(t, 0.0, x.dur * 0.9))
    hu.light(dir=(-0.8, -0.6), lit=STUDIO['lit'], shade=STUDIO['shade'], rim=STUDIO['rim'], rim_a=0.4, glow=0.12)
    j = painter(c, t * 1.4, (440, 1272), energy=1.2, expr='grit', brows=0.9, tip='#3F6FB0')
    hx, hy = j['ra'][1]
    rng = np.random.default_rng(3)
    cols = ['#E8604A', '#3F6FB0', '#F0B84A', '#6CC28E']
    for i in range(14):
        ph = (t * 1.3 + rng.random()) % 1
        ang = math.pi * (0.7 + 0.6 * rng.random())
        dd = 40 + 260 * ph
        circ(c, hx + dd * math.cos(ang) * 0.6, hy - 60 * math.sin(math.pi * ph) + dd * math.sin(ang) * 0.4 + 120 * ph * ph,
             4 + 4 * rng.random(), cols[i % 4], 0.9 * (1 - ph))


def sc_sketch(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#5A3A2E', '#2E1C16'])
    glow(c, 540, 900, 900, WARM['lamp'], 0.3)
    grr(c, -100, 1240, W + 200, 900, 20, ('#7A5236', '#4E3422'))
    n = int(t / 0.32)
    q = clamp(0.35 + 0.08 * n, 0.0, 0.95)
    k = (t % 0.32) / 0.32
    bx, by, pw, phh = 120, 820, 420, 330
    rect(c, bx - 20, by - 20 + 24, pw * 2 + 40, phh + 40, '#000000', 0.35, blur=18)
    grr(c, bx - 16, by - 16, pw * 2 + 32, phh + 32, 14, ('#2E3D5E', '#22304C'))
    for side in (0, 1):
        x0 = bx + side * pw
        rect(c, x0, by, pw, phh, '#FBF7EE')
        painting(c, x0 + 26, by + 26, pw - 52, phh - 52, clamp(q - 0.08 * (1 - side)), seed=40 + n * 2 + side)
    line(c, bx + pw, by, bx + pw, by + phh, '#D8CFBF', w=3)
    if k < 0.45:
        u = ease(k / 0.45)
        wpg = pw * math.cos(math.pi * u)
        x0 = bx + pw
        poly(c, [(x0, by - 6 * math.sin(math.pi * u)), (x0 + wpg, by - 18 * math.sin(math.pi * u)),
                 (x0 + wpg, by + phh + 4), (x0, by + phh)], '#FFFDF8' if u < 0.5 else '#F1EADD')
    hu.light(dir=(-0.3, -0.95), lit=WARM['lit'], shade=WARM['shade'], glow=0.0)
    hx, hy = 760 + 30 * math.sin(2 * math.pi * 2.2 * t), 1060 + 20 * math.sin(2 * math.pi * 3.1 * t)
    hu.tube(c, [(1200, 1700), (980, 1320), (hx, hy)], 70, cast=True)
    line(c, hx - 6, hy - 10, hx - 70, hy - 70, '#E8B04A', w=10)
    line(c, hx - 70, hy - 70, hx - 82, hy - 82, '#3A2A22', w=6)


def post_card(c, x, y, w, h, i):
    if i == 0:
        painting(c, x, y, w, h, 0.85, seed=77)


def sc_share(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#141A38', '#07081A'])
    a = ramp(t, x.T[0] - 0.3, 0.4) * (1 - ramp(t, x.E[0] + 0.2, 0.4))
    t_tap = x.T[1] - 0.15
    big_phone(c, 540, 1010, t, 0.0, '9:41', feed=post_card, reflect=0.12 + 0.45 * a)
    likes = 0 if t < t_tap else int(min(1204, 3 + 1500 * (t - t_tap) ** 2))
    text(c, '♥', 380, 1350, 52, '#FF5A7A' if likes else '#9AA4BC', tf='bold')
    text(c, f'{likes:,}', 470, 1348, 40, '#1A1A26', tf='pop')
    k = ramp(t, t_tap - 0.35, 0.2) * (1 - ramp(t, t_tap + 0.1, 0.2))
    hu.light(dir=(-0.3, -0.95), lit='#DCE8FF', shade='#6E78A8', glow=0.0)
    hu.tube(c, [(1180, 1900), (900, 1600), (700 - 300 * k, 1500 - 160 * k)], 84, cast=True)
    if t > t_tap:
        rng = np.random.default_rng(9)
        for i in range(16):
            ph = ((t - t_tap) * 0.8 + rng.random()) % 1
            hx = 380 + 360 * rng.random() + 40 * math.sin(ph * 6 + i)
            hy = 1300 - 700 * ph
            text(c, '♥', hx, hy, 40 + 30 * rng.random(), ['#FF5A7A', '#FF8FA8', '#FFD27A'][i % 3], 0.9 * (1 - ph), tf='bold')


GALLERY_WALL = dict(NIGHT, wall=('#2E3352', '#1E2138'), floor=('#3A2A22', '#1E140F'), trim='#2A2E4E')


def frame_art(c, x, y, w, h, q, seed, spot=1.0):
    cone = kit.path([(x + w / 2 - 30, y - 260), (x + w / 2 + 30, y - 260), (x + w + 40, y + h + 60), (x - 40, y + h + 60)])
    c.drawPath(cone, P('#ffffff', shader=kit.lgrad(0, y - 260, 0, y + h + 60, [('#FFE2B0', 0.2 * spot), ('#FFE2B0', 0.0)]), blur=18))
    rect(c, x - 14 + 8, y - 14 + 14, w + 28, h + 28, '#000000', 0.4, blur=14)
    rect(c, x - 14, y - 14, w + 28, h + 28, '#C9A25A')
    rect(c, x - 6, y - 6, w + 12, h + 12, '#8A6A34')
    painting(c, x, y, w, h, q, seed)


def sc_gallery(c, t, x):
    room(c, GALLERY_WALL, 1620)
    for i, q in enumerate((0.02, 0.38, 0.6, 0.8)):
        frame_art(c, 100 + i * 230, 600, 170, 130, q, seed=(7, 11, 23, 31)[i])
    frame_art(c, 200, 900, 470, 340, 1.0, seed=77, spot=1.3)
    dust(c, t, (100, 500, 900, 1500), cl='#FFE2B0', a=0.45, seed=31)
    hu.light(dir=(-0.4, -0.9), lit='#FFF3E6', shade='#A996BC', rim='#FFC080', rim_a=0.4, glow=0.12)
    hu.figure(c, 850, 1700, 1.05, dict(hu.stand(), head=-6.0), flip=True, expr='smile', brows=0.2, look=(0.6, -0.4))


SCENES = {
    'dream': dict(draw=sc_dream, cam=(1.04, 1.12, 420, 1150), cap_y=600, vig=0.7),
    'dust': dict(draw=sc_dust, cam=(1.06, 1.12, 460, 1200), cap_y=820, vig=0.7),
    'compare': dict(draw=sc_compare, cam=(1.0, 1.08, 540, 1010), cap_y=430, vig=0.7),
    'covered': dict(draw=sc_covered, cam=(1.06, 1.14, 560, 1250), cap_y=600, vig=0.72),
    'turn': dict(draw=sc_turn, cam=(1.0, 1.05, 540, 1150), cap_y=420, vig=0.72),
    'day1': dict(draw=sc_day1, cam=(1.0, 1.0, 540, 960), cap_y=900, vig=0.7),
    'first': dict(draw=sc_first, cam=(1.04, 1.12, 400, 1150), cap_y=560, vig=0.62),
    'again': dict(draw=sc_again, cam=(1.08, 1.16, 420, 1150), cap_y=560, vig=0.6, day=8),
    'sketch': dict(draw=sc_sketch, cam=(1.0, 1.06, 540, 1000), cap_y=560, vig=0.62, day=30),
    'share': dict(draw=sc_share, cam=(1.0, 1.06, 540, 1010), cap_y=430, vig=0.7, day=60),
    'gallery': dict(draw=sc_gallery, cam=(1.12, 1.0, 520, 1100), cap_y=470, vig=0.55, day=100),
}

SCORE = dict(root=49.0, dark_notes=[61, 68, 64, 61, 68, 66], dark_every=1.7, turn='turn', title='day1', end='gallery',
             bpm=118, chords=[(49, 53, 56), (54, 58, 61), (56, 60, 63), (51, 54, 58)], end_chord=[49, 53, 56, 61],
             end_melody=[73, 68, 65], duck=0.6)


def tick():
    n = int(0.03 * SR)
    return music.hp(np.random.default_rng(3).standard_normal(n), 3000) * env(n, 0.0005, 0.006)


def blip(f):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * env(n, 0.002, 0.05) * 0.5


def SFX(tl, spans, rng):
    out = []
    L = lambda name: [ln for ln in tl['lines'] if ln['scene'] == name]
    dr = spans['dream']
    out.append((dr['start'], wind(dr['end'] - dr['start'], rng), 0.08))
    du = spans['dust']
    tt, gap = du['start'], 0.3
    while tt < du['end'] - 0.05:
        out.append((tt, tick(), 0.5))
        tt += gap
        gap = max(0.06, gap * 0.93)
    cp = spans['compare']
    tt = cp['start']
    while tt < cp['end'] - 0.1:
        out.append((tt + 0.05, noise_hit(rng, 1500, 6000, 0.12, 0.04), 0.2))
        tt += 0.5
    cv = spans['covered']
    n = int((cv['end'] - cv['start']) * SR)
    out.append((cv['start'], music.bp(rng.standard_normal(n), 400, 3000) * 0.15, 0.25))
    tn = L('turn')
    t_open = tn[0]['end'] + 0.05
    out += [(t_open, thump(), 0.9), (tn[1]['start'], music.sfx('boom'), 0.7)]
    for name in ('first', 'again', 'sketch', 'share', 'gallery'):
        out.append((spans[name]['start'] - 0.35, music.sfx('whoosh'), 0.3))
    for name, step in (('first', 0.62), ('again', 0.45)):
        sp = spans[name]
        tt = sp['start'] + 0.2
        while tt < sp['end'] - 0.1:
            out.append((tt, noise_hit(rng, 900, 4000, 0.18, 0.06), 0.18))
            tt += step
    sk = spans['sketch']
    tt = sk['start']
    while tt < sk['end'] - 0.05:
        out.append((tt + 0.02, noise_hit(rng, 1200, 6000, 0.14, 0.04), 0.22))
        tt += 0.32
    sh = L('share')
    t_tap = sh[1]['start'] - 0.15
    out.append((t_tap, noise_hit(rng, 2000, 6000, 0.03, 0.008), 0.6))
    for k in range(12):
        out.append((t_tap + 0.1 + 0.11 * k, blip(880 * 2 ** ((k % 5) / 12)), 0.18))
    g = spans['gallery']
    out.append((g['start'], wind(g['end'] - g['start'], rng), 0.1))
    return out


def THUMB_T(tl):
    d = [ln for ln in tl['lines'] if ln['scene'] == 'dream']
    return d[1]['start'] + 0.3
