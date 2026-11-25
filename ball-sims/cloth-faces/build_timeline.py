"""Writes build/timeline.json from settings.SPEC for the current HERO.
Run:  HERO=duck python3 build_timeline.py"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as CFG
import numpy as np

FPS = 30
SIMS = [os.path.join(CFG.SIMS, f'stage{i}.npz') for i in range(7)]
LABELS = CFG.LABELS
COUNTS = CFG.COUNTS
SPEC = CFG.SPEC[CFG.HERO]
REFILL = CFG.REFILL


def mapping(spec):
    fr = [0.0] * spec['hold']
    for (a, b, sp) in spec['segs']:
        k = float(a)
        while k < b - 1e-6:
            fr.append(k)
            k += sp
    fr.append(float(spec['segs'][-1][1]))
    return fr


def build(spec_override=None, out=CFG.TIMELINE):
    spec = spec_override or SPEC
    maps = [mapping(s) for s in spec]
    tl = dict(sims=SIMS, labels=LABELS, counts=COUNTS, maps=maps,
              stage_len=[len(m) for m in maps], refill_len=REFILL, refill_stagger=CFG.REFILL_STAGGER, fps=FPS)
    tl['total'] = sum(tl['stage_len']) + REFILL
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(tl, open(out, 'w'))
    return tl


if __name__ == '__main__':
    tl = build()
    print(tl['stage_len'], tl['total'], tl['total'] / FPS)
