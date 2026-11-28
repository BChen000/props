"""showcase: the look reels - each cartoon look's people and props on a plain backdrop, with no story and no narration.

  python make_short.py look_whatif     (also look_palace, look_castle, look_desert, look_pill)
Each reel is three shots of about 4 s: the lineup (three people of the look, each holding a prop from its kit), one
action with props (a curl and a dribble, a toast and a raised sword, a walk to an opening door, a sled hauled on wet
sand, an umbrella in the rain), then the prop sheet (the kit's six props popping in on a grid). Music is the look's bed.
reel(look) returns the episode's NAME, SCRIPT, SCENES, SCORE, SFX and THUMB_T.
"""
import math

import numpy as np

import cast
import cast_props as cp
import humanoid as hu
from motivation import W, H, P, rect, grect, circ, oval, line, ease, eout, clamp, SR, env, music

GROUND = 1500
BACKDROPS = dict(
    whatif=dict(wall=('#F6EEE2', '#E7D7C0'), floor=('#D9BE98', '#BE9C72'), spot='#FFFFFF', vig=0.3),
    palace=dict(wall=('#7A2466', '#3A0F3E'), floor=('#A8322E', '#681820'), spot='#FFD27A', vig=0.45, band='#E8B23E'),
    castle=dict(wall=('#C9B79E', '#8E7E6C'), floor=('#8E2E26', '#5A1C16'), spot='#FFE9B0', vig=0.45, tiles=('#E9DCC4', '#9E3A30')),
    desert=dict(wall=('#F0E3C6', '#E6CC94'), floor=('#EBC67E', '#D8A65A'), spot='#FFF6DC', vig=0.3),
    pill=dict(wall=('#D6E8F8', '#A9C9EA'), floor=('#BDB8CF', '#9993B0'), spot='#FFFFFF', vig=0.3, stones=True),
)
CASTS = dict(   # three people per look: outfit, expression, the prop each holds in the lineup
    whatif=[(dict(top='#2BB5A4'), 'smile', 'phone'), (dict(top='#D93A3A', bottom='#2E3F6E', hair='spiky'), 'grin', 'trophy'),
            (dict(top='#3D6FD8', hat='cap', hat_col='#F2C230'), 'smug', 'water_bottle')],
    palace=[(dict(hat='headband'), 'smug', 'goblet'), (dict(hat='crown', beard='white', top='#7A3FB0', trim='#F2C14E'), 'smile', 'scroll'),
            (dict(top='#59606B', robe=False, beard='stubble'), 'worried', 'potion')],
    castle=[(dict(), 'smug', 'key'), (dict(top='#2E4F8E', trim='#E2C46A', hat='helmet', hair=None), 'open', 'axe'),
            (dict(top='#8E2E3A', trim='#E2C46A', hair=None, hat='crown', beard='white'), 'smile', 'bowl')],
    desert=[(dict(), 'grin', 'jug'), (dict(top='#2F5E9E', hair='cloth'), 'smile', 'basket'),
            (dict(top='#6B4A2E', skin='#A8703F'), 'angry', 'oil_lamp')],
    pill=[(dict(top='#3F7FD6'), 'smile', 'mug'), (dict(top='#3C9A4E', hat='hardhat', hair=None), 'grin', 'newspaper'),
          (dict(top='#F08A24', hat='cap', hat_col='#D8343A', hair=None), 'smug', 'briefcase')],
)
SCALE = dict(whatif=1.0, palace=0.86, castle=0.86, desert=1.15, pill=0.95)
HOLD = dict(phone=(0, -10, 1.0, 0), trophy=(0, 0, 0.8, 0), water_bottle=(0, -10, 0.95, 0), goblet=(0, 8, 0.8, 0),
            scroll=(4, 0, 0.62, 0), potion=(0, 6, 0.7, 0), key=(0, 0, 0.7, -30), axe=(0, 0, 0.75, 0), bowl=(0, 20, 0.62, 0),
            jug=(0, 0, 0.7, 0), basket=(0, -6, 0.66, 0), oil_lamp=(0, 0, 0.48, 0), mug=(0, 10, 0.75, 0),
            newspaper=(0, 0, 0.7, -8), balloon=(0, 0, 1.0, 0), dumbbell=(0, 0, 0.8, 90), basketball=(0, 0, 0.9, 0),
            umbrella=(0, 0, 0.9, 0), ice_cream=(0, 0, 0.6, 0), sword=(0, 0, 0.7, 0), torch=(0, 0, 0.8, 0),
            coin_pouch=(0, 0, 0.7, 0), backpack=(0, 0, 0.7, 0), briefcase=(0, -4, 0.62, 0))
SHEET = dict(   # prop sheet: (dx, dy) from the slot centre to the prop's anchor, scale, rot
    dumbbell=(0, 0, 1.3, 0), phone=(0, 0, 1.6, -10), backpack=(0, -80, 1.15, 0), trophy=(0, 60, 1.3, 0),
    basketball=(0, 0, 1.7, 0), water_bottle=(0, 10, 1.5, 0),
    goblet=(0, 50, 1.4, 0), sword=(-30, 100, 0.95, 35), scroll=(0, 0, 1.15, 0), torch=(0, 90, 1.05, 0),
    potion=(0, -40, 1.25, 0), coin_pouch=(0, -60, 1.2, 0),
    door=(0, 150, 0.68, 0), bowl=(0, 60, 1.25, 0), axe=(-20, 100, 0.95, 20), candle=(0, 80, 1.3, 0),
    barrel=(0, 100, 1.1, 0), key=(-60, 0, 1.35, 0),
    block_sled=(-20, 90, 0.85, 0), jug=(-30, 0, 1.3, 0), palm=(-10, 150, 0.55, 0), basket=(0, -30, 1.3, 0),
    rope=(-20, 50, 1.3, 0), oil_lamp=(-80, 10, 1.15, 0),
    mug=(-10, 20, 1.5, 0), umbrella=(0, 110, 0.75, 0), balloon=(0, 140, 0.9, 0), newspaper=(0, 0, 1.15, -6),
    ice_cream=(0, 90, 1.0, 0), briefcase=(0, -60, 1.1, 0),
)
BEDS = dict(
    whatif=dict(kind='bed', bpm=118, root=60, scale='major', lead='pluck', steps=[0, None, 2, 4, None, 4, 2, None],
                chords=[[0, 2, 4], [3, 5, 7], [4, 6, 8], [3, 5, 7]], drums='pop', lead_g=0.45),
    palace=dict(kind='bed', bpm=96, root=57, scale='hijaz', lead='pluck', steps=[0, 1, 2, None, 3, 2, 1, None],
                chords=[[0, 2, 4], [0, 2, 4], [3, 5, 7], [1, 3, 5]], drums='frame', drone=0.12, lead_g=0.5),
    castle=dict(kind='bed', bpm=84, root=50, scale='minor', lead='piano', steps=[0, None, 2, None, 4, None, 2, 1],
                chords=[[0, 2, 4], [5, 7, 9], [3, 5, 7], [4, 6, 8]], drums='frame', drone=0.1, lead_g=0.4),
    desert=dict(kind='bed', bpm=100, root=62, scale='dorian', lead='marimba', steps=[0, 2, 4, 2, 3, None, 1, None],
                chords=[[0, 2, 4], [3, 5, 7]], drums='shaker', lead_g=0.55),
    pill=dict(kind='bed', bpm=124, root=65, scale='major', lead='marimba', steps=[0, 4, 2, 4, 1, 4, 2, None],
              chords=[[0, 2, 4], [3, 5, 7], [1, 3, 5], [4, 6, 8]], drums='pop', lead_g=0.5, drum_g=0.3),
)
SHOTS = (('lineup', 4.2), ('action', 4.4), ('sheet', 4.4))


def pop(k=1.0):
    """A soft pop: a quick downward sine sweep with a click."""
    n = int(0.14 * SR)
    t = np.arange(n) / SR
    f = 900 * k * np.exp(-t / 0.03) + 220 * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.05) * 0.6


def backdrop(c, look, t):
    B = BACKDROPS[look]
    grect(c, -400, -400, W + 800, GROUND + 400, list(B['wall']))
    grect(c, -400, GROUND - 120, W + 800, H + 800 - GROUND, list(B['floor']))
    if B.get('tiles'):
        a, b = B['tiles']
        for row in range(9):
            y0 = GROUND - 120 + 60 * row * (1 + row * 0.12)
            y1 = GROUND - 120 + 60 * (row + 1) * (1 + (row + 1) * 0.12)
            for col in range(-12, 13):
                k0, k1 = 0.55 + 0.45 * row / 9, 0.55 + 0.45 * (row + 1) / 9
                xs = [540 + (col + d) * 130 * kk for d in (0, 1) for kk in (k0, k1)]
                c.drawPath(_quad(xs, y0, y1), P(a if (row + col) % 2 == 0 else b))
        rect(c, -400, GROUND - 126, W + 800, 10, '#6E6A66')
    if B.get('band'):
        rect(c, -400, GROUND - 70, W + 800, 24, B['band'])
        rect(c, -400, GROUND - 40, W + 800, 6, B['band'], 0.7)
    if B.get('stones'):
        rng = np.random.default_rng(3)
        for row in range(8):
            yy = GROUND - 100 + row * (44 + row * 6)
            for k in range(14):
                xx = -60 + k * 90 + (45 if row % 2 else 0) + rng.random() * 10
                oval(c, xx, yy, 40 + row * 3, 16 + row * 2, '#FFFFFF', 0.12)
    circ(c, 540, 900, 760, B['spot'], 0.2, blur=220)
    rect(c, -400, GROUND - 122, W + 800, 4, '#000000', 0.12)


def _quad(xs, y0, y1):
    import skia
    q = skia.Path()
    q.moveTo(xs[0], y0)
    q.lineTo(xs[2], y0)
    q.lineTo(xs[3], y1)
    q.lineTo(xs[1], y1)
    q.close()
    return q


def draw_prop(c, name, x, y, s, look, rot=0.0, t=0.0, **kw):
    getattr(cp, name)(c, x, y, s, look, rot, t, **kw)


def holder(name, s, look, t, rot_extra=0.0):
    dx, dy, k, rot = HOLD.get(name, (0, 0, 0.8, 0))

    def h(c, j):
        hx, hy = j['ra'][1]
        draw_prop(c, name, hx + dx * s, hy + dy * s, s * k, look, rot + rot_extra, t)
    return h


def lineup(look):
    sc = SCALE[look]

    def draw(c, t, x):
        backdrop(c, look, t)
        for i, (o, expr, prop) in enumerate(CASTS[look]):
            u = eout(clamp((t - 0.12 * i) / 0.45))
            if u <= 0:
                continue
            s = sc * (0.75 + 0.25 * u)
            bob = 5 * math.sin(t * 2.4 + i * 1.3)
            px = 320 + i * 210
            pose = hu.stand_front()
            pose['ra'] = (24.0, 95.0)
            if i == 1 and 0.9 < t < 2.7:
                w_ = math.sin((t - 0.9) * 11)
                pose['la'] = (-150.0, -168.0 + 22 * w_)
            blink = 1.0 if (t + i * 0.7) % 2.6 < 0.09 else 0.0
            gaze = (0.0, 0.0) if t > 2.8 else ((1.0 if i == 0 else -1.0 if i == 2 else 0.0) * 0.6, 0.0)
            cast.person(c, px, GROUND, s, look, pose=pose, outfit=o, expr=expr if t > 0.6 else 'open', gaze=gaze, blink=blink,
                        lift=max(0.0, bob), hold=holder(prop, s, look, t), alpha=clamp(u * 2))
    return draw


def sheet(look):
    def draw(c, t, x):
        backdrop(c, look, t)
        for k, name in enumerate(cp.KITS[look]):
            cx, cy = 290 + (k % 2) * 500, 470 + (k // 2) * 500
            u = eout(clamp((t - 0.25 * k) / 0.4))
            if u <= 0:
                continue
            oval(c, cx, cy + 190, 170 * u, 30 * u, '#000000', 0.16, blur=10)
            dx, dy, sc, rot = SHEET[name]
            sc *= 1.45
            bob = 8 * math.sin(t * 2.2 + k)
            s = sc * (0.4 + 0.6 * u) * (1 + 0.12 * math.sin(math.pi * clamp((t - 0.25 * k) / 0.4)))
            draw_prop(c, name, cx + dx * s / sc, cy + dy * s / sc + bob - 10, s, look, rot + 4 * math.sin(t * 1.7 + k), t)
    return draw


# ---------------------------------------------------------------- the action shots
def act_whatif(c, t, x):
    backdrop(c, 'whatif', t)
    u = 0.5 - 0.5 * math.cos(2 * math.pi * t / 1.1)
    pose = hu.stand_front()
    pose['ra'] = (10.0, 10.0 + 150 * u)
    pose['la'] = (-10.0, -6.0)
    cast.person(c, 370, GROUND, 1.0, 'whatif', pose=pose, outfit=dict(top='#2BB5A4'), expr='angry' if u > 0.6 else 'open',
                sweat=t > 2.0, hold=lambda c_, j: cp.dumbbell(c_, *j['ra'][1], 0.85, 'whatif', 90 + 150 * u * 0.15, t))
    per = 0.62
    ph = (t % per) / per
    d = abs(math.sin(math.pi * ph))
    pose = hu.stand_front()
    pose['la'] = (-24.0, -40.0 - 20 * (1 - d))
    pose['ra'] = (20.0, 12.0)
    j = cast.person(c, 730, GROUND, 1.0, 'whatif', pose=pose, outfit=dict(top='#D93A3A', bottom='#2E3F6E', hair='spiky'),
                    expr='grin', gaze=(-0.5, 0.6))
    hx, hy = j['la'][1]
    by = hy + 40 + (GROUND - 42 - hy - 40) * d
    oval(c, hx - 10, GROUND + 4, 40 * (0.5 + 0.5 * d), 9, '#000000', 0.25 * d, blur=6)
    cp.basketball(c, hx - 10, by, 1.0, 'whatif', 0, t)


def act_palace(c, t, x):
    backdrop(c, 'palace', t)
    cp.torch(c, 215, 1200, 1.0, 'palace', 0, t)
    cp.torch(c, 865, 1200, 1.0, 'palace', 0, t + 0.4)
    u = ease(clamp((t - 0.4) / 0.9))
    pose = hu.stand_front()
    pose['ra'] = (24 + 120 * u, 95 + 70 * u)
    cast.person(c, 380, GROUND, 0.86, 'palace', pose=pose, outfit=dict(hat='crown', beard='white', top='#7A3FB0', trim='#F2C14E'),
                expr='smug', hold=lambda c_, j: cp.goblet(c_, *j['ra'][1], 0.8, 'palace', -20 * u, t))
    v = ease(clamp((t - 1.3) / 0.7))
    pose = hu.stand_front()
    pose['ra'] = (30 + 128 * v, 60 + 112 * v)
    pose['la'] = (-20.0, -40.0)
    cast.person(c, 710, GROUND, 0.86, 'palace', pose=pose, outfit=dict(hat='headband', top='#59606B', robe=False),
                expr='angry' if v > 0.5 else 'open', gaze=(-0.4, -0.3),
                hold=lambda c_, j: cp.sword(c_, *j['ra'][1], 0.8, 'palace', -60 + 60 * v, t))


def act_castle(c, t, x):
    backdrop(c, 'castle', t)
    op = ease(clamp((t - 2.2) / 0.9))
    cp.door(c, 650, GROUND - 100, 0.9, 'castle', 0, t, open_=op)
    walk_t = min(t, 2.4)
    px = 170 + 140 * walk_t
    pose = hu.walk(walk_t * 2 * math.pi * 1.4) if t < 2.4 else hu.stand()
    cast.person(c, px, GROUND, 0.86, 'castle', pose=pose, view='side', outfit=dict(), expr='smug' if t < 2.4 else 'shock',
                hold=lambda c_, j: cp.key(c_, *j['ra'][1], 0.7, 'castle', -20, t))
    pose = hu.stand_front()
    pose['ra'] = (8.0, 8.0)
    cast.person(c, 860, GROUND + 40, 0.8, 'castle', pose=pose, outfit=dict(top='#2E4F8E', trim='#E2C46A', hat='helmet', hair=None),
                expr='angry', gaze=(-0.8, 0.0), hold=lambda c_, j: cp.axe(c_, *j['ra'][1], 0.75, 'castle', 0, t))


def act_desert(c, t, x):
    backdrop(c, 'desert', t)
    cp.palm(c, 860, GROUND - 150, 0.7, 'desert', 0, t)
    off = 22 * t
    sled_x = 250 + off
    cp.block_sled(c, sled_x, GROUND + 40, 0.75, 'desert', 0, t)
    prev = (sled_x + 230 * 0.75 * 1.1, GROUND + 10)        # the rope runs from the sled to each puller's hand
    for k in range(2):
        px = 610 + k * 150 + off
        pose = hu.walk(t * 2 * math.pi * 1.1 + k * 1.7)
        pose['torso'] = 18.0
        pose['head'] = -10.0
        pose['la'] = (60.0, 30.0)
        pose['ra'] = (50.0, 20.0)
        j = cast.person(c, px, GROUND + 60, 1.05, 'desert', pose=pose, view='side', flip=False,
                        outfit=[dict(top='#2F5E9E'), dict(top='#6B4A2E', skin='#A8703F')][k], expr='angry', gaze=(1.0, 0))
        hand = j['ra'][1]
        line(c, prev[0], prev[1], hand[0], hand[1], '#C9A46A', w=6)
        prev = hand
    pr = clamp((t - 0.8) / 0.6)
    pose = hu.stand()
    pose['ra'] = (60.0, 95.0)
    pose['head'] = 14.0
    cast.person(c, sled_x + 215, GROUND + 150, 1.0, 'desert', pose=pose, view='side', outfit=dict(top='#7A2E52'),
                expr='grin', gaze=(0.6, 0.7), hold=lambda c_, j: cp.jug(c_, *j['ra'][1], 0.7, 'desert', 0, t, pour=pr))


def act_pill(c, t, x):
    backdrop(c, 'pill', t)
    px = 190 + 85 * t
    pose = hu.walk(t * 2 * math.pi * 1.3)
    pose['ra'] = (40.0, 150.0)
    j = cast.person(c, px, GROUND, 0.95, 'pill', pose=pose, view='side', outfit=dict(top='#3F7FD6'), expr='smile',
                    hold=lambda c_, j_: cp.umbrella(c_, *j_['ra'][1], 0.95, 'pill', 0, t))
    hx, hy = j['ra'][1]
    rng = np.random.default_rng(5)
    for k in range(60):
        rx = hx - 200 + rng.random() * 400
        ph = (t * 2.2 + rng.random()) % 1.0
        ry = -100 + ph * (hy - 280 + 100)
        line(c, rx, ry, rx - 8, ry + 34, '#5E7FA8', w=3, a=0.6)
        if ph > 0.9:
            circ(c, rx - 8, hy - 280 + 6, 5, '#5E7FA8', 0.6)
    pose = hu.stand_front()
    pose['la'] = (-30.0, -60.0)
    pose['ra'] = (24.0, 100.0)
    bob = 6 * math.sin(t * 3)
    cast.person(c, 770, GROUND, 0.9, 'pill', pose=pose, outfit=dict(top='#F08A24', hat='cap', hat_col='#D8343A', hair=None),
                expr='closed' if (t % 1.6) < 0.8 else 'smile', lift=max(0.0, bob),
                hold=lambda c_, j_: (cp.ice_cream(c_, *j_['ra'][1], 0.6, 'pill', 0, t),
                                     cp.balloon(c_, *j_['la'][1], 1.0, 'pill', 0, t, col='#7B5CE0')))


ACTIONS = dict(whatif=act_whatif, palace=act_palace, castle=act_castle, desert=act_desert, pill=act_pill)
ACTION_ZOOM = dict(whatif=(1.45, 1.5), palace=(1.42, 1.47), castle=(1.36, 1.4), desert=(1.28, 1.32), pill=(1.4, 1.45))


def reel(look):
    script = [dict(scene=name, text=f'{look}-{name}', dur=d, style='none', pre=0.0) for name, d in SHOTS]
    vig = BACKDROPS[look]['vig']

    def cam(z0, z1):
        return lambda t, x: (z0 + (z1 - z0) * ease(t / max(x.dur, 0.1)), 540, GROUND, 540, 1650)

    scenes = dict(lineup=dict(draw=lineup(look), cam=cam(1.48, 1.53), vig=vig),
                  action=dict(draw=ACTIONS[look], cam=cam(*ACTION_ZOOM[look]), vig=vig),
                  sheet=dict(draw=sheet(look), cam=(1.0, 1.03, 540, 960), vig=vig))

    def sfx(tl, spans, rng):
        out = []
        t0 = spans['lineup']['start']
        for i in range(3):
            out.append((t0 + 0.12 * i + 0.05, pop(1.0 + 0.15 * i), 0.5))
        t1 = spans['action']['start']
        out.append((t1 - 0.12, music.sfx('whoosh'), 0.35))
        if look == 'palace':
            out.append((t1 + 1.7, music.sfx('clink'), 0.4))
        if look == 'castle':
            n = int(1.0 * SR)
            creak = music.bp(rng.standard_normal(n), 300, 900) * env(n, 0.2, 0.5) * 0.6
            out.append((t1 + 2.2, creak, 0.5))
        if look == 'whatif':
            for k in range(7):
                out.append((t1 + 0.62 * k + 0.31, music.sfx('click'), 0.25))
        t2 = spans['sheet']['start']
        out.append((t2 - 0.12, music.sfx('whoosh'), 0.35))
        for k in range(6):
            out.append((t2 + 0.25 * k + 0.05, pop(0.9 + 0.1 * k), 0.45))
        return out

    return dict(NAME=f'look_{look}', CAPTIONS='gold', SCRIPT=script, SCENES=scenes, SCORE=BEDS[look], SFX=sfx,
                THUMB_T=lambda tl: 3.2)
