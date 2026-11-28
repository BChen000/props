"""humanoid: the white bean person of the motivational Shorts, drawn with skia-python in the lit look.

A soft-lit white figure: a big round, bald head, dot eyes with a catch-light, thick brows and a small
mouth, a tube body and thin tube limbs. No outlines: every part is shaded like a lit tube or sphere, and the far limbs
are drawn darker, so overlapping white parts stay readable. light(...) sets the scene's key light (direction, lit and
shade colours, an optional coloured rim light, a soft glow). The same rig in near-black with a red rim and red slit
eyes is the shadow, the inner voice.

  use_style('lit' | 'stick')                  the white bean person (default) or a stick figure, same rig and poses
  light(dir, lit, shade, rim, rim_a, glow)   call in each scene before drawing figures
  figure(c, x, ground, s, pose, ...)          feet on `ground` (or hips at hip_y); returns joints
  head(c, x, y, s, ...)                       just the head, e.g. on a pillow
  poses: stand, stand_front, slump, walk, run, sit, sit_slump, kneel, arms_up -> dicts of angles
  a limb is (upper, lower) angles, or ('ik', (x, y), bend) to reach a screen point
  arm(c, root, target, s)  a lone arm;  phone(c, x, y, s)  a lit phone
  wisps / scatter          smoke off the shadow, and the shadow breaking apart

Angles are degrees in screen space: 0 points down, +90 forward (the way the figure faces), 180 up. Side view faces
right; flip=True faces left. At s = 1 the figure is about 500 px tall.
"""
import math
import os
import sys

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kids-songs', 'storytime-kit'))
sys.path.insert(0, HERE)
from storytime_kit import P, circ, oval, line, rrect, lgrad, rgrad, ease, clamp, mix  # noqa: E402
from settings import HUMANOID as SEG, HUM_COLORS as HUM, SHADOW_COLORS as SHA, LIGHT_DEFAULT, STICK  # noqa: E402

L = dict(LIGHT_DEFAULT)
STYLE = {'name': 'lit'}


def use_style(name):
    """'lit' (the white bean person, default) or 'stick' (a stick figure with the same face, rig and poses)."""
    if name not in ('lit', 'stick'):
        raise ValueError(f'unknown style {name!r}: use lit or stick')
    STYLE['name'] = name


def stick():
    return STYLE['name'] == 'stick'


def head_r(s):
    return (STICK['head'] if stick() else SEG['head']) * s


def light(dir=None, lit=None, shade=None, rim=None, rim_a=None, glow=None):
    """Sets the key light for the figures drawn next; anything omitted goes back to LIGHT_DEFAULT."""
    L.clear()
    L.update(LIGHT_DEFAULT)
    for k, v in (('dir', dir), ('lit', lit), ('shade', shade), ('rim', rim), ('rim_a', rim_a), ('glow', glow)):
        if v is not None:
            L[k] = v
    n = math.hypot(*L['dir']) or 1.0
    L['dir'] = (L['dir'][0] / n, L['dir'][1] / n)


light()


def _d(a):
    r = math.radians(a)
    return math.sin(r), math.cos(r)


def _rot(pt, deg, piv):
    r = math.radians(deg)
    x, y = pt[0] - piv[0], pt[1] - piv[1]
    return piv[0] + x * math.cos(r) - y * math.sin(r), piv[1] + x * math.sin(r) + y * math.cos(r)


def ik2(root, target, l1, l2, bend):
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = max(1e-6, min(math.hypot(dx, dy), l1 + l2 - 1e-3))
    a = math.acos(clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1.0, 1.0))
    base = math.atan2(dy, dx)
    el = (root[0] + l1 * math.cos(base + bend * a), root[1] + l1 * math.sin(base + bend * a))
    return el, (root[0] + d * math.cos(base), root[1] + d * math.sin(base))


# ---------------------------------------------------------------- poses (side view, facing right)
def stand():
    return dict(torso=0.0, head=0.0, la=(-5.0, -2.0), ra=(6.0, 3.0), ll=(-4.0, -2.0), rl=(4.0, 2.0))


def stand_front():
    return dict(torso=0.0, head=0.0, la=(-12.0, -6.0), ra=(12.0, 6.0), ll=(-3.0, -1.0), rl=(3.0, 1.0))


def slump():
    return dict(torso=16.0, head=24.0, la=(10.0, 4.0), ra=(14.0, 8.0), ll=(-3.0, -2.0), rl=(5.0, 2.0))


def arms_up():
    return dict(torso=0.0, head=-14.0, la=(-158.0, -170.0), ra=(158.0, 170.0), ll=(-4.0, -2.0), rl=(4.0, 2.0))


def walk(p, amp=22.0, droop=0.0):
    lt, rt = amp * math.sin(p), -amp * math.sin(p)
    return dict(torso=5.0 + 14 * droop, head=-2.0 + 22 * droop,
                la=(-18 * math.sin(p) + 6 * droop, -18 * math.sin(p) + 16), ra=(18 * math.sin(p) + 6 * droop, 18 * math.sin(p) + 16),
                ll=(lt, lt - 40 * max(0.0, math.cos(p))), rl=(rt, rt - 40 * max(0.0, -math.cos(p))))


def run(p):
    lt, rt = 40 * math.sin(p) + 10, -40 * math.sin(p) + 10
    return dict(torso=14.0, head=-6.0,
                la=(-36 * math.sin(p), -36 * math.sin(p) + 92), ra=(36 * math.sin(p), 36 * math.sin(p) + 92),
                ll=(lt, lt - 20 - 75 * max(0.0, math.cos(p))), rl=(rt, rt - 20 - 75 * max(0.0, -math.cos(p))))


def sit():
    return dict(torso=4.0, head=6.0, la=(22.0, 70.0), ra=(28.0, 76.0), ll=(88.0, 2.0), rl=(84.0, -4.0))


def sit_slump():
    return dict(torso=-16.0, head=26.0, la=(16.0, 40.0), ra=(22.0, 48.0), ll=(86.0, 4.0), rl=(80.0, -4.0))


def kneel():
    return dict(torso=8.0, head=14.0, la=(14.0, 30.0), ra=(30.0, 60.0), ll=(0.0, -88.0), rl=(88.0, 0.0))


def lerp_pose(a, b, u):
    u = clamp(u)
    out = {}
    for k, va in a.items():
        vb = b.get(k, va)
        if (isinstance(va, tuple) and va and va[0] == 'ik') or (isinstance(vb, tuple) and vb and vb[0] == 'ik'):
            out[k] = vb if u >= 0.5 else va
        elif isinstance(va, tuple):
            out[k] = tuple(x + (y - x) * u for x, y in zip(va, vb))
        else:
            out[k] = va + (vb - va) * u
    return out


# ---------------------------------------------------------------- shading
def _path(pts):
    pp = skia.Path()
    pp.moveTo(*pts[0])
    for q in pts[1:]:
        pp.lineTo(*q)
    return pp


def _ld(rot):
    """The light direction in a canvas rotated by rot degrees."""
    dx, dy = L['dir']
    if not rot:
        return dx, dy
    r = math.radians(-rot)
    return dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)


def tube(c, pts, w, ld=None, back=False, cast=False, glow=True):
    """A lit white tube through pts, w wide, with round ends: shade colour, a soft highlight toward the light, an
    optional rim light on the far side. back darkens it (far limbs); cast drops a soft shadow on what's behind."""
    if stick():
        stick_path(c, pts, 1.0, back=back, w=max(6.0, w * 0.35))
        return
    ld = ld or L['dir']
    lit, shade = L['lit'], L['shade']
    if back:
        lit, shade = mix(lit, shade, 0.5), mix(shade, '#000000', 0.2)
    pp = _path(pts)
    if glow and L['glow']:
        c.drawPath(pp, P(L['lit'], L['glow'] * (0.5 if back else 1.0), sw=w + 22, blur=12))
    if cast:
        c.save()
        c.translate(-ld[0] * w * 0.3, -ld[1] * w * 0.3 + w * 0.08)
        c.drawPath(pp, P('#000000', 0.2, sw=w * 1.08, blur=w * 0.22))
        c.restore()
    base = P(shade, sw=w)
    c.drawPath(pp, base)
    fill = skia.Path()
    base.getFillPath(pp, fill)
    c.save()
    c.clipPath(fill, skia.ClipOp.kIntersect, True)
    c.save()
    c.translate(ld[0] * w * 0.24, ld[1] * w * 0.24)
    c.drawPath(pp, P(lit, sw=w * 0.7, blur=w * 0.13))
    c.restore()
    if L['rim_a']:
        c.save()
        c.translate(-ld[0] * w * 0.42, -ld[1] * w * 0.42)
        c.drawPath(pp, P(L['rim'], L['rim_a'], sw=w * 0.3, blur=w * 0.08))
        c.restore()
    c.restore()


def stick_path(c, pts, s, back=False, shadow=False, glow_a=0.55, w=None):
    """A stroke of the stick figure through pts (the shadow's version when shadow=True)."""
    w = (w or STICK['width']) * s
    pp = _path(pts)
    if shadow:
        if glow_a:
            c.drawPath(pp, P(SHA['rim'], glow_a, sw=w + 26 * s, blur=16 * s))
        c.drawPath(pp, P(SHA['rim'], sw=w + 2 * (2.5 * s + 1)))
        c.drawPath(pp, P(SHA['fill'], sw=w))
        return
    col = STICK['back'] if back else STICK['color']
    if STICK['glow']:
        c.drawPath(pp, P(col, STICK['glow'], sw=w + 18 * s, blur=10 * s))
    c.drawPath(pp, P(STICK['edge'], STICK['edge_a'], sw=w + 5 * s))
    c.drawPath(pp, P(col, sw=w))


def _shadow_tube(c, pts, w, s, glow_a):
    pp = _path(pts)
    if glow_a:
        c.drawPath(pp, P(SHA['rim'], glow_a, sw=w + 30 * s, blur=20 * s))
    c.drawPath(pp, P(SHA['rim'], sw=w + 2 * (3.5 * s + 1)))
    c.drawPath(pp, P(SHA['fill'], sw=w))


def _tuft(c, x, y, r, f, tilt, ld):
    c.save()
    c.rotate(tilt, x, y)
    q = skia.Path()
    q.moveTo(x - 0.16 * r * f, y - 0.95 * r)
    q.cubicTo(x - 0.19 * r * f, y - 1.22 * r, x + 0.02 * r * f, y - 1.38 * r, x + 0.27 * r * f, y - 1.30 * r)
    q.cubicTo(x + 0.11 * r * f, y - 1.27 * r, x + 0.05 * r * f, y - 1.15 * r, x + 0.08 * r * f, y - 0.97 * r)
    q.close()
    sh = lgrad(x + ld[0] * 0.4 * r, y - 1.15 * r + ld[1] * 0.4 * r, x - ld[0] * 0.4 * r, y - 1.15 * r - ld[1] * 0.4 * r,
               [L['lit'], L['shade']])
    c.drawPath(q, P('#ffffff', shader=sh))
    c.restore()


def _hair(c, x, y, r, f, tilt, ld, kind):
    """Drawn before the head sphere, so only the part outside it shows. kind: True or 'tuft' (him), 'pony', 'bun',
    or False / None for none."""
    if kind in (True, 'tuft', 'old'):
        if kind != 'old':
            _tuft(c, x, y, r, f, tilt, ld)
        if kind == 'old':
            for side in (-1, 1):
                for dx, dy, rr in ((0.92, 0.0, 0.26), (0.86, -0.24, 0.2), (0.86, 0.22, 0.2)):
                    circ(c, x + side * dx * r, y + dy * r, rr * r, '#F2F0F6')
                    circ(c, x + side * dx * r, y + dy * r, rr * r, '#A9A6BA', 0.6, sw=max(1.5, 0.02 * r))
        return
    if kind not in ('pony', 'bun'):
        return
    c.save()
    c.rotate(tilt, x, y)
    hc = mix(L['shade'], '#2A2A3A', 0.55)
    if kind == 'pony':
        q = skia.Path()
        q.moveTo(x - 0.55 * r * f, y - 0.75 * r)
        q.cubicTo(x - 1.25 * r * f, y - 0.9 * r, x - 1.35 * r * f, y + 0.1 * r, x - 1.05 * r * f, y + 0.55 * r)
        q.cubicTo(x - 0.95 * r * f, y + 0.1 * r, x - 0.85 * r * f, y - 0.35 * r, x - 0.5 * r * f, y - 0.4 * r)
        q.close()
        c.drawPath(q, P(hc))
        circ(c, x - 0.62 * r * f, y - 0.66 * r, 0.12 * r, '#E8607A')
    else:
        circ(c, x - 0.35 * r * f, y - 0.95 * r, 0.36 * r, hc)
    c.restore()


def head(c, x, y, s=1.0, expr='open', look=None, blink=0.0, brows=0.0, view='front', flip=False, tilt=0.0, mouth=None,
         tuft=False, ld=None, scheme='hum', glow_a=0.55, old=False):
    """The head alone at (x, y). tilt (degrees) turns the tuft with the head; the face stays upright."""
    r = head_r(s)
    f = -1.0 if flip else 1.0
    ld = ld or L['dir']
    if stick() and scheme != 'shadow':
        _hair(c, x, y, r, f, tilt, ld, tuft)
        if STICK['glow']:
            circ(c, x, y, r + 12 * s, STICK['color'], STICK['glow'], blur=10 * s)
        circ(c, x, y, r + 2.5 * s, STICK['edge'], STICK['edge_a'])
        circ(c, x, y, r, STICK['color'])
        face(c, (x, y), r, f, view, 0.0, look, expr, blink, brows, False, mouth, old)
        return
    if scheme == 'shadow':
        if glow_a:
            circ(c, x, y, r + 18 * s, SHA['rim'], glow_a, blur=22 * s)
        circ(c, x, y, r + 3.5 * s + 1, SHA['rim'])
        circ(c, x, y, r, SHA['fill'])
        face(c, (x, y), r, f, view, 0.0, look, expr, blink, brows, True)
        return
    if L['glow']:
        circ(c, x, y, r + 14 * s, L['lit'], L['glow'] * 1.2, blur=14 * s)
    _hair(c, x, y, r, f, tilt, ld, tuft)
    mid = mix(L['lit'], L['shade'], 0.45)
    c.drawCircle(x, y, r, P('#ffffff', shader=rgrad(x + ld[0] * 0.42 * r, y + ld[1] * 0.42 * r, 1.42 * r,
                                                      [L['lit'], L['lit'], mid, L['shade']], [0, 0.3, 0.68, 1])))
    if L['rim_a']:
        sh = lgrad(x + ld[0] * r, y + ld[1] * r, x - ld[0] * r, y - ld[1] * r,
                   [(L['rim'], 0.0), (L['rim'], 0.0), (L['rim'], L['rim_a'])], [0, 0.6, 1])
        c.drawCircle(x, y, r * 0.93, P('#ffffff', sw=r * 0.14, shader=sh, blur=r * 0.04))
    face(c, (x, y), r, f, view, 0.0, look, expr, blink, brows, False, mouth, old)


# ---------------------------------------------------------------- the figure
def _leg_ext(spec):
    if spec[0] == 'ik':
        return SEG['thigh'] + SEG['shin']
    a1, a2 = spec
    return math.cos(math.radians(a1)) * SEG['thigh'] + math.cos(math.radians(a2)) * SEG['shin']


def figure(c, x, ground, s=1.0, pose=None, view='side', flip=False, lift=0.0, rot=0.0, pivot=None, expr='open',
           look=None, blink=0.0, brows=0.0, scheme='hum', alpha=1.0, glow_a=0.55, ground_shadow=0.45, hold=None,
           legs=True, hip_y=None, mouth=None, tuft=False, old=False):
    """Draws the figure and returns its joints. rot turns it about pivot (default: the feet), clockwise degrees.
    expr: open, smile, sad, tired, closed, wide, grit, shout. brows 0..1 (determined). mouth overrides the mouth:
    small, flat, smile, frown, grit, shout, o. hold(c, joints) draws props after the body (hands: joints['la'][1],
    joints['ra'][1])."""
    p = pose or (stand_front() if view == 'front' else stand())
    f = -1.0 if flip else 1.0
    piv = pivot or (x, ground)
    shadow = scheme == 'shadow'
    ld = _ld(rot)
    if alpha < 1.0:
        c.saveLayerAlpha(None, int(255 * clamp(alpha)))
    if ground_shadow and not rot and not shadow:
        oval(c, x, ground + 6 * s, (60 if stick() else 90) * s, 12 * s, '#000000', ground_shadow * (1 - clamp(lift / (200 * s))),
             blur=8 * s)
    if rot:
        c.save()
        c.rotate(rot, *piv)

    def dv(a, ln):
        dx, dy = _d(a)
        return f * dx * ln * s, dy * ln * s

    low = max(_leg_ext(p['ll']), _leg_ext(p['rl'])) + SEG['leg_w'] / 2
    hip = (x, hip_y - lift) if hip_y is not None else (x, ground - low * s - lift)
    up = 180 - p['torso']
    dx, dy = dv(up, SEG['torso'])
    sh = (hip[0] + dx, hip[1] + dy)
    st = stick()
    dx, dy = dv(up - p['head'], (STICK['neck'] + STICK['head']) if st else (SEG['torso_w'] * 0.5 + SEG['head'] * 0.72))
    hd = (sh[0] + dx, sh[1] + dy)
    dx, dy = dv(up - p['head'], STICK['neck'] + 2)
    nk = (sh[0] + dx, sh[1] + dy)
    ux, uy = _d(up)
    ux *= f
    px_, py_ = -uy, ux
    if st:
        aroots, lroots = {'la': sh, 'ra': sh}, {'ll': hip, 'rl': hip}
    elif view == 'front':
        o_ = (SEG['torso_w'] / 2 - 2) * s
        aroots = {'la': (sh[0] - px_ * o_ - ux * 12 * s, sh[1] - py_ * o_ - uy * 12 * s),
                  'ra': (sh[0] + px_ * o_ - ux * 12 * s, sh[1] + py_ * o_ - uy * 12 * s)}
        lroots = {'ll': (hip[0] - px_ * 15 * s, hip[1] - py_ * 15 * s), 'rl': (hip[0] + px_ * 15 * s, hip[1] + py_ * 15 * s)}
    else:
        r0 = (sh[0] - ux * 12 * s, sh[1] - uy * 12 * s)
        aroots, lroots = {'la': r0, 'ra': r0}, {'ll': hip, 'rl': hip}
    joints = dict(hip=hip, shoulder=sh, head=hd, aroot=aroots['ra'], aroot_l=aroots['la'])

    def limb(k, l1, l2, w, back=False, cast=False):
        spec = p[k]
        root = aroots.get(k) or lroots[k]
        if spec[0] == 'ik':
            tgt = spec[1]
            if rot:
                tgt = _rot(tgt, -rot, piv)
            el, end = ik2(root, tgt, SEG[l1] * s, SEG[l2] * s, spec[2] * f)
        else:
            dx, dy = dv(spec[0], SEG[l1])
            el = (root[0] + dx, root[1] + dy)
            dx, dy = dv(spec[1], SEG[l2])
            end = (el[0] + dx, el[1] + dy)
        joints[k] = (el, end)
        if st:
            stick_path(c, [root, el, end], s, back=back, shadow=shadow, glow_a=glow_a)
        elif shadow:
            _shadow_tube(c, [root, el, end], w * s, s, glow_a)
        else:
            tube(c, [root, el, end], w * s, ld, back=back, cast=cast)

    def torso():
        if st:
            stick_path(c, [hip, sh, nk], s, shadow=shadow, glow_a=glow_a)
        elif shadow:
            _shadow_tube(c, [hip, sh], SEG['torso_w'] * s, s, glow_a)
        else:
            tube(c, [hip, sh], SEG['torso_w'] * s, ld)

    tilt = f * (p['torso'] + p['head'])

    def head_():
        head(c, hd[0], hd[1], s, expr, look, blink, brows, view, flip, tilt, mouth, tuft, ld, scheme, glow_a, old)

    if legs:
        if view == 'front':
            limb('ll', 'thigh', 'shin', SEG['leg_w'])
            limb('rl', 'thigh', 'shin', SEG['leg_w'])
        else:
            limb('ll', 'thigh', 'shin', SEG['leg_w'], back=True)
    else:
        joints['ll'] = joints['rl'] = (hip, hip)
    if view != 'front':
        limb('la', 'upper', 'fore', SEG['arm_w'], back=True)
    torso()
    if legs and view != 'front':
        limb('rl', 'thigh', 'shin', SEG['leg_w'], cast=True)
    if rot:
        if shadow:
            circ(c, hd[0], hd[1], head_r(s) + 3.5 * s + 1, SHA['rim'])
            circ(c, hd[0], hd[1], head_r(s), SHA['fill'])
        elif st:
            circ(c, hd[0], hd[1], head_r(s) + 2.5 * s, STICK['edge'], STICK['edge_a'])
            circ(c, hd[0], hd[1], head_r(s), STICK['color'])
        else:
            r = SEG['head'] * s
            _hair(c, hd[0], hd[1], r, f, tilt, ld, tuft)
            mid = mix(L['lit'], L['shade'], 0.45)
            c.drawCircle(hd[0], hd[1], r, P('#ffffff', shader=rgrad(hd[0] + ld[0] * 0.42 * r, hd[1] + ld[1] * 0.42 * r, 1.42 * r,
                                                                    [L['lit'], L['lit'], mid, L['shade']], [0, 0.3, 0.68, 1])))
    else:
        head_()
    if view == 'front':
        limb('la', 'upper', 'fore', SEG['arm_w'], cast=True)
    limb('ra', 'upper', 'fore', SEG['arm_w'], cast=True)
    if hold:
        hold(c, joints)
    if rot:
        c.restore()
        joints = {k: (tuple(_rot(q, rot, piv) for q in v) if isinstance(v[0], tuple) else _rot(v, rot, piv)) for k, v in joints.items()}
        face(c, joints['head'], head_r(s), f, view, 0.0, look, expr, blink, brows, shadow, mouth, old)
    if alpha < 1.0:
        c.restore()
    return joints


# ---------------------------------------------------------------- the face
MOUTHS = dict(open='small', smile='smile', sad='frown', tired='flat', closed='small', wide='o', grit='grit', shout='shout')


def face(c, hd, r, f, view, head_tilt, look, expr, blink, brows, shadow, mouth=None, old=False):
    if look is None:
        look = (0.0, 0.0) if view == 'front' else (0.55, 0.0)
    lx, ly = look[0] * f, look[1] + head_tilt / 45
    cx0, cy0 = hd[0] + lx * r * 0.36, hd[1] - 0.02 * r + ly * r * 0.2
    sp = (0.29 if view == 'front' else 0.25) * r
    ink = HUM['eye']
    for side in (-1, 1):
        ex, ey = cx0 + side * sp, cy0
        sz = 1.0 if view == 'front' or side * f > 0 else 0.86
        erx, ery = 0.105 * r * sz, 0.15 * r * sz
        if expr == 'wide':
            erx, ery = erx * 1.22, ery * 1.22
        if shadow:
            pp = skia.Path()
            pp.moveTo(ex - side * erx * 2.4, ey - ery * 0.55)
            pp.lineTo(ex + side * erx * 2.0, ey + ery * 0.2)
            pp.lineTo(ex + side * erx * 1.7, ey + ery * 0.85)
            pp.lineTo(ex - side * erx * 2.4, ey + ery * 0.1)
            pp.close()
            c.drawPath(pp, P(SHA['eye'], 0.7, blur=10 * r / 60))
            c.drawPath(pp, P(SHA['eye']))
            continue
        k = 1 - blink
        if expr == 'closed' or k <= 0.06:
            pp = skia.Path()
            pp.moveTo(ex - erx * 1.3, ey)
            pp.quadTo(ex, ey + ery * 0.7, ex + erx * 1.3, ey)
            c.drawPath(pp, P(ink, sw=max(2.5, 0.055 * r)))
        else:
            kk = k * (0.55 if expr == 'tired' else 1.0)
            oy = ey + ery * (1 - kk) * 0.5
            oval(c, ex, oy, erx, ery * kk, ink)
            if kk > 0.45:
                circ(c, ex - erx * 0.32, oy - ery * kk * 0.42, erx * 0.34, HUM['catch'])
            if expr == 'tired':
                line(c, ex - erx * 1.4, oy - ery * kk + 1, ex + erx * 1.4, oy - ery * kk + 1, ink, w=max(2.5, 0.05 * r))
        # brows: thick rounded strokes; brows (0..1) pulls the inner ends down into a determined frown
        bw = max(3.0, 0.075 * r)
        by = ey - ery - 0.16 * r
        inner, outer = ex - side * erx * 1.2, ex + side * erx * 1.5
        if expr == 'sad':
            yi, yo = by - 0.07 * r, by + 0.03 * r
        elif expr == 'tired':
            yi, yo = by + 0.04 * r, by + 0.05 * r
        elif expr == 'wide':
            yi, yo = by - 0.08 * r, by - 0.07 * r
        else:
            b = max(brows, 1.0 if expr in ('grit', 'shout') else 0.0)
            yi, yo = by - 0.01 * r + 0.09 * r * b, by - 0.03 * r - 0.03 * r * b
        if old:
            yo += 0.05 * r
            bw *= 1.3
        pp = skia.Path()
        pp.moveTo(inner, yi)
        pp.quadTo((inner + outer) / 2, min(yi, yo) - 0.025 * r, outer, yo)
        c.drawPath(pp, P('#BDBAC9' if old else HUM['brow'], sw=bw))
    if shadow:
        return
    if old:
        for side in (-1, 1):
            ex = cx0 + side * sp
            circ(c, ex, cy0, 0.21 * r, '#FFFFFF', 0.12)
            circ(c, ex, cy0, 0.21 * r, '#2A2730', sw=max(2.0, 0.045 * r))
        line(c, cx0 - sp + 0.21 * r, cy0 - 0.02 * r, cx0 + sp - 0.21 * r, cy0 - 0.02 * r, '#2A2730', w=max(2.0, 0.04 * r))
    m = mouth or MOUTHS.get(expr, 'small')
    mx, my = cx0 + (0.03 * r * f if view != 'front' else 0.0), cy0 + 0.34 * r
    if old:
        bx = mx
        q = skia.Path()
        q.moveTo(bx - 0.62 * r, cy0 + 0.05 * r)
        q.cubicTo(bx - 0.72 * r, cy0 + 0.75 * r, bx - 0.3 * r, cy0 + 1.25 * r, bx, cy0 + 1.3 * r)
        q.cubicTo(bx + 0.3 * r, cy0 + 1.25 * r, bx + 0.72 * r, cy0 + 0.75 * r, bx + 0.62 * r, cy0 + 0.05 * r)
        q.cubicTo(bx + 0.4 * r, cy0 + 0.32 * r, bx - 0.4 * r, cy0 + 0.32 * r, bx - 0.62 * r, cy0 + 0.05 * r)
        q.close()
        c.drawPath(q, P('#000000', 0.18, blur=0.08 * r))
        c.drawPath(q, P('#ffffff', shader=lgrad(bx, cy0 + 0.2 * r, bx, cy0 + 1.3 * r, ['#FFFFFF', '#C6C2D4'])))
        c.drawPath(q, P('#8E8AA4', 0.7, sw=max(2.0, 0.03 * r)))
        for side in (-1, 1):
            q = skia.Path()
            q.moveTo(bx, my - 0.07 * r)
            q.quadTo(bx + side * 0.2 * r, my - 0.2 * r, bx + side * 0.38 * r, my + 0.04 * r)
            q.quadTo(bx + side * 0.18 * r, my - 0.03 * r, bx, my + 0.01 * r)
            q.close()
            c.drawPath(q, P('#F2F0F6'))
            c.drawPath(q, P('#8E8AA4', 0.7, sw=max(1.5, 0.025 * r)))
    mw = max(2.5, 0.05 * r)
    ink = HUM['mouth']
    if m == 'small':
        pp = skia.Path()
        pp.moveTo(mx - 0.07 * r, my)
        pp.quadTo(mx, my + 0.02 * r, mx + 0.07 * r, my)
        c.drawPath(pp, P(ink, sw=mw))
    elif m == 'flat':
        line(c, mx - 0.09 * r, my + 0.01 * r, mx + 0.09 * r, my - 0.005 * r, ink, w=mw)
    elif m in ('smile', 'frown'):
        pp = skia.Path()
        dy = 0.09 * r if m == 'smile' else -0.07 * r
        pp.moveTo(mx - 0.12 * r, my - dy * 0.3)
        pp.quadTo(mx, my + dy, mx + 0.12 * r, my - dy * 0.3)
        c.drawPath(pp, P(ink, sw=mw))
    elif m == 'grit':
        w_, h_ = 0.34 * r, 0.13 * r
        rrect(c, mx - w_ / 2, my - h_ / 2, w_, h_, 0.05 * r, '#FFFFFF')
        rrect(c, mx - w_ / 2, my - h_ / 2, w_, h_, 0.05 * r, ink, sw=mw * 0.8)
        line(c, mx - w_ / 2 + 2, my, mx + w_ / 2 - 2, my, ink, w=mw * 0.6)
    elif m == 'shout':
        oval(c, mx, my + 0.03 * r, 0.12 * r, 0.10 * r, HUM['mouth_in'])
        oval(c, mx, my + 0.03 * r, 0.12 * r, 0.10 * r, ink, sw=mw * 0.8)
    elif m == 'o':
        oval(c, mx, my, 0.045 * r, 0.055 * r, ink, sw=mw * 0.8)


# ---------------------------------------------------------------- the shadow's smoke
def wisps(c, joints, t, s, a=1.0, n=18, seed=3):
    """Smoke curling up off the shadow's head and shoulders."""
    rng = np.random.default_rng(seed)
    pts = [joints['head'], joints['shoulder'], joints['ra'][0], joints['la'][0]]
    for i in range(n):
        bx, by = pts[i % len(pts)]
        ph = (t * (0.35 + rng.random() * 0.4) + rng.random()) % 1.0
        x = bx + (rng.random() - 0.5) * 90 * s + 26 * s * math.sin(ph * 7 + i)
        y = by - 30 * s - ph * 220 * s
        r = (10 + 22 * ph) * s
        circ(c, x, y, r, SHA['rim'], 0.18 * a * (1 - ph), blur=r * 0.6)
        circ(c, x, y, r * 0.8, SHA['fill'], 0.5 * a * (1 - ph), blur=r * 0.35)


def scatter(c, joints, s, u, seed=11, n=170):
    """The shadow breaking into embers and smoke; u goes 0 -> 1."""
    if u <= 0 or u >= 1:
        return
    rng = np.random.default_rng(seed)
    hx, hy = joints['head']
    fx_, fy_ = joints['hip']
    for _ in range(n):
        w = rng.random()
        bx = fx_ + (hx - fx_) * w + (rng.random() - 0.5) * 120 * s
        by = fy_ + (hy - fy_) * w + (rng.random() - 0.5) * 60 * s
        d = clamp(u * 1.3 - rng.random() * 0.3)
        if d <= 0 or d >= 1:
            continue
        x = bx + (rng.random() - 0.5) * 300 * s * d
        y = by - (120 + rng.random() * 420) * s * d
        r = (5 + rng.random() * 14) * s * (1 - 0.6 * d)
        ember = rng.random() < 0.3
        circ(c, x, y, r, SHA['rim'] if ember else SHA['fill'], 0.9 * (1 - d))
        if not ember:
            circ(c, x, y, r, SHA['rim'], 0.45 * (1 - d), sw=2)


# ---------------------------------------------------------------- pieces
def arm(c, root, target, s=1.0, bend=1, scheme='hum', back=False):
    """A lone arm from root to target (screen points), e.g. reaching out of a blanket. Returns the hand point."""
    el, end = ik2(root, target, SEG['upper'] * s, SEG['fore'] * s, bend)
    if stick():
        stick_path(c, [root, el, end], s, back=back, shadow=scheme == 'shadow')
    elif scheme == 'shadow':
        _shadow_tube(c, [root, el, end], SEG['arm_w'] * s, s, 0.55)
    else:
        tube(c, [root, el, end], SEG['arm_w'] * s, back=back, cast=True)
    return end


def phone(c, x, y, s=1.0, rot=0.0, t=0.0, glow_a=1.0):
    """A phone held at (x, y) with a scrolling feed on its lit screen."""
    from storytime_kit import glow as glow_
    if glow_a:
        glow_(c, x, y, 220 * s, '#6FA8FF', 0.28 * glow_a)
    c.save()
    c.rotate(rot, x, y)
    w, h = 58 * s, 108 * s
    rrect(c, x - w / 2, y - h / 2, w, h, 9 * s, '#0B0B0E')
    sx, sy, sw_, sh_ = x - w / 2 + 4 * s, y - h / 2 + 6 * s, w - 8 * s, h - 12 * s
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(sx, sy, sw_, sh_))
    rrect(c, sx, sy, sw_, sh_, 5 * s, '#DCE8FF')
    off = (t * 120 * s) % (40 * s)
    cols = ['#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7', '#FF9F43', '#54A0FF']
    for i in range(-1, 4):
        k = (i + int(t * 3)) % len(cols)
        yy = sy + i * 40 * s - off + 40 * s
        rrect(c, sx + 3 * s, yy, sw_ - 6 * s, 30 * s, 4 * s, cols[k], 0.9)
    c.restore()
    c.restore()
