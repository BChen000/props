"""neon-kit: the navy-and-neon look of the Marble Pop Shorts Crown Clash and Ring Escape.

Canvas, the 8-colour marble palette, UI colours, the DejaVu Sans Bold text helper,
easing, colour helpers, a stable hash for stateless particles, and the navy grid
background. Every Ring Escape prop imports this file. Drawing is done with skia-python.

This is a different look from ../style-kit (Sword Roulette: purple, Poppins, pycairo).
"""
import os

import skia

# --------------------------------------------------------------------------- canvas
W, H = 1080, 1920          # YouTube Shorts, portrait
FPS = 30

# --------------------------------------------------------------------------- marble palette
# Order matters: chip order (row 1 left -> right, then row 2).
NAMES = ["RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE", "PINK", "CYAN"]
BALL_COLORS = {
    "RED": (255, 68, 79),
    "BLUE": (52, 137, 255),
    "GREEN": (68, 218, 120),
    "YELLOW": (254, 217, 52),
    "PURPLE": (172, 108, 255),
    "ORANGE": (255, 146, 56),
    "PINK": (254, 118, 198),
    "CYAN": (33, 217, 230),
}

# --------------------------------------------------------------------------- UI colours
BG = (10, 13, 31)              # background edge
BG_MID = (13, 17, 37)          # background gradient stop 0.55
BG_GLOW = (22, 30, 54)         # background gradient centre
GRID = (70, 90, 140)           # grid lines, drawn at alpha 0.07
ARENA = (31, 43, 65)           # arena disc
ARENA_GLOW = (40, 54, 82)      # arena centre glow, alpha 0.55
WHITE = (255, 253, 255)        # title, big numbers
CAPTION = (182, 200, 225)      # bottom caption
SUBCYAN = (123, 219, 244)      # subtitle under the title
YELLOW = (254, 214, 70)        # status line, progress bar
PICK_YELLOW = (254, 217, 52)   # "PICK YOUR COLOR!"
SMALLCAP = (134, 152, 180)     # small caption
GOLD = (255, 205, 60)          # count badges, holder glow, "LAST RING!"
CHIP_FILL = (14, 19, 38)       # chip background, alpha 0.92
DIM = (90, 98, 120)            # dimmed chip outline / dot
DIM_TEXT = (110, 118, 140)     # dimmed chip name
CTA_CYAN = (120, 220, 255)     # "COMMENT YOUR COLOR!"

# --------------------------------------------------------------------------- font
# DejaVu Sans Bold 2.37 (free, Bitstream Vera licence). Install with:  python get_fonts.py
FONT_FAMILY = "DejaVu Sans"
FONT_FILE = "DejaVuSans-Bold.ttf"
FONT_FINGERPRINT = {"text": "RING ESCAPE", "size": 100, "advance_px": 746.0}

_HERE = os.path.dirname(os.path.abspath(__file__))
_TF = None


def typeface():
    """DejaVu Sans Bold: ./fonts/DejaVuSans-Bold.ttf next to this file if present, else the system font."""
    global _TF
    if _TF is not None:
        return _TF
    local = os.path.join(_HERE, "fonts", FONT_FILE)
    tf = None
    if os.path.exists(local):
        tf = skia.Typeface.MakeFromFile(local)
    if tf is None:
        tf = skia.FontMgr().matchFamilyStyle(FONT_FAMILY, skia.FontStyle.Bold())
    if tf is None or tf.getFamilyName() != FONT_FAMILY:
        raise SystemExit("DejaVu Sans Bold not found. Run: python get_fonts.py  "
                         "(or put DejaVuSans-Bold.ttf in neon-kit/fonts/)")
    adv = skia.Font(tf, FONT_FINGERPRINT["size"]).measureText(FONT_FINGERPRINT["text"])
    if abs(adv - FONT_FINGERPRINT["advance_px"]) > 0.5:
        print(f"warning: font advance {adv:.1f}px != {FONT_FINGERPRINT['advance_px']}px; text will not match the videos")
    _TF = tf
    return tf


# --------------------------------------------------------------------------- colour + easing helpers
def col(c, a=1.0):
    return skia.Color4f(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, max(0.0, min(1.0, a)))


def lerp(a, b, x):
    return a + (b - a) * x


def lerpc(a, b, x):
    return tuple(lerp(a[i], b[i], x) for i in range(3))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x):
    x = clamp(x)
    c1 = 1.9
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def hrand(*args):
    """Stable 0..1 hash of the arguments (FNV-1a). Particles use it so any frame renders on its own."""
    h = 2166136261
    for a in args:
        for ch in repr(a).encode():
            h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return (h % 1000003) / 1000003.0


# --------------------------------------------------------------------------- text
def text_w(s, size, spacing=0.0):
    f = skia.Font(typeface(), size)
    return f.measureText(s) + spacing * max(0, len(s) - 1)


def draw_text(c, s, x, y, size, color, alpha=1.0, align="center", spacing=0.0, scale=1.0, maxw=None, shadow=0.0):
    """Draw text with its visual centre near y (baseline = y + 0.36*size).

    align: "center" | "left" | "right" around x. spacing: extra px between letters.
    scale: extra zoom around (x, y) for pop animations. maxw: shrink to fit. shadow: 0..1 soft drop shadow.
    """
    if alpha <= 0.004:
        return
    f = skia.Font(typeface(), size)
    w = f.measureText(s) + spacing * max(0, len(s) - 1)
    k = scale
    if maxw and w * k > maxw:
        k = maxw / w
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    x0 = -w / 2 if align == "center" else (0 if align == "left" else -w)
    base = size * 0.36
    paints = []
    if shadow > 0:
        sp = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.55 * alpha * shadow))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.08))
        paints.append((sp, size * 0.03, size * 0.05))
    paints.append((skia.Paint(AntiAlias=True, Color4f=col(color, alpha)), 0, 0))
    for p, ox, oy in paints:
        if spacing == 0:
            c.drawString(s, x0 + ox, base + oy, f, p)
        else:
            xx = x0
            for ch in s:
                c.drawString(ch, xx + ox, base + oy, f, p)
                xx += f.measureText(ch) + spacing
    c.restore()


# --------------------------------------------------------------------------- background
def make_background(center=(540.0, 990.0), glow=BG_GLOW, grid_origin=None, title=None, subtitle=None,
                    title_y=112, subtitle_y=180):
    """Navy radial gradient + faint 72 px grid (+ optional title/subtitle). Returns a skia.Image (W x H).

    grid_origin: a point the grid passes through (default = center). The videos use the arena centre.
    """
    cx, cy = center
    gx, gy = grid_origin if grid_origin is not None else center
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    sh = skia.GradientShader.MakeRadial(skia.Point(cx, cy), 1150,
                                        [col(glow).toColor(), col(BG_MID).toColor(), col(BG).toColor()],
                                        [0.0, 0.55, 1.0])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))
    gp = skia.Paint(AntiAlias=False, Color4f=col(GRID, 0.07), StrokeWidth=1)
    step = 72
    for x in range(int(gx) % step, W, step):
        c.drawLine(x, 0, x, H, gp)
    for y in range(int(gy) % step, H, step):
        c.drawLine(0, y, W, y, gp)
    if title:
        draw_text(c, title, W / 2, title_y, 84, WHITE, spacing=2)
    if subtitle:
        draw_text(c, subtitle, W / 2, subtitle_y, 34, SUBCYAN, spacing=3.5)
    return surf.makeImageSnapshot()


def new_surface():
    return skia.Surface(W, H)


def to_bgra(img):
    """skia.Image -> HxWx4 uint8 BGRA array (feed to ffmpeg with -pix_fmt bgra)."""
    return img.toarray(colorType=skia.kBGRA_8888_ColorType)


# --------------------------------------------------------------------------- preview
def _preview(path):
    bg = make_background(title="NEON KIT", subtitle="CROWN CLASH / RING ESCAPE LOOK")
    surf = new_surface()
    c = surf.getCanvas()
    c.drawImage(bg, 0, 0)
    for i, name in enumerate(NAMES):
        x = 135 + (i % 4) * 270
        y = 330 + (i // 4) * 250
        c.drawCircle(x, y, 70, skia.Paint(AntiAlias=True, Color4f=col(BALL_COLORS[name])))
        draw_text(c, name, x, y + 110, 30, WHITE)
        r, g, b = BALL_COLORS[name]
        draw_text(c, f"#{r:02x}{g:02x}{b:02x}", x, y + 148, 24, SMALLCAP)
    ui = [("BG", BG), ("ARENA", ARENA), ("WHITE", WHITE), ("CAPTION", CAPTION), ("SUBCYAN", SUBCYAN),
          ("YELLOW", YELLOW), ("SMALLCAP", SMALLCAP), ("GOLD", GOLD), ("CHIP_FILL", CHIP_FILL), ("DIM", DIM)]
    for i, (n, cc) in enumerate(ui):
        x = 110 + (i % 5) * 215
        y = 960 + (i // 5) * 190
        c.drawRoundRect(skia.Rect(x - 80, y - 55, x + 80, y + 55), 14, 14, skia.Paint(AntiAlias=True, Color4f=col(cc)))
        c.drawRoundRect(skia.Rect(x - 80, y - 55, x + 80, y + 55), 14, 14,
                        skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color4f=col(SMALLCAP, 0.6)))
        draw_text(c, n, x, y + 80, 22, CAPTION)
    draw_text(c, "PICK YOUR COLOR!", W / 2, 1420, 76, PICK_YELLOW)
    draw_text(c, "7 RINGS LEFT  •  RED HAS THE CROWN", W / 2, 1510, 34, YELLOW, spacing=1.0)
    draw_text(c, "FIND THE GAP!", W / 2, 1600, 46, CAPTION, spacing=1.2)
    draw_text(c, "DEJAVU SANS BOLD", W / 2, 1700, 28, SMALLCAP, spacing=2.0)
    surf.makeImageSnapshot().save(path, skia.kPNG)


if __name__ == "__main__":
    typeface()
    _preview(os.path.join(_HERE, "preview.png"))
    print("font ok, wrote preview.png")
