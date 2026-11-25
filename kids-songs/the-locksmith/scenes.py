"""The Locksmith: one draw function per scene, plus the camera and caption position for each (the SCENES table at the end).

Every draw function is draw(c, t, x): c is the skia canvas in 1080x1920 coordinates, t is seconds since the scene
started, x is a Ctx with x.T / x.E (each line's start and end, scene-relative) and x.dur. cam is either
(zoom_from, zoom_to, focus_x, focus_y), eased over the scene, or a function (t, x) -> (zoom, fx, fy[, screen_x, screen_y]).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'storytime-kit'))
from storytime_kit import *  # noqa: E402,F401,F403

WALTER = dict(skin=SKIN['light'], hair='bald', hair_col='#9A938C', top='#55697A', collar='#E8E6E1', apron='#6B4A2F',
              pants='#3A3A42', glasses=True, mustache='#8E8780')
WALTER_OUT = dict(WALTER, apron=None, top='#6B5444', collar='#D9D2C5')
WALTER_NIGHT = dict(WALTER, apron=None, top='#59616B', collar=None, glasses=False)


def mustache(c, x, y, s):
    pass


def keys_wall(c, t):
    rrect(c, 110, 560, 860, 520, 14, '#4A3828')
    for i in range(16):
        for j in range(9):
            circ(c, 150 + i * 52, 590 + j * 58, 3.5, '#2E2218')
    rng = random.Random(3)
    for r_ in range(3):
        for k in range(7):
            x = 200 + k * 113
            y = 630 + r_ * 150
            circ(c, x, y - 10, 6, '#2A2A2A')
            cl = rng.choice(['#D6B04C', '#C9CDD2', '#B8893C', '#D6B04C'])
            key(c, x, y, 1.05, 90 + 5 * math.sin(t * 1.4 + k * 0.9 + r_), cl)


def shop(c, t, x):
    grect(c, 0, 0, W, H, ['#3B2B20', '#21170F'])
    glow(c, 540, 1050, 760, '#FFB870', 0.22)
    keys_wall(c, t)
    rrect(c, 300, 440, 480, 96, 10, '#1C140E')
    rrect(c, 312, 452, 456, 72, 6, '#1C140E', sw=3)
    text(c, 'LOCKSMITH', 540, 508, 54, '#D9B25A', tf='serifb')
    person(c, 540, 2010, 1.7, WALTER, expr='smile', arms=(8, 8), t=t, seed=1, look=0.1)
    rect(c, 40, 1535, 1000, 400, '#5A3D28')
    rect(c, 28, 1520, 1024, 28, '#7A5438')
    for xx in (190, 540, 890):
        rect(c, xx - 130, 1600, 260, 300, '#4E3422', sw=5)
    key(c, 300, 1528, 1.0, -12)
    key(c, 760, 1526, 1.0, 168, '#C9CDD2')
    circ(c, 880, 1510, 20, '#C9A44A')
    rect(c, 860, 1510, 40, 10, '#8E7230')


def cutting(c, t, x):
    grect(c, 0, 0, W, H, ['#2B241F', '#15110E'])
    glow(c, 540, 1080, 650, '#FFC07A', 0.18)
    rect(c, 160, 600, 760, 22, '#5A4330')
    for k in range(9):
        key(c, 210 + k * 80, 600, 1.0, 90, '#C9A44A' if k % 3 else '#C9CDD2')
    rect(c, 0, 1300, W, 620, '#4E3A2A')
    rect(c, 0, 1290, W, 20, '#6A4E38')
    rrect(c, 230, 1030, 620, 270, 18, '#4E565E')
    rrect(c, 250, 1050, 580, 60, 10, '#636C75')
    rrect(c, 300, 760, 480, 220, 30, '#59626B')
    rect(c, 520, 980, 40, 80, '#3F474F')
    c.save()
    c.translate(540, 960)
    c.rotate(t * 900)
    circ(c, 0, 0, 120, '#8C949C')
    for i in range(28):
        a = math.radians(i * 360 / 28)
        poly(c, [(118 * math.cos(a - 0.08), 118 * math.sin(a - 0.08)), (134 * math.cos(a), 134 * math.sin(a)), (118 * math.cos(a + 0.08), 118 * math.sin(a + 0.08))], '#8C949C')
    circ(c, 0, 0, 34, '#5A6168')
    line(c, -100, 0, 100, 0, '#7A8289', 6)
    c.restore()
    p = skia.Path()
    p.addArc(R(390, 810, 300, 300), 180, 180)
    p.close()
    c.drawPath(p, P('#3F474F'))
    kx = 470 + 70 * math.sin(t * 2.2)
    key(c, kx - 130, 1110, 3.0, 0, '#D6B04C')
    rng = random.Random(int(t * 30))
    for i in range(26):
        rs = random.Random(i * 7919)
        life = (t * 2.5 + rs.random()) % 1.0
        ang = math.radians(200 + rs.random() * 140)
        sp = 260 + rs.random() * 320
        px = 545 + math.cos(ang) * sp * life
        py = 1080 + math.sin(ang) * sp * life + 500 * life * life
        circ(c, px, py, 3.2 * (1 - life) + 1, '#FFD27A', 1 - life)
        glow(c, px, py, 16 * (1 - life) + 4, '#FF9A3C', 0.5 * (1 - life))
    glow(c, 545, 1080, 90, '#FFE0A0', 0.55 + 0.15 * math.sin(t * 40))
    a2 = ramp(t, x.T[2] - 0.2, 0.35)
    if a2 > 0:
        for i, kx2 in enumerate((390, 690)):
            key(c, kx2 - 80 * (1 - a2), 1560, 2.4, -6 + 12 * i, '#D6B04C', a2)
        sparkle(c, 820, 1530, 26 * a2, '#FFFFFF', a2 * (0.6 + 0.4 * math.sin(t * 8)))


STREETS = ['ELM ST', 'OAK AVE', 'MAPLE DR', 'PINE ST', 'BIRCH LN', 'CEDAR CT', 'MAIN ST', 'LAKE RD', 'HILL ST',
           'RIVER RD', 'MILL ST', 'PARK AVE', 'ASH ST', 'ROSE LN', 'GROVE ST', 'FERN WAY', 'SPRUCE ST', 'CHURCH ST']
NAMES = ['MORRISON', 'HAYES', 'PATEL', 'KLINE', 'OKAFOR', 'BRENNAN', 'DUVAL', 'ROSS', 'LEE', 'FOSTER', 'GRANT', 'NOVAK', 'PRICE', 'WEBB', 'YATES']


def drawer(c, t, x):
    grect(c, 0, 0, W, H, ['#2A1F17', '#140E0A'])
    rect(c, 70, 300, 940, 1500, '#5B3F2A')
    rect(c, 70, 300, 940, 1500, '#3E2A1C', sw=10)
    k = 0
    for row in range(7):
        for colm in range(3):
            dx, dy = 110 + colm * 295, 340 + row * 205
            if (row, colm) == (4, 1):
                k += 1
                continue
            rrect(c, dx, dy, 270, 180, 8, '#6B4A31')
            rrect(c, dx + 85, dy + 40, 100, 44, 4, '#C9A44A')
            rect(c, dx + 92, dy + 46, 86, 32, '#EFE6CF')
            text(c, STREETS[k % len(STREETS)], dx + 135, dy + 69, 15, '#3A2A1C', tf='serifb')
            rrect(c, dx + 110, dy + 112, 50, 20, 10, '#8E7230')
            k += 1
    hl = ramp(t, x.T[2], 0.3) * (1 - ramp(t, x.T[3] + 0.4, 0.5))
    dx, dy = 110 + 295, 340 + 4 * 205
    rect(c, dx - 10, dy - 6, 290, 200, '#0E0A07')
    poly(c, [(dx - 30, dy + 150), (dx + 300, dy + 150), (dx + 330, dy + 470), (dx - 60, dy + 470)], '#3A2819')
    poly(c, [(dx - 10, dy + 170), (dx + 280, dy + 170), (dx + 305, dy + 440), (dx - 35, dy + 440)], '#24180F')
    rng = random.Random(5)
    for r_ in range(3):
        for k2 in range(4):
            fx = dx + 20 + k2 * 72 + r_ * 4 - 10
            fy = dy + 200 + r_ * 80
            key(c, fx, fy, 0.75, 70 + rng.random() * 30, rng.choice(['#D6B04C', '#C9CDD2']))
            c.save()
            c.translate(fx + 28, fy + 42)
            c.rotate(-8 + rng.random() * 16)
            rect(c, -34, -12, 68, 24, mix('#EFE6CF', '#FFF7C2', hl))
            text(c, NAMES[(r_ * 4 + k2) % len(NAMES)], 0, 6, 11, '#3A2A1C', tf='bold')
            c.restore()
    rrect(c, dx - 60, dy + 440, 390, 150, 10, '#6B4A31')
    rrect(c, dx + 85, dy + 480, 100, 44, 4, '#C9A44A')
    rect(c, dx + 92, dy + 486, 86, 32, '#EFE6CF')
    text(c, 'ELM ST', dx + 135, dy + 509, 15, '#3A2A1C', tf='serifb')
    rrect(c, dx + 110, dy + 545, 50, 20, 10, '#8E7230')
    glow(c, 540, 1300, 500, '#FFC07A', 0.12)


def drawer_cam(t, x):
    k = ramp(t, x.T[4] - 0.2, 1.4)
    z = 1.75 + (1.0 - 1.75) * k
    return z, 540, 1400 + (960 - 1400) * k


def street(c, t, x):
    grect(c, 0, 0, W, 1250, ['#7F95A6', '#C3CDD4'])
    for i, hx in enumerate((-60, 820)):
        house(c, hx, 1250, 320, 260, ['#8A8F8A', '#7E8792'][i], '#4A4040', '#3E3A3A')
    tree(c, 80, 1390, 1.1, '#3F5A3F')
    tree(c, 1010, 1390, 1.0, '#3A553C')
    rect(c, 0, 1250, W, 260, '#4F6B4A')
    dx, dw = house(c, 290, 1390, 500, 430, '#7F8E99', '#3E3434', '#6E2A2A', door_open=ramp(t, x.T[3] + 0.2, 0.5))
    poly(c, [(820, 1390), (990, 1390), (1080, 1560), (760, 1560)], '#8C8A84')
    rect(c, 0, 1500, W, 80, '#9A9890')
    rect(c, 0, 1580, W, 340, '#45484D')
    for i in range(6):
        rect(c, i * 220 + 20, 1745, 120, 14, '#C9C4A8')
    poly(c, [(dx + 10, 1390), (dx + dw - 10, 1390), (dx + dw + 40, 1500), (dx - 40, 1500)], '#8C8A84')
    k = ramp(t, x.T[2] + 0.3, 2.4)
    car(c, 900 + 700 * k ** 1.6, 1555 + 120 * min(k * 3, 1), 0.95, '#6F7F8C', faces=2)
    wk = ramp(t, x.T[2] + 1.6, (x.T[3] + 0.2) - (x.T[2] + 1.6))
    wx = 150 + (dx + dw / 2 - 150) * wk
    wy = 1660 + (1392 - 1660) * wk
    s = 1.0 - 0.18 * wk
    gone = ramp(t, x.T[3] + 0.5, 0.6)
    walking = 0 < wk < 1
    c.saveLayerAlpha(None, int(255 * (1 - gone)))
    person(c, wx, wy, s, WALTER_OUT, mode='walk' if walking else 'stand', phase=t * 9, expr='stare' if wk < 1 else 'neutral',
           look=0.7 if wk == 0 else 0.2, t=t, seed=2,
           hold=(lambda cc: key(cc, 0, 6, 0.9, 80)) if wk < 1 else None, arms=(6, 6))
    c.restore()


def room_living(c, wall='#5D6B5B'):
    grect(c, 0, 0, W, 1460, [wall, dk(wall, 0.75)])
    floor_planks(c, 1460, H, '#4A3A2E', '#2E241C')
    rect(c, 0, 1440, W, 24, dk(wall, 0.6))


def living(c, t, x):
    room_living(c)
    window(c, 90, 540, 300, 400, '#3B2F28', ('#9FB6C9', '#DCE3E6'), inner=lambda cc, a, b, w, h: tree(cc, a + 150, b + h + 120, 0.9, '#55704F'))
    rect(c, 60, 500, 40, 520, '#7A5A6A')
    rect(c, 380, 500, 40, 520, '#7A5A6A')
    frame_pic(c, 520, 560, 160, 200)
    frame_pic(c, 720, 600, 130, 160, inner='#7C6E62')
    lamp(c, 940, 1440, 1.0)
    couch(c, 540, 1520, 780, '#7A4B3A', 'back')
    nap = ramp(t, x.T[3] + 0.1, 0.6)
    reading = ramp(t, x.T[1] - 0.15, 0.3) * (1 - ramp(t, x.T[2] - 0.15, 0.25))
    drinking = ramp(t, x.T[2] - 0.1, 0.35) * (1 - ramp(t, x.T[3], 0.3))
    if reading > 0.5:
        arms = ((15, -110), (15, -110))
        hold = lambda cc: paper(cc, -20, -10, 90, 110, -4, lines=5)
    elif drinking > 0.5:
        arms = (10, (-50, 168))
        hold = lambda cc: mug(cc, 4, 6, 0.75, '#2F6E8E', handle=-1)
    else:
        arms = ((18, -60), (18, -60))
        hold = None
    person(c, 540, 1420, 1.15, WALTER_OUT, mode='sit', legs=False, expr='sleep' if nap > 0.5 else 'smile', arms=arms,
           t=t, seed=3, hold=hold, rot=-5 * nap, look=0.0)
    couch(c, 540, 1520, 780, '#7A4B3A', 'front')
    if nap > 0:
        for i in range(3):
            ph = (t * 0.6 + i / 3) % 1.0
            text(c, 'z', 610 + 70 * ph + i * 12, 1090 - 170 * ph, 50 + 18 * i, '#ffffff', nap * (1 - ph), sw=6)
    ctable(c, 540, 1660, 600, '#3E2C20')
    paper(c, 400, 1630, 110, 70, 8, '#EFE9DC', lines=2)
    paper(c, 470, 1636, 110, 70, -6, '#F3EFE6', lines=2)
    if drinking < 0.5:
        mug(c, 700, 1612, 0.8, '#2F6E8E', handle=1)


def putback(c, t, x):
    grect(c, 0, 0, W, H, ['#4E5A4C', '#323B31'])
    rect(c, 130, 520, 820, 1180, '#5C4330')
    rect(c, 150, 540, 780, 1140, '#3A2A1E')
    shelves = [880, 1220, 1560]
    for sy in shelves:
        rect(c, 140, sy, 800, 26, '#6E5038')
    rng = random.Random(11)
    cols = ['#7A2E2E', '#2E4A6E', '#4E6B3A', '#8E6E2E', '#5A3A6E', '#2E6B6B', '#6E4A2E', '#3A3A3A']
    for si, sy in enumerate(shelves):
        xx = 170
        while xx < 880:
            bw = rng.randint(34, 58)
            bh = rng.randint(220, 300)
            if si == 0 and xx > 600:
                break
            if si == 1 and 690 < xx < 790:
                xx += 100
                continue
            book(c, xx, sy - bh, bw, bh, rng.choice(cols))
            xx += bw + 4
    flip = ramp(t, x.T[2] + 0.1, 0.45)
    cx, cy = 790, 812
    c.save()
    c.translate(cx, cy)
    sx = math.cos(math.pi * flip)
    c.scale(max(abs(sx), 0.05), 1)
    mug(c, 0, 0, 1.8, '#B03A2E', handle=1 if sx >= 0 else -1)
    c.restore()
    if flip > 0:
        glow(c, cx, cy, 160, '#FFFFFF', 0.12 * (1 - ramp(t, x.T[2] + 1.4, 0.8)))
    mv = ramp(t, x.T[3] + 0.1, 0.7)
    bx = 640 + (712 - 640) * mv
    by = (880 - 250) + ((1220 - 250) - (880 - 250)) * mv - math.sin(math.pi * mv) * 90
    book(c, bx, by, 52, 250, '#2E4A6E')
    if 0 < mv < 1:
        for i in range(6):
            circ(c, bx + 26 + (i - 3) * 14 * mv, 1220 - 6 - 20 * mv * (i % 2), 6 * (1 - mv), '#C9C1B4', 0.6 * (1 - mv))


def putback_cam(t, x):
    a = ramp(t, x.T[1] - 0.1, 0.8)
    b = ramp(t, x.T[3], 0.8)
    z = 1.0 + 0.22 * a - 0.06 * b
    fx = 540 + (790 - 540) * a + (700 - 790) * b
    fy = 1100 + (830 - 1100) * a + (1050 - 830) * b
    return z, fx, fy


def kitchen(c, wall='#9A8F7E', light='#E8EEF0'):
    grect(c, 0, 0, W, H, [wall, dk(wall, 0.72)])
    window(c, 380, 540, 320, 330, '#E9E4DA', ('#B7C8D3', light), panes=True)
    for x0 in (40, 740):
        rrect(c, x0, 520, 300, 330, 8, '#5E6B73')
        line(c, x0 + 150, 530, x0 + 150, 840, '#4C575E', 4)
        rect(c, x0 + 120, 760, 8, 50, '#C9CDD2')
        rect(c, x0 + 172, 760, 8, 50, '#C9CDD2')
    rect(c, 0, 1360, W, 560, '#5E6B73')
    rect(c, 0, 1340, W, 34, '#D8D2C4')
    for x0 in (60, 400, 740):
        rrect(c, x0, 1420, 280, 420, 8, '#55626A')
        rect(c, x0 + 120, 1450, 40, 8, '#C9CDD2')


WOMAN = dict(skin=SKIN['mid'], hair='long', hair_col='#5A3A26', top='#7A4E6E', pants='#2F3340')
MAN = dict(skin=SKIN['light'], hair='short', hair_col='#3A2A20', top='#4E6E5A', pants='#2F3340', collar='#DADADA')


def couple(c, t, x):
    kitchen(c)
    shrug = ramp(t, x.T[1] - 0.1, 0.35) * (1 - ramp(t, x.T[2] - 0.1, 0.3))
    if shrug > 0.5:
        wa, ma = ((28, 78), (28, 78)), ((28, 78), (28, 78))
        wh = mh = None
    else:
        wa = ((18, -95), (18, -95))
        wh = lambda cc: mug(cc, -18, -24, 0.9, '#B03A2E', handle=-1)
        ma = ((25, 175), 6)
        mh = None
    shake = math.sin(t * 6) * 0.5 if t > x.T[2] else 0
    person(c, 360, 1790, 1.27, WOMAN, expr='worried', arms=wa, hold=wh, look=0.4 + shake, t=t, seed=4)
    person(c, 730, 1800, 1.3, MAN, expr='worried', arms=ma, hold=mh, look=-0.4 + shake, t=t, seed=5)
    if t < x.T[1] - 0.1:
        book(c, 640, 1420, 46, 210, '#2E4A6E')


def mainst(c, t, x):
    grect(c, 0, 0, W, 700, ['#8FA5B5', '#C8D2D8'])
    shops = [(-40, 'BAKERY', '#8C5A4A', '#E9C9A0'), (330, 'LOCKSMITH', '#4A5A6A', '#D9B25A'), (720, 'DINER', '#6A4A5A', '#E0D6C6')]
    for sx, name, cl, aw in shops:
        rect(c, sx, 560, 400, 950, cl)
        rect(c, sx, 560, 400, 40, dk(cl, 0.8))
        for wx in (sx + 50, sx + 230):
            rect(c, wx, 640, 120, 180, '#2B3540')
            rect(c, wx, 640, 120, 180, '#E9E4DA', sw=8)
        rect(c, sx + 30, 900, 340, 70, '#1F1A16')
        text(c, name, sx + 200, 950, 40, aw, tf='serifb')
        for i in range(8):
            poly(c, [(sx + 20 + i * 45, 1000), (sx + 65 + i * 45, 1000), (sx + 75 + i * 45, 1080), (sx + 10 + i * 45, 1080)], aw if i % 2 else '#F2EEE6')
        rect(c, sx + 40, 1100, 320, 300, '#2B3540')
        rect(c, sx + 40, 1100, 320, 300, '#E9E4DA', sw=8)
        rect(c, sx + 150, 1180, 100, 330, dk(cl, 0.7))
    rect(c, 0, 1500, W, 230, '#A29F96')
    rect(c, 0, 1730, W, 190, '#4B4E53')
    wave = 150 + 18 * math.sin(t * 9)
    person(c, 540, 1690, 1.22, WALTER_OUT, expr='smile', arms=(6, wave), t=t, seed=6)
    k = clamp(t / max(x.dur, 0.1))
    person(c, -60 + 260 * k, 1760, 0.95, dict(WOMAN, top='#4E6E8E', hair='bun', hair_col='#2E2420'), mode='walk', phase=t * 8,
           expr='smile', arms=(6, 140 + 10 * math.sin(t * 9)), look=0.8, t=t, seed=7)
    person(c, 1140 - 260 * k, 1770, 1.0, dict(MAN, top='#7A6A4E', hair='side'), mode='walk', phase=t * 8 + 1, expr='smile',
           arms=(150 + 10 * math.sin(t * 9 + 1), 6), look=-0.8, t=t, seed=8)


def morrison_room(c, t):
    grect(c, 0, 0, W, 1470, ['#55495A', '#2E2733'])
    floor_planks(c, 1470, H + 500, '#3D2F28', '#211915')
    window(c, 640, 480, 340, 460, '#2A2228', ('#D8C49A', '#F0E2C0'), panes=False)
    for i in range(12):
        rect(c, 640, 480 + i * 38, 340, 18, '#3A3036')
    for i in range(5):
        poly(c, [(640 - 40 * i, 520 + i * 70), (990 - 40 * i, 520 + i * 70), (600 - 300 - 40 * i, 1560 + i * 50), (250 - 300 - 40 * i, 1560 + i * 50)], '#F0D9A8', 0.05)
    couch(c, 300, 1500, 560, '#4E3A46')
    frame_pic(c, 150, 600, 220, 160, inner='#6E6A78')


def morrison(c, t, x):
    morrison_room(c, t)
    wk = ramp(t, 0.2, x.T[2] - 0.2)
    wx = 1180 + (700 - 1180) * wk
    exp = 'shock' if t > x.T[3] + 0.2 else ('neutral' if wk >= 1 else 'stare')
    person(c, wx, 1780, 1.25, WALTER_OUT, mode='walk' if 0 < wk < 1 else 'stand', phase=t * 8, expr=exp,
           look=-0.7 if wk >= 1 else -0.3, t=t, seed=9, arms=(6, 6))
    ctable(c, 520, 1650, 560, '#3B2B22')
    c.save()
    c.translate(520, 1625)
    c.rotate(-8)
    rect(c, -52, -16, 104, 30, '#F2EFE8')
    rect(c, -44, -12, 88, 18, '#2A2A35')
    c.restore()
    if t > x.T[3]:
        glow(c, 520, 1625, 120, '#FFFFFF', 0.18 * ramp(t, x.T[3], 0.4))


def morrison_cam(t, x):
    k = ramp(t, x.T[3] + 0.1, 1.2)
    return 1.0 + 0.9 * k, 540 + (520 - 540) * k, 960 + (1625 - 960) * k, 540, 960 + (1150 - 960) * k


def sleeper(c, cx, cy, s, L, t):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    rrect(c, -170, -150, 340, 130, 50, '#DAD7D0')
    circ(c, 0, -80, 52, L['skin'])
    for sx in (-1, 1):
        oval(c, sx * 48, -84, 10, 22, L['hair_col'])
    for sx in (-18, 18):
        p = skia.Path()
        p.moveTo(sx - 8, -84)
        p.quadTo(sx, -78, sx + 8, -84)
        c.drawPath(p, P('#26211F', sw=3.4))
    if L.get('mustache'):
        rrect(c, -16, -66, 32, 9, 4, L['mustache'])
    line(c, -6, -56, 6, -56, '#6B3A32', 3.5)
    rrect(c, -230, -40, 460, 420, 40, '#3B4A66')
    line(c, -230, -10, 230, -10, '#4A5A78', 10)
    c.restore()


def photo(c, t, x):
    grect(c, 0, 0, W, H, ['#3B2B22', '#24190F'])
    for i in range(14):
        line(c, 0, 120 + i * 130, W, 140 + i * 130, '#2E2018', 4, 0.6)
    c.save()
    c.translate(540, 1080)
    c.rotate(-4)
    rect(c, -310, -360, 640, 760, '#000000', 0.45, blur=18)
    rect(c, -320, -380, 640, 760, '#F2EFE8')
    c.save()
    c.clipRect(R(-280, -340, 560, 560))
    rect(c, -280, -340, 560, 560, '#1A1C24')
    sleeper(c, 0, -30, 1.0, WALTER_NIGHT, t)
    rect(c, 150, -330, 140, 120, '#2A2420')
    text(c, '3:12', 220, -258, 36, '#FF5A4A', tf='mono')
    c.drawRect(R(-280, -340, 560, 560), P('#ffffff', shader=rgrad(0, -80, 430, [('#000000', 0), ('#000000', 0.15), ('#000000', 0.8)], [0, 0.55, 1])))
    glow(c, 0, -100, 300, '#FFFFFF', 0.12)
    c.restore()
    text(c, '3:12 AM', 0, 300, 52, '#3A3A48', tf='serifi')
    c.restore()


def photo_cam(t, x):
    steps = [ramp(t, T, 0.5) for T in x.T[1:4]]
    z = 1.0 + 0.16 * steps[0] + 0.16 * steps[1] + 0.22 * steps[2]
    k = sum(steps) / 3
    return z, 540 + (530 - 540) * k, 1100 + (990 - 1100) * k


def locks(c, t, x):
    grect(c, 0, 0, W, H, ['#1F2A3A', '#121822'])
    glow(c, 150, 700, 420, '#FFCF8A', 0.18)
    rect(c, 120, 640, 40, 60, '#C9A44A')
    floor_planks(c, 1640, H, '#1E222B', '#11141A')
    rect(c, 300, 480, 480, 1170, '#2A1E16')
    rect(c, 330, 510, 420, 1140, '#5A3A2A')
    rect(c, 380, 560, 320, 160, '#8FB4D9', 0.35)
    for i in range(2):
        rrect(c, 380, 780 + i * 420, 320, 360, 10, '#4E3224', sw=8)
    n = 1 + int(t > 0.9) + int(t > x.T[1] - 0.1) + int(t > x.T[1] + 0.5)
    new = ramp(t, x.T[2], 0.3)
    lock_col = mix('#C9A44A', '#D9DEE3', new)
    for i in range(n):
        ly = 900 + i * 150
        rrect(c, 660, ly, 70, 90, 10, lock_col)
        circ(c, 695, ly + 45, 12, dk(lock_col, 0.5))
        if t < [0, 0.9, x.T[1] - 0.1, x.T[1] + 0.5][i] + 0.25:
            glow(c, 695, ly + 45, 90, '#FFE9B0', 0.5)
    if new > 0:
        for i in range(n):
            sparkle(c, 735, 900 + i * 150, 22 * new, '#FFFFFF', new * (0.5 + 0.5 * math.sin(t * 9 + i)))
    def drill(cc):
        rrect(cc, -10, -8, 36, 78, 10, '#2B2B2B')
        rrect(cc, -70, -52, 130, 52, 18, '#C0392B')
        rect(cc, -96, -38, 30, 24, '#6E757C')
        rect(cc, -150, -30, 56, 8, '#AAB2BA')
    person(c, 900, 1800, 1.25, WALTER_NIGHT, expr='worried', arms=(6, (40, -95)), hold=drill, look=-0.8, t=t, seed=10)


def awake(c, t, x):
    sun = ramp(t, x.T[2] - 0.3, 1.6)
    grect(c, 0, 0, W, H, [mix('#141B2B', '#3A3036', sun), mix('#0B0F18', '#1E1A1E', sun)])
    window(c, 90, 460, 320, 440, '#1A1F2A', (mix('#2A3A5A', '#E8A878', sun), mix('#5A6E8E', '#F6D9A8', sun)))
    poly(c, [(90, 900), (410, 900), (900, 1650), (300, 1650)], mix('#8FB4D9', '#FFD9A8', sun), 0.08 + 0.06 * sun)
    rrect(c, 260, 1080, 760, 300, 20, '#2E2018')
    rect(c, 240, 1360, 800, 560, '#22180F')
    person(c, 640, 1490, 1.15, WALTER_NIGHT, mode='sit', expr='stare', arms=(10, 10), look=math.sin(t * 1.3) * 0.9, t=t, seed=11, blink=False)
    rrect(c, 230, 1440, 820, 420, 40, '#3B4A66')
    line(c, 230, 1470, 1050, 1470, '#4A5A78', 12)
    rect(c, 40, 1380, 160, 300, '#2A1E16')
    times = ['3:12', '4:47', '5:58']
    idx = sum(1 for T in x.T if t >= T - 0.1) - 1
    tm = times[max(0, min(idx, 2))]
    glow(c, 120, 1340, 110, '#FF5A4A', 0.25)
    rrect(c, 50, 1300, 140, 80, 10, '#141414')
    text(c, tm, 120, 1355, 44, '#FF5A4A', tf='mono')


def mugscene(c, t, x):
    kitchen(c, '#AEB6B8', '#F2F5F6')
    glow(c, 540, 700, 700, '#FFFFFF', 0.18)
    person(c, 780, 1650, 1.4, WALTER_NIGHT, expr='shock' if t > x.T[1] else 'stare', arms=(6, 6), look=-0.9, t=t, seed=12, blink=False)
    rect(c, 0, 1360, W, 560, '#5E6B73')
    rect(c, 0, 1340, W, 34, '#D8D2C4')
    for x0 in (60, 400, 740):
        rrect(c, x0, 1420, 280, 420, 8, '#55626A')
        rect(c, x0 + 120, 1450, 40, 8, '#C9CDD2')
    rrect(c, 90, 1150, 150, 200, 14, '#2B2B2E')
    rect(c, 110, 1180, 110, 70, '#1A1A1C')
    oval(c, 400, 1342, 80, 12, '#000000', 0.25, blur=6)
    mug(c, 400, 1290, 2.1, '#2F6E8E', handle=-1, steam=0.8, t=t)
    if t > x.T[2]:
        glow(c, 400, 1260, 220, '#FFFFFF', 0.12 * ramp(t, x.T[2], 0.3))


def mug_cam(t, x):
    k = ramp(t, 0, x.T[2] + 0.4)
    k2 = ramp(t, x.T[2], 0.6)
    return 1.0 + 0.12 * k + 0.2 * k2, 540 + (420 - 540) * k, 1100 + (1260 - 1100) * k


SCENES = {
    'shop': dict(draw=shop, cam=(1.0, 1.1, 540, 1150), cap_y=820),
    'cutting': dict(draw=cutting, cam=(1.22, 1.32, 540, 1120), cap_y=560),
    'drawer': dict(draw=drawer, cam=drawer_cam, cap_y=760),
    'street': dict(draw=street, cam=(1.0, 1.05, 540, 1300), cap_y=700),
    'living': dict(draw=living, cam=(1.0, 1.07, 540, 1300), cap_y=760),
    'putback': dict(draw=putback, cam=putback_cam, cap_y=430),
    'couple': dict(draw=couple, cam=(1.0, 1.06, 540, 1300), cap_y=1000),
    'mainst': dict(draw=mainst, cam=(1.0, 1.06, 540, 1300), cap_y=780),
    'morrison': dict(draw=morrison, cam=morrison_cam, cap_y=760),
    'photo': dict(draw=photo, cam=photo_cam, cap_y=1720),
    'locks': dict(draw=locks, cam=(1.0, 1.08, 600, 1100), cap_y=330),
    'awake': dict(draw=awake, cam=(1.0, 1.08, 640, 1200), cap_y=330),
    'mug': dict(draw=mugscene, cam=mug_cam, cap_y=760),
}
