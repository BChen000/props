"""A quick look at a studio colour before rendering: the static set without marbles, at 540x960, in about 5 s.

Usage:
  python3 preview_look.py <song>                 the song's hue, sat and bright from songs.py
  python3 preview_look.py <hue> [sat] [bright]   any look, e.g. 100 0.9 or 40 1 0.35

Writes build/look_previews/hue<h>_sat<s>_bright<b>.png. Noisy (few samples), but enough to judge the colour; render
--stills of the real thing before a full video.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
try:
    hue, sat, bright = (float(a) for a in (args + ["1", "1"])[:3]) if len(args) > 1 else (float(args[0]), 1.0, 1.0)
except ValueError:
    from songs import SONGS
    s = SONGS[args[0]]
    hue, sat, bright = s.get("hue", 0.0), s.get("sat", 1.0), s.get("bright", 1.0)

import look
look.set_hue(hue, sat, bright)
import scene as S
import tracers
from PIL import Image

out = os.path.join(BUILD, "look_previews")
os.makedirs(out, exist_ok=True)
tag = "hue%g_sat%g_bright%g" % (hue, sat, bright)
scene_txt = os.path.join(out, tag + "_scene.txt")
S.write_scene(scene_txt, 540, 960, 9, 16)
tracers.render_static(tracers.build("boxtrace", BUILD), scene_txt, os.path.join(out, tag))
png = os.path.join(out, tag + ".png")
Image.open(os.path.join(out, tag + "_preview.ppm")).save(png)
for f in os.listdir(out):
    if f.startswith(tag + "_") and not f.endswith(".png"):
        os.remove(os.path.join(out, f))
print(png)
