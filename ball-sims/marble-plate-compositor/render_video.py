"""Renders a range of frames to a silent H.264 mp4 (1080x1920, 30 fps).

Run:  python3 render_video.py SIM.npz CFG.json START_FRAME END_FRAME OUT.mp4 [--ns 8] [--overlay FILE.py]
--overlay loads a Python file with apply_overlay(frame, t) and draws it on every frame
(e.g. ../marble-counter/counter.py for the x1 ... x40! counter).
Split long videos into two ranges and run them at the same time (one per CPU core),
then join with ffmpeg's concat demuxer (-c copy). xylophone-song-template does this for you.
"""
import os, sys, argparse, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from settings import *
from compositor import Renderer, tonemap
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('sim')
ap.add_argument('cfg')
ap.add_argument('f0', type=int)
ap.add_argument('f1', type=int)
ap.add_argument('out')
ap.add_argument('--ns', type=int, default=SAMPLES_PER_PIXEL)
ap.add_argument('--exposure', type=float, default=EXPOSURE)
ap.add_argument('--overlay', default=None)
a = ap.parse_args()
overlay = None
if a.overlay:
    import importlib.util
    spec = importlib.util.spec_from_file_location('overlay_mod', a.overlay)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    overlay = mod.apply_overlay

rd = Renderer(a.sim, a.cfg)
base = tonemap(rd.beauty, a.exposure)
tmp = a.out[:-4] + '.tmp.mp4'
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-c:v', 'libx264', '-preset', X264_PRESET, '-crf', str(CRF), '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
t0 = time.time()
last = None
for f in range(a.f0, a.f1):
    t = f / FPS
    Pc, _ = rd.centers(t)
    if last is not None and np.abs(Pc - last[0]).max() < 2e-5:
        frame = last[1]
    else:
        frame = rd.frame(t, ns=a.ns, exposure=a.exposure, base=base)
        last = (Pc, frame)
    p.stdin.write((overlay(frame, t) if overlay else frame).tobytes())
    if (f - a.f0) % 10 == 0:
        print(f'frame {f} ({f - a.f0 + 1}/{a.f1 - a.f0}) {time.time() - t0:.0f}s', flush=True)
p.stdin.close()
if p.wait() == 0:
    os.replace(tmp, a.out)
    print('DONE', a.out, '%.0fs' % (time.time() - t0))
else:
    sys.exit('ffmpeg failed')
