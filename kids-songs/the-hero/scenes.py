"""The Hero: one draw function per scene, plus the camera and caption position for each (the SCENES table at the end).

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

VICTOR = dict(skin=SKIN['light'], hair='side', hair_col='#CFCBC6', top='#1F3A5F', stripe='#E8E8E8', pants='#1E2430', shoe='#E8E8E8')
VICTOR_SUIT = dict(VICTOR, top='#22262E', tie='#7A1E2A', shirt='#F2F2F2', stripe=None, shoe='#1B1B20', pants='#22262E')
LEO_POOR = dict(skin=SKIN['tan'], hair='beanie', hair_col='#3A2A20', beanie='#5B4A3A', beard=True, beard_col='#3A2A20',
                top='#5A5A3A', patch='#6E6A4E', pants='#3E3A34', shoe='#2B2621')
LEO_RICH = dict(skin=SKIN['tan'], hair='short', hair_col='#2E221A', beard=True, beard_col='#2E221A', beard_a=0.85,
                top='#2C2F36', tie='#2E4A6E', shirt='#F2F2F2', pants='#2C2F36')
LEO_JOG = dict(LEO_RICH, top='#1F3A5F', stripe='#E8E8E8', tie=None, shirt=None, pants='#1E2430', shoe='#E8E8E8')
SON = dict(skin=SKIN['light'], hair='side', hair_col='#5A4632', top='#3A3F4A', tie='#5A2E2E', shirt='#EDEDED', pants='#2E323B')
DAUGHTER = dict(skin=SKIN['light'], hair='long', hair_col='#C9A15A', top='#6E2E3E', dress=True, necklace='#E8D18A')
JUDGE = dict(skin=SKIN['mid'], hair='bald', hair_col='#CFCBC6', top='#141418', glasses=True)
YOUNG = dict(skin=SKIN['mid'], hair='messy', hair_col='#2A1E16', top='#4A4E44', hood=True, patch='#5E5A4A', pants='#33302B',
             beard=True, beard_col='#2A1E16', beard_a=0.3, shoe='#2B2621')


def river_bg(c, t, fogk=0.35, warm=1.0, night=0.0):
    sky = [mix('#2B3A55', '#0C1220', night), mix(mix('#4E5470', '#6E6A86', warm), '#141C2C', night),
           mix(mix('#9A8C8A', '#D99A78', warm), '#1E2A3A', night)]
    grect(c, -500, 0, W + 1000, 1160, sky, [0, 0.6, 1])
    if night < 1:
        glow(c, 760, 1120, 520, '#FFC48A', 0.35 * warm * (1 - night))
    else:
        circ(c, 820, 360, 50, '#DDE6F0', 0.9)
        glow(c, 820, 360, 260, '#9FB6D9', 0.25)
    rng = random.Random(4)
    for i in range(-3, 13):
        bx = i * 130 - 20
        bh = 60 + rng.random() * 150
        rect(c, bx, 1150 - bh, 90, bh, mix('#3A4256', '#0E1420', night), 0.6)
    for i in range(-6, 23):
        circ(c, i * 75, 1150 + rng.random() * 10, 50 + rng.random() * 30, mix('#2A3340', '#0A0F18', night))
    fog(c, 1040, 260, fogk, '#D9DEE3' if night < 0.5 else '#7E8DA6', t, 6)
    grect(c, -500, 1160, W + 1000, 330, [mix('#3A5468', '#0F1C28', night), mix('#22323F', '#0A121A', night)])
    for i in range(14):
        yy = 1190 + i * 20
        xx = (i * 173 + t * 30) % W
        line(c, xx - 60, yy, xx + 60, yy, '#FFC48A' if night < 0.5 else '#BFD3EA', 3, 0.25 * (1 - 0.5 * night))


def railing(c, broken=0.0, gap=(470, 650), night=0.0):
    pc = mix('#2B2F36', '#14171C', night)
    for px in range(-470, W + 480, 120):
        rect(c, px - 6, 1470, 12, 100, pc)
    x0, x1 = gap
    for yy, w in ((1480, 9), (1522, 6)):
        line(c, -500, yy, x0, yy, pc, w)
        line(c, x1, yy, W + 500, yy, pc, w)
        if broken <= 0:
            line(c, x0, yy, x1, yy, pc, w)
        else:
            ang = math.radians(70 * broken)
            ln = x1 - x0
            line(c, x0, yy, x0 + ln * math.cos(ang), yy - ln * math.sin(ang) * 0.6, pc, w)


def path_fg(c, night=0.0):
    grect(c, -500, 1560, W + 1000, 760, [mix('#9C8F7C', '#2A2C33', night), mix('#7E735F', '#1C1E24', night)])
    rect(c, -500, 1556, W + 1000, 8, mix('#6E6352', '#15171C', night))


def lamp_post(c, x, night=0.0, on=0.4):
    rect(c, x - 7, 900, 14, 660, '#23262C')
    rrect(c, x - 30, 870, 60, 44, 10, '#23262C')
    glow(c, x, 900, 220, '#FFE0A8', on)


def jog(c, t, x):
    river_bg(c, t)
    lamp_post(c, 160)
    railing(c)
    path_fg(c)
    text(c, '5:00 AM', 900, 330, 44, '#FFFFFF', 0.85 * ramp(t, 0.3, 0.5), tf='mono')
    if t > x.T[5] - 0.2:
        g = ramp(t, x.T[5] - 0.2, 0.6)
        for i in range(6):
            gx = 80 + i * 180
            c.saveLayerAlpha(None, int(60 * g))
            person(c, gx, 1820, 1.2, VICTOR, mode='walk', phase=i * 1.1, arms=((20, -70), (20, -70)), expr='neutral', look=0.6, t=t, seed=i)
            c.restore()
    k = t / max(x.dur, 0.1)
    person(c, -120 + 1330 * k, 1820, 1.25, VICTOR, mode='walk', phase=t * 11, arms=((20, -70), (20, -70)), expr='neutral', look=0.7, t=t, seed=1)


def railing_scene(c, t, x):
    river_bg(c, t, fogk=0.6, warm=0.6)
    fog(c, 1250, 300, 0.45, '#D9DEE3', t, -4)
    brk = ramp(t, x.T[3] + 0.1, 0.5)
    railing(c, brk)
    path_fg(c)
    fall = ramp(t, x.T[3] + 0.15, 0.7)
    stretch = ramp(t, x.T[1], 0.3) * (1 - ramp(t, x.T[2] - 0.1, 0.3))
    lean = ramp(t, x.T[2], 0.4)
    arms = (165, 165) if stretch > 0.5 else ((28, 28) if lean > 0.5 else (8, 8))
    if fall < 1:
        a = int(255 * (1 - ramp(t, x.T[3] + 0.5, 0.35)))
        c.saveLayerAlpha(None, a)
        person(c, 560, 1830 - 420 * fall, 1.25 - 0.4 * fall, VICTOR, arms=arms, back=True, rot=-6 * lean + 25 * fall, t=t)
        c.restore()
    if t > x.T[3] + 0.5:
        sp = t - (x.T[3] + 0.5)
        for i in range(18):
            rs = random.Random(i * 31)
            ang = math.radians(200 + rs.random() * 140)
            v = 300 + rs.random() * 300
            px = 560 + math.cos(ang) * v * sp
            py = 1360 + math.sin(ang) * v * sp + 900 * sp * sp
            if sp < 0.9:
                circ(c, px, py, 7 * (1 - sp), '#DDEBF5', 0.9 * (1 - sp))
        for k2 in range(3):
            rr = 40 + (sp * 160 + k2 * 60) % 260
            oval(c, 560, 1360, rr, rr * 0.25, '#DDEBF5', max(0, 0.5 - rr / 520), sw=4)


def water(c, t, x):
    grect(c, 0, 0, W, H, ['#33505F', '#14232D', '#0A141A'], [0, 0.5, 1])
    fog(c, 300, 500, 0.35, '#CFD8DE', t, 8)
    for k2 in range(5):
        rr = (t * 140 + k2 * 110) % 560
        oval(c, 540, 1180, rr, rr * 0.22, '#BFD3E0', max(0, 0.45 - rr / 1300), sw=5)
    for i, (ix, iy) in enumerate(((170, 1050), (890, 1120), (260, 1500), (850, 1620))):
        poly(c, [(ix - 60, iy), (ix - 10, iy - 22), (ix + 70, iy - 10), (ix + 40, iy + 16), (ix - 40, iy + 14)], '#D7E4EC', 0.55)
    j = math.sin(t * 40) * 3
    flail = math.sin(t * 7)
    person(c, 540 + j, 1640, 1.3, VICTOR, arms=(135 + 25 * flail, 150 - 25 * flail), expr='shock', look=0.3 * flail, t=t, wet=True)
    grect(c, 0, 1160, W, 760, [('#1C3442', 0.92), ('#0C1820', 1.0)])
    line(c, 0, 1162, W, 1162, '#BFD3E0', 4, 0.5)
    for i in range(10):
        rs = random.Random(i)
        ph = (t * 0.8 + rs.random()) % 1.0
        circ(c, 300 + rs.random() * 480, 1700 - ph * 520, 6 + rs.random() * 8, '#BFD3E0', 0.6 * (1 - ph), sw=3)


def bank_bg(c, t):
    grect(c, 0, 0, W, 900, ['#4E5470', '#9A8C8A'])
    fog(c, 760, 260, 0.5, '#D9DEE3', t, 5)
    grect(c, 0, 900, W, 560, ['#3A5468', '#22323F'])
    poly(c, [(0, 1380), (300, 1330), (700, 1360), (1080, 1300), (1080, 1920), (0, 1920)], '#5A5244')
    poly(c, [(0, 1440), (400, 1400), (1080, 1380), (1080, 1920), (0, 1920)], '#4A4338')
    for i in range(8):
        rs = random.Random(i + 40)
        line(c, rs.random() * W, 1420 + rs.random() * 400, rs.random() * W, 1430 + rs.random() * 400, '#3E382F', 3, 0.5)


def rescue(c, t, x):
    bank_bg(c, t)
    jt = x.T[1]
    if t < x.T[2] - 0.15:
        k = ramp(t, jt, 0.6)
        lx = 820 + (430 - 820) * k
        ly = 1660 - math.sin(math.pi * k) * 260 + (1150 - 1660) * k * k * (0 if k < 1 else 1)
        if k < 1:
            person(c, lx, 1660 - math.sin(math.pi * k) * 260 - 500 * k * k, 1.15, LEO_POOR,
                   arms=(150, 150) if k > 0 else (6, 6), expr='shock' if k > 0 else 'worried', look=-0.8, t=t, rot=-30 * k, seed=3)
        if t > jt + 0.5:
            sp = t - (jt + 0.5)
            for i in range(16):
                rs = random.Random(i * 13)
                ang = math.radians(200 + rs.random() * 140)
                v = 260 + rs.random() * 260
                if sp < 0.8:
                    circ(c, 430 + math.cos(ang) * v * sp, 1180 + math.sin(ang) * v * sp + 800 * sp * sp, 7 * (1 - sp), '#DDEBF5', 0.9)
        for k2 in range(3):
            rr = 30 + (t * 120 + k2 * 70) % 300
            oval(c, 330, 1120, rr, rr * 0.25, '#DDEBF5', max(0, 0.4 - rr / 750), sw=4)
    else:
        person(c, 110, 1660, 1.15, VICTOR, rot=90, expr='sleep', arms=(4, 4), t=t, wet=True)
        breath = math.sin(t * 5) * 4
        person(c, 880, 1700 + breath * 0.3, 1.2, LEO_POOR, arms=((30, 60), 8), expr='worried', look=-0.9, t=t, wet=True, seed=3)


def viral(c, t, x):
    grect(c, 0, 0, W, H, ['#1A1F2A', '#0D1016'])
    rng = random.Random(9)
    for i in range(14):
        glow(c, rng.random() * W, rng.random() * H, 60 + rng.random() * 90, rng.choice(['#FFB870', '#8FB4D9', '#D98FB4']), 0.12)
    views = int(10_000_000 * eout(ramp(t, x.T[1] + 0.3, 1.6) if t > x.T[1] else 0) ** 1.0)
    views = int(10_000_000 * clamp((t - x.T[1] - 0.2) / 1.6) ** 0.6) if t > x.T[1] + 0.2 else int(1200 + t * 3000)

    def screen(cc, sx, sy, sw_, sh):
        grect(cc, sx, sy, sw_, sh, ['#101418', '#101418'])
        vy = sy + 220
        grect(cc, sx, vy, sw_, 400, ['#6E6A86', '#9A8C8A'])
        rect(cc, sx, vy + 220, sw_, 180, '#2E4A5A')
        poly(cc, [(sx, vy + 330), (sx + sw_, vy + 300), (sx + sw_, vy + 400), (sx, vy + 400)], '#5A5244')
        cc.save()
        cc.translate(sx + 170, vy + 330)
        person(cc, 0, 0, 0.32, VICTOR, rot=-90, expr='sleep', t=t)
        cc.restore()
        person(cc, sx + 330, vy + 360, 0.36, LEO_POOR, arms=((30, 60), 8), expr='worried', look=-0.8, t=t, seed=3)
        rect(cc, sx, vy + 390, sw_ * clamp(t / x.dur), 10, '#FF2E2E')
        rrect(cc, sx + 20, sy + 40, sw_ - 40, 130, 12, '#C8102E')
        text(cc, 'HOMELESS MAN SAVES', sx + sw_ / 2, sy + 96, 34, '#FFFFFF')
        text(cc, 'BILLIONAIRE', sx + sw_ / 2, sy + 144, 40, '#FFFFFF')
        text(cc, f'{views:,} views', sx + sw_ / 2, vy + 500, 46, '#FFFFFF')
        text(cc, 'Billionaire pulled from freezing river', sx + 30, vy + 580, 24, '#C9CED6', tf='reg', align='left')
        for i in range(5):
            ph = (t * 0.7 + i * 0.21) % 1.0
            hx = sx + sw_ - 70 + 20 * math.sin(ph * 9 + i)
            hy = sy + sh - 60 - ph * 380
            circ(cc, hx - 9, hy, 11, '#FF3B5C', 1 - ph)
            circ(cc, hx + 9, hy, 11, '#FF3B5C', 1 - ph)
            poly(cc, [(hx - 20, hy + 4), (hx + 20, hy + 4), (hx, hy + 26)], '#FF3B5C', 1 - ph)
    phone(c, 540, 1120, 600, 1160, -2 + math.sin(t * 1.5), screen=screen)


def dining_bg(c):
    grect(c, -500, 0, W + 1000, H + 300, ['#3A2026', '#1E1014'])
    rect(c, -500, 1100, W + 1000, 1120, '#2A1418')
    for i in range(-3, 9):
        rect(c, 30 + i * 175, 1150, 140, 260, '#3A1E24', sw=6)
    frame_pic(c, 90, 560, 280, 340, '#C9A25A', '#5A4E3A', fig=False)
    frame_pic(c, 710, 560, 280, 340, '#C9A25A', '#3E4A3A', fig=False)
    line(c, 540, 0, 540, 260, '#C9A25A', 4)
    for i in range(7):
        a = math.radians(200 + i * 23)
        line(c, 540, 300, 540 + 150 * math.cos(a), 300 - 60 * math.sin(a) + 40, '#C9A25A', 5)
        circ(c, 540 + 150 * math.cos(a), 300 - 60 * math.sin(a) + 30, 10, '#FFE9B0')
    glow(c, 540, 320, 520, '#FFD9A0', 0.3)


def table_fg(c, y=1450):
    rect(c, 0, y, W, 500, '#F1ECE2')
    rect(c, 0, y, W, 16, '#D9D2C4')
    for px in (200, 540, 880):
        oval(c, px, y + 90, 110, 34, '#FFFFFF')
        oval(c, px, y + 90, 70, 20, '#E6E0D4')
    for cx in (150, 930):
        rect(c, cx - 10, y - 110, 20, 110, '#F2E6C9')
        circ(c, cx, y - 126, 9, '#FFB84A')
        glow(c, cx, y - 126, 90, '#FFB84A', 0.4)


def mansion(c, t, x):
    dining_bg(c)
    hand = ramp(t, x.T[0] + 0.3, 0.4)
    person(c, 400, 1700, 1.25, VICTOR_SUIT, expr='smile', arms=(6, 6 + 64 * hand), look=0.6, t=t, seed=2)
    person(c, 720, 1700, 1.25, LEO_RICH, expr='smile', arms=(6, 6), look=-0.5, t=t, seed=3)
    table_fg(c)


def kids(c, t, x):
    dining_bg(c)
    point = ramp(t, x.T[1] - 0.1, 0.3)
    person(c, 1150, 1760, 1.15, VICTOR_SUIT, back=True, arms=(6, 6), t=t)
    person(c, 330, 1800, 1.3, SON, expr='angry', arms=((22, -100), (22, -100)), look=0.5, t=t, seed=4)
    person(c, 690, 1800, 1.3, DAUGHTER, expr='angry', arms=(6, 6 + 74 * point), look=0.7, t=t, seed=5)


def kids_cam(t, x):
    k = ramp(t, x.T[2] - 0.1, 0.8)
    return 1.0 + 0.05 * k, 540 + 340 * k, 1300, 540, 1300


def will(c, t, x):
    grect(c, 0, 0, W, H, ['#4A3226', '#2A1C14'])
    for i in range(12):
        line(c, 0, 100 + i * 160, W, 130 + i * 160, '#3A281E', 4, 0.6)
    c.save()
    c.translate(540, 1080)
    c.rotate(-2)
    rect(c, -300, -400, 620, 820, '#000000', 0.4, blur=16)
    rect(c, -310, -420, 620, 840, '#F4EFE4')
    text(c, 'LAST WILL', 0, -320, 44, '#2A2420', tf='serifb')
    text(c, 'AND TESTAMENT', 0, -268, 32, '#2A2420', tf='serifb')
    text(c, 'of Victor Hale', 0, -220, 26, '#4A4440', tf='serifi')
    for i in range(6):
        line(c, -240, -150 + i * 34, 240 - (60 if i % 3 == 2 else 0), -150 + i * 34, '#A49E94', 4)
    hl = ramp(t, x.T[1] + 0.2, 0.6)
    rect(c, -250, 66, 500 * hl, 46, '#F6E27A', 0.85)
    text(c, '50% of my estate to', 0, 98, 28, '#2A2420', tf='serifi')
    text(c, 'Leo Marsh', 0, 142, 34, '#2A2420', tf='serifb')
    for i in range(3):
        line(c, -240, 190 + i * 34, 200, 190 + i * 34, '#A49E94', 4)
    line(c, -40, 350, 260, 350, '#4A4440', 3)
    text(c, 'Signed', -100, 356, 22, '#4A4440', tf='serifi')
    sg = ramp(t, x.T[2] - 0.1, 1.4)
    pts = []
    n = 80
    for i in range(int(n * sg) + 1):
        u = i / n
        pts.append((-20 + 260 * u + 14 * math.sin(u * 30), 330 - 26 * math.sin(u * 18) * (1 - u * 0.5)))
    if len(pts) > 1:
        pa = skia.Path()
        pa.moveTo(*pts[0])
        for q in pts[1:]:
            pa.lineTo(*q)
        c.drawPath(pa, P('#1A2A5A', sw=4))
    c.restore()
    if 0 < sg:
        px, py = pts[-1] if pts else (0, 0)
        c.save()
        c.translate(540 + px, 1080 + py)
        c.rotate(-30)
        rrect(c, -8, -190, 16, 190, 6, '#1B1B1E')
        rect(c, -8, -190, 16, 30, '#C9A44A')
        poly(c, [(-8, 0), (8, 0), (0, 22)], '#C9A44A')
        c.restore()


def funeral(c, t, x):
    grect(c, 0, 0, W, H, ['#16131A', '#0B090D'])
    rect(c, 140, 1420, 800, 500, '#E8E4DC')
    rect(c, 140, 1420, 800, 18, '#CFC9BE')
    c.save()
    rect(c, 300, 620, 480, 620, '#2A2420')
    rect(c, 320, 640, 440, 580, '#C9A25A', sw=8)
    c.clipRect(R(330, 650, 420, 560))
    grect(c, 330, 650, 420, 560, ['#5A6470', '#3A4048'])
    person(c, 540, 1560, 1.15, VICTOR_SUIT, expr='smile', arms=(6, 6), t=0, blink=False)
    c.restore()
    poly(c, [(620, 640), (780, 640), (780, 800)], '#0A0A0A')
    for fx in (210, 870):
        for k in range(5):
            a = math.radians(k * 72 + 18)
            oval(c, fx + 34 * math.cos(a), 1330 + 34 * math.sin(a), 26, 16, '#F4F1EA')
        circ(c, fx, 1330, 14, '#E8D18A')
        line(c, fx, 1350, fx, 1420, '#4E6B3A', 8)
    for cx in (390, 690):
        rect(c, cx - 16, 1260, 32, 160, '#F2E6C9')
        fl = 1 + 0.15 * math.sin(t * 13 + cx)
        oval(c, cx, 1236, 10 * fl, 22 * fl, '#FFB84A')
        glow(c, cx, 1236, 140 * fl, '#FFB84A', 0.35)


def inherit(c, t, x):
    grect(c, 0, 0, W, H, ['#0E1A14', '#050A08'])
    glow(c, 540, 800, 700, '#E8C35A', 0.2)
    k = clamp((t - x.T[1] + 0.1) / 1.3)
    val = int(400_000_000 * eout(k)) if t > x.T[1] - 0.1 else 0
    text(c, f'${val:,}', 540, 860, 98, '#F2CF62', tf='bold', sw=8, scol='#3A2A0A')
    rs = random.Random(2)
    for i in range(24):
        ph = (t * 0.5 + rs.random()) % 1.0
        gx = rs.random() * W
        oval(c, gx, -40 + ph * 2000, 18, 8 + 8 * abs(math.sin(t * 5 + i)), '#E8C35A', 0.8)
    person(c, 540, 2050, 1.55, LEO_RICH, expr='sinister' if t > x.T[1] else 'neutral', arms=(6, 6), t=t, seed=3)


def court(c, t, x):
    grect(c, 0, 0, W, H, ['#4A3222', '#2A1C12'])
    for i in range(8):
        rect(c, i * 140, 0, 6, 1300, '#3A2618')
    circ(c, 540, 560, 110, '#C9A44A')
    circ(c, 540, 560, 90, '#8E7230')
    text(c, '⚖', 540, 600, 90, '#E8D18A', tf='reg')
    bang = ramp(t, x.T[1] - 0.1, 0.12) * (1 - ramp(t, x.T[1] + 0.1, 0.25))
    person(c, 540, 1300, 1.0, JUDGE, expr='neutral', arms=(6, (30 + 90 * (1 - bang), 140 * (1 - bang) + 40)), t=t, seed=7)
    rect(c, 220, 1050, 640, 300, '#5A3A26')
    rect(c, 200, 1030, 680, 34, '#6E4A32')
    if t > x.T[1]:
        sw_ = t - x.T[1]
        if sw_ < 0.6:
            oval(c, 760, 1030, 60 + 300 * sw_, 18 + 60 * sw_, '#FFFFFF', 0.5 * (1 - sw_ / 0.6), sw=5)
    rect(c, 0, 1350, W, 570, '#3A2618')
    lost = t > x.T[1]
    person(c, 190, 1900, 1.15, SON, expr='sad' if lost else 'angry', arms=(6, 6), look=0.4, t=t, seed=4)
    person(c, 420, 1900, 1.15, DAUGHTER, expr='sad' if lost else 'angry', arms=(6, 6), look=0.5, t=t, seed=5)
    person(c, 860, 1900, 1.18, LEO_RICH, expr='sinister' if t > x.T[3] + 0.3 else 'smile', arms=(6, 6), look=-0.3, t=t, seed=3)
    rect(c, 0, 1640, W, 40, '#5A3A26')


def reveal(c, t, x):
    night = ramp(t, x.T[4] - 0.25, 0.5)
    if night < 1:
        c.saveLayerAlpha(None, int(255 * (1 - night)))
        river_bg(c, t, fogk=0.65, warm=0.35)
        railing(c)
        path_fg(c)
        rect(c, 640, 1610, 300, 26, '#4A3A2E')
        rect(c, 660, 1636, 14, 70, '#2E241C')
        rect(c, 906, 1636, 14, 70, '#2E241C')
        person(c, 790, 1620, 1.2, LEO_POOR, mode='sit', expr='stare', arms=((18, -95), (18, -95)), look=-0.8, t=t, seed=3,
               hold=lambda cc: rrect(cc, -36, -50, 70, 90, 6, '#E8E2D2'), shin=95)
        k = clamp(t / 4.0)
        person(c, -100 + 700 * k, 1830, 0.9, VICTOR, mode='walk', phase=t * 11, arms=((20, -70), (20, -70)), look=0.7, t=t)
        nb = ramp(t, x.T[1], 0.5)
        if nb > 0:
            c.save()
            c.translate(540, 560)
            c.rotate(3)
            rect(c, -230, -170, 460, 340, '#000000', 0.4 * nb, blur=12)
            rect(c, -240, -180, 460, 340, '#EDE6D2', nb)
            for i, d in enumerate(['MON', 'TUE', 'WED', 'THU', 'FRI']):
                yy = -120 + i * 58
                text(c, d, -200, yy, 30, '#3A3A48', nb, tf='serifi', align='left')
                text(c, '5:00 AM', -70, yy, 30, '#3A3A48', nb, tf='serifi', align='left')
                cx_ = -70 + tw('5:00 AM  ', 30, 'serifi')   # DejaVu Serif has no ✓ glyph, so the tick is a path
                c.drawPath(path([(cx_, yy - 12), (cx_ + 8, yy - 2), (cx_ + 24, yy - 24)], close=False), P('#3A3A48', nb, sw=4))
                line(c, -210, yy + 14, 200, yy + 14, '#B8B0A0', 2, nb)
            c.restore()
        c.restore()
    if night > 0:
        c.saveLayerAlpha(None, int(255 * night))
        river_bg(c, t, fogk=0.5, warm=0.0, night=1.0)
        railing(c, night=1.0)
        path_fg(c, night=1.0)
        tw_ = math.sin(t * 10) * 25
        person(c, 600, 1820, 1.25, LEO_POOR, arms=((30, -60), 6), expr='sinister' if t > x.T[5] + 0.2 else 'stare',
               look=0.8 if t < x.T[5] + 0.2 else 0.0, t=t, seed=3, hold=lambda cc: wrench(cc, 6, -10, 1.0, -110 + tw_))
        for bx in (470, 590):
            circ(c, bx, 1500, 8, '#BFC6CE')
            sparkle(c, bx + 6, 1494, 14, '#FFFFFF', 0.4 + 0.4 * math.sin(t * 7 + bx))
        if t > x.T[5]:
            ft = t - x.T[5]
            circ(c, 470, min(1500 + 600 * ft * ft, 1700), 8, '#BFC6CE')
        grect(c, 0, 0, W, H, [('#0A1428', 0.25), ('#0A1428', 0.35)])
        c.restore()


def present(c, t, x):
    river_bg(c, t, fogk=0.4, warm=1.0)
    lamp_post(c, 160)
    railing(c)
    path_fg(c)
    rect(c, 720, 1610, 300, 26, '#4A3A2E')
    rect(c, 740, 1636, 14, 70, '#2E241C')
    rect(c, 986, 1636, 14, 70, '#2E241C')
    end_x = 1300
    k = clamp(t / (x.T[6] + 0.5))
    lx = -120 + (end_x + 120) * k
    look_dir = clamp((lx - 870) / 400, -1, 1)
    sx_ = 870
    if True:
        person(c, sx_, 1622, 1.2, YOUNG, mode='sit', expr='stare', arms=((18, -60), (18, -60)), look=look_dir * (1 - ramp(t, x.T[6] + 0.1, 0.5)), t=t, seed=8, shin=95, blink=t < x.T[6])
    text(c, '5:00 AM', 900, 330, 44, '#FFFFFF', 0.85 * ramp(t, x.T[1] - 0.2, 0.5) * (1 - ramp(t, x.T[3] + 0.6, 0.5)), tf='mono')
    person(c, lx, 1830, 1.25, LEO_JOG, mode='walk', phase=t * 11, arms=((20, -70), (20, -70)), expr='smile', look=0.7, t=t, seed=3)


def present_cam(t, x):
    k = ramp(t, x.T[4] - 0.2, 1.6)
    k2 = ramp(t, x.T[6] - 0.1, 2.2)
    z = 1.0 + 0.45 * k + 0.6 * k2
    fx = 540 + (870 - 540) * k
    fy = 960 + (1250 - 960) * k + (1330 - 1250) * k2
    sy = 960 + (1000 - 960) * k
    return z, fx, fy, 540, sy


SCENES = {
    'jog': dict(draw=jog, cam=(1.0, 1.05, 540, 1400), cap_y=760),
    'railing': dict(draw=railing_scene, cam=(1.12, 1.2, 560, 1450), cap_y=760),
    'water': dict(draw=water, cam=(1.0, 1.08, 540, 1200), cap_y=560),
    'rescue': dict(draw=rescue, cam=(1.0, 1.05, 540, 1400), cap_y=640),
    'viral': dict(draw=viral, cam=(1.0, 1.06, 540, 1100), cap_y=330),
    'mansion': dict(draw=mansion, cam=(1.0, 1.06, 540, 1300), cap_y=760),
    'kids': dict(draw=kids, cam=kids_cam, cap_y=760),
    'will': dict(draw=will, cam=(1.18, 1.28, 540, 1120), cap_y=340),
    'funeral': dict(draw=funeral, cam=(1.0, 1.07, 540, 1000), cap_y=420),
    'inherit': dict(draw=inherit, cam=(1.0, 1.05, 540, 1000), cap_y=420),
    'court': dict(draw=court, cam=(1.0, 1.05, 540, 1200), cap_y=330),
    'reveal': dict(draw=reveal, cam=(1.0, 1.08, 600, 1500), cap_y=1000),
    'present': dict(draw=present, cam=present_cam, cap_y=760),
}
