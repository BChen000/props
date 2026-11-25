"""Renders every frame with two single-thread workers (even/odd frames), one per CPU core.

Each worker restarts Blender every CHUNK frames because a long Blender session slowly grows in memory.
Frames that already exist are skipped, so it is safe to stop and re-run.
Run:  HERO=duck python3 run_render.py      (~60-80 min for ~600 frames on 2 cores)
"""
import os, sys, json, subprocess, threading
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as CFG

N = json.load(open(CFG.TIMELINE))['total']
os.makedirs(CFG.FRAMES, exist_ok=True)


def worker(off):
    log = open(os.path.join(CFG.BUILD, f'render_log{off}.txt'), 'a')
    for c in range(0, N, CFG.CHUNK):
        e = min(N, c + CFG.CHUNK)
        if all(os.path.exists(os.path.join(CFG.FRAMES, f'f_{g:04d}.png')) for g in range(c + off, e, 2)):
            continue
        cmd = [sys.executable, os.path.join(HERE, 'render_frames.py'), '--', '--start', str(c + off), '--end', str(e),
               '--stride', '2', '--threads', '1']
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)


ts = [threading.Thread(target=worker, args=(o,)) for o in (0, 1)]
for t in ts:
    t.start()
for t in ts:
    t.join()
missing = [g for g in range(N) if not os.path.exists(os.path.join(CFG.FRAMES, f'f_{g:04d}.png'))]
print('missing frames:', missing if missing else 'none')
