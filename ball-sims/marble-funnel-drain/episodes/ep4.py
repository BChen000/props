"""Episode 4 of "Last Color Left WINS" (Marble Pop, Nov 2026): eight teams of 60 instead of four, so colours drop out
one by one through the whole push-in. Run with EPISODE=ep4.

Race: seed 26, picked from seeds 1-28 with `pick_race.py races` (passes all three checks): the last three marbles
drain at 22.87, 24.04 and 25.21 s, 1.17 s apart, with 19 marbles left at 17 s and 9 when the camera reaches the hole.
Teams: equal teams need the n-th colour from the bottom to have 60 marbles drained by its own drop, so the drops
are timed at 7.5 s (8th), 9.0, 10.4, 11.8 and 13.2 s (4th), each after the moment the drained count allows.
The finale is timed as in episode 1: the camera reaches the hole 2.9 s before 3rd place drops and holds until
0.21 s after the winner drops.
"""
SEED = int(os.environ.get("SEED", 26))
SIM["seed"] = SEED
RECORDED_SIM = os.path.join(HERE, "assets", f"drain_seed{SEED}.npz")
OUT_NAME = os.environ.get("OUT_NAME", "last_color_left_wins_ep4")

PLACES = ["BLUE", "ORANGE", "GREEN", "PURPLE", "RED", "CYAN", "YELLOW", "PINK"]   # 1st ... 8th
FOURTH_OUT_AT = 13.2
MORE_OUT_AT = [11.8, 10.4, 9.0, 7.5]          # 5th, 6th, 7th, 8th
TEAM_COLOURS = True
TEAM_SEED = int(os.environ.get("TEAM_SEED", 9))
LOOK["RH"] = SIM["RH"]                         # the hole drawn at its physics size

SHOTS["CLOSE"] = dict(T=(-0.5, -20.6, 1.6), D=20.0, yaw=0.0, elev=29.0, hf=0.24, kd=28.0)
KEYS = [(0.0, "OPEN"), (1.05, "OPEN"), (2.55, "MAIN"), (6.6, "MAIN"), (7.25, "CLOSE"), (8.65, "CLOSE"), (9.3, "MAIN"),
        (10.2, "MAIN"), (19.36, "MAIN2"), (19.96, "FINALE"), (25.42, "FINALE"), (26.72, "OPEN")]
SPEED = [(0.0, 0.55), (1.15, 0.55), (1.75, 1.0), (6.6, 1.0), (7.2, 0.45), (8.7, 0.45), (9.3, 1.0), (12.0, 1.0),
         (12.6, 1.3), (18.71, 1.3), (19.41, 0.7), (25.37, 0.7), (25.77, 1.15), (60.0, 1.15)]
T_END = 26.72

THUMB = dict(t=8.3, T=(2.5, -21.0, 1.6), D=20.0, yaw=15.0, elev=33.0, hf=0.33, kd=24.0)
