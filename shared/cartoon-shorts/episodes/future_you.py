"""FUTURE YOU. - a knock at midnight: his 70-year-old self in the doorway. He never started anything; the shadow
told him he had time. He fades; the young one starts: running, guitar, painting, studying. 50 years later the old man
is smiling, and says thank you."""
import math

import numpy as np
import skia

from motivation import (kit, hu, music, W, H, R, P, rect, rrect, line, circ, oval, glow, grect, poly, ease, eout, ramp,
                        clamp, mix, text, room, beam, dust, window, couch, painting, grr, noise_hit, wind, thump, piano, put,
                        SR, env, NIGHT, WARM, DAWN)
import five_more_minutes as fmm
import one_more_video as omv
import when_im_ready as wir

NAME = 'future_you'
RED = '#FF3B3B'
FLOOR = 1600
DX, DW, DTOP = 770, 240, 1050          # the doorway
OLD_LIGHT = dict(dir=(-0.6, -0.8), lit='#ECEAF2', shade='#8C88A0', rim='#CFE0FF', rim_a=0.6, glow=0.1)

SCRIPT = [
    dict(scene='couch', text='knock knock.', dur=1.4, style='cap', pre=0.9, pos=(540, 640)),
    dict(scene='door', v='nar', text='Who | are you?', key=['who'], pre=0.5),
    dict(scene='door', v='old', text="Don't be scared, | kid.", key=['scared'], pre=0.3),
    dict(scene='door', v='old', text="I'm you. | Fifty years | from now.", key=['fifty'], pre=0.25),
    dict(scene='regrets', v='old', text='I never | started anything.', key=['never'], pre=0.6),
    dict(scene='regrets', v='old', text='I always said | tomorrow.', key=['tomorrow'], pre=0.2),
    dict(scene='voice', v='sha', text='you have time.', pre=0.7, pos=(380, 800)),
    dict(scene='voice', v='old', text="That's what | it told me | too.", key=['too'], pre=0.3),
    dict(scene='fade', v='old', text="Don't | waste it.", key=['waste'], pre=0.5),
    dict(scene='fade', text='·fade', dur=1.0, style='none'),
    dict(scene='start', text='DAY 1', dur=1.3, style='title', pos=(540, 900)),
    dict(scene='run', text='·run', dur=1.5, style='none'),
    dict(scene='guitar', text='·guitar', dur=1.4, style='none'),
    dict(scene='paint', text='·paint', dur=1.4, style='none'),
    dict(scene='study', text='·study', dur=1.4, style='none'),
    dict(scene='later', text='50 YEARS LATER', dur=1.8, style='title', pos=(540, 380), size=96, pre=0.1),
    dict(scene='later', v='old', text='Thank you.', key=['thank'], pre=0.4),
    dict(scene='later', text='future you is watching.', dur=2.8, style='word', pre=0.4, pos=(540, 380), size=70),
]


class FX:
    def __init__(self, x, T=None, E=None):
        self.T = x.T if T is None else T
        self.E = x.E if E is None else E
        self.dur = x.dur


def talk(t, spans):
    """An open mouth on alternate beats while one of `spans` (start, end) is being spoken, else None."""
    for a, b in spans:
        if a <= t <= b:
            return 'o' if (t * 7.0) % 1.0 < 0.5 else 'small'
    return None


# ---------------------------------------------------------------- the room and the door
def doorway(c, t, open_u, glow_a=1.0):
    rect(c, DX - 20, DTOP - 20, DW + 40, FLOOR - DTOP + 20, '#2A2448')
    if open_u > 0:
        grect(c, DX, DTOP, DW, FLOOR - DTOP, [mix('#1A1C3A', '#D7E4FF', open_u), mix('#1A1C3A', '#93A9E6', open_u)])
        glow(c, DX + DW / 2, DTOP + 260, 420, '#C9DAFF', 0.45 * open_u * glow_a)
        beam(c, [(DX, DTOP + 20), (DX, FLOOR), (DX - 560, FLOOR + 160), (DX - 220, FLOOR + 160)], '#C9DAFF', 0.18 * open_u * glow_a)
        c.save()
        c.clipRect(R(DX, DTOP, DW, FLOOR - DTOP))
        for k in range(4):
            fx_ = DX + ((k * 90 + t * 30) % (DW + 160)) - 80
            oval(c, fx_, FLOOR - 40 - 20 * k, 120, 26, '#FFFFFF', 0.22 * open_u, blur=16)
        c.restore()
    pw = DW * (1 - 0.82 * ease(open_u))
    px = DX + DW - pw
    grr(c, px, DTOP, pw, FLOOR - DTOP, 4, ('#5A4632', '#3C2E21'))
    if pw > 60:
        rrect(c, px + 18, DTOP + 40, pw - 36, 180, 6, '#000000', 0.12)
        rrect(c, px + 18, DTOP + 260, pw - 36, 220, 6, '#000000', 0.12)
        circ(c, px + 26, DTOP + 280, 9, '#D9B46A')


def living_room(c, t, open_u=0.0, shake=0.0, glow_a=1.0):
    room(c, NIGHT, FLOOR)
    window(c, 60, 380, 300, 400, NIGHT, t)
    c.save()
    c.translate(shake * 4 * math.sin(t * 90), 0)
    doorway(c, t, open_u, glow_a)
    c.restore()


def old_man(c, x, t, s=1.0, mouth=None, expr='open', look=(0.6, 0.0), alpha=1.0, cane=True, pose=None, view='side',
            flip=True, ground=FLOOR):
    hu.light(**OLD_LIGHT)
    p = pose or dict(hu.stand(), torso=16.0, head=8.0, ra=('ik', (x - 70 * (1 if flip else -1), ground - 210), -1),
                     ll=(-4.0, -2.0), rl=(6.0, 2.0))

    def cane_(c_, j):
        if cane:
            hx, hy = j['ra'][1]
            line(c_, hx, hy - 6, hx - 8 * (1 if flip else -1), ground, '#6A4A30', w=9)
            line(c_, hx - 4, hy - 8, hx + 22 * (-1 if flip else 1), hy - 18, '#6A4A30', w=9)
    return hu.figure(c, x, ground, s, p, flip=flip, view=view, expr=expr, look=look, mouth=mouth, tuft='old', old=True,
                     alpha=alpha, hold=cane_)


# ---------------------------------------------------------------- scenes
def sc_couch(c, t, x):
    knock = 1.0 if (0.95 < t < 1.25 or 1.35 < t < 1.65) else 0.0
    living_room(c, t, shake=knock)
    couch(c, 360, 700, 1400, FLOOR, ('#4A4070', '#352E56'))
    up = ramp(t, 1.0, 0.3)
    hu.light(dir=(0.3, -0.95), lit='#DCE8FF', shade=NIGHT['shade'], glow=0.06)
    pose = dict(hu.sit_slump(), head=34.0 - 40 * up, la=('ik', (568, 1306), -1), ra=('ik', (584, 1310), -1))
    j = hu.figure(c, 500, 0, 1.0, pose, hip_y=1388, expr='tired' if up < 0.5 else 'wide', look=(0.6, 0.8 - 1.0 * up),
                  ground_shadow=0)
    hx, hy = j['ra'][1]
    hu.phone(c, hx + 4, hy - 24, 0.85, rot=30, t=t, glow_a=0.9)


def young(c, t, spans, expr='wide', brows=0.0, look=(0.6, 0.0), pose=None, x=380):
    hu.light(dir=(0.9, -0.4), lit='#E8EEFF', shade=NIGHT['shade'], rim='#C9DAFF', rim_a=0.25, glow=0.08)
    return hu.figure(c, x, FLOOR, 1.0, pose or hu.stand(), expr=expr, brows=brows, look=look, mouth=talk(t, spans))


def sc_door(c, t, x):
    o = ramp(t, 0.0, 0.6)
    living_room(c, t, open_u=o)
    old_man(c, 890, t, mouth=talk(t, [(x.T[1], x.E[1]), (x.T[2], x.E[2])]), expr='smile' if t > x.T[1] else 'open')
    young(c, t, [(x.T[0], x.E[0])], expr='wide')


SNEAKER = '#E8604A'


def sneaker(c, x, y, s, rot):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    p = skia.Path()
    p.moveTo(-60, 10)
    p.cubicTo(-62, -20, -40, -34, -18, -34)
    p.lineTo(10, -14)
    p.cubicTo(30, -10, 60, -8, 64, 8)
    p.lineTo(64, 14)
    p.lineTo(-60, 14)
    p.close()
    c.drawPath(p, P(SNEAKER))
    rect(c, -62, 10, 128, 10, '#F4F0E6')
    for k in range(3):
        line(c, -30 + 10 * k, -26 + 6 * k, -14 + 10 * k, -30 + 6 * k, '#FFFFFF', w=3)
    c.restore()


def sc_regrets(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#141628', '#07080F'])
    cone = kit.path([(470, -200), (610, -200), (900, 1520), (180, 1520)])
    c.drawPath(cone, P('#ffffff', shader=kit.lgrad(0, 0, 0, 1520, [('#C9D3FF', 0.05), ('#C9D3FF', 0.16)]), blur=30))
    oval(c, 540, 1500, 320, 50, '#C9D3FF', 0.16, blur=24)
    dust(c, t, (150, 300, 930, 1500), cl='#C9D3FF', a=0.45, seed=51)
    items = [(lambda cx, cy, a: omv.guitar(c, cx, cy, -60 + 8 * math.sin(t * 0.7), 0.7)),
             (lambda cx, cy, a: (rect(c, cx - 110, cy - 85, 220, 170, '#E9E3D6'), rect(c, cx - 110, cy - 85, 220, 170, '#B9B2A2', sw=3))),
             (lambda cx, cy, a: (sneaker(c, cx - 40, cy, 0.9, -10), sneaker(c, cx + 50, cy + 30, 0.9, 8))),
             (lambda cx, cy, a: grr(c, cx - 90, cy - 60, 180, 120, 8, ('#3F6FB0', '#2E5288')))]
    for k, draw in enumerate(items):
        ang = t * 0.35 + k * math.pi / 2
        cx, cy = 540 + 330 * math.cos(ang), 980 + 130 * math.sin(ang) - 80 * (k % 2)
        draw(cx, cy, 1.0)
        rect(c, cx - 150, cy - 110, 300, 220, '#6E6A7E', 0.0)
    c.save()
    rect(c, -500, -500, W + 1000, H + 1000, '#0A0B14', 0.25)
    c.restore()
    pose = dict(hu.stand(), torso=24.0, head=30.0, ra=('ik', (470, 1290), -1), ll=(-4.0, -2.0), rl=(6.0, 2.0))
    old_man(c, 540, t, s=1.1, pose=pose, expr='sad', look=(0.4, 0.9), ground=1500,
            mouth=talk(t, [(x.T[0], x.E[0]), (x.T[1], x.E[1])]))


def sc_voice(c, t, x):
    living_room(c, t, open_u=1.0)
    a = ramp(t, x.T[0] - 0.8, 0.6)
    if a > 0:
        glow(c, 230, 1050, 520, RED, 0.18 * a)
        sp = dict(torso=24.0, head=20.0, la=(20.0, 50.0), ra=('ik', (392, 1200), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
        js = hu.figure(c, 210, FLOOR, 1.35, sp, scheme='shadow', alpha=a, ground_shadow=0)
        hu.wisps(c, js, t, 1.35, a=a)
    old_man(c, 890, t, mouth=talk(t, [(x.T[1], x.E[1])]), expr='sad', look=(0.7, -0.2))
    young(c, t, [], expr='open', look=(0.6, 0.0))


def sc_fade(c, t, x):
    living_room(c, t, open_u=1.0, glow_a=1.0 + 0.6 * ramp(t, x.E[0] - 0.2, 0.6))
    u = ramp(t, x.T[0] + 0.3, 1.4)
    j = old_man(c, 890, t, mouth=talk(t, [(x.T[0], x.E[0])]), expr='smile', alpha=1 - ease(u))
    if 0 < u < 1:
        rng = np.random.default_rng(7)
        hx, hy = j['head']
        fx_, fy_ = j['hip']
        for _ in range(120):
            w = rng.random()
            bx = fx_ + (hx - fx_) * w + (rng.random() - 0.5) * 120
            by = fy_ + (hy - fy_) * w + (rng.random() - 0.5) * 80 + 150 * rng.random()
            d = clamp(u * 1.3 - rng.random() * 0.3)
            if 0 < d < 1:
                circ(c, bx + (rng.random() - 0.5) * 120 * d, by - 380 * d * (0.5 + rng.random()), 3 + 5 * rng.random(),
                     '#FFF3D6', 0.9 * (1 - d))
    reach = ramp(t, x.T[0] + 0.5, 0.6)
    pose = dict(hu.stand(), ra=('ik', (470 + 120 * reach, 1290 - 60 * reach), -1))
    young(c, t, [], expr='sad' if u > 0.5 else 'open', look=(0.6, -0.1), pose=pose)


def sc_start(c, t, x):
    grect(c, -500, -500, W + 1000, H + 1000, ['#0C0E22', '#121430', '#2A1F3A'], [0, 0.6, 1])
    glow(c, 540, 2000, 1000, DAWN['sun'], 0.3 * ramp(t, 0.05, 0.8))
    dust(c, t, (60, 400, 1020, 1700), cl=DAWN['sun'], a=0.4, seed=8)


def sc_run(c, t, x):
    fmm.sc_run(c, t, x)


def sc_guitar(c, t, x):
    omv.sc_guitar(c, t, x)


def sc_paint(c, t, x):
    wir.sc_again(c, t, x)


def sc_study(c, t, x):
    fmm.sc_study(c, t, FX(x, T=[-5.0, -2.0], E=[-4.0, -1.5]))


def sc_later(c, t, x):
    room(c, dict(WARM, wall=('#B07A58', '#7E5240')), 1560)
    window(c, 720, 540, 260, 330, dict(WARM, frame='#4E3123', sky=('#F7D7A0', '#EC9E60')), t, moon=None, stars=0)
    beam(c, [(720, 560), (720, 870), (240, 1560), (640, 1560)], '#FFE2B0', 0.2)
    dust(c, t, (100, 500, 1000, 1500), cl='#FFE2B0', a=0.5, seed=61)
    for i, (fx_, fy_, w_, h_, sd) in enumerate(((90, 520, 220, 160, 77), (360, 520, 220, 160, 11), (110, 760, 180, 140, 23))):
        rect(c, fx_ - 12 + 8, fy_ - 12 + 12, w_ + 24, h_ + 24, '#000000', 0.35, blur=12)
        rect(c, fx_ - 12, fy_ - 12, w_ + 24, h_ + 24, '#C9A25A')
        painting(c, fx_, fy_, w_, h_, 1.0, seed=sd)
    omv.guitar(c, 860, 1380, -80, 0.8)
    line(c, 830, 1560, 860, 1440, '#3E2619', w=8)
    line(c, 890, 1560, 860, 1440, '#3E2619', w=8)
    hu.light(dir=(0.7, -0.7), lit='#FFF6EA', shade='#B49484', rim='#FFC890', rim_a=0.5, glow=0.14)
    hu.figure(c, 540, 1580, 1.05, dict(hu.stand_front(), head=-4.0), view='front', expr='smile', look=(0.0, -0.1),
              mouth=talk(t, [(x.T[1], x.E[1])]), tuft='old', old=True)


SCENES = {
    'couch': dict(draw=sc_couch, cam=(1.02, 1.08, 600, 1300), cap_y=640, vig=0.72),
    'door': dict(draw=sc_door, cam=(1.0, 1.06, 640, 1300), cap_y=600, vig=0.68),
    'regrets': dict(draw=sc_regrets, cam=(1.0, 1.08, 540, 1100), cap_y=560, vig=0.75),
    'voice': dict(draw=sc_voice, cam=(1.04, 1.1, 560, 1300), cap_y=600, vig=0.7),
    'fade': dict(draw=sc_fade, cam=(1.06, 1.12, 700, 1300), cap_y=600, vig=0.68),
    'start': dict(draw=sc_start, cam=(1.0, 1.0, 540, 960), cap_y=900, vig=0.7),
    'run': dict(draw=sc_run, cam=(1.0, 1.0, 540, 960), cap_y=620, vig=0.55, day=3),
    'guitar': dict(draw=sc_guitar, cam=(1.06, 1.12, 520, 1250), cap_y=780, vig=0.6, day=60),
    'paint': dict(draw=sc_paint, cam=(1.08, 1.16, 420, 1150), cap_y=560, vig=0.6, day=300),
    'study': dict(draw=sc_study, cam=(1.04, 1.1, 560, 1200), cap_y=640, vig=0.66, day=1000),
    'later': dict(draw=sc_later, cam=(1.1, 1.0, 540, 1150), cap_y=380, vig=0.55),
}

SCORE = dict(root=47.0, dark_notes=[59, 66, 62, 59, 66, 64], dark_every=1.8, turn='fade', title='start', end='later',
             bpm=116, chords=[(47, 51, 54), (52, 56, 59), (54, 58, 61), (49, 52, 56)], end_chord=[47, 51, 54, 59],
             end_melody=[71, 66, 63], duck=0.6)


def knock():
    a, b = thump(90, 0.07), noise_hit(np.random.default_rng(2), 200, 1800, 0.08, 0.02) * 0.6
    out = np.zeros(max(len(a), len(b)))
    out[:len(a)] += a
    out[:len(b)] += b
    return out


def SFX(tl, spans, rng):
    out = []
    for tk in (0.98, 1.38):
        out.append((spans['couch']['start'] + tk, knock(), 0.9))
    d = spans['door']
    n = int(0.9 * SR)
    creak = music.bp(rng.standard_normal(n), 300, 900) * env(n, 0.2, 0.4) * np.sin(np.linspace(0, 40, n)) ** 2
    out.append((d['start'], creak, 0.35))
    for name in ('door', 'voice', 'fade'):
        sp = spans[name]
        out.append((sp['start'], wind(sp['end'] - sp['start'], rng), 0.08))
    fl = [ln for ln in tl['lines'] if ln['scene'] == 'fade']
    for k in range(10):
        out.append((fl[0]['start'] + 0.4 + 0.12 * k, piano(84 + [0, 4, 7, 12][k % 4], 1.2, 0.35), 0.18))
    for name in ('run', 'guitar', 'paint', 'study', 'later'):
        out.append((spans[name]['start'] - 0.3, music.sfx('whoosh'), 0.3))
    r = spans['run']
    k = 0
    while r['start'] + k / (2 * fmm.RUN_HZ) < r['end']:
        out.append((r['start'] + k / (2 * fmm.RUN_HZ), noise_hit(rng, 80, 500, 0.15, 0.04), 0.3))
        k += 1
    g = spans['guitar']
    tt, k = g['start'] + 1 / 12, 0
    chords = [(55, 59, 62, 67), (52, 55, 59, 64)]
    while tt < g['end'] - 0.1:
        ch = chords[(k // 4) % 2]
        for i, m in enumerate(ch if k % 2 == 0 else ch[::-1]):
            out.append((tt + 0.012 * i, piano(m, 1.0, 0.5), 0.18))
        tt += 1 / 3
        k += 1
    return out


def THUMB_T(tl):
    d = [ln for ln in tl['lines'] if ln['scene'] == 'door']
    return d[2]['start'] + 0.5


THUMB_CROP = (180, 300, 1080, 1900)
