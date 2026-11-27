#!/usr/bin/env python3
"""No-text 1280x720 thumbnails for the long-form, one per entry of settings.THUMBNAILS (YouTube's Test & Compare
takes up to three).

  still: a template's own thumbnail render from its close 16:9 camera (MARBLE_CAM=widethumb, see README)
  grid:  a 2x2 collage of frames from the 16:9 renders and reframed Shorts, to show the variety

python3 thumbs.py                 -> build/thumbnail_<name>.jpg
python3 thumbs.py --render        first makes the missing widethumb renders (~8 min each on 2 cores)
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S  # noqa: E402
import ui  # noqa: E402

GUTTER = 8                      # white lines between collage cells, px at 1280x720


def wide_video(tpl, song):
    d = os.path.join(S.PROPS, tpl, S.WIDE_BUILD, song)
    vids = [p for p in glob.glob(os.path.join(d, "*.mp4")) if not os.path.basename(p).startswith("part")]
    if not vids:
        sys.exit(f"thumbs: no 16:9 render in {d}")
    return vids[0], d


def frame_at(path, t):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                                   "-vf", "scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return Image.frombytes("RGB", (1920, 1080), raw)


def template_still(tpl, build, song, cam=None):
    """A template's own title-free --thumb-only render; made first (with that camera) when --render is given."""
    p = os.path.join(S.PROPS, tpl, build, song, "thumbnail.png")
    if not os.path.exists(p) and cam and "--render" in sys.argv:
        tdir = os.path.join(S.PROPS, tpl)
        env = dict(os.environ, MARBLE_RES="1920x1080", MARBLE_CAM=cam, BUILD_DIR=os.path.join(tdir, build),
                   WATERMARK="")
        subprocess.run([sys.executable, "make_video.py", song, "--thumb-only"], cwd=tdir, env=env, check=True)
    if not os.path.exists(p):
        raise FileNotFoundError(f"{p} (python3 thumbs.py --render makes it)")
    return Image.open(p).convert("RGB")


def cell_image(c):
    if c["src"][0] == "still":
        im = template_still(*c["src"][1:], cam=c.get("cam"))
        t = None
    elif c["src"][0] == "wide":
        path, d = wide_video(*c["src"][1:])
        t = c["t"]
        if isinstance(t, str) and t.startswith("finale"):
            t = json.load(open(os.path.join(d, "timeline.json")))["finale_t"] + float(t[6:] or 0)
    else:
        path, t = os.path.join(S.BUILD, "reframe", f"{c['src'][1]}.mp4"), c["t"]
    if t is not None:
        im = frame_at(path, float(t))
    if c.get("box"):
        x, y, w = c["box"]
        im = im.crop((x, y, x + w, y + round(w * 9 / 16)))
    return im


def grid(cells):
    W, H = 1280, 720
    cw, ch = (W - GUTTER) // 2, (H - GUTTER) // 2
    out = Image.new("RGB", (W, H), "white")
    for i, c in enumerate(cells):
        im = cell_image(c).resize((cw, ch), Image.LANCZOS)
        out.paste(im, ((i % 2) * (cw + GUTTER) + (W - 2 * cw - GUTTER) * (i % 2),
                       (i // 2) * (ch + GUTTER) + (H - 2 * ch - GUTTER) * (i // 2)))
    return out


def main():
    os.makedirs(S.BUILD, exist_ok=True)
    for th in S.THUMBNAILS:
        if "still" in th:
            try:
                img = ui.polish_thumbnail(template_still(th["still"][0], S.THUMB_BUILD, th["still"][1], th["cam"]))
            except FileNotFoundError as e:
                print(f"thumbs: skip {th['name']} ({e})")
                continue
        else:
            try:
                img = ui.polish_thumbnail(grid(th["grid"]))
            except (SystemExit, subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"thumbs: skip {th['name']} ({e})")
                continue
        if th.get("notes"):
            img = ui.add_notes(img, th["notes"])
        out = os.path.join(S.BUILD, f"thumbnail_{th['name']}.jpg")
        img.save(out, quality=92)
        print(out)


if __name__ == "__main__":
    main()
