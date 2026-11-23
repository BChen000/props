"""Find races (seeds) with a good story for retention, using the physics in settings.PHYS.

Score rewards: a win at 22-24 s; the first ring breaking 0.45-0.9 s in (an early hook); no gap
over 3.2 s between ring breaks; a final-ring stretch of 4.8-6.8 s; many different colours
breaking rings; no streak longer than 2; an underdog winner (few earlier breaks); near misses on
the last gap, by different marbles and close to the end. AVOID_WINNER gets a small penalty
(GREEN won the previous episode).
The physics decides every race. This only picks which one to show.

  python search.py 0 40000        -> top 12 printed, top 40 saved to out/top_seeds.json
Then put the seed you like in settings.py -> SEED, and run `python sim.py record`.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

import settings as S
import sim

AVOID_WINNER = "GREEN"
NRG = len(S.PHYS["gaps"])


def story(sd):
    r = sim.run(sd, S.PHYS)
    b = sim.breaks(r)
    if r["winner"] < 0 or len(b) != NRG:
        return None
    t = [x[0] for x in b]
    who = [x[1] for x in b]
    Tw, w = t[-1], who[-1]
    fin = [(e[1] * S.DT, int(e[2])) for e in r["ev"] if int(e[0]) == sim.EV_END and int(e[3]) == NRG - 1]
    nm = [x for x in fin if t[-2] < x[0] < Tw - 0.25]
    nm_late = [x for x in nm if x[0] > Tw - 2.2 and x[1] != w]
    nm_who = len(set(x[1] for x in nm))
    gaps_iv = np.diff([0] + t[:-1])
    streak = ms = 1
    for a, bb in zip(who, who[1:]):
        streak = streak + 1 if a == bb else 1
        ms = max(ms, streak)
    s = dict(seed=sd, Tw=float(Tw), t1=float(t[0]), fs=float(Tw - t[-2]), maxiv=float(gaps_iv.max()), distinct=len(set(who[:-1])),
             streak=ms, wprev=who[:-1].count(w), nm=len(nm), nm_late=len(nm_late), nm_who=nm_who,
             winner=S.NAMES[w], breaks=[round(float(x), 2) for x in t], who=[S.NAMES[i] for i in who])
    sc = 0.0
    sc -= max(0, 22.0 - Tw) * 5 + max(0, Tw - 24.0) * 5
    sc -= max(0, 0.45 - t[0]) * 12 + max(0, t[0] - 0.9) * 8
    sc -= max(0, 4.8 - s["fs"]) * 1.5 + max(0, s["fs"] - 6.8) * 1.5
    sc -= max(0, s["maxiv"] - 3.2) * 3
    sc += min(s["distinct"], 7) * 1.0
    sc -= max(0, ms - 2) * 3
    sc += 2.5 if s["wprev"] == 0 else (1.0 if s["wprev"] == 1 else 0)
    sc += min(len(nm), 8) * 0.5 + min(len(nm_late), 3) * 1.2 + min(nm_who, 5) * 0.8
    sc -= 1.5 if S.NAMES[w] == AVOID_WINNER else 0
    s["score"] = sc
    return s


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    t0 = time.time()
    with Pool(os.cpu_count() or 2) as pool:
        res = [x for x in pool.map(story, range(a, b), chunksize=50) if x]
    res.sort(key=lambda s: -s["score"])
    print("scored", len(res), "races in", round(time.time() - t0, 1), "s")
    for s in res[:12]:
        print(f"{s['score']:6.2f} seed {s['seed']:6d} {s['winner']:6s} win {s['Tw']:5.2f}s first {s['t1']:.2f}s "
              f"last-ring {s['fs']:.1f}s near-misses {s['nm']} ({s['nm_who']} marbles, {s['nm_late']} late)")
        print("        ", list(zip(s["breaks"], s["who"])))
    os.makedirs(S.OUT_DIR, exist_ok=True)
    with open(os.path.join(S.OUT_DIR, "top_seeds.json"), "w") as f:
        json.dump(res[:40], f, indent=1)
