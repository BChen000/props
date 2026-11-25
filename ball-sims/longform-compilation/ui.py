"""Everything drawn over the full-screen rounds: round pill and progress marbles, logo, the game panel (countdown,
answer, pick-your-colour), banners, up-next pill, intro and end screen, and the marble-pop transition frames.

Sprites are drawn at 2x and downsampled, so circles and rounded boxes are anti-aliased. Functions return either an
RGBA image or (image, x, y) placed on the 1920x1080 frame.
"""
import itertools
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


def layer(w, h):
    return Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))


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
    """cx, y and size in 1x pixels; im is a 2x layer."""
    f = font(key, size * SS)
    fill = fill if len(fill) == 4 else tuple(fill) + (255,)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((cx * SS, (y + size * 0.07) * SS), s, font=f, anchor=anchor, fill=(0, 0, 0, 150),
                                stroke_width=stroke * SS, stroke_fill=(0, 0, 0, 150))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5 * SS)))
    ImageDraw.Draw(im).text((cx * SS, y * SS), s, font=f, anchor=anchor, fill=fill, stroke_width=stroke * SS,
                            stroke_fill=rgb(stroke_fill) if isinstance(stroke_fill, str) else stroke_fill)


def draw_lines(im, lines, cx, top, key, size, fills, stroke=6, gap=0.98, max_w=None):
    if max_w:
        size = fit_size(lines, key, size, max_w)
    y = top
    for i, l in enumerate(lines):
        draw_text(im, l, cx, y, key, size, fills[i] if isinstance(fills, list) else fills, stroke=stroke)
        y += size * gap
    return y


def rrect(im, box, r, fill, outline=None, ow=0):
    ImageDraw.Draw(im).rounded_rectangle([v * SS for v in box], radius=r * SS, fill=fill, outline=outline,
                                         width=int(ow * SS))


def marble(r, color):
    """Glossy marble sprite (RGBA, 2r x 2r), lit from the top left like the 3D sets."""
    n = max(4, int(2 * r * 4))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    nx = (xx + 0.5) / (n / 2) - 1
    ny = (yy + 0.5) / (n / 2) - 1
    rr = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    L = np.array([-0.45, -0.6, 0.66])
    L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    spec = np.clip(2 * lam * nz - L[2], 0, 1) ** 40
    base = np.array(rgb(color), np.float32) / 255
    col = base[None, None, :] * (0.38 + 0.72 * lam[..., None]) + spec[..., None] * 0.95 + ((1 - nz) ** 3 * 0.35)[..., None]
    img = np.dstack([np.clip(col, 0, 1) * 255, (rr <= 1)[..., None] * 255.0]).astype(np.uint8)
    return Image.fromarray(img, "RGBA").resize((max(2, int(2 * r)), max(2, int(2 * r))), Image.LANCZOS)


def paste_center(dst, src, cx, cy):
    dst.alpha_composite(src, (int(round(cx - src.width / 2)), int(round(cy - src.height / 2))))


def heart(im, cx, cy, s):
    t = np.linspace(0, 2 * np.pi, 400)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    ImageDraw.Draw(im).polygon([((cx + a * s / 17) * SS, (cy + b * s / 17) * SS) for a, b in zip(x, y)],
                               fill=rgb(S.BALL["red"], 255))


def check_badge(im, bx, by, br=30):
    d = ImageDraw.Draw(im)
    d.ellipse([(bx - br) * SS, (by - br) * SS, (bx + br) * SS, (by + br) * SS], fill=rgb(S.BALL["green"], 255),
              outline=(255, 255, 255, 255), width=5 * SS)
    d.line([((bx - 13) * SS, by * SS), ((bx - 3) * SS, (by + 10) * SS), ((bx + 14) * SS, (by - 10) * SS)],
           fill=(255, 255, 255, 255), width=7 * SS, joint="curve")


def wrap_balanced(title, key, max_w, min_size={1: 50, 2: 42, 3: 0}, top=60):
    """Fewest lines that still allow a big font; within a line count, the split whose longest line is shortest."""
    words = title.split()
    best = None
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
        size = min(top, int(max_w / best[0]) // 2 * 2)
        if size >= min_size[n]:
            return best[1], size
    return best[1], max(size, 28)


# ----------------------------------------------------------------------------------------------- always-on corners
def dots_layout(total):
    x0, step = S.PILL_XY[0] + 16, 18.5
    return [(x0 + i * step, S.DOTS_Y) for i in range(total)] + [(x0 + total * step + 12, S.DOTS_Y)]


def corner_left(idx, total, kind, label=None):
    """Round pill + a row of progress marbles (done: coloured, current: ringed, to come: faint, bonus: gold)."""
    w, h = 470, 160
    im = layer(w, h)
    text = label or ("BONUS SONG!" if kind == "bonus" else f"ROUND {idx + 1}")
    f = font("blk", 40 * SS)
    pw = text_w(text, f) / SS + 64
    x0, y0 = S.PILL_XY
    fill = rgb(S.GOLD, 255) if (kind == "bonus" or label) else rgb(S.PINK, 255)
    rrect(im, (0, 0, pw, 70), 35, fill, (255, 255, 255, 255), 4)
    draw_text(im, text, pw / 2, 35, "blk", 40, rgb(S.INK), shadow=False, anchor="mm")
    for i, (x, y) in enumerate(dots_layout(total)):
        x, y = x - x0, y - y0
        if i == total:
            paste_center(im, marble(13 * SS, S.GOLD), x * SS, y * SS)
        elif i < idx or kind == "bonus":
            paste_center(im, marble(8 * SS, S.MARBLES[i % len(S.MARBLES)]), x * SS, y * SS)
        elif i == idx:
            pass
        else:
            ImageDraw.Draw(im).ellipse([(x - 6) * SS, (y - 6) * SS, (x + 6) * SS, (y + 6) * SS], fill=(255, 255, 255, 80))
    return down(im), x0, y0


def corner_logo():
    f = font("blk", 40 * SS)
    tw = text_w(S.CHANNEL, f) / SS
    w, h = int(tw + 76), 70
    im = layer(w, h)
    paste_center(im, marble(25 * SS, S.PINK), 27 * SS, 35 * SS)
    draw_text(im, S.CHANNEL, 62 + tw / 2, 35, "blk", 40, (255, 255, 255), stroke=5, anchor="mm")
    img = down(im)
    return img, S.LOGO_RIGHT - img.width, S.LOGO_Y - img.height // 2


# ----------------------------------------------------------------------------------------------- the game panel
def panel_base(h=None):
    P = S.PANEL
    h = h or P["h"]
    im = layer(P["w"], h)
    rrect(im, (2, 2, P["w"] - 2, h - 2), 30, S.PANEL_RGBA, (255, 255, 255, 190), 3)
    return im


def panel_guess(kind, label=None):
    P = S.PANEL
    im = panel_base()
    cx = P["w"] / 2
    if kind == "bonus":
        draw_lines(im, ["GUESS THE", "NEW SONG!"], cx, 28, "blk", 60, [(255, 255, 255), rgb(S.GOLD)], max_w=P["w"] - 50)
        draw_text(im, "Never posted before!", cx, P["h"] - 70, "xb", 32, rgb(S.GOLD), stroke=4)
    else:
        if label:
            draw_text(im, label, cx, 22, "blk", 40, rgb(S.GOLD), stroke=5)
        draw_lines(im, ["GUESS THE", "SONG!"], cx, 74 if label else 28, "blk", 60, [(255, 255, 255), rgb(S.YELLOW)],
                   max_w=P["w"] - 50)
        draw_text(im, "Shout it out!", cx, P["h"] - 70, "xb", 34, (255, 255, 255), stroke=5)
    return down(im), P["x"], P["y"]


def countdown(n, total, r=104):
    im = layer(2 * r + 30, 2 * r + 30)
    c = r + 15
    d = ImageDraw.Draw(im)
    box = [(c - r) * SS, (c - r) * SS, (c + r) * SS, (c + r) * SS]
    d.ellipse(box, fill=(0, 0, 0, 90))
    d.ellipse(box, outline=(255, 255, 255, 70), width=13 * SS)
    d.arc(box, start=-90, end=-90 + 360 * n / total, fill=rgb(S.YELLOW, 255), width=13 * SS)
    draw_text(im, str(n), c, c + 6, "blk", 128, rgb(S.YELLOW), stroke=7, anchor="mm")
    img = down(im)
    return img, S.PANEL["x"] + S.PANEL["w"] // 2 - img.width // 2, S.PANEL["y"] + 300 - img.height // 2


def answer_card(title, w, extra=None, points=True, header="IT'S...", icon=None, color=None):
    """Header + white card with the answer (balanced wrap) + optional lines; sized to its content."""
    lines, size = wrap_balanced(title, "blk", w - 60)
    icon_h = 120 if icon else 0
    box_h = len(lines) * size * 1.08 + 46 + icon_h
    total_h = 78 + box_h + 24 + (48 if extra else 0) + (48 if points else 0) + 10
    im = layer(w, total_h)
    cx = w / 2
    draw_text(im, header, cx, 4, "blk", 54, rgb(S.YELLOW), stroke=6)
    top = 78
    rrect(im, (14, top, w - 14, top + box_h), 30, (255, 255, 255, 255), rgb(S.BALL["green"], 255), 7)
    y = top + 22
    if icon == "heart":
        heart(im, cx, y + 54, 56)
        y += icon_h
    elif icon == "marble":
        paste_center(im, marble(50 * SS, S.BALL[color]), cx * SS, (y + 54) * SS)
        y += icon_h
    for l in lines:
        draw_text(im, l, cx, y, "blk", size, rgb(S.BALL[color]) if (icon == "marble" and color) else rgb(S.INK),
                  shadow=False)
        y += size * 1.08
    check_badge(im, w - 30, top + 6)
    yb = top + box_h + 22
    if extra:
        draw_text(im, extra, cx, yb, "xb", 32, (255, 255, 255), stroke=5)
        yb += 48
    if points:
        draw_text(im, "Got it? +1 point!", cx, yb, "xb", 32, rgb(S.YELLOW), stroke=5)
    return down(im)


def panel_answer(title, extra=None):
    """Panel after the reveal: the answer card on top, the equalizer (a widget) fills the bottom."""
    P = S.PANEL
    im = panel_base()
    card = answer_card(title, P["w"] - 24, extra=extra)
    out = down(im)
    out.alpha_composite(card, (12, 16))
    return out, P["x"], P["y"]


def pop_frames(img, scales=(0.55, 0.82, 1.06, 1.12, 1.05)):
    return [img.resize((max(2, int(img.width * s) // 2 * 2), max(2, int(img.height * s) // 2 * 2)), Image.LANCZOS)
            for s in scales]


def panel_race_start(colors, sub):
    P = S.PANEL
    h = 470
    im = panel_base(h)
    cx = P["w"] / 2
    draw_lines(im, ["PICK YOUR", "COLOR!"], cx, 26, "blk", 66, [(255, 255, 255), rgb(S.YELLOW)], max_w=P["w"] - 50)
    n = len(colors)
    r = 44 if n <= 2 else 34
    gap = 2 * r + (30 if n <= 2 else 16)
    x0 = cx - (n - 1) * gap / 2
    for i, c in enumerate(colors):
        paste_center(im, marble(r * SS, S.BALL[c]), (x0 + i * gap) * SS, 240 * SS)
        draw_text(im, c.upper(), x0 + i * gap, 240 + r + 10, "xb", 24 if n <= 2 else 20, (255, 255, 255), stroke=4)
    draw_text(im, sub, cx, 350, "xb", 32, (255, 255, 255), stroke=5)
    draw_text(im, "Comment your pick!", cx, 400, "sb", 28, (230, 230, 240), stroke=4)
    return down(im), P["x"], P["y"]


def chip_race(colors):
    n = len(colors)
    w, h = 64 + 52 * n + 150, 76
    im = layer(w, h)
    rrect(im, (2, 2, w - 2, h - 2), 36, S.PANEL_RGBA, (255, 255, 255, 190), 3)
    draw_text(im, "PICK:", 70, h / 2, "blk", 30, rgb(S.YELLOW), stroke=4, anchor="mm")
    for i, c in enumerate(colors):
        paste_center(im, marble(21 * SS, S.BALL[c]), (140 + i * 52) * SS, (h / 2) * SS)
    img = down(im)
    return img, S.PANEL["x"] + S.PANEL["w"] - img.width, S.PANEL["y"]


def panel_race_end():
    P = S.PANEL
    h = 210
    im = panel_base(h)
    draw_lines(im, ["DID YOUR", "COLOR WIN?"], P["w"] / 2, 34, "blk", 64, [(255, 255, 255), rgb(S.YELLOW)],
               max_w=P["w"] - 50)
    return down(im), P["x"], P["y"]


def banner(text, y=22, color=S.YELLOW):
    f = font("blk", 50 * SS)
    tw = text_w(text, f) / SS
    w, h = int(tw + 80), 86
    im = layer(w, h)
    rrect(im, (2, 2, w - 2, h - 2), 43, S.PANEL_RGBA, (255, 255, 255, 200), 3)
    draw_text(im, text, w / 2, h / 2 + 2, "blk", 50, rgb(color), stroke=5, anchor="mm")
    img = down(im)
    return img, (S.W - img.width) // 2, y


def run_reveal(answer, icon=None, color=None):
    card = answer_card(answer, 520, points=False, icon=icon, color=color)
    return card, (S.W - card.width) // 2, (S.H - card.height) // 2 - 40


def upnext(text, gold=False):
    f1, f2 = font("xb", 26 * SS), font("blk", 40 * SS)
    tw = max(text_w("UP NEXT", f1), text_w(text, f2)) / SS
    w, h = int(tw + 140), 118
    im = layer(w, h)
    rrect(im, (2, 2, w - 2, h - 2), 28, (12, 5, 24, 230), rgb(S.GOLD if gold else S.PINK, 255), 4)
    d = ImageDraw.Draw(im)
    tx = 30
    d.polygon([(tx * SS, (h / 2 - 20) * SS), (tx * SS, (h / 2 + 20) * SS), ((tx + 32) * SS, (h / 2) * SS)],
              fill=rgb(S.YELLOW, 255))
    d.text(((tx + 54) * SS, 20 * SS), "UP NEXT", font=f1, fill=rgb(S.YELLOW, 255))
    d.text(((tx + 54) * SS, 50 * SS), text, font=f2, fill=(255, 255, 255, 255))
    return down(im)


# ----------------------------------------------------------------------------------------------- intro / end
def intro_overlay():
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:S.H, 0:S.W].astype(np.float32)
    v = np.clip(1 - (((xx - S.W / 2) / (S.W * 0.42)) ** 2 + ((yy - S.H * 0.47) / (S.H * 0.30)) ** 2), 0, 1)
    shade = (np.clip(v * 1.6, 0, 1) * 150).astype(np.uint8)
    im.putalpha(Image.fromarray(shade))
    ui = layer(S.W, S.H)
    t1, t2 = S.INTRO_LINES
    draw_lines(ui, [t1], S.W / 2, 360, "blk", 118, [rgb(S.YELLOW)], stroke=9, max_w=S.W - 200)
    draw_text(ui, t2, S.W / 2, 520, "blk", 56, (255, 255, 255), stroke=7)
    for i in range(7):
        paste_center(ui, marble(30 * SS, S.MARBLES[i]), (S.W / 2 + (i - 3) * 86) * SS, 660 * SS)
    im.alpha_composite(down(ui))
    return im


def endscreen_overlay():
    """Right-hand end screen: thanks + comment ask, a frame for YouTube's video element and a circle for Subscribe."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    ui = layer(S.W, S.H)
    x0, x1 = 1130, 1890
    rrect(ui, (x0, 40, x1, 1010), 36, (12, 5, 24, 215), (255, 255, 255, 200), 3)
    cx = (x0 + x1) / 2
    t, l1, l2 = S.END_LINES
    draw_lines(ui, t, cx, 70, "blk", 70, [(255, 255, 255), rgb(S.YELLOW)], max_w=x1 - x0 - 60)
    draw_text(ui, l1, cx, 238, "xb", 34, (255, 255, 255), stroke=5)
    draw_text(ui, l2, cx, 284, "xb", 34, rgb(S.YELLOW), stroke=5)
    bw, bh = 560, 315
    top = 360
    rrect(ui, (cx - bw / 2, top, cx + bw / 2, top + bh), 20, (255, 255, 255, 28), (255, 255, 255, 210), 5)
    d = ImageDraw.Draw(ui)
    d.polygon([((cx - 24) * SS, (top + bh / 2 - 32) * SS), ((cx - 24) * SS, (top + bh / 2 + 32) * SS),
               ((cx + 34) * SS, (top + bh / 2) * SS)], fill=(255, 255, 255, 170))
    draw_text(ui, "WATCH NEXT", cx, top + bh + 14, "blk", 36, (255, 255, 255), stroke=5)
    r, cy = 78, 845
    d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=(255, 255, 255, 28),
              outline=(255, 255, 255, 210), width=5 * SS)
    draw_text(ui, "SUBSCRIBE", cx, cy + r + 10, "blk", 34, rgb(S.BALL["red"]), stroke=5)
    im.alpha_composite(down(ui))
    return im


# ----------------------------------------------------------------------------------------------- transitions
_grid = None


def _sphere(r, color):
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
    """The "marble pop": n cover frames (a glossy marble grows from the centre until it fills the frame) and n uncover
    frames (it bursts open from the centre, a white rim racing outward). RGBA, full frame."""
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
        cover.append(Image.fromarray(np.dstack([rgbf * 255, np.maximum(a, ring)[..., None] * 255]).astype(np.uint8), "RGBA"))
    for j in range(n):
        q = j / n
        hole = Rmax * (1 - (1 - q) ** 1.8) if j else 0.0
        _, d = _sphere(Rmax, color)
        a = np.clip(d - hole + 0.5, 0, 1) if j else np.ones_like(d)
        ring = np.clip(1 - np.abs(d - hole) / (ring_w + 6 * q), 0, 1) * (1 - q) * 0.95 if j else np.zeros_like(d)
        rgbf = full * (1 - ring[..., None]) + ring[..., None]
        uncover.append(Image.fromarray(np.dstack([rgbf * 255, np.maximum(a, ring)[..., None] * 255]).astype(np.uint8), "RGBA"))
    return cover, uncover


def polish_thumbnail(img):
    """No-text thumbnail from a 16:9 render: a touch more saturation and contrast, a soft vignette, 1280x720."""
    from PIL import ImageEnhance
    im = img.convert("RGB").resize((1280, 720), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.25)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    v = ((xx - 640) / 640) ** 2 + ((yy - 360) / 360) ** 2
    a *= np.clip(1.06 - 0.22 * v, 0.7, 1.06)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
