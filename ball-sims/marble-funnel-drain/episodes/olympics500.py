"""Grand Final of the Marble Olympics (Marble Pop 500-subscriber special, Nov 2026): 500 marbles, one per subscriber,
in red, blue, green and yellow teams of 125, won by blue. Run with EPISODE=olympics500.

settings.py runs this file at its end, so only what differs from episode 1 is reassigned here. 500 marbles is a
different race from every 480-marble episode, so its sims and renders go to build/olympics500/.
Race: seed 12, picked from 500-marble seeds 1-26 for its finale. The last three marbles drain at 21.81, 22.77 and
24.70 s, so the last two circle the hole for almost two seconds, with 9 marbles left when the camera arrives. The
finale is timed as in episode 2: the camera reaches the hole 2.91 s before 3rd place drops and holds until 0.21 s
after the winner drops, and the slow motion around it moves the same way.
"""
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build", "olympics500"))
SEED = int(os.environ.get("SEED", 12))
SIM["N"] = 500
SIM["seed"] = SEED
RECORDED_SIM = os.path.join(HERE, "assets", f"drain500_seed{SEED}.npz")
OUT_NAME = os.environ.get("OUT_NAME", "olympics_final_500")

PLACES = ["BLUE", "YELLOW", "RED", "GREEN"]    # 1st = last marble into the hole, 2nd, 3rd, 4th
TEAM_COLOURS = True
TEAM_SEED = int(os.environ.get("TEAM_SEED", 18))   # even finish: 5/5/5 finalists at 17 s, 3/3/3 when the camera arrives
LOOK["RH"] = SIM["RH"]                         # the hole drawn at its physics size

SHOTS["CLOSE"] = dict(T=(-0.5, -20.6, 1.6), D=20.0, yaw=0.0, elev=29.0, hf=0.24, kd=28.0)
KEYS = [(0.0, "OPEN"), (1.05, "OPEN"), (2.55, "MAIN"), (6.6, "MAIN"), (7.25, "CLOSE"), (8.65, "CLOSE"), (9.3, "MAIN"),
        (10.2, "MAIN"), (18.30, "MAIN2"), (18.90, "FINALE"), (24.91, "FINALE"), (26.21, "OPEN")]
SPEED = [(0.0, 0.55), (1.15, 0.55), (1.75, 1.0), (6.6, 1.0), (7.2, 0.45), (8.7, 0.45), (9.3, 1.0), (12.0, 1.0),
         (12.6, 1.3), (17.65, 1.3), (18.35, 0.7), (24.86, 0.7), (25.26, 1.15), (60.0, 1.15)]
T_END = 26.21
SPLIT_AT = int(os.environ.get("SPLIT_AT", 385))
