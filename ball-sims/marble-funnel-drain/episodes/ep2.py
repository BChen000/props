"""Episode 2 of "Last Marble Left WINS" (Marble Pop, Nov 2026): the race of seed 7, won by blue.

Run with EPISODE=ep2. settings.py runs this file at its end, so only what differs from episode 1 is reassigned here.
Race: last drains at 23.15, 23.89 and 24.51 s, with 8 marbles still circling the rim at 20-21 s. The colours roll
past together along y = -18 to -24 at 7.6-8.6 s, a little lower than in episode 1, so CLOSE and THUMB aim lower.
The finale moves with the race, timed as in episode 1: the camera reaches the hole 2.9 s before 3rd place drops
(0.21 s earlier than episode 1) and holds until 0.21 s after the winner drops (0.93 s earlier), and the slow motion
around it moves the same way.
"""
SEED = int(os.environ.get("SEED", 7))
SIM["seed"] = SEED
RECORDED_SIM = os.path.join(HERE, "assets", f"drain_seed{SEED}.npz")
OUT_NAME = os.environ.get("OUT_NAME", "last_marble_wins_ep2")

PLACES = ["BLUE", "RED", "YELLOW", "GREEN"]    # 1st = last marble into the hole, 2nd, 3rd, 4th
LOOK["RH"] = SIM["RH"]                         # the hole drawn at its physics size

SHOTS["CLOSE"] = dict(T=(-0.5, -20.6, 1.6), D=20.0, yaw=0.0, elev=29.0, hf=0.24, kd=28.0)
KEYS = [(0.0, "OPEN"), (1.05, "OPEN"), (2.55, "MAIN"), (6.6, "MAIN"), (7.25, "CLOSE"), (8.65, "CLOSE"), (9.3, "MAIN"),
        (10.2, "MAIN"), (19.64, "MAIN2"), (20.24, "FINALE"), (24.72, "FINALE"), (26.02, "OPEN")]
SPEED = [(0.0, 0.55), (1.15, 0.55), (1.75, 1.0), (6.6, 1.0), (7.2, 0.45), (8.7, 0.45), (9.3, 1.0), (12.0, 1.0),
         (12.6, 1.3), (18.99, 1.3), (19.69, 0.7), (24.67, 0.7), (25.07, 1.15), (60.0, 1.15)]
T_END = 26.02

THUMB = dict(t=8.3, T=(2.5, -21.0, 1.6), D=20.0, yaw=15.0, elev=33.0, hf=0.33, kd=24.0)   # all four colours in frame
