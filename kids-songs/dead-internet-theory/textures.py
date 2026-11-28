"""Textures for the Dead Internet set, drawn with Pillow: evidence-board papers, the CRT forum post, phone screens."""
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
def header_card():
    im = paper(1000, 300, (238, 234, 222), 1)
    d = ImageDraw.Draw(im)
    f = F('marker', 104)
    d.text((500, 140), 'DEAD INTERNET', font=f, fill=(25, 25, 30), anchor='mm')
    d.line([(80, 240), (920, 233)], fill=(190, 20, 20), width=9)
    return im


def calendar_2016():
    im = paper(420, 520, (242, 240, 236), 2)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 420, 120], fill=(160, 30, 35))
    d.text((210, 62), '2016', font=F('anton', 92), fill=(250, 245, 240), anchor='mm')
    fs = F('sansb', 22)
    for i, n in enumerate('SMTWTFS'):
        d.text((40 + i * 57, 150), n, font=fs, fill=(80, 80, 80), anchor='mm')
    fn = F('sans', 26)
    day = 1
    for row in range(5):
        for col in range(7):
            if row == 0 and col < 5:
                continue
            if day > 31:
                break
            d.text((40 + col * 57, 200 + row * 62), str(day), font=fn, fill=(40, 40, 40), anchor='mm')
            day += 1
    circle_mark(d, (160, 150, 400, 470), seed=3)
    d.text((300, 495), 'THE END?', font=F('marker', 34), fill=(190, 20, 20), anchor='mm')
    return im


def clipping():
    im = paper(520, 640, (228, 221, 200), 3, 0.8)
    d = ImageDraw.Draw(im)
    d.text((260, 50), 'THE EVENING CIRCUIT', font=F('serifb', 34), fill=(30, 30, 30), anchor='mm')
    d.line([(30, 82), (490, 82)], fill=(30, 30, 30), width=3)
    y = 110
    for ln in wrap_text(d, 'IS ANYONE ONLINE ACTUALLY HUMAN?', F('anton', 64), 460):
        d.text((260, y), ln, font=F('anton', 64), fill=(15, 15, 15), anchor='mt'); y += 70
    fs = F('serif', 17)
    r = np.random.default_rng(4)
    y += 14
    for k in range(13):
        ww = int(r.integers(200, 230)) if k % 5 != 4 else int(r.integers(90, 160))
        for col in (30, 270):
            d.line([(col, y), (col + ww, y)], fill=(90, 90, 85), width=6)
        y += 24
    return im


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


def photo_phonefarm():
    im = Image.new('RGB', (520, 380), (16, 18, 24))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(5)
    for row in range(5):
        for col in range(12):
            x, y = 22 + col * 40, 30 + row * 68
            c = tuple(int(v) for v in r.choice([[90, 200, 255], [120, 240, 200], [255, 255, 255], [70, 140, 255]]))
            d.rectangle([x, y, x + 26, y + 50], fill=(30, 30, 36))
            d.rectangle([x + 3, y + 4, x + 23, y + 44], fill=c)
        d.line([(10, 30 + row * 68 + 54), (510, 30 + row * 68 + 54)], fill=(120, 120, 130), width=4)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    frame = Image.new('RGB', (560, 440), (240, 238, 232))
    frame.paste(im, (20, 20))
    d = ImageDraw.Draw(frame)
    d.text((280, 418), 'phone farm', font=F('type', 24), fill=(60, 60, 60), anchor='mm')
    return frame


def photo_shrimp():
    im = shrimp_image(520, 400)
    frame = Image.new('RGB', (560, 470), (240, 238, 232))
    frame.paste(im, (20, 20))
    d = ImageDraw.Draw(frame)
    d.text((280, 446), '40,000 likes??', font=F('marker', 30), fill=(190, 20, 20), anchor='mm')
    return frame


def shrimp_image(w, h):
    im = Image.new('RGB', (w, h), (120, 190, 220))
    a = np.asarray(im).astype(float)
    y = np.mgrid[0:h, 0:w][0] / h
    a = a * (1 - 0.35 * y[..., None]) + np.array([30, 10, -20]) * y[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(9)
    for _ in range(40):
        x, yy = r.integers(0, w), r.integers(0, h)
        d.ellipse([x - 3, yy - 3, x + 3, yy + 3], fill=(235, 245, 255))
    cx, cy, s = w * 0.5, h * 0.55, min(w, h) / 400
    segs = []
    for k in range(7):
        t = k / 6
        ang = math.pi * (0.15 + 1.05 * t)
        rad = 120 * s * (1 - 0.35 * t)
        segs.append((cx + rad * math.cos(ang) * 1.15, cy - rad * math.sin(ang) * 0.85, 46 * s * (1 - 0.5 * t)))
    for i, (x, yy, rr) in enumerate(segs):
        shade = 1 - 0.08 * (i % 2)
        d.polygon([(x - rr, yy), (x - rr * 0.3, yy - rr), (x + rr * 0.6, yy - rr * 0.8), (x + rr, yy + rr * 0.1),
                   (x + rr * 0.3, yy + rr), (x - rr * 0.6, yy + rr * 0.8)],
                  fill=(int(250 * shade), int(120 * shade), int(95 * shade)), outline=(200, 80, 60))
    x, yy, rr = segs[0]
    d.ellipse([x - 6 * s, yy - rr * 0.5 - 6 * s, x + 6 * s, yy - rr * 0.5 + 6 * s], fill=(20, 20, 20))
    for k in range(2):
        d.line([(x, yy - rr * 0.4), (x + (60 + 30 * k) * s, yy - (120 + 50 * k) * s)], fill=(230, 110, 90), width=max(2, int(3 * s)))
    for k in range(5):
        lx, ly = segs[1 + k // 2][0], segs[1 + k // 2][1]
        d.line([(lx, ly + 20 * s), (lx - 10 * s + k * 4 * s, ly + 55 * s)], fill=(230, 110, 90), width=max(2, int(4 * s)))
    tx, ty, tr = segs[-1]
    d.polygon([(tx, ty), (tx - 40 * s, ty - 30 * s), (tx - 50 * s, ty + 10 * s)], fill=(240, 110, 85))
    return im


def quote_card():
    im = paper(620, 420, (246, 246, 244), 6, 0.2)
    d = ImageDraw.Draw(im)
    d.ellipse([30, 28, 90, 88], fill=(60, 60, 70))
    d.text((110, 34), 'OpenAI CEO', font=F('sansb', 26), fill=(20, 20, 20))
    d.text((110, 64), 'posted Sept 3, 2025', font=F('sans', 20), fill=(110, 110, 110))
    f = F('sans', 30)
    y = 118
    for ln in wrap_text(d, 'i never took the dead internet theory that seriously but it seems like there are really a lot '
                           'of LLM-run twitter accounts now', f, 560):
        d.text((32, y), ln, font=f, fill=(20, 20, 20)); y += 40
    d.line([(36, y + 6), (590, y + 6)], fill=(200, 200, 200), width=2)
    circle_mark(d, (14, 190, 606, 292), seed=8, w=6)
    return im


def forum_print():
    im = paper(600, 440, (244, 244, 240), 7, 0.3)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 600, 54], fill=(60, 70, 110))
    d.text((20, 27), "Agora Road's Macintosh Cafe", font=F('sansb', 22), fill=(240, 240, 255), anchor='lm')
    d.text((24, 80), 'Thread', font=F('sans', 18), fill=(110, 110, 110))
    f = F('sansb', 36)
    y = 110
    for ln in wrap_text(d, 'Dead Internet Theory: Most of the Internet is Fake', f, 550):
        d.text((24, y), ln, font=f, fill=(20, 20, 30)); y += 46
    d.text((24, y + 10), 'IlluminatiPirate  ·  Jan 2021', font=F('sans', 20), fill=(90, 90, 120))
    r = np.random.default_rng(3)
    y += 56
    for k in range(5):
        d.line([(24, y), (24 + int(r.integers(380, 550)), y)], fill=(150, 150, 150), width=7); y += 22
    circle_mark(d, (14, 100, 590, 210), seed=11, w=6)
    return im


def stat_print():
    im = paper(520, 420, (244, 244, 240), 8, 0.3)
    d = ImageDraw.Draw(im)
    d.text((260, 34), 'BOTS: SHARE OF WEB TRAFFIC', font=F('anton', 34), fill=(25, 25, 25), anchor='mm')
    bars = [('2024', 51), ('2025', 53)]                  # bot share of all web traffic (Imperva / Thales reports)
    for i, (yr, v) in enumerate(bars):
        x = 110 + i * 190; h = v * 4.6
        d.rectangle([x, 360 - h, x + 110, 360], fill=(200, 40, 40))
        d.text((x + 55, 345 - h), f'{v}%', font=F('sansb', 26), fill=(40, 40, 40), anchor='mb')
        d.text((x + 55, 385), yr, font=F('sansb', 20), fill=(40, 40, 40), anchor='mm')
    return im


def big_question():
    im = paper(300, 380, (240, 236, 226), 10)
    d = ImageDraw.Draw(im)
    d.text((150, 190), '?', font=F('marker', 300), fill=(190, 20, 20), anchor='mm')
    return im


BOARD_ITEMS = {
    'p_header': header_card, 'p_cal': calendar_2016, 'p_clip': clipping, 'p_farm': photo_phonefarm,
    'p_shrimp': photo_shrimp, 'p_quote': quote_card, 'p_forum': forum_print, 'p_stat': stat_print, 'p_q': big_question,
    'n_who': lambda: sticky("WHO'S REAL?", (250, 224, 80), 1), 'n_bots': lambda: sticky('ALL BOTS?', (255, 150, 170), 2),
    'n_2016': lambda: sticky('2016 !!', (150, 230, 160), 3, 64), 'n_likes': lambda: sticky('FOLLOW THE LIKES', (250, 224, 80), 4, 46),
    'n_amen': lambda: sticky('AMEN x 1000??', (140, 200, 255), 5, 46),
}


# ------------------------------------------------------------------ screens
def crt_forum(w=640, h=480):
    im = Image.new('RGB', (w, h), (18, 22, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 50], fill=(58, 66, 110))
    d.text((18, 25), "Agora Road's Macintosh Cafe", font=F('monob', 22), fill=(220, 225, 255), anchor='lm')
    d.rectangle([24, 74, w - 24, 300], outline=(110, 220, 170), width=2)
    d.text((40, 92), 'THREAD', font=F('mono', 18), fill=(110, 220, 170))
    f = F('monob', 34)
    y = 124
    for ln in wrap_text(d, 'Dead Internet Theory: Most of the Internet is Fake', f, w - 90):
        d.text((40, y), ln, font=f, fill=(235, 240, 235)); y += 44
    d.text((40, y + 14), 'posted by IlluminatiPirate', font=F('mono', 20), fill=(150, 170, 220))
    d.text((40, y + 42), 'January 2021', font=F('mono', 20), fill=(150, 170, 220))
    r = np.random.default_rng(2)
    yy = 326
    for k in range(6):
        d.line([(40, yy), (40 + int(r.integers(300, w - 90)), yy)], fill=(80, 100, 90), width=9); yy += 22
    a = np.asarray(im).astype(float)
    a[::3] *= 0.82
    return Image.fromarray(a.astype(np.uint8))


def phone_cells():
    """8 phone-screen cells (each 180x360) for the bot farm: posts, comments, likes, chat, 'Amen' typing."""
    cells = []
    kinds = ['post', 'comment', 'like', 'chat', 'amen', 'post2', 'chat2', 'amen2']
    for k, kind in enumerate(kinds):
        im = Image.new('RGB', (180, 360), (14, 16, 22))
        im = im.resize((180, 360))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 180, 26], fill=(30, 36, 52))
        d.text((90, 13), '9:41', font=F('sansb', 13), fill=(220, 220, 230), anchor='mm')
        if kind.startswith('post'):
            d.ellipse([10, 40, 36, 66], fill=(90, 140, 230)); d.rectangle([44, 46, 140, 54], fill=(160, 160, 175))
            d.rectangle([10, 76, 170, 196], fill=(70, 110, 160) if kind == 'post' else (200, 120, 90))
            d.ellipse([60, 100, 120, 170], fill=(230, 200, 120) if kind == 'post' else (250, 150, 110))
            for i in range(4):
                d.rectangle([10, 212 + i * 16, 170 - 30 * (i % 2), 220 + i * 16], fill=(120, 120, 135))
            d.text((20, 300), '♥ 12.4K', font=F('sansb', 18), fill=(255, 80, 110))
        elif kind == 'comment':
            for i in range(5):
                y = 42 + i * 62
                d.ellipse([10, y, 34, y + 24], fill=(100 + 30 * i, 120, 200))
                d.rounded_rectangle([42, y, 170, y + 44], 10, fill=(40, 46, 62))
                d.rectangle([52, y + 10, 150 - 12 * i, y + 18], fill=(190, 190, 200))
                d.rectangle([52, y + 26, 120, y + 32], fill=(140, 140, 155))
        elif kind == 'like':
            d.text((90, 170), '♥', font=F('sansb', 150), fill=(255, 60, 100), anchor='mm')
            d.text((90, 290), '+1', font=F('sansb', 40), fill=(255, 255, 255), anchor='mm')
        elif kind.startswith('chat'):
            for i in range(6):
                y = 40 + i * 52
                left = (i + (kind == 'chat2')) % 2 == 0
                x0, x1 = (10, 120) if left else (60, 170)
                d.rounded_rectangle([x0, y, x1, y + 38], 12, fill=(52, 58, 76) if left else (40, 150, 255))
                d.rectangle([x0 + 10, y + 15, x1 - 16, y + 23], fill=(220, 225, 235))
        else:
            d.rounded_rectangle([10, 250, 170, 296], 14, fill=(34, 40, 56))
            d.text((22, 273), 'Amen' + ('|' if kind == 'amen' else ''), font=F('sansb', 22), fill=(235, 235, 240), anchor='lm')
            for i in range(3):
                y = 50 + i * 64
                d.ellipse([10, y, 34, y + 24], fill=(150, 110 + 40 * i, 90))
                d.rounded_rectangle([42, y, 160, y + 40], 10, fill=(40, 46, 62))
                d.text((54, y + 20), 'Amen', font=F('sansb', 18), fill=(220, 220, 230), anchor='lm')
        cells.append(im.resize((360, 720), Image.LANCZOS))
    atlas = Image.new('RGB', (360 * 8, 720), 0)
    for i, c in enumerate(cells):
        atlas.paste(c, (360 * i, 0))
    return atlas


NAMES = ['Linda M.', 'Gary Thompson', 'Blessed_Mom77', 'Robert K.', 'Sharon Lee', 'user84721', 'Debbie R.',
         'Faith Hope Love', 'Mike_D', 'Carol Jean', 'Patricia W.', 'user20193', 'Brenda S.', 'Dennis Hall']


def shrimp_post(w=720, h=1480):
    """Phone screen: a generic dark-mode social post (an AI shrimp picture) over a long run of 'Amen' comments.
    The texture is tall; the phone shows a window of it and scrolls through the comments."""
    H = 3600
    im = Image.new('RGB', (w, H), (24, 25, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 90], fill=(32, 34, 42))
    d.text((40, 45), '←', font=F('sansb', 40), fill=(220, 220, 230), anchor='lm')
    d.text((w / 2, 45), 'Post', font=F('sansb', 34), fill=(235, 235, 240), anchor='mm')
    d.ellipse([30, 120, 110, 200], fill=(170, 120, 80))
    d.text((128, 128), 'Blessed Crafts Daily', font=F('sansb', 32), fill=(240, 240, 245))
    d.text((128, 170), '2h · Public', font=F('sans', 24), fill=(150, 150, 160))
    d.text((30, 226), 'Made it with my own hands!', font=F('sans', 32), fill=(235, 235, 240))
    sh = shrimp_image(w, 560)
    im.paste(sh, (0, 284))
    y = 860
    d.ellipse([30, y, 66, y + 36], fill=(60, 120, 255)); d.ellipse([52, y, 88, y + 36], fill=(255, 70, 100))
    d.text((100, y + 18), '41K', font=F('sans', 28), fill=(170, 170, 180), anchor='lm')
    d.text((w - 30, y + 18), '9.8K comments', font=F('sans', 28), fill=(170, 170, 180), anchor='rm')
    d.line([(0, y + 60), (w, y + 60)], fill=(50, 52, 60), width=2)
    y += 90
    r = np.random.default_rng(12)
    k = 0
    while y < H - 150:
        nm = NAMES[k % len(NAMES)]
        col = tuple(int(v) for v in r.integers(70, 200, 3))
        d.ellipse([30, y, 100, y + 70], fill=col)
        d.rounded_rectangle([118, y - 4, 118 + max(300, 30 + d.textlength(nm, font=F('sansb', 28))), y + 96], 26, fill=(44, 46, 56))
        d.text((140, y + 10), nm, font=F('sansb', 28), fill=(235, 235, 240))
        d.text((140, y + 50), ['Amen', 'Amen ♥', 'AMEN', 'Amen!!', 'Amen ♥♥'][int(r.integers(0, 5))],
               font=F('sans', 30), fill=(225, 225, 230))
        y += 130; k += 1
    return im


def build_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for k, fn in BOARD_ITEMS.items():
        fn().save(os.path.join(out_dir, k + '.png'))
    crt_forum().save(os.path.join(out_dir, 'crt.png'))
    phone_cells().save(os.path.join(out_dir, 'cells.png'))
    shrimp_post().save(os.path.join(out_dir, 'post.png'))


if __name__ == '__main__':
    build_all(os.path.join(HERE, 'build', 'tex'))
    print('ok')
