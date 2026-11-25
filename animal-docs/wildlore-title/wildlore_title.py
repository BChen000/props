"""wildlore-title: the Wildlore Shorts thumbnail title over any 1080x1920 still.

Four centred lines at the top of the frame: a small tracked "THE" (Cinzel Bold), a huge key word in light blue
with a soft blue glow ("BLUE", Cinzel Black), the rest of the name in warm white ("RASPBERRY", Cinzel Black),
and the Latin species name under it in Cormorant Garamond Medium Italic. The still gets a gentle grade
(+12 % saturation, +6 % contrast), a dark gradient behind the title, a lighter one at the bottom and a soft
vignette. Everything sits in the top ~32 %, clear of YouTube's title/view-count overlay on the bottom ~20 %.

  python wildlore_title.py still.png thumb.jpg                                  -> default (robin) layout
  python wildlore_title.py still.png thumb.jpg --preset macro                   -> the shipped macro thumbnail
  python wildlore_title.py still.png thumb.jpg --word JACK --name ALOPE --species "Lepus cornutus"
  python wildlore_title.py still.png thumb.jpg --white-word --title-band 0.5    -> white key word, extra shade for bright backdrops

Fonts: run `python get_fonts.py` once (or `--local` to put them in fonts/ here).
"""
import argparse
import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- settings
W, H = 1080, 1920
TOP, WORD, NAME, SPECIES = "THE", "BLUE", "RASPBERRY", "Rubus cyanocarpus"
TOP_SIZE, WORD_SIZE, NAME_SIZE, SPECIES_SIZE = 66, 226, 131, 84      # px; NAME_SIZE keeps RASPBERRY ~94 px from each edge
TOP_WGHT, WORD_WGHT, NAME_WGHT, SPECIES_WGHT = 700, 900, 900, 560     # variable-font weights (560 = the shipped "medium" italic)
TRACKING = (18, 6, 4, 0)                                             # extra px between letters, per line
GAPS = (26, 26, 30)                                                  # px between the ink of consecutive lines
MAX_W = 940                                                          # a line wider than this is shrunk to fit
TITLE_Y = 120                                                        # top of "THE"
WHITE = (250, 246, 236)
WORD_COLOUR = (112, 168, 255)
WORD_GLOW = ((40, 90, 255), 18, 0.55)                                # colour, blur radius, strength
SPECIES_COLOUR = (226, 232, 255)
SHADOW = (6, 10, 0.75)                                               # y offset, blur radius, opacity
SAT, CON = 1.12, 1.06                                                # grade
TOP_DARK, TOP_END = 0.62, 760                                        # gradient: strength at y=0, fades out by TOP_END
BOTTOM_DARK = 0.30                                                   # from y=1500 down
VIGNETTE = 0.38
SPECIES_BAND = 0.42                                                  # soft shade behind the thin italic line
TITLE_BAND = 0.0                                                     # soft shade behind the whole block (bright backdrops)
JPG_QUALITY = 94
# the shipped Blue Raspberry thumbnails (Nov 2026): robin = defaults
PRESETS = {
    "robin": {},
    "macro": dict(title_y=95, top_dark=0.45),
    "board": dict(top_dark=0.72, top_end=860, title_band=0.5),
}


def find_font(names):
    dirs = [os.path.join(HERE, "fonts"), os.environ.get("WILDLORE_FONTS", ""), os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/Library/Fonts"), "/usr/share/fonts", "/home/claude/assets/fonts"]
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for n in names:
            hits = glob.glob(os.path.join(d, "**", n), recursive=True)
            if hits:
                return hits[0]
    raise SystemExit("font not found: %s (run python get_fonts.py)" % names[0])


CINZEL = ["Cinzel[wght].ttf", "Cinzel.ttf"]
CORMORANT_IT = ["CormorantGaramond-Italic-560.ttf", "CormorantGaramond-MediumItalic-static.ttf",  # static weight 560 (exact)
                "CormorantGaramond-Italic[wght].ttf", "CormorantGaramond-Italic.ttf"]                    # variable, set to 560


def font(names, size, wght):
    f = ImageFont.truetype(find_font(names), size)
    try:
        f.set_variation_by_axes([wght])
    except OSError:
        pass  # a static file: use it as it is
    return f


def grade(im, top_dark, top_end):
    a = np.asarray(im).astype(np.float32) / 255.0
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    lum = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])[..., None]
    a = lum + (a - lum) * SAT
    a = np.clip((a - 0.5) * CON + 0.5, 0, 1)
    top = 1.0 - top_dark * np.clip(1 - yy / top_end, 0, 1) ** 1.35
    bot = 1.0 - BOTTOM_DARK * np.clip((yy - 1500.0) / 420.0, 0, 1) ** 1.5
    r = np.sqrt(((xx - 560) / 760.0) ** 2 + ((yy - 1020) / 1150.0) ** 2)
    vig = 1.0 - VIGNETTE * np.clip(r - 0.55, 0, 1) ** 1.6
    a = a * (top * bot * vig)[..., None]
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))


def ink_h(f, s):
    b = f.getbbox(s)
    return b[3] - b[1]


def draw_tracked(d, x, y, s, f, fill, tr):
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tr


def tracked_width(s, f, tr):
    return sum(f.getlength(ch) for ch in s) + tr * (len(s) - 1)


def make(src, dst, top=TOP, word=WORD, name=NAME, species=SPECIES, word_colour=WORD_COLOUR, blue_word=True,
         title_y=TITLE_Y, top_dark=TOP_DARK, top_end=TOP_END, title_band=TITLE_BAND, verbose=True):
    im = Image.open(src).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    im = grade(im, top_dark, top_end)
    def fitted(names, size, wght, s, tr):
        f = font(names, size, wght)
        w = tracked_width(s, f, tr) if s else 0
        return f if w <= MAX_W else font(names, int(size * MAX_W / w), wght)
    f_top = fitted(CINZEL, TOP_SIZE, TOP_WGHT, top, TRACKING[0])
    f_word = fitted(CINZEL, WORD_SIZE, WORD_WGHT, word, TRACKING[1])
    f_name = fitted(CINZEL, NAME_SIZE, NAME_WGHT, name, TRACKING[2])
    f_sp = fitted(CORMORANT_IT, SPECIES_SIZE, SPECIES_WGHT, species, TRACKING[3])
    key = word_colour if blue_word else WHITE
    lines = [(top, f_top, WHITE, TRACKING[0]), (word, f_word, key, TRACKING[1]),
             (name, f_name, WHITE, TRACKING[2]), (species, f_sp, SPECIES_COLOUR, TRACKING[3])]
    items, y = [], title_y
    for i, (s, f, col, tr) in enumerate(lines):
        if not s:
            continue
        items.append((s, f, y, col, tr))
        y += ink_h(f, s) + (GAPS[i] if i < len(GAPS) else 0)
    text_bottom = items[-1][2] + ink_h(items[-1][1], items[-1][0])
    shadow = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(shadow)
    glow = Image.new("L", (W, H), 0); gd = ImageDraw.Draw(glow)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(txt)
    for s, f, ty, col, tr in items:
        b = f.getbbox(s)
        x = (W - tracked_width(s, f, tr)) / 2
        yy_ = ty - b[1]
        draw_tracked(sd, x, yy_ + SHADOW[0], s, f, 255, tr)
        if blue_word and s == word:
            draw_tracked(gd, x, yy_, s, f, 255, tr)
        draw_tracked(td, x, yy_, s, f, col + (255,), tr)
        if verbose:
            print("LINE", s, "x", round(x), "w", round(tracked_width(s, f, tr)), "y", ty, "h", b[3] - b[1])
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    if species:
        s_text, s_font, s_top = items[-1][0], items[-1][1], items[-1][2]
        cy = s_top + ink_h(s_font, s_text) / 2
        band = Image.new("L", (W, H), 0)
        ImageDraw.Draw(band).ellipse((W / 2 - 400, cy - 62, W / 2 + 400, cy + 62), fill=255)
        band = band.filter(ImageFilter.GaussianBlur(38)).point(lambda v: int(v * SPECIES_BAND))
        im = Image.composite(dark, im, band)
    if title_band > 0:
        tb = Image.new("L", (W, H), 0)
        ImageDraw.Draw(tb).rounded_rectangle((60, title_y - 20, W - 60, text_bottom + 20), radius=120, fill=255)
        tb = tb.filter(ImageFilter.GaussianBlur(70)).point(lambda v: int(v * title_band))
        im = Image.composite(dark, im, tb)
    shadow = shadow.filter(ImageFilter.GaussianBlur(SHADOW[1]))
    im = Image.composite(dark, im, shadow.point(lambda v: int(v * SHADOW[2])))
    if blue_word:
        g = glow.filter(ImageFilter.GaussianBlur(WORD_GLOW[1])).point(lambda v: int(v * WORD_GLOW[2]))
        im = Image.composite(Image.new("RGB", (W, H), WORD_GLOW[0]), im, g)
    im.paste(txt, (0, 0), txt)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    if dst.lower().endswith((".jpg", ".jpeg")):
        im.save(dst, quality=JPG_QUALITY, subsampling=0)
    else:
        im.save(dst)
    if verbose:
        print("TEXT_BOTTOM", text_bottom, "wrote", dst)
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--preset", choices=sorted(PRESETS), default=None)
    ap.add_argument("--top", default=TOP)
    ap.add_argument("--word", default=WORD)
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--species", default=SPECIES)
    ap.add_argument("--word-colour", default=",".join(map(str, WORD_COLOUR)))
    ap.add_argument("--white-word", action="store_true")
    ap.add_argument("--title-y", type=int, default=None)
    ap.add_argument("--top-dark", type=float, default=None)
    ap.add_argument("--top-end", type=float, default=None)
    ap.add_argument("--title-band", type=float, default=None)
    a = ap.parse_args()
    kw = dict(PRESETS.get(a.preset, {}))
    for k in ("title_y", "top_dark", "top_end", "title_band"):
        if getattr(a, k) is not None:
            kw[k] = getattr(a, k)
    make(a.src, a.dst, top=a.top, word=a.word, name=a.name, species=a.species,
         word_colour=tuple(int(v) for v in a.word_colour.split(",")), blue_word=not a.white_word, **kw)
