"""fx: impact effects engine for POWER BALLS (skia).

Particles (rotating squares, sparks, glows, smoke puffs), expanding rings, floating "-1" damage numbers
and upgrade labels, screen shake and a white flash. Presets reproduce the video's effects:
hit(), ko(), explosion(), plus burst()/ring()/glow()/puff()/float_text() for new ones.

Advance with update(dt, speed) at the physics rate (1/240 s in the video); pass speed < 1 in slow motion so
shake and flash still decay in real (video) time. Draw in this order around your own content:
draw_smoke, draw_rings (under fighters), then draw_particles, draw_texts (over fighters).

    python fx.py --preview preview.png
"""
import math
import random
import sys
from pathlib import Path

import skia

import drawkit as dk

# ---------------------------------------------------------------- settings
BALL_R = 46.0
DAMAGE_TEXT = dict(text='-1', color='#FF4557', size=40, life=0.95, jitter=14, above=8)
LABEL_TEXT = dict(size=24, life=1.0, above=34)
TEXT_STYLE = dict(weight='Black', outline='#140A12', ow=7, rise=70, pop=0.5, pop_time=0.12, fade_from=0.55,
                  fade_len=0.45)
HIT = dict(n=14, speed=(140, 460), life=0.55, size=9, spread=1.4)
KO = dict(white_ring=(170, 0.5, 12), color_ring=(0.5, 110, 0.42, 9), n=44, speed=(220, 820), life=0.9, size=12,
          glow=(120, 0.3), shake=14.0, flash=0.25, flash_final=0.55)
EXPLOSION = dict(ring=('#FFB450', 6, 64, 44, 0.32, 7), glow=('#FFE696', 40, 26, 0.22),
                 palette=['#FFAA3C', '#FFDC6E', '#FF6E32'], n=(12, 7), speed=(90, 380), life=0.45, size=7,
                 smoke=('#96969E', 5, 90, 0.7, 10, 3), shake=4.0)
SPARK_COLORS = dict(bullet_wall=['#FF7882', '#FFC88C'], absorb='#FFFFFF', bump='#FFFFFF',
                    laser_wall=['#B4D7FF', '#FFFFFF'])
SMOKE_COLORS = dict(launch='#C8CDD2', trail='#B9BEC4', fizzle='#8C8C96')
RING_COLORS = dict(blaster='#FF7882')
LIGHTNING_GLOW = ('#FFF5BE', 48, 0.2)
SHAKE_DECAY = 40.0   # px per second of video time
FLASH_DECAY = 2.4    # per second of video time


def configure(**kw):
    g = globals()
    for k, v in kw.items():
        if k not in g:
            raise KeyError(k)
        g[k] = v


def _c(col):
    return [dk.rgb(x) for x in col] if isinstance(col, list) else dk.rgb(col)


class FX:
    """parts: [x, y, vx, vy, age, life, size, rgb, kind, rot, vrot, drag]
    texts: [text, x, y, age, life, rgb, size, kind]   rings: [x, y, r0, r1, age, life, rgb, width]"""

    def __init__(self, seed=0, rng=None):
        self.rng = rng or random.Random(seed)
        self.parts = []
        self.texts = []
        self.rings = []
        self.bolts = []
        self.shake = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------ primitives
    def burst(self, x, y, n, rgb, smin, smax, life, size, kind='sq', drag=2.5, spread=None, ang=None):
        rng = self.rng
        for _ in range(n):
            if ang is not None:
                a = ang + rng.uniform(-spread, spread)
            else:
                a = rng.uniform(0, 2 * math.pi)
            sp = rng.uniform(smin, smax)
            col = rgb if not isinstance(rgb, list) else rng.choice(rgb)
            self.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 0.0, life * rng.uniform(0.7, 1.2),
                               size * rng.uniform(0.7, 1.3), col, kind, rng.uniform(0, 6.28),
                               rng.uniform(-12, 12), drag])

    def ring(self, x, y, r0, r1, life, rgb, width):
        self.rings.append([x, y, r0, r1, 0.0, life, rgb, width])

    def glow(self, x, y, size, life, rgb):
        self.parts.append([x, y, 0, 0, 0.0, life, size, rgb, 'glow', 0, 0, 0])

    def puff(self, x, y, n, spread, life, size, rgb, drag):
        rng = self.rng
        for _ in range(n):
            self.parts.append([x, y, rng.uniform(-spread, spread), rng.uniform(-spread, spread), 0.0, life, size,
                               rgb, 'smoke', 0, 0, drag])

    def float_text(self, text, x, y, rgb, size, life, kind='label'):
        self.texts.append([text, x, y, 0.0, life, rgb, size, kind])

    def add_bolt(self, **info):
        seed = self.rng.randrange(1 << 30)
        self.bolts.append(dict(info, age=0.0, life=0.3, seed=seed))

    # ------------------------------------------------------------ presets from the video
    def hit(self, x, y, sx, sy, color):
        """Victim at (x, y) hit from (sx, sy): squares spray away from the hit + a '-1' pops above."""
        h, d = HIT, DAMAGE_TEXT
        col = dk.rgb(color)
        ang = math.atan2(y - sy, x - sx)
        self.burst(x, y, h['n'], [col, col, (255, 255, 255)], h['speed'][0], h['speed'][1], h['life'], h['size'],
                   ang=ang, spread=h['spread'])
        self.float_text(d['text'], x + self.rng.uniform(-d['jitter'], d['jitter']), y - BALL_R - d['above'],
                        dk.rgb(d['color']), d['size'], d['life'], kind='dmg')

    def label(self, text, x, y, color):
        self.float_text(text, x, y - BALL_R - LABEL_TEXT['above'], dk.rgb(color), LABEL_TEXT['size'], LABEL_TEXT['life'])

    def ko(self, x, y, color, final=False):
        k = KO
        col = dk.rgb(color)
        self.ring(x, y, BALL_R, BALL_R + k['white_ring'][0], k['white_ring'][1], (255, 255, 255), k['white_ring'][2])
        self.ring(x, y, BALL_R * k['color_ring'][0], BALL_R + k['color_ring'][1], k['color_ring'][2], col,
                  k['color_ring'][3])
        self.burst(x, y, k['n'], [col, col, (255, 255, 255)], k['speed'][0], k['speed'][1], k['life'], k['size'])
        self.glow(x, y, k['glow'][0], k['glow'][1], (255, 255, 255))
        self.shake = max(self.shake, k['shake'])
        self.flash = max(self.flash, k['flash_final'] if final else k['flash'])

    def explosion(self, x, y, hit=True):
        e = EXPLOSION
        rc, r0, r_hit, r_miss, rlife, rw = e['ring']
        gc, g_hit, g_miss, glife = e['glow']
        self.ring(x, y, r0, r_hit if hit else r_miss, rlife, dk.rgb(rc), rw)
        self.glow(x, y, g_hit if hit else g_miss, glife, dk.rgb(gc))
        self.burst(x, y, e['n'][0] if hit else e['n'][1], _c(e['palette']), e['speed'][0], e['speed'][1], e['life'],
                   e['size'])
        sc, n, spread, slife, ssize, sdrag = e['smoke']
        self.puff(x, y, n, spread, slife, ssize, dk.rgb(sc), sdrag)
        if hit:
            self.shake = max(self.shake, e['shake'])

    # ------------------------------------------------------------ update
    def update(self, dt, speed=1.0):
        alive_parts = []
        for p in self.parts:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            d = math.exp(-p[11] * dt)
            p[2] *= d
            p[3] *= d
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[9] += p[10] * dt
            alive_parts.append(p)
        self.parts = alive_parts
        for tx in self.texts:
            tx[3] += dt
        self.texts = [tx for tx in self.texts if tx[3] < tx[4]]
        for rg in self.rings:
            rg[4] += dt
        self.rings = [rg for rg in self.rings if rg[4] < rg[5]]
        for bo in self.bolts:
            bo['age'] += dt
        self.bolts = [bo for bo in self.bolts if bo['age'] < bo['life']]
        self.shake = max(0.0, self.shake - SHAKE_DECAY * dt / speed)
        self.flash = max(0.0, self.flash - FLASH_DECAY * dt / speed)

    # ------------------------------------------------------------ draw
    def draw_smoke(self, c):
        for p in self.parts:
            if p[8] == 'smoke':
                u = p[4] / p[5]
                c.drawCircle(p[0], p[1], p[6] * (1 + 1.6 * u), dk.fill(p[7], 120 * (1 - u)))

    def draw_rings(self, c):
        for rg in self.rings:
            u = rg[4] / rg[5]
            rad = rg[2] + (rg[3] - rg[2]) * dk.ease_out(u)
            c.drawCircle(rg[0], rg[1], rad, dk.stroke(rg[6], max(0.5, rg[7] * (1 - u)), 255 * (1 - u)))

    def draw_particles(self, c):
        for p in self.parts:
            kind = p[8]
            if kind == 'smoke':
                continue
            u = p[4] / p[5]
            al = 255 * (1 - u)
            if kind == 'sq':
                sz = p[6] * (1 - 0.5 * u)
                c.save()
                c.translate(p[0], p[1])
                c.rotate(math.degrees(p[9]))
                c.drawRect(skia.Rect(-sz / 2, -sz / 2, sz / 2, sz / 2), dk.fill(p[7], al))
                c.restore()
            elif kind == 'spark':
                c.drawLine(p[0], p[1], p[0] - p[2] * 0.03, p[1] - p[3] * 0.03, dk.stroke(p[7], p[6], al))
            elif kind == 'glow':
                c.drawCircle(p[0], p[1], p[6] * (0.6 + 0.6 * u), dk.fill(p[7], 200 * (1 - u)))

    def draw_texts(self, c, hide_labels=False):
        s = TEXT_STYLE
        for tx in self.texts:
            if hide_labels and tx[7] != 'dmg':
                continue
            age, life = tx[3], tx[4]
            u = age / life
            al = 255 * (1 - dk.clamp01((u - s['fade_from']) / s['fade_len']))
            sc = 1.0 + s['pop'] * (1 - dk.ease_out(age / s['pop_time']))
            c.save()
            c.translate(tx[1], tx[2] - s['rise'] * dk.ease_out(u))
            c.scale(sc, sc)
            dk.text(c, tx[0], 0, 0, tx[6], s['weight'], tx[5], al, outline=s['outline'], ow=s['ow'])
            c.restore()


def style():
    return {
        'ball_radius': BALL_R,
        'damage_text': dict(DAMAGE_TEXT, font='Poppins'), 'label_text': dict(LABEL_TEXT, font='Poppins'),
        'text_motion': dict(TEXT_STYLE, font='Poppins', rise_easing='easeOutCubic'),
        'hit_burst': dict(HIT, colors='victim, victim, white', note='squares spray within +-spread rad of knockback'),
        'ko': dict(KO, colors='victim, victim, white'),
        'missile_explosion': EXPLOSION,
        'spark_colors': SPARK_COLORS, 'smoke_colors': SMOKE_COLORS, 'ring_colors': RING_COLORS,
        'lightning_glow': {'color': LIGHTNING_GLOW[0], 'size': LIGHTNING_GLOW[1], 'life': LIGHTNING_GLOW[2]},
        'particles': {'sq': 'rotating square, size*(1-0.5u), alpha 255(1-u)',
                      'spark': 'line of length v*0.03 s, alpha 255(1-u)', 'glow': 'circle size*(0.6+0.6u), alpha 200(1-u)',
                      'smoke': 'circle size*(1+1.6u), alpha 120(1-u)', 'drag': 'velocity *= exp(-drag*dt)'},
        'rings': 'radius r0->r1 easeOutCubic, width w*(1-u), alpha 255(1-u)',
        'shake_decay_px_per_s': SHAKE_DECAY, 'flash_decay_per_s': FLASH_DECAY,
        'timestep': '1/240 s',
    }


def preview(path):
    """Film strip: each preset (rows) at 0.04 / 0.12 / 0.24 / 0.40 s (columns), drawn at half scale."""
    cell, left, top = 220, 178, 44
    times = [0.04, 0.12, 0.24, 0.40]
    rows = [('hit + -1', lambda f: f.hit(0, 0, -120, 70, '#FE394C')),
            ('knockout', lambda f: f.ko(0, 0, '#2F7EFF')),
            ('missile boom', lambda f: f.explosion(0, 0, hit=True)),
            ('ring + sparks', lambda f: (f.ring(0, 0, BALL_R, BALL_R + 46, 0.2, dk.rgb(RING_COLORS['blaster']), 6),
                                         f.burst(0, 0, 10, [dk.rgb(x) for x in SPARK_COLORS['bullet_wall']], 80, 260,
                                                 0.25, 3, kind='spark', drag=4),
                                         f.label('+1 BULLET', 0, 40, '#FE394C')))]
    surf = dk.new_surface(left + cell * len(times) + 10, top + cell * len(rows) + 10)
    c = surf.getCanvas()
    c.clear(dk.C('#130D22'))
    for j, t in enumerate(times):
        dk.text(c, f'{t:.2f} s', left + cell * j + cell / 2, top / 2, 22, 'Bold', '#EAE4FF')
    dt = 1 / 240
    for i, (name, make) in enumerate(rows):
        dk.text(c, name, 12, top + cell * i + cell / 2, 22, 'Bold', '#EAE4FF', align='left')
        for j, t in enumerate(times):
            x0, y0 = left + cell * j, top + cell * i
            c.save()
            c.clipRect(skia.Rect(x0 + 3, y0 + 3, x0 + cell - 3, y0 + cell - 3))
            c.drawRect(skia.Rect(x0, y0, x0 + cell, y0 + cell), dk.fill('#0D0D17'))
            gp = dk.stroke('#AFAFBE', 1.6 * 0.5, 120, cap=skia.Paint.kButt_Cap)
            for k in range(1, 6):
                c.drawLine(x0 + 40 * k - 10, y0, x0 + 40 * k - 10, y0 + cell, gp)
                c.drawLine(x0, y0 + 40 * k - 10, x0 + cell, y0 + 40 * k - 10, gp)
            c.translate(x0 + cell / 2, y0 + cell / 2)
            c.scale(0.5, 0.5)
            f = FX(seed=3)
            make(f)
            for _ in range(int(round(t / dt))):
                f.update(dt)
            f.draw_smoke(c)
            f.draw_rings(c)
            f.draw_particles(c)
            f.draw_texts(c)
            c.restore()
    dk.save_png(surf, path)


if __name__ == '__main__':
    if '--preview' in sys.argv:
        out = sys.argv[sys.argv.index('--preview') + 1]
        preview(out)
        print('wrote', out)
    elif '--style' in sys.argv:
        import json
        out = sys.argv[sys.argv.index('--style') + 1]
        Path(out).write_text(json.dumps(dict(style(), **dk.style()), indent=2, ensure_ascii=False))
        print('wrote', out)
    else:
        print(__doc__)
