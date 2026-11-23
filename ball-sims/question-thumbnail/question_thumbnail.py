"""question-thumbnail: a 1080x1920 Shorts thumbnail with a big two-line question over a game scene.

Line 1 is white, line 2 is huge yellow with a warm glow. Both have a thick dark outline and a soft
drop shadow. A glowing crown sits between the text and the scene. The default scene is the
Ring Escape arena zoomed 1.5x at sim time 5.2 s, with no crown on any marble so the winner isn't
spoiled. Pass --scene to put any image under the text instead.

  python question_thumbnail.py                       -> out/thumbnail.png + out/thumbnail.jpg (q92, < 2 MB)
  python question_thumbnail.py --scene frame.png     -> same layout over your own 1080x1920 image
  python question_thumbnail.py --line1 "WHO WINS" --line2 "THE CROWN?"
"""
import argparse
import os
import sys

import skia

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ("neon-kit", "crown-icon", "ring-escape"):
    sys.path.append(os.path.join(_HERE, "..", _p))
from crown_icon import draw_crown  # noqa: E402
from neon_kit import BG, H, PICK_YELLOW, W, col, make_background, typeface  # noqa: E402

# --------------------------------------------------------------------------- settings
LINE1, LINE2 = "WHO ESCAPES", "FIRST?"
LINE1_Y, LINE1_SIZE, LINE1_MAXW = 250, 132, 1010
LINE2_Y, LINE2_SIZE, LINE2_MAXW = 440, 215, 980
LINE1_FILL, LINE2_FILL = (255, 255, 255), PICK_YELLOW
LINE2_GLOW = (255, 190, 40)
OUTLINE, OUTLINE_W = (8, 10, 26), 14
CROWN_X, CROWN_Y, CROWN_SCALE, CROWN_GLOW = 540.0, 640.0, 3.0, 1.6
SCENE_T = 5.2                  # Ring Escape sim time to show (just after RED broke ring 3)
SCENE_ZOOM, SCENE_CY = 1.5, 1300.0   # arena zoom and where its centre lands on the thumbnail
BG_CENTER, BG_GLOW = (540.0, 1235.0), (26, 36, 66)
JPG_QUALITY = 92


def outlined(c, s, x, y, size, fill, stroke=OUTLINE, sw=OUTLINE_W, maxw=1000, glow=None):
    """Centred text: drop shadow, optional glow, outline, fill. Shrinks to maxw."""
    f = skia.Font(typeface(), size)
    w = f.measureText(s)
    k = min(1.0, maxw / w)
    c.save()
    c.translate(x, y)
    c.scale(k, k)
    x0 = -w / 2
    base = size * 0.36
    blob = skia.TextBlob.MakeFromString(s, f)
    sh = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.6))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
    c.drawTextBlob(blob, x0 + 6, base + 10, sh)
    if glow:
        gp = skia.Paint(AntiAlias=True, Color4f=col(glow, 0.55))
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
        c.drawTextBlob(blob, x0, base, gp)
    st = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=sw, Color4f=col(stroke),
                    StrokeJoin=skia.Paint.kRound_Join)
    c.drawTextBlob(blob, x0, base, st)
    c.drawTextBlob(blob, x0, base, skia.Paint(AntiAlias=True, Color4f=col(fill)))
    c.restore()


def ring_escape_scene(c, t=SCENE_T, zoom=SCENE_ZOOM, cy=SCENE_CY):
    """Draw the Ring Escape arena (rings, marbles, effects) at sim time t, zoomed, no crown."""
    import settings as S
    from render import Scene
    from timeline import Race
    race = Race()
    scene = Scene(race)
    scene.show_crown = False
    scene.show_holder = False
    st = dict(phase="race", t=t, tau=race.tau_of(t), rate=1.0, u=0.0)
    c.save()
    c.translate(S.CX, cy)
    c.scale(zoom, zoom)
    c.translate(-S.CX, -S.CY)
    scene.draw_arena(c, st, 0.0)
    c.restore()


def make(out_png, line1=LINE1, line2=LINE2, scene_path=None):
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    if scene_path:
        img = skia.Image.open(scene_path)
        c.drawImageRect(img, skia.Rect(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear))
    else:
        c.drawImage(make_background(center=BG_CENTER, glow=BG_GLOW, grid_origin=(0, 0)), 0, 0)
        ring_escape_scene(c)
    draw_crown(c, CROWN_X, CROWN_Y, CROWN_SCALE, 1.0, glow=CROWN_GLOW)
    outlined(c, line1, W / 2, LINE1_Y, LINE1_SIZE, LINE1_FILL, maxw=LINE1_MAXW)
    outlined(c, line2, W / 2, LINE2_Y, LINE2_SIZE, LINE2_FILL, maxw=LINE2_MAXW, glow=LINE2_GLOW)
    img = surf.makeImageSnapshot()
    img.save(out_png, skia.kPNG)
    return img


def to_jpg(png, jpg, quality=JPG_QUALITY):
    from PIL import Image
    Image.open(png).convert("RGB").save(jpg, quality=quality, optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", help="1080x1920 image to use instead of the Ring Escape arena")
    ap.add_argument("--line1", default=LINE1)
    ap.add_argument("--line2", default=LINE2)
    ap.add_argument("--preview", action="store_true", help="also write preview.png")
    a = ap.parse_args()
    out = os.path.join(_HERE, "out")
    os.makedirs(out, exist_ok=True)
    png = os.path.join(out, "thumbnail.png")
    make(png, a.line1, a.line2, a.scene)
    to_jpg(png, os.path.join(out, "thumbnail.jpg"))
    if a.preview:
        make(os.path.join(_HERE, "preview.png"), a.line1, a.line2, a.scene)
    print("wrote out/thumbnail.png and out/thumbnail.jpg")
