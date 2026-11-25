"""blue-raspberry / make_board_texture: builds build/board_strips.jpg, the edge-glued cutting-board grain.

Five seamless plank lengths cut from hardwood2_diffuse.jpg (the three.js example wood texture, kept in the
Wildlore asset folder, not in this repo), stacked like the strips of a glued board, two of them mirrored and
each with its own brightness. Rows 1, 3, 5 and 7 of that texture (y = 128, 384, 640, 896, 128 px tall) are
seamless between x = 598 and 1563, so every crop stays inside that span.

  python make_board_texture.py            -> build/board_strips.jpg (958 x 610)
board_scene.py runs this automatically when the file is missing.
"""
import os
import sys
from PIL import Image, ImageEnhance, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.environ.get("WILDLORE_ASSETS", "/home/claude/assets")
SRC = os.path.join(ASSETS, "tex", "hardwood2_diffuse.jpg")
OUT = os.path.join(HERE, "build", "board_strips.jpg")

# --------------------------------------------------------------------------- settings
# (row top y, crop start x, mirrored, brightness) for each strip, top to bottom
STRIPS = [(128, 600, False, 1.0), (384, 604, True, 0.86), (896, 602, False, 0.95), (128, 604, True, 0.80), (384, 600, False, 0.92)]
STRIP_W, TRIM = 958, 3          # crop width, and pixels trimmed off each row edge (hides the plank joints)


def build(src=SRC, out=OUT):
    img = Image.open(src).convert("RGB")
    strips = []
    for y0, x0, flip, k in STRIPS:
        s = img.crop((x0, y0 + TRIM, x0 + STRIP_W, y0 + 128 - TRIM))
        if flip:
            s = ImageOps.mirror(s)
        strips.append(ImageEnhance.Brightness(s).enhance(k))
    board = Image.new("RGB", (STRIP_W, sum(s.size[1] for s in strips)))
    y = 0
    for s in strips:
        board.paste(s, (0, y))
        y += s.size[1]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    board.save(out, quality=95)
    return out


if __name__ == "__main__":
    print(build(*sys.argv[1:3]))
