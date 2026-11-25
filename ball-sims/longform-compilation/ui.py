"""Everything drawn on top of the Shorts: backdrop, card shadow, side-panel game UI, transitions, thumbnail.

All sprites are drawn at 2x and downsampled, so circles and rounded boxes are anti-aliased.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import settings as S

SS = 2
_fonts = {}


def font(key, size):
    k = (key, int(size))
    if k not in _fonts:
        for d in S.FONT_DIRS:
            p = os.path.join(d, S.FONTS[key])
            if os.path.exists(p):
                _fonts[k] = ImageFont.truetype(p, int(size))
                break
        else:
            raise FileNotFoundError(f"{S.FONTS[key]} not found in {S.FONT_DIRS}: run ../style-kit/get_fonts.py")
    return _fonts[k]


def rgb(h, a=None):
    h = h.lstrip("#")
    c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return c if a is None else c + (a,)


class Layout:
    def __init__(self, mode):
        crop_h = S.MODES[mode]
        self.cw = int(round(1080 * S.CARD_H / crop_h / 2)) * 2
        self.cx = (S.W - self.cw) // 2
        self.pw = self.cx
        self.lx = self.pw // 2
        self.rx = self.cx + self.cw + self.pw // 2
        self.crop_h = crop_h


# ----------------------------------------------------------------------------------------------- primitives
def layer(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def down(im):
    return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)


def text_w(s, f):
    b = f.getbbox(s)
    return b[2] - b[0]


def fit_size(lines, key, size, max_w):
    while size > 16 and max(text_w(l, font(key, size * SS)) for l in lines) > max_w * SS:
        size -= 2
    return size


def draw_text(im, s, cx, y, key, size, fill, stroke=0, stroke_fill=S.OUTLINE, shadow=True, anchor="mt"):
    """cx, y and sizes in 1x pixels; im is a 2x layer."""
    f = font(key, size * SS)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((cx * SS, (y + size * 0.07) * SS), s, font=f, anchor=anchor,
                                fill=(0, 0, 0, 150), stroke_width=stroke * SS, stroke_fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(5 * SS))
        im.alpha_composite(sh)
    d = ImageDraw.Draw(im)
    d.text((cx * SS, y * SS), s, font=f, anchor=anchor, fill=fill if len(fill) == 4 else fill + (255,),
           stroke_width=stroke * SS, stroke_fill=rgb(stroke_fill) if isinstance(stroke_fill, str) else stroke_fill)


def draw_lines(im, lines, cx, top, key, size, fills, stroke=6, gap=0.98, max_w=None):
    if max_w:
        size = fit_size(lines, key, size, max_w)
    y = top
    for i, l in enumerate(lines):
        draw_text(im, l, cx, y, key, size, fills[i] if isinstance(fills, list) else fills, stroke=stroke)
        y += size * gap
    return y


def pill(im, cx, cy, w, h, fill, outline=None, ow=0):
    d = ImageDraw.Draw(im)
    box = [(cx - w / 2) * SS, (cy - h / 2) * SS, (cx + w / 2) * SS, (cy + h / 2) * SS]
    d.rounded_rectangle(box, radius=h / 2 * SS, fill=fill, outline=outline, width=ow * SS)


def marble(r, color, glow=False):
    """A glossy marble sprite (RGBA, 2r x 2r at 1x), lit from the top left like the 3D sets."""
    n = 2 * r * 4
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    nx = (xx + 0.5) / (n / 2) - 1
    ny = (yy + 0.5) / (n / 2) - 1
    rr = nx ** 2 + ny ** 2
    inside = rr <= 1
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    L = np.array([-0.45, -0.6, 0.66])
    L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    refl_z = 2 * lam * nz - L[2]
    spec = np.clip(refl_z, 0, 1) ** 40
    rim = (1 - nz) ** 3 * 0.35
    base = np.array(rgb(color), np.float32) / 255
    col = base[None, None, :] * (0.38 + 0.72 * lam[..., None]) + spec[..., None] * 0.95 + rim[..., None] * 0.6
    col = np.clip(col, 0, 1)
    a = inside.astype(np.float32)
    img = np.dstack([col * 255, a[..., None] * 255]).astype(np.uint8)
    im = Image.fromarray(img, "RGBA").resize((2 * r, 2 * r), Image.LANCZOS)
    return im


def paste_center(dst, src, cx, cy):
    dst.alpha_composite(src, (int(round(cx - src.width / 2)), int(round(cy - src.height / 2))))


# ----------------------------------------------------------------------------------------------- backdrop
def backdrop(frame):
    """Blurred, darkened copy of a clip frame filling the 16:9 canvas."""
    f = frame.convert("RGB")
    scale = S.W / f.width
    f = f.resize((S.W, int(f.height * scale)), Image.BILINEAR)
    top = (f.height - S.H) // 2
    f = f.crop((0, top, S.W, top + S.H))
    small = f.resize((S.W // 8, S.H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
    f = small.resize((S.W, S.H), Image.BICUBIC)
    a = np.asarray(f).astype(np.float32) * S.BG_BRIGHTNESS
    yy, xx = np.mgrid[0:S.H, 0:S.W].astype(np.float32)
    v = ((xx - S.W / 2) / (S.W / 2)) ** 2 + ((yy - S.H / 2) / (S.H / 2)) ** 2
    a *= np.clip(1.08 - 0.32 * v, 0.55, 1)[..., None]
    tint = np.array(rgb("#1e0c33"), np.float32)
    a = a * 0.86 + tint * 0.14
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def card_mask(lay):
    m = Image.new("L", (lay.cw * 4, S.CARD_H * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, lay.cw * 4 - 1, S.CARD_H * 4 - 1], radius=S.CARD_R * 4, fill=255)
    return m.resize((lay.cw, S.CARD_H), Image.LANCZOS)


def logo(im, cx, cy):
    """Channel wordmark: a pink marble + "Marble Pop"."""
    f = font("blk", 44 * SS)
    tw = text_w(S.CHANNEL, f) / SS
    total = 56 + 14 + tw
    x0 = cx - total / 2
    m = marble(28 * SS // 2 * 2, S.PINK)
    paste_center(im, m, (x0 + 28) * SS, cy * SS)
    draw_text(im, S.CHANNEL, x0 + 56 + 14 + tw / 2, cy, "blk", 44, (255, 255, 255), stroke=5, anchor="mm")


def progress(im, lay, idx, total, kind):
    cx = lay.rx
    draw_text(im, f"ROUND {min(idx + 1, total)} OF {total}" if kind != "bonus" else "BONUS ROUND",
              cx, 232, "xb", 34, rgb(S.YELLOW) if kind == "bonus" else (255, 255, 255), stroke=5)
    cols, step, r = 5, 66, 23
    gx0 = cx - (cols - 1) * step / 2
    for i in range(total):
        x = gx0 + (i % cols) * step
        y = 330 + (i // cols) * step
        if i < idx or kind == "bonus":
            paste_center(im, marble(r * SS, S.MARBLES[i % len(S.MARBLES)]), x * SS, y * SS)
        elif i == idx:
            d = ImageDraw.Draw(im)
            d.ellipse([(x - r - 8) * SS, (y - r - 8) * SS, (x + r + 8) * SS, (y + r + 8) * SS], outline=(255, 255, 255, 255),
                      width=5 * SS)
            paste_center(im, marble((r + 3) * SS, S.MARBLES[i % len(S.MARBLES)]), x * SS, y * SS)
        else:
            d = ImageDraw.Draw(im)
            d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=(255, 255, 255, 38),
                      outline=(255, 255, 255, 70), width=2 * SS)
    by = 330 + 4 * step + 30
    gold = marble(36 * SS, S.GOLD)
    paste_center(im, gold, cx * SS, by * SS)
    if kind != "bonus":
        draw_text(im, "?", cx, by, "blk", 44, (90, 50, 0), shadow=False, anchor="mm")
        draw_text(im, "SECRET BONUS", cx, by + 50, "xb", 30, rgb(S.GOLD), stroke=4)
    else:
        draw_text(im, "!", cx, by, "blk", 44, (90, 50, 0), shadow=False, anchor="mm")
        draw_text(im, "UNLOCKED!", cx, by + 50, "xb", 30, rgb(S.GOLD), stroke=4)


def round_pill(im, lay, idx, kind, label=None):
    text = label or ("BONUS SONG!" if kind == "bonus" else f"ROUND {idx + 1}")
    f = font("blk", 40 * SS)
    w = text_w(text, f) / SS + 70
    fill = rgb(S.GOLD, 255) if kind == "bonus" or label else rgb(S.PINK, 255)
    pill(im, lay.lx, 112, w, 76, fill, outline=(255, 255, 255, 255), ow=4)
    draw_text(im, text, lay.lx, 112, "blk", 40, rgb(S.INK), shadow=False, anchor="mm")


def color_row(im, cx, cy, names, r=46, labels=True, gap=None):
    gap = gap or (2 * r + 26)
    x0 = cx - (len(names) - 1) * gap / 2
    for i, n in enumerate(names):
        x = x0 + i * gap
        paste_center(im, marble(r * SS, S.BALL[n]), x * SS, cy * SS)
        if labels:
            draw_text(im, n.upper(), x, cy + r + 14, "xb", 26 if len(names) < 4 else 22, (255, 255, 255), stroke=4)


def static_layer(item, lay, idx, total, bg):
    """Opaque full frame under the card: backdrop, card shadow, right panel and the static left-panel content."""
    base = bg.convert("RGBA")
    sh = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([lay.cx - 6, S.CARD_Y + 4, lay.cx + lay.cw + 6, S.CARD_Y + S.CARD_H + 18],
                                         radius=S.CARD_R + 6, fill=(0, 0, 0, 170))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    ui = layer(S.W, S.H)
    d = ImageDraw.Draw(ui)
    d.rounded_rectangle([(lay.cx - 3) * SS, (S.CARD_Y - 3) * SS, (lay.cx + lay.cw + 3) * SS, (S.CARD_Y + S.CARD_H + 3) * SS],
                        radius=(S.CARD_R + 3) * SS, outline=(255, 255, 255, 120), width=3 * SS)
    logo(ui, lay.rx, 108)
    progress(ui, lay, idx, total, item["kind"])
    round_pill(ui, lay, idx, item["kind"], item.get("label"))
    k = item["kind"]
    maxw = lay.pw - 60
    if k == "race":
        draw_lines(ui, ["PICK YOUR", "COLOR!"], lay.lx, 210, "blk", 82, [(255, 255, 255), rgb(S.YELLOW)], max_w=maxw)
        color_row(ui, lay.lx, 560, item["colors"], r=50 if len(item["colors"]) <= 2 else 40)
        draw_text(ui, item.get("sub", ""), lay.lx, 690, "xb", 34, (255, 255, 255), stroke=5)
        draw_text(ui, "Comment your pick!", lay.lx, 745, "sb", 30, (230, 230, 240), stroke=4)
    elif k == "run":
        fills = [(255, 255, 255)] * (len(item["prompt"]) - 1) + [rgb(S.YELLOW)]
        y = draw_lines(ui, item["prompt"], lay.lx, 205, "blk", 74, fills, max_w=maxw)
        if item.get("colors"):
            n = len(item["colors"])
            color_row(ui, lay.lx, 640, item["colors"], r=40 if n <= 3 else 30, labels=n <= 3,
                      gap=None if n <= 3 else 74)
    return base, down(ui)


def compose_static(base, ui):
    out = base.copy()
    out.alpha_composite(ui)
    return out.convert("RGB")


# ----------------------------------------------------------------------------------------------- dynamic sprites
def crop_sprite(im):
    """Trim a 1x RGBA layer to its content; returns (sprite, x, y)."""
    bb = im.getbbox()
    if not bb:
        return im.crop((0, 0, 2, 2)), 0, 0
    x0, y0 = max(bb[0] - 2, 0) // 2 * 2, max(bb[1] - 2, 0) // 2 * 2
    x1, y1 = min(bb[2] + 2, im.width), min(bb[3] + 2, im.height)
    x1 = x0 + (x1 - x0 + 1) // 2 * 2
    y1 = y0 + (y1 - y0 + 1) // 2 * 2
    return im.crop((x0, y0, x1, y1)), x0, y0


def song_prompt(lay, kind):
    ui = layer(S.W, S.H)
    if kind == "bonus":
        draw_lines(ui, ["GUESS THE", "NEW SONG!"], lay.lx, 215, "blk", 86, [(255, 255, 255), rgb(S.GOLD)],
                   max_w=lay.pw - 60)
        draw_text(ui, "Never posted before!", lay.lx, 880, "xb", 36, rgb(S.GOLD), stroke=5)
    else:
        draw_lines(ui, ["GUESS THE", "SONG!"], lay.lx, 215, "blk", 86, [(255, 255, 255), rgb(S.YELLOW)],
                   max_w=lay.pw - 60)
        draw_text(ui, "Shout it out!", lay.lx, 880, "xb", 36, (255, 255, 255), stroke=5)
    return crop_sprite(down(ui))


def countdown(lay, n, total):
    r = 122
    im = layer(2 * r + 40, 2 * r + 40)
    c = r + 20
    d = ImageDraw.Draw(im)
    d.ellipse([(c - r) * SS, (c - r) * SS, (c + r) * SS, (c + r) * SS], fill=S.PANEL_RGBA)
    d.ellipse([(c - r) * SS, (c - r) * SS, (c + r) * SS, (c + r) * SS], outline=(255, 255, 255, 70), width=14 * SS)
    frac = n / total
    d.arc([(c - r) * SS, (c - r) * SS, (c + r) * SS, (c + r) * SS], start=-90, end=-90 + 360 * frac,
          fill=rgb(S.YELLOW, 255), width=14 * SS)
    draw_text(im, str(n), c, c + 6, "blk", 150, rgb(S.YELLOW), stroke=7, anchor="mm")
    return down(im)


def answer_block(lay, title, extra=None, header="IT'S...", icon=None, color=None, points=False):
    w = lay.pw - 70
    ui = layer(lay.pw, 640)
    cx = lay.pw / 2
    draw_text(ui, header, cx, 10, "blk", 58, rgb(S.YELLOW), stroke=6)
    key = "blk"
    lines, size = wrap_balanced(title, key, w - 56)
    icon_h = 130 if icon else 0
    box_h = len(lines) * size * 1.08 + 56 + icon_h
    top = 100
    d = ImageDraw.Draw(ui)
    d.rounded_rectangle([(cx - w / 2) * SS, top * SS, (cx + w / 2) * SS, (top + box_h) * SS], radius=34 * SS,
                        fill=(255, 255, 255, 255), outline=rgb(S.BALL["green"], 255), width=8 * SS)
    y = top + 28
    if icon == "heart":
        heart(ui, cx, y + 58, 62)
        y += icon_h
    elif icon == "marble":
        paste_center(ui, marble(54 * SS, S.BALL[color]), cx * SS, (y + 58) * SS)
        y += icon_h
    for l in lines:
        draw_text(ui, l, cx, y, key, size, rgb(color and S.BALL[color] or S.INK) if icon == "marble" else rgb(S.INK),
                  shadow=False)
        y += size * 1.08
    bx, by, br = cx + w / 2 - 14, top + 8, 34
    d.ellipse([(bx - br) * SS, (by - br) * SS, (bx + br) * SS, (by + br) * SS], fill=rgb(S.BALL["green"], 255),
              outline=(255, 255, 255, 255), width=5 * SS)
    d.line([((bx - 15) * SS, (by + 1) * SS), ((bx - 4) * SS, (by + 12) * SS), ((bx + 16) * SS, (by - 11) * SS)],
           fill=(255, 255, 255, 255), width=8 * SS, joint="curve")
    yb = top + box_h + 26
    if extra:
        draw_text(ui, extra, cx, yb, "xb", 36, (255, 255, 255), stroke=5)
        yb += 52
    if points:
        draw_text(ui, "Got it? +1 point!", cx, yb, "xb", 36, rgb(S.YELLOW), stroke=5)
    return down(ui)


def wrap_balanced(title, key, max_w, min_size={1: 54, 2: 46, 3: 0}):
    """Fewest lines that still allow a big font; within a line count, the split with the shortest longest line."""
    import itertools
    words = title.split()
    for n in (1, 2, 3):
        if n > len(words):
            break
        best = None
        for cuts in itertools.combinations(range(1, len(words)), n - 1):
            idx = (0,) + cuts + (len(words),)
            ls = [" ".join(words[idx[i]:idx[i + 1]]) for i in range(n)]
            wmax = max(text_w(l, font(key, 100)) for l in ls) / 100
            if best is None or wmax < best[0]:
                best = (wmax, ls)
        size = min(66, int(max_w / best[0]) // 2 * 2)
        if size >= min_size[n]:
            return best[1], size
    return best[1], max(size, 30)


def heart(im, cx, cy, s):
    t = np.linspace(0, 2 * np.pi, 400)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    pts = [((cx + xi * s / 17) * SS, (cy + yi * s / 17) * SS) for xi, yi in zip(x, y)]
    ImageDraw.Draw(im).polygon(pts, fill=rgb(S.BALL["red"], 255))


def pop_frames(block, scales=(0.55, 0.82, 1.06, 1.12, 1.05)):
    out = []
    for s in scales:
        w, h = max(2, int(block.width * s) // 2 * 2), max(2, int(block.height * s) // 2 * 2)
        out.append(block.resize((w, h), Image.LANCZOS))
    return out


def race_end(lay):
    ui = layer(lay.pw, 260)
    cx = lay.pw / 2
    pill(ui, cx, 130, lay.pw - 60, 210, (10, 4, 20, 215), outline=rgb(S.YELLOW, 255), ow=5)
    draw_lines(ui, ["DID YOUR", "COLOR WIN?"], cx, 52, "blk", 62, [(255, 255, 255), rgb(S.YELLOW)], max_w=lay.pw - 120)
    return down(ui)


def upnext(text, gold=False):
    f1, f2 = font("xb", 26 * SS), font("blk", 40 * SS)
    tw = max(text_w("UP NEXT", f1), text_w(text, f2)) / SS
    w, h = int(tw + 150), 124
    im = layer(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=28 * SS, fill=(10, 4, 20, 225),
                        outline=rgb(S.GOLD if gold else S.PINK, 255), width=4 * SS)
    tx = 34
    d.polygon([((tx) * SS, (h / 2 - 22) * SS), ((tx) * SS, (h / 2 + 22) * SS), ((tx + 34) * SS, (h / 2) * SS)],
              fill=rgb(S.YELLOW, 255))
    d.text(((tx + 58) * SS, 22 * SS), "UP NEXT", font=f1, fill=rgb(S.YELLOW, 255))
    d.text(((tx + 58) * SS, 52 * SS), text, font=f2, fill=(255, 255, 255, 255))
    return down(im)


def panels_overlay(lay, bg):
    """Opaque side panels (backdrop only) with a transparent hole over the card."""
    im = bg.convert("RGBA")
    hole = Image.new("L", (S.W, S.H), 255)
    ImageDraw.Draw(hole).rectangle([lay.cx - 8, 0, lay.cx + lay.cw + 8, S.H], fill=0)
    im.putalpha(hole)
    return im


def intro_overlay(lay, bg):
    im = panels_overlay(lay, bg)
    ui = layer(S.W, S.H)
    left, right = S.INTRO_LINES
    draw_lines(ui, left, lay.lx, 150, "blk", 150, [(255, 255, 255), (255, 255, 255), rgb(S.YELLOW), rgb(S.YELLOW)],
               stroke=8, gap=0.93, max_w=lay.pw - 50)
    logo(ui, lay.rx, 108)
    draw_lines(ui, right[:1], lay.rx, 290, "blk", 92, [(255, 255, 255)], stroke=7, max_w=lay.pw - 60)
    draw_lines(ui, right[1:], lay.rx, 430, "blk", 70, [rgb(S.GOLD), rgb(S.GOLD), (255, 255, 255)], stroke=6,
               max_w=lay.pw - 60)
    paste_center(ui, marble(60 * SS, S.GOLD), lay.rx * SS, 790 * SS)
    draw_text(ui, "?", lay.rx, 790, "blk", 74, (90, 50, 0), shadow=False, anchor="mm")
    im.alpha_composite(down(ui))
    return im


def endscreen_overlay(lay, bg):
    im = panels_overlay(lay, bg)
    ui = layer(S.W, S.H)
    title, l1, l2 = S.END_LINES
    draw_lines(ui, title, lay.lx, 110, "blk", 76, [(255, 255, 255), rgb(S.YELLOW)], max_w=lay.pw - 60)
    draw_text(ui, l1, lay.lx, 300, "xb", 36, (255, 255, 255), stroke=5)
    draw_text(ui, l2, lay.lx, 350, "xb", 36, rgb(S.YELLOW), stroke=5)
    d = ImageDraw.Draw(ui)
    r, cy = 112, 640
    d.ellipse([(lay.lx - r) * SS, (cy - r) * SS, (lay.lx + r) * SS, (cy + r) * SS], fill=(255, 255, 255, 30),
              outline=(255, 255, 255, 200), width=5 * SS)
    draw_text(ui, "SUBSCRIBE", lay.lx, cy + r + 24, "blk", 40, rgb(S.BALL["red"]), stroke=6)
    logo(ui, lay.rx, 108)
    draw_text(ui, "WATCH NEXT", lay.rx, 300, "blk", 58, (255, 255, 255), stroke=6)
    bw = lay.pw - 70
    bh = int(bw * 9 / 16)
    top = 400
    d.rounded_rectangle([(lay.rx - bw / 2) * SS, top * SS, (lay.rx + bw / 2) * SS, (top + bh) * SS], radius=22 * SS,
                        fill=(255, 255, 255, 30), outline=(255, 255, 255, 200), width=5 * SS)
    tri = [((lay.rx - 26) * SS, (top + bh / 2 - 34) * SS), ((lay.rx - 26) * SS, (top + bh / 2 + 34) * SS),
           ((lay.rx + 36) * SS, (top + bh / 2) * SS)]
    d.polygon(tri, fill=(255, 255, 255, 170))
    im.alpha_composite(down(ui))
    return im


_grid = None


def _sphere(r, color):
    """RGB float image of a glossy marble of radius r centred on the frame, plus its distance map."""
    global _grid
    if _grid is None:
        yy, xx = np.mgrid[0:S.H, 0:S.W].astype(np.float32)
        _grid = (xx - S.W / 2 + 0.5, yy - S.H / 2 + 0.5, np.hypot(xx - S.W / 2 + 0.5, yy - S.H / 2 + 0.5))
    dx, dy, d = _grid
    r = max(r, 1.0)
    nx, ny = dx / r, dy / r
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    L = np.array([-0.45, -0.6, 0.66], np.float32)
    L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    spec = np.clip(2 * lam * nz - L[2], 0, 1) ** 36
    base = np.array(rgb(color), np.float32) / 255
    col = base * (0.42 + 0.68 * lam[..., None]) + spec[..., None] * 0.9 + ((1 - nz) ** 3 * 0.25)[..., None]
    return np.clip(col, 0, 1), d


def transition_frames(color, n=S.TRANSITION_FRAMES):
    """The "marble pop": n cover frames (a glossy marble grows from the centre until it fills the frame) and
    n uncover frames (it bursts open from the centre, a white rim racing outward). RGBA, full frame."""
    Rmax = 1.04 * np.hypot(S.W / 2, S.H / 2)
    ring_w = 7.0
    full, _ = _sphere(Rmax, color)
    cover, uncover = [], []
    for j in range(n):
        q = (j + 1) / n
        r = Rmax * q ** 1.6
        col, d = _sphere(r, color)
        a = np.clip(r - d + 0.5, 0, 1)
        ring = np.clip(1 - np.abs(d - r) / ring_w, 0, 1) * (0.95 if q < 1 else 0)
        rgbf = col * (1 - ring[..., None]) + ring[..., None]
        alpha = np.maximum(a, ring)
        cover.append(Image.fromarray(np.dstack([rgbf * 255, alpha[..., None] * 255]).astype(np.uint8), "RGBA"))
    for j in range(n):
        q = j / n
        h = Rmax * (1 - (1 - q) ** 1.8) if j else 0.0
        _, d = _sphere(Rmax, color)
        a = np.clip(d - h + 0.5, 0, 1) if j else np.ones_like(d)
        ring = np.clip(1 - np.abs(d - h) / (ring_w + 6 * q), 0, 1) * (1 - q) * 0.95 if j else np.zeros_like(d)
        rgbf = full * (1 - ring[..., None]) + ring[..., None]
        alpha = np.maximum(a, ring)
        uncover.append(Image.fromarray(np.dstack([rgbf * 255, alpha[..., None] * 255]).astype(np.uint8), "RGBA"))
    return cover, uncover


def thumbnail(frames, size=(1280, 720), seed=7):
    """No-text thumbnail: three tilted cards cut from 1080x1920 frames (below the round title) on a purple
    radial gradient with scattered marbles. frames: [left, middle, right] PIL images."""
    W, H = size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.clip(np.hypot((xx - W / 2) / (W * 0.62), (yy - H / 2) / (H * 0.75)), 0, 1)
    c0, c1 = np.array(rgb("#4a1d80"), np.float32), np.array(rgb("#12061f"), np.float32)
    bg = Image.fromarray((c0 * (1 - v[..., None]) + c1 * v[..., None]).astype(np.uint8), "RGB").convert("RGBA")
    rng = np.random.default_rng(seed)
    for _ in range(26):
        r = int(rng.uniform(10, 30))
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        if abs(x - W / 2) < 330 and abs(y - H / 2) < 300:
            continue
        paste_center(bg, marble(r, S.MARBLES[int(rng.integers(len(S.MARBLES)))]), x, y)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W / 2 - 330, H / 2 - 300, W / 2 + 330, H / 2 + 300], fill=(255, 140, 220, 90))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))

    def card(fr, w):
        crop = fr.convert("RGB").crop((0, 330, 1080, 1630))
        h = int(w * crop.height / crop.width)
        im = crop.resize((w, h), Image.LANCZOS).convert("RGBA")
        m = Image.new("L", (w * 4, h * 4), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=26 * 4, fill=255)
        im.putalpha(m.resize((w, h), Image.LANCZOS))
        b = 8
        out = Image.new("RGBA", (w + 2 * b, h + 2 * b), (0, 0, 0, 0))
        mm = Image.new("L", ((w + 2 * b) * 4, (h + 2 * b) * 4), 0)
        ImageDraw.Draw(mm).rounded_rectangle([0, 0, (w + 2 * b) * 4 - 1, (h + 2 * b) * 4 - 1], radius=(26 + b) * 4,
                                             fill=255)
        white = Image.new("RGBA", out.size, (255, 255, 255, 255))
        white.putalpha(mm.resize(out.size, Image.LANCZOS))
        out.alpha_composite(white)
        out.alpha_composite(im, (b, b))
        return out

    def place(c, cx, cy, ang):
        c = c.rotate(ang, resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        a = c.split()[3].point(lambda p: int(p * 0.6))
        blk = Image.new("RGBA", c.size, (0, 0, 0, 255))
        blk.putalpha(a)
        sh.alpha_composite(blk, (int(cx - c.width / 2 + 8), int(cy - c.height / 2 + 16)))
        bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        bg.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))
    place(card(frames[0], 390), W / 2 - 370, H / 2 + 22, 7)
    place(card(frames[2], 390), W / 2 + 370, H / 2 + 22, -7)
    place(card(frames[1], 470), W / 2, H / 2, 0)
    return bg.convert("RGB")
