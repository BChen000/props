"""Finds event seeds that tell the special's story: every team wins one event and finishes once in every place, so
all four teams go into the double-points final tied.

  python pick_seeds.py                     # seeds 2000-2999 for every event but the final, then the best combinations
  python pick_seeds.py --seeds 0-5999      # a wider search (POWER BALLS takes about 1 min per 1,000 seeds per event)

Each event is searched in its own template copy (events.copy_template), with that template's own drama score:
POWER BALLS uses its search.py score_seed(); Sword Roulette uses its search.py score() with filters loosened for 4
balls. Put the chosen seeds and their places in settings.EVENTS. The final's places are free: marble-funnel-drain
gives its colours after the race (see its README), so pick them for the ending you want.
"""
import itertools
import json
import subprocess
import sys

import events as E
import settings as S

SEARCH = {
    "ability-battle-template": (
        "import json, sys, search, settings as S\n"
        "from multiprocessing import Pool\n"
        "a, b = int(sys.argv[1]), int(sys.argv[2])\n"
        "with Pool(2) as p:\n"
        "    for r in p.imap(search.score_seed, range(a, b), chunksize=50):\n"
        "        if r:\n"
        "            print(json.dumps(dict(seed=r['seed'], score=r['score'] + (1.0 if r['comeback'] else 0.0),\n"
        "                                  places=[r['winner']] + r['ko_order'][::-1])))\n"),
    "sword-roulette": (
        "import json, sys, search, sim\n"
        "from multiprocessing import Pool\n"
        "a, b = int(sys.argv[1]), int(sys.argv[2])\n"
        "def keep(s):\n"
        "    return (s is not None and 12 <= s['dur'] <= 26 and s['big_in_final'] and s['whp'] <= 30\n"
        "            and s['maxgap'] <= 3.8 and s['first_kill'] <= 8 and 3.0 <= s['duel_len'] <= 9.0\n"
        "            and s['duel_clash'] >= 2 and s['fb'] <= 0.6 * sim.ARENA_R and s['duel_r'] <= 0.65 * sim.ARENA_R)\n"
        "with Pool(2) as p:\n"
        "    for s in p.imap(search.score, range(a, b), chunksize=20):\n"
        "        if keep(s):\n"
        "            sc = 10 + min(s['duel_clash'], 6) * 0.5 + (4.5 if not s['big_won'] else 0)\n"
        "            sc += (1 if s['whp'] <= 10 else 0) + (1 if 15 <= s['dur'] <= 22 else 0)\n"
        "            print(json.dumps(dict(seed=s['seed'], score=sc, places=[s['winner']] + [o[1] for o in s['order']][::-1])))\n"),
}


def candidates(ev, a, b):
    cwd = E.copy_template(ev)
    out = subprocess.run([sys.executable, "-c", SEARCH[ev["template"]], str(a), str(b)], cwd=cwd, capture_output=True,
                         text=True, check=True).stdout
    return [json.loads(x) for x in out.splitlines() if x.startswith("{")]


def main():
    a, b = 2000, 3000
    if "--seeds" in sys.argv:
        lo, hi = sys.argv[sys.argv.index("--seeds") + 1].split("-")
        a, b = int(lo), int(hi) + 1
    evs = [e for e in S.EVENTS if not e.get("double")]
    pools = []
    for ev in evs:
        c = sorted(candidates(ev, a, b), key=lambda r: -r["score"])[:40]
        print("%-15s %4d candidates, best %s" % (ev["key"], len(c), c[0] if c else None), flush=True)
        pools.append(c)
    combos = []
    for pick in itertools.product(*pools):
        rows = [p["places"] for p in pick]
        if all(len({r[k] for r in rows}) == len(S.TEAMS) for k in range(len(S.TEAMS))):
            combos.append((sum(p["score"] for p in pick), pick))
    combos.sort(key=lambda c: -c[0])
    print("%d combinations tie every team before the final; the best:" % len(combos))
    for sc, pick in combos[:10]:
        print("  %.1f  " % sc + "  ".join("%s %d %s" % (ev["key"], p["seed"], "".join(t[0] for t in p["places"]))
                                         for ev, p in zip(evs, pick)))


if __name__ == "__main__":
    main()
