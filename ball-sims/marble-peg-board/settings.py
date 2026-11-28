"""Every setting of the marble peg-board challenge Short ("Which bin gets the most marbles?"), in one place.

A wooden board stands upright with rows of brass pegs and 7 bins at the bottom. Marbles drop one by one from a
hopper at the top centre, bounce down through the pegs (every peg hit flashes the peg and rings a note), and pile up
in the bins, which count them. The bin with the most marbles at the end wins.

Units: the marble radius is 1. x right, y up, z toward the camera; the board's front face is z = 0 and marble centres
roll down at z = Z_MARBLE. Override values per episode with EPISODE=<name> (episodes/<name>.py runs at the end).
"""
import math
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build_preview" if os.environ.get("PREVIEW") else "build"))

# ----------------------------------------------------------------------------------------------- video
W, H, FPS = 1080, 1920, 30
if os.environ.get("PREVIEW"):
    W, H = 540, 960
FILE = "Marble_Peg_Board"
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
STATIC_SAMPLES = (36, 49) if not os.environ.get("PREVIEW") else (9, 16)
HOLD_S = 3.2                     # after the last marble lands: count, winner, crown

# ----------------------------------------------------------------------------------------------- board
BINS = 7
DX = 5.0                         # peg spacing in a row = bin width
DY = 4.4                         # row spacing
ROWS = 8                         # rows alternate 7 pegs (one at x = 0) and 6 pegs (in line with the bin walls)
PEG_HALF = 0.62                  # pegs are square posts turned 45 degrees (diamonds), half the side
PEG_DEPTH = 2.6                  # how far the pegs and walls stand out of the board
Z_MARBLE = 1.05                  # marble centres (just in front of the board)
BIN_FLOOR_Y = 3.0
BIN_H = 27.0                     # bin walls
WALL_T = 0.5                     # bin walls and the side rails
GAP_PEGS_BINS = 3.2              # from the bin tops to the lowest peg row
HOPPER_GAP = 5.2                 # from the top peg row up to the hopper mouth
HOPPER_W = 7.0                   # hopper box, outside width and height
HOPPER_H = 6.0
BOARD_MARGIN = 2.2               # board edge beyond the side rails
BOARD_T = 1.0

# ----------------------------------------------------------------------------------------------- colours (sRGB)
BOARD_SRGB = (238, 192, 132)     # warm maple board
RAIL_SRGB = (150, 96, 56)        # darker walnut rails, bin walls, hopper
PEG_SRGB = (212, 160, 48)        # brass pegs
PEG_GLOW_SRGB = (255, 214, 120)  # a peg's flash when a marble hits it
BASE_SRGB = (120, 74, 42)
MARBLE_SRGB = [(236, 52, 52), (250, 138, 28), (250, 206, 38), (60, 200, 90), (40, 170, 235), (70, 100, 240),
               (160, 90, 230), (245, 90, 170)]

# ----------------------------------------------------------------------------------------------- marbles and physics
N = 72
RATE = 5.0                       # marbles per second out of the hopper
T_FIRST = 0.55                   # first marble out (s)
SEED = int(os.environ.get("SEED", 2))     # picked with `sim.py --search 1-40`: bin 3 wins 22 to 21, lead changes at 20.1 s
G = 120.0                        # gravity (marble radii / s^2): with DRAG, a slow, readable fall
SIM_HZ = 4000
REC_HZ = 120
K_CONTACT = 3.0e5                # contact stiffness (per unit mass)
ZETA_PEG, ZETA_WALL, ZETA_BALL = 0.6, 0.6, 0.6     # damping ratios
SPAWN_JITTER = 0.35              # random x offset at the hopper mouth
SPAWN_V = 6.0                    # downward speed leaving the hopper
DRAG = 6.0                       # drag (1/s), like marbles rolling down a tilted board: top speed G/DRAG
T_SIM = 40.0                     # simulate this long at most; stops 1 s after everything rests

# ----------------------------------------------------------------------------------------------- camera and light
CAM_AZ = math.radians(12.0)      # a little from the right, so the pegs show their depth
CAM_EL = math.radians(4.0)
CAM_FOVY = math.radians(30.0)
CAM_SHIFT = (0.0, 0.0)
FRAME_PAD = 1.075                # framing: board height times this fills the frame height (room for the watermark)
FOG_START, FOG_DIST = 400.0, 200.0

# ----------------------------------------------------------------------------------------------- text
TITLE = "WHICH BIN WINS?"
SUBTITLE = "PICK 1 TO 7"
TITLE_UNTIL = 3.4                # s
WIN_TEXT = "BIN {n} WINS!"

# ----------------------------------------------------------------------------------------------- sound
SOUND_SEED = 5
SCALE = [72, 74, 76, 79, 81, 84, 86, 88, 91, 93]   # C major pentatonic, low row to high row
PEG_GAIN = 0.20
LAND_GAIN = 0.55

EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    for _k, _v in runpy.run_path(_ep, init_globals=dict(globals())).items():
        if not _k.startswith("_") and _k.isupper():
            globals()[_k] = _v
