"""Episode 3 of "Last Marble Left WINS" (Marble Pop, Nov 2026): the race of seed 30 in new team colours, won by purple.

Run with EPISODE=ep3. settings.py runs this file at its end, so only what differs from episode 1 is reassigned here.
Race: picked from seeds 1-40 for an even finale with a crowd. The last three marbles drain at 23.92, 25.01 and 26.24 s
(about 1.1 and 1.2 s apart), with 14 marbles left at 20 s and 7 at 22 s. The finale is timed as in episode 1: the
camera reaches the hole 2.9 s before 3rd place drops and holds until 0.21 s after the winner drops.
TEAM_SEED 19 was picked out of 40 for a neck-and-neck finish: purple, orange and cyan have 3, 3 and 4 marbles when
the camera reaches the hole, and 2 each at 23 s.
"""
SEED = int(os.environ.get("SEED", 30))
SIM["seed"] = SEED
RECORDED_SIM = os.path.join(HERE, "assets", f"drain_seed{SEED}.npz")
OUT_NAME = os.environ.get("OUT_NAME", "last_color_left_wins_ep3")

PLACES = ["PURPLE", "ORANGE", "CYAN", "PINK"]  # 1st = last marble into the hole, 2nd, 3rd, 4th (new colours, so it
                                               # doesn't look like the red/blue/yellow/green episode 2)
TEAM_COLOURS = True
TEAM_SEED = 19
LOOK["RH"] = SIM["RH"]                         # the hole drawn at its physics size

SHOTS["CLOSE"] = dict(T=(-0.5, -20.6, 1.6), D=20.0, yaw=0.0, elev=29.0, hf=0.24, kd=28.0)
KEYS = [(0.0, "OPEN"), (1.05, "OPEN"), (2.55, "MAIN"), (6.6, "MAIN"), (7.25, "CLOSE"), (8.65, "CLOSE"), (9.3, "MAIN"),
        (10.2, "MAIN"), (20.41, "MAIN2"), (21.01, "FINALE"), (26.45, "FINALE"), (27.75, "OPEN")]
SPEED = [(0.0, 0.55), (1.15, 0.55), (1.75, 1.0), (6.6, 1.0), (7.2, 0.45), (8.7, 0.45), (9.3, 1.0), (12.0, 1.0),
         (12.6, 1.3), (19.76, 1.3), (20.46, 0.7), (26.4, 0.7), (26.8, 1.15), (60.0, 1.15)]
T_END = 27.75

VOLUME_DB = -1.1                               # this race's soundtrack is quieter; lands at -14.0 LUFS like episode 2
THUMB = dict(t=8.3, T=(2.5, -21.0, 1.6), D=20.0, yaw=15.0, elev=33.0, hf=0.33, kd=24.0)
