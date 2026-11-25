import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import settings as C

FPS = 30
HOLD = C.HOLD
END = C.END


def mapping(s):
    d = np.load(os.path.join(C.SIMS, f'stage{s}.npz'))
    bf = [int(x) for x in d['break_frames'] if x >= 0]
    n = len(d['ball_pos'])
    end = min(END[s], n - 1)
    fr = [0.0] * HOLD
    if s == len(C.STAGES) - 1 and bf:
        a, b = max(1, min(bf) - 2), min(end, max(bf) + 8)
        k = 0.0
        while k < a:
            fr.append(k); k += 1.0
        while k < b:
            fr.append(k); k += 0.5
        while k <= end:
            fr.append(k); k += 1.0
    else:
        fr += [float(k) for k in range(0, end + 1)]
    return fr


def build(out=C.TIMELINE):
    maps = [mapping(s) for s in range(len(C.STAGES))]
    tl = dict(sims=[os.path.join(C.SIMS, f'stage{s}.npz') for s in range(len(C.STAGES))],
              labels=[st['label'] for st in C.STAGES], counts=[st['kg'] for st in C.STAGES],
              kgs=[st['kg'] for st in C.STAGES], unit='KG', maps=maps,
              stage_len=[len(m) for m in maps], refill_len=0, fps=FPS)
    tl['total'] = sum(tl['stage_len'])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(tl, open(out, 'w'))
    return tl


if __name__ == '__main__':
    tl = build()
    print(tl['stage_len'], tl['total'], round(tl['total'] / FPS, 2))
