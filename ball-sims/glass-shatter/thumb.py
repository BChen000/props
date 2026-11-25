"""No-text thumbnail: renders one finale frame at full quality, then zooms in and grades it.
Writes build/out/thumbnail.jpg.  Run:  python3 thumb.py [FRAME]"""
import os, sys, subprocess
import numpy as np
from PIL import Image, ImageEnhance
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as C

g = int(sys.argv[1]) if len(sys.argv) > 1 else C.THUMB_FRAME
tdir = os.path.join(C.BUILD, 'thumbs')
subprocess.run([sys.executable, os.path.join(HERE, 'glass_render.py'), '--', '--list', str(g), '--spp', '48', '--cspp', '24',
                '--cdiv', '2', '--mscale', '1.0', '--reuse', '0', '--out', tdir], check=True)
im = Image.open(os.path.join(tdir, f'f_{g:04d}.png')).convert('RGB')
w, h = int(C.WIDTH / C.THUMB_ZOOM), int(C.HEIGHT / C.THUMB_ZOOM)
cx, cy = C.THUMB_CENTER
im = im.crop((cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h)).resize((C.WIDTH, C.HEIGHT), Image.LANCZOS)
im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.08)).enhance(1.04)
a = np.asarray(im).astype(np.float32)
yy, xx = np.mgrid[0:C.HEIGHT, 0:C.WIDTH]
d = np.sqrt(((xx - C.WIDTH / 2) / (C.WIDTH * 0.75)) ** 2 + ((yy - C.HEIGHT * 0.55) / (C.HEIGHT * 0.7)) ** 2)
a *= (1 - 0.2 * np.clip(d - 0.45, 0, 1) ** 1.5)[..., None]
os.makedirs(C.OUT, exist_ok=True)
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(C.OUT, 'thumbnail.jpg'), quality=92, optimize=True)
print('saved', os.path.join(C.OUT, 'thumbnail.jpg'))
