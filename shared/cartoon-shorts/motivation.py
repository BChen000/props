"""motivation: the engine behind every Short in cartoon-shorts (1080x1920, 30 fps): voices, captions, sound, sets.

An episode (episodes/<name>.py) gives NAME, SCRIPT, SCENES, SCORE, THUMB_T and optionally SFX(tl, spans, rng), THUMB_CROP
and CAPTIONS.
  SCRIPT lines: dict(scene, text, v='nar' | 'sha' | 'old' | 'story' | None, style=..., key=[...], pre=, gap=, dur=,
                pos=(x, y), size=)
    v='nar'    the narrator: captions two or three words at a time ('|' in text sets the breaks), key words highlighted
    v='story'  the storyteller of the five cartoon looks: brighter and quicker, same captions
    v='old'    an old man (FUTURE YOU.), captioned like the narrator
    v='sha'    the shadow (the narrator pitched down): red handwriting written on at pos
    v=None     a silent beat lasting dur: style 'title' (DAY 1), 'no' (his answer), 'word' (end card), 'cap' or 'none'
  CAPTIONS: gold (default: white with gold key words), punch (one slanted comic word at a time), outline (white with a
            black edge) or karaoke (the whole line in capitals, words lighting up as they are spoken)
  SCENES: {name: dict(draw(c, t, x), cam, cap_y, vig, day=N or f(t, x) -> label, day_pos, overlay=f(c, t, x))}
    draw gets t (seconds into the scene) and x (x.T / x.E: its lines' start / end times, x.dur)
    cam is (zoom from, zoom to, focus x, focus y) or f(t, x) -> (zoom, fx, fy[, screen x, screen y])
  SCORE: the motivational score (dark piano, a riser into the beat at the 'title' scene, an end chord) or
         dict(kind='bed', ...) for a looping bed from the first frame (music_bed)
  build(episode) -> build/<name>/<name>.mp4, mix.wav, timeline.json, thumb.png   (CLI: python make_short.py <episode>)
Sets shared by episodes are below; the lit and stick people are in humanoid.py, the five cartoon looks in cast.py.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
KIDS = os.path.join(HERE, '..', '..', 'kids-songs')
for _p in ('storytime-kit', 'storytime-narrator', 'storytime-music'):
    sys.path.insert(0, os.path.join(KIDS, _p))
sys.path.insert(0, HERE)
import skia  # noqa: E402
import storytime_kit as kit  # noqa: E402
import narrate  # noqa: E402
import music  # noqa: E402
from storytime_kit import (W, H, P, R, rect, rrect, circ, oval, line, path, poly, grect, glow, text, tw, wrap,  # noqa: E402
                           ease, eout, ramp, clamp, mix, lgrad, rgrad)
from blob import grain  # noqa: E402
from settings import (VIGNETTE, SCENE_FADE_IN, VOICES, LEAD_IN, TAIL, FONTS, CAP, SHA_TEXT, TITLE, DAY, DUST,  # noqa: E402
                      NIGHT, WARM, DUSK, DAWN, GREY, CAP_LOOKS, HUD)
import humanoid as hu  # noqa: E402

SR = music.SR

for _k, _fn in FONTS.items():
    _fp = os.path.join(HERE, 'fonts', _fn)
    if not os.path.exists(_fp):
        raise SystemExit(f'{_fn} is missing: run python get_fonts.py')
    kit.TF[_k] = skia.Typeface.MakeFromFile(_fp)

kit.SCENE_FADE_IN = SCENE_FADE_IN
LINES = {}
VOICE_CACHE = os.environ.get('VOICE_CACHE', os.path.join(HERE, 'build', 'voice-cache'))   # spoken lines, shared
OUT_TAG = ['']           # make_short.py --style stick -> build/<name>_stick/
TEXT_ON = [True]          # thumbnail() turns captions and counters off
CAP_LOOK = ['gold']       # the episode's CAPTIONS: gold, punch, outline or karaoke (settings.CAP_LOOKS)
SPOKEN_STYLES = ('nar', 'old', 'story')


# ---------------------------------------------------------------- text
def spaced(c, s, x, y, size, cl, a=1.0, tf='pop', sp=0.0, blur=0):
    """s centred on x with extra letter spacing sp; y is the baseline."""
    f = kit.font(tf, size)
    ws = [f.measureText(ch) for ch in s]
    xx = x - (sum(ws) + sp * (len(s) - 1)) / 2
    pt = P(cl, a, blur=blur)
    for ch, w in zip(s, ws):
        c.drawString(ch, xx, y, f, pt)
        xx += w + sp


def glow_text(c, s, x, y, size, a=1.0, cl='#FFFFFF', glow_a=None, sp=0.0):
    """Bold white text with a wide soft glow, like light bleeding off it. y is the text's middle."""
    if a <= 0:
        return
    by = y + size * 0.36
    g = TITLE['glow'] if glow_a is None else glow_a
    spaced(c, s, x, by, size, cl, g * a, 'pop', sp, blur=size * 0.18)
    spaced(c, s, x, by + size * 0.05, size, '#000000', 0.3 * a, 'pop', sp, blur=size * 0.06)
    spaced(c, s, x, by, size, cl, a, 'pop', sp)


def _norm(w):
    return ''.join(ch for ch in w.lower() if ch.isalnum() or ch == "'")


def chunks(raw, dur):
    """Splits a narration line into caption chunks with start times (seconds into the line): at '|' marks, or else
    every CAP['words'] words and after punctuation. Times follow the letters, plus a pause after punctuation."""
    if '|' in raw:
        parts = [p.strip() for p in raw.split('|') if p.strip()]
    else:
        parts, cur = [], []
        for w in raw.split():
            cur.append(w)
            if len(cur) >= CAP['words'] or w[-1] in ',.!?':
                parts.append(' '.join(cur))
                cur = []
        if cur:
            parts.append(' '.join(cur))
    wts = []
    for i, p in enumerate(parts):
        wt = sum(ch.isalnum() for ch in p) + 2.0 * len(p.split())
        if i < len(parts) - 1 and p[-1] in ',.!?':
            wt += 4.0
        wts.append(wt)
    tot, acc, out = sum(wts), 0.0, []
    for p, wt in zip(parts, wts):
        out.append((dur * acc / tot, p))
        acc += wt
    return out


def chunk_text(c, s, x, y, age, out, keys, size):
    words = s.split()
    f = kit.font('pop', size)
    gap = size * 0.26
    ws = [f.measureText(w) for w in words]
    total = sum(ws) + gap * (len(words) - 1)
    k = min(1.0, 980 / total)
    a = clamp(age / 0.05) * clamp(out)
    if a <= 0:
        return
    sc = k * (0.84 + 0.16 * eout(age / CAP['pop']))
    c.save()
    c.translate(x, y - 6 * (1 - eout(age / 0.2)))
    c.scale(sc, sc)
    xx, by = -total / 2, size * 0.36
    for w, ww in zip(words, ws):
        cl = CAP['key'] if _norm(w) in keys else CAP['white']
        c.drawString(w, xx + 3, by + 7, f, P('#000000', 0.6 * a, blur=10))
        c.drawString(w, xx, by, f, P(cl, a))
        xx += ww + gap
    c.restore()


def sha_text(c, s, x, y, age, out, size, dur, seed=0):
    """The shadow's words: red handwriting written on left to right, with a red glow and a faint tremble."""
    a = clamp(age / 0.05) * clamp(out)
    if a <= 0:
        return
    ls = wrap(s, size, 880, 'brush')
    lh = size * 1.02
    lens = [tw(ln, size, 'brush') for ln in ls]
    u = clamp(age / min(SHA_TEXT['write'], 0.5 * dur)) * sum(lens)
    k = int(age * 12)
    jx = (math.sin(k * 12.9898 + seed) * 43758.5453) % 1.0 - 0.5
    jy = (math.sin(k * 78.233 + seed) * 24634.6345) % 1.0 - 0.5
    c.save()
    c.translate(x + 2.4 * jx, y + 2.4 * jy)
    c.rotate(-3)
    y0 = -(len(ls) - 1) * lh / 2 + size * 0.3
    for i, (ln, ln_w) in enumerate(zip(ls, lens)):
        vis = clamp(u - sum(lens[:i]), 0.0, ln_w)
        if vis <= 0:
            break
        x0, yy = -ln_w / 2, y0 + i * lh
        c.save()
        c.clipRect(R(x0 - 20, yy - size * 1.2, vis + 30, size * 1.8))
        text(c, ln, 3, yy + 6, size, '#000000', 0.55 * a, tf='brush', blur=8)
        text(c, ln, 0, yy, size, SHA_TEXT['glow'], 0.55 * a, tf='brush', blur=16)
        text(c, ln, 0, yy, size, SHA_TEXT['color'], a, tf='brush')
        c.restore()
    c.restore()


def word_times(cs, d):
    """(t, word) for every word of a line: each caption chunk's time shared out by its letters."""
    out = []
    for i, (t0, txt) in enumerate(cs):
        t1 = cs[i + 1][0] if i + 1 < len(cs) else d
        ws = txt.split()
        wts = [sum(ch.isalnum() for ch in w) + 1.5 for w in ws]
        acc = 0.0
        for w, wt in zip(ws, wts):
            out.append((t0 + (t1 - t0) * acc / sum(wts), w))
            acc += wt
    return out


def _edge_text(c, s, x, y, f, fill, edge, ew, a, shadow=0.45):
    """s from (x, y) on the baseline, with a round-joined edge ew wide and a soft drop shadow."""
    if shadow:
        c.drawString(s, x + ew * 0.2, y + ew * 0.5, f, P('#000000', shadow * a, blur=ew * 0.7))
    if ew:
        c.drawString(s, x, y, f, P(edge, a, sw=ew))
    c.drawString(s, x, y, f, P(fill, a))


def punch_text(c, w, x, y, age, out, key):
    """One word, big, slanted and edged, popping in (the what-if look)."""
    S = CAP_LOOKS['punch']
    a = clamp(age / 0.03) * clamp(out)
    if a <= 0:
        return
    s = w.upper()
    f = kit.font('punch', S['size'])
    ww = f.measureText(s)
    k = min(1.0, 960 / max(ww, 1))
    sc = k * (1.0 + 0.22 * (1 - eout(age / S['pop'])))
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    c.skew(S['skew'], 0)
    _edge_text(c, s, -ww / 2, S['size'] * 0.36, f, S['key'] if key else S['fill'], S['edge'], S['edge_w'], a, 0.55)
    c.restore()


def outline_text(c, s, x, y, age, out, keys, size=None):
    """A chunk of words in white with a black edge, key words in yellow (the palace, castle and pill looks)."""
    S = CAP_LOOKS['outline']
    size = size or S['size']
    a = clamp(age / 0.03) * clamp(out)
    if a <= 0:
        return
    words = s.split()
    f = kit.font('pop', size)
    gap = size * 0.24
    ws = [f.measureText(w) for w in words]
    total = sum(ws) + gap * (len(words) - 1)
    k = min(1.0, 960 / max(total, 1))
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    xx = -total / 2
    for w, wd in zip(words, ws):
        _edge_text(c, w, xx, size * 0.36, f, S['key'] if _norm(w) in keys else S['fill'], S['edge'], S['edge_w'], a, 0.35)
        xx += wd + gap
    c.restore()


def karaoke_text(c, raw, x, y, tt, out, wt):
    """The whole line in capitals, on up to three lines; words already spoken are white, the rest dim (desert look)."""
    S = CAP_LOOKS['karaoke']
    a = clamp((tt + 0.05) / 0.08) * clamp(out)
    if a <= 0:
        return
    words = plain(raw).upper().split()
    lit = sum(1 for t0, _ in wt if t0 <= tt + 0.02)
    f = kit.font('pop', S['size'])
    sp = S['spacing']

    def width(ws):
        return sum(f.measureText(w) + sp * len(w) for w in ws) + f.measureText(' ') * (len(ws) - 1)

    rows, cur = [], []
    for w in words:
        if cur and width(cur + [w]) > S['width']:
            rows.append(cur)
            cur = []
        cur.append(w)
    rows.append(cur)
    lh = S['size'] * S['lead']
    y0 = y - (len(rows) - 1) * lh / 2 + S['size'] * 0.36
    k = 0
    for r, row in enumerate(rows):
        xx = x - width(row) / 2
        for w in row:
            on = k < lit
            pt = P('#FFFFFF', (1.0 if on else S['dim']) * a)
            sh = P('#000000', 0.4 * a * (1.0 if on else 0.5), blur=6)
            for ch in w:
                c.drawString(ch, xx + 2, y0 + r * lh + 4, f, sh)
                c.drawString(ch, xx, y0 + r * lh, f, pt)
                xx += f.measureText(ch) + sp
            xx += f.measureText(' ')
            k += 1


def _caption(c, s, cy, age):
    ln = LINES.get(s)
    if ln is None:
        return
    d = ln['end'] - ln['start']
    x, y = ln.get('pos') or (540, cy)
    st = ln['style']
    look = CAP_LOOK[0]
    if st in SPOKEN_STYLES and look in ('punch', 'karaoke'):
        tt = age - 0.05
        wt = word_times(ln['chunks'], d)
        if look == 'karaoke':
            karaoke_text(c, ln['text'], x, y if ln.get('pos') else CAP_LOOKS['karaoke']['y'], tt,
                         1 - ramp(tt, d + 0.3, 0.15), wt)
            return
        cur = [w for w in wt if w[0] <= tt + 0.02] or wt[:1]
        t0, w = cur[-1]
        out = 1 - ramp(tt, d + 0.25, 0.12) if len(cur) == len(wt) else 1.0
        punch_text(c, w, x, y if ln.get('pos') else CAP_LOOKS['punch']['y'], tt - t0 + 0.03, out, _norm(w) in ln['key'])
    elif st in SPOKEN_STYLES:
        tt = age - 0.05
        cur = [ch for ch in ln['chunks'] if ch[0] <= tt + 0.03] or ln['chunks'][:1]
        t0, txt = cur[-1]
        out = 1 - ramp(tt, d + CAP['hold'], 0.2) if txt == ln['chunks'][-1][1] else 1.0
        if look == 'outline':
            outline_text(c, txt, x, y if ln.get('pos') else CAP_LOOKS['outline']['y'], tt - t0 + 0.03, out, ln['key'],
                         ln.get('size'))
        else:
            chunk_text(c, txt, x, y, tt - t0 + 0.03, out, ln['key'], ln.get('size', CAP['size']))
    elif st == 'sha':
        sha_text(c, s, x, y, age, 1 - ramp(age, d + 0.45, 0.25), ln.get('size', SHA_TEXT['size']), d, ln['i'])
    elif st == 'title':
        a = clamp(age / 0.08) * (1 - ramp(age, d - 0.18, 0.18))
        sc = 1.0 + 0.16 * (1 - eout(age / 0.35))
        c.save()
        c.translate(x, y)
        c.scale(sc, sc)
        glow_text(c, s, 0, 0, ln.get('size', TITLE['size']), a, sp=ln.get('size', TITLE['size']) * 0.05)
        c.restore()
    elif st == 'no':
        a = clamp(age / 0.05) * (1 - ramp(age, d - 0.15, 0.15))
        sc = 1.0 + 0.35 * (1 - eout(age / 0.22))
        c.save()
        c.translate(x, y)
        c.scale(sc, sc)
        glow_text(c, s, 0, 0, ln.get('size', 170), a)
        c.restore()
    elif st == 'cap':
        chunk_text(c, s, x, y, age, 1 - ramp(age, d - 0.12, 0.12), ln['key'], ln.get('size', CAP['size']))
    elif st == 'word':
        a = ease(age / 0.6)
        glow_text(c, s, x, y - 18 * eout(age / 1.2), ln.get('size', 120), a, glow_a=0.6)


kit.caption = _caption


def day_counter(c, label, a, pos=None):
    if a <= 0:
        return
    x, y = pos or (W / 2, DAY['y'])
    spaced(c, label, x, y, DAY['size'], DAY['color'], 0.5 * a, 'pop', DAY['spacing'], blur=16)
    spaced(c, label, x, y, DAY['size'], DAY['color'], a, 'pop', DAY['spacing'])


def hud(c, items, a=1.0, x=None, y=None):
    """Counter boxes in the top-left corner, stacked: items = [(label, value), ...] (the what-if look)."""
    if a <= 0 or not TEXT_ON[0]:
        return
    S = HUD
    x0, y0 = S['x'] if x is None else x, S['y'] if y is None else y
    fl, fv = kit.font('pop', 30), kit.font('pop', 60)
    for k, (label, value) in enumerate(items):
        lw = sum(fl.measureText(ch) + 3 for ch in label)
        w = S['pad'] * 2 + lw + 18 + fv.measureText(str(value))
        yy = y0 + k * (S['h'] + S['gap'])
        rrect(c, x0 + 3, yy + 6, w, S['h'], 22, '#000000', 0.35 * a, blur=8)
        rrect(c, x0, yy, w, S['h'], 22, S['bg'], S['bg_a'] * a)
        rrect(c, x0, yy, w, S['h'], 22, S['edge'], a, sw=3)
        xx = x0 + S['pad']
        for ch in label:
            c.drawString(ch, xx, yy + S['h'] / 2 + 11, fl, P(S['label'], a))
            xx += fl.measureText(ch) + 3
        c.drawString(str(value), xx + 18, yy + S['h'] / 2 + 21, fv, P(S['value'], a))


def bubble(c, x, y, s, a=1.0, size=58, tail=(-60, 90), fill='#FFFFFF', ink='#15151C', tf='pop', maxw=640):
    """A speech bubble centred on (x, y) with its tail pointing to (x + tail[0], y + tail[1])."""
    if a <= 0 or not TEXT_ON[0]:
        return
    ls = wrap(s, size, maxw, tf)
    lh = size * 1.12
    w = max(tw(ln, size, tf) for ln in ls) + size * 1.1
    h = lh * len(ls) + size * 0.7
    sc = 0.7 + 0.3 * eout(clamp(a * 1.6))
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    tx, ty = tail
    q = skia.Path()
    q.moveTo(-size * 0.5 + tx * 0.25, h / 2 - 4)
    q.lineTo(tx, ty)
    q.lineTo(size * 0.35 + tx * 0.25, h / 2 - 4)
    q.close()
    rrect(c, -w / 2 + 6, -h / 2 + 10, w, h, size * 0.5, '#000000', 0.3 * a, blur=10)
    c.drawPath(q, P(ink, a, sw=10))
    rrect(c, -w / 2, -h / 2, w, h, size * 0.5, ink, a, sw=10)
    c.drawPath(q, P(fill, a))
    rrect(c, -w / 2, -h / 2, w, h, size * 0.5, fill, a)
    for i, ln in enumerate(ls):
        text(c, ln, 0, -h / 2 + size * 0.35 + lh * i + size * 0.86, size, ink, a, tf=tf)
    c.restore()


def thought(c, x, y, s, a=1.0, size=54, toward=(0, 160), fill='#FFFFFF', ink='#1B1B1F', maxw=560):
    """A cloud-shaped thought bubble centred on (x, y), with three dots trailing toward (x, y) + toward."""
    if a <= 0 or not TEXT_ON[0]:
        return
    ls = wrap(s, size, maxw, 'pop')
    lh = size * 1.12
    w = max(tw(ln, size, 'pop') for ln in ls) + size * 1.4
    h = lh * len(ls) + size * 1.1
    sc = 0.6 + 0.4 * eout(clamp(a * 1.5))
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    lobes = []
    for k in range(14):
        th = 2 * math.pi * k / 14
        lobes.append((math.cos(th) * w * 0.5, math.sin(th) * h * 0.5, size * (0.62 + 0.12 * ((k * 7) % 3))))
    for lx, ly, r in lobes:
        circ(c, lx, ly, r + 5, ink, a)
    oval(c, 0, 0, w * 0.5 + 5, h * 0.5 + 5, ink, a)
    for lx, ly, r in lobes:
        circ(c, lx, ly, r, fill, a)
    oval(c, 0, 0, w * 0.5, h * 0.5, fill, a)
    for i, f_ in enumerate((0.62, 0.8, 0.94)):
        r = size * (0.32 - 0.08 * i)
        bx, by = toward[0] * f_, toward[1] * f_ + h * 0.2
        circ(c, bx, by, r + 5, ink, a)
        circ(c, bx, by, r, fill, a)
    for i, ln in enumerate(ls):
        text(c, ln, 0, -lh * (len(ls) - 1) / 2 + lh * i + size * 0.36, size, ink, a, tf='pop')
    c.restore()


def _post(c, vig):
    kit.vignette(c, vig, 0.46)
    grain(c)


def draw_frame(c, scenes, sp, tl, t):
    """The kit's frame with two additions: a DAY counter (scene key 'day') and a screen-space overlay ('overlay')."""
    lt_ = t - sp['start']
    ctx = kit.Ctx(sp)
    sc = scenes[sp['scene']]
    c.clear(kit.col('#000000'))
    c.save()
    cam = sc.get('cam', (1.0, 1.05, 540, 960))
    if callable(cam):                       # f(t, x) -> (zoom, fx, fy) or (zoom, fx, fy, sx, sy)
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
    _post(c, sc.get('vig', VIGNETTE))
    if sc.get('overlay'):
        sc['overlay'](c, lt_, ctx)
    if TEXT_ON[0]:
        d = sc.get('day')
        if d is not None:
            label = d(lt_, ctx) if callable(d) else f'DAY {d}'
            if label:
                day_counter(c, label, clamp((lt_ - 0.1) / 0.3) * (1 - ramp(lt_, ctx.dur - 0.12, 0.12)), sc.get('day_pos'))
        ln = kit.active_line(tl['lines'], t)
        if ln is not None:
            kit.caption(c, ln['text'], sc.get('cap_y', 1380), t - ln['start'] + 0.05)
    if sp['start'] > 0 and lt_ < SCENE_FADE_IN:
        rect(c, 0, 0, W, H, '#000000', 1 - ease(lt_ / SCENE_FADE_IN))
    tail = tl['duration'] - t
    if tail < kit.END_FADE:
        rect(c, 0, 0, W, H, '#000000', 1 - clamp(tail / kit.END_FADE))


kit.draw_frame = draw_frame


# ---------------------------------------------------------------- voices + timeline
_KOKORO = [None]


def speak(txt, vc, cache):
    tag = hashlib.sha1(f"{txt}|{vc['voice']}|{vc['speed']}".encode()).hexdigest()[:10]
    fn = os.path.join(cache, f'{tag}.wav')
    if os.path.exists(fn):
        a, sr = sf.read(fn)
        return a, sr
    if _KOKORO[0] is None:
        _KOKORO[0] = narrate.load()
    a, sr = _KOKORO[0].create(txt, voice=vc['voice'], speed=vc['speed'], lang='en-us')
    a = narrate.trim(np.asarray(a, dtype=np.float32), sr)
    sf.write(fn, a, sr)
    return a, sr


def plain(s):
    return ' '.join(s.replace('|', ' ').split())


def pauses(a, sr, db=-38.0, min_len=0.06):
    """Silent stretches inside a spoken line: (start, end) in seconds, quieter than db below the line's peak."""
    hop = int(0.01 * sr)
    n = len(a) // hop
    if n < 6:
        return []
    rms = np.sqrt(np.mean(np.asarray(a[:n * hop], np.float64).reshape(n, hop) ** 2, axis=1))
    q = 20 * np.log10(rms / (rms.max() + 1e-9) + 1e-9) < db
    out, k = [], 0
    while k < n:
        if q[k]:
            j = k
            while j < n and q[j]:
                j += 1
            if j - k >= int(round(min_len / 0.01)) and k > 2 and j < n - 2:
                out.append((k * 0.01, j * 0.01))
            k = j
        else:
            k += 1
    return out


def snap(cs, ps, reach=0.2):
    """Moves each caption break onto the end of a nearby pause (each pause used once), so the next words appear as
    they are spoken."""
    out, used = list(cs), set()
    for i in range(1, len(out)):
        t_est = out[i][0]
        near = [(abs(p1 - t_est), k) for k, (_, p1) in enumerate(ps) if abs(p1 - t_est) < reach and k not in used]
        if near:
            _, k = min(near)
            used.add(k)
            out[i] = (ps[k][1] - 0.03, out[i][1])
        out[i] = (max(out[i][0], out[i - 1][0] + 0.12), out[i][1])
    return out


def chunk_times(cs, d, vc, cache):
    """Re-times caption chunks by speaking each chunk on its own: the line's length is shared out in proportion to
    how long each chunk takes alone, which follows the voice far better than counting letters."""
    if len(cs) < 2:
        return cs
    ds = [len(speak(narrate.spoken(('', p)), vc, cache)[0]) for _, p in cs]
    acc, out = 0.0, []
    for (_, p), n in zip(cs, ds):
        out.append((d * acc / sum(ds), p))
        acc += n
    return out


def timeline(script, out):
    cache = VOICE_CACHE
    os.makedirs(cache, exist_ok=True)
    t, lines, segs = LEAD_IN, [], []
    for i, e in enumerate(script):
        last = i == len(script) - 1
        t += e.get('pre', 0.0)
        v = e.get('v')
        if v in VOICES:
            txt = narrate.spoken(('', plain(e['text']), e['say']) if e.get('say') else ('', plain(e['text'])))
            a, sr = speak(txt, VOICES[v], cache)
            d = len(a) / sr / VOICES[v]['pitch_len']
            segs.append((v, t, a, sr))
            gap = e.get('gap', TAIL if last else narrate.gap_after(plain(e['text']), False) + VOICES[v]['extra_gap'])
        else:
            d = e['dur']
            gap = e.get('gap', TAIL if last else 0.0)
        ln = dict(i=i, scene=e['scene'], text=e['text'], start=round(t, 3), end=round(t + d, 3), v=v or 'text',
                  style=e.get('style', v or 'none'), key=[_norm(k) for k in e.get('key', [])])
        if ln['style'] in SPOKEN_STYLES:
            pl = VOICES[v]['pitch_len']
            ln['chunks'] = snap(chunk_times(chunks(e['text'], d), d, VOICES[v], cache),
                                [(p0 / pl, p1 / pl) for p0, p1 in pauses(a, sr)])
        for k in ('pos', 'size'):
            if k in e:
                ln[k] = e[k]
        lines.append(ln)
        t += d + gap
    tl = dict(duration=round(t, 3), lines=lines, hook=('', ''), name=os.path.basename(out))
    LINES.clear()
    LINES.update({ln['text']: ln for ln in lines})
    return tl, segs


def voice_tracks(tl, segs, out):
    """One processed stereo track per voice, at SR, placed on the timeline."""
    n = int(math.ceil(tl['duration'] * SR)) + SR
    tracks = {}
    for v, vc in VOICES.items():
        raw = np.zeros(int(math.ceil(tl['duration'] * 24000)) + 24000, np.float32)
        any_ = False
        for vv, t0, a, sr in segs:
            if vv != v:
                continue
            any_ = True
            s0 = int(round(t0 * sr * vc['pitch_len']))
            raw[s0:s0 + len(a)] += a[:len(raw) - s0]
        if not any_:
            continue
        p_raw, p_out = os.path.join(out, f'{v}_raw.wav'), os.path.join(out, f'{v}.wav')
        sf.write(p_raw, raw, 24000)
        p = vc['pitch']
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', p_raw, '-af',
                        f'asetrate=24000*{p},aresample={SR},atempo={vc["pitch_len"] / p:.5f}', p_out], check=True)
        x, _ = sf.read(p_out)
        x = np.pad(x, (0, max(0, n - len(x))))[:n]
        x = music.lp(x, vc['lp'])
        if vc.get('trem'):
            fq, dp = vc['trem']
            x = x * (1 + dp * np.sin(2 * np.pi * fq * np.arange(len(x)) / SR))
        if vc.get('breath'):
            env_ = music.lp(np.abs(x), 30)
            x = x + music.bp(np.random.default_rng(5).standard_normal(n), 2500, 8000) * env_ * vc['breath']
        tracks[v] = music.reverb(x, vc['reverb']) * vc['gain']
    return tracks


# ---------------------------------------------------------------- sound
def env(n, att, dec):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(att, 1e-4)) * np.exp(-t / dec)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def piano(midi, dur=2.5, vel=1.0):
    f = hz(midi)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for h, (a, d) in enumerate(((1.0, 1.8), (0.42, 1.0), (0.2, 0.7), (0.1, 0.45), (0.05, 0.3)), 1):
        x += a * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-t / (d * (330 / max(f, 110)) ** 0.3))
    x *= np.minimum(1, t / 0.004) * np.minimum(1, (t[-1] - t) / 0.25 + 1e-9)
    return x * vel * 0.25


def pad(midis, dur, att=0.6, rel=0.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for m in midis:
        for det in (-0.12, 0.0, 0.11):
            f = hz(m) * 2 ** (det / 12)
            x += sum(np.sin(2 * np.pi * f * h * t + h) / h for h in range(1, 7)) / 3
    x = music.lp(x, 2200)
    e = np.minimum(1, t / att) * np.minimum(1, np.maximum(0, (t[-1] - t)) / rel)
    return x * e / max(len(midis), 1) * 0.5


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(45 + 95 * np.exp(-t / 0.035)) / SR
    return np.sin(ph) * np.exp(-t / 0.2) + music.hp(np.random.default_rng(1).standard_normal(n), 2000) * np.exp(-t / 0.003) * 0.3


def snare(rng):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    return music.bp(rng.standard_normal(n), 900, 6000) * env(n, 0.001, 0.07) * 0.8 + np.sin(2 * np.pi * 185 * t) * env(n, 0.001, 0.05) * 0.5


def hat(rng):
    n = int(0.08 * SR)
    return music.hp(rng.standard_normal(n), 7000) * env(n, 0.001, 0.018)


def bass(midi, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)) * env(n, 0.01, 0.9) * np.minimum(1, (t[-1] - t) / 0.05)


def drone(dur, root=55.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * root * m * t + p) for m, a, p in ((1, 0.9, 0), (2.005, 0.5, 1), (2.997, 0.25, 2), (4.01, 0.12, 3)))
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * t)
    return x + music.lp(np.random.default_rng(4).standard_normal(n), 400) * 0.25


def beep():
    n = int(0.075 * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * 2050 * k * t) / k for k in (1, 3, 5))
    return x * np.minimum(1, t / 0.003) * np.minimum(1, (t[-1] - t) / 0.004) * 0.35


def thump(f=52, dec=0.15):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.6 * t)) * env(n, 0.004, dec)


def noise_hit(rng, lo, hi, dur, dec):
    n = int(dur * SR)
    return music.bp(rng.standard_normal(n), lo, hi) * env(n, 0.002, dec)


def riser(dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for k in range(16):
        s0, s1 = k * n // 16, (k + 1) * n // 16
        fc = 250 * 2 ** (k / 4)
        out[s0:s1] = music.bp(x[s0:s1], fc * 0.7, fc * 1.4)
    return out * (t / t[-1]) ** 2 * 0.6


def wind(dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return music.lp(rng.standard_normal(n), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t) ** 2)


def put(buf, x, t0, gain=1.0):
    s0 = int(round(t0 * SR))
    if s0 < 0:
        x, s0 = x[-s0:], 0
    if s0 < len(buf):
        x = x[:len(buf) - s0]
        buf[s0:s0 + len(x)] += x * gain


def score(tl, spans, S, rng):
    """S: dict(root, dark_notes, dark_every, turn, title, end, bpm, chords, end_chord, levels...). Returns mono music."""
    dur = tl['duration']
    n = int(math.ceil(dur * SR)) + SR
    mus = np.zeros(n)
    t_turn, t_title, t_end = spans[S['turn']]['start'], spans[S['title']]['start'], spans[S['end']]['start']
    d = drone(t_turn + 0.5, S['root'])
    tt = np.arange(len(d)) / SR
    d *= np.minimum(1, tt / 1.5) * np.minimum(1, (len(d) / SR - tt) / 0.4) * (0.6 + 0.4 * np.clip(tt / max(t_turn, 1), 0, 1))
    put(mus, d, 0.0, S.get('drone', 0.16))
    k, t0 = 0, S.get('dark_start', 0.9)
    while t0 < t_turn - 0.6:
        put(mus, piano(S['dark_notes'][k % len(S['dark_notes'])], 2.8, 0.7), t0, S.get('piano', 0.34))
        k += 1
        t0 += S['dark_every']
    put(mus, riser(t_title - t_turn, rng) if t_title - t_turn > 0.8 else np.zeros(1), t_turn, 0.22)
    beat = 60 / S['bpm']
    chords = S['chords']
    bar = 4 * beat
    k = 0
    while t_title + k * beat < t_end - 0.01:
        tb = t_title + k * beat
        put(mus, kick(), tb, S.get('kick', 0.5))
        put(mus, hat(rng), tb + beat / 2, S.get('hat', 0.1))
        if k % 4 in (1, 3) and k >= 4:
            put(mus, snare(rng), tb, S.get('snare', 0.22))
        k += 1
    k = 0
    while t_title + k * bar < t_end - 0.01:
        ch = chords[k % len(chords)]
        tb = t_title + k * bar
        ln = min(bar, t_end - tb) + 0.6
        put(mus, pad([m + 12 for m in ch], ln), tb, S.get('pad', 0.22))
        put(mus, bass(ch[0] - 12, min(bar, t_end - tb)), tb, S.get('bass', 0.3))
        for j in range(8):
            tj = tb + j * beat / 2
            if tj < t_end - 0.05:
                put(mus, piano(ch[[0, 1, 2, 1][j % 4]] + 12, 1.2, 0.5), tj, S.get('piano', 0.34))
        k += 1
    ec = S['end_chord']
    put(mus, pad([m + 12 for m in ec], dur - t_end + 0.5, att=0.3, rel=2.5), t_end, S.get('pad', 0.22) * 1.3)
    for j, m in enumerate(ec):
        put(mus, piano(m, 4.0, 0.8), t_end + 0.04 * j, S.get('piano', 0.34))
    put(mus, piano(ec[0] - 12, 4.0, 0.9), t_end, S.get('piano', 0.34))
    for j, m in enumerate(S.get('end_melody', [])):
        put(mus, piano(m, 2.6, 0.55), t_end + 1.6 + j * 0.8, S.get('piano', 0.34))
    return mus


def pluck(midi, dur=0.7, bright=0.6):
    """A plucked string: a few decaying harmonics, the high ones dying first."""
    f = hz(midi)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(bright ** (h - 1) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (3.5 + 2.2 * h) / max(dur, 0.1) * 0.6)
            for h in range(1, 6))
    return x * np.minimum(1, t / 0.002) * np.minimum(1, (t[-1] - t) / 0.03) * 0.3


def marimba(midi, dur=0.6):
    f = hz(midi)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.22) + 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.03)
    return x * np.minimum(1, t / 0.002) * 0.35


def shaker(rng):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    return music.bp(rng.standard_normal(n), 5000, 11000) * np.sin(np.pi * t / t[-1]) ** 2 * 0.5


def frame_drum(rng, low=True):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 70 if low else 190
    return (np.sin(2 * np.pi * f * t * (1 + 0.4 * np.exp(-t / 0.02))) * env(n, 0.001, 0.12 if low else 0.06)
            + music.bp(rng.standard_normal(n), 300, 3000) * env(n, 0.001, 0.02) * 0.4)


SCALES = dict(major=[0, 2, 4, 7, 9], minor=[0, 3, 5, 7, 10], hijaz=[0, 1, 4, 5, 7, 8, 10], dorian=[0, 2, 3, 7, 9])


def music_bed(tl, spans, S, rng):
    """The music under the five cartoon looks: a looping pattern over a pad and bass, from the first frame to the end.
    S: dict(kind='bed', bpm, root (midi), scale, lead=pluck|marimba|piano, steps (scale degrees per 8th, None = rest),
    chords (degree lists per bar), drums=pop|frame|shaker|none, drone, levels lead/pad/bass/drums)."""
    dur = tl['duration']
    n = int(math.ceil(dur * SR)) + SR
    mus = np.zeros(n)
    beat = 60 / S['bpm']
    sc = SCALES[S.get('scale', 'major')]

    def deg(d, base):
        o, k = divmod(d, len(sc))
        return base + 12 * o + sc[k]

    root = S['root']
    lead = dict(pluck=pluck, marimba=marimba, piano=lambda m, d: piano(m, d * 2.2, 0.6))[S.get('lead', 'pluck')]
    steps, chords = S['steps'], S.get('chords', [[0, 2, 4]])
    end = dur - 0.6
    k = 0
    while k * beat / 2 < end:
        t0 = k * beat / 2
        d = steps[k % len(steps)]
        if d is not None:
            put(mus, lead(deg(d, root + 12), beat * 1.4), t0, S.get('lead_g', 0.5) * (1.0 if k % 2 == 0 else 0.8))
        k += 1
    bar = 4 * beat
    for b in range(int(end / bar) + 1):
        ch = chords[b % len(chords)]
        tb = b * bar
        ln = min(bar, dur - tb) + 0.5
        put(mus, pad([deg(x, root) for x in ch], ln, att=0.3, rel=0.6), tb, S.get('pad_g', 0.16))
        put(mus, bass(deg(ch[0], root - 12), min(bar, dur - tb)), tb, S.get('bass_g', 0.22))
    if S.get('drone'):
        put(mus, drone(dur, hz(root - 12)), 0.0, S['drone'])
    kind = S.get('drums', 'pop')
    for j in range(int(end / beat) + 1):
        tb = j * beat
        if kind == 'pop':
            put(mus, kick(), tb, S.get('drum_g', 0.4) * (1.0 if j % 2 == 0 else 0.6))
            put(mus, hat(rng), tb + beat / 2, 0.09)
            if j % 2 == 1:
                put(mus, snare(rng), tb, S.get('drum_g', 0.4) * 0.45)
        elif kind == 'frame':
            put(mus, frame_drum(rng, j % 4 in (0, 3)), tb, S.get('drum_g', 0.4) * (1.0 if j % 4 == 0 else 0.55))
            put(mus, frame_drum(rng, False), tb + beat * 0.75, S.get('drum_g', 0.4) * 0.3)
        elif kind == 'shaker':
            put(mus, shaker(rng), tb, 0.22)
            put(mus, shaker(rng), tb + beat / 2, 0.14)
    mus[int((dur - 1.0) * SR):int(dur * SR)] *= np.linspace(1, 0.15, int(dur * SR) - int((dur - 1.0) * SR))
    return mus


def soundtrack(tl, segs, S, sfx_fn, out):
    rng = np.random.default_rng(9)
    spans = {}
    for sp in kit.scene_spans(tl):
        spans.setdefault(sp['scene'], sp)
    n = int(math.ceil(tl['duration'] * SR)) + SR
    voices = voice_tracks(tl, segs, out)
    vsum = sum(voices.values()) if voices else np.zeros((n, 2))
    mus = music_bed(tl, spans, S, rng) if S.get('kind') == 'bed' else score(tl, spans, S, rng)
    fx = np.zeros(n)
    if S.get('title'):
        put(fx, music.sfx('boom'), spans[S['title']]['start'], 0.9)
    for t0, snd, g in (sfx_fn(tl, spans, rng) if sfx_fn else []):
        put(fx, snd, t0, g)
    envv = music.lp(np.abs(vsum.mean(1)), 8)
    envv = envv / max(envv.max(), 1e-6)
    duck = 1 - S.get('duck', 0.45) * np.clip(envv * 3, 0, 1)
    mixd = vsum + music.reverb(mus * duck, 0.26) + music.reverb(fx * (1 - 0.5 * np.clip(envv * 3, 0, 1)), 0.2) * S.get('fx', 0.6)
    mixd = mixd[:int(round(tl['duration'] * SR))]
    fade = int(0.8 * SR)
    mixd[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mixd = mixd / max(np.abs(mixd).max(), 1e-6) * 0.89
    raw = os.path.join(out, 'mix_raw.wav')
    wav = os.path.join(out, 'mix.wav')
    sf.write(raw, mixd.astype(np.float32), SR)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', music.LOUDNORM, '-ar', str(SR), wav], check=True)
    return wav


# ---------------------------------------------------------------- lit sets (palettes in settings.py)
def grr(c, x, y, w, h, r, cols, pos=None, a=1.0):
    """A rounded rectangle filled with a top-to-bottom gradient."""
    c.drawRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), P('#ffffff', a, shader=lgrad(x, y, x, y + h, list(cols), pos)))


def room(c, pal, floor_y=1480):
    grect(c, -500, -500, W + 1000, floor_y + 500, list(pal['wall']))
    grect(c, -500, floor_y, W + 1000, H + 600 - floor_y, list(pal['floor']))
    rect(c, -500, floor_y - 12, W + 1000, 14, pal['trim'])


def beam(c, pts, cl, a=0.14, blur=24):
    """A soft shaft of light over the polygon pts, fading out downward."""
    ys = [p[1] for p in pts]
    sh = lgrad(0, min(ys), 0, max(ys), [(cl, a), (cl, a * 0.5), (cl, 0.0)], [0, 0.55, 1])
    c.drawPath(path(pts), P('#ffffff', shader=sh, blur=blur))


def dust(c, t, box, n=None, cl=None, a=None, seed=1, size=1.0):
    """Motes drifting and twinkling inside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    n, cl = n or DUST['n'], cl or DUST['color']
    a = DUST['a'] if a is None else a
    rng = np.random.default_rng(seed)
    for i in range(n):
        px, py, sp, ph = rng.random(), rng.random(), 0.3 + 0.7 * rng.random(), 6.283 * rng.random()
        r = (1.6 + 3.4 * rng.random()) * size
        fx = (px + 0.010 * sp * t + 0.02 * math.sin(0.6 * sp * t + ph)) % 1.0
        fy = (py - 0.018 * sp * t + 0.015 * math.sin(0.8 * t + 2 * ph)) % 1.0
        edge = clamp(min(fx, 1 - fx, fy, 1 - fy) * 8)
        tw_ = 0.55 + 0.45 * math.sin((1.0 + sp) * t + 3 * ph)
        circ(c, x0 + fx * (x1 - x0), y0 + fy * (y1 - y0), r, cl, a * tw_ * edge, blur=r * 0.9)


def window(c, x, y, w, h, pal, t=0.0, moon=(0.68, 0.3), stars=22, light=1.0, seed=3):
    rrect(c, x - 18, y - 18, w + 36, h + 36, 8, pal['frame'])
    grect(c, x, y, w, h, list(pal['sky']))
    c.save()
    c.clipRect(R(x, y, w, h))
    rng = np.random.default_rng(seed)
    for i in range(stars):
        sx, sy, sr = x + rng.random() * w, y + rng.random() * h * 0.75, 1.4 + 1.6 * rng.random()
        circ(c, sx, sy, sr, '#FFFFFF', light * (0.35 + 0.35 * math.sin(2.1 * t + 7 * i)))
    if moon:
        mx, my = x + moon[0] * w, y + moon[1] * h
        glow(c, mx, my, 170, pal['moon'], 0.35 * light)
        circ(c, mx, my, 36, pal['moon'], light)
        circ(c, mx + 12, my - 8, 30, mix(pal['sky'][0], pal['moon'], 0.15), light)
    c.restore()
    line(c, x + w / 2, y, x + w / 2, y + h, pal['frame'], w=14, cap='butt')
    line(c, x, y + h / 2, x + w, y + h / 2, pal['frame'], w=14, cap='butt')
    rrect(c, x - 34, y + h + 12, w + 68, 22, 6, mix(pal['frame'], '#FFFFFF', 0.08))


def poster(c, x, y, w, h, pal):
    """A framed print of a mountain at sunrise on the wall."""
    rect(c, x + 8, y + 12, w, h, '#000000', 0.35, blur=12)
    rrect(c, x, y, w, h, 6, pal['frame'])
    ix, iy, iw, ih = x + 16, y + 16, w - 32, h - 32
    grect(c, ix, iy, iw, ih, [mix(DAWN['sky'][1], pal['wall'][1], 0.45), mix(DAWN['sky'][3], pal['wall'][1], 0.4)])
    c.save()
    c.clipRect(R(ix, iy, iw, ih))
    circ(c, ix + iw * 0.6, iy + ih * 0.6, iw * 0.15, mix(DAWN['sun'], pal['wall'][1], 0.3))
    poly(c, [(ix - 10, iy + ih), (ix + iw * 0.4, iy + ih * 0.36), (ix + iw * 0.6, iy + ih * 0.58), (ix + iw * 0.78, iy + ih * 0.48),
             (ix + iw + 10, iy + ih)], mix(DAWN['ridges'][2], pal['wall'][1], 0.3))
    c.restore()


def hanging_lamp(c, x, y, w, pal, on=1.0, floor_y=1480):
    """A dome lamp hanging on a cord, throwing a warm cone and a pool of light on the floor."""
    line(c, x, -500, x, y - w * 0.34, '#1A1210', w=5)
    if on > 0:
        cone = path([(x - w * 0.42, y + 4), (x + w * 0.42, y + 4), (x + w * 2.0, floor_y + 60), (x - w * 2.0, floor_y + 60)])
        c.drawPath(cone, P('#ffffff', shader=lgrad(0, y, 0, floor_y + 60, [(pal['lamp'], 0.3 * on), (pal['lamp'], 0.1 * on),
                                                                                (pal['lamp'], 0.0)], [0, 0.6, 1]), blur=24))
        glow(c, x, y + 12, w * 1.5, pal['lamp'], 0.5 * on)
        oval(c, x, floor_y + 24, w * 1.8, 64, pal['lamp'], 0.2 * on, blur=30)
    dome = skia.Path()
    dome.moveTo(x - w / 2, y)
    dome.cubicTo(x - w / 2, y - w * 0.46, x + w / 2, y - w * 0.46, x + w / 2, y)
    dome.close()
    c.drawPath(dome, P('#ffffff', shader=lgrad(x - w / 2, y - w * 0.3, x + w / 2, y, [mix(pal['dome'], '#FFFFFF', 0.4), pal['dome'],
                                                                                           mix(pal['dome'], '#000000', 0.4)])))
    oval(c, x, y, w / 2, w * 0.07, mix(pal['lamp'], '#FFFFFF', 0.6 * on))
    rrect(c, x - 11, y - w * 0.4, 22, 20, 6, '#2A1C15')


def bed(c, pal, x0=210, x1=1010, top=1200, floor_y=1450):
    grr(c, x0 - 30, top - 230, 54, floor_y - top + 230, 22, pal['bed'])
    for lx in (x0 + 4, x1 - 44):
        rect(c, lx, top + 170, 30, floor_y - top - 170, pal['bed'][1])
    grr(c, x0, top + 96, x1 - x0, 96, 18, pal['bed'])
    grr(c, x0 + 8, top + 8, x1 - x0 - 16, 118, 34, (mix(pal['pillow'][0], pal['blanket'][1], 0.35), mix(pal['pillow'][1], pal['blanket'][1], 0.5)))
    grr(c, x0 + 34, top - 44, 230, 92, 42, pal['pillow'])


def blanket(c, t, pal, cover=0.0, breathe=1.0, x0=445, x1=1004, top=1200):
    """The blanket over the sleeper (head at about x0 - 98); cover 0 -> 1 pulls it up over his head."""
    b = 6 * math.sin(2 * math.pi * 0.35 * t) * breathe
    k = ease(cover)
    xs = x0 - 150 * k
    p = skia.Path()
    p.moveTo(xs, top + 104)
    p.cubicTo(xs + 20, top - 20 - 40 * k - b, x0 + 200, top + 22 - b, x0 + 330, top + 36 - b * 0.6)
    p.cubicTo(x0 + 420, top + 48, x1 - 50, top + 60, x1, top + 104)
    p.lineTo(x1, top + 150)
    p.lineTo(xs - 8, top + 150)
    p.close()
    if k > 0:
        xh = x0 - 98
        q = skia.Path()
        q.moveTo(xh - 140, top + 104)
        q.cubicTo(xh - 150, top - 150 * k - b, xh + 130, top - 165 * k - b, xh + 170, top + 30 - b)
        q.lineTo(xh + 170, top + 104)
        q.close()
        p = skia.Op(p, q, skia.PathOp.kUnion_PathOp)
    c.drawPath(p, P('#ffffff', shader=lgrad(0, top - 60 - 100 * k, 0, top + 150, list(pal['blanket']))))
    c.save()
    c.clipPath(p, skia.ClipOp.kIntersect, True)
    line(c, xs - 20, top + 128, x1 + 20, top + 128, mix(pal['blanket'][0], '#FFFFFF', 0.25), w=8, a=0.5)
    c.restore()


def sleeper(c, x, y, s, t, expr='closed', blink=0.0, look=(0.0, 0.0), brows=0.0, mouth=None):
    """His head on the pillow, top of the head toward the headboard."""
    hu.head(c, x, y + 3 * math.sin(2 * math.pi * 0.35 * t), s, expr, look, blink, brows, 'front', tilt=-80.0, mouth=mouth)


def nightstand(c, x, floor_y, pal, clock=None, ring=0.0, t=0.0, w=190, h=250):
    grr(c, x, floor_y - h, w, h, 14, pal['stand'])
    line(c, x + 16, floor_y - h * 0.52, x + w - 16, floor_y - h * 0.52, mix(pal['stand'][1], '#000000', 0.35), w=4)
    circ(c, x + w / 2, floor_y - h * 0.28, 8, mix(pal['stand'][0], '#FFFFFF', 0.3))
    if clock is None:
        return
    cx, cy = x + w / 2 + 3.5 * math.sin(t * 70) * ring, floor_y - h - 50
    oval(c, cx - 44, cy + 46, 12, 6, '#0B0C18')
    oval(c, cx + 44, cy + 46, 12, 6, '#0B0C18')
    rrect(c, cx - 74, cy - 46, 148, 92, 20, '#0C0D1C')
    rrect(c, cx - 74, cy - 46, 148, 92, 20, mix(pal['frame'], '#FFFFFF', 0.1), sw=3)
    if ring <= 0 or math.sin(2 * math.pi * 2.0 * t) > -0.2:
        glow(c, cx, cy, 180, '#FF2B2B', 0.22 + 0.2 * ring)
        size = 58 if len(clock) <= 4 else 50
        text(c, clock, cx, cy + 20, size, '#FF3434', 1.0, tf='mono', blur=7)
        text(c, clock, cx, cy + 20, size, '#FF4A4A', 1.0, tf='mono')


def desk(c, x0, x1, top, floor_y, cols):
    """A side-view desk: a slab, a drawer box under the far end, two legs."""
    grr(c, x0, top, x1 - x0, 28, 8, cols['top'])
    rect(c, x0 + 20, top + 28, 22, floor_y - top - 28, cols['body'][1])
    grr(c, x1 - 200, top + 28, 180, 150, 6, cols['body'])
    rrect(c, x1 - 140, top + 92, 60, 12, 6, cols['knob'])
    rect(c, x1 - 42, top + 178, 22, floor_y - top - 178, cols['body'][1])


def desk_lamp(c, x, y, on=1.0, cl='#2C2A3C', light='#FFD28A', reach=-1.0):
    """An angle-poise lamp standing at (x, y) on a desk, its head out over the desk (reach -1: to the left), shining
    down. Returns the x where its light lands."""
    r = reach
    ex, ey = x - 26 * r, y - 180
    hx, hy = x + 70 * r, y - 250
    d, p = (0.62 * r, 0.78), (0.78, -0.62 * r)
    mx, my = hx + d[0] * 92, hy + d[1] * 92
    m1, m2 = (mx + p[0] * 62, my + p[1] * 62), (mx - p[0] * 62, my - p[1] * 62)
    a1, a2 = (hx + p[0] * 22, hy + p[1] * 22), (hx - p[0] * 22, hy - p[1] * 22)
    tx = mx + d[0] * (y - my) / d[1]
    if on > 0:
        cone = path([m1, m2, (tx + 190 * -r, y), (tx - 190 * -r, y)])
        c.drawPath(cone, P('#ffffff', shader=lgrad(0, my, 0, y, [(light, 0.34 * on), (light, 0.12 * on)]), blur=16))
        glow(c, mx, my, 380, light, 0.45 * on)
        oval(c, tx, y + 2, 230, 26, light, 0.25 * on, blur=14)
    oval(c, x, y - 8, 52, 13, cl)
    line(c, x, y - 12, ex, ey, cl, w=10)
    line(c, ex, ey, hx, hy, cl, w=10)
    poly(c, [a1, m1, m2, a2], cl)
    line(c, m1[0], m1[1], m2[0], m2[1], mix(light, '#FFFFFF', 0.5) if on > 0 else '#3C3A50', w=8)
    circ(c, hx, hy, 14, mix(cl, '#FFFFFF', 0.15))
    return tx


def books(c, x, y, n=4, seed=2, a=1.0):
    """A stack of n closed books standing on y, centred on x."""
    rng = np.random.default_rng(seed)
    cols = ['#B23A36', '#3F6FB0', '#D9A440', '#4E8A62', '#7B4FA0', '#C46A3A']
    yy = y
    for i in range(n):
        w, h = 150 + 40 * rng.random(), 30 + 10 * rng.random()
        dx = (rng.random() - 0.5) * 24
        cl = cols[int(rng.integers(len(cols)))]
        grr(c, x - w / 2 + dx, yy - h, w, h, 6, (mix(cl, '#FFFFFF', 0.12), mix(cl, '#000000', 0.25)), a=a)
        rect(c, x - w / 2 + dx + 10, yy - h + 6, w - 20, 5, '#FFF4E4', 0.7 * a)
        yy -= h + 1


def open_book(c, x, y, s=1.0, flip=None, cover='#B23A36', page='#FFF4E4', ink='#CDBBA2'):
    """An open book lying on y (the spine at x). flip in [0, 1) turns a page right to left."""
    poly(c, [(x, y), (x - 104 * s, y - 8 * s), (x - 100 * s, y - 34 * s), (x, y - 26 * s), (x + 100 * s, y - 34 * s),
             (x + 104 * s, y - 8 * s)], cover)
    for side in (-1, 1):
        poly(c, [(x, y - 4 * s), (x + side * 96 * s, y - 12 * s), (x + side * 92 * s, y - 36 * s), (x, y - 30 * s)], page)
        for k in range(3):
            yy = y - 30 * s + 6 * s * k + 4 * s
            line(c, x + side * 14 * s, yy + 2 * s, x + side * 80 * s, yy - 4 * s, ink, w=2.5 * s)
    if flip is not None and 0 <= flip < 1:
        u = ease(flip)
        tip = x + 94 * s * math.cos(math.pi * u)
        lift = 40 * s * math.sin(math.pi * u)
        poly(c, [(x, y - 4 * s), (tip, y - 12 * s - lift), (tip, y - 36 * s - lift), (x, y - 30 * s)], mix(page, '#FFFFFF', 0.5))


def chair(c, x, seat_y, floor_y, cols, facing=1):
    """A side-view chair: the back post behind x (facing: the way its sitter looks)."""
    bx = x - 100 * facing
    grr(c, bx - 17, seat_y - 250, 34, floor_y - seat_y + 250, 12, cols)
    grr(c, min(bx, bx + 214 * facing), seat_y, 214, 32, 10, cols)
    rect(c, bx + 190 * facing - 11, seat_y + 30, 22, floor_y - seat_y - 30, cols[1])


def punching_bag(c, px, py, ang, cols=('#3D4370', '#22264A'), band='#5C64A0', chain='#8C90AA', length=420, w=150):
    """A heavy bag hanging on a chain from (px, py), swung ang degrees (positive: away to the right)."""
    c.save()
    c.rotate(-ang, px, py)
    line(c, px, py, px, py + 130, chain, w=5)
    line(c, px - 40, py + 150, px, py + 120, chain, w=4)
    line(c, px + 40, py + 150, px, py + 120, chain, w=4)
    grr(c, px - w / 2, py + 140, w, length, 34, cols)
    rect(c, px - w / 2, py + 140 + length * 0.18, w, 22, band, 0.9)
    rect(c, px - w / 2, py + 140 + length * 0.78, w, 22, band, 0.9)
    c.drawRRect(skia.RRect.MakeRectXY(R(px - w / 2 + 12, py + 150, w * 0.32, length - 24), 26, 26),
                P('#FFFFFF', 0.12, blur=10))
    c.restore()


# the desk set: a night room with a desk, a chair, a stack of books; he sits at x 460 with his hands on BOOK
RED = '#FF3B3B'
DESK_N = dict(top=('#5B4F78', '#463E64'), body=('#3A3458', '#28243F'), knob='#A8A0D0')
CHAIR_N = ('#433B66', '#2C2748')
FLOOR_D = 1440
BOOK = (600, 1250)


def desk_room(c, t):
    room(c, NIGHT, FLOOR_D)
    window(c, 790, 250, 220, 290, NIGHT, t, moon=(0.62, 0.34), stars=12)
    desk(c, 500, 1060, 1250, FLOOR_D, DESK_N)
    books(c, 990, 1250, 4, seed=3)


def desk_shadow(c, t, a, sc=0.0):
    if a <= 0 and not 0 < sc < 1:
        return
    pose = dict(torso=30.0, head=20.0, la=(20.0, 50.0), ra=('ik', (482, 1196), -1), ll=(0.0, 0.0), rl=(0.0, 0.0))
    glow(c, 360, 1060, 420, RED, 0.16 * a)
    js = hu.figure(c, 250, FLOOR_D, 1.2, pose, scheme='shadow', alpha=max(a, 0.0), ground_shadow=0)
    hu.wisps(c, js, t, 1.2, a=a, n=12)
    hu.scatter(c, js, 1.2, sc)


def seated(c, t, pose, expr='open', brows=0.0, look=(0.6, 0.8), mouth=None):
    chair(c, 460, 1345, FLOOR_D, CHAIR_N, facing=1)
    return hu.figure(c, 460, 0, 1.0, pose, hip_y=1330, expr=expr, brows=brows, look=look, mouth=mouth, ground_shadow=0)


# ---------------------------------------------------------------- time passing, phones
SEASONS = [(('#6FA4E0', '#CFE6F7'), '#FFF1D6', 'sun'), (('#D98B4E', '#F4C98A'), '#FFD29A', 'leaves'),
           (('#7C8AA3', '#D3DAE4'), '#DCE6F2', 'snow'), (('#9AD0EE', '#F6D9E6'), '#FFF0F4', 'petals')]


def weather(c, kind, x, y, w, h, t, a):
    if a <= 0 or kind == 'sun':
        return
    rng = np.random.default_rng({'snow': 1, 'leaves': 2, 'petals': 3}[kind])
    n = {'snow': 46, 'leaves': 14, 'petals': 18}[kind]
    for i in range(n):
        px, sp, ph = rng.random(), 0.5 + 0.5 * rng.random(), rng.random()
        fy = (ph + t * sp * (0.35 if kind == 'snow' else 0.5)) % 1.0
        fx = px + 0.05 * math.sin(6 * fy + 7 * ph)
        xx, yy = x + fx * w, y - 20 + fy * (h + 40)
        if kind == 'snow':
            circ(c, xx, yy, 3 + 3 * rng.random(), '#FFFFFF', 0.85 * a)
        else:
            cl = ['#E0662F', '#C8442A', '#F0A23B'][i % 3] if kind == 'leaves' else ['#F7B6C8', '#FFD9E3'][i % 2]
            c.save()
            c.rotate(200 * fy + 90 * ph, xx, yy)
            oval(c, xx, yy, 9, 5, cl, 0.9 * a)
            c.restore()


def season_window(c, x, y, w, h, t, rate=0.72):
    k = t * rate
    i = int(k) % len(SEASONS)
    u = clamp((k % 1 - 0.7) / 0.3)
    (s0, l0, f0), (s1, l1, f1) = SEASONS[i], SEASONS[(i + 1) % len(SEASONS)]
    dn = 0.5 + 0.5 * math.cos(2 * math.pi * 1.5 * t)
    top = mix(mix(s0[0], s1[0], u), NIGHT['sky'][0], 0.82 * dn)
    bot = mix(mix(s0[1], s1[1], u), NIGHT['sky'][1], 0.82 * dn)
    rrect(c, x - 18, y - 18, w + 36, h + 36, 8, NIGHT['frame'])
    grect(c, x, y, w, h, [top, bot])
    c.save()
    c.clipRect(R(x, y, w, h))
    ph = (1.5 * t + 0.5) % 1.0
    sx, sy = x + w * (1.15 - 1.3 * ph), y + h * (0.8 - 0.55 * math.sin(math.pi * ph))
    day = clamp(1 - 2 * dn)
    if day > 0:
        glow(c, sx, sy, 150, '#FFE9B0', 0.55 * day)
        circ(c, sx, sy, 30, '#FFF3D0', day)
    if day < 1:
        circ(c, sx, sy, 26, NIGHT['moon'], 1 - day)
    weather(c, f0, x, y, w, h, t, 1 - u)
    weather(c, f1, x, y, w, h, t, u)
    c.restore()
    line(c, x + w / 2, y, x + w / 2, y + h, NIGHT['frame'], w=14, cap='butt')
    line(c, x, y + h / 2, x + w, y + h / 2, NIGHT['frame'], w=14, cap='butt')
    rrect(c, x - 34, y + h + 12, w + 68, 22, 6, mix(NIGHT['frame'], '#FFFFFF', 0.08))
    return mix(l0, l1, u), day


def cobweb(c, x, y, a, size=160):
    """A web spun into the corner at (x, y), growing with a."""
    if a <= 0:
        return
    cl = '#D4DCFF'
    angs = [0, 22, 45, 68, 90]
    ln = size * (0.4 + 0.6 * a)
    for g in angs:
        r_ = math.radians(g)
        line(c, x, y, x + ln * math.cos(r_), y + ln * math.sin(r_), cl, w=1.6, a=0.55 * a)
    for k, rr in enumerate((0.3, 0.52, 0.74, 0.96)):
        if a < 0.2 * k:
            continue
        pts = [(x + rr * ln * math.cos(math.radians(g)), y + rr * ln * math.sin(math.radians(g))) for g in angs]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            line(c, x0, y0, (x0 + x1) / 2 + 3, (y0 + y1) / 2 + 3, cl, w=1.3, a=0.45 * a)
            line(c, (x0 + x1) / 2 + 3, (y0 + y1) / 2 + 3, x1, y1, cl, w=1.3, a=0.45 * a)


def big_phone(c, x, y, t, scroll, clock, feed=None, reflect=0.16):
    """A phone filling the frame, its feed scrolled by `scroll` px. feed(c, x, y, w, h, i) draws card i (default:
    coloured blocks); reflect is how strongly the shadow's red eyes show in the glass."""
    w, h = 400, 780
    glow(c, x, y, 760, '#5E9BFF', 0.3)
    rrect(c, x - w / 2 - 16, y - h / 2 - 16, w + 32, h + 32, 60, '#0B0B10')
    sx, sy = x - w / 2, y - h / 2
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(R(sx, sy, w, h), 46, 46), True)
    rect(c, sx, sy, w, h, '#E6EEFF')
    cols = ['#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7', '#FF9F43', '#54A0FF', '#1DD1A1', '#F368E0']
    card = 300
    k0 = int(scroll // card)
    for i in range(k0 - 1, k0 + 4):
        yy = sy + 90 + i * card - scroll
        if feed:
            feed(c, sx + 22, yy, w - 44, 200, i)
        else:
            rrect(c, sx + 22, yy, w - 44, 200, 18, cols[i % len(cols)], 0.92)
        rrect(c, sx + 22, yy + 214, (w - 44) * 0.8, 16, 8, '#B8C4DC')
        rrect(c, sx + 22, yy + 240, (w - 44) * 0.55, 16, 8, '#CBD5E8')
    rect(c, sx, sy, w, 72, '#E6EEFF')
    text(c, clock, sx + 74, sy + 50, 30, '#1A1A26', tf='pop')
    rrect(c, sx + w - 86, sy + 28, 46, 22, 6, '#1A1A26', sw=3)
    rect(c, sx + w - 82, sy + 32, 20, 14, '#1A1A26')
    rrect(c, x - 60, sy + 18, 120, 34, 17, '#0B0B10')
    for side in (-1, 1):
        pp = kit.path([(x - side * 52 - 10, y - 150), (x + side * 22, y - 122), (x + side * 18, y - 106), (x - side * 52, y - 128)])
        c.drawPath(pp, P(RED, reflect))
    c.drawPath(kit.path([(sx, sy + 220), (sx + w, sy - 40), (sx + w, sy + 60), (sx, sy + 320)]), P('#FFFFFF', 0.08))
    c.restore()


# ---------------------------------------------------------------- painting
def painting(c, x, y, w, h, q=1.0, seed=0):
    """A small landscape (sky, sun, mountains) painted at skill q: 0 a lopsided muddy mess, 1 a clean sunrise."""
    rng = np.random.default_rng(abs(int(seed)))
    c.save()
    c.clipRect(R(x, y, w, h))
    mud = ('#A3A07A', '#8C7B66', '#6E7562')
    jit = 1 - q
    grect(c, x, y, w, h, [mix(mud[0], DAWN['sky'][1], q), mix(mud[1], DAWN['sky'][3], q)])
    sx = x + w * (0.6 + (rng.random() - 0.5) * 0.35 * jit)
    sy = y + h * (0.5 + (rng.random() - 0.5) * 0.3 * jit)
    sr = w * (0.1 + 0.06 * jit * rng.random())
    if q > 0.4:
        glow(c, sx, sy, sr * 3.2, DAWN['sun'], 0.6 * (q - 0.4))
    c.save()
    c.rotate(40 * (rng.random() - 0.5) * jit, sx, sy)
    oval(c, sx, sy, sr * (1 + 0.4 * jit), sr * (1 - 0.25 * jit), mix('#D9A93A', mix(DAWN['sun'], '#FFFFFF', 0.4), q))
    c.restore()
    for k, base in enumerate((0.64, 0.76, 0.9)):
        if q < 0.35 and k == 0:
            continue
        pts = [(x - 10, y + h + 10)]
        n = 6 + 4 * int(q * 2)
        for i in range(n + 1):
            u = i / n
            peak = max(0.0, math.sin(u * math.pi * (1.2 + 0.7 * k) + 1.3 * k + seed))
            yy = y + h * (base - (0.2 - 0.04 * k) * peak) + (rng.random() - 0.5) * h * 0.18 * jit
            pts.append((x + u * w + (rng.random() - 0.5) * w * 0.08 * jit, yy))
        pts.append((x + w + 10, y + h + 10))
        poly(c, pts, mix(mud[2], DAWN['ridges'][k], q))
    if q > 0.6:
        oval(c, x + w * 0.5, y + h * 0.72, w * 0.6, h * 0.04, DAWN['mist'], 0.35 * (q - 0.6) / 0.4, blur=max(2, w * 0.02))
    for i in range(int(round(7 * jit))):
        x0, y0 = x + rng.random() * w, y + rng.random() * h
        line(c, x0, y0, x0 + (rng.random() - 0.5) * w * 0.5, y0 + (rng.random() - 0.5) * h * 0.35, mud[i % 3],
             w=max(3, w * 0.035), a=0.85)
    c.restore()


def easel(c, x, floor_y, q=None, seed=0, top=None, w=300, h=230, dusty=0.0, cover=0.0, reveal=1.0):
    """A wooden easel and canvas: blank (q None) or a painting at skill q, shown up to `reveal` (0..1, left to right).
    dusty greys it over; cover drapes a sheet on it. Returns the canvas rectangle."""
    top = top or floor_y - 640
    wood, dark = '#7A5236', '#4E3422'
    line(c, x + 36, floor_y, x + 6, top - 30, dark, w=12)
    line(c, x - 120, floor_y, x - 8, top - 50, wood, w=14)
    line(c, x + 120, floor_y, x + 8, top - 50, wood, w=14)
    rect(c, x - w / 2 - 24, top + h, w + 48, 18, '#5A3C28')
    rect(c, x - w / 2 + 8, top + 10, w, h, '#000000', 0.3, blur=10)
    grect(c, x - w / 2, top, w, h, ['#FBF8F1', '#E9E3D6'])
    if q is not None and reveal > 0:
        c.save()
        c.clipRect(R(x - w / 2, top, w * clamp(reveal), h))
        painting(c, x - w / 2, top, w, h, q, seed)
        c.restore()
    rect(c, x - w / 2, top, w, h, '#D9D2C2', sw=3)
    if dusty > 0:
        rect(c, x - w / 2, top, w, h + 18, '#7D7A70', 0.4 * dusty)
        rng = np.random.default_rng(5)
        for i in range(int(40 * dusty)):
            circ(c, x - w / 2 + rng.random() * w, top + rng.random() * h, 1.5 + 2 * rng.random(), '#B8B2A4', 0.6 * dusty)
    if cover > 0:
        k = ease(cover)
        p = skia.Path()
        p.moveTo(x - w / 2 - 20, top - 24)
        p.cubicTo(x - w / 6, top - 50 * k, x + w / 6, top - 50 * k, x + w / 2 + 20, top - 24)
        p.cubicTo(x + w / 2 + 60, top + h * 0.6, x + w / 2 + 50, top + h + 140 * k, x + w / 2 + 10, top + h + 170 * k)
        p.cubicTo(x + w / 6, top + h + 130 * k, x - w / 6, top + h + 180 * k, x - w / 2 - 10, top + h + 160 * k)
        p.cubicTo(x - w / 2 - 50, top + h * 0.6, x - w / 2 - 40, top + 10, x - w / 2 - 20, top - 24)
        p.close()
        c.drawPath(p, P('#ffffff', k, shader=lgrad(x - w / 2, top, x + w / 2, top + h + 170, ['#C2BFDA', '#6E6C90'])))
    return x - w / 2, top, w, h


def couch(c, x0, x1, seat_y, floor_y, cols):
    """A side-view couch facing right: a tall back cushion at x0, the seat out to x1."""
    for lx in (x0 + 20, x1 - 40):
        rect(c, lx, seat_y + 60, 20, floor_y - seat_y - 60, '#2A2238')
    grr(c, x0, seat_y - 230, 90, 300, 40, cols)
    grr(c, x0 + 40, seat_y, x1 - x0 - 40, 74, 30, (mix(cols[0], '#FFFFFF', 0.12), cols[1]))


def tv(c, x, y, w, h, t, on=1.0):
    """A TV on a low stand, its screen flickering blue-white; returns the flicker level for lighting."""
    fl = 0.75 + 0.25 * math.sin(t * 23) * math.sin(t * 7.3 + 1)
    rect(c, x + w * 0.2, y + h, w * 0.6, 26, '#1B1828')
    grr(c, x - 40, y + h + 26, w + 80, 160, 10, ('#2C2640', '#1D1930'))
    if on:
        glow(c, x + w / 2, y + h / 2, w * 1.6, '#8FB6FF', 0.3 * fl * on)
    rrect(c, x - 10, y - 10, w + 20, h + 20, 8, '#0E0D16')
    grect(c, x, y, w, h, [mix('#0E0D16', '#BFD6FF', fl * on), mix('#0E0D16', '#6E8FD8', fl * on)])
    return fl * on


def sky(c, top, bottom, cols, pos=None):
    grect(c, -500, top, W + 1000, bottom - top, list(cols), pos)


def ridge(c, horizon, amp, freq, off, colr, base=None, seed=0.0):
    pts = [(-500, base or H + 600)]
    for i in range(0, 61):
        xx = -500 + i * 36
        pts.append((xx, horizon - amp * (0.55 + 0.45 * math.sin((xx + off) * freq + seed)) - amp * 0.3 * math.sin((xx + off) * freq * 2.7 + 1 + seed)))
    pts.append((W + 500, base or H + 600))
    poly(c, pts, colr)


def _tiles(off, tile, lo=-560, hi=W + 560):
    k0 = math.floor((lo - off) / tile)
    return [off + k * tile for k in range(k0, k0 + int((hi - lo) / tile) + 2)]


def city(c, off, base, colr, win, seed=4, tile=1400, a=1.0):
    """Far blocks of flats with a few lit windows."""
    rng = np.random.default_rng(seed)
    blocks, x = [], 0.0
    while x < tile:
        w, h = 110 + 120 * rng.random(), 180 + 260 * rng.random()
        blocks.append((x, w, h, rng.random(4 * 12)))
        x += w + 10 + 30 * rng.random()
    for ox in _tiles(off, tile):
        for bx, w, h, lit in blocks:
            rect(c, ox + bx, base - h, w, h + 400, colr, a)
            for j in range(4):
                for k in range(int(h // 64)):
                    if lit[(j * 12 + k) % len(lit)] > 0.72:
                        rect(c, ox + bx + 14 + j * (w - 28) / 4, base - h + 24 + k * 64, 14, 22, win, 0.85 * a)


def houses(c, off, base, colr, win, seed=7, tile=1500):
    """Gabled houses in silhouette with warm windows."""
    rng = np.random.default_rng(seed)
    hs, x = [], 0.0
    while x < tile:
        w, h = 230 + 140 * rng.random(), 190 + 120 * rng.random()
        hs.append((x, w, h, rng.random() < 0.7, rng.random() < 0.6))
        x += w + 60 + 120 * rng.random()
    for ox in _tiles(off, tile):
        for hx, w, h, l1, l2 in hs:
            x0 = ox + hx
            rect(c, x0, base - h, w, h + 400, colr)
            poly(c, [(x0 - 18, base - h + 2), (x0 + w / 2, base - h - w * 0.36), (x0 + w + 18, base - h + 2)], colr)
            for k, on in enumerate((l1, l2)):
                wx, wy = x0 + w * (0.22 + 0.4 * k), base - h * 0.62
                if on:
                    glow(c, wx + 24, wy + 30, 90, win, 0.3)
                rect(c, wx, wy, 48, 60, win if on else mix(colr, '#000000', 0.3), 0.95)
                line(c, wx + 24, wy, wx + 24, wy + 60, colr, w=4, cap='butt')


def trees(c, off, base, colr, seed=9, tile=1300, s=1.0):
    """Round, puffy trees in silhouette."""
    rng = np.random.default_rng(seed)
    ts, x = [], 0.0
    while x < tile:
        ts.append((x, (0.8 + 0.5 * rng.random()) * s, rng.random()))
        x += 260 + 260 * rng.random()
    for ox in _tiles(off, tile):
        for tx, k, ph in ts:
            x0 = ox + tx
            line(c, x0, base, x0, base - 150 * k, colr, w=16 * k)
            line(c, x0, base - 100 * k, x0 - 40 * k, base - 170 * k, colr, w=9 * k)
            line(c, x0, base - 120 * k, x0 + 44 * k, base - 190 * k, colr, w=9 * k)
            for dx, dy, r in ((0, -260, 92), (-70, -210, 72), (72, -205, 74), (-30, -300, 70), (40, -300, 66)):
                circ(c, x0 + dx * k, base + dy * k, r * k, colr)


def streetlamp(c, x, base, pal, h=420):
    line(c, x, base, x, base - h, '#141230', w=12)
    line(c, x, base - h, x + 54, base - h - 10, '#141230', w=10)
    glow(c, x + 64, base - h + 4, 200, pal['lamp'], 0.5)
    oval(c, x + 64, base - h + 2, 26, 12, mix(pal['lamp'], '#FFFFFF', 0.5))
    beam(c, [(x + 44, base - h + 8), (x + 84, base - h + 8), (x + 190, base + 30), (x - 62, base + 30)], pal['lamp'], 0.14, 16)


def tear_calendar(c, x, y, t, schedule, w=520, h=600):
    """A tear-off day calendar; schedule(t) -> (day, seconds since it changed)."""
    n, since = schedule(t)
    rect(c, x - w / 2 + 14, y - h / 2 + 22, w, h, '#000000', 0.45, blur=22)

    def page(num, a=1.0):
        grr(c, x - w / 2, y - h / 2, w, h, 16, ('#FFF8EE', '#E9DCCB'), a=a)
        grr(c, x - w / 2, y - h / 2, w, 132, 16, ('#D9443A', '#A8282A'), a=a)
        rect(c, x - w / 2, y - h / 2 + 100, w, 32, '#A8282A', a)
        spaced(c, 'DAY', x, y - h / 2 + 92, 60, '#FFF3EC', a, 'pop', 10)
        text(c, str(num), x, y + 150, 250 if num < 100 else 210, '#241B22', a, tf='pop')

    page(n)
    if n > 1 and since < 0.45:
        u = since / 0.45
        c.save()
        c.translate(x + 380 * u, y - 520 * u * u - 60 * u)
        c.rotate(35 * u)
        c.translate(-x, -y)
        page(n - 1, 1 - u)
        c.restore()
    for i in range(5):
        rrect(c, x - w / 2 + 50 + i * (w - 100) / 4 - 9, y - h / 2 - 26, 18, 52, 9, '#3A2A26')


# ---------------------------------------------------------------- build
def thumbnail(ep, tl, out):
    """A frame with no text at all (GJ's best Shorts had text-free thumbnails)."""
    from PIL import Image
    tt = ep.THUMB_T(tl) if callable(ep.THUMB_T) else ep.THUMB_T
    TEXT_ON[0] = False
    try:
        f = kit.render(tl, ep.SCENES, None, frames_at=[tt])[0]
    finally:
        TEXT_ON[0] = True
    im = Image.fromarray(f)
    if getattr(ep, 'THUMB_CROP', None):
        im = im.crop(ep.THUMB_CROP).resize((W, H), Image.LANCZOS)
    p = os.path.join(out, 'thumb.png')
    im.save(p)
    return p


def build(ep, stills=False, frames=None, only=None):
    t0 = time.time()
    name = ep.NAME + OUT_TAG[0]
    CAP_LOOK[0] = getattr(ep, 'CAPTIONS', 'gold')
    out = os.path.join(HERE, 'build', name)
    os.makedirs(out, exist_ok=True)
    tl, segs = timeline(ep.SCRIPT, out)
    json.dump(tl, open(os.path.join(out, 'timeline.json'), 'w'), indent=1)
    if stills or frames:
        if stills:
            print('wrote', kit.contact_sheet(tl, ep.SCENES, os.path.join(out, 'stills.png'), cols=4, thumb=(270, 480), when='late'))
        if frames:
            from PIL import Image
            for tt, f in zip(frames, kit.render(tl, ep.SCENES, None, frames_at=frames)):
                p = os.path.join(out, f'frame_{tt:.2f}.png')
                Image.fromarray(f).save(p)
                print('wrote', p)
        return tl
    wav = soundtrack(tl, segs, ep.SCORE, getattr(ep, 'SFX', None), out)
    kit.render(tl, ep.SCENES, os.path.join(out, 'scenes'), only=only)
    mp4 = kit.concat_and_mux(os.path.join(out, 'scenes'), wav, os.path.join(out, name + '.mp4'))
    if getattr(ep, 'THUMB_T', None) is not None:
        thumbnail(ep, tl, out)
    print('DONE', mp4, f'{tl["duration"]:.2f} s video in {time.time() - t0:.0f} s')
    return tl
