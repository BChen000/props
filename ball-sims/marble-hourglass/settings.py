"""Every setting of the rainbow marble hourglass Short ("Which color falls last?"), in one place.

An upright wooden board holds a marble hourglass: a funnel of slanted rails narrows to a neck and opens out again
below. The top half starts full of marbles in rainbow patches; they pour through the neck and heap up in the bottom
half. A colour is out when its last marble passes the neck; the last colour still up top wins.

Units: the marble radius is 1. x right, y up, z toward the camera; the board's front face is z = 0 and marble
centres move at z = Z_MARBLE. Override values per episode with EPISODE=<name> (episodes/<name>.py runs at the end).
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
FILE = "Marble_Hourglass"
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
STATIC_SAMPLES = (36, 49) if not os.environ.get("PREVIEW") else (9, 16)
LEAD_S = 3.2                     # video starts this long before the gate opens: the full hourglass, then 3-2-1-GO
HOLD_S = 3.0                     # after the winner's last marble passes the neck

# ----------------------------------------------------------------------------------------------- hourglass (in the board plane)
HALF_W = 13.0                    # inner half-width of the frame (top and bottom chambers)
TOP_Y = 80.0                     # inner top of the frame
NECK_Y = 42.0                    # centre of the neck
NECK_HALF = 2.55                 # half the neck's opening (2.55 marble radii: two marbles abreast without jamming)
FUNNEL_TOP_Y = 64.0              # where the top funnel's slanted rails start (full width above this)
FUNNEL_BOT_Y = 18.0              # where the bottom funnel's slanted rails reach full width (bottom chamber below)
FLOOR_Y = 4.0
RAIL_T = 0.9                     # rail thickness
DEPTH = 2.6                      # how far the rails stand out of the board
Z_MARBLE = 1.05
BOARD_MARGIN = 2.4
BOARD_T = 1.0

# ----------------------------------------------------------------------------------------------- colours (sRGB)
BOARD_SRGB = (92, 58, 40)        # dark walnut board
RAIL_SRGB = (226, 192, 140)      # pale maple rails and frame
BASE_SRGB = (150, 104, 66)
COLOURS = [("RED", (236, 52, 52)), ("ORANGE", (250, 138, 28)), ("YELLOW", (250, 206, 38)),
           ("GREEN", (60, 200, 90)), ("BLUE", (52, 120, 240)), ("PURPLE", (160, 90, 230))]
PER_COLOUR = 24                  # marbles per colour
BATCH = 6                        # poured in one-colour batches of this many, in a random order (sand-art patches)

# ----------------------------------------------------------------------------------------------- physics
SEED = int(os.environ.get("SEED", 37))     # from sim.py --search 1-60
G = 80.0
DRAG = 2.5                       # light drag, like marbles rolling on a tilted board
SIM_HZ = 4000
REC_HZ = 120
K_CONTACT = 3.0e5
ZETA_WALL, ZETA_BALL = 0.6, 0.6
FILL_STREAM_S = 0.05             # one marble poured in every this many seconds before the clock starts
POUR_V = 45.0                    # poured marbles start moving down this fast, so each is clear before the next
FILL_S = 11.6                    # the gate opens (the clock starts) at this sim time: pour 7.2 s, settle, then LEAD_S at rest on camera
T_SIM = 40.0

# ----------------------------------------------------------------------------------------------- camera and light
CAM_AZ = math.radians(-10.0)
CAM_EL = math.radians(3.0)
CAM_FOVY = math.radians(30.0)
CAM_SHIFT = (0.0, 0.0)
FRAME_PAD = 1.10
FOG_START, FOG_DIST = 400.0, 200.0

# ----------------------------------------------------------------------------------------------- text
TITLE = "WHICH COLOR FALLS LAST?"
SUBTITLE = "PICK YOUR COLOR!"
WIN_TEXT = "{c} WINS!"
CHIP_X = 0.093                   # counter discs beside the top half: x of the left column (the right one mirrors it)
CHIP_Y0, CHIP_DY = 0.31, 0.105   # first row and spacing, as fractions of the height
CHIP_R = 56                      # disc radius in px at 1080 wide
THUMB_AFTER_GO = 2.5             # the thumbnail is this long after the gate opens

# ----------------------------------------------------------------------------------------------- sound
SOUND_SEED = 3
NOTES = {"RED": 72, "ORANGE": 74, "YELLOW": 76, "GREEN": 79, "BLUE": 81, "PURPLE": 84}   # C major pentatonic
NECK_GAIN = 0.16
KNOCK_GAIN = 0.8

EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    for _k, _v in runpy.run_path(_ep, init_globals=dict(globals())).items():
        if not _k.startswith("_") and _k.isupper():
            globals()[_k] = _v
