#!/usr/bin/env python3
"""search: check ability balance and find dramatic seeds for POWER BALLS.

    python search.py balance --n 600              # win rate per fighter, fight length, hits dealt
    python search.py seeds --from 1000 --to 7000  # score fights for drama, print the best (writes out/top_seeds.json)
    python search.py show 1774                    # hit-by-hit story of one seed

A good seed (what 1774 scored on): 36-44 s fight, winner left on 1 HP, a 8-15 s final duel, the eventual
winner in last place at some point, every fighter landing 3+ hits, no lull over 4 s, first hit inside 3.5 s.
"""
import json
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import settings as S
import sim

HERE = Path(__file__).resolve().parent


def summarize(seed):
    s = sim.run(seed)
    hits = [0, 0, 0, 0]
    for e in s.events:
        if e['type'] == 'hit':
            hits[e['attacker']] += 1
    kos = [(e['t'], e['victim']) for e in s.events if e['type'] == 'ko']
    return dict(seed=seed, winner=s.winner, t_end=s.t_end, hits=hits, first_ko=kos[0][0] if kos else None)


def score_seed(seed):
    s = sim.run(seed)
    if s.winner is None or s.t_end is None:
        return None
    T = s.t_end
    hits_ev = [e for e in s.events if e['type'] == 'hit']
    kos = sorted(e['t'] for e in s.events if e['type'] == 'ko')
    if len(kos) != 3:
        return None
    gaps = [kos[0], kos[1] - kos[0], kos[2] - kos[1]]
    hp = [S.HP] * 4
    leader = None
    changes = 0
    comeback = False
    for e in hits_ev:
        hp[e['victim']] = e['hp']
        alive = [i for i in range(4) if hp[i] > 0]
        mx = max(hp[i] for i in alive)
        top = [i for i in alive if hp[i] == mx]
        if len(top) == 1 and top[0] != leader:
            if leader is not None:
                changes += 1
            leader = top[0]
        if e['t'] > 6 and len(alive) >= 3:
            mn = min(hp[i] for i in alive)
            if hp[s.winner] == mn and sum(1 for i in alive if hp[i] == mn) == 1:
                comeback = True
    hit_times = [e['t'] for e in hits_ev]
    max_lull = max([hit_times[0]] + [b - a for a, b in zip(hit_times, hit_times[1:])])
    hits = [0, 0, 0, 0]
    for e in hits_ev:
        hits[e['attacker']] += 1
    win_hp = s.balls[s.winner].hp
    sc = 0.0
    sc += {1: 4.0, 2: 2.0, 3: 0.5}.get(win_hp, 0.0)
    fd = gaps[2]
    sc += 2.0 if 8 <= fd <= 15 else (1.0 if 6 <= fd <= 18 else -1.0)
    sc += 1.0 if gaps[0] >= 14 else 0.0
    sc += 1.0 if min(gaps[1], gaps[2]) >= 5 else (-2.0 if min(gaps[1], gaps[2]) < 3 else 0.0)
    sc += 0.5 * min(changes, 6)
    sc += 2.0 if comeback else 0.0
    sc += 1.5 if min(hits) >= 3 else (0.0 if min(hits) >= 2 else -3.0)
    sc += 1.0 if hit_times[0] < 3.5 else 0.0
    sc += 1.5 if max_lull <= 4.0 else (0.0 if max_lull <= 5.5 else -2.0)
    if 36 <= T <= 44:
        sc += 3.0
    elif 33 <= T <= 47:
        sc += 1.0
    else:
        sc -= 4.0
    return dict(seed=seed, score=round(sc, 2), T=round(T, 1), winner=S.NAMES[s.winner], win_hp=win_hp,
                kos=[round(k, 1) for k in kos], changes=changes, comeback=comeback, hits=hits,
                lull=round(max_lull, 1), first_hit=round(hit_times[0], 1), final_kind=hits_ev[-1]['kind'],
                ko_order=[S.NAMES[e['victim']] for e in s.events if e['type'] == 'ko'])


def _opt(args, name, default, cast=int):
    return cast(args[args.index(name) + 1]) if name in args else default


def main():
    args = sys.argv[1:]
    mode = args[0] if args else 'help'
    jobs = _opt(args, '--jobs', 2)
    if mode == 'balance':
        n = _opt(args, '--n', 600)
        with Pool(jobs) as pool:
            res = pool.map(summarize, range(n), chunksize=25)
        wins = Counter(r['winner'] for r in res)
        durs = sorted(r['t_end'] for r in res if r['t_end'])
        print(f'{n} fights  draws={wins.get(None, 0)}')
        for i, name in enumerate(S.NAMES):
            print(f'  {name:7s} {S.ABILITIES[i]:9s} wins {100 * wins.get(i, 0) / n:5.1f}%   '
                  f'avg hits dealt {sum(r["hits"][i] for r in res) / n:.1f}')
        print(f'  fight length median {durs[len(durs) // 2]:.1f}s  p10 {durs[len(durs) // 10]:.1f}s  '
              f'p90 {durs[9 * len(durs) // 10]:.1f}s')
    elif mode == 'seeds':
        a, b = _opt(args, '--from', 1000), _opt(args, '--to', 7000)
        top = _opt(args, '--top', 15)
        with Pool(jobs) as pool:
            res = [r for r in pool.map(score_seed, range(a, b), chunksize=50) if r]
        res.sort(key=lambda r: -r['score'])
        out = HERE / 'out' / 'top_seeds.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(res[:60], indent=1))
        print('winners among the top 40:', dict(Counter(r['winner'] for r in res[:40])))
        for r in res[:top]:
            print(r)
    elif mode == 'show':
        seed = int(args[1]) if len(args) > 1 else S.SEED
        s = sim.run(seed)
        hp = [S.HP] * 4
        print(f'seed {seed}: winner {S.NAMES[s.winner] if s.winner is not None else "draw"} at {s.t_end:.1f}s')
        for e in s.events:
            if e['type'] == 'hit':
                hp[e['victim']] = e['hp']
                print(f"  {e['t']:5.1f}s  {S.NAMES[e['attacker']]:>6} -> {S.NAMES[e['victim']]:<6} ({e['kind']:9s}) "
                      f"HP {' '.join(str(h) for h in hp)}")
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
