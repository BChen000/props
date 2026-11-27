"""Episode 2 in team colours: the race of ep2 (seed 7), but all 480 marbles are red, blue, yellow or green, 120 each.

Run with EPISODE=ep2-teams. It applies episodes/ep2.py, then turns on TEAM_COLOURS. Green is out at 15.8 s, then yellow
(23.15 s) and red (23.89 s); blue wins at 24.51 s. TEAM_SEED 22 was picked for a close finish: of the 30 seeds tried,
it keeps the three finalists even (2 blue, 3 red, 3 yellow when the camera reaches the hole) and leaves blue, the
winner, with a single marble from 22 s on.
"""
_ep = os.path.join(HERE, "episodes", "ep2.py")
with open(_ep, encoding="utf-8") as _f:
    exec(compile(_f.read(), _ep, "exec"))
TEAM_COLOURS = True
TEAM_SEED = 22
OUT_NAME = os.environ.get("OUT_NAME", "last_marble_wins_ep2_colors")
