"""Renders every frame with two single-thread workers (even/odd frames), one per CPU core.
Blender restarts every CHUNK frames so its memory doesn't grow; existing frames are skipped.
Run:  python3 run_render.py      (~80 min for ~660 frames on 2 cores)"""
import os, sys, json, subprocess, threading
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as C

N = json.load(open(C.TIMELINE))['total']
os.makedirs(C.FRAMES, exist_ok=True)


def worker(off):
    log = open(os.path.join(C.BUILD, f'render_log{off}.txt'), 'a')
    for c in range(0, N, C.CHUNK):
        e = min(N, c + C.CHUNK)
        if all(os.path.exists(os.path.join(C.FRAMES, f'f_{g:04d}.png')) for g in range(c + off, e, 2)):
            continue
        cmd = [sys.executable, os.path.join(HERE, 'glass_render.py'), '--', '--start', str(c + off), '--end', str(e),
               '--stride', '2', '--threads', '1']
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)


ts = [threading.Thread(target=worker, args=(o,)) for o in (0, 1)]
for t in ts:
    t.start()
for t in ts:
    t.join()
missing = [g for g in range(N) if not os.path.exists(os.path.join(C.FRAMES, f'f_{g:04d}.png'))]
print('missing frames:', missing if missing else 'none')
