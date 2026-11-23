"""Renders single frames to PNG (for previews and thumbnails).

Run:  python3 render_frame.py SIM.npz CFG.json --t 9.5 [--t 2.0 ...] [--ns 16] [--out build/frame_{t}.png]
Example (Twinkle thumbnail frame):
  python3 render_frame.py ../marble-drop-sim/build/melody_sim.npz ../marble-drop-sim/build/melody.json --t 9.5 --ns 16 --out preview.png
"""
import os, sys, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from settings import *
from compositor import Renderer, tonemap
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('sim')
ap.add_argument('cfg')
ap.add_argument('--t', type=float, action='append', required=True)
ap.add_argument('--ns', type=int, default=SAMPLES_PER_PIXEL)
ap.add_argument('--exposure', type=float, default=EXPOSURE)
ap.add_argument('--out', default=os.path.join(HERE, 'build', 'frame_{t:.2f}.png'))
a = ap.parse_args()
rd = Renderer(a.sim, a.cfg)
base = tonemap(rd.beauty, a.exposure)
for t in a.t:
    t0 = time.time()
    img = rd.frame(t, ns=a.ns, exposure=a.exposure, base=base)
    path = a.out.format(t=t)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(img).save(path)
    print('saved', path, 'in %.1fs' % (time.time() - t0))
