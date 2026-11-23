"""Loads the set's params.py and build files so the sim scripts share one geometry."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from settings import *
sys.path.insert(0, SET_DIR)
from params import *
import numpy as np


def scene_meta():
    return json.load(open(SCENE_META))


def frame_top_z(y):
    """Height of the frame's top edge (center column) at depth y."""
    c = scene_meta()['camera']
    M = np.array(c['matrix'])
    C, R = M[:3, 3], M[:3, :3]
    TV = (c['sensor_h'] / 2) / c['lens']
    TH = TV * c['W'] / c['H']
    nx = (c['W'] / 2 + 0.5) / c['W'] * 2 - 1
    ny = 1.0
    d = np.array([nx * TH, ny * TV, -1.0]) @ R.T
    d = d / np.linalg.norm(d)
    t = (y - C[1]) / d[1]
    return float((C + t * d)[2])


def spawn_z(y):
    return frame_top_z(y) + MARBLE_R + SPAWN_MARGIN


def make_guards():
    guards = []
    for sgn in (-1, 1):
        s0, s1 = -0.03, L - 0.01
        xe = sgn * (BAR_LEN / 2 + SIDE_GUARD_GAP)
        A = ramp_point(s0, xe, 0.04); B = ramp_point(s1, xe, 0.04)
        yv = (A - B) / np.linalg.norm(A - B); zv = N.copy(); xv = np.cross(yv, zv); xv /= np.linalg.norm(xv); zv = np.cross(xv, yv)
        guards.append(dict(name=f'side{sgn}', center=list(map(float, (A + B) / 2)), dims=[0.01, float(np.linalg.norm(A - B)), SIDE_GUARD_HEIGHT],
                           basis=np.stack([xv, yv, zv], 1).tolist()))
    Bk = np.array([0.0, TOP[1] + 0.014, TOP[2] + 0.2])
    guards.append(dict(name='back', center=list(map(float, Bk)), dims=[0.4, 0.01, 0.5], basis=np.eye(3).tolist()))
    guards.append(dict(kind='ring', name='rimguard', **RIM_GUARD))
    return guards


def base_cfg(duration):
    return dict(guards=make_guards(), duration=float(duration), preroll=PREROLL, phys=dict(PHYS),
                substeps=SUBSTEPS, iters=SOLVER_ITERS)


def note_midi(name):
    """'C6' -> 84, 'F#4' -> 66."""
    pcs = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    pc = pcs[name[0].upper()]
    rest = name[1:]
    while rest and rest[0] in '#b':
        pc += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def bar_for(name):
    m = note_midi(name)
    for k in range(NB):
        if bar_midi(k) == m:
            return k
    raise SystemExit(f'No bar plays {name} (midi {m}). Check SCALE / TOP_MIDI in xylophone-ramp/params.py')


def run_bpy(script, *args):
    import subprocess
    cmd = (BLENDER_CMD + [script, '--']) if BLENDER_CMD else [sys.executable, script]
    subprocess.run(cmd + [str(a) for a in args], check=True)
