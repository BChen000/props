"""two-dragons-episode / thumb.py: the two thumbnails, from the t_w and t_c renders (shots3d.py t_w t_c).

  python thumb.py -> $WORK/thumbnail_9x16.jpg (1080x1920: fire-breathing Western dragon over the volcano on top, the
                     Chinese dragon in karst mist below, title on the seam) and $WORK/thumbnail_16x9.jpg (1280x720)
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
os.environ.setdefault("RENDERS", os.path.join(WORK, "renders"))
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-2d-comp"))
import numpy as np, cv2
from comp import *
from bgs import *

OUT = WORK
HH = 960


def half_bg_w():
    bg = volcano_bg(1.3, hz=0.62, vx=0.3, vh=0.36, vw=0.5, sun=(0.75, 0.55), seed=21)
    bg = blur(bg, 10)
    return cv2.resize(bg[480:1440], (W, HH))


def half_bg_c():
    bg = karst_bg(0.5, hz=0.55, blur_px=10)
    return cv2.resize(bg[560:1520], (W, HH))


def load_hero(name):
    p = os.path.join(R, name, "0000.png")
    return load_rgba(p)


def build():
    top = half_bg_w()
    w = load_hero("t_w")
    top = over(top, w)
    big = np.zeros((H, W, 3), np.float32); big[:HH] = top
    big = fire_jet(big, 0.52 * W, 0.545 * HH, -10, 700, 0.8, intensity=1.0, w0=12, w1=150, grow=1.0, smoke=False)
    top = np.clip(big[:HH], 0, 1.4)
    bot = half_bg_c()
    c = load_hero("t_c")
    bot = over(bot, c)
    a, cc = Mist(seed=4).layer(0.0, 0.72, 1.0, 0.35)
    bot = bot * (1 - a[:HH, :, None]) + cc * a[:HH, :, None]
    img = np.zeros((H, W, 3), np.float32)
    img[:HH] = top; img[HH:] = bot
    # soft dark band for the title
    y = np.arange(H, dtype=np.float32)[:, None]
    band = np.exp(-((y - HH) / 120.0) ** 2) * 0.72
    img = img * (1 - band[..., None])
    img[HH - 2:HH + 2] = img[HH - 2:HH + 2] * 0.5 + 0.45
    tl = text_layer([("THE TWO DRAGONS", HH - 4, 78, False, 9, 1.0)])
    img = add_text(img, tl, 1.0)
    img = finish(img, 1, grain=0.008, vig=0.3)
    cv2.imwrite(os.path.join(OUT, "thumbnail_9x16.jpg"), (np.clip(img, 0, 1)[..., ::-1] * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 93])
    # 16:9 version: left W, right C, title band at the bottom
    L = cv2.resize(top[:, 100:100 + 880], (640, 640))
    Rr = cv2.resize(bot[:, 180:180 + 880], (640, 640))
    wide = np.zeros((720, 1280, 3), np.float32)
    wide[:600, :640] = L[20:620]; wide[:600, 640:] = Rr[20:620]
    wide[600:] = 0.03
    wide[:600, 638:642] = wide[:600, 638:642] * 0.5 + 0.45
    im = (np.clip(wide, 0, 1) * 255).astype(np.uint8)
    from PIL import Image, ImageDraw, ImageFont
    pil = Image.fromarray(im)
    d = ImageDraw.Draw(pil)
    f = ImageFont.truetype(FONT_R, 62)
    text = "THE TWO DRAGONS"
    track = 9
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + track * (len(text) - 1)
    x = (1280 - total) / 2
    for ch, cw in zip(text, widths):
        d.text((x, 660), ch, font=f, fill=(255, 255, 255), anchor="lm")
        x += cw + track
    pil.save(os.path.join(OUT, "thumbnail_16x9.jpg"), quality=93)
    print("thumbs done")


if __name__ == "__main__":
    build()
