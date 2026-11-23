"""layout: the 1080x1920 POWER BALLS screen (board).

Purple radial background, title + subtitle header (and the winner header pop), the white-framed grid
arena, and the caption line under the arena. Overlays and the arena contents draw in arena-local
coordinates (0..ARENA_SIZE) between begin_arena()/begin_overlay() and canvas.restore().

    python layout.py --preview preview.png
"""
import math
import sys
from pathlib import Path

import skia

import drawkit as dk

# ---------------------------------------------------------------- settings
W, H = 1080, 1920
BG_CENTER, BG_RADIUS = (540, 880), 1150
BG_STOPS = [('#261A3E', 0.0), ('#1A112D', 0.55), ('#130D22', 1.0)]

TITLE = 'POWER BALLS'
SUBTITLE = 'Every hit UPGRADES your power'
WIN_TITLE = 'WE HAVE A WINNER!'
TITLE_Y, SUBTITLE_Y = 150, 214
TITLE_STYLE = dict(weight='Black', size=88, color='#FED64D', outline=12, shadow=5)
SUBTITLE_STYLE = dict(weight='ExtraBold', size=33, color='#EAE4FF', outline=8)
WIN_TITLE_STYLE = dict(weight='Black', size=74, color='#FED64D', outline=12, shadow=5, max_w=900,
                       pop_from=0.6, pop_time=0.35)

ARENA_X, ARENA_Y, ARENA_SIZE = 104.0, 474.0, 872.0   # inner (playable) square
FRAME_PAD, FRAME_RADIUS = 20, 30                      # white frame around it
FRAME_COLOR, FRAME_ALERT = '#FFFFFF', '#FF3B4E'      # alert = FINAL BLOW red
ARENA_BG = '#0D0D17'
GRID = dict(start=76, step=80, color='#AFAFBE', alpha=120, width=1.6)

CAPTION_Y = 1435
CAPTION = 'Comment your fighter!'
DUEL_CAPTION = 'FINAL DUEL!'
END_CAPTION = 'Did your fighter win? Comment!'
CAPTION_STYLE = dict(weight='ExtraBold', size=42, color='#FFFFFF', outline=9)
DUEL_STYLE = dict(weight='Black', size=46, color='#FED64D', outline=10, pulse=0.05, pulse_hz=6)

_CACHE = {}


def configure(**kw):
    g = globals()
    for k, v in kw.items():
        if k not in g:
            raise KeyError(k)
        g[k] = v
    _CACHE.clear()


# ---------------------------------------------------------------- static images
def background():
    if 'bg' not in _CACHE:
        surf = dk.new_surface(W, H)
        c = surf.getCanvas()
        sh = skia.GradientShader.MakeRadial(BG_CENTER, BG_RADIUS, [dk.C(col) for col, _ in BG_STOPS],
                                           [pos for _, pos in BG_STOPS])
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))
        _CACHE['bg'] = surf.makeImageSnapshot()
    return _CACHE['bg']


def arena_image():
    if 'arena' not in _CACHE:
        n = int(ARENA_SIZE)
        surf = dk.new_surface(n, n)
        c = surf.getCanvas()
        c.clear(dk.C(ARENA_BG))
        p = dk.stroke(GRID['color'], GRID['width'], GRID['alpha'], cap=skia.Paint.kButt_Cap)
        for k in range(11):
            v = GRID['start'] + GRID['step'] * k
            if v < ARENA_SIZE:
                c.drawLine(v, 0, v, ARENA_SIZE, p)
                c.drawLine(0, v, ARENA_SIZE, v, p)
        _CACHE['arena'] = surf.makeImageSnapshot()
    return _CACHE['arena']


# ---------------------------------------------------------------- drawing
def draw_background(c):
    c.drawImage(background(), 0, 0)


def draw_header(c, title=None, subtitle=None):
    t, s = TITLE_STYLE, SUBTITLE_STYLE
    dk.text(c, title or TITLE, W / 2, TITLE_Y, t['size'], t['weight'], t['color'], outline=dk.DARK, ow=t['outline'],
            shadow=t['shadow'])
    dk.text(c, subtitle or SUBTITLE, W / 2, SUBTITLE_Y, s['size'], s['weight'], s['color'], outline=dk.DARK,
            ow=s['outline'], caps=False)


def draw_win_header(c, age, title=None):
    t = WIN_TITLE_STYLE
    sc = t['pop_from'] + (1 - t['pop_from']) * dk.ease_out_back(age / t['pop_time'])
    c.save()
    c.translate(W / 2, TITLE_Y)
    c.scale(sc, sc)
    dk.text(c, title or WIN_TITLE, 0, 0, t['size'], t['weight'], t['color'], outline=dk.DARK, ow=t['outline'],
            shadow=t['shadow'], max_w=t['max_w'])
    c.restore()


def draw_arena_frame(c, ox=0.0, oy=0.0, alert=0.0):
    col = dk.mix(FRAME_COLOR, FRAME_ALERT, alert)
    x0, y0 = ARENA_X - FRAME_PAD, ARENA_Y - FRAME_PAD
    x1, y1 = ARENA_X + ARENA_SIZE + FRAME_PAD, ARENA_Y + ARENA_SIZE + FRAME_PAD
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x0 + ox, y0 + oy, x1 + ox, y1 + oy), FRAME_RADIUS, FRAME_RADIUS),
                dk.fill(col))


def begin_arena(c, ox=0.0, oy=0.0, zoom=1.0, focus=None):
    """save + clip to the arena, switch to arena coords (zoomed on focus), draw the grid. Caller restores."""
    c.save()
    c.clipRect(skia.Rect(ARENA_X + ox, ARENA_Y + oy, ARENA_X + ARENA_SIZE + ox, ARENA_Y + ARENA_SIZE + oy))
    c.translate(ARENA_X + ox, ARENA_Y + oy)
    if zoom != 1.0:
        fx, fy = focus or (ARENA_SIZE / 2, ARENA_SIZE / 2)
        c.translate(ARENA_SIZE / 2, ARENA_SIZE / 2)
        c.scale(zoom, zoom)
        c.translate(-fx, -fy)
    c.drawImage(arena_image(), 0, 0)


def begin_overlay(c, ox=0.0, oy=0.0):
    """save + clip to the arena in unzoomed arena coords (for banners/panels). Caller restores."""
    c.save()
    c.clipRect(skia.Rect(ARENA_X + ox, ARENA_Y + oy, ARENA_X + ARENA_SIZE + ox, ARENA_Y + ARENA_SIZE + oy))
    c.translate(ARENA_X + ox, ARENA_Y + oy)


def draw_caption(c, kind='normal', tau=0.0, text=None):
    """kind: 'normal' (Comment your fighter!), 'duel' (pulsing FINAL DUEL!) or 'end'."""
    if kind == 'duel':
        s = DUEL_STYLE
        pulse = 1.0 + s['pulse'] * math.sin(tau * s['pulse_hz'])
        c.save()
        c.translate(W / 2, CAPTION_Y)
        c.scale(pulse, pulse)
        dk.text(c, text or DUEL_CAPTION, 0, 0, s['size'], s['weight'], s['color'], outline=dk.DARK, ow=s['outline'])
        c.restore()
    else:
        s = CAPTION_STYLE
        msg = text or (END_CAPTION if kind == 'end' else CAPTION)
        dk.text(c, msg, W / 2, CAPTION_Y, s['size'], s['weight'], s['color'], outline=dk.DARK, ow=s['outline'],
                caps=False)


def style():
    return {
        'canvas': {'width': W, 'height': H},
        'background': {'type': 'radial', 'center': list(BG_CENTER), 'radius': BG_RADIUS,
                       'stops': [{'color': col, 'pos': pos} for col, pos in BG_STOPS]},
        'title': dict(TITLE_STYLE, text=TITLE, y=TITLE_Y, outline_color=dk.DARK, font='Poppins'),
        'subtitle': dict(SUBTITLE_STYLE, text=SUBTITLE, y=SUBTITLE_Y, outline_color=dk.DARK, font='Poppins'),
        'winner_title': dict(WIN_TITLE_STYLE, text=WIN_TITLE, y=TITLE_Y, easing='easeOutBack', font='Poppins'),
        'arena': {'inner': [ARENA_X, ARENA_Y, ARENA_SIZE, ARENA_SIZE], 'background': ARENA_BG,
                  'frame': {'pad': FRAME_PAD, 'radius': FRAME_RADIUS, 'color': FRAME_COLOR,
                            'final_blow_color': FRAME_ALERT},
                  'grid': GRID},
        'caption': dict(CAPTION_STYLE, y=CAPTION_Y, texts={'normal': CAPTION, 'end': END_CAPTION},
                        outline_color=dk.DARK, font='Poppins'),
        'duel_caption': dict(DUEL_STYLE, y=CAPTION_Y, text=DUEL_CAPTION, outline_color=dk.DARK, font='Poppins'),
    }


def preview(path):
    surf = dk.new_surface(W, H)
    c = surf.getCanvas()
    draw_background(c)
    draw_header(c)
    draw_arena_frame(c)
    begin_arena(c)
    c.restore()
    draw_caption(c, 'normal')
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
