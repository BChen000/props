"""YouTube channel banner (2560x1440): the hooded man at his evidence board, a title on the right.
Everything that matters sits in YouTube's centre safe area (1546x423). Needs build/assets.npz (build_all.py) and fonts/.

  python3 banner.py      -> build/banner/channel_banner.png, .jpg and preview.png (TV, desktop and phone crops)
  BANNER_TITLE='CONSPIRACY|THEORIES' BANNER_SUB='explained by a man with no face' python3 banner.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: F401  (sibling props on sys.path)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import meshkit, shots, post
from glr import Renderer

# ------------------------------------------------------------------ settings
TITLE = os.environ.get('BANNER_TITLE', 'CONSPIRACY|THEORIES').split('|')   # one or two lines; no channel name yet (rebrand pending)
SUB = os.environ.get('BANNER_SUB', 'explained by a man with no face')
BUILD = os.path.join(HERE, 'build')
OUT = os.path.join(BUILD, 'banner')

W, H = 2560, 1440
SAFE = (W - 1546) // 2, (H - 423) // 2, (W + 1546) // 2, (H + 423) // 2
parts = meshkit.load(os.path.join(BUILD, 'assets.npz'))
R = Renderer(W, H)
R.add_meshes(parts)
texwh = {}
for fn in os.listdir(os.path.join(BUILD, 'tex')):
    im = np.asarray(Image.open(os.path.join(BUILD, 'tex', fn)).convert('RGB'))
    R.add_texture(fn[:-4], im); texwh[fn[:-4]] = (im.shape[1], im.shape[0])
shots.GLOBAL.update(R=R, parts=parts, texwh=texwh, env=None)
c = dict(eye=(0.52, -3.5, 1.63), target=(0.52, 0.0, 1.63), fov=24)
fd = shots.room_frame(10.0, 10.0, c, [(0, dict(head=(1, 6, -3)))], dict(dof=2.0, focus=3.5, grain=0.012, vignette=0.35))
img = R.render(fd['items'], fd['cam'], fd['lights'], fd['env'], fd['adds'])
out = Image.fromarray(post.finish(img, fd['post'], 0))
# darken behind the title for legibility
grad = np.zeros((H, W), np.float32)
x = np.arange(W)
grad[:] = np.clip((x - 980) / 480, 0, 1) * 0.62
y = np.arange(H)[:, None]
grad *= np.clip(1 - np.abs(y - H / 2) / 520, 0, 1) ** 0.7
a = np.asarray(out).astype(np.float32) * (1 - grad[..., None])
out = Image.fromarray(a.astype(np.uint8))
d = ImageDraw.Draw(out)
F = lambda n, s: ImageFont.truetype(os.path.join(HERE, 'fonts', n), s)
title = F('Anton-Regular.ttf', 150)
tx = 1150
lines = [(t, (240, 233, 218)) for t in TITLE]
y0 = SAFE[1] + 6
ys = []
for k, (t, col) in enumerate(lines):
    bb = d.textbbox((tx, 0), t, font=title)
    ys.append(y0 - bb[1] + k * 158)
shadow = Image.new('L', (W, H), 0)
sd = ImageDraw.Draw(shadow)
for (t, col), y in zip(lines, ys):
    sd.text((tx + 8, y + 10), t, font=title, fill=200)
out.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(10)))
d = ImageDraw.Draw(out)
tw = 0
for (t, col), y in zip(lines, ys):
    d.text((tx, y), t, font=title, fill=col)
    tw = max(tw, d.textlength(t, font=title))
bottom = d.textbbox((tx, ys[-1]), lines[-1][0], font=title)[3]
yl = bottom + 22
d.line([(tx + 4, yl), (tx + tw * 0.55, yl - 6), (tx + tw - 4, yl + 2)], fill=(185, 22, 22), width=7, joint='curve')
for px, dy in ((tx + 4, 0), (tx + tw - 4, 2)):
    d.ellipse([px - 11, yl - 11 + dy, px + 11, yl + 11 + dy], fill=(200, 30, 30))
sub = F('SpecialElite-Regular.ttf', 40)
d.text((tx + 4, yl + 22), SUB, font=sub, fill=(222, 212, 192))
sub_bb = d.textbbox((tx + 4, yl + 22), SUB, font=sub)
print('text box', tx, ys[0], int(max(tx + tw, sub_bb[2])), sub_bb[3], 'safe', SAFE)
os.makedirs(OUT, exist_ok=True)
out.save(os.path.join(OUT, 'channel_banner.png'), optimize=True)
out.convert('RGB').save(os.path.join(OUT, 'channel_banner.jpg'), quality=93)
# previews: TV (full), desktop (centre strip), phone (safe area)
prev = Image.new('RGB', (1280, 720 + 30 + 212 + 30 + 212), (24, 24, 28))
prev.paste(out.resize((1280, 720)), (0, 0))
prev.paste(out.crop((0, SAFE[1], W, SAFE[3])).resize((1280, 212)), (0, 750))
pc = out.crop(SAFE).resize((int(1546 * 212 / 423), 212))
prev.paste(pc, ((1280 - pc.width) // 2, 750 + 242))
prev.save(os.path.join(OUT, 'preview.png'))
print('ok', os.path.getsize(os.path.join(OUT, 'channel_banner.jpg')) // 1024, 'KB jpg')
