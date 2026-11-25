"""The Baby Griffin thumbnails: the adult (top) and the chick (bottom) blended across the middle under
"BABY / GRIFFIN" in Cinzel Black with a dark stroke, plus a 16:9 version (chick left, adult right).

  python3 thumbnail.py      -> build/thumbnail_vertical.jpg (1080x1920) and build/thumbnail_16x9.jpg (1280x720)

Frames come from the composited shots in build/out/ (assemble.py). Needs Cinzel[wght].ttf from
../wildlore-title/get_fonts.py (setup.sh puts it in ~/.fonts), or set THUMB_FONT.
"""
import os, sys, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths

# ---------------------------------------------------------------- settings (shipped values)
SETTINGS = dict(
    TOP=('s28', 40, (0, 400, 1080, 1495)),      # shot, frame (0-based), crop box in the 1080x1920 frame: adult guarding the egg
    BOTTOM=('s07b', 40, (0, 300, 1080, 1395)),  # the chick's face
    BLEND_PX=260,
    OUT_V=os.environ.get('THUMB_V', ep_paths.BUILD + 'thumbnail_vertical.jpg'),
    OUT_H=os.environ.get('THUMB_H', ep_paths.BUILD + 'thumbnail_16x9.jpg'),
)
OUT = ep_paths.OUT


def _find_font():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.environ.get('THUMB_FONT', ''), os.path.expanduser('~/.fonts/Cinzel[wght].ttf'),
              os.path.expanduser('~/Library/Fonts/Cinzel[wght].ttf'), os.path.join(here, '..', 'wildlore-title', 'fonts', 'Cinzel[wght].ttf')):
        if p and os.path.exists(p):
            return p
    raise SystemExit('Cinzel[wght].ttf not found: run ../wildlore-title/get_fonts.py (or set THUMB_FONT)')


FONT = None
# ----------------------------------------------------------------


def grab(shot, frame):
    cmd = ['ffmpeg', '-loglevel', 'error', '-i', OUT + shot + '.mp4', '-vf', f"select='eq(n\\,{frame})'", '-frames:v', '1',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    return Image.frombytes('RGB', (1080, 1920), raw)


def crop_to(im, box, size):
    return im.crop(box).resize(size, Image.LANCZOS)


def text_center2(draw, y, txt, font, fill, W, spacing=0):
    w = draw.textlength(txt, font=font) + spacing * (len(txt) - 1)
    x = (W - w) / 2
    for ch in txt:
        draw.text((x, y), ch, font=font, fill=fill, stroke_width=4, stroke_fill=(28, 20, 12, 255))
        x += draw.textlength(ch, font=font) + spacing


def make(top_shot, top_frame, top_box, bot_shot, bot_frame, bot_box, out_v, out_h, blend=260):
    W, H = 1080, 1920
    half = (H + blend) // 2
    top = crop_to(grab(top_shot, top_frame), top_box, (W, half))
    bot = crop_to(grab(bot_shot, bot_frame), bot_box, (W, half))
    A = np.asarray(top).astype(np.float32); B = np.asarray(bot).astype(np.float32)
    canvas = np.zeros((H, W, 3), np.float32)
    canvas[:half] = A
    y0 = H - half
    canvas[y0 + blend:] = B[blend:]
    a = np.linspace(0, 1, blend)[:, None, None]
    a = a * a * (3 - 2 * a)
    canvas[y0:y0 + blend] = A[half - blend:] * (1 - a) + B[:blend] * a
    ym = y0 + blend // 2
    yy = np.arange(H)[:, None, None]
    shade = 1 - 0.38 * np.exp(-((yy - ym) / 150.0) ** 2)
    canvas = np.clip(canvas * shade, 0, 255).astype(np.uint8)
    img = Image.fromarray(canvas).convert('RGBA')
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    big = ImageFont.truetype(FONT, 124); big.set_variation_by_name('Black')
    for layer, fill in ((sh, (0, 0, 0, 200)), (ov, (255, 246, 228, 255))):
        d = ImageDraw.Draw(layer)
        dy = 6 if layer is sh else 0
        if layer is sh:
            for txt, y in (('BABY', ym - 138), ('GRIFFIN', ym - 6)):
                w = d.textlength(txt, font=big) + 14 * (len(txt) - 1); x = (W - w) / 2
                for ch in txt:
                    d.text((x + 4, y + dy), ch, font=big, fill=fill); x += d.textlength(ch, font=big) + 14
        else:
            text_center2(d, ym - 138, 'BABY', big, fill, W, spacing=14)
            text_center2(d, ym - 6, 'GRIFFIN', big, fill, W, spacing=14)
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    img = Image.alpha_composite(Image.alpha_composite(img, sh), ov).convert('RGB')
    img.save(out_v, quality=95)
    # 16:9: chick left, adult right, soft vertical blend
    W2, H2 = 1280, 720
    bw = 160
    lw = (W2 + bw) // 2
    l_box = (bot_box[0], bot_box[1], bot_box[2], bot_box[1] + int((bot_box[2] - bot_box[0]) * 720 / lw))
    r_box = (top_box[0], top_box[1], top_box[2], top_box[1] + int((top_box[2] - top_box[0]) * 720 / lw))
    L = np.asarray(crop_to(grab(bot_shot, bot_frame), l_box, (lw, H2))).astype(np.float32)
    R = np.asarray(crop_to(grab(top_shot, top_frame), r_box, (lw, H2))).astype(np.float32)
    c2 = np.zeros((H2, W2, 3), np.float32)
    c2[:, :lw] = L
    x0 = W2 - lw
    c2[:, x0 + bw:] = R[:, bw:]
    a = np.linspace(0, 1, bw)[None, :, None]; a = a * a * (3 - 2 * a)
    c2[:, x0:x0 + bw] = L[:, lw - bw:] * (1 - a) + R[:, :bw] * a
    img2 = Image.fromarray(np.clip(c2, 0, 255).astype(np.uint8)).convert('RGBA')
    ov2 = Image.new('RGBA', (W2, H2), (0, 0, 0, 0)); sh2 = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    f2 = ImageFont.truetype(FONT, 96); f2.set_variation_by_name('Black')
    d2 = ImageDraw.Draw(sh2)
    txt = 'BABY GRIFFIN'; w = d2.textlength(txt, font=f2) + 8 * (len(txt) - 1); x = (W2 - w) / 2
    for ch in txt:
        d2.text((x + 4, H2 - 160 + 6), ch, font=f2, fill=(0, 0, 0, 200)); x += d2.textlength(ch, font=f2) + 8
    sh2 = sh2.filter(ImageFilter.GaussianBlur(7))
    text_center2(ImageDraw.Draw(ov2), H2 - 160, txt, f2, (255, 246, 228, 255), W2, spacing=8)
    img2 = Image.alpha_composite(Image.alpha_composite(img2, sh2), ov2).convert('RGB')
    img2.save(out_h, quality=95)
    print('saved', out_v, out_h)


if __name__ == '__main__':
    FONT = _find_font()
    t, b = SETTINGS['TOP'], SETTINGS['BOTTOM']
    make(t[0], t[1], t[2], b[0], b[1], b[2], SETTINGS['OUT_V'], SETTINGS['OUT_H'], blend=SETTINGS['BLEND_PX'])
