"""storytime-kit: the flat 2D look of the Story Time with Kenji Shorts, drawn with skia-python at 1080x1920, 30 fps.

Everything one episode needs besides its own scenes: colour and drawing helpers, the character rig (person()), props
(key, mug, phone, paper, wrench, book), set pieces (window, framed picture, lamp, couch, coffee table, house, tree,
car, fog, sparkle), the caption style, the hook card, the vignette, and the renderer that turns a narration timeline
plus a dict of scene functions into one H.264 file per scene and a concat list.

  python storytime_kit.py        -> redraws preview.png (hook card, caption, expressions, looks, props)

Fonts: DejaVu (Sans Bold for captions). Run `python get_fonts.py` once if they aren't installed.
"""
import skia, numpy as np, math, random, subprocess, os, json

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- settings
W, H, FPS = 1080, 1920, 30
CAPTION_SIZE, CAPTION_MAXW, CAPTION_STROKE = 66, 960, 10       # DejaVu Sans Bold, white with a black outline
HOOK_SIZES, HOOK_TOP, HOOK_YELLOW = (56, 40), 140, '#F4C542'   # hook card: white line(s), yellow line, top y
HOOK_SHOW_UNTIL, HOOK_FADE = 3.7, 0.35                          # seconds
SCENE_FADE_IN, END_FADE = 0.2, 0.9                              # dip from black at each cut, fade out at the end
VIGNETTE = 0.6
X264 = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p']
FONT_FILES = dict(bold='DejaVuSans-Bold.ttf', reg='DejaVuSans.ttf', serif='DejaVuSerif.ttf', serifb='DejaVuSerif-Bold.ttf',
                  serifi='DejaVuSerif-Italic.ttf', mono='DejaVuSansMono-Bold.ttf', cond='DejaVuSansCondensed-Bold.ttf')
FONT_DIRS = [os.environ.get('DEJAVU_DIR', ''), os.path.join(HERE, 'fonts'), '/usr/share/fonts/truetype/dejavu',
             os.path.expanduser('~/.fonts'), os.path.expanduser('~/.local/share/fonts'), os.path.expanduser('~/Library/Fonts')]


def _font_path(name):
    for d in FONT_DIRS:
        if d and os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    raise FileNotFoundError(f'{name} not found; run python get_fonts.py (or set DEJAVU_DIR)')


TF = {k: skia.Typeface.MakeFromFile(_font_path(f)) for k, f in FONT_FILES.items()}


def hexrgb(h):
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def col(h, a=1.0):
    r, g, b = hexrgb(h)
    return skia.ColorSetARGB(max(0, min(255, int(round(a * 255)))), r, g, b)


def mix(h1, h2, t):
    t = max(0.0, min(1.0, t))
    a, b = hexrgb(h1), hexrgb(h2)
    return '#%02x%02x%02x' % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def dk(h, f=0.7):
    return mix(h, '#000000', 1 - f)


def lt(h, f=0.3):
    return mix(h, '#ffffff', f)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def eout(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ramp(t, t0, d):
    return ease((t - t0) / d) if d > 0 else float(t >= t0)


def P(c='#000000', a=1.0, sw=0, blur=0, shader=None, cap='round'):
    p = skia.Paint(AntiAlias=True)
    p.setColor(col(c, a))
    if sw:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(sw)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == 'round' else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
    return p


def R(x, y, w, h):
    return skia.Rect.MakeXYWH(x, y, w, h)


def rect(c, x, y, w, h, cl, a=1.0, **k):
    c.drawRect(R(x, y, w, h), P(cl, a, **k))


def rrect(c, x, y, w, h, r, cl, a=1.0, **k):
    c.drawRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), P(cl, a, **k))


def circ(c, x, y, r, cl, a=1.0, **k):
    c.drawCircle(x, y, r, P(cl, a, **k))


def oval(c, cx, cy, rx, ry, cl, a=1.0, **k):
    c.drawOval(R(cx - rx, cy - ry, 2 * rx, 2 * ry), P(cl, a, **k))


def line(c, x0, y0, x1, y1, cl, w=4, a=1.0, cap='round', blur=0):
    c.drawLine(x0, y0, x1, y1, P(cl, a, sw=w, cap=cap, blur=blur))


def path(pts, close=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def poly(c, pts, cl, a=1.0, **k):
    c.drawPath(path(pts), P(cl, a, **k))


def _cols(cols):
    return [col(cc[0], cc[1]) if isinstance(cc, tuple) else col(cc) for cc in cols]


def lgrad(x0, y0, x1, y1, cols, pos=None):
    return skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)], _cols(cols), pos)


def rgrad(x, y, r, cols, pos=None):
    return skia.GradientShader.MakeRadial(skia.Point(x, y), r, _cols(cols), pos)


def grect(c, x, y, w, h, cols, pos=None, horiz=False, a=1.0):
    sh = lgrad(x, y, x + w if horiz else x, y if horiz else y + h, cols, pos)
    c.drawRect(R(x, y, w, h), P('#ffffff', a, shader=sh))


def glow(c, x, y, r, cl, a=0.5):
    c.drawCircle(x, y, r, P('#ffffff', shader=rgrad(x, y, r, [(cl, a), (cl, a * 0.35), (cl, 0)], [0, 0.45, 1])))


def cone(c, x, y, w0, w1, h, cl, a=0.25):
    sh = lgrad(x, y, x, y + h, [(cl, a), (cl, a * 0.5), (cl, 0)], [0, 0.6, 1])
    c.drawPath(path([(x - w0 / 2, y), (x + w0 / 2, y), (x + w1 / 2, y + h), (x - w1 / 2, y + h)]), P('#ffffff', shader=sh, blur=6))


_FC = {}


def font(tf, size):
    k = (tf, round(size, 1))
    if k not in _FC:
        f = skia.Font(TF[tf], size)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        _FC[k] = f
    return _FC[k]


def tw(s, size, tf='bold'):
    return font(tf, size).measureText(s)


def text(c, s, x, y, size, cl='#ffffff', a=1.0, tf='bold', align='center', sw=0, scol='#000000', blur=0):
    f = font(tf, size)
    w = f.measureText(s)
    x0 = x - w / 2 if align == 'center' else (x - w if align == 'right' else x)
    if sw:
        c.drawString(s, x0, y, f, P(scol, a, sw=sw))
    c.drawString(s, x0, y, f, P(cl, a, blur=blur))
    return w


def wrap(s, size, maxw, tf='bold'):
    words, lines, cur = s.split(), [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if not cur or tw(t, size, tf) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def caption(c, s, y, age):
    size = CAPTION_SIZE
    ls = wrap(s, size, CAPTION_MAXW)
    lh = size * 1.18
    pop = eout(age / 0.14)
    sc = 0.9 + 0.1 * pop
    a = clamp(age / 0.07)
    y0 = y - (len(ls) - 1) * lh / 2
    c.save()
    c.translate(W / 2, y0)
    c.scale(sc, sc)
    c.translate(-W / 2, -y0)
    for i, ln in enumerate(ls):
        yy = y0 + i * lh + size * 0.36
        text(c, ln, W / 2 + 2, yy + 6, size, '#000000', a * 0.55, blur=5)
        text(c, ln, W / 2, yy, size, '#ffffff', a, sw=CAPTION_STROKE)
    c.restore()


def hook_card(c, l1, l2, a):
    if a <= 0:
        return
    s1, s2 = HOOK_SIZES
    L1, L2 = wrap(l1, s1, 920), wrap(l2, s2, 920)
    hgt = 44 + len(L1) * s1 * 1.16 + 10 + len(L2) * s2 * 1.22 + 26
    x, y, w = 38, HOOK_TOP, 1004
    rrect(c, x + 4, y + 10, w, hgt, 30, '#000000', 0.35 * a, blur=14)
    rrect(c, x, y, w, hgt, 30, '#0B0B0D', 0.8 * a)
    yy = y + 44 + s1 * 0.78
    for ln in L1:
        text(c, ln, W / 2, yy, s1, '#ffffff', a)
        yy += s1 * 1.16
    yy += 4
    for ln in L2:
        text(c, ln, W / 2, yy, s2, HOOK_YELLOW, a)
        yy += s2 * 1.22


def vignette(c, s=0.6, cy=0.46):
    c.drawRect(R(0, 0, W, H), P('#ffffff', shader=rgrad(W / 2, H * cy, 1180, [('#000000', 0), ('#000000', 0), ('#000000', s)], [0, 0.5, 1])))


# ---------------- characters ----------------
SKIN = dict(light='#F2CBA8', mid='#E2AE88', tan='#C98F68', dark='#8E5B3D')


def _limb(x0, y0, a, ln):
    r = math.radians(a)
    return x0 + ln * math.sin(r), y0 + ln * math.cos(r)


def _arm(c, side, x0, y0, spec, colr, skin, w=25, ln=176):
    sgn = 1 if side > 0 else -1
    if isinstance(spec, (tuple, list)):
        a1, a2 = spec
        ex, ey = _limb(0, 0, a1, ln * 0.52)
        hx, hy = _limb(ex, ey, a2, ln * 0.5)
        pts = [(x0, y0), (x0 + sgn * ex, y0 + ey), (x0 + sgn * hx, y0 + hy)]
    else:
        hx, hy = _limb(0, 0, spec, ln)
        pts = [(x0, y0), (x0 + sgn * hx, y0 + hy)]
    pa = skia.Path()
    pa.moveTo(*pts[0])
    for q in pts[1:]:
        pa.lineTo(*q)
    c.drawPath(pa, P(colr, sw=w))
    hx, hy = pts[-1]
    circ(c, hx, hy, w * 0.5, skin)
    return hx, hy


def person(c, x, y, s=1.0, L=None, mode='stand', phase=0.0, arms=(4, 4), expr='neutral', look=0.0,
           t=0.0, seed=0, hold=None, back=False, faceless=False, rot=0.0, shin=170, blink=True, wet=False, legs=True):
    L = L or {}
    skin = L.get('skin', SKIN['light'])
    hairc = L.get('hair_col', '#4A3426')
    top = L.get('top', '#2F3A56')
    pants = L.get('pants', '#2A2E38')
    shoe = L.get('shoe', '#1B1B20')
    c.save()
    c.translate(x, y)
    if rot:
        c.rotate(rot)
    c.scale(s, s)
    bob = 0.0
    la = ra = 0.0
    al, ar = arms
    if mode == 'walk':
        sw = math.sin(phase)
        bob = -abs(math.cos(phase)) * 5
        la, ra = 20 * sw, -20 * sw
        al = (al + 14 * sw) if not isinstance(al, (tuple, list)) else (al[0] + 22 * sw, al[1] + 22 * sw)
        ar = (ar - 14 * sw) if not isinstance(ar, (tuple, list)) else (ar[0] - 22 * sw, ar[1] - 22 * sw)
    oy = 212 if mode == 'sit' else 0
    c.translate(0, bob + oy)
    hy = -452
    r = 46
    hs = L.get('hair', 'short')
    if hs == 'long':
        c.drawPath(_hair_back(r, hy), P(hairc))
    if mode == 'sit' and not legs:
        pass
    elif mode == 'sit':
        rrect(c, -62, -214, 124, 34, 12, pants)
        for sx in (-27, 27):
            line(c, sx, -196, sx, -196 + shin, pants, 25)
            oval(c, sx + (4 if sx > 0 else -4), -196 + shin + 6, 26, 10, shoe)
    elif not L.get('dress'):
        for sx, ang in ((-24, la), (24, ra)):
            ex, ey = _limb(sx, -214, ang, 200)
            line(c, sx, -214, ex, ey, pants, 25)
            oval(c, ex + (4 if sx > 0 else -4), ey + 3, 26, 10, shoe)
    else:
        for sx, ang in ((-20, la), (20, ra)):
            ex, ey = _limb(sx, -120, ang, 106)
            line(c, sx, -120, ex, ey, L.get('legs', '#2B2B33'), 18)
            oval(c, ex + (4 if sx > 0 else -4), ey + 3, 20, 8, shoe)
    if L.get('dress'):
        rrect(c, -64, -400, 128, 170, 18, top)
        poly(c, [(-60, -250), (60, -250), (110, -60), (-110, -60)], top)
    else:
        rrect(c, -66, -402, 132, 196, 18, top)
        if L.get('stripe'):
            rect(c, -66, -340, 132, 16, L['stripe'])
        if L.get('hood'):
            oval(c, 0, -400, 52, 20, dk(top, 0.8))
            line(c, -12, -392, -14, -350, '#d9d4c8', 3)
            line(c, 12, -392, 14, -350, '#d9d4c8', 3)
        if L.get('patch'):
            rrect(c, 18, -300, 30, 26, 4, L['patch'])
            rrect(c, -50, -250, 26, 22, 4, dk(L['patch'], 0.8))
    if not back:
        if L.get('tie'):
            poly(c, [(-22, -402), (22, -402), (0, -356)], L.get('shirt', '#F2F2F2'))
            poly(c, [(0, -394), (8, -380), (5, -300), (0, -290), (-5, -300), (-8, -380)], L['tie'])
        elif L.get('collar'):
            poly(c, [(-24, -402), (0, -376), (24, -402)], L['collar'])
        if L.get('apron'):
            ap = L['apron']
            rrect(c, -50, -372, 100, 250, 10, ap)
            line(c, -40, -372, -16, -404, dk(ap, 0.8), 6)
            line(c, 40, -372, 16, -404, dk(ap, 0.8), 6)
            rrect(c, -26, -300, 52, 34, 5, dk(ap, 0.85))
        if L.get('necklace'):
            c.drawPath(_arcpath(0, -404, 40, 14), P(L['necklace'], sw=4))
    if back and hs == 'long':
        pass
    hand_r = _arm(c, 1, 78, -392, ar, top, skin)
    _arm(c, -1, -78, -392, al, top, skin)
    rect(c, -11, -414, 22, 18, skin)
    circ(c, 0, hy, r, skin)
    if back:
        _hair_backview(c, hs, hairc, r, hy)
    else:
        if L.get('beard'):
            c.drawPath(_beard(r, hy), P(L.get('beard_col', hairc), L.get('beard_a', 1.0)))
        if not faceless:
            _face(c, expr, look, hy, t, seed, blink, L)
        _hair_front(c, hs, hairc, r, hy, L)
        if L.get('mustache') and not faceless:
            mp = skia.Path()
            mp.moveTo(-19, hy + 18)
            mp.quadTo(0, hy + 4, 19, hy + 18)
            mp.quadTo(0, hy + 24, -19, hy + 18)
            mp.close()
            c.drawPath(mp, P(L['mustache']))
        if L.get('glasses') and not faceless:
            gx = look * 5
            for sx in (-17, 17):
                circ(c, sx + gx, hy - 2, 12, '#2A2A2A', sw=3.5)
            line(c, -5 + gx, hy - 3, 5 + gx, hy - 3, '#2A2A2A', 3)
        if wet:
            for i in range(3):
                yy = hy - 20 + ((t * 120 + i * 37) % 70)
                oval(c, -30 + i * 30, yy, 3, 5, '#9CC8E8', 0.8)
    if hold:
        c.save()
        c.translate(*hand_r)
        hold(c)
        c.restore()
    c.restore()


def _arcpath(cx, cy, rx, ry):
    p = skia.Path()
    p.moveTo(cx - rx, cy)
    p.quadTo(cx, cy + ry * 2, cx + rx, cy)
    return p


def _hair_back(r, hy):
    p = skia.Path()
    p.addCircle(0, hy - 4, r + 9)
    p.addRRect(skia.RRect.MakeRectXY(R(-r - 11, hy - 10, 2 * r + 22, r * 2.5), 26, 26))
    return p


def _cap(r, hy, fringe):
    p = skia.Path()
    cr = r + 4
    p.moveTo(-cr + 1, hy + 4)
    p.arcTo(R(-cr, hy - 3 - cr, 2 * cr, 2 * cr), 180, 180, False)
    p.lineTo(cr - 1, hy + 4)
    p.lineTo(r - 2, hy + 8)
    fringe(p)
    p.close()
    return p


def _hair_front(c, hs, hc, r, hy, L):
    if hs in ('short', 'bun'):
        top = 0.42 if hs == 'short' else 0.3
        c.drawPath(_cap(r, hy, lambda p: p.cubicTo(r * 0.55, hy - r * top - 8, -r * 0.55, hy - r * top - 8, -(r - 2), hy + 8)), P(hc))
        if hs == 'bun':
            circ(c, 0, hy - r - 14, 21, hc)
    elif hs == 'side':
        c.drawPath(_cap(r, hy, lambda p: p.cubicTo(r * 0.35, hy - r * 0.18, -r * 0.45, hy - r * 0.86, -(r - 2), hy - 2)), P(hc))
    elif hs == 'long':
        p = skia.Path()
        cr = r + 6
        p.moveTo(-cr, hy + 34)
        p.arcTo(R(-cr, hy - 4 - cr, 2 * cr, 2 * cr), 180, 180, False)
        p.lineTo(cr, hy + 34)
        p.lineTo(r - 8, hy + 34)
        p.lineTo(r - 4, hy - 2)
        p.cubicTo(r * 0.5, hy - r * 0.45, r * 0.1, hy - r * 0.7, 0, hy - r * 0.74)
        p.cubicTo(-r * 0.1, hy - r * 0.7, -r * 0.5, hy - r * 0.45, -(r - 4), hy - 2)
        p.lineTo(-(r - 8), hy + 34)
        p.close()
        c.drawPath(p, P(hc))
    elif hs == 'bald':
        for sx in (-1, 1):
            oval(c, sx * (r - 3), hy - 2, 9, 20, hc)
    elif hs == 'messy':
        p = skia.Path()
        n = 11
        for i in range(n + 1):
            ang = math.radians(180 + 180 * i / n)
            rr = r + (12 if i % 2 else 4)
            px, py = rr * math.cos(ang), hy - 3 + rr * math.sin(ang)
            (p.moveTo if i == 0 else p.lineTo)(px, py)
        p.lineTo(r + 2, hy + 14)
        p.lineTo(r - 4, hy + 10)
        for i in range(6):
            fx = r - 4 - (2 * r - 8) * (i + 0.5) / 6
            p.lineTo(fx, hy - r * 0.32 + (8 if i % 2 else -4))
        p.lineTo(-(r - 4), hy + 10)
        p.lineTo(-(r + 2), hy + 14)
        p.close()
        c.drawPath(p, P(hc))
    elif hs == 'beanie':
        bc = L.get('beanie', '#5B4A3A')
        p = skia.Path()
        cr = r + 6
        p.moveTo(-cr, hy - r * 0.18)
        p.arcTo(R(-cr, hy - r * 0.18 - cr * 1.05, 2 * cr, 2 * cr * 1.05), 180, 180, False)
        p.close()
        c.drawPath(p, P(bc))
        rrect(c, -cr - 2, hy - r * 0.32, 2 * cr + 4, 20, 8, dk(bc, 0.82))
        for i in range(-3, 4):
            line(c, i * 11, hy - r * 0.42, i * 11 * 0.8, hy - r - 2, dk(bc, 0.88), 3)


def _hair_backview(c, hs, hc, r, hy):
    if hs == 'long':
        c.drawPath(_hair_back(r, hy), P(hc))
    elif hs == 'bald':
        for sx in (-1, 1):
            oval(c, sx * (r - 6), hy + 4, 14, 24, hc)
        oval(c, 0, hy + 22, r - 6, 16, hc)
    elif hs == 'beanie':
        p = skia.Path()
        p.addArc(R(-r - 4, hy - r - 6, 2 * r + 8, 2 * r + 8), 175, 190)
        p.close()
        c.drawPath(p, P('#5B4A3A'))
    else:
        p = skia.Path()
        p.addArc(R(-r - 4, hy - r - 6, 2 * r + 8, 2 * r + 10), 150, 240)
        p.close()
        c.drawPath(p, P(hc))
        if hs == 'bun':
            circ(c, 0, hy - r - 12, 21, hc)


def _beard(r, hy):
    p = skia.Path()
    p.moveTo(-(r - 1), hy - 2)
    p.cubicTo(-(r - 1), hy + r * 1.25, r - 1, hy + r * 1.25, r - 1, hy - 2)
    p.lineTo(r - 9, hy + 4)
    p.quadTo(0, hy + 14, -(r - 9), hy + 4)
    p.close()
    return p


def _face(c, expr, look, hy, t, seed, blink, L):
    ex = look * 6
    ey = hy - 2
    eyec = '#26211F'
    brc = dk(L.get('hair_col', '#4A3426'), 0.7) if L.get('hair') not in ('bald',) else '#6E6A66'
    if L.get('brow_col'):
        brc = L['brow_col']
    mc = '#6B3A32'
    closed = expr == 'sleep' or (blink and ((t * 0.27 + seed * 0.37) % 1.0) < 0.035)
    if closed:
        for sx in (-16, 16):
            p = skia.Path()
            p.moveTo(sx - 7 + ex, ey)
            p.quadTo(sx + ex, ey + 6, sx + 7 + ex, ey)
            c.drawPath(p, P(eyec, sw=3.2))
    else:
        rr = 6.5 if expr in ('shock', 'stare') else 5.2
        for sx in (-16, 16):
            circ(c, sx + ex, ey, rr, eyec)
    by = hy - 21
    b = {'neutral': ((-25, by, -9, by), (9, by, 25, by)),
         'smile': ((-25, by - 2, -9, by - 3), (9, by - 3, 25, by - 2)),
         'grin': ((-25, by - 1, -9, by + 3), (9, by + 3, 25, by - 1)),
         'angry': ((-26, by - 5, -8, by + 5), (8, by + 5, 26, by - 5)),
         'worried': ((-26, by + 3, -9, by - 5), (9, by - 5, 26, by + 3)),
         'sad': ((-26, by + 4, -9, by - 4), (9, by - 4, 26, by + 4)),
         'shock': ((-26, by - 8, -8, by - 10), (8, by - 10, 26, by - 8)),
         'stare': ((-26, by - 2, -8, by - 1), (8, by - 1, 26, by - 2)),
         'sinister': ((-26, by - 3, -8, by + 4), (8, by - 6, 26, by - 8)),
         'sleep': ((-25, by + 2, -9, by + 2), (9, by + 2, 25, by + 2))}[expr]
    for x0, y0, x1, y1 in b:
        line(c, x0 + ex, y0, x1 + ex, y1, brc, 4.5)
    my = hy + 22
    mx = ex * 0.6
    p = skia.Path()
    if expr in ('smile',):
        p.moveTo(mx - 13, my - 3)
        p.quadTo(mx, my + 9, mx + 13, my - 3)
    elif expr == 'grin':
        p.moveTo(mx - 20, my - 5)
        p.quadTo(mx, my + 13, mx + 20, my - 5)
    elif expr in ('worried', 'sad', 'angry'):
        p.moveTo(mx - 11, my + 4)
        p.quadTo(mx, my - 5, mx + 11, my + 4)
    elif expr == 'shock':
        oval(c, mx, my + 2, 7, 9, '#3A1F1F')
        return
    elif expr == 'sinister':
        p.moveTo(mx - 12, my)
        p.quadTo(mx + 4, my + 7, mx + 15, my - 6)
    else:
        p.moveTo(mx - 8, my)
        p.lineTo(mx + 8, my)
    c.drawPath(p, P(mc, sw=4))


# ---------------- props ----------------
def key(c, x, y, s=1.0, rot=0.0, cl='#D6B04C', a=1.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    circ(c, 0, 0, 15, cl, a, sw=8)
    rect(c, 14, -4, 46, 8, cl, a)
    poly(c, [(36, 4), (42, 4), (42, 12), (48, 12), (48, 4), (54, 4), (54, 9), (60, 9), (60, 4)], cl, a)
    circ(c, -5, -5, 4, '#ffffff', 0.35 * a)
    c.restore()


def mug(c, x, y, s=1.0, cl='#B03A2E', handle=1, steam=0.0, t=0.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    if handle:
        c.drawPath(_handle(handle), P(dk(cl, 0.85), sw=8))
    rrect(c, -24, -30, 48, 58, 8, cl)
    oval(c, 0, -30, 24, 6, dk(cl, 0.6))
    rect(c, -24, -16, 48, 6, lt(cl, 0.25), 0.5)
    if steam > 0:
        for i in range(3):
            ph = t * 1.3 + i * 0.33
            yy = -40 - (ph % 1.0) * 50
            line(c, -10 + i * 10 + 4 * math.sin(ph * 6), yy, -10 + i * 10 + 4 * math.sin(ph * 6 + 1), yy - 14, '#ffffff', 3, steam * (1 - (ph % 1.0)) * 0.6)
    c.restore()


def _handle(side):
    p = skia.Path()
    p.moveTo(side * 22, -18)
    p.cubicTo(side * 44, -18, side * 44, 12, side * 22, 12)
    return p


def book(c, x, y, w, h, cl, label=None):
    rrect(c, x, y, w, h, 3, cl)
    rect(c, x + 3, y + 8, w - 6, 5, lt(cl, 0.35), 0.7)
    rect(c, x + 3, y + h - 14, w - 6, 5, lt(cl, 0.35), 0.7)


def paper(c, x, y, w, h, rot=0.0, cl='#F3EFE6', lines=6, a=1.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    rect(c, -w / 2 + 4, -h / 2 + 6, w, h, '#000000', 0.25 * a, blur=6)
    rect(c, -w / 2, -h / 2, w, h, cl, a)
    for i in range(lines):
        ly = -h / 2 + h * 0.18 + i * (h * 0.7 / max(lines, 1))
        line(c, -w / 2 + w * 0.12, ly, w / 2 - w * (0.12 if i % 3 else 0.3), ly, '#9A958C', 3, a)
    c.restore()


def phone(c, x, y, w, h, rot=0.0, body='#151518', screen=None):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    rrect(c, -w / 2 + 6, -h / 2 + 10, w, h, w * 0.14, '#000000', 0.35, blur=10)
    rrect(c, -w / 2, -h / 2, w, h, w * 0.14, body)
    rrect(c, -w / 2 + 12, -h / 2 + 14, w - 24, h - 28, w * 0.1, '#0E1726')
    if screen:
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(R(-w / 2 + 12, -h / 2 + 14, w - 24, h - 28), w * 0.1, w * 0.1), True)
        screen(c, -w / 2 + 12, -h / 2 + 14, w - 24, h - 28)
        c.restore()
    c.restore()


def wrench(c, x, y, s=1.0, rot=0.0, cl='#9AA3AD'):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    rrect(c, -6, 0, 12, 90, 5, cl)
    c.drawPath(_wrench_head(), P(cl))
    c.restore()


def _wrench_head():
    p = skia.Path()
    p.moveTo(-16, 4)
    p.lineTo(-16, -18)
    p.lineTo(-6, -26)
    p.lineTo(-6, -10)
    p.lineTo(6, -10)
    p.lineTo(6, -26)
    p.lineTo(16, -18)
    p.lineTo(16, 4)
    p.close()
    return p


# ---------------- environment ----------------
def floor_planks(c, y0, y1, c1, c2, n=7):
    grect(c, 0, y0, W, y1 - y0, [c1, c2])
    for i in range(1, n):
        yy = y0 + (y1 - y0) * (i / n) ** 1.4
        line(c, 0, yy, W, yy, dk(c1, 0.8), 2, 0.5)


def window(c, x, y, w, h, frame='#3B2F28', sky=('#9FB6C9', '#D9E1E6'), inner=None, panes=True, a=1.0):
    rect(c, x - 14, y - 14, w + 28, h + 28, frame)
    grect(c, x, y, w, h, list(sky))
    if inner:
        c.save()
        c.clipRect(R(x, y, w, h))
        inner(c, x, y, w, h)
        c.restore()
    if panes:
        rect(c, x + w / 2 - 6, y, 12, h, frame)
        rect(c, x, y + h / 2 - 6, w, 12, frame)
    rect(c, x - 22, y + h + 10, w + 44, 16, lt(frame, 0.15))


def frame_pic(c, x, y, w, h, fcol='#C9A25A', inner='#6F7F8C', fig=True):
    rect(c, x + 4, y + 8, w, h, '#000000', 0.3, blur=6)
    rect(c, x, y, w, h, fcol)
    rect(c, x + 10, y + 10, w - 20, h - 20, inner)
    if fig:
        for i, cx in enumerate((x + w * 0.35, x + w * 0.65)):
            circ(c, cx, y + h * 0.45, w * 0.07, '#E8C7A6')
            rect(c, cx - w * 0.08, y + h * 0.53, w * 0.16, h * 0.32, ['#3D4F66', '#8C4A4A'][i])


def lamp(c, x, y, on=1.0, shade='#D8C7A0'):
    line(c, x, y, x, y - 300, '#2A2420', 8)
    oval(c, x, y, 50, 12, '#2A2420')
    poly(c, [(x - 60, y - 300), (x + 60, y - 300), (x + 40, y - 390), (x - 40, y - 390)], shade)
    if on:
        glow(c, x, y - 330, 300, '#FFD9A0', 0.35 * on)


def couch(c, x, y, w, cl, part='all'):
    if part in ('all', 'back'):
        rrect(c, x - w / 2, y - 250, w, 170, 30, dk(cl, 0.85))
        for i in range(2):
            rrect(c, x - w / 2 + 70 + i * (w - 140) / 2 + 6, y - 232, (w - 140) / 2 - 12, 100, 20, lt(cl, 0.08))
    if part in ('all', 'front'):
        rrect(c, x - w / 2 + 40, y - 130, w - 80, 70, 16, cl)
        rrect(c, x - w / 2, y - 170, 70, 160, 24, dk(cl, 0.92))
        rrect(c, x + w / 2 - 70, y - 170, 70, 160, 24, dk(cl, 0.92))
        rrect(c, x - w / 2 + 20, y - 70, w - 40, 60, 12, dk(cl, 0.75))


def ctable(c, x, y, w, cl='#4A3426'):
    rect(c, x - w / 2 + 20, y + 10, 16, 90, dk(cl, 0.8))
    rect(c, x + w / 2 - 36, y + 10, 16, 90, dk(cl, 0.8))
    rrect(c, x - w / 2, y - 18, w, 30, 6, cl)
    rect(c, x - w / 2, y - 18, w, 6, lt(cl, 0.15))


def house(c, x, y, w, h, wall='#8C9AA6', roof='#4B3B3B', door='#6E2A2A', lit=0.0, door_open=0.0):
    rect(c, x, y - h, w, h, wall)
    for i in range(1, 9):
        line(c, x, y - h + i * h / 9, x + w, y - h + i * h / 9, dk(wall, 0.9), 2, 0.6)
    poly(c, [(x - 30, y - h), (x + w / 2, y - h - h * 0.5), (x + w + 30, y - h)], roof)
    dw, dh = w * 0.2, h * 0.42
    dx = x + w / 2 - dw / 2
    rect(c, dx - 8, y - dh - 8, dw + 16, dh + 8, dk(wall, 0.7))
    rect(c, dx, y - dh, dw, dh, '#141210')
    if door_open < 1:
        rect(c, dx, y - dh, dw * (1 - door_open), dh, door)
        circ(c, dx + dw * (1 - door_open) - 14, y - dh * 0.5, 5, '#D6B04C')
    for wx in (x + w * 0.12, x + w * 0.66):
        for wy in (y - h * 0.86, y - h * 0.42):
            wcol = mix('#2B3A47', '#F2C66D', lit)
            rect(c, wx - 6, wy - 6, w * 0.22 + 12, h * 0.24 + 12, '#EDEDED')
            rect(c, wx, wy, w * 0.22, h * 0.24, wcol)
            line(c, wx + w * 0.11, wy, wx + w * 0.11, wy + h * 0.24, '#EDEDED', 5)
    return dx, dw


def tree(c, x, y, s=1.0, cl='#3D5A3D'):
    rect(c, x - 12 * s, y - 160 * s, 24 * s, 160 * s, '#4A3728')
    for dx, dy, r in ((0, -260, 95), (-60, -200, 75), (60, -200, 75), (0, -180, 80)):
        circ(c, x + dx * s, y + dy * s, r * s, cl)
    circ(c, x - 25 * s, y - 285 * s, 45 * s, lt(cl, 0.12), 0.6)


def car(c, x, y, s=1.0, cl='#7A8C99', faces=0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    rrect(c, -170, -90, 340, 70, 22, cl)
    poly(c, [(-110, -90), (-70, -150), (80, -150), (120, -90)], cl)
    poly(c, [(-95, -92), (-62, -138), (0, -138), (0, -92)], '#BFD3E0')
    poly(c, [(10, -92), (10, -138), (72, -138), (102, -92)], '#BFD3E0')
    for fx in range(faces):
        circ(c, -40 + fx * 70, -112, 14, '#E2AE88')
    for wx in (-100, 100):
        circ(c, wx, -20, 30, '#1B1B1E')
        circ(c, wx, -20, 13, '#8D9399')
    rect(c, 150, -76, 18, 12, '#F2D28A')
    c.restore()


def sparkle(c, x, y, r, cl='#FFFFFF', a=1.0):
    p = skia.Path()
    p.moveTo(x, y - r)
    p.quadTo(x, y, x + r, y)
    p.quadTo(x, y, x, y + r)
    p.quadTo(x, y, x - r, y)
    p.quadTo(x, y, x, y - r)
    c.drawPath(p, P(cl, a))


def fog(c, y, h, a=0.5, cl='#E6E9EC', t=0.0, drift=0.0):
    sh = lgrad(0, y, 0, y + h, [(cl, 0), (cl, a), (cl, 0)], [0, 0.5, 1])
    c.save()
    c.translate(drift * t, 0)
    c.drawRect(R(-700, y, W + 1400, h), P('#ffffff', shader=sh))
    c.restore()


# ---------------- rendering ----------------
def scene_spans(tl):
    lines = tl['lines']
    spans = []
    for i, ln in enumerate(lines):
        if not spans or spans[-1]['scene'] != ln['scene']:
            st = 0.0 if i == 0 else (lines[i - 1]['end'] + ln['start']) / 2
            spans.append({'scene': ln['scene'], 'start': st, 'lines': []})
        spans[-1]['lines'].append(ln)
    for k, sp in enumerate(spans):
        sp['end'] = spans[k + 1]['start'] if k + 1 < len(spans) else tl['duration']
    return spans


def active_line(lines, t):
    cur = None
    for ln in lines:
        if ln['start'] - 0.05 <= t:
            cur = ln
    return cur


class Ctx:
    def __init__(self, sp):
        self.T = [ln['start'] - sp['start'] for ln in sp['lines']]
        self.E = [ln['end'] - sp['start'] for ln in sp['lines']]
        self.dur = sp['end'] - sp['start']


def draw_frame(c, scenes, sp, tl, t):
    lt_ = t - sp['start']
    ctx = Ctx(sp)
    sc = scenes[sp['scene']]
    c.clear(col('#000000'))
    c.save()
    cam = sc.get('cam', (1.0, 1.07, 540, 960))
    if callable(cam):
        cv = cam(lt_, ctx)
        z, fx, fy = cv[:3]
        sx, sy = (cv[3], cv[4]) if len(cv) > 3 else (fx, fy)
    else:
        z0, z1, fx, fy = cam
        z = z0 + (z1 - z0) * ease(lt_ / max(ctx.dur, 0.1))
        sx, sy = fx, fy
    c.translate(sx, sy)
    c.scale(z, z)
    c.translate(-fx, -fy)
    sc['draw'](c, lt_, ctx)
    c.restore()
    vignette(c, sc.get('vig', VIGNETTE))
    ln = active_line(tl['lines'], t)
    if ln is not None:
        cy = sc.get('cap_y', 800)
        if callable(cy):
            cy = cy(lt_, ctx)
        caption(c, ln['text'], cy, t - ln['start'] + 0.05)
    ha = 1.0 - ramp(t, HOOK_SHOW_UNTIL, HOOK_FADE)
    hook_card(c, tl['hook'][0], tl['hook'][1], ha)
    if sp['start'] > 0 and lt_ < SCENE_FADE_IN:
        rect(c, 0, 0, W, H, '#000000', 1 - ease(lt_ / SCENE_FADE_IN))
    tail = tl['duration'] - t
    if tail < END_FADE:
        rect(c, 0, 0, W, H, '#000000', 1 - clamp(tail / END_FADE))


def render(tl, scenes, outdir, only=None, frames_at=None, log=print):
    """tl: timeline dict (duration, hook, lines with scene/text/start/end). scenes: {name: dict(draw, cam, cap_y, vig)}.
    frames_at=[t, ...] returns RGB arrays instead of encoding. Otherwise writes outdir/sNN.mp4 per scene and list.txt;
    only=[k, ...] re-renders just those scenes when the others exist."""
    spans = scene_spans(tl)
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    if frames_at is not None:
        outs = []
        for t in frames_at:
            sp = [s for s in spans if s['start'] <= t < s['end']][0]
            draw_frame(c, scenes, sp, tl, t)
            outs.append(arr[:, :, :3].copy())
        return outs
    os.makedirs(outdir, exist_ok=True)
    files = []
    for k, sp in enumerate(spans):
        f0, f1 = int(round(sp['start'] * FPS)), int(round(sp['end'] * FPS))
        fn = f'{outdir}/s{k:02d}.mp4'
        files.append(fn)
        if only is not None and k not in only and os.path.exists(fn):
            continue
        tmp = f'{outdir}/s{k:02d}.tmp.mp4'
        cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-'] + X264 + [tmp]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(f0, f1):
            draw_frame(c, scenes, sp, tl, f / FPS)
            pr.stdin.write(arr.tobytes())
        pr.stdin.close()
        if pr.wait() == 0:
            os.replace(tmp, fn)
        log(f'scene {k:2d} {sp["scene"]:10s} {f1 - f0} frames')
    with open(f'{outdir}/list.txt', 'w') as fh:
        for fn in files:
            fh.write(f"file '{os.path.basename(fn)}'\n")
    return files


def concat_and_mux(outdir, audio, out_mp4):
    """Joins the scene files with -c copy, then adds the soundtrack (AAC 192k) without re-encoding the video."""
    video = os.path.join(outdir, 'video.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(outdir, 'list.txt'), '-c', 'copy', video], check=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out_mp4], check=True)
    return out_mp4


def contact_sheet(tl, scenes, path, cols=4, thumb=(180, 320), when='mid', title=None):
    """One frame per scene (its middle, or 0.6 s after its last line starts with when='late') as a PNG grid.
    title: optional list of lines (first one big) drawn in the empty cells of the last row."""
    from PIL import Image, ImageDraw, ImageFont
    spans = scene_spans(tl)
    ts = [(s['start'] + s['end']) / 2 if when == 'mid' else min(s['lines'][-1]['start'] + 0.6, s['end'] - 0.05) for s in spans]
    frames = render(tl, scenes, None, frames_at=ts)
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * thumb[0], rows * thumb[1]), '#14161C')
    for i, f in enumerate(frames):
        sheet.paste(Image.fromarray(f).resize(thumb, Image.LANCZOS), ((i % cols) * thumb[0], (i // cols) * thumb[1]))
    free = (cols - len(frames) % cols) % cols
    if title and free:
        d = ImageDraw.Draw(sheet)
        x0, y = (len(frames) % cols) * thumb[0] + 28, (rows - 1) * thumb[1] + 36
        for k, ln in enumerate(title):
            size = 34 if k == 0 else 19
            fnt = ImageFont.truetype(_font_path(FONT_FILES['bold' if k == 0 else 'reg']), size)
            d.text((x0, y), ln, font=fnt, fill='#F4C542' if k == 0 else '#E8EEF0')
            y += size + (22 if k == 0 else 12)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sheet.save(path, optimize=True)
    return path


def _preview(path):
    """parts sheet: hook card, caption, the ten expressions, five looks from the episodes, and the props"""
    from PIL import Image
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    grect(c, 0, 0, W, H, ['#2B2F3A', '#14161C'])
    glow(c, 540, 1300, 800, '#FFD9A0', 0.12)
    rect(c, 0, 1690, W, 230, '#3A3F4B')
    face = dict(skin=SKIN['light'], hair='short', hair_col='#3A2A20', top='#4E6E5A')
    exprs = ['neutral', 'smile', 'grin', 'worried', 'sad', 'angry', 'shock', 'stare', 'sinister', 'sleep']
    for i, ex in enumerate(exprs):
        cx, cy = 140 + (i % 5) * 200, 800 + (i // 5) * 250
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(R(cx - 90, cy - 105, 180, 190), 22, 22))
        rect(c, cx - 90, cy - 105, 180, 190, '#3A3F4B')
        person(c, cx, cy + 452 * 1.5, 1.5, face, expr=ex, arms=(6, 6), blink=False)
        c.restore()
        text(c, ex, cx, cy + 122, 24, '#C9CED6', tf='reg')
    looks = [
        (dict(skin=SKIN['light'], hair='bald', hair_col='#9A938C', top='#55697A', collar='#E8E6E1', apron='#6B4A2F', pants='#3A3A42', glasses=True, mustache='#8E8780'), 'smile'),
        (dict(skin=SKIN['mid'], hair='long', hair_col='#5A3A26', top='#7A4E6E', pants='#2F3340'), 'worried'),
        (dict(skin=SKIN['tan'], hair='beanie', hair_col='#3A2A20', beanie='#5B4A3A', beard=True, beard_col='#3A2A20', top='#5A5A3A', patch='#6E6A4E', pants='#3E3A34', shoe='#2B2621'), 'stare'),
        (dict(skin=SKIN['light'], hair='side', hair_col='#CFCBC6', top='#22262E', tie='#7A1E2A', shirt='#F2F2F2', pants='#22262E'), 'sinister'),
        (dict(skin=SKIN['light'], hair='long', hair_col='#C9A15A', top='#6E2E3E', dress=True, necklace='#E8D18A'), 'angry'),
    ]
    for i, (L, ex) in enumerate(looks):
        person(c, 130 + i * 205, 1680, 0.78, L, expr=ex, arms=(6, 6), t=0.5, seed=i, look=0.3 * (i - 2) / 2)
    key(c, 250, 1800, 1.4, -10)
    mug(c, 420, 1790, 1.2, '#B03A2E')
    phone(c, 580, 1795, 80, 150, screen=lambda c, x, y, w, h: (grect(c, x, y, w, h, ['#3A6EA5', '#1E3A5F']), text(c, '10M', x + w / 2, y + h / 2 + 8, 22, '#ffffff')))
    paper(c, 740, 1795, 110, 140, 6)
    wrench(c, 900, 1765, 1.0, 30)
    hook_card(c, 'He kept a copy of every key he ever made...', 'then someone got into HIS house', 1.0)
    caption(c, 'he cut twice.', 560, 1.0)
    vignette(c, 0.35)
    Image.fromarray(arr[:, :, :3].copy()).resize((720, 1280), Image.LANCZOS).save(path, optimize=True)
    print('wrote', path)


if __name__ == '__main__':
    _preview(os.path.join(HERE, 'preview.png'))
