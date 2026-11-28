"""Textures for Area 51, drawn with Pillow: evidence-board papers, the 1989 TV interview, the event page, the warning sign, the fence."""
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


def header_card():
    im = paper(900, 300, (238, 234, 222), 1)
    d = ImageDraw.Draw(im)
    d.text((450, 140), 'AREA 51', font=F('marker', 150), fill=(25, 25, 30), anchor='mm')
    d.line([(150, 245), (750, 238)], fill=(190, 20, 20), width=9)
    return im


def nevada_map():
    im = paper(460, 560, (236, 232, 214), 2)
    d = ImageDraw.Draw(im)
    d.text((230, 40), 'NEVADA', font=F('anton', 44), fill=(40, 40, 40), anchor='mm')
    poly = [(70, 80), (300, 80), (300, 290), (420, 430), (390, 520), (330, 520), (70, 210)]
    d.polygon(poly, fill=(214, 196, 160), outline=(60, 50, 40))
    d.line(poly + [poly[0]], fill=(60, 50, 40), width=4)
    cx, cy = 255, 330
    circle_mark(d, (cx - 55, cy - 45, cx + 55, cy + 45), seed=4)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(190, 20, 20))
    d.text((cx - 10, cy + 70), 'GROOM LAKE', font=F('marker', 26), fill=(190, 20, 20), anchor='mm')
    d.text((110, 470), 'Las Vegas', font=F('type', 22), fill=(60, 60, 60))
    d.ellipse([290, 470, 300, 480], fill=(40, 40, 40))
    return im


def u2_photo(w=520, h=360):
    im = Image.new('RGB', (w, h))
    a = np.zeros((h, w, 3))
    y = np.linspace(0, 1, h)[:, None]
    a[:] = (np.array([18, 24, 60]) * (1 - y) + np.array([210, 110, 60]) * y)[:, None, :][:, 0][:, None, :]
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.5, h * 0.42
    d.polygon([(cx - 230, cy + 6), (cx + 230, cy + 6), (cx + 230, cy + 14), (cx - 230, cy + 14)], fill=(30, 30, 34))
    d.polygon([(cx - 14, cy - 60), (cx + 14, cy - 60), (cx + 10, cy + 90), (cx - 10, cy + 90)], fill=(30, 30, 34))
    d.polygon([(cx - 60, cy + 78), (cx + 60, cy + 78), (cx + 60, cy + 86), (cx - 60, cy + 86)], fill=(30, 30, 34))
    frame = Image.new('RGB', (w + 40, h + 70), (240, 238, 232))
    frame.paste(im, (20, 20))
    ImageDraw.Draw(frame).text(((w + 40) / 2, h + 45), 'U-2, 1955', font=F('type', 26), fill=(60, 60, 60), anchor='mm')
    return frame


def cia_doc():
    im = paper(560, 720, (240, 238, 230), 5, 0.4)
    d = ImageDraw.Draw(im)
    d.text((280, 50), 'CENTRAL INTELLIGENCE AGENCY', font=F('type', 28), fill=(30, 30, 30), anchor='mm')
    y = 100
    for ln in wrap_text(d, 'The Central Intelligence Agency and Overhead Reconnaissance: The U-2 and OXCART Programs, 1954-1974', F('type', 24), 480):
        d.text((280, y), ln, font=F('type', 24), fill=(30, 30, 30), anchor='mm'); y += 32
    r = np.random.default_rng(6)
    y += 20
    for k in range(13):
        x = 40
        while x < 510:
            wd = int(r.integers(40, 120)); wd = min(wd, 515 - x)
            col = (15, 15, 15) if r.random() < 0.3 else (120, 120, 115)
            d.rectangle([x, y, x + wd, y + (14 if col[0] < 20 else 6)], fill=col); x += wd + 12
        y += 30
        if k == 4:
            d.text((200, y), 'AREA 51', font=F('type', 30), fill=(20, 20, 20))
            circle_mark(d, (170, y - 16, 360, y + 46), seed=7, w=6)
            y += 44
    st = Image.new('RGBA', (420, 110), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rectangle([4, 4, 415, 105], outline=(190, 30, 30, 230), width=8)
    sd.text((210, 56), 'DECLASSIFIED 2013', font=F('anton', 50), fill=(190, 30, 30, 230), anchor='mm')
    st = st.rotate(-12, expand=True, resample=Image.BICUBIC)
    im.paste(st, (90, 520), st)
    return im


def cia_quote():
    im = paper(620, 360, (246, 246, 244), 6, 0.2)
    d = ImageDraw.Draw(im)
    d.ellipse([30, 28, 90, 88], fill=(30, 40, 70))
    d.text((60, 58), 'CIA', font=F('sansb', 16), fill=(240, 240, 240), anchor='mm')
    d.text((110, 34), 'CIA', font=F('sansb', 28), fill=(20, 20, 20))
    d.text((110, 68), 'posted Dec 29, 2014', font=F('sans', 20), fill=(110, 110, 110))
    f = F('sans', 34)
    y = 120
    for ln in wrap_text(d, "Reports of unusual activity in the skies in the '50s? It was us.", f, 560):
        d.text((32, y), ln, font=f, fill=(20, 20, 20)); y += 46
    circle_mark(d, (370, 160, 610, 230), seed=9, w=6)
    return im


def saucer_photo(w=480, h=360):
    a = np.zeros((h, w, 3))
    y = np.linspace(0, 1, h)[:, None]
    a[:] = (np.array([150, 160, 170]) * (1 - y) + np.array([90, 95, 100]) * y)[:, None, :][:, 0][:, None, :]
    r = np.random.default_rng(3)
    a += r.normal(0, 12, a.shape)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.ellipse([140, 150, 340, 205], fill=(40, 40, 45))
    d.ellipse([200, 125, 280, 175], fill=(55, 55, 60))
    im = im.filter(ImageFilter.GaussianBlur(2.2))
    frame = Image.new('RGB', (w + 40, h + 70), (238, 236, 228))
    frame.paste(im, (20, 20))
    ImageDraw.Draw(frame).text(((w + 40) / 2, h + 45), 'UFO??', font=F('marker', 34), fill=(190, 20, 20), anchor='mm')
    return frame


def storm_print():
    im = paper(520, 380, (244, 244, 240), 8, 0.3)
    d = ImageDraw.Draw(im)
    d.text((260, 60), 'STORM AREA 51', font=F('anton', 56), fill=(25, 25, 25), anchor='mm')
    d.text((260, 130), 'Sept 20, 2019', font=F('type', 30), fill=(60, 60, 60), anchor='mm')
    d.text((260, 220), '2,000,000 GOING', font=F('anton', 50), fill=(190, 30, 30), anchor='mm')
    d.text((260, 300), 'showed up: < 100', font=F('marker', 40), fill=(25, 25, 60), anchor='mm')
    return im


BOARD_ITEMS = {
    'p_header': header_card, 'p_cal': nevada_map, 'p_clip': cia_doc, 'p_farm': u2_photo, 'p_shrimp': saucer_photo,
    'p_quote': cia_quote, 'p_forum': storm_print, 'p_stat': lambda: sticky('60,000 FT ??', (250, 224, 80), 11, 56).resize((300, 300)),
    'p_q': lambda: sticky('?', (255, 150, 170), 12, 220),
    'n_who': lambda: sticky('DREAMLAND', (250, 224, 80), 1, 46), 'n_bots': lambda: sticky('NINE SAUCERS?', (255, 150, 170), 2, 46),
    'n_2016': lambda: sticky('1955', (150, 230, 160), 3, 72), 'n_likes': lambda: sticky('IT WAS US?', (250, 224, 80), 4, 50),
    'n_amen': lambda: sticky('WHO FLIES THAT HIGH?', (140, 200, 255), 5, 40),
}


# ------------------------------------------------------------------ screens
def crt_forum(w=640, h=480):
    """The 1989 TV interview: a man in shadow against a blue backlight, with a news lower third."""
    a = np.zeros((h, w, 3))
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.sqrt(((xx - w * 0.5) / (w * 0.5)) ** 2 + ((yy - h * 0.42) / (h * 0.6)) ** 2)
    a[:] = (np.array([20, 50, 110]) * np.clip(1.2 - rr, 0, 1)[..., None] + np.array([6, 8, 18]))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.ellipse([w * 0.5 - 70, 110, w * 0.5 + 70, 290], fill=(4, 4, 8))
    d.polygon([(w * 0.5 - 60, 270), (w * 0.5 + 60, 270), (w * 0.5 + 190, 420), (w * 0.5 - 190, 420)], fill=(4, 4, 8))
    d.rectangle([0, 360, w, 440], fill=(20, 20, 30))
    d.rectangle([0, 360, 200, 440], fill=(170, 20, 20))
    d.text((100, 400), '1989', font=F('anton', 48), fill=(250, 250, 250), anchor='mm')
    d.text((220, 380), 'ANONYMOUS SOURCE', font=F('sansb', 26), fill=(240, 240, 240))
    d.text((220, 412), 'claims alien craft near Area 51', font=F('sans', 20), fill=(200, 200, 210))
    d.rectangle([w - 110, 20, w - 20, 56], fill=(200, 20, 20))
    d.text((w - 65, 38), 'LIVE', font=F('sansb', 24), fill=(255, 255, 255), anchor='mm')
    a = np.asarray(im).astype(float)
    a[::3] *= 0.8
    return Image.fromarray(a.astype(np.uint8))


def phone_cells():
    """Unused in this episode; kept so build_sets can make the farm atlas if a scene wants it."""
    return Image.new('RGB', (360 * 8, 720), (10, 10, 14))


def shrimp_post(w=720, h=1480):
    """Phone screen: the 'Storm Area 51' event page (generic UI). Tall texture; the phone shows a window of it."""
    H = 2400
    im = Image.new('RGB', (w, H), (24, 25, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 90], fill=(32, 34, 42))
    d.text((40, 45), '←', font=F('sansb', 40), fill=(220, 220, 230), anchor='lm')
    d.text((w / 2, 45), 'Event', font=F('sansb', 34), fill=(235, 235, 240), anchor='mm')
    cover = Image.new('RGB', (w, 420))
    ca = np.zeros((420, w, 3)); yv = np.linspace(0, 1, 420)[:, None]
    ca[:] = (np.array([10, 12, 40]) * (1 - yv) + np.array([120, 60, 40]) * yv)[:, None, :][:, 0][:, None, :]
    cover = Image.fromarray(ca.astype(np.uint8)); cd = ImageDraw.Draw(cover)
    cd.polygon([(0, 420), (180, 300), (330, 380), (520, 280), (720, 360), (720, 420)], fill=(40, 25, 20))
    cd.ellipse([w / 2 - 70, 120, w / 2 + 70, 280], fill=(90, 200, 110))
    cd.ellipse([w / 2 - 50, 170, w / 2 - 10, 215], fill=(10, 10, 10)); cd.ellipse([w / 2 + 10, 170, w / 2 + 50, 215], fill=(10, 10, 10))
    im.paste(cover, (0, 90))
    y = 540
    d.text((36, y), 'FRI, SEP 20, 2019 AT 3 AM', font=F('sansb', 26), fill=(230, 90, 80)); y += 50
    for ln in wrap_text(d, "Storm Area 51, They Can't Stop All of Us", F('sansb', 44), w - 70):
        d.text((36, y), ln, font=F('sansb', 44), fill=(240, 240, 245)); y += 56
    d.text((36, y + 10), 'Amargosa Valley, Nevada', font=F('sans', 28), fill=(170, 170, 180)); y += 80
    d.rounded_rectangle([36, y, w - 36, y + 80], 18, fill=(40, 110, 230))
    d.text((w / 2, y + 40), '✓ Going', font=F('sansb', 34), fill=(255, 255, 255), anchor='mm'); y += 120
    d.text((36, y), '2.0M', font=F('sansb', 64), fill=(240, 240, 245)); d.text((36, y + 76), 'going', font=F('sans', 28), fill=(170, 170, 180))
    d.text((380, y), '1.5M', font=F('sansb', 64), fill=(240, 240, 245)); d.text((380, y + 76), 'interested', font=F('sans', 28), fill=(170, 170, 180))
    y += 150
    d.line([(0, y), (w, y)], fill=(50, 52, 60), width=2); y += 30
    r = np.random.default_rng(12)
    for k in range(14):
        col = tuple(int(v) for v in r.integers(70, 200, 3))
        d.ellipse([36, y, 96, y + 60], fill=col)
        d.rounded_rectangle([112, y - 4, w - 36, y + 80], 22, fill=(44, 46, 56))
        d.text((132, y + 6), ['im going', 'Naruto run!', 'see them aliens', 'who is driving', "I'm bringing snacks", 'they cant stop all of us'][k % 6], font=F('sans', 28), fill=(225, 225, 230))
        y += 110
    return im


def sign_warning(w=600, h=420):
    im = Image.new('RGB', (w, h), (240, 240, 236))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 90], fill=(200, 30, 30))
    d.text((w / 2, 45), 'WARNING', font=F('anton', 64), fill=(255, 255, 255), anchor='mm')
    y = 120
    for ln, f in (('RESTRICTED AREA', F('anton', 52)), ('No trespassing beyond this point', F('sansb', 26)),
                  ('Photography of this area is prohibited', F('sansb', 24)), ('USE OF DEADLY FORCE AUTHORIZED', F('anton', 40))):
        d.text((w / 2, y), ln, font=f, fill=(20, 20, 20), anchor='mt'); y += f.size + 26
    return im


def build_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for k, fn in BOARD_ITEMS.items():
        fn().save(os.path.join(out_dir, k + '.png'))
    crt_forum().save(os.path.join(out_dir, 'crt.png'))
    shrimp_post().save(os.path.join(out_dir, 'post.png'))
    sign_warning().save(os.path.join(out_dir, 'warn.png'))
    fence_tex().save(os.path.join(out_dir, 'fence.png'))


def fence_tex():
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(-128, 256, 32):
        d.line([(k, 0), (k + 128, 128)], fill=(170, 175, 180, 255), width=4)
        d.line([(k + 128, 0), (k, 128)], fill=(170, 175, 180, 255), width=4)
    return im




if __name__ == '__main__':
    build_all(os.path.join(HERE, 'build', 'tex'))
    print('ok')
