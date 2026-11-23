"""cards: the POWER BALLS scoreboard, a row of 4 fighter cards (skia).

Each card: colored top bar, name, 7 hearts, ability label + power bar (level / MAX_LEVEL), a gold
crown + white border on the unique leader, a shake when that fighter is hit, a popping heart when one
is lost, and a K.O. stamp that slams in when the fighter is out.

    python cards.py --preview preview.png
    python cards.py --hp 6,2,0,4 --levels 3,5,2,4 --out cards.png
"""
import math
import sys
from pathlib import Path

import skia

import drawkit as dk

# ---------------------------------------------------------------- settings
NAMES = ['RED', 'BLUE', 'GREEN', 'YELLOW']
COLORS = ['#FE394C', '#2F7EFF', '#21C45D', '#FEC32F']
LABELS = ['BLASTER', 'LASER', 'MISSILES', 'LIGHTNING']
MAX_HP = 7
MAX_LEVEL = 10

CARD = dict(x0=66, pitch=240, y=262, w=228, h=132, radius=14, bar_h=14, bar_radius=7)
CARD_BG = '#181526'
BORDER, BORDER_W = '#504A61', 2.5
LEADER_BORDER, LEADER_BORDER_W = '#FFFFFF', 3.5
DEAD_COLOR = '#5A5868'
NAME = dict(weight='ExtraBold', size=25, dx=16, dy=40, color='#FFFFFF', dead='#787684')
HEARTS = dict(dx0=23, pitch=30, dy=79, scale=0.98, full='#FF4557', empty='#45454F', pop_time=0.3, pop_grow=0.6,
              pop_from='#FFFFFF')
LABEL = dict(weight='Bold', size=14.5, dx=16, dy=112, color='#C4BED8', dead='#6E6C7A')
POWER = dict(gap=7, x1=213, y0=106, y1=118, radius=6, bg='#343140', fill='#DAE1EF', dead='#646270', min_frac=0.09)
CROWN = dict(dx=200, dy=-6, w=40)
KO = dict(text='K.O.', weight='Black', size=62, color='#FF3B4E', outline='#140A12', ow=10, shadow=4, rotate=-6,
          dx=114, dy=72, pop=0.9, pop_time=0.25, shade='#0A0812', shade_alpha=90)
SHAKE = dict(time=0.4, freq=70, amp=5)


def configure(**kw):
    g = globals()
    for k, v in kw.items():
        if k not in g:
            raise KeyError(k)
        g[k] = v


def heart(c, x, y, s, col, a=255):
    p = dk.fill(col, a)
    c.drawCircle(x - 5.6 * s, y - 2.8 * s, 6.4 * s, p)
    c.drawCircle(x + 5.6 * s, y - 2.8 * s, 6.4 * s, p)
    path = skia.Path()
    path.moveTo(x - 11.7 * s, y - 0.6 * s)
    path.lineTo(x + 11.7 * s, y - 0.6 * s)
    path.lineTo(x, y + 10.5 * s)
    path.close()
    c.drawPath(path, p)


def auto_leader(hp, alive=None):
    alive = alive if alive is not None else [h > 0 for h in hp]
    live = [i for i in range(len(hp)) if alive[i]]
    if not live:
        return None
    mx = max(hp[i] for i in live)
    top = [i for i in live if hp[i] == mx]
    return top[0] if len(top) == 1 else None


def draw_cards(c, hp, levels, alive=None, leader=None, ko_age=None, shake=None, heart_pop=None):
    """hp/levels: per fighter. alive defaults to hp > 0. leader: index or None (see auto_leader).
    ko_age: seconds since each K.O. (None = long ago). shake: seconds of hit-shake left (0..0.4).
    heart_pop: None or (heart_index, age) per fighter, for the heart that was just lost."""
    n = len(hp)
    alive = alive if alive is not None else [h > 0 for h in hp]
    ko_age = ko_age or [None] * n
    shake = shake or [0.0] * n
    heart_pop = heart_pop or [None] * n
    hps = [hp[i] if alive[i] else 0 for i in range(n)]
    for i in range(n):
        x = CARD['x0'] + CARD['pitch'] * i
        y = CARD['y']
        jit = 0.0
        if shake[i] > 0:
            jit = math.sin(shake[i] * SHAKE['freq']) * SHAKE['amp'] * (shake[i] / SHAKE['time'])
        x += jit
        dead = not alive[i]
        w, h = CARD['w'], CARD['h']
        col = COLORS[i] if not dead else DEAD_COLOR
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, y + 6, x + w, y + h), CARD['radius'], CARD['radius']),
                    dk.fill(CARD_BG))
        border, bw = BORDER, BORDER_W
        if leader == i:
            border, bw = LEADER_BORDER, LEADER_BORDER_W
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, y + 6, x + w, y + h), CARD['radius'], CARD['radius']),
                    dk.stroke(border, bw))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, y, x + w, y + CARD['bar_h']), CARD['bar_radius'],
                                          CARD['bar_radius']), dk.fill(col))
        dk.text(c, NAMES[i], x + NAME['dx'], y + NAME['dy'], NAME['size'], NAME['weight'],
                NAME['color'] if not dead else NAME['dead'], align='left')
        for j in range(MAX_HP):
            full = j < hps[i]
            hc = dk.rgb(HEARTS['full']) if full else dk.rgb(HEARTS['empty'])
            sc = HEARTS['scale']
            if heart_pop[i] is not None and j == heart_pop[i][0]:
                a = heart_pop[i][1]
                sc = HEARTS['scale'] * (1 + HEARTS['pop_grow'] * math.sin(min(1, a / HEARTS['pop_time']) * math.pi))
                hc = dk.mix(HEARTS['pop_from'], hc, dk.clamp01(a / HEARTS['pop_time']))
            heart(c, x + HEARTS['dx0'] + HEARTS['pitch'] * j, y + HEARTS['dy'], sc, hc)
        lw = dk.text(c, LABELS[i], x + LABEL['dx'], y + LABEL['dy'], LABEL['size'], LABEL['weight'],
                     LABEL['color'] if not dead else LABEL['dead'], align='left')
        bx0, bx1 = x + LABEL['dx'] + lw + POWER['gap'], x + POWER['x1']
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx0, y + POWER['y0'], bx1, y + POWER['y1']), POWER['radius'],
                                          POWER['radius']), dk.fill(POWER['bg']))
        frac = max(POWER['min_frac'], levels[i] / MAX_LEVEL)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx0, y + POWER['y0'], bx0 + (bx1 - bx0) * frac,
                                                    y + POWER['y1']), POWER['radius'], POWER['radius']),
                    dk.fill(POWER['fill'] if not dead else POWER['dead']))
        if leader == i:
            dk.crown(c, x + CROWN['dx'], y + CROWN['dy'], CROWN['w'])
        if dead:
            age = ko_age[i] if ko_age[i] is not None else 9
            sc = 1.0 + KO['pop'] * (1 - dk.ease_out(age / KO['pop_time']))
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, y, x + w, y + h), CARD['radius'], CARD['radius']),
                        dk.fill(KO['shade'], KO['shade_alpha']))
            c.save()
            c.translate(x + KO['dx'], y + KO['dy'])
            c.scale(sc, sc)
            c.rotate(KO['rotate'])
            dk.text(c, KO['text'], 0, 0, KO['size'], KO['weight'], KO['color'], outline=KO['outline'], ow=KO['ow'],
                    shadow=KO['shadow'])
            c.restore()


def style():
    return {
        'fighters': [{'name': n, 'color': col, 'label': lab} for n, col, lab in zip(NAMES, COLORS, LABELS)],
        'max_hp': MAX_HP, 'max_level': MAX_LEVEL,
        'card': dict(CARD, background=CARD_BG, border=BORDER, border_width=BORDER_W, leader_border=LEADER_BORDER,
                     leader_border_width=LEADER_BORDER_W, dead_bar=DEAD_COLOR,
                     x_formula='x0 + pitch * index (px, 1080-wide canvas)'),
        'name': dict(NAME, font='Poppins'), 'hearts': HEARTS, 'label': dict(LABEL, font='Poppins'),
        'power_bar': dict(POWER, fraction='max(min_frac, level / max_level)'),
        'leader_crown': CROWN, 'ko_stamp': dict(KO, font='Poppins', pop_easing='easeOutCubic'),
        'hit_shake': dict(SHAKE, formula='sin(left * freq) * amp * left / time'),
    }


def _preview_background(c, w, h):
    """Same purple radial background as layout.py, so the preview matches the video."""
    sh = skia.GradientShader.MakeRadial((540, 880), 1150, [dk.C('#261A3E'), dk.C('#1A112D'), dk.C('#130D22')],
                                       [0.0, 0.55, 1.0])
    c.drawRect(skia.Rect(0, 0, w, h), skia.Paint(Shader=sh))


def preview(path, hp=(6, 2, 0, 4), levels=(3, 5, 2, 4), leader='auto', heart_pop=None, height=460):
    surf = dk.new_surface(1080, height)
    c = surf.getCanvas()
    _preview_background(c, 1080, height)
    c.translate(0, height / 2 - (CARD['y'] + CARD['h'] / 2))
    alive = [h > 0 for h in hp]
    ld = auto_leader(list(hp), alive) if leader == 'auto' else leader
    draw_cards(c, list(hp), list(levels), alive, ld, heart_pop=heart_pop)
    dk.save_png(surf, path)


def _arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


if __name__ == '__main__':
    if '--style' in sys.argv:
        import json
        out = _arg('--style', 'style.json')
        Path(out).write_text(json.dumps(dict(style(), **dk.style()), indent=2, ensure_ascii=False))
        print('wrote', out)
    elif '--preview' in sys.argv or '--out' in sys.argv:
        out = _arg('--preview', None) or _arg('--out', 'cards.png')
        hp = [int(v) for v in _arg('--hp', '6,2,0,4').split(',')]
        lv = [int(v) for v in _arg('--levels', '3,5,2,4').split(',')]
        hpop = None
        if '--preview' in sys.argv:
            hpop = [None, (2, 0.12), None, None]
        preview(out, hp, lv, heart_pop=hpop)
        print('wrote', out)
    else:
        print(__doc__)
