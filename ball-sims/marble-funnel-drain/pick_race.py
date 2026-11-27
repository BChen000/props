"""Ranks races and team colourings for a new "Last Marble Left WINS" episode.

Usage:
  python3 pick_race.py races 1-40                 simulate any seed not yet in BUILD_DIR (about 10 s each), then rank
  EPISODE=<name> python3 pick_race.py teams 1-40  rank TEAM_SEEDs for that episode's race and PLACES

races: a good finale has the last three marbles draining 0.7-2 s apart, 6-12 marbles left when the camera reaches the
hole (2.9 s before 3rd place drops, as in episode 1), and the winner out between 21.5 and 27.5 s, so the shipped
camera timing only needs a shift. Rows marked * pass all three; "left@17" is the crowd during the push-in.
teams: how many marbles each finalist colour (1st/2nd/3rd place) still has at 17 s, when the camera reaches the hole
and 3 s before the winner drops, then the colours of the last nine marbles to drain. Pick a seed with even counts.
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S


def seed_range(arg):
    a, _, b = arg.partition("-")
    return range(int(a), int(b or a) + 1)


def races(seeds):
    rows = []
    for seed in seeds:
        path = os.path.join(S.BUILD, "sim_seed%d.npz" % seed)
        if not os.path.exists(path):
            env = dict(os.environ, SEED=str(seed), USE_RECORDED_SIM="0")
            env.pop("EPISODE", None)
            subprocess.run([sys.executable, os.path.join(HERE, "sim.py")], env=env, check=True,
                           stdout=subprocess.DEVNULL)
        dr = np.load(path)["drain_t"]
        if (dr < 0).any():
            print("%4d  not every marble drained; skipped" % seed)
            continue
        t3, t2, t1 = np.sort(dr)[-3:]
        g32, g21 = t2 - t3, t1 - t2
        ring = int((dr > t3 - 2.9).sum())
        ok = 0.7 <= g32 <= 2.0 and 0.7 <= g21 <= 2.0 and 6 <= ring <= 12 and 21.5 <= t1 <= 27.5
        rows.append((not ok, seed, t3, g32, g21, ring, int((dr > 17.0).sum()), t1))
    print("    seed  3rd out  gap 3-2  gap 2-1  left@camera  left@17  winner out")
    for r in sorted(rows):
        mark = " " if r[0] else "*"
        print("  %s %4d %8.2f %8.2f %8.2f %12d %8d %11.2f" % ((mark,) + r[1:]))


def teams(seeds):
    import timeline as TL
    from sim import sim_path
    path = sim_path()
    cam = next(t for t, shot in S.KEYS if shot == "FINALE")
    initials = "/".join(p[0] for p in S.PLACES[:3])
    print("race %s, camera at the hole at sim %.2f s; counts are %s marbles left" % (os.path.basename(path), cam, initials))
    for seed in seeds:
        S.TEAM_SEED = seed
        ep = TL.Episode(path)
        dr = ep.d["drain_t"]
        order = np.argsort(dr)
        t1 = dr[order[-1]]

        def left(t):
            return "/".join(str(int(((dr > t) & (ep.btype == k)).sum())) for k in (1, 2, 3))

        last9 = "".join(S.PLACES[ep.btype[b] - 1][0] for b in order[-9:])
        print("  %3d   at 17 s %-9s  at camera %-8s  3 s before the end %-7s  last nine %s"
              % (seed, left(17.0), left(cam), left(t1 - 3.0), last9))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("races", "teams"):
        sys.exit(__doc__)
    {"races": races, "teams": teams}[sys.argv[1]](seed_range(sys.argv[2]))
