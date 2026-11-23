"""Shorts thumbnail (1080x1920) from a rendered frame: crop/zoom + title text in one of two looks.

  rainbow-outline : Archivo Black, rainbow or white fill, dark outline, soft drop shadow, darkened top
  clean-white     : Montserrat (heavy weight), plain white text, soft shadow (same feel as the "1 MARBLE" labels)
Run:  python3 make_thumbnail.py FRAME.png OUT.jpg --preset fifty-marbles
Presets below are the exact thumbnails made for the two marble xylophone videos. Add your own.
"""
import os, sys, argparse, glob
HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ======================================================================= SETTINGS
FONT_DIRS = ['fonts', '../../shared/fonts']     # searched relative to this file, then installed system fonts
ARCHIVO = 'ArchivoBlack-Regular.ttf'
MONTSERRAT = 'Montserrat[wght].ttf'             # variable font; weight is set per line
EMOJI = 'NotoColorEmoji.ttf'
RAINBOW = [(255, 59, 48), (255, 149, 0), (255, 214, 10), (52, 199, 89), (0, 199, 190), (10, 132, 255), (175, 82, 222), (255, 55, 145)]
PRESETS = {
    # "40 marbles" video
    'forty-marbles': dict(style='rainbow-outline', zoom=1.0, center_y=960, top_shade=(430, 1.5, 0.30),
                          lines=[dict(text='40 MARBLES', size=150, rainbow=True, y=140),
                                 dict(text='vs XYLOPHONE', size=92, rainbow=False, y=272)]),
    # Twinkle video: first version, then the final one, then the no-text one
    'fifty-marbles-twinkle': dict(style='clean-white',
                                  lines=[dict(text='50 MARBLES', size=112, weight=850, y=165),
                                         dict(text='play Twinkle Twinkle', size=66, weight=750, y=268, emoji='⭐')]),
    'fifty-marbles': dict(style='clean-white', lines=[dict(text='50 MARBLES', size=122, weight=850, y=200)]),
    'no-text': dict(style='none', zoom=1.08, anchor='bottom', bottom_margin=20),
}
# ===================================================================== END SETTINGS


def find_font(name):
    for d in FONT_DIRS:
        hits = glob.glob(os.path.join(HERE, d, '**', name), recursive=True)
        if hits:
            return hits[0]
    try:
        from matplotlib import font_manager
        for f in font_manager.findSystemFonts():
            if os.path.basename(f) == name:
                return f
    except Exception:
        pass
    raise SystemExit(f'Font {name} not found. Put it in {os.path.join(HERE, "fonts")} (see README).')


def label_image(text, size, rainbow=False, stroke=None):
    font = ImageFont.truetype(find_font(ARCHIVO), size)
    stroke = stroke or max(6, size // 14)
    tmp = Image.new('L', (10, 10))
    bb = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=font, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    ox, oy = 30 - bb[0], 30 - bb[1]
    mask_fill = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask_fill).text((ox, oy), text, font=font, fill=255)
    mask_all = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask_all).text((ox, oy), text, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    if rainbow:
        xs = np.linspace(0, 1, w)
        cols = np.array(RAINBOW, float)
        pos = np.linspace(0, 1, len(cols))
        grad = np.stack([np.interp(xs, pos, cols[:, c]) for c in range(3)], -1)
        fill_rgb = np.broadcast_to(grad[None], (h, w, 3)).astype(np.uint8)
    else:
        fill_rgb = np.full((h, w, 3), 255, np.uint8)
    out = np.zeros((h, w, 4), np.float32)
    shadow = np.asarray(mask_all.filter(ImageFilter.GaussianBlur(size / 18)), np.float32) / 255
    sh = np.zeros_like(shadow)
    d = max(3, size // 28)
    sh[d:, d:] = shadow[:-d, :-d]
    out[..., 3] = sh * 0.45
    a_all = np.asarray(mask_all, np.float32) / 255
    a_fill = np.asarray(mask_fill, np.float32) / 255
    stroke_col = np.array([28, 28, 34], np.float32)
    rgb = stroke_col[None, None] * (1 - a_fill[..., None]) + fill_rgb * a_fill[..., None]
    alpha = np.maximum(a_all, out[..., 3])
    out_rgb = rgb * a_all[..., None]
    out[..., :3] = np.where(alpha[..., None] > 0, out_rgb / np.maximum(alpha[..., None], 1e-6), 0)
    out[..., 3] = alpha
    return out


def rainbow_outline(src, out, p):
    im = Image.open(src).convert('RGB')
    W, H = im.size
    zoom = p.get('zoom', 1.0); cy = p.get('center_y', H / 2)
    cw, ch = W / zoom, H / zoom
    x0 = (W - cw) / 2
    y0 = min(max(cy - ch / 2, 0), H - ch)
    im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    arr = np.asarray(im, np.float32)
    span, power, strength = p.get('top_shade', (430, 1.5, 0.30))
    grad = np.clip(1 - np.arange(H) / span, 0, 1) ** power * strength
    arr = arr * (1 - grad[:, None, None])
    base = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert('RGBA')
    for i, ln in enumerate(p['lines']):
        lab = label_image(ln['text'], ln['size'], rainbow=ln.get('rainbow', False))
        if i == 0 and lab.shape[1] > W - 40:
            lab = label_image(ln['text'], int(ln['size'] * (W - 60) / lab.shape[1]), rainbow=ln.get('rainbow', False))
        h, w = lab.shape[:2]
        li = Image.fromarray((lab * [1, 1, 1, 255]).clip(0, 255).astype(np.uint8), 'RGBA')
        base.alpha_composite(li, (int(W / 2 - w / 2), int(ln['y'] - h / 2)))
    base.convert('RGB').save(out, quality=95)


def clean_white(src, out, p):
    im = Image.open(src).convert('RGBA')
    W, H = im.size
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    shadow = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(layer)
    ds = ImageDraw.Draw(shadow)
    for ln in p['lines']:
        f = ImageFont.truetype(find_font(MONTSERRAT), ln['size'])
        try:
            f.set_variation_by_axes([ln.get('weight', 850)])
        except Exception as e:
            print('font weight not applied:', e)
        size, cy = ln['size'], ln['y']
        bb = d.textbbox((0, 0), ln['text'], font=f)
        tw = bb[2] - bb[0]
        ew = 0
        em = None
        if ln.get('emoji'):
            ef = ImageFont.truetype(find_font(EMOJI), 109)
            em = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
            ImageDraw.Draw(em).text((6, 6), ln['emoji'], font=ef, embedded_color=True)
            em = em.crop(em.getbbox())
            sc = size * 0.95 / em.height
            em = em.resize((int(em.width * sc), int(em.height * sc)), Image.LANCZOS)
            ew = em.width + int(size * 0.25)
        x0 = (W - tw - ew) / 2 - bb[0]
        y0 = cy - (bb[1] + bb[3]) / 2
        ds.text((x0 + 4, y0 + 6), ln['text'], font=f, fill=200)
        d.text((x0, y0), ln['text'], font=f, fill=(255, 255, 255, 255))
        if em is not None:
            layer.alpha_composite(em, (int(x0 + bb[2] + size * 0.25), int(cy - em.height / 2)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    sh_rgba = Image.new('RGBA', (W, H), (10, 12, 20, 0))
    sh_rgba.putalpha(shadow.point(lambda v: int(v * 0.55)))
    base = im.copy()
    base.alpha_composite(sh_rgba)
    base.alpha_composite(layer)
    base.convert('RGB').save(out, quality=95)


def no_text(src, out, p):
    im = Image.open(src).convert('RGB')
    W, H = im.size
    z = p.get('zoom', 1.08)
    cw, ch = W / z, H / z
    x0 = (W - cw) / 2
    y0 = H - ch - p.get('bottom_margin', 20) if p.get('anchor') == 'bottom' else (H - ch) / 2
    im = im.crop((int(round(x0)), int(round(y0)), int(round(x0 + cw)), int(round(y0 + ch)))).resize((W, H), Image.LANCZOS)
    im.save(out, quality=95)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('frame'); ap.add_argument('out')
    ap.add_argument('--preset', default='fifty-marbles', choices=list(PRESETS))
    a = ap.parse_args()
    p = PRESETS[a.preset]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    {'rainbow-outline': rainbow_outline, 'clean-white': clean_white, 'none': no_text}[p['style']](a.frame, a.out, p)
    print('saved', a.out)
