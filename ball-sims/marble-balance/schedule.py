"""The race on paper: from the landing times in settings.py and the two masses, the running totals in each basket,
which side should be down after every landing, and where the lead changes. Run it after editing LAND_LEFT /
LAND_RIGHT (or the teams) to check a new race before any physics or rendering; sim.py then shows what the beam
really does (landing knocks can lift it for a moment, and a lead of under a marble tips slowly).

    python3 schedule.py
"""
import settings as C


def totals():
    ev = sorted([(t, "L") for t in C.LAND_LEFT] + [(t, "R") for t in C.LAND_RIGHT])
    ml = mr = 0.0
    nl = nr = 0
    down = None
    rows = []
    for t, s in ev:
        if s == "L":
            ml += C.LEFT["mass"]
            nl += 1
        else:
            mr += C.RIGHT["mass"]
            nr += 1
        new = "L" if ml > mr else ("R" if mr > ml else down)
        rows.append((t, s, nl, nr, ml, mr, new, new != down))
        down = new
    return rows


if __name__ == "__main__":
    rows = totals()
    flips = 0
    last = None
    for t, s, nl, nr, ml, mr, down, changed in rows:
        mark = ""
        if changed:
            flips += 1
            gap = f" ({t - last:.2f} s after the last change)" if last is not None else ""
            mark = f"  <- {C.RIGHT['name'] if down == 'R' else C.LEFT['name']} goes down{gap}"
            last = t
        print(f"{t:6.2f} s  {C.LEFT['name'] if s == 'L' else C.RIGHT['name']:6s} lands   {nl:2d} vs {nr:2d}   "
              f"{ml:6.2f} vs {mr:6.2f}{mark}")
    win = rows[-1][6]
    print(f"{flips} lead changes; {C.RIGHT['name'] if win == 'R' else C.LEFT['name']} wins "
          f"{max(rows[-1][4], rows[-1][5]):.2f} to {min(rows[-1][4], rows[-1][5]):.2f}")
