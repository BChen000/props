"""Thumbnail from the two hero renders: top team's scene above a glowing diagonal seam, the other below.

No text by default (the channel's best Shorts had text-free thumbnails, and the title already asks
the question). `--text` adds the team names with an "or" pill.
  python3 thumb.py            -> build/out/thumbnail.jpg
  python3 thumb.py --text     -> build/out/thumbnail_text.jpg
"""
import math
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import settings
import post as P

W, H = P.W, P.H


def compose(png, mood, t, dy=0):
    bg = P.BG[mood].copy()
    bk = np.zeros((H // 2, W // 2, 3), np.float32)
    for b in P.bok:
        x = (b['x'] + b['ax'] * math.sin(2 * math.pi * b['k1'] * t / P.T + b['p1'])) / 2
        y = (b['y'] + b['ay'] * math.sin(2 * math.pi * b['k2'] * t / P.T + b['p2'])) / 2
        P.blit_add(bk, P.disc_sprite(b['r'] / 2, 2.5), x, y, b['c'], b['s'] * 1.2)
    bk = np.asarray(Image.fromarray(np.clip(bk, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
    bg = 255 - (255 - bg) * (255 - bk) / 255.0
    src = Image.open(png).convert('RGBa')
    shifted = Image.new('RGBa', (W, H), (0, 0, 0, 0))
    shifted.paste(src, (0, dy))
    arr = np.asarray(shifted, np.float32)
    A = arr[..., 3:4] / 255.0
    img = arr[..., :3] + bg * (1 - A)
    mx = img.max(axis=2, keepdims=True)
    bright = img * np.clip((mx - 160) / 95.0, 0, 1) ** 1.3
    small = Image.fromarray(np.clip(bright, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BOX)
    b1 = np.asarray(small.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), np.float32)
    b2 = np.asarray(small.filter(ImageFilter.GaussianBlur(16)).resize((W, H), Image.BILINEAR), np.float32)
    img = img + 0.85 * b1 + 0.6 * b2
    img = img * P.VIG
    for s in P.snow:
        P.blit_over(img, P.disc_sprite(s['r'] * 1.2, 1.6), s['x'], s['y'], (255, 255, 255), s['a'])
    return np.clip(img, 0, 255)


def big_text(txt, size, fill, stroke=12, rot=0.0, wght=900):
    f = P.font(size, wght)
    bb = f.getbbox(txt, stroke_width=stroke)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = 60
    lay = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1] + 14), txt, font=f, fill=(0, 0, 0, 200), stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    gl = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=fill + (255,), stroke_width=stroke + 10, stroke_fill=fill + (255,))
    lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22)))
    ImageDraw.Draw(lay).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=(255, 255, 255, 255))
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    return lay


def fitted(txt, size, wght=900, stroke=12, max_w=980):
    while size > 60 and P.font(size, wght).getbbox(txt, stroke_width=stroke)[2] > max_w:
        size -= 8
    return size


def put(canvas, lay, cx, cy):
    canvas.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


if __name__ == '__main__':
    text = '--text' in sys.argv
    tp, bt = settings.THUMB['top'], settings.THUMB['bottom']
    top = compose(os.path.join(settings.THUMBS, 'hero_top.png'), tp['mood'], tp['t'], dy=tp['dy'])
    bot = compose(os.path.join(settings.THUMBS, 'hero_bottom.png'), bt['mood'], bt['t'], dy=bt['dy'])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sd = yy - (1085 - (xx / W) * 250)
    mask = np.clip(sd / 6 + 0.5, 0, 1)[..., None]
    img = top * (1 - mask) + bot * mask
    img = img + np.exp(-(sd / 6) ** 2)[..., None] * 255 * 0.9 + np.exp(-(sd / 34) ** 2)[..., None] * np.array([255, 245, 220], np.float32) * 0.3
    img = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
    if text:
        rounds = {r['k']: r for r in P.rounds}
        t_team, b_team = rounds[tp['round']]['team'], rounds[bt['round']]['team']
        put(img, big_text(t_team, fitted(t_team, 170), settings.TEAMS[t_team], rot=3), W / 2, 250)
        put(img, big_text(b_team + '?', fitted(b_team + '?', 190), settings.TEAMS[b_team], rot=3), W / 2, 1600)
        f = P.font(84, 900)
        pill = Image.new('RGBA', (300, 150), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([20, 20, 280, 130], radius=55, fill=(18, 16, 24, 235), outline=(255, 255, 255, 255), width=6)
        bb = f.getbbox('or')
        pd.text((150 - (bb[2] - bb[0]) / 2 - bb[0], 75 - (bb[3] - bb[1]) / 2 - bb[1]), 'or', font=f, fill=(255, 255, 255, 255))
        put(img, pill.rotate(10, resample=Image.BICUBIC, expand=True), W / 2, 955)
    os.makedirs(settings.OUT, exist_ok=True)
    out = os.path.join(settings.OUT, 'thumbnail_text.jpg' if text else 'thumbnail.jpg')
    img.convert('RGB').save(out, quality=94)
    print('wrote', out)
