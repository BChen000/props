"""fighters: the four POWER BALLS fighters and their ability visuals (skia).

A fighter is a colored ball (white rim, soft highlight, HP number) plus weapon hardware:
  blaster   - ring of gun barrels (count grows per level), recoil + muzzle flash when it fires
  laser     - turret with a lens that charges, plus a fading laser sight while idle
  missiles  - launcher pod with two missiles that slide out as the next volley reloads
  lightning - electric aura ring with crackling sparks
Ability visuals: bullets, laser aim line / beam, homing missiles, lightning bolts (with a branch),
the lightning range ring, and the soft motion trail behind each ball.

All functions draw at the given position in the canvas' current coordinates (arena px in the video).

    python fighters.py --preview preview.png
"""
import math
import random
import sys
from pathlib import Path

import skia

import drawkit as dk

# ---------------------------------------------------------------- settings
COLORS = ['#FE394C', '#2F7EFF', '#21C45D', '#FEC32F']
ABILITIES = ['blaster', 'laser', 'missiles', 'lightning']
BALL_R = 46.0

BALL = dict(rim='#FFFFFF', rim_w=4, highlight='#FFFFFF', highlight_alpha=60, hp_weight='Black', hp_size=50,
            hp_color='#FFFFFF', hp_outline='#100C16', hp_ow=8, flash_to='#FFFFFF', shield='#FFFFFF', shield_w=3,
            shield_gap=8, shield_alpha=150)
BLASTER = dict(outline='#0C0A12', body='#302E3E', tip='#FF5F6E', stripe='#5A586E', flash='#FFBE6E',
               flash_core='#FFFFFF', recoil=6.0, recoil_time=0.16, flash_time=0.08, static_n=6, static_rot=-0.3)
LASER = dict(outline='#0A0E1C', body='#202E50', stripe='#508CFF', sight='#78B4FF', sight_alpha=110,
             glow='#5096FF', glow_core='#96C8FF', lens_rim='#0A0E1C', lens='#AAD7FF', lens_core='#FFFFFF',
             static_aim=-0.6)
MISSILE_POD = dict(outline='#08160E', body='#224830', stripe='#21C45D', missile_outline='#0A1E12',
                   missile_body='#ECF6EE', nose_outline='#0A2814', nose='#21C45D', reload=1.2, static_aim=-0.4)
COIL = dict(aura='#FFD750', aura_alpha=70, spark_glow='#FFD23C', spark_glow_alpha=110, spark_core='#FFFFE1')
RANGE_RING = dict(fill='#FEC32F', fill_alpha=12, fill_alpha_ready=22, line='#FED250', line_w=3.5, line_alpha=130,
                  line_alpha_ready=210, dash=[16, 11], dash_speed=40)
LASER_AIM = dict(color='#8CBEFF', width=2.5, alpha0=70, alpha_gain=120, dash=[18, 12], dash_speed=200,
                 locked='#FF788C', locked_w=3.5, locked_alpha=160, locked_blink=90, blink_hz=90)
LASER_BEAM = dict(layers=[(34, '#286EFF', 45), (16, '#468CFF', 110), (0, '#82B9FF', 235), (-1, '#FFFFFF', 255)],
                  core_frac=0.42, attack=0.04, wobble=0.08, wobble_hz=160, end_glow='#C8E1FF', end_alpha=160,
                  end_pad=18)
BULLET = dict(trail='#FF465A', trail_w=10, trail_alpha=90, trail_len=0.05, glow='#FF394C', glow_r=16, glow_alpha=75,
              body='#FF7886', body_r=9, core='#FFFFFF', core_r=4.8)
MISSILE = dict(scale=1.4, flame='#FFA03C', flame_alpha=230, flame_core='#FFF0B4', fins='#14783C', body='#ECF6EE',
               body_outline='#14281C', nose='#21C45D', nose_outline='#0A3219')
BOLT = dict(segs=12, amp=26, layers=[(16, '#FFC828', 0.35), (7, '#FFE878', 0.85), (2.8, '#FFFFFF', 1.0)],
            branch_len=70, branch_layers=[(4, '#FFE878', 0.6), (1.6, '#FFFFFF', 0.8)])
TRAIL = dict(every=6, alpha=34)

R = BALL_R


def configure(**kw):
    g = globals()
    for k, v in kw.items():
        if k not in g:
            raise KeyError(k)
        g[k] = v


# ---------------------------------------------------------------- fighter
def draw_ball(c, i, x, y, hp, scale=1.0, flash=0.0, shield=0.0, alpha=255):
    """Ball i at (x, y) with its HP. flash 0..1 whitens it (hit), shield 0..1 shows the i-frame ring."""
    r = BALL_R * scale
    col = dk.rgb(COLORS[i])
    body = dk.mix(col, BALL['flash_to'], flash)
    if shield > 0:
        c.drawCircle(x, y, r + BALL['shield_gap'] * scale,
                     dk.stroke(BALL['shield'], BALL['shield_w'] * scale, BALL['shield_alpha'] * shield))
    c.drawCircle(x, y, r, dk.fill(body, alpha))
    c.drawCircle(x, y, r - 2 * scale, dk.stroke(BALL['rim'], BALL['rim_w'] * scale, alpha))
    c.drawCircle(x - r * 0.42, y - r * 0.42, r * 0.22, dk.fill(BALL['highlight'], BALL['highlight_alpha'] * alpha / 255))
    dk.text(c, str(hp), x, y, BALL['hp_size'] * scale, BALL['hp_weight'], BALL['hp_color'], alpha,
            outline=BALL['hp_outline'], ow=BALL['hp_ow'] * scale)


def draw_weapon(c, ability, x, y, scale=1.0, *, n=None, rot=None, since_fire=9.0, aim=None, sight=False,
                charge=0.0, ready=1.0, rng=None):
    """Weapon hardware for `ability` on a ball at (x, y). Draw it before draw_ball so it sits underneath.

    blaster: n barrels, rot (rad), since_fire (s since the last volley).  laser: aim (rad), sight (bool),
    charge 0..1.  missiles: aim (rad), ready 0..1 (reload progress).  lightning: rng (sparks).
    """
    R_ = BALL_R
    c.save()
    c.translate(x, y)
    c.scale(scale, scale)
    if ability == 'blaster':
        b = BLASTER
        n = b['static_n'] if n is None else n
        rot = b['static_rot'] if rot is None else rot
        since = since_fire
        rec = b['recoil'] * (1 - since / b['recoil_time']) if 0 <= since < b['recoil_time'] else 0.0
        for k in range(n):
            a = rot + 2 * math.pi * k / n
            c.save()
            c.rotate(math.degrees(a))
            r0, r1 = R_ - 6 - rec, R_ + 23 - rec
            rr = skia.RRect.MakeRectXY(skia.Rect(r0, -7.5, r1, 7.5), 3.5, 3.5)
            c.drawRRect(rr, dk.stroke(b['outline'], 5))
            c.drawRRect(rr, dk.fill(b['body']))
            c.drawRect(skia.Rect(r1 - 8, -7.5, r1, 7.5), dk.fill(b['tip']))
            c.drawRect(skia.Rect(r0 + 4, -2, r1 - 10, 2), dk.fill(b['stripe']))
            if 0 <= since < b['flash_time']:
                u = since / b['flash_time']
                c.drawCircle(r1 + 7, 0, 12 * (1 - u), dk.fill(b['flash'], 200))
                c.drawCircle(r1 + 5, 0, 6 * (1 - u), dk.fill(b['flash_core']))
            c.restore()
    elif ability == 'laser':
        L = LASER
        a = L['static_aim'] if aim is None else aim
        c.save()
        c.rotate(math.degrees(a))
        if sight:
            sh = skia.GradientShader.MakeLinear([(R_ + 36, 0), (R_ + 300, 0)],
                                                [dk.C(L['sight'], L['sight_alpha']), dk.C(L['sight'], 0)])
            sp = skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=2.5)
            c.drawLine(R_ + 36, 0, R_ + 300, 0, sp)
        rr = skia.RRect.MakeRectXY(skia.Rect(R_ - 10, -14, R_ + 33, 14), 6, 6)
        c.drawRRect(rr, dk.stroke(L['outline'], 5))
        c.drawRRect(rr, dk.fill(L['body']))
        c.drawRect(skia.Rect(R_ + 4, -14, R_ + 10, 14), dk.fill(L['stripe']))
        c.drawRect(skia.Rect(R_ + 15, -14, R_ + 19, 14), dk.fill(L['stripe']))
        glow_r = 10 + 16 * charge
        if charge > 0:
            c.drawCircle(R_ + 36, 0, glow_r * 1.8, dk.fill(L['glow'], 70 * charge))
            c.drawCircle(R_ + 36, 0, glow_r, dk.fill(L['glow_core'], 170 * charge))
        c.drawCircle(R_ + 35, 0, 10, dk.fill(L['lens_rim']))
        c.drawCircle(R_ + 35, 0, 8, dk.fill(L['lens']))
        c.drawCircle(R_ + 35, 0, 4, dk.fill(L['lens_core']))
        c.restore()
    elif ability == 'missiles':
        M = MISSILE_POD
        a = M['static_aim'] if aim is None else aim
        c.save()
        c.rotate(math.degrees(a))
        for oy in (-9.5, 9.5):
            tip = R_ + 22 + 12 * ready
            body = skia.RRect.MakeRectXY(skia.Rect(R_ + 4, oy - 5.5, tip, oy + 5.5), 3, 3)
            c.drawRRect(body, dk.stroke(M['missile_outline'], 3.5))
            c.drawRRect(body, dk.fill(M['missile_body']))
            path = skia.Path()
            path.moveTo(tip - 1, oy - 5.5)
            path.lineTo(tip + 10, oy)
            path.lineTo(tip - 1, oy + 5.5)
            path.close()
            c.drawPath(path, dk.stroke(M['nose_outline'], 2.5))
            c.drawPath(path, dk.fill(M['nose']))
        rr = skia.RRect.MakeRectXY(skia.Rect(R_ - 12, -18, R_ + 24, 18), 6, 6)
        c.drawRRect(rr, dk.stroke(M['outline'], 5))
        c.drawRRect(rr, dk.fill(M['body']))
        c.drawRect(skia.Rect(R_ + 2, -18, R_ + 7, 18), dk.fill(M['stripe']))
        c.restore()
    elif ability == 'lightning':
        K = COIL
        rng = rng or random.Random(1)
        c.drawCircle(0, 0, R_ + 7, dk.stroke(K['aura'], 6, K['aura_alpha']))
        for _ in range(3):
            a0 = rng.uniform(0, 2 * math.pi)
            pts = []
            for k in range(6):
                aa = a0 + k * 0.16
                rad = R_ + 4 + rng.uniform(0, 18)
                pts.append((math.cos(aa) * rad, math.sin(aa) * rad))
            path = skia.Path()
            path.moveTo(*pts[0])
            for p in pts[1:]:
                path.lineTo(*p)
            c.drawPath(path, dk.stroke(K['spark_glow'], 8, K['spark_glow_alpha']))
            c.drawPath(path, dk.stroke(K['spark_core'], 2.6, 255))
    c.restore()


def missile_ready(cooldown_left):
    """Reload progress shown on the pod (missiles slide out over the last MISSILE_POD['reload'] s)."""
    return dk.clamp01(1 - cooldown_left / MISSILE_POD['reload'])


# ---------------------------------------------------------------- ability visuals
def draw_range_ring(c, x, y, r, t, ready=False):
    g = RANGE_RING
    c.drawCircle(x, y, r, dk.fill(g['fill'], g['fill_alpha'] if not ready else g['fill_alpha_ready']))
    pe = skia.DashPathEffect.Make(g['dash'], (t * g['dash_speed']) % sum(g['dash']))
    p = dk.stroke(g['line'], g['line_w'], g['line_alpha'] if not ready else g['line_alpha_ready'],
                  cap=skia.Paint.kButt_Cap)
    p.setPathEffect(pe)
    c.drawCircle(x, y, r, p)


def draw_laser_aim(c, x0, y0, x1, y1, t, progress, locked):
    """Charging aim line from the turret tip to the wall. progress 0..1; locked = red blinking warning."""
    g = LASER_AIM
    if locked:
        blink = 0.5 + 0.5 * math.sin(t * g['blink_hz'])
        c.drawLine(x0, y0, x1, y1, dk.stroke(g['locked'], g['locked_w'], g['locked_alpha'] + g['locked_blink'] * blink))
    else:
        pa = dk.stroke(g['color'], g['width'], g['alpha0'] + g['alpha_gain'] * progress)
        pa.setPathEffect(skia.DashPathEffect.Make(g['dash'], (-t * g['dash_speed']) % sum(g['dash'])))
        c.drawLine(x0, y0, x1, y1, pa)


def draw_laser_beam(c, x0, y0, x1, y1, width, age, duration, t):
    """Wall-to-wall beam `age` s into a `duration` s shot."""
    g = LASER_BEAM
    w = width
    u = age / duration
    env = min(1.0, age / g['attack']) * (1 - 0.6 * max(0.0, (u - 0.6) / 0.4))
    wob = 1 + g['wobble'] * math.sin(t * g['wobble_hz'])
    for extra, col, al in g['layers']:
        ww = w * g['core_frac'] if extra < 0 else w + extra
        c.drawLine(x0, y0, x1, y1, dk.stroke(col, ww * wob * env, al, cap=skia.Paint.kRound_Cap))
    c.drawCircle(x1, y1, (w + g['end_pad']) * env, dk.fill(g['end_glow'], g['end_alpha']))


def draw_bullet(c, x, y, vx, vy):
    g = BULLET
    tx, ty = x - vx * g['trail_len'], y - vy * g['trail_len']
    c.drawLine(tx, ty, x, y, dk.stroke(g['trail'], g['trail_w'], g['trail_alpha']))
    c.drawCircle(x, y, g['glow_r'], dk.fill(g['glow'], g['glow_alpha']))
    c.drawCircle(x, y, g['body_r'], dk.fill(g['body']))
    c.drawCircle(x, y, g['core_r'], dk.fill(g['core']))


def draw_missile(c, x, y, ang, rng):
    """Homing missile pointing along ang; rng flickers the flame."""
    g = MISSILE
    c.save()
    c.translate(x, y)
    c.rotate(math.degrees(ang))
    c.scale(g['scale'], g['scale'])
    fl = 10 + 8 * rng.random()
    path = skia.Path()
    path.moveTo(-14, -5)
    path.lineTo(-14 - fl, 0)
    path.lineTo(-14, 5)
    path.close()
    c.drawPath(path, dk.fill(g['flame'], g['flame_alpha']))
    c.drawCircle(-15, 0, 4, dk.fill(g['flame_core']))
    fp = skia.Path()
    fp.moveTo(-12, -4)
    fp.lineTo(-17, -10)
    fp.lineTo(-6, -4)
    fp.close()
    fp.moveTo(-12, 4)
    fp.lineTo(-17, 10)
    fp.lineTo(-6, 4)
    fp.close()
    c.drawPath(fp, dk.fill(g['fins']))
    rr = skia.RRect.MakeRectXY(skia.Rect(-14, -5, 10, 5), 3, 3)
    c.drawRRect(rr, dk.fill(g['body']))
    c.drawRRect(rr, dk.stroke(g['body_outline'], 1.6))
    nose = skia.Path()
    nose.moveTo(8, -5)
    nose.lineTo(18, 0)
    nose.lineTo(8, 5)
    nose.close()
    c.drawPath(nose, dk.fill(g['nose']))
    c.drawPath(nose, dk.stroke(g['nose_outline'], 1.4))
    c.restore()


def lightning_path(p0, p1, rng, segs=11, amp=20):
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    pts = [(x0, y0)]
    for k in range(1, segs):
        u = k / segs
        off = rng.uniform(-amp, amp) * math.sin(math.pi * u) ** 0.6
        pts.append((x0 + dx * u + nx * off, y0 + dy * u + ny * off))
    pts.append((x1, y1))
    return pts


def poly(c, pts, paint):
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    c.drawPath(path, paint)


def draw_bolt(c, p0, p1, alpha, rng):
    """One jagged lightning bolt p0 -> p1 with a side branch. Reseed rng every 2 frames for flicker."""
    g = BOLT
    pts = lightning_path(p0, p1, rng, segs=g['segs'], amp=g['amp'])
    for w, col, k in g['layers']:
        poly(c, pts, dk.stroke(col, w, alpha * k))
    if len(pts) > 6:
        bi = rng.randrange(3, len(pts) - 3)
        bx, by = pts[bi]
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + rng.choice([-1, 1]) * rng.uniform(0.5, 1.0)
        L = g['branch_len']
        bp = lightning_path((bx, by), (bx + math.cos(ang) * L, by + math.sin(ang) * L), rng, 5, 12)
        for w, col, k in g['branch_layers']:
            poly(c, bp, dk.stroke(col, w, alpha * k))


def draw_trail(c, i, hist):
    """Soft trail from recent positions (oldest first), sampled at the physics rate."""
    n = len(hist)
    for j in range(0, n - 4, TRAIL['every']):
        u = 1 - j / max(1, n)
        hx, hy = hist[j]
        c.drawCircle(hx, hy, BALL_R * (0.55 + 0.4 * u), dk.fill(COLORS[i], TRAIL['alpha'] * u))


def style():
    return {
        'fighters': [{'color': col, 'ability': ab} for col, ab in zip(COLORS, ABILITIES)],
        'ball_radius': BALL_R, 'ball': dict(BALL, font='Poppins', highlight='circle r*0.22 at (-0.42r, -0.42r)'),
        'blaster_barrels': dict(BLASTER, barrel='rounded rect r-6..r+23 x 15 px, tip 8 px, recoil over recoil_time s'),
        'laser_turret': dict(LASER, turret='rounded rect r-10..r+33 x 28 px, lens at r+35, sight r+36..r+300'),
        'missile_pod': dict(MISSILE_POD, pod='rounded rect r-12..r+24 x 36 px, missiles slide out 12 px'),
        'lightning_coil': dict(COIL, aura='ring r+7 width 6', sparks='3 zigzags, 6 points, radius r+4..r+22'),
        'range_ring': RANGE_RING, 'laser_aim': LASER_AIM,
        'laser_beam': dict(LASER_BEAM, layers=[{'extra_width': e, 'color': col, 'alpha': a}
                                               for e, col, a in LASER_BEAM['layers']],
                           note='extra_width -1 = core (width * core_frac); envelope attack then fades 60% after u=0.6'),
        'bullet': BULLET, 'missile': MISSILE,
        'lightning_bolt': dict(BOLT, life_s=0.3, alpha='255 * (1 - age/life) ** 0.7', rejag='every 2 frames'),
        'trail': dict(TRAIL, history='last 40 physics steps (1/240 s)', radius='r * (0.55 + 0.4 u)'),
    }


# ---------------------------------------------------------------- preview
def preview(path):
    """Each fighter mid-attack on the arena grid (872 x 872, same look as the video)."""
    S = 872
    surf = dk.new_surface(S, S)
    c = surf.getCanvas()
    c.clear(dk.C('#0D0D17'))
    gp = dk.stroke('#AFAFBE', 1.6, 120, cap=skia.Paint.kButt_Cap)
    for k in range(11):
        v = 76 + 80 * k
        if v < S:
            c.drawLine(v, 0, v, S, gp)
            c.drawLine(0, v, S, v, gp)
    t = 3.1
    rng = random.Random(7)
    red, blue, green, yellow = (215, 230), (650, 175), (220, 650), (640, 640)
    # yellow: range ring + bolt to green
    draw_range_ring(c, *yellow, 250, t, ready=True)
    # green missiles with smoke, flying up-right
    for k, (mx, my, ma) in enumerate([(360, 560, -0.9), (420, 640, -0.55), (330, 470, -1.2)]):
        for j in range(9):
            sx, sy = mx - math.cos(ma) * (20 + 13 * j), my - math.sin(ma) * (20 + 13 * j)
            u = j / 9
            c.drawCircle(sx, sy, 5 * (1 + 1.6 * u), dk.fill('#B9BEC4', 120 * (1 - u)))
        draw_missile(c, mx, my, ma, rng)
    # blue: beam firing down-left past the red ball
    aim = math.atan2(red[1] + 120 - blue[1], red[0] - 40 - blue[0])
    tipx, tipy = blue[0] + math.cos(aim) * (BALL_R + 36), blue[1] + math.sin(aim) * (BALL_R + 36)
    ex, ey = blue[0] + math.cos(aim) * 900, blue[1] + math.sin(aim) * 900
    draw_laser_beam(c, blue[0], blue[1], ex, ey, 28, 0.12, 0.3, t)
    # red: a ring of 9 bullets leaving the barrels
    n = 9
    for k in range(n):
        a = 0.35 + 2 * math.pi * k / n
        d = BALL_R + 70
        draw_bullet(c, red[0] + math.cos(a) * d, red[1] + math.sin(a) * d, math.cos(a) * 480, math.sin(a) * 480)
    hist = [(yellow[0] - 2.2 * (40 - j), yellow[1] + 1.1 * (40 - j)) for j in range(40)]
    draw_trail(c, 3, hist)
    draw_weapon(c, 'blaster', *red, n=n, rot=0.35, since_fire=0.03)
    draw_weapon(c, 'laser', *blue, aim=aim, charge=1.0)
    draw_weapon(c, 'missiles', *green, aim=-0.9, ready=0.3)
    draw_weapon(c, 'lightning', *yellow, rng=random.Random(11))
    draw_ball(c, 0, *red, 5)
    draw_ball(c, 1, *blue, 6)
    draw_ball(c, 2, *green, 3, flash=0.75, shield=0.9)
    draw_ball(c, 3, *yellow, 7)
    draw_bolt(c, yellow, green, 230, random.Random(5))
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
