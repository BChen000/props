"""Find seeds (matches) with a dramatic story. The physics is real; this only picks which match to show.

  python search.py 0 6000 --outcome upset   # a small ball takes down the BIG sword in the final duel
  python search.py 0 6000 --outcome big     # the BIG sword wins the final duel
  python search.py 0 6000 --outcome any

Filters: 16-27 s fight, final duel = big sword vs one small ball lasting 3-8 s with >= 2 clashes,
big sword >= 3 KOs, winner <= 25 HP, no hit gap > 3.6 s, first KO before 7 s, final blow and
duel near the arena centre. Put the chosen seed in settings.SEED.
"""
import argparse
import math
import os
from multiprocessing import Pool

import sim


def score(seed):
    r = sim.run(seed, record=True)
    if r["winner"] is None or r["winner"] < 0:
        return None
    ch, w = r["chosen"], r["winner"]
    ev = r["events"]
    kills = [e for e in ev if e["type"] == "kill"]
    if len(kills) != sim.N - 1:
        return None
    last = kills[-1]
    final_pair = {last["i"], last["j"]}
    hits = [e["t"] for e in ev if e["type"] == "hit"]
    gaps = [b - a for a, b in zip([0.0] + hits, hits)]
    fk = kills[-2]["t"]  # time when 2 remain
    fb = math.hypot(last["x"] - sim.CX, last["y"] - sim.CY)
    k0 = int((last["t"] - 1.5) / r["dt"])
    k1 = int(last["t"] / r["dt"])
    ds = []
    for k in range(max(0, k0), k1):
        xs, ys, _, _, al = r["states"][k]
        for i in (last["i"], last["j"]):
            ds.append(math.hypot(xs[i] - sim.CX, ys[i] - sim.CY))
    return dict(seed=seed, chosen=sim.NAMES[ch], winner=sim.NAMES[w], big_won=(w == ch),
                fb=round(fb), duel_r=round(sum(ds) / max(1, len(ds))),
                dur=round(r["duration"], 2), big_in_final=(ch in final_pair),
                big_kills=sum(1 for e in kills if e["i"] == ch),
                whp=r["states"][-1][3][w], maxgap=round(max(gaps), 2), first_kill=round(kills[0]["t"], 2),
                duel_len=round(last["t"] - fk, 2),
                duel_clash=sum(1 for e in ev if e["type"] == "clash" and e["t"] > fk),
                duel_hits=sum(1 for e in ev if e["type"] == "hit" and e["t"] > fk),
                order=[(round(e["t"], 1), sim.NAMES[e["j"]], "by", sim.NAMES[e["i"]]) for e in kills])


def keep(s, outcome):
    if s is None or not (16 <= s["dur"] <= 27) or not s["big_in_final"]:
        return False
    if s["big_kills"] < 3 or s["whp"] > 25 or s["maxgap"] > 3.6 or s["first_kill"] > 7:
        return False
    if not (3.0 <= s["duel_len"] <= 8.0) or s["duel_clash"] < 2:
        return False
    if s["fb"] > 0.55 * sim.ARENA_R or s["duel_r"] > 0.6 * sim.ARENA_R:
        return False
    if outcome == "upset" and s["big_won"]:
        return False
    if outcome == "big" and not s["big_won"]:
        return False
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("start", type=int)
    ap.add_argument("stop", type=int)
    ap.add_argument("--outcome", choices=["any", "upset", "big"], default="any")
    args = ap.parse_args()
    out = []
    with Pool(os.cpu_count()) as p:
        for s in p.imap(score, range(args.start, args.stop), chunksize=20):
            if keep(s, args.outcome):
                out.append(s)
    for s in out:
        print(s)
    print(len(out), "candidates")
