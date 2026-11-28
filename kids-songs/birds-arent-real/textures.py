"""Textures for Birds Aren't Real, drawn with Pillow: evidence-board papers, protest signs, the billboard, the CRT and phone screens."""
import paths  # noqa: F401  (sibling props on sys.path)
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
DEJAVU = '/usr/share/fonts/truetype/dejavu'


def F(name, size):
    p = {'type': os.path.join(FONTS, 'SpecialElite-Regular.ttf'), 'marker': os.path.join(FONTS, 'PermanentMarker-Regular.ttf'),
         'anton': os.path.join(FONTS, 'Anton-Regular.ttf'), 'sans': os.path.join(DEJAVU, 'DejaVuSans.ttf'),
         'sansb': os.path.join(DEJAVU, 'DejaVuSans-Bold.ttf'), 'mono': os.path.join(DEJAVU, 'DejaVuSansMono.ttf'),
         'monob': os.path.join(DEJAVU, 'DejaVuSansMono-Bold.ttf'), 'serifb': os.path.join(DEJAVU, 'DejaVuSerif-Bold.ttf'),
         'serif': os.path.join(DEJAVU, 'DejaVuSerif.ttf')}[name]
    return ImageFont.truetype(p, size)


def paper(w, h, tone=(236, 230, 214), seed=0, age=0.5):
    r = np.random.default_rng(seed)
    a = np.ones((h, w, 3)) * np.array(tone, float)
    n = r.normal(0, 4, (h // 8 + 1, w // 8 + 1))
    n = np.array(Image.fromarray(n.astype(np.float32)).resize((w, h), Image.BILINEAR))
    a += n[..., None]
    y, x = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(x, w - 1 - x), np.minimum(y, h - 1 - y)) / (0.12 * min(w, h))
    a *= (0.86 + 0.14 * np.clip(edge, 0, 1))[..., None] * (1 - 0.06 * age)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def wrap_text(d, text, font, maxw):
    words, lines, cur = text.split(), [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if not cur or d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = wd
    if cur:
        lines.append(cur)
    return lines


def circle_mark(d, box, col=(200, 20, 20), w=7, seed=0):
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts = []
    for k in range(70):
        t = 2 * math.pi * k / 60 + 0.3
        jit = 1 + 0.04 * math.sin(3 * t + seed) + r.normal(0, 0.01)
        pts.append((cx + rx * jit * math.cos(t), cy + ry * jit * math.sin(t)))
    d.line(pts, fill=col, width=w, joint='curve')


# ------------------------------------------------------------------ board items
def sticky(text, col=(250, 224, 80), seed=0, size=52):
    im = Image.new('RGB', (300, 300), col)
    a = np.asarray(im).astype(float)
    y = np.mgrid[0:300, 0:300][0]
    a *= (1 - 0.10 * (y / 300))[..., None]
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    f = F('marker', size)
    lines = wrap_text(d, text, f, 250)
    h = len(lines) * size * 1.1
    for i, ln in enumerate(lines):
        d.text((150, 150 - h / 2 + i * size * 1.1 + size * 0.55), ln, font=f, fill=(25, 25, 60), anchor='mm')
    return im


def pigeon_silhouette(d, cx, cy, s, fill):
    """A simple side-on pigeon shape facing left, s = body length in px."""
    d.ellipse([cx - 0.45 * s, cy - 0.22 * s, cx + 0.35 * s, cy + 0.2 * s], fill=fill)
    d.ellipse([cx - 0.62 * s, cy - 0.42 * s, cx - 0.32 * s, cy - 0.12 * s], fill=fill)
    d.polygon([(cx - 0.62 * s, cy - 0.30 * s), (cx - 0.76 * s, cy - 0.25 * s), (cx - 0.60 * s, cy - 0.22 * s)], fill=fill)
    d.polygon([(cx + 0.25 * s, cy - 0.12 * s), (cx + 0.75 * s, cy + 0.02 * s), (cx + 0.30 * s, cy + 0.14 * s)], fill=fill)
    d.line([(cx - 0.05 * s, cy + 0.18 * s), (cx - 0.08 * s, cy + 0.40 * s)], fill=fill, width=max(2, int(s * 0.04)))
    d.line([(cx + 0.08 * s, cy + 0.18 * s), (cx + 0.07 * s, cy + 0.40 * s)], fill=fill, width=max(2, int(s * 0.04)))


def header_card():
    im = paper(1100, 300, (238, 234, 222), 1)
    d = ImageDraw.Draw(im)
    d.text((550, 140), "BIRDS AREN'T REAL", font=F('marker', 92), fill=(25, 25, 30), anchor='mm')
    d.line([(120, 245), (980, 238)], fill=(190, 20, 20), width=9)
    return im


def us_map():
    im = paper(560, 420, (236, 232, 214), 2)
    d = ImageDraw.Draw(im)
    d.text((280, 34), 'BILLBOARDS', font=F('anton', 40), fill=(40, 40, 40), anchor='mm')
    poly = [(40, 110), (120, 80), (300, 92), (430, 84), (520, 70), (530, 120), (500, 180), (470, 250), (480, 320), (450, 330),
            (420, 280), (330, 300), (280, 350), (230, 300), (150, 300), (80, 260), (50, 200)]
    d.polygon(poly, fill=(214, 196, 160))
    d.line(poly + [poly[0]], fill=(60, 50, 40), width=4)
    for (x, y, name, lx, ly) in ((70, 225, 'LA', 110, 262), (360, 245, 'MEMPHIS', 330, 290), (455, 140, 'PITTSBURGH', 400, 185)):
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(190, 20, 20))
        d.text((lx, ly), name, font=F('marker', 26), fill=(190, 20, 20), anchor='mm')
    return im


def satire_paper():
    """Newspaper clipping with an invented masthead."""
    im = paper(640, 760, (232, 228, 214), 3, 0.4)
    d = ImageDraw.Draw(im)
    d.text((320, 52), 'THE DAILY LEDGER', font=F('serifb', 50), fill=(20, 20, 20), anchor='mm')
    d.line([(30, 92), (610, 92)], fill=(30, 30, 30), width=3)
    d.text((320, 112), 'THURSDAY, DECEMBER 9, 2021', font=F('serif', 20), fill=(60, 60, 60), anchor='mm')
    d.line([(30, 130), (610, 130)], fill=(30, 30, 30), width=2)
    d.text((320, 205), 'IT WAS SATIRE', font=F('anton', 92), fill=(15, 15, 15), anchor='mm')
    f = F('serifb', 25)
    y = 270
    for ln in wrap_text(d, "‘Birds Aren’t Real’ founder breaks character: the movement was a joke all along", f, 560):
        d.text((320, y), ln, font=f, fill=(35, 35, 35), anchor='mt'); y += 34
    r = np.random.default_rng(5)
    for col in range(2):
        x0 = 36 + col * 292
        yy = y + 24
        while yy < 730:
            w_ = 270 if r.random() > 0.15 else int(r.uniform(90, 230))
            d.rectangle([x0, yy, x0 + w_, yy + 7], fill=(150, 146, 136)); yy += 17
    circle_mark(d, (330, 150, 600, 262), seed=7, w=7)
    return im


def blueprint():
    w, h = 600, 440
    a = np.zeros((h, w, 3)); a[:] = (24, 60, 128)
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 30):
        d.line([(x, 0), (x, h)], fill=(40, 80, 150), width=1)
    for y in range(0, h, 30):
        d.line([(0, y), (w, y)], fill=(40, 80, 150), width=1)
    d.text((300, 36), 'PIGEON DRONE  MK II', font=F('monob', 34), fill=(230, 240, 255), anchor='mm')
    pigeon_silhouette(d, 300, 240, 300, None) if False else None
    cx, cy, s = 300, 250, 300
    d.ellipse([cx - 0.45 * s, cy - 0.22 * s, cx + 0.35 * s, cy + 0.2 * s], outline=(230, 240, 255), width=4)
    d.ellipse([cx - 0.62 * s, cy - 0.42 * s, cx - 0.32 * s, cy - 0.12 * s], outline=(230, 240, 255), width=4)
    d.line([(cx + 0.30 * s, cy - 0.08 * s), (cx + 0.72 * s, cy + 0.04 * s), (cx + 0.32 * s, cy + 0.12 * s)], fill=(230, 240, 255), width=4)
    d.ellipse([cx - 0.52 * s - 9, cy - 0.30 * s - 9, cx - 0.52 * s + 9, cy - 0.30 * s + 9], fill=(255, 60, 60))
    d.rectangle([cx - 0.15 * s, cy - 0.08 * s, cx + 0.10 * s, cy + 0.06 * s], outline=(230, 240, 255), width=3)
    for (x0, y0, x1, y1, lab) in ((cx - 0.52 * s, cy - 0.30 * s, 90, 120, 'CAMERA'), (cx - 0.02 * s, cy - 0.01 * s, 420, 120, 'BATTERY'),
                                  (cx + 0.1 * s, cy + 0.15 * s, 430, 390, 'GPS')):
        d.line([(x0, y0), (x1, y1)], fill=(230, 240, 255), width=2)
        d.text((x1, y1 + (-16 if y1 < 200 else 16)), lab, font=F('monob', 24), fill=(230, 240, 255), anchor='mm')
    return im


def logo_clip():
    im = paper(620, 400, (246, 246, 244), 6, 0.2)
    d = ImageDraw.Draw(im)
    d.text((310, 50), 'JULY 2023', font=F('anton', 44), fill=(190, 30, 30), anchor='mm')
    f = F('anton', 64)
    d.text((310, 140), 'BIRD LOGO', font=f, fill=(20, 20, 20), anchor='mm')
    d.text((310, 215), 'RETIRED', font=f, fill=(20, 20, 20), anchor='mm')
    fs = F('serif', 24)
    y = 280
    for ln in wrap_text(d, 'Twitter renames itself and drops its famous bird.', fs, 540):
        d.text((310, y), ln, font=fs, fill=(70, 70, 70), anchor='mt'); y += 32
    circle_mark(d, (110, 95, 510, 255), seed=9, w=6)
    return im


def protest_flyer():
    im = paper(520, 400, (244, 244, 240), 8, 0.3)
    d = ImageDraw.Draw(im)
    d.text((260, 60), 'PROTEST AT HQ', font=F('anton', 58), fill=(25, 25, 25), anchor='mm')
    d.text((260, 130), 'San Francisco, 2021', font=F('type', 30), fill=(60, 60, 60), anchor='mm')
    d.text((260, 225), 'DROP THE BIRD', font=F('anton', 64), fill=(190, 30, 30), anchor='mm')
    d.text((260, 320), 'every bird is a drone', font=F('marker', 34), fill=(25, 25, 60), anchor='mm')
    return im


def wire_photo(w=480, h=340):
    a = np.zeros((h, w, 3))
    yv = np.linspace(0, 1, h)[:, None]
    a[:] = (np.array([170, 200, 225]) * (1 - yv) + np.array([215, 225, 230]) * yv)[:, None, :][:, 0][:, None, :]
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for k, yy in enumerate((150, 190)):
        d.line([(0, yy - 12), (w / 2, yy + 8), (w, yy - 12)], fill=(40, 40, 45), width=3)
    for k in range(6):
        x = 50 + k * 72
        pigeon_silhouette(d, x, 128 + abs(x - w / 2) * -0.06 + 12, 52, (55, 58, 66))
    frame = Image.new('RGB', (w + 40, h + 70), (238, 236, 228))
    frame.paste(im.filter(ImageFilter.GaussianBlur(0.8)), (20, 20))
    ImageDraw.Draw(frame).text(((w + 40) / 2, h + 45), 'CHARGING??', font=F('marker', 34), fill=(190, 20, 20), anchor='mm')
    return frame


def billion_card():
    im = paper(560, 300, (246, 244, 236), 4, 0.3)
    d = ImageDraw.Draw(im)
    d.text((280, 110), '12,000,000,000', font=F('anton', 76), fill=(190, 30, 30), anchor='mm')
    d.text((280, 200), 'birds replaced, 1959-2001', font=F('type', 30), fill=(40, 40, 40), anchor='mm')
    return im


BOARD_ITEMS = {
    'p_header': header_card, 'p_cal': us_map, 'p_clip': satire_paper, 'p_farm': blueprint, 'p_shrimp': wire_photo,
    'p_quote': logo_clip, 'p_forum': protest_flyer, 'p_stat': billion_card,
    'p_q': lambda: sticky('?', (255, 150, 170), 12, 220),
    'n_who': lambda: sticky('IF IT FLIES IT SPIES', (250, 224, 80), 1, 44), 'n_bots': lambda: sticky('TRACKING DEVICE?', (255, 150, 170), 2, 44),
    'n_2016': lambda: sticky('2017', (150, 230, 160), 3, 72), 'n_likes': lambda: sticky('WAKE UP', (250, 224, 80), 4, 60),
    'n_amen': lambda: sticky('WHO IS WATCHING?', (140, 200, 255), 5, 42),
}


# ------------------------------------------------------------------ signs, billboard, screens
def placard(text, w=620, h=420, tone=(226, 200, 160), ink=(20, 20, 24), seed=0, size=96):
    """Cardboard protest sign, hand-lettered."""
    im = paper(w, h, tone, seed, 0.6)
    d = ImageDraw.Draw(im)
    f = F('marker', size)
    lines = wrap_text(d, text, f, w - 60)
    lh = size * 1.08
    y0 = h / 2 - len(lines) * lh / 2 + lh / 2
    for i, ln in enumerate(lines):
        d.text((w / 2, y0 + i * lh), ln, font=f, fill=ink, anchor='mm')
    return im


def billboard_tex(w=1500, h=500):
    im = Image.new('RGB', (w, h), (245, 245, 240))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, h], outline=(20, 20, 20), width=14)
    d.text((w * 0.40, h * 0.5), "BIRDS AREN'T REAL", font=F('anton', 150), fill=(18, 18, 18), anchor='mm')
    pigeon_silhouette(d, w * 0.87, h * 0.55, 190, (18, 18, 18))
    d.ellipse([w * 0.87 - 0.52 * 190 - 9, h * 0.55 - 0.30 * 190 - 9, w * 0.87 - 0.52 * 190 + 9, h * 0.55 - 0.30 * 190 + 9], fill=(220, 30, 30))
    return im


def crt_news(w=640, h=480):
    """The CRT: a news channel showing a pigeon, with a lower third."""
    a = np.zeros((h, w, 3))
    yv = np.linspace(0, 1, h)[:, None]
    a[:] = (np.array([120, 160, 200]) * (1 - yv) + np.array([200, 215, 225]) * yv)[:, None, :][:, 0][:, None, :]
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.line([(0, 250), (w, 230)], fill=(40, 40, 45), width=4)
    pigeon_silhouette(d, 320, 190, 190, (70, 74, 84))
    d.ellipse([320 - 0.52 * 190 - 6, 190 - 0.30 * 190 - 6, 320 - 0.52 * 190 + 6, 190 - 0.30 * 190 + 6], fill=(230, 30, 30))
    d.rectangle([0, 360, w, 440], fill=(20, 24, 40))
    d.rectangle([0, 360, 170, 440], fill=(190, 30, 30))
    d.text((85, 400), 'LIVE', font=F('anton', 48), fill=(255, 255, 255), anchor='mm')
    d.text((190, 380), 'ARE BIRDS DRONES?', font=F('sansb', 30), fill=(255, 255, 255), anchor='lm')
    d.text((190, 418), 'protesters say yes', font=F('sans', 22), fill=(200, 200, 210), anchor='lm')
    d.rectangle([w - 110, 20, w - 20, 56], fill=(190, 30, 30))
    d.text((w - 65, 38), 'LIVE', font=F('sansb', 22), fill=(255, 255, 255), anchor='mm')
    return im


def phone_feed(w=720, h=1480):
    H = 2400
    im = Image.new('RGB', (w, H), (24, 25, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 90], fill=(32, 34, 42))
    d.text((w / 2, 45), '#birdsarentreal', font=F('sansb', 34), fill=(235, 235, 240), anchor='mm')
    y = 120
    posts = ['If it flies, it spies.', 'saw one charging on a power line today', 'my car got tagged AGAIN',
             'they replaced 12 billion of them', 'wake up', 'birds are real (they made me say this)']
    r = np.random.default_rng(3)
    for k in range(12):
        col = tuple(int(v) for v in r.integers(70, 200, 3))
        d.ellipse([36, y, 100, y + 64], fill=col)
        d.text((120, y + 4), '@user' + str(int(r.integers(100, 999))), font=F('sansb', 26), fill=(200, 200, 210))
        for ln in wrap_text(d, posts[k % len(posts)], F('sans', 30), w - 160):
            y += 40
            d.text((120, y), ln, font=F('sans', 30), fill=(235, 235, 240))
        y += 90
        d.line([(0, y - 20), (w, y - 20)], fill=(50, 52, 60), width=2)
    return im


SIGNS = {'sign_real': ("BIRDS AREN'T REAL", (226, 200, 160), 0, 92), 'sign_spies': ('IF IT FLIES, IT SPIES', (245, 240, 225), 1, 84),
         'sign_drop': ('DROP THE BIRD', (250, 220, 90), 2, 100), 'sign_wake': ('WAKE UP', (226, 200, 160), 3, 120),
         'sign_drones': ('BIRDS = DRONES', (245, 240, 225), 4, 96)}


def build_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for k, fn in BOARD_ITEMS.items():
        fn().save(os.path.join(out_dir, k + '.png'))
    for k, (text, tone, seed, size) in SIGNS.items():
        placard(text, tone=tone, seed=seed, size=size).save(os.path.join(out_dir, k + '.png'))
    billboard_tex().save(os.path.join(out_dir, 'billboard.png'))
    crt_news().save(os.path.join(out_dir, 'crt.png'))
    phone_feed().save(os.path.join(out_dir, 'post.png'))


if __name__ == '__main__':
    build_all(os.path.join(HERE, 'build', 'tex'))
    print('ok')
