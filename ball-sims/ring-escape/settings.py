"""Ring Escape: every setting you would change, in one place.

Seed, physics, rings, timing, slow motion, all on-screen text and colours.
Everything else in this folder reads from here.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "..", "neon-kit"))
from neon_kit import BALL_COLORS, NAMES as KIT_NAMES  # noqa: E402

# --------------------------------------------------------------------------- episode
SEED = int(os.environ.get("RING_SEED", 8450))  # which simulated race to show; find good ones with search.py
NAMES = list(KIT_NAMES)      # 8 marbles; chip order row 1 then row 2
COLORS = dict(BALL_COLORS)   # name -> RGB
USE_RECORDED_RACE = True     # replay assets/race_<SEED>.npz if it exists (identical on every machine)
RACE_DIR = os.environ.get("RING_RACE_DIR", os.path.join(_HERE, "assets"))  # sim.py record saves here too
RACE_FILE = os.path.join(RACE_DIR, f"race_{SEED}.npz")

# --------------------------------------------------------------------------- canvas
W, H, FPS = 1080, 1920, 30
CX, CY = 540.0, 990.0        # arena centre
TARGET_REST_DEG = -137.0     # the whole race is rotated so the winner comes to rest up-left (clear of the HUD
                             # and of YouTube's buttons on the right); clockwise from +x, y down

# --------------------------------------------------------------------------- physics (sim.py)
N_MARBLES = 8
MARBLE_R = 22.0              # px
RING_HALF_WIDTH = 4.0        # collision half thickness of a ring wall
DT = 1.0 / 240.0             # physics step (s)
R_INNER, R_OUTER = 110.0, 452.0
PHYS = dict(
    v0=640.0,                # marble speed px/s (kept constant, relaxed after hits)
    om0=0.9, om_k=0.05,      # ring spin rad/s: (om0 + om_k * k), alternating direction
    sp_t=0.35,               # the speed-up starts this long after the last ring becomes active
    sp_om=1.6, sp_v=1.18,    # speed-up factors for ring spin and marble speed
    noise=0.12,              # random bounce angle off a wall (rad), keeps the billiards fair
    gaps=[32, 26, 23, 21, 20, 19, 19, 19, 19, 11],   # gap width per ring in degrees (inner -> outer)
)
START_RADIUS = 60.0          # marbles start in a circle of this radius around the centre
POST_WIN = 3.4               # seconds simulated after the win

# --------------------------------------------------------------------------- video timing (timeline.py)
SLOWMO_RATE = 0.24           # playback rate at the slowest
SLOWMO_FROM = 0.40           # slow motion covers sim time [win - SLOWMO_FROM, win + SLOWMO_TO]
SLOWMO_TO = 0.09
SLOWMO_RAMP_IN, SLOWMO_RAMP_OUT = 0.20, 0.32   # s of video to ramp the rate down / back up
CELEBRATE = 1.55             # sim seconds shown after the win
RESET_FRAMES = 16            # loop reset: everything glides back to frame 0 (seamless loop)
NEAR_MISS_GAP = 0.55         # min seconds between "SO CLOSE" callouts

# --------------------------------------------------------------------------- on-screen text
TITLE = "RING ESCAPE"
SUBTITLE = "FIRST ONE OUT WINS"
INTRO_1 = "PICK YOUR COLOR!"
INTRO_2 = "THE FIRST ONE OUT WINS THE CROWN"
LAST_RING = "LAST RING!"
RINGS_LEFT = "{n} RINGS LEFT  •  "
ONE_RING_LEFT = "1 RING LEFT  •  "
HAS_CROWN = " HAS THE CROWN"
WIN_SUB = "LIKE & SUBSCRIBE!"
CAP_START = ("8 MARBLES. 10 RINGS.", "BREAK OUT. STEAL THE CROWN.")
CAP_RACE = ("FIND THE GAP!", "BREAK A RING = TAKE THE CROWN")
CAP_FINAL = ("WHO GETS OUT FIRST?", "THE RINGS ARE SPEEDING UP")
CAP_BREAK = "{name} BREAKS OUT!"
CAP_FINAL_RING = "FINAL RING!"
CAP_NEAR = "SO CLOSE, {name}!"
CAP_WIN = ("LIKE • COMMENT • SUBSCRIBE", "COMMENT YOUR COLOR!")
CAP_BREAK_SECONDS = 1.3
CAP_NEAR_SECONDS = 1.0

# --------------------------------------------------------------------------- render
CRF, PRESET = 17, "veryfast"  # libx264
CHUNKS = 4                    # build.py renders this many chunks, 2 at a time
OUT_DIR = os.environ.get("RING_OUT_DIR", os.path.join(_HERE, "out"))
OUT_NAME = "ring_escape.mp4"
LOUDNESS = dict(I=-14, TP=-1.0, LRA=11)   # two-pass ffmpeg loudnorm (linear) on the final mix

RING_DEG = [math.radians(g) for g in PHYS["gaps"]]
