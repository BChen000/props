"""Every setting of the wooden marble run -> picture Short, in one place (shipped values).

Units: the marble radius is 1. y is up, x to the right, z toward the camera; the front face of the bottom row of
blocks is z = 0 and the floor is y = 0. Override any value per episode with EPISODE=<name> (episodes/<name>.py runs
at the end of this file and only reassigns what differs).
"""
import math
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build_preview" if os.environ.get("PREVIEW") else "build"))

# ----------------------------------------------------------------------------------------------- video
W, H, FPS = 1080, 1920, 30
if os.environ.get("PREVIEW"):            # quarter-size set and frames for quick checks
    W, H = 540, 960
R = 1.0
FILE = "Marble_Run_Heart"
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WATERMARK_Y = 0.962              # under the picture, near the bottom edge
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
HOLD_S = 2.6                     # picture held after the last marble settles
STATIC_SAMPLES = (25, 36)        # key-light / ambient samples per pixel of the static path trace (2x size)
if os.environ.get("PREVIEW"):
    STATIC_SAMPLES = (9, 16)

# ----------------------------------------------------------------------------------------------- blocks
B = 6.4                          # cube size (3.2 marble diameters, like the classic wooden kits)
RG = 1.2                         # groove radius (centerline at the block's top face)
RH = 1.25                        # radius of drop holes and tunnels
ROUND = 0.16                     # rounded block edges
MC_STEP = 0.1                    # marching-cubes grid for carved pieces
NCOL = 4
X0 = -12.8                       # left face of column 0
NROW = 5                         # rows 0 (back, rail) .. 4 (front)
TURN_R = 3.2                     # U-turn centerline radius
TURN_IN = 1.6                    # U-turn center sits this far inside the end block
WAVE_A = 0.55                    # wave piece: half the groove's up-down travel
WAVE_N = 3                       # waves along the wave piece
MEANDER_A = 1.0                  # meander piece: sideways swing of the groove
MEANDER_N = 2
BEAM_W, BEAM_H = 3.6, 3.2        # rail and wave piece cross-section
RAIL_END = 36.0                  # the rail runs off-screen to the right up to here
RAIL_POSTS = [17.0, 33.0]        # x of the rail's support posts
BRIDGE_COL = None                # a plain cube can sit across level 3's groove in this column (the groove tunnels under it)
EXIT_COL = 1                     # the bottom level ends in a hole here and the marbles leave through the front face

# ----------------------------------------------------------------------------------------------- room
WALL_Z = -36.0
WALL_H = 90.0
BASEBOARD_H, BASEBOARD_D = 2.6, 0.45
MAT_HALF_W = 18.5                # green felt mat, centered on the exit hole
MAT_DEPTH = 33.0
MAT_T = 0.22

# ----------------------------------------------------------------------------------------------- colours (sRGB)
WOOD_SRGB = (224, 200, 166)      # pale pine blocks (grain is added after the trace)
FLOOR_SRGB = (214, 208, 200)     # whitewashed floor boards
WALL_SRGB = (206, 208, 210)      # light gray wall
BASEBOARD_SRGB = (238, 238, 236)
MAT_SRGB = (90, 148, 74)         # green felt

# ----------------------------------------------------------------------------------------------- the picture
# batches leave the rail in this order; the first batch ends up outermost
BATCHES = [("gold", (250, 192, 36), 55), ("white", (244, 244, 244), 45), ("red", (228, 36, 46), 30)]
SHAPE = "heart"                  # "heart" or "present" (a gift box with a bow, see PRESENT)
N_MARBLES = None                 # default: the sum of BATCHES
REGION_COLOURS = False           # True: colour each spot by where it is in the picture (REGION_SRGB), not by band
REGION_SRGB = {}
PRESENT = dict(half_w=12.5, depth=19.0, bow_r=2.6, bow_dx=1.1, bow_dy=0.8, ribbon_half=1.5, ribbon_at=0.45)
LATTICE_GAP = 0.05               # gap between neighbouring marbles in the finished picture
CUSP_Z = 5.6                     # the heart's notch sits this far in front of the exit hole
SHAPE_TILT = 0.0

# ----------------------------------------------------------------------------------------------- motion
RATE = 7.0                       # marbles per second leaving the rail
V_TRACK = 27.0                   # rolling speed in the grooves (marble radii per second)
G_DROP = 520.0                   # gravity for the hidden drops through the holes
WAVE_DV = 0.16                   # speed swing on the wave piece (fraction)
T_FIRST = -1.6                   # time the first marble enters the first U-turn (negative: already rolling at frame 0)
ACCEL_S = 0.45                   # time to speed up from the queue to V_TRACK
MAT_ROLL_V = 16.0                # speed rolling out of the tunnel across the mat to the picture
PUSH_S = 0.22                    # how long each new marble takes to push the picture outward
RELAX_ITERS = 4                  # contact iterations per physics step (240 Hz)
PILE_HZ = 2.2                    # how quickly a marble follows its point of the growing picture

# ----------------------------------------------------------------------------------------------- camera and light
CAM_TARGET = (-2.4, 7.0, -4.0)
CAM_AZ = math.radians(0.0)
CAM_EL = math.radians(54.0)
CAM_DIST = 120.0
CAM_FOVY = math.radians(31.0)
CAM_SHIFT = (0.0, 0.0)
THUMB_FRAME = None               # default: the finished picture
LIGHT_FROM = (-0.45, 1.0, 0.12)  # key light direction (toward the light): upper left, nearly overhead
LIGHT_ANG = math.radians(16.0)
LIGHT_COL = (2.05, 1.98, 1.86)
SKY_Z = (0.90, 0.93, 0.98)
SKY_H = (0.78, 0.80, 0.84)
EXPOSURE = 0.92
VIG = 0.10
FOG_START, FOG_DIST = 400.0, 200.0

# ----------------------------------------------------------------------------------------------- sound
SOUND_SEED = 11
ROLL_LEVEL = 0.055
TICK_RATE = 26.0                 # wood ticks per second per rolling marble
CLONK_GAIN = 0.07                # marble landing at the bottom of a hole (inside the block, so quiet)
CLACK_GAIN = 0.11                # marble reaching the picture
CHIME_GAIN = 0.065               # sparkle when the picture is finished

EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    for _k, _v in runpy.run_path(_ep, init_globals=dict(globals())).items():
        if not _k.startswith("_") and _k.isupper():
            globals()[_k] = _v
