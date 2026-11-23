"""Balance check: how long races last with the current settings.PHYS (or a variant).

Prints the median time each ring breaks, the 10/50/90 % win times and the median last-ring
stretch over N seeds. Use it after changing ring count, gaps or speeds, before searching seeds.
The shipped settings give a median win of 24.8 s over seeds 100-199; 23 of those 100 races
run past 40 s and are skipped (search.py drops them too).

  python tune.py 100
"""
import sys

import numpy as np

import settings as S
import sim

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    B = []
    for sd in range(100, 100 + n):
        r = sim.run(sd, S.PHYS)
        b = sim.breaks(r)
        if r["winner"] < 0 or len(b) != len(S.PHYS["gaps"]):
            continue
        B.append([x[0] for x in b])
    B = np.array(B)
    print("finished races", len(B), "of", n)
    print("median break time per ring (s):", np.median(B, axis=0).round(1))
    print("win time 10/50/90 %:", np.percentile(B[:, -1], [10, 50, 90]).round(1))
    print("median last-ring stretch (s):", np.median(B[:, -1] - B[:, -2]).round(1))
