"""TWO PATHS. - split screen. Top (A): the guy who listens to the shadow. Bottom (B): the guy who doesn't. The same
365 days side by side, ending on 'A or B?'. Captions sit in the band between the halves."""
import math

from motivation import (kit, hu, music, W, H, R, P, rect, rrect, line, circ, oval, glow, grect, poly, ease, eout, ramp,
                        clamp, mix, text, spaced, room, beam, dust, window, poster, bed, blanket, sleeper, nightstand, couch,
                        noise_hit, wind, thump, beep, put, SR, env, NIGHT, CAP, TEXT_ON)
import five_more_minutes as fmm

NAME = 'two_paths'
RED = '#FF3B3B'
GOLD = '#FFC93C'
BAND_Y, BAND_H = 850, 120
TOP_H, BOT_Y = BAND_Y, BAND_Y + BAND_H
BOT_H = H - BOT_Y

SCRIPT = [
    dict(scene='alarm', text='Same alarm.', dur=1.5, style='cap', key=['alarm'], pre=0.0),
    dict(scene='alarm', v='sha', text='five more minutes...', pre=0.15, pos=(420, 236), size=84),
    dict(scene='alarm', v='nar', text='Same voice.', key=['voice'], pre=0.3),
    dict(scene='alarm', v='nar', text='Two | different answers.', key=['different'], pre=0.1),
    dict(scene='d30', v='nar', text='One stays | comfortable.', key=['comfortable'], pre=0.6),
    dict(scene='d30', v='nar', text='One gets | uncomfortable.', key=['uncomfortable'], pre=0.15),
    dict(scene='d90', v='nar', text='One waits | for motivation.', key=['motivation'], pre=0.6),
    dict(scene='d90', v='nar', text="One doesn't | need it.", key=['need'], pre=0.15),
    dict(scene='d180', v='nar', text='The voice | grows.', key=['grows'], pre=0.6),
    dict(scene='d180', v='nar', text='Or | it fades.', key=['fades'], pre=0.15),
    dict(scene='d365', v='nar', text='Same person.', key=['person'], pre=0.6),
    dict(scene='d365', v='nar', text='Same year.', key=['year'], pre=0.15),
    dict(scene='d365', v='nar', text='Which one | are you | becoming?', key=['becoming'], pre=0.3),
    dict(scene='d365', text='A or B?', dur=2.4, style='word', pre=0.3, pos=(540, BAND_Y + BAND_H / 2), size=96),
]


class FX:
    """Line times for a borrowed scene, so it plays its own beat inside this one."""
    def __init__(self, x, T=None, E=None):
        self.T = x.T if T is None else T
        self.E = x.E if E is None else E
        self.dur = x.dur


def half(c, draw, t, x, top, h, wy0, sc=1.0, cx=540, zoom=0.05):
    """Draws a full-frame scene into one half: world (cx, wy0) at the half's top centre, scaled sc, slowly pushing in."""
    z = sc * (1 + zoom * ease(t / max(x.dur, 0.1)))
    wc = wy0 + h / 2 / sc
    c.save()
    c.clipRect(R(0, top, W, h))
    c.translate(540, top + h / 2)
    c.scale(z, z)
    c.translate(-cx, -wc)
    draw(c, t, x)
    c.restore()


def split(a, b, crop_a=(760, 1.0), crop_b=(820, 1.0)):
    def draw(c, t, x):
        half(c, a, t, x, 0, TOP_H, crop_a[0], crop_a[1])
        half(c, b, t, x, BOT_Y, BOT_H, crop_b[0], crop_b[1])
    return draw


def band(c, t, x):
    """The bar between the halves (captions go in it) and the A / B badges."""
    rect(c, 0, BAND_Y, W, BAND_H, '#06070E', 0.94)
    line(c, 0, BAND_Y, W, BAND_Y, '#FFFFFF', w=2, a=0.18, cap='butt')
    line(c, 0, BAND_Y + BAND_H, W, BAND_Y + BAND_H, '#FFFFFF', w=2, a=0.18, cap='butt')
    if not TEXT_ON[0]:
        return
    for lab, y, cl in (('A', 300, RED), ('B', BOT_Y + 70, GOLD)):
        circ(c, 74, y, 40, cl, 0.25, blur=14)
        circ(c, 74, y, 34, cl)
        spaced(c, lab, 74, y + 17, 46, '#0B0B10', 1.0, 'pop')


# ---------------------------------------------------------------- day 1: the alarm
def bedroom(c, t, x, ring):
    fmm.bedroom(c, t, ring=ring)


def alarm_shadow(c, t, x, s=1.45, leave=0.0):
    rise = ease((t - (x.T[1] - 1.1)) / 1.2)
    al = clamp(rise * 1.4) * (1 - ease(leave * 1.6))
    if rise <= 0:
        return 0.0
    glow(c, 720, 1150, 620, RED, 0.17 * al)
    c.save()
    c.clipRect(R(-500, -500, W + 1000, 2050))
    pose = dict(torso=30.0, head=18.0, la=(24.0, 60.0), ra=('ik', (560 + 8 * math.sin(1.7 * t), 1280), -1),
                ll=(0.0, 0.0), rl=(0.0, 0.0))
    j = hu.figure(c, 780, 1600 + 700 * (1 - rise), s, pose, flip=True, scheme='shadow', alpha=max(al, 0.0),
                  ground_shadow=0)
    hu.wisps(c, j, t, s, a=al)
    hu.scatter(c, j, s, leave)
    c.restore()
    return al


def a_alarm(c, t, x):
    bedroom(c, t, x, 1.0 if t < x.T[1] - 0.25 else 0.0)
    al = alarm_shadow(c, t, x)
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    hu.light(dir=(-0.5, -0.86), lit=NIGHT['lit'], shade=NIGHT['shade'], rim=RED, rim_a=0.45 * al, glow=0.08)
    sleeper(c, 442, 1320, 0.95, t, expr='closed')
    blanket(c, t, NIGHT, cover=ramp(t, x.T[3] + 0.2, 0.8), x0=540, x1=1110, top=1360)


def b_alarm(c, t, x):
    bedroom(c, t, x, 1.0 if t < x.T[1] - 0.25 else 0.0)
    up = ramp(t, x.T[3] + 0.2, 0.3)
    al = alarm_shadow(c, t, x, leave=ramp(t, x.T[3] + 0.2, 0.9))
    bed(c, NIGHT, 300, 1120, 1360, 1600)
    hu.light(dir=(-0.5, -0.86), lit=NIGHT['lit'], shade=NIGHT['shade'], rim=RED, rim_a=0.45 * al * (1 - up), glow=0.08)
    if up < 1:
        c.saveLayerAlpha(None, int(255 * (1 - up)))
        sleeper(c, 442, 1320, 0.95, t, expr='closed' if t < x.T[2] else 'open', brows=ramp(t, x.T[2], 0.3))
        blanket(c, t, NIGHT, x0=540, x1=1110, top=1360)
        c.restore()
    if up > 0:
        c.saveLayerAlpha(None, int(255 * up))
        grr_blanket(c)
        st = ease(ramp(t, x.T[3] + 0.3, 0.6))
        pose = hu.lerp_pose(hu.stand(), dict(hu.arms_up(), head=-20.0), st)
        hu.figure(c, 700, 1700, 1.0, pose, expr='smile', brows=0.4, look=(0.4, -0.2))
        c.restore()


def grr_blanket(c):
    """The blanket thrown back to the foot of the bed."""
    p = kit.path([(820, 1362), (900, 1310), (1000, 1300), (1110, 1330), (1110, 1470), (820, 1470)])
    c.drawPath(p, P('#ffffff', shader=kit.lgrad(0, 1300, 0, 1470, list(NIGHT['blanket']))))


# ---------------------------------------------------------------- day 30
def a_couch(c, t, x):
    room(c, NIGHT, 1600)
    window(c, 60, 380, 300, 400, NIGHT, t)
    couch(c, 520, 900, 1400, 1600, ('#4A4070', '#352E56'))
    sp = dict(hu.sit(), torso=-14.0, head=10.0, la=(20.0, 60.0), ra=('ik', (662, 1196), -1))
    js = hu.figure(c, 570, 0, 1.0, sp, hip_y=1388, scheme='shadow', ground_shadow=0, glow_a=0.4)
    hu.wisps(c, js, t, 1.0, a=0.7, n=10)
    hu.light(dir=(0.3, -0.95), lit='#DCE8FF', shade=NIGHT['shade'], rim=RED, rim_a=0.3, glow=0.06)
    pose = dict(hu.sit_slump(), la=('ik', (728, 1306), -1), ra=('ik', (744, 1310), -1))
    j = hu.figure(c, 660, 0, 1.0, pose, hip_y=1388, expr='tired', look=(0.6, 0.8), ground_shadow=0)
    hx, hy = j['ra'][1]
    hu.phone(c, hx + 4, hy - 24, 0.85, rot=30, t=t, glow_a=0.9)


def b_run(c, t, x):
    fmm.sc_run(c, t, x)


# ---------------------------------------------------------------- day 90
def a_desk(c, t, x):
    fmm.sc_desk_fail(c, t, FX(x, T=[-2.0, 0.2], E=[-1.0, x.dur - 0.45]))


def b_study(c, t, x):
    fmm.sc_study(c, t, FX(x, T=[-5.0, -2.0], E=[-4.0, -1.5]))


# ---------------------------------------------------------------- day 180
def a_grows(c, t, x):
    room(c, NIGHT, 1600)
    window(c, 60, 380, 300, 400, dict(NIGHT, sky=('#0E1230', '#1E2550')), t, moon=None, stars=6)
    g = ease(clamp(t / x.dur))
    s = 1.5 + 0.7 * g
    glow(c, 640, 1100, 700, RED, 0.18 + 0.12 * g)
    pose = dict(torso=22.0, head=22.0, la=(20.0, 50.0), ra=('ik', (500, 1330), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
    js = hu.figure(c, 700, 1600, s, pose, flip=True, scheme='shadow', ground_shadow=0)
    hu.wisps(c, js, t, s, a=1.0)
    hu.light(dir=(-0.5, -0.86), lit=NIGHT['shade'], shade=mix(NIGHT['shade'], '#000000', 0.3), rim=RED, rim_a=0.5, glow=0.0)
    hu.figure(c, 460, 0, 0.9, dict(hu.sit_slump(), head=34.0, ll=(70.0, -20.0), rl=(64.0, -26.0)), hip_y=1545,
              expr='sad', look=(0.3, 0.9), ground_shadow=0.4)


def b_fades(c, t, x):
    fmm.sc_boxing(c, t, FX(x, T=[-3.0, -2.0, 0.0], E=[-2.5, 0.0, x.E[1]]))


# ---------------------------------------------------------------- day 365
def a_final(c, t, x):
    room(c, dict(NIGHT, wall=('#1A1C36', '#0E0F20'), floor=('#0E0F20', '#07070F')), 1600)
    glow(c, 600, 1000, 800, RED, 0.25)
    s = 2.4 + 0.15 * ease(clamp(t / x.dur))
    pose = dict(torso=8.0, head=26.0, la=(24.0, 60.0), ra=(30.0, 70.0), ll=(-4.0, -2.0), rl=(4.0, 2.0))
    js = hu.figure(c, 720, 1640, s, pose, flip=True, scheme='shadow', ground_shadow=0)
    hu.wisps(c, js, t, s, a=1.0, n=24)
    hu.light(dir=(0.5, -0.86), lit=mix(NIGHT['shade'], '#FF8080', 0.25), shade=mix(NIGHT['shade'], '#000000', 0.35),
             rim=RED, rim_a=0.6, glow=0.0)
    hu.figure(c, 380, 0, 0.8, dict(hu.sit_slump(), head=36.0, ll=(70.0, -20.0), rl=(64.0, -26.0)), hip_y=1560,
              expr='tired', look=(0.2, 0.9), ground_shadow=0.4)


def b_final(c, t, x):
    fmm.sc_summit(c, t, FX(x, T=[0.2, 1.2]))


SCENES = {
    'alarm': dict(draw=split(a_alarm, b_alarm, (780, 1.0), (840, 1.0)), cam=(1.0, 1.0, 540, 960), cap_y=BAND_Y + BAND_H / 2,
                  vig=0.6, day_pos=(880, 232), day=1, overlay=band),
    'd30': dict(draw=split(a_couch, b_run, (780, 1.0), (760, 1.0)), cam=(1.0, 1.0, 540, 960), cap_y=BAND_Y + BAND_H / 2,
                vig=0.6, day_pos=(880, 232), day=30, overlay=band),
    'd90': dict(draw=split(a_desk, b_study, (780, 1.0), (800, 1.0)), cam=(1.0, 1.0, 540, 960), cap_y=BAND_Y + BAND_H / 2,
                vig=0.6, day_pos=(880, 232), day=90, overlay=band),
    'd180': dict(draw=split(a_grows, b_fades, (600, 0.8), (780, 1.0)), cam=(1.0, 1.0, 540, 960), cap_y=BAND_Y + BAND_H / 2,
                 vig=0.6, day_pos=(880, 232), day=180, overlay=band),
    'd365': dict(draw=split(a_final, b_final, (470, 0.72), (820, 1.0)), cam=(1.0, 1.0, 540, 960), cap_y=BAND_Y + BAND_H / 2,
                 vig=0.6, day_pos=(880, 232), day=365, overlay=band),
}

SCORE = dict(root=50.0, dark_notes=[62, 69, 65, 62, 69, 67], dark_every=1.6, turn='d30', title='d30', end='d365',
             bpm=118, chords=[(50, 53, 57), (46, 50, 53), (48, 52, 55), (45, 48, 52)], end_chord=[50, 53, 57, 62],
             end_melody=[74, 69, 65], duck=0.6)


def SFX(tl, spans, rng):
    out = []
    first = tl['lines'][1]['start']
    tt = 0.2
    while tt < first - 0.35:
        out += [(tt + k * 0.13, beep(), 1.0) for k in range(3)]
        tt += 0.62
    for name in ('d30', 'd90', 'd180', 'd365'):
        out.append((spans[name]['start'] - 0.3, music.sfx('whoosh'), 0.35))
    r = spans['d30']
    k = 0
    while r['start'] + k / (2 * fmm.RUN_HZ) < r['end']:
        out.append((r['start'] + k / (2 * fmm.RUN_HZ), noise_hit(rng, 80, 500, 0.15, 0.04), 0.25))
        k += 1
    bx = spans['d180']
    ln = [l_ for l_ in tl['lines'] if l_['scene'] == 'd180']
    fx = FX(type('X', (), {'T': None, 'E': None, 'dur': 0})(), T=[-3.0, -2.0, 0.0], E=[-2.5, 0.0, ln[1]['end'] - bx['start']])
    for tk, arm_, pw in fmm.punches(fx):
        th = bx['start'] + tk + fmm.HIT_DT
        out += [(th, thump(70 if pw < 2 else 48, 0.08 if pw < 2 else 0.2), 0.35 * min(pw, 2.0))]
        if pw > 2:
            out.append((th, music.sfx('boom'), 0.7))
    sm = spans['d365']
    out.append((sm['start'], wind(sm['end'] - sm['start'], rng), 0.15))
    return out


def THUMB_T(tl):
    d = [l_ for l_ in tl['lines'] if l_['scene'] == 'd180']
    return d[1]['start'] + 0.2
