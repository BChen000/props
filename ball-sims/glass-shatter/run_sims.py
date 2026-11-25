"""Runs the 7 shatter sims (pybullet) in two parallel queues, one per CPU core. ~15 min on 2 cores.
Run:  python3 run_sims.py"""
import os, sys, subprocess, threading
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as C

os.makedirs(C.SIMS, exist_ok=True)


def run(stages):
    for s in stages:
        cmd = [sys.executable, os.path.join(HERE, 'glass_sim.py'), '--stage', str(s)] + C.SIM_ARGS[s].split()
        with open(os.path.join(C.SIMS, f'log{s}.txt'), 'w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('sim done', s, flush=True)


qs = [threading.Thread(target=run, args=([6, 0, 2, 4],)), threading.Thread(target=run, args=([5, 1, 3],))]
for q in qs:
    q.start()
for q in qs:
    q.join()
