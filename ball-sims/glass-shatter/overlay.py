import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIR = os.path.expanduser('~/.fonts')
F_NUM = os.path.join(FONT_DIR, 'Poppins-ExtraBold.ttf')
F_LBL = os.path.join(FONT_DIR, 'Poppins-Bold.ttf')
W, H = 1080, 1920
CY = 250
NUM_SIZE = 150
LBL_SIZE = 50
POP_FRAMES = 9
GOLD = (255, 205, 70)
_cache = {}


def font(path, size):
    k = (path, size)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(path, size)
    return _cache[k]


def ease_out_back(t, s=2.2):
    t = min(max(t, 0.0), 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


def text_layer(txt, size, fpath, color, outline=(20, 18, 40), ow=6, scale=1.0, alpha=1.0, letter=0):
    fs = max(8, int(size * scale))
    f = font(fpath, fs)
    l, t, r, b = f.getbbox(txt, stroke_width=ow)
    tw = r - l + letter * max(0, len(txt) - 1)
    th = b - t
    pad = 40
    im = Image.new('RGBA', (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if letter:
        x = pad - l
        for ch in txt:
            d.text((x, pad - t), ch, font=f, fill=color + (255,), stroke_width=ow, stroke_fill=outline + (255,))
            x += f.getlength(ch) + letter
    else:
        d.text((pad - l, pad - t), txt, font=f, fill=color + (255,), stroke_width=ow, stroke_fill=outline + (255,))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sa = im.split()[3].filter(ImageFilter.GaussianBlur(10 * scale + 2))
    sh.putalpha(sa.point(lambda v: int(v * 0.55)))
    out = Image.new('RGBA', (im.width + 16, im.height + 16), (0, 0, 0, 0))
    out.alpha_composite(sh, (12, 14))
    out.alpha_composite(im, (4, 4))
    if alpha < 1:
        a = out.split()[3].point(lambda v: int(v * alpha))
        out.putalpha(a)
    return out


def draw_counter(frame, label, n_faces, t_since, fade=1.0, gold=False, unit=None):
    pop = ease_out_back(t_since / POP_FRAMES) if t_since < POP_FRAMES else 1.0
    sc = 0.55 + 0.45 * pop
    al = min(1.0, 0.25 + t_since / 4.0) * fade
    col = GOLD if gold else (255, 255, 255)
    num = text_layer(label, NUM_SIZE, F_NUM, col, scale=sc, alpha=al, ow=max(3, int(7 * sc)))
    word = unit if unit else ('FACE' if n_faces == 1 else 'FACES')
    lbl = text_layer(word, LBL_SIZE, F_LBL, (255, 255, 255), scale=0.8 + 0.2 * pop, alpha=al * 0.95, ow=4, letter=6)
    frame.alpha_composite(num, (W // 2 - num.width // 2, CY - num.height // 2))
    frame.alpha_composite(lbl, (W // 2 - lbl.width // 2, CY + int(NUM_SIZE * 0.52) - lbl.height // 2 + 18))
    return frame


def schedule(tl):
    out = []
    labels = tl['labels']
    for si, L in enumerate(tl['stage_len']):
        for f in range(L):
            out.append((si, f, 1.0))
    R = tl.get('refill_len', 0)
    for f in range(R):
        out.append((len(labels) - 1, tl['stage_len'][-1] + f, max(0.0, 1 - f / (R * 0.6))))
    return out


def apply(frame_png, g, tl, out_png):
    sch = schedule(tl)
    si, f, fade = sch[g]
    im = Image.open(frame_png).convert('RGBA')
    draw_counter(im, tl['labels'][si], tl['counts'][si], f, fade=fade, gold=(si == len(tl['labels']) - 1), unit=tl.get('unit'))
    im.convert('RGB').save(out_png)


if __name__ == '__main__':
    tl = json.load(open(sys.argv[1]))
    src, dst = sys.argv[2], sys.argv[3]
    a, b = int(sys.argv[4]), int(sys.argv[5])
    os.makedirs(dst, exist_ok=True)
    for g in range(a, b):
        p = f'{src}/f_{g:04d}.png'
        if os.path.exists(p):
            apply(p, g, tl, f'{dst}/f_{g:04d}.png')
