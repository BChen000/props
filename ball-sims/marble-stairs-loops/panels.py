"""Side panels of the loops, drawn with Pillow in the look of the other Marble Pop streams (../marble-live-streams):
"pick your marble" with the 7 marble colors, a "now playing" card per song, and the medley's name. Every panel sits
outside the middle 9:16 strip (x 656-1264), which YouTube shows on its own in the Shorts feed.
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ===================================================================== SETTINGS (shipped values)
FONT = os.environ.get("LOOP_FONT", os.path.join(HERE, "..", "marble-raytrace-kit", "fonts", "Montserrat[wght].ttf"))
W, H = 1920, 1080
STRIP = (656, 1264)             # the middle 9:16 strip: keep it clear
LAYOUT = {                      # panel boxes (x0, y0, x1, y1)
    "stairs": dict(pick=(1404, 60, 1856, 392), now=(1404, 760, 1856, 1010), label=(64, 878, 592, 1010)),
    "twin": dict(pick=(64, 60, 516, 392), now=(64, 760, 516, 1010), label=(1328, 878, 1856, 1010)),
}
LABEL = {"stairs": ("MARBLE LULLABIES", "calm bells, nonstop"),
         "twin": ("MARBLE MUSIC BOX", "classics on bells, nonstop")}
DOTS = [(246, 246, 246), (88, 196, 250), (255, 122, 98), (255, 112, 190), (92, 228, 168), (255, 206, 64),
        (172, 128, 255)]
GOLD = (255, 206, 64)
WHITE = (255, 255, 255)
SOFT = (200, 210, 230)
# ================================================================= END SETTINGS


def font(size, weight="ExtraBold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def panel(d, box):
    d.rounded_rectangle(box, 34, fill=(8, 12, 30, 165), outline=(255, 255, 255, 46), width=2)


def center_text(d, cx, y, s, f, fill):
    d.text((cx - d.textlength(s, font=f) / 2, y), s, font=f, fill=fill)
    return y + f.getbbox(s)[3]


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def dots(d, cx, y, colors, r=22, gap=14, per_row=4):
    rows = [colors[i:i + per_row] for i in range(0, len(colors), per_row)]
    for ri, row in enumerate(rows):
        total = len(row) * 2 * r + (len(row) - 1) * gap
        x0 = cx - total / 2 + r
        for i, c in enumerate(row):
            x, yy = x0 + i * (2 * r + gap), y + r + ri * (2 * r + gap)
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=c + (255,), outline=(255, 255, 255, 120), width=3)
            d.ellipse((x - r * 0.45, yy - r * 0.62, x - r * 0.05, yy - r * 0.25), fill=(255, 255, 255, 110))
    return y + len(rows) * (2 * r + gap)


def _check(box):
    x0, _, x1, _ = box
    assert x1 <= STRIP[0] or x0 >= STRIP[1], f"panel {box} overlaps the 9:16 strip"


def base_panel(path, loop):
    """Pick-your-marble panel and the medley label."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lay = LAYOUT[loop]
    box = lay["pick"]
    _check(box)
    panel(d, box)
    cx = (box[0] + box[2]) / 2
    y = center_text(d, cx, box[1] + 30, "PICK YOUR", font(44, "Black"), WHITE)
    y = center_text(d, cx, y + 4, "MARBLE", font(44, "Black"), GOLD)
    y = dots(d, cx, y + 28, DOTS, r=21, gap=14, per_row=4)
    center_text(d, cx, y + 12, "and comment your color!", font(25, "SemiBold"), SOFT)
    box = lay["label"]
    _check(box)
    panel(d, box)
    cx = (box[0] + box[2]) / 2
    title, sub = LABEL[loop]
    y = center_text(d, cx, box[1] + 26, title, font(38, "Black"), WHITE)
    center_text(d, cx, y + 10, sub, font(25, "SemiBold"), SOFT)
    im.save(path)


def song_panel(path, loop, name, k, n):
    """'Now playing' card for one song."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = LAYOUT[loop]["now"]
    _check(box)
    panel(d, box)
    cx = (box[0] + box[2]) / 2
    y = center_text(d, cx, box[1] + 26, "NOW PLAYING", font(26, "Bold"), GOLD)
    f = font(40, "Black")
    lines = wrap(d, name, f, box[2] - box[0] - 56)[:2]
    y += 16
    for ln in lines:
        y = center_text(d, cx, y, ln, f, WHITE) + 8
    center_text(d, cx, box[3] - 50, f"song {k} of {n}", font(24, "SemiBold"), SOFT)
    im.save(path)
