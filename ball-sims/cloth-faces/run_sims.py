"""Runs the 7 blanket sims (one per face count) in two parallel queues, one per CPU core.

Run:  HERO=duck python3 run_sims.py      (python3 = the interpreter that has bpy 5.3.0)
The 1,000,000 stage (62,500 simulated faces) takes ~25 min on one core; the others take ~10 min together.
"""
import os, sys, subprocess, threading
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as CFG

os.makedirs(CFG.SIMS, exist_ok=True)
args = CFG.SIM_ARGS[CFG.HERO]


def run(stages):
    for s in stages:
        cmd = [sys.executable, os.path.join(HERE, 'sim.py'), '--', '--stage', str(s)] + args[s].split()
        with open(os.path.join(CFG.SIMS, f'log{s}.txt'), 'w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('sim done', s, flush=True)


qs = [threading.Thread(target=run, args=([6],)), threading.Thread(target=run, args=([0, 1, 2, 3, 4, 5],))]
for q in qs:
    q.start()
for q in qs:
    q.join()
