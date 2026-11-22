"""Balance check for settings.PHYSICS over many seeds.

  python tune.py 150                              # current settings
  python tune.py 150 small.dmg=20 big.dmg=40      # try overrides (dotted keys for sword params)

Prints: finished matches, big-sword win rate (aim ~0.5), fight length median / p10 / p90 (s),
hits per second, average KOs by the big sword. Shipped values: big win 0.51, median 17.2 s.
"""
import copy
import statistics
import sys

import sim


def batch(P, seeds):
    rows = [sim.summary(sim.run(s, P, record=False)) for s in seeds]
    done = [r for r in rows if r["winner"]]
    durs = sorted(r["duration"] for r in done)
    return dict(n=len(rows), finished=len(done),
                big_win=round(sum(r["big_won"] for r in done) / max(1, len(done)), 2),
                dur_med=statistics.median(durs) if durs else None,
                dur_p10=durs[len(durs) // 10] if durs else None,
                dur_p90=durs[9 * len(durs) // 10] if durs else None,
                hits_per_s=round(statistics.mean(r["hits"] / r["duration"] for r in rows), 2),
                big_kills=round(statistics.mean(r["big_kills"] for r in done), 2) if done else None)


def variant(**kw):
    P = copy.deepcopy(sim.DEFAULT)
    for k, v in kw.items():
        if "." in k:
            a, b = k.split(".")
            P[a][b] = v
        else:
            P[k] = v
    return P


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    kw = {}
    for arg in sys.argv[2:]:
        k, v = arg.split("=")
        kw[k] = float(v) if "." in v else int(v)
    print(batch(variant(**kw), range(n)))
