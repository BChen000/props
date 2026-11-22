"""Sword Roulette: every setting you would change, in one place.

Text, colours, the episode seed, timings and physics. Everything else reads from here.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "..", "style-kit"))
from kit import BALL_COLORS, NAMES as KIT_NAMES  # noqa: E402

# --------------------------------------------------------------------------- episode
SEED = 3993                 # which simulated match to show; find good ones with search.py
NAMES = list(KIT_NAMES)     # ball order: chips left->right, roulette clockwise from top
COLORS = dict(BALL_COLORS)  # name -> RGB

# --------------------------------------------------------------------------- canvas
W, H, FPS = 1080, 1920, 30
ARENA_CX, ARENA_CY, ARENA_R = 540.0, 1010.0, 445.0
RING_R = 250.0              # start ring (roulette positions)

# --------------------------------------------------------------------------- on-screen text
TITLE = "SWORD ROULETTE"
SUBTITLE = "One random ball gets the BIG sword!"
INTRO_PROMPT = "Comment who you think will win!"
GOT_SWORD = "{name} GETS THE BIG SWORD!"
FIGHT_PROMPT = "Can anyone stop the BIG sword?"
AFTER_BIG_DOWN_PROMPT = "Comment your color!"
OUT_MSG = "{name} IS OUT!"
WIN_TITLE = "{name} WINS!"
WIN_SUB_BIG = "The BIG sword took them all!"   # big-sword owner won
WIN_SUB_KILLER = "Took down the BIG sword!"     # winner landed the blow on the big sword
WIN_SUB_SURVIVOR = "Survived the BIG sword!"    # someone else took the big sword down
BIG_TAG = "BIG SWORD"
BANNER_FIGHT = "FIGHT!"
BANNER_DUEL = "FINAL DUEL!"
STATUS_LEFT = "{n} LEFT"
STATUS_PICK, STATUS_SPIN, STATUS_GOT = "PICK YOUR COLOR", "SPINNING...", "BIG SWORD!"
STATUS_FIGHT, STATUS_DUEL, STATUS_WIN = "FIGHT!", "FINAL DUEL!", "WINNER!"
SUBSCRIBE_LABEL = "SUBSCRIBE"
NEXT_LINES = ("What do you want to see next?", "Tell me in the comments!")

# --------------------------------------------------------------------------- timings (video seconds)
SPIN_START, SPIN_END = 0.75, 4.55   # roulette spin (cubic ease-out)
SPIN_TURNS = 4
START_ANGLE = -math.pi / 2 + 0.55   # needle rest angle
FLY_START, FLY_END = 4.85, 5.35     # big sword flies onto the chosen ball
POP_START, POP_STEP = 5.35, 0.06    # small swords pop on
FIGHT_TXT = 5.85                    # "FIGHT!" banner
V_FIGHT = 6.0                       # physics starts (sim t = 0)
REVEAL_AFTER_FINAL = 1.15           # final blow -> winner + SUBSCRIBE appear together
OUTRO = 5.4                         # end card length
DUEL_BANNER_DELAY = 0.85            # "FINAL DUEL!" after the 4th KO
# slow motion (rates are sim seconds per video second)
SLOWMO_KO = (0.10, 0.22, 0.35)      # around each KO: from t-0.10 to t+0.22 at 0.35x
SLOWMO_FINAL = (0.85, 0.28)         # last 0.85 sim-s before the final blow at 0.28x
SLOWMO_AFTER = (0.5, 0.45)          # 0.5 sim-s after it at 0.45x
HITSTOP = 0.32                      # freeze on the final blow (video s)
FINAL_ZOOM = 1.18

# --------------------------------------------------------------------------- physics
PHYSICS = dict(
    dt=1 / 120,
    ball_r=40.0,
    hp=100,
    speed=380.0,                     # px/s base speed (knockback relaxes back to it)
    relax=0.55,
    small=dict(grip=18.0, blade=100.0, width=18.0, dmg=15, omega=4.2, knock=240.0),
    big=dict(grip=28.0, blade=200.0, width=34.0, dmg=30, omega=2.4, knock=340.0),
    hit_cd=0.40,                     # s before the same sword can hit the same ball again
    clash_cd=0.22,
    clash_push=150.0,
    max_time=60.0,
    seek={6: 0.0, 5: 0.2, 4: 0.5, 3: 1.0, 2: 1.8},   # rad/s steering toward the nearest enemy
)
